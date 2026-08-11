# Codebase Structure

**Analysis Date:** 2026-08-10

## Directory Layout

```
market-research-copilot/
├── app/                          # Databricks App: human-facing Flask frontend
│   ├── app.py                    # Flask routes / REST API + healthz
│   ├── app.yaml                  # Databricks App deployment manifest (command, env vars)
│   ├── lakebase.py                # Lakebase (Postgres) connection + query helpers
│   ├── massive_client.py         # Massive API client (price/news)
│   ├── requirements.txt          # App-specific Python dependencies
│   ├── static/                   # Static assets (currently empty of tracked files)
│   └── templates/
│       └── index.html            # Full SPA-ish UI: HTML + inline CSS + inline JS
├── mcp_server/                   # Databricks App: MCP tool server for the agent
│   ├── research_mcp_server.py    # FastMCP tool definitions (6 read, 4 write tools)
│   ├── app.yaml                  # Databricks App deployment manifest
│   ├── lakebase.py                # Duplicate of app/lakebase.py (independent deploy unit)
│   ├── massive_client.py         # Duplicate of app/massive_client.py
│   └── requirements.txt          # MCP-server-specific Python dependencies (fastmcp, no flask)
├── pipeline/                     # Spark ETL: ingest, transform, embed, load
│   ├── market_pipeline_serverless.py   # Databricks notebook (source-formatted .py)
│   └── resources/
│       └── market_pipeline_job.yml     # Databricks Jobs definition for scheduling
├── sql/
│   └── 01_schema.sql             # Full Lakebase Postgres/pgvector DDL, run once manually
├── setup_secrets.py              # One-time script: populates Databricks secret scopes
├── .env.example                  # Documents expected local env vars (no real secrets)
├── .gitignore
├── README.md                     # Architecture diagram, runbook, demo script
└── .planning/                    # GSD planning artifacts (not application code)
    └── codebase/                 # This directory — generated codebase maps
```

## Directory Purposes

**`app/`:**
- Purpose: standalone Databricks App providing the human UI over the same Lakebase data the agent uses.
- Contains: Flask app (`app.py`), a single Jinja template that embeds the entire frontend (`templates/index.html`), DB/API helper modules, its own `requirements.txt` and `app.yaml`.
- Key files: `app/app.py` (routes), `app/templates/index.html` (UI).
- Deployment: synced independently via `databricks sync app` / `databricks apps deploy market-copilot` — must be self-contained (no imports outside this directory).

**`mcp_server/`:**
- Purpose: standalone Databricks App exposing MCP tools to an Agent Bricks agent.
- Contains: `research_mcp_server.py` (tool definitions), duplicate `lakebase.py`/`massive_client.py`, its own `requirements.txt`/`app.yaml`.
- Key files: `mcp_server/research_mcp_server.py`.
- Deployment: synced independently via `databricks sync mcp_server` / `databricks apps deploy market-copilot-mcp` — same self-containment constraint as `app/`.

**`pipeline/`:**
- Purpose: batch Spark job — ingestion, feature engineering, news/price join, embedding, and load into Delta + Lakebase.
- Contains: one notebook-formatted `.py` file with `# COMMAND ----------` cell markers (import as a Databricks notebook, not run as a plain script) and a `resources/` subfolder for the Databricks Jobs YAML.
- Key files: `pipeline/market_pipeline_serverless.py`, `pipeline/resources/market_pipeline_job.yml`.

**`sql/`:**
- Purpose: single source of truth for the Lakebase Postgres schema.
- Contains: `01_schema.sql` — idempotent (`CREATE TABLE IF NOT EXISTS`) DDL for all 9 tables plus pgvector/HNSW index setup.
- Run manually once via the Lakebase SQL editor before first pipeline run (README "Runbook" step 1).

**`.planning/`:**
- Purpose: GSD workflow state (phases, plans, this codebase map). Not part of the runtime application.

## Key File Locations

**Entry Points:**
- `app/app.py`: Flask app entry point (`if __name__ == "__main__"` at line 254, `PORT` env var, default 8000).
- `mcp_server/research_mcp_server.py`: MCP server entry point (`if __name__ == "__main__"` at line 309, `streamable-http` transport).
- `pipeline/market_pipeline_serverless.py`: run top-to-bottom as a Databricks notebook ("Run All"), also schedulable via `pipeline/resources/market_pipeline_job.yml`.

**Configuration:**
- `app/app.yaml`, `mcp_server/app.yaml`: Databricks App manifests — command to run, requirements file, and non-secret env vars (secret scope/key names, embedding model name).
- `.env.example`: documents local dev env var names; never contains real values.
- `pipeline/market_pipeline_serverless.py:34-45`: `dbutils.widgets` define all pipeline runtime parameters (tickers, lookback days, rate limit, chunk size, etc.) — this is the pipeline's "config file" since it's a notebook.

