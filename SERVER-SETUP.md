# OPUS PRO backend

This repository deploys a FastAPI HTTPS service on Render.

## Endpoints
- GET /health
- GET /api/status
- GET /api/history
- POST /api/history with period, outcome, source, optional event_id, observed_at, and payload_hash
- GET /api/cycles/current?cycle_seconds=30 or 60
- GET /api/tools and GET /api/tools/{tool_id}
- GET /api/analysis
- GET /docs

## Live provider integration
The app records source provenance and rejects duplicate provider event IDs. Set OPUS_INGEST_TOKEN on the server to require X-OPUS-INGEST-TOKEN for write requests; never put this token in the Android app or browser. No verified provider API endpoint or credentials are currently available. The server therefore reports provider=not_configured and does not fabricate live results or predictions. Configure PROVIDER_API_URL and provider credentials only after the provider supplies official API documentation and access keys.

The free Render plan may sleep when idle. SQLite on the free ephemeral filesystem is not durable across instance replacement; configure a persistent database before relying on long-term history.
