# OPUS PRO backend

This repository deploys a FastAPI HTTPS service on Render.

## Endpoints
- GET /health
- GET /api/status
- GET /api/history
- POST /api/history with JSON {"period":"...","outcome":"BIG"}
- GET /api/analysis
- GET /docs

## Live provider integration
No verified provider API endpoint or credentials are currently available. The server therefore reports provider=not_configured and does not fabricate live results or predictions. Configure PROVIDER_API_URL and provider credentials only after the provider supplies official API documentation and access keys.

The free Render plan may sleep when idle. SQLite on the free ephemeral filesystem is not durable across instance replacement; configure a persistent database before relying on long-term history.
