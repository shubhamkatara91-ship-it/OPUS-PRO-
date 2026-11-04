from datetime import datetime, timezone
import os
import time
import sqlite3
from fastapi import FastAPI, HTTPException, Header
import hmac
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from signal_engine import analyze as analyze_history
from live_provider import fetch_live_snapshot, ProviderNotConfigured, ProviderError

APP_NAME = "OPUS PRO"
DB_PATH = os.getenv("OPUS_DB_PATH", "/tmp/opus_history.sqlite3")
TOOL_PROFILES = [
    {"id": "opus-1-1", "name": "OPUS 1.1", "window": 20},
    {"id": "opus-1-0", "name": "OPUS 1.0", "window": 30},
    {"id": "opus-1-2", "name": "OPUS 1.2", "window": 50},
    {"id": "opus-1-4", "name": "OPUS 1.4", "window": 75},
    {"id": "opus-1-8", "name": "OPUS 1.8", "window": 100},
    {"id": "opus-1-6", "name": "OPUS 1.6", "window": 150},
    {"id": "opus-2-0", "name": "OPUS 2.0", "window": 200},
    {"id": "opus-2-2", "name": "OPUS 2.2", "window": 500},
]
app = FastAPI(title=APP_NAME, version="1.1.0",
              description="Educational historical analytics. No wagering or automated betting.")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period TEXT NOT NULL,
        outcome TEXT NOT NULL CHECK(outcome IN ('BIG','SMALL')),
        created_at TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'manual',
        event_id TEXT,
        observed_at TEXT,
        payload_hash TEXT
    )""")
    # Forward-only migration for databases created by earlier OPUS builds.
    existing = {row[1] for row in conn.execute("PRAGMA table_info(results)").fetchall()}
    migrations = {
        "source": "ALTER TABLE results ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'",
        "event_id": "ALTER TABLE results ADD COLUMN event_id TEXT",
        "observed_at": "ALTER TABLE results ADD COLUMN observed_at TEXT",
        "payload_hash": "ALTER TABLE results ADD COLUMN payload_hash TEXT",
    }
    for column, statement in migrations.items():
        if column not in existing:
            conn.execute(statement)
    conn.execute("UPDATE results SET observed_at = created_at WHERE observed_at IS NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_results_event_id ON results(event_id) WHERE event_id IS NOT NULL")
    return conn

class ResultIn(BaseModel):
    period: str = Field(min_length=1, max_length=80)
    outcome: str
    source: str = Field(default="manual", min_length=1, max_length=120)
    event_id: str | None = Field(default=None, max_length=160)
    observed_at: datetime | None = None
    payload_hash: str | None = Field(default=None, max_length=128)

def read_outcomes(limit=500):
    conn = db()
    try:
        return conn.execute(
            "SELECT period,outcome,created_at FROM "
            "(SELECT id,period,outcome,created_at FROM results ORDER BY id DESC LIMIT ?) "
            "ORDER BY id ASC", (limit,)
        ).fetchall()
    finally:
        conn.close()

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<meta name="theme-color" content="#080d19"><title>OPUS PRO</title>
<style>
:root{color-scheme:dark;--bg:#080d19;--panel:#111b2c;--line:#25334a;--text:#edf3ff;--muted:#9aaac2;--accent:#67d5ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px Arial,sans-serif;min-height:100vh;padding-bottom:80px}
header{height:64px;display:flex;align-items:center;padding:0 20px;border-bottom:1px solid var(--line);font-size:20px;font-weight:800;letter-spacing:1px}
header span{color:var(--accent);margin-left:5px}.page{max-width:760px;margin:auto;padding:20px 16px 30px}
h1{font-size:23px;margin:5px 0 8px}.muted{color:var(--muted);line-height:1.5}
.status,.panel{margin-top:18px;padding:16px;border:1px solid var(--line);border-radius:14px;background:var(--panel)}
.status strong{color:#f7c66b}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:18px}
.tool{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 14px;text-align:left;color:var(--text);min-height:92px;cursor:pointer}
.tool b{display:block;font-size:17px;margin-bottom:8px}.tool small{color:var(--muted)}
.tool:active{border-color:var(--accent);transform:scale(.99)}
.row{display:flex;gap:8px;flex-wrap:wrap}input,select{background:#080f1d;border:1px solid var(--line);color:var(--text);padding:12px;border-radius:9px;min-width:0}
input{flex:1}button.action{background:var(--accent);border:0;color:#06111c;font-weight:700;padding:12px 16px;border-radius:9px}
.metric{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--line);gap:12px}.metric:last-child{border:0}
.warning{font-size:12px;color:var(--muted);line-height:1.5}
nav{position:fixed;bottom:0;left:0;right:0;height:72px;background:#0d1626;border-top:1px solid var(--line);display:flex;z-index:5}
nav button{width:50%;border:0;background:transparent;color:var(--muted);font-size:14px;font-weight:700}
nav button.active{color:var(--accent)}.hidden{display:none!important}
@media(min-width:600px){.grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
</style></head><body>
<header>OPUS <span>PRO</span></header><main class="page">
<section id="homePage"><h1>Home</h1><p class="muted">OPUS PRO research workspace.</p>
<div class="status">Service status: <strong id="serverStatus">Connecting…</strong>
<p class="muted">Provider connection status is shown below. No sample or fabricated live results are displayed.</p></div>
<div class="panel"><h3>Live provider feed</h3><div class="metric"><span>Connection</span><b id="liveConnection">Checking…</b></div><div class="metric"><span>Active period</span><b id="liveIssue">—</b></div><div class="metric"><span>Provider countdown</span><b id="liveCountdown">—</b></div><div class="metric"><span>Last completed result</span><b id="liveLastResult">—</b></div><div id="liveHistory" class="muted">Waiting for provider connection…</div><p class="warning" id="liveNote">Live feed requires a verified provider HTTPS endpoint and any required credentials to be configured on the server.</p></div>
<div class="panel"><h3>Cycle synchronizer</h3>
<p class="muted">Choose the cycle length. This is a UTC-aligned timer, not a live result feed.</p>
<div class="row"><select id="cycleLength" onchange="syncCycle()"><option value="60">1 minute</option><option value="30">30 seconds</option></select>
<button class="action" onclick="syncCycle()">Sync cycle</button></div>
<div class="metric"><span>Time remaining</span><b id="cycleCountdown">--:--</b></div>
<div class="metric"><span>Cycle ID</span><b id="cycleId">Waiting</b></div>
<p class="warning" id="cycleNote">Timer boundaries do not generate or verify external outcomes.</p></div></section>
<section id="toolsPage" class="hidden"><h1>Tools</h1><p class="muted">Choose an OPUS analysis tool.</p>
<div class="grid" id="toolGrid"></div>
<div class="panel"><h3>Save a historical result</h3>
<p class="muted">Enter a period and its observed BIG or SMALL result. This saves history; it does not fetch live results.</p>
<div class="row"><input id="period" placeholder="Period ID"><select id="outcome"><option>BIG</option><option>SMALL</option></select><button class="action" onclick="saveResult()">Save</button></div><p id="saveMessage" class="muted"></p></div>
<div id="result" class="panel hidden" aria-live="polite"></div>
<div class="panel"><div class="row" style="justify-content:space-between;align-items:center"><h3>Recent history</h3><button class="action" onclick="loadHistory()">Refresh</button></div><div id="historyList" class="muted">Loading history…</div></div></section></main>
<nav><button id="homeTab" class="active" onclick="showPage('home')">Home</button><button id="toolsTab" onclick="showPage('tools')">Tools</button></nav>
<script>
var profiles=[
["opus-1-1","OPUS 1.1",20],["opus-1-0","OPUS 1.0",30],["opus-1-2","OPUS 1.2",50],["opus-1-4","OPUS 1.4",75],
["opus-1-8","OPUS 1.8",100],["opus-1-6","OPUS 1.6",150],["opus-2-0","OPUS 2.0",200],["opus-2-2","OPUS 2.2",500]];
function showPage(page){
 document.getElementById("homePage").classList.toggle("hidden",page!=="home");
 document.getElementById("toolsPage").classList.toggle("hidden",page!=="tools");
 document.getElementById("homeTab").classList.toggle("active",page==="home");
 document.getElementById("toolsTab").classList.toggle("active",page==="tools");
 if(page==="tools")loadHistory();
}
function renderTools(){
 var html="";
 profiles.forEach(function(p){html+='<button class="tool" data-tool="'+p[0]+'"><b>'+p[1]+'</b><small>Last '+p[2]+' results</small></button>';});
 document.getElementById("toolGrid").innerHTML=html;
 document.querySelectorAll(".tool").forEach(function(button){button.addEventListener("click",function(){runTool(button.getAttribute("data-tool"));});});
}
async function runTool(id){
 var box=document.getElementById("result");box.classList.remove("hidden");box.textContent="Loading historical analysis…";
 try{
  var r=await fetch("/api/tools/"+id),d=await r.json();if(!r.ok)throw new Error(d.detail||"Unable to load tool");
  var a=d.analysis,f=a.observed_frequency_pct,w=a.recency_weighted_frequency_pct,t=a.smoothed_transition_pct_after_last;
  var transition=t?("BIG "+t.BIG+"% / SMALL "+t.SMALL+"%"):"Not enough data";
  box.innerHTML="<h3>"+d.name+"</h3><p class='muted'>"+d.window+" result lookback · "+a.sample_size+" records found</p>"+
  "<div class='metric'><span>Observed BIG / SMALL</span><b>"+f.BIG+"% / "+f.SMALL+"%</b></div>"+
  "<div class='metric'><span>Recency weighted BIG / SMALL</span><b>"+w.BIG+"% / "+w.SMALL+"%</b></div>"+
  "<div class='metric'><span>Last observed</span><b>"+(a.last_observed||"—")+"</b></div>"+
  "<div class='metric'><span>Current streak</span><b>"+(a.current_streak.outcome||"—")+" × "+a.current_streak.length+"</b></div>"+
  "<div class='metric'><span>Transition after last</span><b>"+transition+"</b></div>"+
  "<div class='metric'><span>Historical research lean</span><b>"+(a.historical_bias||"Not enough data")+"</b></div>"+
  "<div class='metric'><span>Indicator agreement</span><b>"+(a.model_agreement_score===null?"—":a.model_agreement_score+"%")+"</b></div>"+
  "<div class='metric'><span>Binary entropy</span><b>"+a.binary_entropy+"</b></div>"+
  "<div class='metric'><span>Research status</span><b>"+a.status+"</b></div>"+
  "<p class='warning'>"+a.limitations.join(" ")+"</p><p class='warning'>Historical statistics are not a guaranteed next-result prediction.</p>";
 }catch(e){box.textContent=e.message;}
}
async function loadHistory(){
 var box=document.getElementById("historyList");box.textContent="Loading history…";
 try{
  var r=await fetch("/api/history?limit=20"),d=await r.json();if(!r.ok)throw new Error(d.detail||"Unable to load history");
  box.replaceChildren();
  if(!d.items.length){box.textContent="No historical records saved yet.";return;}
  d.items.forEach(function(item){
   var row=document.createElement("div");row.className="metric";
   var left=document.createElement("span");left.textContent=item.period+" · "+item.source;
   var right=document.createElement("b");right.textContent=item.outcome;
   row.appendChild(left);row.appendChild(right);box.appendChild(row);
  });
 }catch(e){box.textContent=e.message;}
}
async function saveResult(){
 var period=document.getElementById("period").value.trim(),outcome=document.getElementById("outcome").value,msg=document.getElementById("saveMessage");
 if(!period){msg.textContent="Enter a period ID first.";return;}
 try{
  var r=await fetch("/api/history",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({period:period,outcome:outcome})});
  var d=await r.json();if(!r.ok)throw new Error(d.detail||"Save failed");
  msg.textContent="Saved. Open a tool to refresh its analysis.";document.getElementById("period").value="";
  loadHistory();
 }catch(e){msg.textContent=e.message;}
}
var cycleRemaining=0,cycleTick=null,cycleSyncTimer=null;
function paintCycle(){
 var value=Math.max(0,cycleRemaining),mm=String(Math.floor(value/60)).padStart(2,"0"),ss=String(value%60).padStart(2,"0");
 document.getElementById("cycleCountdown").textContent=mm+":"+ss;
}
async function syncCycle(){
 var length=document.getElementById("cycleLength").value;
 try{
  var r=await fetch("/api/cycles/current?cycle_seconds="+length),d=await r.json();
  if(!r.ok)throw new Error(d.detail||"Cycle sync failed");
  cycleRemaining=d.seconds_remaining;
  document.getElementById("cycleId").textContent=d.cycle_id;
  document.getElementById("cycleNote").textContent=d.note;
  paintCycle();
 }catch(e){document.getElementById("cycleNote").textContent=e.message;}
}
async function checkServer(){try{var r=await fetch("/health"),d=await r.json();document.getElementById("serverStatus").textContent=d.ok?"Online":"Unavailable";}catch(e){document.getElementById("serverStatus").textContent="Unavailable";}}
renderTools();checkServer();syncCycle();
cycleTick=setInterval(function(){if(cycleRemaining>0)cycleRemaining--;paintCycle();if(cycleRemaining===0)syncCycle();},1000);
cycleSyncTimer=setInterval(syncCycle,10000);
</script></body></html>"""

