<!-- refreshed: 2026-08-10 -->
# Architecture

**Analysis Date:** 2026-08-10

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│  Massive API (bars + news)                                          │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │ driver-only HTTP (no executor internet)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Spark pipeline (Databricks notebook, serverless)                    │
│  `pipeline/market_pipeline_serverless.py`                            │
│  ├─ window functions ─► returns, MA5/MA20, 20d volatility,           │
│  │                      volume z-score, drawdown, trend              │
│  ├─ join news × metrics ─► news_price_signals                        │
│  └─ pandas UDF ─► chunk + embed article text (distributed)           │
└───────────┬─────────────────────────────────┬─────────────────────────┘
            │                                 │
            ▼                                 ▼
┌──────────────────────────┐     ┌───────────────────────────────────┐
│ Delta / Unity Catalog     │     │ Lakebase Postgres (serving)        │
│ analytics tables,         │     │ pgvector + HNSW, generated SQL     │
│ partitioned by ticker     │     │ file replayed via psycopg2         │
└──────────────────────────┘     └───────────────┬─────────────────────┘
                                                  │
                          ┌───────────────────────┴───────────────────────┐
                          ▼                                               ▼
          ┌───────────────────────────────┐             ┌───────────────────────────────┐
          │ app/ (Databricks App)          │             │ mcp_server/ (Databricks App)    │
          │ Flask + vanilla JS             │             │ FastMCP over streamable HTTP    │
          │ `app/app.py`, `app/templates/` │             │ `mcp_server/research_mcp_server.py` │
          │ watchlist, semantic search,    │             │ 10 tools (6 read, 4 write)      │
          │ signals, notes, reports        │             └───────────────┬─────────────────┘
          └───────────────────────────────┘                             │ MCP (streamable HTTP)
                                                                          ▼
                                                          ┌───────────────────────────────┐
                                                          │ Agent Bricks agent              │
                                                          │ (+ Day 3's Alpaca MCP server     │
                                                          │  for paper trading)             │
                                                          └───────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Spark pipeline | Ingests Massive bars/news, computes technical features, joins news to price moves, embeds article chunks, writes Delta + Lakebase | `pipeline/market_pipeline_serverless.py` |
| Pipeline job resource | Databricks Jobs definition for scheduling the pipeline notebook | `pipeline/resources/market_pipeline_job.yml` |
| Lakebase schema | Postgres/pgvector DDL for all serving tables | `sql/01_schema.sql` |
| Flask app backend | REST API over Lakebase for the human-facing UI | `app/app.py` |
| Flask app frontend | Single-page vanilla JS UI (watchlist, search, signals, notes, reports) | `app/templates/index.html`, `app/static/` |
| App DB helper | Connection + query/write helpers against Lakebase | `app/lakebase.py` |
| App Massive client | Thin REST client for on-demand price lookups (e.g. add-to-watchlist) | `app/massive_client.py` |
| MCP server | Exposes read/write research tools to an Agent Bricks agent over MCP | `mcp_server/research_mcp_server.py` |
| MCP DB helper | Duplicate of `app/lakebase.py`, deployed independently with the MCP app | `mcp_server/lakebase.py` |
| MCP Massive client | Duplicate of `app/massive_client.py`, deployed independently with the MCP app | `mcp_server/massive_client.py` |
| Secrets bootstrap | One-time script to populate Databricks secret scopes | `setup_secrets.py` |

## Pattern Overview

**Overall:** Batch ETL feeding a shared Postgres serving layer, consumed by two independent, separately-deployed Databricks Apps (one human-facing web app, one MCP tool server) that read/write the same tables. No shared Python package between `app/` and `mcp_server/` — each is a self-contained deployable unit with its own copy of `lakebase.py` and `massive_client.py`.

**Key Characteristics:**
- Single writer (Spark pipeline) for analytical tables (`price_bars`, `ticker_metrics`, `news_price_signals`, embeddings); multiple writers (human via `app/`, agent via `mcp_server/`) for interactive tables (`watchlist`, `research_notes`, `analysis_reports`, `user_visits`).
- No ORM — hand-written parameterized SQL via `psycopg2`, `RealDictCursor` for dict-shaped rows.
- Two runtimes read the same schema through structurally identical (copy-pasted) DB helpers rather than a shared library — a deliberate deployment-isolation tradeoff (each Databricks App is synced/deployed independently and cannot import across app boundaries).
- Secrets resolved at runtime via the Databricks SDK secret scopes (`WorkspaceClient().secrets.get_secret`), never stored in code, `.env`, or `app.yaml`.
- Embedding model (`sentence-transformers/all-MiniLM-L6-v2`, dim 384) is loaded lazily and cached as a module-level global in both `app/app.py` and `mcp_server/research_mcp_server.py`.

