# External Integrations

**Analysis Date:** 2026-08-10

## APIs & External Services

**Market data & news:**
- Massive API (`https://api.massive.com`) - daily price aggregates and ticker news
  - SDK/Client: hand-rolled `MassiveClient` (`app/massive_client.py`, `mcp_server/massive_client.py`, both 115 lines, near-identical duplicates) wrapping `requests.Session`
  - Auth: Bearer token, fetched from Databricks secret scope `massive`/`api-key`, base64-decoded in `_get_api_key()`
  - Endpoints used: `GET /v2/aggs/ticker/{symbol}/prev` (`get_latest_price`), `GET /v2/reference/news` (`get_news`)
  - Rate limit: free tier is 5 requests/minute, end-of-day data only — pipeline throttles ingest via a `max_requests_per_minute` widget (per README)
  - Generic `paginated_get()` helper exists for cursor-based pagination but the two concrete methods above each make a single call to conserve quota

**Trading (referenced, not in this repo):**
- Alpaca paper trading - README references "Day 3's Alpaca server" as a second MCP tool an agent can use for trades; not implemented in this codebase

## Data Storage

**Databases:**
- Lakebase (Databricks-managed Postgres) - primary serving store
  - Connection: single `LAKEBASE_URL` Postgres connection string, resolved from Databricks secret scope `database`/`lakebase-url` (`app/lakebase.py`, `mcp_server/lakebase.py`, both 74 lines, near-identical duplicates)
  - Client: raw `psycopg2` (with `RealDictCursor`) for queries via `run_query`/`run_write`/`run_returning`; `sqlalchemy.create_engine()` also exposed via `get_engine()`
  - Extension: pgvector, with an HNSW index for similarity search (`sql/01_schema.sql`)
  - Tables: `watchlist`, `ticker_news_documents`, `ticker_news_chunk_embeddings`, `price_bars`, `ticker_metrics`, `news_price_signals`, `research_notes`, `analysis_reports`, `user_visits`

- Delta Lake / Unity Catalog - analytics store written by the Spark pipeline (`main.market_research.*`), partitioned by ticker; queried directly in notebooks (README demo step 6)

**File Storage:**
- Not detected — no object storage (S3/ADLS/GCS) client code found; Delta tables serve as the durable analytics layer

**Caching:**
- None detected

## Authentication & Identity

**Auth Provider:**
- Databricks-native — `databricks.sdk.WorkspaceClient()` used implicitly for identity/auth to Databricks workspace resources (secrets API); no separate user-facing auth/identity provider (e.g., OAuth, Supabase Auth) found in `app/app.py`
- End-user identity for app records (e.g., `watchlist.email`, `user_visits`) appears to be a plain string field, not backed by an auth system — verify in `app/app.py` if user-facing login is added later

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry/error-tracking SDK in either `requirements.txt`)

**Logs:**
- Not detected beyond standard Databricks App platform logging; no structured logging library found in dependencies

## CI/CD & Deployment

**Hosting:**
- Databricks Apps (PaaS) - two independent app deployments:
  - `market-copilot-app` from `app/` (Flask UI + API, healthcheck at `/healthz`)
  - `market-copilot-mcp` from `mcp_server/` (FastMCP server, streamable HTTP at `/mcp`)
- Deployment commands: `databricks sync app|mcp_server ...` then `databricks apps deploy ...` (manual, per README runbook) — no CI pipeline file detected

**CI Pipeline:**
- None detected — no `.github/workflows`, no CI config files in the repo

## Environment Configuration

**Required env vars (non-secret, set in each `app.yaml`):**
- `LAKEBASE_SECRET_SCOPE` (default `database`)
- `LAKEBASE_SECRET_KEY` (default `lakebase-url`)
- `MASSIVE_SECRET_SCOPE` (default `massive`)
- `MASSIVE_SECRET_KEY` (default `api-key`)
- `MASSIVE_API_BASE_URL` (default `https://api.massive.com`, app only)
- `EMBEDDING_MODEL` (default `sentence-transformers/all-MiniLM-L6-v2`)

**Secrets location:**
- Databricks secret scopes, never in env vars, `.env`, or `app.yaml`: scope `database` key `lakebase-url` (Lakebase Postgres URL), scope `massive` key `api-key` (Massive API key)
- Provisioned one-time via `setup_secrets.py`, which also sets READ ACLs for the `users` principal on both scopes
- `.env.example` documents the same variable names for local dev only ("Local dev only. Never commit real values."); actual `.env` is gitignored

## Webhooks & Callbacks

**Incoming:**
- MCP protocol endpoint `/mcp` on the `mcp_server` app — Agent Bricks (Databricks' agent platform) connects here as an "external MCP tool" per README; this is the closest analog to an incoming integration surface, exposing 10 tools (6 read: e.g., ticker lookups, semantic search, signals; 4 write: `add_to_watchlist`, `remove_from_watchlist`, `save_research_note`, `save_analysis_report`) — see `mcp_server/research_mcp_server.py`

**Outgoing:**
- None detected (no outbound webhook dispatch found)

---

*Integration audit: 2026-08-10*