@app.get("/api/cycles/current")
def current_cycle(cycle_seconds: int = 60):
    """Return a 30s or 60s UTC-aligned timer window; not a result feed."""
    if cycle_seconds not in (30, 60):
        raise HTTPException(422, "cycle_seconds must be 30 or 60")
    epoch = int(time.time())
    start = epoch - (epoch % cycle_seconds)
    return {
        "cycle_seconds": cycle_seconds,
        "cycle_id": f"{cycle_seconds}-{start}",
        "cycle_started_at": datetime.fromtimestamp(start, timezone.utc).isoformat(),
        "seconds_remaining": cycle_seconds - (epoch % cycle_seconds),
        "note": "Timer boundary only; it does not verify or generate an external result."
    }

@app.get("/health")
def health():
    return {"ok": True, "service": APP_NAME, "time": datetime.now(timezone.utc).isoformat()}

@app.get("/api/status")
def status():
    return {"server": "online", "provider": "not_configured", "live_data": False,
            "message": "No verified provider API is connected. Only user-entered historical results are analyzed."}

def _persist_provider_history(records: list[dict], cycle_type: str) -> int:
    """Store only provider rows with an explicit BIG/SMALL value; ignore repeats."""
    conn = db()
    inserted = 0
    try:
        for row in records:
            if row.get("outcome") not in ("BIG", "SMALL"):
                continue
            period = str(row["period"])
            event_id = f"wingo-{cycle_type}-{period}"
            observed_at = row.get("observed_at")
            if not isinstance(observed_at, str) or not observed_at:
                observed_at = datetime.now(timezone.utc).isoformat()
            try:
                conn.execute(
                    """INSERT INTO results(period,outcome,created_at,source,event_id,observed_at,payload_hash)
                       VALUES(?,?,?,?,?,?,?)""",
                    (period, row["outcome"], datetime.now(timezone.utc).isoformat(),
                     f"provider:wingo:{cycle_type}", event_id, observed_at, row.get("payload_hash"))
                )
                inserted += 1
            except sqlite3.IntegrityError:
                # Same provider event already stored; do not create duplicates.
                continue
        conn.commit()
    finally:
        conn.close()
    return inserted