## Layers

**Ingestion / transform (pipeline):**
- Purpose: pull raw bars + news from Massive, compute technical features, join news to price signals, embed article chunks, persist to Delta and Lakebase.
- Location: `pipeline/market_pipeline_serverless.py`
- Contains: Databricks notebook cells (`# COMMAND ----------` delimited), PySpark DataFrame/window logic, a pandas UDF, a driver-side `foreachPartition`-free SQL-generation upsert routine (`emit()`).
- Depends on: Massive API, Unity Catalog volume for the staged embedding model, Lakebase secret scope.
- Used by: nothing downstream in-process; output consumed by `app/` and `mcp_server/` via Lakebase tables.

**Serving store (Lakebase Postgres):**
- Purpose: single source of truth read by both the app and the agent; the only place app/agent state (watchlist, notes, reports) and pipeline output (metrics, signals, embeddings) coexist.
- Location: `sql/01_schema.sql` (schema); accessed via `app/lakebase.py` / `mcp_server/lakebase.py`.
- Contains: 9 tables — `watchlist`, `ticker_news_documents`, `ticker_news_chunk_embeddings` (pgvector + HNSW), `price_bars`, `ticker_metrics`, `news_price_signals`, `research_notes`, `analysis_reports`, `user_visits`.

**Human app layer (`app/`):**
- Purpose: Flask REST API + server-rendered shell + vanilla JS SPA-ish frontend giving a human the same views/actions as the agent.
- Location: `app/app.py` (routes), `app/templates/index.html` (UI + inline JS/CSS), `app/static/` (present but currently empty of tracked assets beyond `.DS_Store`).
- Depends on: `app/lakebase.py`, `app/massive_client.py`, `sentence_transformers` (lazy-loaded for `/api/search`).
- Used by: end user's browser; also the demo/verification path (`/healthz`).

**Agent tool layer (`mcp_server/`):**
- Purpose: exposes the same underlying data/actions as callable MCP tools for an Agent Bricks agent.
- Location: `mcp_server/research_mcp_server.py`
- Depends on: `mcp_server/lakebase.py`, `fastmcp`, `sentence_transformers`.
- Used by: Agent Bricks agent over `streamable-http` MCP transport (deployed as its own Databricks App, separate URL from `app/`).

## Data Flow

### Pipeline run (batch)

1. Notebook config widgets set catalog/schema/tickers/lookback (`pipeline/market_pipeline_serverless.py:34-58`).
2. Embedding model staged once into a UC Volume so read-only executors can load it later (`pipeline/market_pipeline_serverless.py:93-116`).
3. Ticker universe resolved from Lakebase `watchlist` via a JDBC read, falling back to the widget list; capped by `max_tickers` for the Massive free tier (`pipeline/market_pipeline_serverless.py:128-155`).
4. Bars + news fetched from Massive on the driver only — executors have no outbound internet (`pipeline/market_pipeline_serverless.py:159-233`, `def massive_get`).
5. Optional full article body fetch via `trafilatura`, falling back to title+description (`pipeline/market_pipeline_serverless.py:236-273`).
6. Technical features computed with per-ticker `Window` functions: `daily_return` (`lag`), `ma_5`/`ma_20` (`rowsBetween`), `volatility_20d` (rolling stddev × √252), `volume_zscore_20d`, `drawdown_from_high` (unbounded running max), `trend` (MA5 vs MA20) (`pipeline/market_pipeline_serverless.py:284-341`).
7. News joined to same-day metrics into `news_price_signals`, bucketed strong/material/routine by `abs_return` (`pipeline/market_pipeline_serverless.py:345-388`).
8. Article text chunked and embedded via a pandas UDF (`ArrayType(FloatType())`) running on executors against the pre-staged model (`pipeline/market_pipeline_serverless.py:391-482`, `def chunk_text`, `_make_embed`).
9. Results written to Delta/Unity Catalog (analytics) and to Lakebase via a generated-SQL upsert (`emit()`) — chosen because serverless blocks JDBC writes and psycopg2 crashes the kernel directly (`pipeline/market_pipeline_serverless.py:485-593`).

### Human web request path

