# Technology Stack

**Analysis Date:** 2026-08-10

## Languages

**Primary:**
- Python 3 - Entire codebase: Spark pipeline (`pipeline/market_pipeline_serverless.py`), Flask app (`app/app.py`), MCP server (`mcp_server/research_mcp_server.py`)

**Secondary:**
- SQL - Schema DDL (`sql/01_schema.sql`), embedded query strings throughout `app/`, `mcp_server/`, and `pipeline/`
- JavaScript (vanilla, no framework) - Frontend served by the Flask app (`app/` static/templates, per README)
- PySpark DataFrame/SQL API - `pipeline/market_pipeline_serverless.py` (window functions, joins, pandas UDF)

## Runtime

**Environment:**
- Databricks Runtime 15.4+ (DBR) for the Spark pipeline notebook (per README runbook)
- Databricks Apps runtime (Python) for `app/` and `mcp_server/` — each deployed as a separate Databricks App with its own `app.yaml`

**Package Manager:**
- pip, with per-app `requirements.txt` (no single root manifest)
- Lockfile: missing (requirements use `>=` version floors, no pinned lock)

## Frameworks

**Core:**
- Flask >=3.0.3 - Web app framework for `app/app.py` (255 lines), serves UI + API endpoints including `/healthz`
- FastMCP >=3.2.0 - MCP server framework for `mcp_server/research_mcp_server.py` (314 lines), exposes 10 tools (6 read, 4 write) over streamable HTTP at `/mcp`
- Apache Spark (PySpark, via Databricks) - `pipeline/market_pipeline_serverless.py` (611 lines): window functions, DataFrame join, pandas UDF for distributed embedding, partitioned Delta writes, `foreachPartition` upsert to Lakebase

**Testing:**
- Not detected - no test framework, test files, or test config found in the repo

**Build/Dev:**
- `databricks sync` / `databricks apps deploy` (Databricks CLI) - deployment mechanism for both `app/` and `mcp_server/` (see README runbook)
- `python-dotenv` >=1.0.1 - local `.env` loading for dev (see `.env.example`)

## Key Dependencies

**Critical:**
- `databricks-sdk` >=0.30.0 - `WorkspaceClient` used in `app/lakebase.py`, `mcp_server/lakebase.py`, `app/massive_client.py`, `mcp_server/massive_client.py`, `setup_secrets.py` for secret-scope resolution
- `psycopg2-binary` >=2.9.9 - raw Postgres/Lakebase connections (`app/lakebase.py`, `mcp_server/lakebase.py`) with `RealDictCursor`
- `sqlalchemy` >=2.0.30 - `get_engine()` helper in `lakebase.py` (used alongside raw psycopg2 for different query shapes)
- `sentence-transformers` >=2.2.0 - embedding model `all-MiniLM-L6-v2` (384-dim), used both in the Spark pandas UDF and app-side query embedding for semantic search
- `requests` >=2.32.3 - HTTP client underlying `MassiveClient` (`app/massive_client.py`, `mcp_server/massive_client.py`)

**Infrastructure:**
- `flask` >=3.0.3 - app server + routing (`app/app.py`)
- `fastmcp` >=3.2.0 - MCP tool server (`mcp_server/research_mcp_server.py`)
- pgvector extension (Postgres) - vector column type + HNSW index in Lakebase, referenced in `sql/01_schema.sql` (`VECTOR(384)`)
- trafilatura (implied by README, not in `requirements.txt` — verify before relying on it) - article body extraction run on Spark executors during pipeline ingest

## Configuration

**Environment:**
- App/MCP config supplied via each `app.yaml`'s `env:` block (non-secret settings only): `LAKEBASE_SECRET_SCOPE`, `LAKEBASE_SECRET_KEY`, `MASSIVE_SECRET_SCOPE`, `MASSIVE_SECRET_KEY`, `MASSIVE_API_BASE_URL` (app only), `EMBEDDING_MODEL`
- Actual secrets (Lakebase URL, Massive API key) are never in env vars or `app.yaml` — resolved at runtime through Databricks secret scopes via `WorkspaceClient().secrets.get_secret()`, base64-decoded
- Local dev template: `.env.example` documents the same var names for local development with `python-dotenv`; a real `.env` is gitignored and never committed

**Build:**
- `app/app.yaml` — Databricks App descriptor for the Flask app (`command: python app.py`, `resources: requirements.txt`)
- `mcp_server/app.yaml` — Databricks App descriptor for the MCP server (`command: python research_mcp_server.py`)
- `app/requirements.txt`, `mcp_server/requirements.txt` — per-app dependency lists (no root-level requirements file)

## Platform Requirements

**Development:**
- Databricks CLI configured with workspace auth (used by `setup_secrets.py` and the `databricks sync`/`databricks apps deploy` runbook steps)
- Databricks secret scopes `database` (key `lakebase-url`) and `massive` (key `api-key`) provisioned via `setup_secrets.py`
- Outbound internet from Spark executors, for `MassiveClient` API calls and `trafilatura` article fetching (falls back to title+description if unavailable)

**Production:**
- Databricks Apps (two separate app deployments: `market-copilot-app`, `market-copilot-mcp`)
- Databricks Lakebase (managed Postgres with pgvector) as the serving store
- Delta Lake / Unity Catalog (`main.market_research.*`) as the analytics store, written by the Spark pipeline
- Databricks cluster (DBR 15.4+) to run `pipeline/market_pipeline_serverless.py`

---

*Stack analysis: 2026-08-10*