@app.get("/api/live/status")
def live_status():
    configured = bool(os.getenv("PROVIDER_API_URL", "").strip())
    return {
        "configured": configured,
        "status": "configured_not_yet_verified" if configured else "not_configured",
        "provider_host": (os.getenv("PROVIDER_API_URL", "").strip().split("://")[-1].split("/")[0]
                          if configured else None),
        "message": ("Provider URL is configured; test a live fetch to verify access."
                    if configured else "Set PROVIDER_API_URL after confirming the provider's official endpoint and access rights.")
    }


@app.get("/api/live/snapshot")
async def live_snapshot(cycle_seconds: int = 60, limit: int = 50):
    if cycle_seconds not in (30, 60):
        raise HTTPException(422, "cycle_seconds must be 30 or 60")
    try:
        snapshot = await fetch_live_snapshot(cycle_seconds, limit)
    except ProviderNotConfigured as exc:
        return {"connected": False, "status": "not_configured", "message": str(exc),
                "cycle_seconds": cycle_seconds, "history": []}
    except ProviderError as exc:
        return {"connected": False, "status": "provider_error", "message": str(exc),
                "cycle_seconds": cycle_seconds, "history": []}
    inserted = _persist_provider_history(snapshot["history"], snapshot["cycle_type"])
    snapshot["connected"] = True
    snapshot["status"] = "connected"
    snapshot["new_records_saved"] = inserted
    return snapshot