1. Browser hits `app/app.py` route (e.g. `GET /api/watchlist`).
2. `_user()` resolves identity from the `X-Forwarded-Email` header (Databricks Apps SSO) or `DEFAULT_EMAIL` (`app/app.py:34-36`).
3. Route calls `run_query`/`run_write`/`run_returning` from `app/lakebase.py`, which opens a fresh `psycopg2` connection per call using a Lakebase URL fetched from the Databricks secret scope (`app/lakebase.py:25-38`).
4. JSON response rendered via `jsonify`; `index.html` fetches these routes with `fetch()` from inline JS.

### Agent tool-call path

1. Agent Bricks agent calls an MCP tool (e.g. `save_research_note`) over `streamable-http` against the deployed `mcp_server` app URL (`mcp_server/research_mcp_server.py:309-314`).
2. Tool function runs parameterized SQL via `mcp_server/lakebase.py` (same helper shape as `app/lakebase.py`, independently deployed).
3. Write tools (`add_to_watchlist`, `remove_from_watchlist`, `save_research_note`, `save_analysis_report`) commit directly to Lakebase; the human app reflects the change on next poll/reload without a redeploy.
4. `flag_moves_since_last_visit` both reads (`user_visits`, `ticker_metrics`, `news_price_signals`) and writes (`user_visits.last_seen_at`) in one tool call (`mcp_server/research_mcp_server.py:190-225`).

**State Management:**
- No application-level session state; identity per request/tool-call is just an email string (`X-Forwarded-Email` header or explicit `email` tool argument, defaulting to `DEFAULT_EMAIL`).
- All persistent state lives in Lakebase Postgres; there is no in-memory cache layer.

## Key Abstractions

**DB access helpers (`run_query` / `run_write` / `run_returning`):**
- Purpose: uniform psycopg2 access pattern — `run_query` for SELECT (returns `list[dict]` via `RealDictCursor`), `run_write` for INSERT/UPDATE/DELETE (returns row count, commits), `run_returning` for INSERT...RETURNING (commits, returns rows, rolls back on exception).
- Examples: `app/lakebase.py:46-75`, `mcp_server/lakebase.py` (identical copy).
- Pattern: context-managed connection per call (`get_connection()`), no connection pooling, secret fetched fresh from `WorkspaceClient` each call.

**Massive API client (`MassiveClient`):**
- Purpose: thin authenticated wrapper (`requests.Session`) around the Massive REST API for prices and news, with a generator-based `paginated_get` for cursor-paginated endpoints.
- Examples: `app/massive_client.py`, `mcp_server/massive_client.py` (identical copy).
- Pattern: API key resolved once at client construction from a Databricks secret scope; single-call helpers (`get_latest_price`, `get_news`) are used in preference to `paginated_get` to respect the free-tier rate limit.

**MCP tool functions:**
- Purpose: each `@mcp.tool`-decorated function in `mcp_server/research_mcp_server.py` is both a Python function and an agent-callable tool, with its docstring serving as the tool description shown to the LLM.
- Examples: `search_ticker_news`, `get_ticker_metrics`, `compare_tickers`, `get_news_price_signals`, `get_watchlist`, `get_research_notes`, `flag_moves_since_last_visit` (reads); `add_to_watchlist`, `remove_from_watchlist`, `save_research_note`, `save_analysis_report` (writes).
- Pattern: every tool returns a JSON string (`_json()` wrapping `json.dumps(..., default=str, indent=2)`), never raw dicts, so the agent always receives serializable text.

**Spark `emit()` upsert helper:**
- Purpose: generates a batched, driver-executed SQL `INSERT ... ON CONFLICT DO UPDATE` file per table instead of a JDBC write, working around serverless's blocked JDBC writes and psycopg2-crashes-kernel constraint.
- Location: `pipeline/market_pipeline_serverless.py:513` (`def emit`).
- Pattern: takes a DataFrame, target table, column list, conflict key, and update clause; batches rows (default 200) into generated SQL statements.

## Entry Points

**Flask app (`app/app.py`):**
- Location: `app/app.py`
- Triggers: HTTP requests to the Databricks App URL (deployed via `databricks apps deploy market-copilot`); local dev via `python app.py` (`PORT` env var, default 8000).
- Responsibilities: serves `index.html`, all `/api/*` REST routes, `/healthz` liveness check.

**MCP server (`mcp_server/research_mcp_server.py`):**
- Location: `mcp_server/research_mcp_server.py`
- Triggers: MCP tool calls from an Agent Bricks agent over `streamable-http`; deployed as its own Databricks App (`databricks apps deploy market-copilot-mcp`).
- Responsibilities: exposes the 10 research/watchlist/notes/reports tools listed above.

