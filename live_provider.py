"""Configurable live-results adapter for an explicitly authorized WinGo provider.

No provider host, credentials, or prediction endpoint is hard-coded. Configure
PROVIDER_API_URL only after verifying the provider's documentation and access rights.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

import httpx

DEFAULT_ISSUE_PATH = "/games/wingo/issue"
DEFAULT_HISTORY_PATH = "/games/wingo/history"
MAX_HISTORY_LIMIT = 500


class ProviderNotConfigured(RuntimeError):
    pass


class ProviderError(RuntimeError):
    pass


def _history_limit(limit: int) -> int:
    """Clamp provider history requests to the maximum supported OPUS window."""
    return min(max(int(limit), 1), MAX_HISTORY_LIMIT)


def _cycle_type(seconds: int) -> str:
    if seconds == 30:
        return "30s"
    if seconds == 60:
        return "1m"
    raise ValueError("Only 30-second and 1-minute cycles are supported")


def _first_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    return {}


def _unwrap(payload: Any) -> dict:
    """Unwrap common API response envelopes without assuming success."""
    data = _first_dict(payload)
    for key in ("data", "result", "payload"):
        nested = data.get(key)
        if isinstance(nested, dict):
            data = nested
    return data


def _find_list(payload: Any) -> list:
    candidates = [payload]
    root = _first_dict(payload)
    for key in ("data", "result", "payload"):
        if key in root:
            candidates.append(root[key])
    for candidate in list(candidates):
        obj = _first_dict(candidate)
        for key in ("results", "list", "records", "history", "items"):
            if isinstance(obj.get(key), list):
                return obj[key]
        if isinstance(candidate, list):
            return candidate
    return []


def _size_outcome(row: dict) -> str | None:
    for key in ("size", "outcome", "big_small", "bigSmall", "result_size"):
        value = row.get(key)
        if isinstance(value, str) and value.strip().upper() in ("BIG", "SMALL"):
            return value.strip().upper()
    # Do not infer BIG/SMALL from a numeric result until the provider's rules
    # are verified; numeric values remain available in raw_result.
    return None


def normalize_history(payload: Any) -> list[dict]:
    normalized = []
    for row in _find_list(payload):
        if not isinstance(row, dict):
            continue
        period = next((row.get(k) for k in
                       ("issue_number", "period", "issue", "period_id", "issueNumber")
                       if row.get(k) is not None), None)
        if period is None:
            continue
        outcome = _size_outcome(row)
        raw = json.dumps(row, sort_keys=True, separators=(",", ":"), default=str)
        normalized.append({
            "period": str(period),
            "outcome": outcome,
            "observed_at": next((row.get(k) for k in
                                 ("observed_at", "draw_time", "open_time", "created_at", "time")
                                 if row.get(k) is not None), None),
            "raw_result": row.get("number", row.get("result")),
            "raw": raw,
            "payload_hash": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        })
    return normalized


async def fetch_live_snapshot(cycle_seconds: int, history_limit: int = 50) -> dict:
    base_url = os.getenv("PROVIDER_API_URL", "").strip().rstrip("/")
    if not base_url:
        raise ProviderNotConfigured("PROVIDER_API_URL is not configured")
    if not base_url.startswith("https://"):
        raise ProviderError("Provider URL must use HTTPS")

    cycle_type = _cycle_type(cycle_seconds)
    issue_path = os.getenv("PROVIDER_ISSUE_PATH", DEFAULT_ISSUE_PATH)
    history_path = os.getenv("PROVIDER_HISTORY_PATH", DEFAULT_HISTORY_PATH)
    headers = {"Accept": "application/json", "User-Agent": "OPUS-PRO-LiveConnector/1.0"}
    origin = os.getenv("PROVIDER_ORIGIN", "").strip()
    if origin:
        headers["Origin"] = origin
    api_token = os.getenv("PROVIDER_API_TOKEN", "").strip()
    if api_token:
        auth_header = os.getenv("PROVIDER_AUTH_HEADER", "Authorization").strip()
        auth_scheme = os.getenv("PROVIDER_AUTH_SCHEME", "Bearer").strip()
        headers[auth_header] = f"{auth_scheme} {api_token}".strip()

    cycle_param = os.getenv("PROVIDER_CYCLE_PARAM", "type").strip()
    issue_params = {cycle_param: cycle_type}
    history_params = {cycle_param: cycle_type}
    game_code_param = os.getenv("PROVIDER_GAME_CODE_PARAM", "").strip()
    if game_code_param:
        game_code = os.getenv(
            "PROVIDER_GAME_CODE_30S" if cycle_seconds == 30 else "PROVIDER_GAME_CODE_60S", ""
        ).strip()
        if game_code:
            issue_params[game_code_param] = game_code
            history_params[game_code_param] = game_code
    lottery_param = os.getenv("PROVIDER_LOTTERY_PARAM", "").strip()
    lottery_value = os.getenv("PROVIDER_LOTTERY_VALUE", "").strip()
    if lottery_param and lottery_value:
        issue_params[lottery_param] = lottery_value
        history_params[lottery_param] = lottery_value
    limit_param = os.getenv("PROVIDER_HISTORY_LIMIT_PARAM", "size").strip()
    history_params[limit_param] = _history_limit(history_limit)

    timeout = httpx.Timeout(8.0, connect=4.0)
    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=timeout,
                                 follow_redirects=False) as client:
        try:
            import asyncio
            issue_response, history_response = await asyncio.gather(
                client.get(issue_path, params=issue_params),
                client.get(history_path, params=history_params),
            )
            issue_response.raise_for_status()
            history_response.raise_for_status()
            issue_payload = issue_response.json()
            history_payload = history_response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Provider request failed: {type(exc).__name__}") from exc

    issue = _unwrap(issue_payload)
    records = normalize_history(history_payload)
    issue_number = next((issue.get(k) for k in
                         ("issue_number", "period", "issue", "period_id", "issueNumber")
                         if issue.get(k) is not None), None)
    countdown = next((issue.get(k) for k in
                      ("countdown_seconds", "remaining_seconds", "countdown")
                      if issue.get(k) is not None), None)
    server_time = next((issue.get(k) for k in
                        ("server_time", "timestamp", "now")
                        if issue.get(k) is not None), None)
    if issue_number is None:
        raise ProviderError("Provider issue response did not contain a recognized issue number")

    return {
        "provider_configured": True,
        "provider_host": base_url.split("://", 1)[-1].split("/", 1)[0],
        "cycle_seconds": cycle_seconds,
        "cycle_type": cycle_type,
        "active_issue": str(issue_number),
        "countdown_seconds": countdown,
        "provider_server_time": server_time,
        "history_count": len(records),
        "history": records,
        "last_completed": records[0] if records else None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source_note": "Upstream response; results without an explicit BIG/SMALL field are not converted."
    }
