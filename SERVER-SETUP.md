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
The app now includes a configurable live WinGo adapter. It reads PROVIDER_API_URL, optional PROVIDER_ORIGIN and PROVIDER_API_TOKEN, plus optional PROVIDER_ISSUE_PATH and PROVIDER_HISTORY_PATH. Default paths are /games/wingo/issue and /games/wingo/history with type=30s or 1m. The adapter uses HTTPS only, does not follow redirects, validates the active issue number, and only converts explicit BIG/SMALL fields; it does not infer a size from a numeric draw. Up to 500 history rows can be requested for the OPUS 2.2 lookback. GET /api/live/status reports configuration and GET /api/live/snapshot?cycle_seconds=30|60 fetches the upstream issue and history. All raw provider rows are retained and de-duplicated in provider_observations; only rows with explicit BIG/SMALL outcomes enter the analytical results table. GET /api/live/history?cycle_seconds=30|60 returns the retained raw observations. All POST /api/history writes fail closed with HTTP 503 until OPUS_INGEST_TOKEN is configured on Render; afterward every write requires X-OPUS-INGEST-TOKEN. The dashboard does not expose this token or allow public manual writes. Do not configure a provider URL or credentials until the provider's official API documentation and access rights are verified. The current account has not supplied a verified provider endpoint or key, so live connection will remain not_configured until those server-side settings are provided.

### Provider environment settings (Render service only)
- `PROVIDER_API_URL`: HTTPS API base host (not the BDG browser page URL).
- `PROVIDER_ISSUE_PATH`, `PROVIDER_HISTORY_PATH`: documented read-only issue and history routes.
- `PROVIDER_API_TOKEN`: optional server-side token; never expose it to the app.
- `PROVIDER_AUTH_HEADER`, `PROVIDER_AUTH_SCHEME`: optional authentication header settings.
- `PROVIDER_ORIGIN`: optional provider-required Origin header.
- `PROVIDER_CYCLE_PARAM`: defaults to `type`; `PROVIDER_GAME_CODE_PARAM` can be used for gameCode-style APIs.
- `PROVIDER_GAME_CODE_30S`, `PROVIDER_GAME_CODE_60S`, `PROVIDER_LOTTERY_PARAM`, `PROVIDER_LOTTERY_VALUE`: optional provider-specific query mapping.
- `OPUS_INGEST_TOKEN`: required private token for POST /api/history; never put it in the dashboard or Android app.
- `PROVIDER_HISTORY_LIMIT_PARAM`: defaults to `size`; the connector accepts up to 500 rows to cover OPUS 2.2's lookback. Set `PROVIDER_HISTORY_ORDER` to `oldest_first` or `newest_first` only after confirming the provider's documented response ordering. Its default is `unknown`: raw rows are archived, but they are not inserted into chronological BIG/SMALL analysis until the order is verified.

Only use read-only public result endpoints. Do not configure login, wallet, deposit, withdrawal, bet-placement, or account-control endpoints.

The free Render plan may sleep when idle. SQLite on the free ephemeral filesystem is not durable across instance replacement; configure a persistent database before relying on long-term history.
