# OPUS PRO

Independent analytics application. This repository starts as a clean codebase; it does not reuse Mark Pro or BDG private code, servers, credentials, or undocumented endpoints.

## Product scope
- Home dashboard and Tools workspace
- Eight separately configured tool modules (names/logic must be confirmed from authorized product requirements; no hidden algorithms are assumed)
- 60-second and 30-second cycle scheduling
- Independent historical-data analytics with source, sample size, timestamp, and uncertainty shown
- Backend API with health and analytics endpoints
- Android client planned after API contract and UI are stable

## Current implementation status
- Initial repository scaffold
- Backend API scaffold
- Cycle timing is a scheduling boundary only; it does not imply a new result is available
- No live results provider is connected
- No prediction accuracy or guaranteed outcome is claimed

## Backend quick start
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Data integrity
Only ingest historical records from a source the project owner is authorized to use. Store provider, event ID, observed time, received time, and raw payload hash. Reject duplicate event IDs. Never label synthetic/demo data as live.

## Roadmap
1. Confirm the eight module names and their permitted data sources.
2. Implement persistence and authenticated ingestion.
3. Add evaluation/backtesting with time-ordered splits and leakage checks.
4. Build dashboard and Android app.
5. Test on real devices and deploy backend after secrets and hosting configuration are supplied.
