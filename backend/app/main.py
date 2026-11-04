"""OPUS PRO API entry point."""
import os
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from .analytics import analyze_labels
from .modules import list_modules

app = FastAPI(
    title="OPUS PRO API",
    version="0.1.0",
    description="Independent analytics backend; no third-party private endpoints are assumed.",
)


class AnalyzeRequest(BaseModel):
    labels: list[str] = Field(default_factory=list, max_length=10000)
    source: str = Field(default="user_supplied", min_length=1, max_length=120)
    observed_at: datetime | None = None

    @field_validator("labels")
    @classmethod
    def normalize_labels(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().upper() for value in values]
        if any(value not in {"BIG", "SMALL"} for value in normalized):
            raise ValueError("Each label must be BIG or SMALL.")
        return normalized


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "opus-pro-api"}


@app.get("/api/v1/modules")
def modules() -> dict[str, object]:
    return {"count": 8, "modules": list_modules()}


@app.get("/api/v1/cycles/current")
def current_cycle(cycle_seconds: int = 60) -> dict[str, object]:
    now = time.time()
    seconds = cycle_seconds
    if seconds not in (30, 60):
        raise HTTPException(status_code=422, detail="cycle_seconds must be 30 or 60.")
    epoch = int(now)
    cycle_start = epoch - (epoch % seconds)
    remaining = seconds - (epoch % seconds)
    return {
        "cycle_seconds": seconds,
        "cycle_id": f"{seconds}-{cycle_start}",
        "cycle_started_at": datetime.fromtimestamp(cycle_start, timezone.utc).isoformat(),
        "seconds_remaining": remaining,
        "note": "Cycle boundary is a timer only; it does not confirm that a new external result exists.",
    }


@app.post("/api/v1/analytics/summary")
def analytics_summary(request: AnalyzeRequest) -> dict[str, object]:
    try:
        summary = analyze_labels(request.labels)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "source": request.source,
        "observed_at": request.observed_at.isoformat() if request.observed_at else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis": summary,
    }
