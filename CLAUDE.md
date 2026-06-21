# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A demo centralized log management / SIEM system: multi-source log ingestion, normalization into one schema, fake GeoIP enrichment, an inline alert/rule engine, and a React dashboard with basic multi-tenant RBAC. Backend is FastAPI + SQLAlchemy + PostgreSQL; frontend is Vite + React + Recharts; everything is wired together with Docker Compose and an Nginx TLS-terminating proxy.

## Commands

Backend (run from `backend/`):
```bash
pip install -r requirements.txt
uvicorn main:app --reload          # dev server on :8000, http://127.0.0.1:8000/docs for Swagger
pytest test_syslog.py              # run all tests
pytest test_syslog.py::test_normalize_syslog_success   # run a single test
```
`database.py` defaults to `postgresql://loguser:password@localhost:5432/logmanagement` if `DATABASE_URL` is unset; Docker Compose overrides it to point at the `db` service.

Frontend (run from `frontend/`):
```bash
npm install
npm run dev       # Vite dev server
npm run build
npm run lint
```

Full stack via Docker:
```bash
mkdir -p certs
docker run --rm -v ${PWD}/certs:/certs alpine/openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 -keyout /certs/server.key -out /certs/server.crt \
  -subj "/C=TH/ST=Bangkok/L=Bangkok/O=Demo/CN=localhost"
docker compose up -d --build
```
A self-signed cert in `./certs/` is required before `frontend` will start — Nginx mounts it and fails without it. Dashboard at `https://localhost:3443` (and `http://localhost:3000`, which just redirects to HTTPS), API at `http://localhost:8000`.

CI (`.github/workflows/ci-cd.yml`) only runs `pytest test_syslog.py` on push/PR to `main`/`master` — it does not exercise `main.py` or the API.

## Architecture

**Services** (`docker-compose.yml`): `db` (Postgres 15), `backend` (FastAPI on 8000, plus UDP 5140 exposed for syslog), `frontend` (Nginx serving the built React app, terminating TLS using `nginx-custom.conf` + `./certs`).

**Backend is a single-file app** (`backend/main.py`) — all endpoints, normalization, enrichment, and rule-engine logic live there. `models.Base.metadata.create_all()` runs on startup; there are no migrations.

**Schema**: `models.py` defines one wide `LogEntry` table with columns for every field any source might produce (network, user, cloud, etc.) plus a `raw` JSONB column for source-specific extras, and a separate `Alert` table (`log_id` is a plain int, not an FK). Multi-tenancy is logical only — a `tenant` string column shared in one table, not separate schemas/DBs.

**Ingestion flow** (`POST /api/ingest`): `normalize_log(source, raw_data)` dispatches on `source` (`m365` / `syslog` / `api`+`crowdstrike`+`aws`) into the common `LogEntry` shape, each branch defaulting different fields. `enrich_geoip()` is a fake lookup that buckets `src_ip` into a country string by prefix-matching, stored at `raw["enriched_country"]`. Immediately after insert, the same request handler runs both alert rules synchronously against the DB (no queue/async worker):
- brute force: ≥5 `app_login_failed`/`LogonFailed` events from the same `src_ip` in 5 minutes
- flooding: ≥10 events from the same `source` or `event_type` in 1 minute

A triggered rule inserts an `Alert` row and calls `webhook_alert()`, which POSTs to a webhook.site URL hardcoded in `main.py`.

**Syslog path is a separate process**: `backend/syslog.py` is a standalone UDP server (port 5140) that regex-parses syslog lines and forwards them as JSON to `POST /api/ingest` over HTTP. It is **not** started by the backend Dockerfile (whose `CMD` only runs `uvicorn main:app`) — run it manually as a second process to test syslog ingestion. `send_syslog.py` is a one-shot script that fires a single sample UDP packet at it.

**File upload** (`POST /api/ingest/file_sample`): accepts a multipart file upload (matching the admin "File Batch Upload" UI), parses it as a JSON array, and ingests any `m365`-sourced entries via the same `normalize_log` path. `backend/sample_logs.json` is sample data for that upload, not read directly by the server.

**Auth/RBAC is a stub, not real auth**: `POST /api/login` checks a hardcoded `users_db` dict (`admin`/`viewer`, both `password123`) and returns a fake token string. There is no token verification on other endpoints — `GET /api/logs` enforces tenant scoping purely from the `tenant`/`user_role` query params the frontend happens to send (`user_role == "viewer"` forces `tenant = "demo"`); nothing stops a client from omitting or forging these.

**Frontend is one component** (`frontend/src/App.jsx`): login form, then a dashboard that fetches `/api/logs` and `/api/alerts` on login/tenant change, does all date-range and text-search filtering client-side over the already-fetched logs, and renders two Recharts views (top event types bar chart, per-day timeline line chart) plus a log table. No router, no state management library — just `useState`/`useEffect`.

## Reference docs

`docs/architecture.md` has a Mermaid diagram and sequence diagram of the ingest → enrich → alert → display flow plus more detail on the tenant/RBAC model. `docs/setup_appliance.md` and `docs/setup_saas.md` cover on-prem vs. cloud deployment specifics (firewall ports, Let's Encrypt instead of self-signed certs, env-based secrets for SaaS).
