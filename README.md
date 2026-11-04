# OPUS PRO

Independent historical-analytics application. The project does not reuse Mark Pro or BDG private code, credentials, undocumented endpoints, or hidden server logic.

## Current application
- Home and Tools dashboard
- Eight OPUS profiles: 1.1, 1.0, 1.2, 1.4, 1.8, 1.6, 2.0, 2.2
- Profile-specific historical lookback windows: 20, 30, 50, 75, 100, 150, 200, and 500 records
- Original statistical engine: observed frequency, recency-weighted frequency, transition counts with Laplace smoothing, streaks, entropy, and per-tool expanding-window walk-forward baseline results
- Historical result ingestion with source, event ID, observed timestamp, and payload-hash provenance
- Separate de-duplicated archive of raw provider observations, including numeric draws that are not yet mapped to BIG/SMALL
- Chronological ingestion gate: raw records are retained immediately, but BIG/SMALL analysis ingestion stays paused until the provider's oldest-first/newest-first response order is verified
- Required server-side ingestion token (`OPUS_INGEST_TOKEN` / `X-OPUS-INGEST-TOKEN`) for all public history writes; disabled by default until configured
- Read-only result history endpoints; authenticated server-side ingestion endpoint
- Selectable 30-second and 60-second UTC-aligned cycle timer endpoint
- Configurable HTTPS live-provider adapter with issue/history polling (up to 500 records for OPUS 2.2), provider-specific query/auth mapping, source-tagged persistence, and duplicate event protection
- Live provider status and recent-result panel in the Home dashboard

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
- `GET /api/live/status`
- `GET /api/live/snapshot?cycle_seconds=30` or `60` (optional `limit=1..500`)
- `GET /api/live/history?cycle_seconds=30` or `60` (optional `limit=1..500`)

## Data and limitations
- The live adapter is implemented but no verified BDG API base URL, documented read-only routes, or credentials are configured yet. The BDG game URL is a browser route, not an API endpoint.
- The cycle endpoint is a timer boundary only. It does not mean a result has arrived.
- Historical frequencies, transitions, agreement scores, and retrospective backtests are not calibrated probabilities and do not guarantee future accuracy.
- The current SQLite database path defaults to `/tmp/opus_history.sqlite3`. On ephemeral hosting, data can be lost on restart/redeploy. Production persistence and authenticated ingestion must be configured before relying on stored history.
- `POST /api/history` fails closed with HTTP 503 until `OPUS_INGEST_TOKEN` is set, then requires `X-OPUS-INGEST-TOKEN`; the token is never embedded in the browser or Android app. End-user authentication and rate limits remain future production hardening.
- Android APK packaging and device testing remain separate tasks; a successful backend deploy is not an APK.

## Next engineering steps
1. Verify the BDG provider's official read-only API host, issue/history routes, response schema, and access permission.
2. Configure provider settings on the Render server only; never embed credentials in Android or browser code.
3. Keep CI checks green; expand walk-forward tests and calibration metrics using verified, chronological data.
4. Add durable database storage and production authentication before public use.
5. Test live ingestion and the Android client against real provider responses.
