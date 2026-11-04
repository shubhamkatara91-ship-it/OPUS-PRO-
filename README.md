# OPUS PRO

Independent historical-analytics application. The project does not reuse Mark Pro or BDG private code, credentials, undocumented endpoints, or hidden server logic.

## Current application
- Home and Tools dashboard
- Eight OPUS profiles: 1.1, 1.0, 1.2, 1.4, 1.8, 1.6, 2.0, 2.2
- Profile-specific historical lookback windows: 20, 30, 50, 75, 100, 150, 200, and 500 records
- Original statistical engine: observed frequency, recency-weighted frequency, transition counts with Laplace smoothing, streaks, entropy, and a walk-forward majority baseline
- Historical result ingestion with source, event ID, observed timestamp, and payload-hash provenance
- Optional server-side ingestion token (`OPUS_INGEST_TOKEN` / `X-OPUS-INGEST-TOKEN`) and duplicate event protection
- Result entry and history endpoints
- Selectable 30-second and 60-second UTC-aligned cycle timer endpoint

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000 and API docs at http://127.0.0.1:8000/docs.

## API
- `GET /health`
- `GET /api/status`
- `GET /api/tools`
- `GET /api/tools/{tool_id}`
- `GET /api/cycles/current?cycle_seconds=30` or `60`
- `POST /api/history`
- `GET /api/history`
- `GET /api/analysis`

## Data and limitations
- No verified external result provider is connected; historical records are entered by the operator.
- The cycle endpoint is a timer boundary only. It does not mean a result has arrived.
- Historical frequencies, transitions, agreement scores, and retrospective backtests are not calibrated probabilities and do not guarantee future accuracy.
- The current SQLite database path defaults to `/tmp/opus_history.sqlite3`. On ephemeral hosting, data can be lost on restart/redeploy. Production persistence and authenticated ingestion must be configured before relying on stored history.
- Before public deployment, configure `OPUS_INGEST_TOKEN` for server-side write protection; do not embed this token in the browser or Android app. Add end-user authentication, rate limits, and source validation before production ingestion.
- Android APK packaging and device testing remain separate tasks; a successful backend deploy is not an APK.

## Next engineering steps
1. Add authenticated, idempotent ingestion and durable database storage.
2. Add source metadata, event IDs, timestamps, and payload hashes for every observation.
3. Keep CI checks green; expand walk-forward tests and calibration metrics using verified, chronological data.
4. Finish dashboard UX and integrate the cycle timer.
5. Build and test the Android client after the API contract stabilizes.