**Core Logic:**
- `app/app.py`: all REST routes (`/api/watchlist`, `/api/metrics/<ticker>`, `/api/signals`, `/api/search`, `/api/notes`, `/api/reports`, `/api/stats`).
- `mcp_server/research_mcp_server.py`: all MCP tool functions.
- `app/lakebase.py` / `mcp_server/lakebase.py`: `run_query`, `run_write`, `run_returning` — the only way either app touches Postgres.
- `app/massive_client.py` / `mcp_server/massive_client.py`: `MassiveClient` class — the only way either app touches the Massive API.
- `pipeline/market_pipeline_serverless.py`: window-function feature computation (~line 284), news/price join (~line 345), pandas UDF embedding (~line 401), Lakebase `emit()` upsert (~line 513).

**Testing:**
- No test suite exists anywhere in this repository (no `tests/` directory, no `pytest`/`unittest` files, no test runner configured in either `requirements.txt`).

## Naming Conventions

**Files:**
- Snake_case Python modules matching their single responsibility: `lakebase.py` (DB), `massive_client.py` (external API), `app.py` (Flask entry), `research_mcp_server.py` (MCP entry).
- Numbered SQL files for ordering: `01_schema.sql` (room for future `02_*.sql` migrations).
- Databricks notebook files keep a plain `.py` extension but use `# COMMAND ----------` / `# MAGIC %md` / `# DBTITLE` markers internally — treat as notebooks, not importable modules.

**Directories:**
- Top-level directories are deployment units (`app/`, `mcp_server/`) or artifact type (`pipeline/`, `sql/`), not layered by technical concern (no `src/`, `lib/`, `utils/`).
- `resources/` inside `pipeline/` holds Databricks Asset Bundle-style job definitions, mirroring Databricks' own convention.

**Database:**
- Table names are snake_case nouns (`ticker_metrics`, `news_price_signals`, `research_notes`); `email` is the consistent ownership/foreign-key column across `watchlist`, `research_notes`, `analysis_reports`, `user_visits`.

## Where to Add New Code

**New Flask API route (human-facing feature):**
- Add the route function to `app/app.py`, grouped under the relevant `# ── Section ──` comment banner (Watchlist / Metrics / Search / Notes / Stats).
- Wire any new frontend UI into `app/templates/index.html` (inline JS `fetch()` calls follow the existing `/api/*` pattern).
- If it needs a new table/column, add it to `sql/01_schema.sql` with `CREATE TABLE IF NOT EXISTS`.

**New MCP tool (agent-facing capability):**
- Add a `@mcp.tool`-decorated function to `mcp_server/research_mcp_server.py`, under the `# ── Read tools ──` or `# ── Write tools ──` banner as appropriate.
- Write a thorough docstring — it is the only description the agent sees.
- Return `_json(...)`, never a raw dict, and mirror any corresponding logic added to `app/app.py` if the same data/action should be reachable by both human and agent (there is currently no shared module — duplicate deliberately, matching the existing `lakebase.py`/`massive_client.py` pattern).

**New Lakebase table or column:**
- Extend `sql/01_schema.sql` (append under `-- ── New for the capstone ──` or a new section); keep `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` idempotency.
- Update both `app/lakebase.py`-consuming routes and `mcp_server/lakebase.py`-consuming tools if the new data should be exposed both ways.

**New pipeline feature/metric:**
- Add to the window-function block in `pipeline/market_pipeline_serverless.py` (~line 284-341, `Window.partitionBy("ticker").orderBy("bar_date")`), then extend the corresponding `emit()` call's column list (~line 513-593) to persist it to Lakebase, and add the column to `ticker_metrics` in `sql/01_schema.sql`.

**Shared utilities:**
- No shared utility module exists between `app/` and `mcp_server/` by design (independent Databricks App deployments cannot share source outside their own directory). Duplicate small helpers into both directories rather than introducing a cross-directory import.

## Special Directories

**`app/static/`:**
- Purpose: intended location for static assets (CSS/JS/images) served by Flask.
- Generated: No.
- Committed: Directory exists but contains no tracked application assets beyond `.DS_Store`; `index.html` currently ships CSS/JS inline instead of via `static/`.

**`.planning/`:**
- Purpose: GSD workflow metadata and generated codebase documentation (this file included).
- Generated: Yes (by GSD tooling).
- Committed: Yes.

---

*Structure analysis: 2026-08-10*