@app.get("/api/tools")
def list_tools():
    return {"tools": TOOL_PROFILES, "mode": "historical_research_only"}

@app.get("/api/tools/{tool_id}")
def run_tool(tool_id: str):
    profile = next((item for item in TOOL_PROFILES if item["id"] == tool_id), None)
    if profile is None:
        raise HTTPException(404, "Unknown OPUS tool")
    rows = read_outcomes(profile["window"])
    result = analyze_history([row[1] for row in rows], min_samples=20)
    return {"id": profile["id"], "name": profile["name"], "window": profile["window"], "analysis": result}

@app.post("/api/history")
def add_result(item: ResultIn, ingest_token: str | None = Header(default=None, alias="X-OPUS-INGEST-TOKEN")):
    outcome = item.outcome.strip().upper()
    if outcome not in ("BIG", "SMALL"):
        raise HTTPException(400, "outcome must be BIG or SMALL")
    # Configure OPUS_INGEST_TOKEN on the server before exposing write access.
    # The token is never shipped to the browser or Android client.
    expected_token = os.getenv("OPUS_INGEST_TOKEN")
    if expected_token and not hmac.compare_digest(ingest_token or "", expected_token):
        raise HTTPException(401, "A valid X-OPUS-INGEST-TOKEN is required.")
    created_at = datetime.now(timezone.utc).isoformat()
    observed_at = item.observed_at.astimezone(timezone.utc).isoformat() if item.observed_at else created_at
    conn = db()
    try:
        if item.event_id:
            existing = conn.execute(
                "SELECT id,period,outcome FROM results WHERE event_id=?", (item.event_id,)
            ).fetchone()
            if existing:
                return {"saved": False, "duplicate": True, "id": existing[0],
                        "period": existing[1], "outcome": existing[2]}
        try:
            cursor = conn.execute(
                """INSERT INTO results(period,outcome,created_at,source,event_id,observed_at,payload_hash)
                   VALUES(?,?,?,?,?,?,?)""",
                (item.period.strip(), outcome, created_at, item.source.strip(),
                 item.event_id, observed_at, item.payload_hash)
            )
            conn.commit()
            record_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            conn.rollback()
            if item.event_id:
                existing = conn.execute(
                    "SELECT id,period,outcome FROM results WHERE event_id=?", (item.event_id,)
                ).fetchone()
                if existing:
                    return {"saved": False, "duplicate": True, "id": existing[0],
                            "period": existing[1], "outcome": existing[2]}
            raise HTTPException(409, "The historical result conflicts with an existing record.")
    finally:
        conn.close()
    return {"saved": True, "id": record_id, "period": item.period.strip(),
            "outcome": outcome, "source": item.source.strip(),
            "event_id": item.event_id, "observed_at": observed_at}

@app.get("/api/history")
def history(limit: int = 100):
    conn = db()
    try:
        rows = conn.execute(
            """SELECT period,outcome,created_at,source,event_id,observed_at,payload_hash
               FROM (SELECT id,period,outcome,created_at,source,event_id,observed_at,payload_hash
                     FROM results ORDER BY id DESC LIMIT ?)
               ORDER BY id ASC""",
            (max(1, min(limit, 500)),)
        ).fetchall()
    finally:
        conn.close()
    return {"items": [
        {"period":r[0], "outcome":r[1], "created_at":r[2], "source":r[3],
         "event_id":r[4], "observed_at":r[5], "payload_hash":r[6]}
        for r in reversed(rows)
    ]}

@app.get("/api/analysis")
def analysis():
    values = [row[1] for row in read_outcomes(100)]
    big, small, total = values.count("BIG"), values.count("SMALL"), len(values)
    return {"sample_size": total, "big": big, "small": small,
            "big_pct": round(big*100/total, 2) if total else None,
            "small_pct": round(small*100/total, 2) if total else None,
            "signal": "insufficient_data" if total < 20 else "historical_frequency_only",
            "note": "Historical frequencies do not predict the next outcome or guarantee accuracy."}