**Spark pipeline notebook (`pipeline/market_pipeline_serverless.py`):**
- Location: `pipeline/market_pipeline_serverless.py`; scheduled via `pipeline/resources/market_pipeline_job.yml`.
- Triggers: manual "Run All" in Databricks or the scheduled Databricks Job.
- Responsibilities: full ingest → transform → embed → Delta/Lakebase write cycle described above.

**Secrets bootstrap (`setup_secrets.py`):**
- Location: `setup_secrets.py`
- Triggers: run manually once during environment setup.
- Responsibilities: populates the `database` and `massive` Databricks secret scopes used by every other component.

## Architectural Constraints

- **Threading:** Flask app runs single-process, default Werkzeug dev server (`app.run(..., debug=False)`); no async framework. MCP server runs FastMCP's `streamable-http` transport, also single-process.
- **Global state:** Lazily-initialized `_model` (SentenceTransformer) module-level global in both `app/app.py:22` and `mcp_server/research_mcp_server.py:30` — first request/tool-call in a process pays the load cost, subsequent ones reuse it. No other shared mutable state.
- **No connection pooling:** every `run_query`/`run_write`/`run_returning` call opens and closes a new `psycopg2` connection and re-fetches the Lakebase secret from the Databricks SDK (`app/lakebase.py:25-38`) — acceptable at demo scale, a scaling concern at higher request volume (see CONCERNS.md if present).
- **Serverless Spark constraints:** no `.cache()`/`persist()`, no executor outbound internet, executors have a read-only filesystem, no JDBC writes from serverless compute — each directly shapes a design choice in `pipeline/market_pipeline_serverless.py` (see header comment block, lines 1-20).
- **Duplicated code across deployables:** `app/lakebase.py` ≈ `mcp_server/lakebase.py` and `app/massive_client.py` ≈ `mcp_server/massive_client.py` are intentionally separate copies (not a shared package) because each Databricks App is synced/deployed as an isolated source tree.

## Anti-Patterns

None identified as deliberate anti-patterns beyond the documented, constraint-driven tradeoffs above (code duplication across `app/` and `mcp_server/`, per-call connection creation) — these are explained in-repo as consequences of the Databricks Apps/serverless deployment model rather than oversights.

## Error Handling

**Strategy:** Flask-level catch-all exception handler returning JSON errors; MCP tools return structured `{"ok": false, "error": ...}` JSON rather than raising, so the agent gets a parseable failure instead of a broken tool call.

**Patterns:**
- `app/app.py:39-42` — `@app.errorhandler(Exception)` logs and returns `{"error": str(err)}` with HTTP 500 for any unhandled exception.
- Route-level input validation returns HTTP 400 with a specific message before hitting the DB (e.g. `add_watchlist` symbol validation, `app/app.py:77-79`).
- Non-critical failures are swallowed deliberately with a comment explaining why: `add_watchlist`'s price lookup catches all exceptions so a rate-limited quote never blocks adding a ticker (`app/app.py:87-88`).
- `run_returning` explicitly rolls back on exception before re-raising (`app/lakebase.py:63-65`); `run_query`/`run_write` rely on the `with get_connection()` context manager closing the connection.
- Pipeline notebook wraps the Lakebase JDBC watchlist read in a `try/except` with a fallback to the widget ticker list, printing the exception type rather than failing the run (`pipeline/market_pipeline_serverless.py:130-143`).

## Cross-Cutting Concerns

**Logging:** Flask's built-in logger (`app.logger.exception` / `app.logger.warning`) only; MCP server has no explicit logging beyond FastMCP's own. Pipeline notebook uses `print()` for cell-by-cell progress/diagnostics (Databricks notebook convention).

**Validation:** Manual, per-route/per-tool input checks (symbol format/length, non-empty note text) — no schema validation library (no Pydantic/marshmallow) in `app/` or `mcp_server/`.

**Authentication:** Identity is trust-based, not verified — `app/app.py` trusts the `X-Forwarded-Email` header set by Databricks Apps' built-in SSO proxy; `mcp_server` tools accept an optional `email` argument but explicitly do NOT trust it for `analysis_reports` ownership (`mcp_server/research_mcp_server.py:283-284`, always uses `DEFAULT_EMAIL`). No app-level auth/session logic exists.

---

*Architecture analysis: 2026-08-10*
