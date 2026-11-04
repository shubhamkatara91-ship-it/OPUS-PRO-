from datetime import datetime, timezone
from collections import Counter
import os, sqlite3
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

APP_NAME = "OPUS PRO"
DB_PATH = os.getenv("OPUS_DB_PATH", "/tmp/opus_history.sqlite3")
app = FastAPI(title=APP_NAME, version="1.0.0", description="Educational analytics backend. No wagering or automated betting.")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period TEXT NOT NULL,
        outcome TEXT NOT NULL CHECK(outcome IN ('BIG','SMALL')),
        created_at TEXT NOT NULL
    )""")
    return conn

class ResultIn(BaseModel):
    period: str = Field(min_length=1, max_length=80)
    outcome: str

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>OPUS PRO</title>
    <style>body{font-family:Arial;background:#0b1020;color:#eef2ff;margin:0;padding:24px}main{max-width:760px;margin:auto}section{background:#151d33;padding:18px;border-radius:14px;margin:14px 0}h1{color:#7dd3fc}code{color:#86efac}a{color:#7dd3fc}</style></head>
    <body><main><h1>OPUS PRO</h1><p>Backend server is online.</p><section><h3>System status</h3><p>API: <b>Available</b></p><p>Live provider: <b>Not configured</b></p><p>Analysis mode: Historical data only</p></section>
    <section><h3>API endpoints</h3><p><code>/health</code> — server status</p><p><code>/api/status</code> — provider connection status</p><p><code>/api/history</code> — stored outcomes</p><p><code>/api/analysis</code> — basic historical frequency analysis</p><p><a href='/docs'>Open API documentation</a></p></section>
    <p>Predictions are not guaranteed. No betting, wallet, deposits or withdrawals are supported.</p></main></body></html>"""

@app.get("/health")
def health():
    return {"ok": True, "service": APP_NAME, "time": datetime.now(timezone.utc).isoformat()}

@app.get("/api/status")
def status():
    configured = bool(os.getenv("PROVIDER_API_URL"))
    return {"server": "online", "provider": "configured" if configured else "not_configured",
            "live_data": False, "message": "Add a verified provider API URL and credentials before enabling live data."}

@app.post("/api/history")
def add_result(item: ResultIn):
    outcome = item.outcome.strip().upper()
    if outcome not in ("BIG", "SMALL"):
        raise HTTPException(400, "outcome must be BIG or SMALL")
    conn = db()
    try:
        conn.execute("INSERT INTO results(period,outcome,created_at) VALUES(?,?,?)",
                     (item.period, outcome, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    finally:
        conn.close()
    return {"saved": True, "period": item.period, "outcome": outcome}

@app.get("/api/history")
def history(limit: int = 100):
    limit = max(1, min(limit, 500))
    conn = db()
    try:
        rows = conn.execute("SELECT period,outcome,created_at FROM results ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    finally:
        conn.close()
    return {"items": [{"period":r[0],"outcome":r[1],"created_at":r[2]} for r in rows]}

@app.get("/api/analysis")
def analysis():
    conn = db()
    try:
        rows = conn.execute("SELECT outcome FROM results ORDER BY id DESC LIMIT 100").fetchall()
    finally:
        conn.close()
    values = [r[0] for r in rows]
    counts = Counter(values)
    total = len(values)
    return {"sample_size": total, "big": counts["BIG"], "small": counts["SMALL"],
            "big_pct": round(counts["BIG"]*100/total, 2) if total else None,
            "small_pct": round(counts["SMALL"]*100/total, 2) if total else None,
            "signal": "insufficient_data" if total < 20 else "historical_frequency_only",
            "note": "Historical frequencies do not predict the next outcome or guarantee accuracy."}
