<!-- GSD:project-start source:PROJECT.md -->

## Project

**Market Research Copilot — Frontend Elevation**

Market Research Copilot is a working Databricks-native market research tool: a Spark pipeline ingests price bars and news, computes technical signals, and embeds article text into Lakebase (Postgres + pgvector); a Flask web app and a FastMCP tool server both read/write that same Lakebase data — one for a human via browser, one for an Agent Bricks agent. This milestone is a frontend-only elevation: take the existing, functioning (screenshot-verified) UI from a plain bordered-table look to a modern, portfolio-grade dashboard, without touching the backend contract.

**Core Value:** The app must look and feel like a real product — a visual quality bar that holds up in a job-application portfolio — while every currently-working feature (watchlist, semantic search, news signals, research notes, agent reports) keeps working exactly as it does today.

### Constraints

- **Tech stack**: No build step / bundler in this repo today (no `package.json`) — frontend work stays in plain HTML/CSS/JS served by Flask; a CDN-hosted charting library (e.g. Chart.js) is acceptable, no npm toolchain introduction.
- **Backend contract**: `app/app.py` route paths, request params, and JSON response shapes must not change unless a plan explicitly calls it out and confirms the MCP server / agent integration is unaffected.
- **Deployment**: Must keep working under Databricks Apps' single-process Flask dev-server deployment (`app/app.yaml`, `command: python app.py`) — no new runtime/process requirements.
- **Data reality**: Most watchlist tickers currently lack computed metrics (pipeline ran against a capped `max_tickers`) — the UI must degrade gracefully for missing data, not assume every row is fully populated.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3 - Entire codebase: Spark pipeline (`pipeline/market_pipeline_serverless.py`), Flask app (`app/app.py`), MCP server (`mcp_server/research_mcp_server.py`)
- SQL - Schema DDL (`sql/01_schema.sql`), embedded query strings throughout `app/`, `mcp_server/`, and `pipeline/`
- JavaScript (vanilla, no framework) - Frontend served by the Flask app (`app/` static/templates, per README)
- PySpark DataFrame/SQL API - `pipeline/market_pipeline_serverless.py` (window functions, joins, pandas UDF)

## Runtime

- Databricks Runtime 15.4+ (DBR) for the Spark pipeline notebook (per README runbook)
- Databricks Apps runtime (Python) for `app/` and `mcp_server/` — each deployed as a separate Databricks App with its own `app.yaml`
- pip, with per-app `requirements.txt` (no single root manifest)
- Lockfile: missing (requirements use `>=` version floors, no pinned lock)

## Frameworks

- Flask >=3.0.3 - Web app framework for `app/app.py` (255 lines), serves UI + API endpoints including `/healthz`
- FastMCP >=3.2.0 - MCP server framework for `mcp_server/research_mcp_server.py` (314 lines), exposes 10 tools (6 read, 4 write) over streamable HTTP at `/mcp`
- Apache Spark (PySpark, via Databricks) - `pipeline/market_pipeline_serverless.py` (611 lines): window functions, DataFrame join, pandas UDF for distributed embedding, partitioned Delta writes, `foreachPartition` upsert to Lakebase
- Not detected - no test framework, test files, or test config found in the repo
- `databricks sync` / `databricks apps deploy` (Databricks CLI) - deployment mechanism for both `app/` and `mcp_server/` (see README runbook)
- `python-dotenv` >=1.0.1 - local `.env` loading for dev (see `.env.example`)

## Key Dependencies

- `databricks-sdk` >=0.30.0 - `WorkspaceClient` used in `app/lakebase.py`, `mcp_server/lakebase.py`, `app/massive_client.py`, `mcp_server/massive_client.py`, `setup_secrets.py` for secret-scope resolution
- `psycopg2-binary` >=2.9.9 - raw Postgres/Lakebase connections (`app/lakebase.py`, `mcp_server/lakebase.py`) with `RealDictCursor`
- `sqlalchemy` >=2.0.30 - `get_engine()` helper in `lakebase.py` (used alongside raw psycopg2 for different query shapes)
- `sentence-transformers` >=2.2.0 - embedding model `all-MiniLM-L6-v2` (384-dim), used both in the Spark pandas UDF and app-side query embedding for semantic search
- `requests` >=2.32.3 - HTTP client underlying `MassiveClient` (`app/massive_client.py`, `mcp_server/massive_client.py`)
- `flask` >=3.0.3 - app server + routing (`app/app.py`)
- `fastmcp` >=3.2.0 - MCP tool server (`mcp_server/research_mcp_server.py`)
- pgvector extension (Postgres) - vector column type + HNSW index in Lakebase, referenced in `sql/01_schema.sql` (`VECTOR(384)`)
- trafilatura (implied by README, not in `requirements.txt` — verify before relying on it) - article body extraction run on Spark executors during pipeline ingest

## Configuration

- App/MCP config supplied via each `app.yaml`'s `env:` block (non-secret settings only): `LAKEBASE_SECRET_SCOPE`, `LAKEBASE_SECRET_KEY`, `MASSIVE_SECRET_SCOPE`, `MASSIVE_SECRET_KEY`, `MASSIVE_API_BASE_URL` (app only), `EMBEDDING_MODEL`
- Actual secrets (Lakebase URL, Massive API key) are never in env vars or `app.yaml` — resolved at runtime through Databricks secret scopes via `WorkspaceClient().secrets.get_secret()`, base64-decoded
- Local dev template: `.env.example` documents the same var names for local development with `python-dotenv`; a real `.env` is gitignored and never committed
- `app/app.yaml` — Databricks App descriptor for the Flask app (`command: python app.py`, `resources: requirements.txt`)
- `mcp_server/app.yaml` — Databricks App descriptor for the MCP server (`command: python research_mcp_server.py`)
- `app/requirements.txt`, `mcp_server/requirements.txt` — per-app dependency lists (no root-level requirements file)

## Platform Requirements

- Databricks CLI configured with workspace auth (used by `setup_secrets.py` and the `databricks sync`/`databricks apps deploy` runbook steps)
- Databricks secret scopes `database` (key `lakebase-url`) and `massive` (key `api-key`) provisioned via `setup_secrets.py`
- Outbound internet from Spark executors, for `MassiveClient` API calls and `trafilatura` article fetching (falls back to title+description if unavailable)
- Databricks Apps (two separate app deployments: `market-copilot-app`, `market-copilot-mcp`)
- Databricks Lakebase (managed Postgres with pgvector) as the serving store
- Delta Lake / Unity Catalog (`main.market_research.*`) as the analytics store, written by the Spark pipeline
- Databricks cluster (DBR 15.4+) to run `pipeline/market_pipeline_serverless.py`

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Lowercase snake_case module names: `app.py`, `lakebase.py`, `massive_client.py`, `research_mcp_server.py`, `setup_secrets.py`
- The three services (`app/`, `mcp_server/`, `pipeline/`) each own their own copy of shared helper modules (`lakebase.py`, `massive_client.py` are duplicated verbatim between `app/` and `mcp_server/` — see CONCERNS.md for the drift risk this creates)
- snake_case throughout: `run_query`, `get_latest_price`, `flag_moves_since_last_visit`
- Private/internal helpers prefixed with a single underscore: `_embed`, `_user`, `_lakebase_url`, `_get_api_key`, `_json`, `_secret` (`pipeline/market_pipeline_serverless.py:73`)
- Route handlers and MCP tools use verb_noun naming that mirrors the HTTP/tool action: `get_watchlist`, `add_watchlist`, `remove_watchlist`, `add_to_watchlist`, `remove_from_watchlist`
- snake_case for locals (`ticker`, `note_text`, `bar_date`)
- SCREAMING_SNAKE_CASE for module-level constants sourced from env or config, always with an inline default: `EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")` (`app/app.py:19`), `_SCOPE`, `_KEY`, `_BASE_URL` (`app/massive_client.py:18-20`)
- Databricks notebook widgets in `pipeline/market_pipeline_serverless.py` follow the same SCREAMING_SNAKE_CASE-from-widget pattern: `CATALOG`, `LOOKBACK_DAYS`, `MAX_RPM` (`pipeline/market_pipeline_serverless.py:41-51`)
- No custom classes beyond `MassiveClient` (`app/massive_client.py:31`) and Flask app/MCP server instances. Type hints use built-in generics (`list[dict]`, `dict[str, Any]`, `tuple | dict | None`) — Python 3.10+ union syntax, no `typing.Optional`/`typing.List`.

## Code Style

- No formatter config present (no `.prettierrc`, `pyproject.toml`, `black` config, or `ruff.toml`). Style is consistent by hand: 4-space indentation, double-quoted strings, trailing commas in multi-line calls.
- Section dividers use a recurring comment banner to group related routes/tools:
- No `.eslintrc`, `ruff.toml`, `.flake8`, or `pyproject.toml` lint config found anywhere in the repo. No lint step is enforced.
- One `# noqa: BLE001` suppression comment appears for an intentionally broad `except Exception` (`app/app.py:87`), implying the author lints locally with `ruff`/`flake8` even though no config is committed — do not assume a lint gate exists in CI (there is no CI, see below).

## Import Organization

- None. Each service directory (`app/`, `mcp_server/`) is flat and imports siblings directly by module name (`from lakebase import ...`), relying on the process working directory rather than a package/`src` layout.

## Error Handling

- Flask app registers one global handler that logs and returns JSON 500s: `@app.errorhandler(Exception)` → `app.logger.exception("request failed")` → `jsonify({"error": str(err)}), 500` (`app/app.py:39-42`). Individual routes generally do not use try/except; they let unexpected errors bubble to this handler.
- Deliberate exceptions to that rule are narrow and explained: `app/app.py:82-88` wraps a price lookup in `try/except Exception as exc` specifically so a rate-limited third-party call cannot block adding a ticker to the watchlist, logging a warning instead of failing the request.
- Input validation is manual and inline at the top of each write route/tool, returning a 400 (Flask) or an `{"ok": False, "error": ...}` payload (MCP), e.g. `app/app.py:78-79`, `mcp_server/research_mcp_server.py:233-235`.
- Database writes that need atomicity wrap the cursor call in `try/except Exception: conn.rollback(); raise` before re-raising to the caller — see `run_returning` in `app/lakebase.py:56-65`. Plain `run_write` does not roll back on error (no try/except around its commit).
- JSON parsing failures are caught narrowly with `json.JSONDecodeError`, not bare `except`: `app/app.py:230-233`, `mcp_server/research_mcp_server.py:287-289`.
- The Spark pipeline (`pipeline/market_pipeline_serverless.py`) implements its own retry loop for HTTP calls: `massive_get(path, params=None, _retries=2)` (`pipeline/market_pipeline_serverless.py:179`) rather than using a library like `tenacity`.

## Logging

- Use `app.logger.exception(...)` for unexpected errors so the traceback is captured (`app/app.py:41`).
- Use `app.logger.warning(...)` with an f-string-free, `%s`-style format for expected-but-notable failures: `app.logger.warning("price lookup failed for %s: %s", symbol, exc)` (`app/app.py:88`).

## Comments

- Module docstrings on every file explain *why* the module exists and any non-obvious constraint (e.g. why Lakebase auth uses one URL secret instead of five vars — `app/lakebase.py:1-8`; why the pipeline only runs on the driver — `pipeline/market_pipeline_serverless.py:1-19`).
- Function docstrings favor one-line summaries; multi-line docstrings are reserved for functions with non-obvious behavior or contracts callers must know (e.g. `massive_client.py:78-87` explains why `get_latest_price` avoids pagination; `research_mcp_server.py:283-284` explains that the `email` MCP arg is not trusted for ownership).
- Inline comments are used sparingly, mostly to flag security/trust boundaries (`# a rate-limited quote must not block the add`, `# Databricks Apps forwards the signed-in user in this header.`) or explain a non-obvious SQL/logic choice.

## Function Design

## Module Design

## Databricks/Notebook-Specific Conventions

- `pipeline/market_pipeline_serverless.py` is a Databricks notebook exported as a `.py` file with `# COMMAND ----------` cell markers and `# DBTITLE` cell titles — treat it as notebook source, not a conventional importable module. Config comes from `dbutils.widgets` rather than argparse/env vars.
- Secrets are never read from `.env` in the app/mcp_server services; they are fetched at runtime via `WorkspaceClient().secrets.get_secret(scope=..., key=...)` and base64-decoded (`app/lakebase.py:25-28`, `app/massive_client.py:25-28`). `.env` is used only for local dev overrides (see `.env.example`).

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

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

- Single writer (Spark pipeline) for analytical tables (`price_bars`, `ticker_metrics`, `news_price_signals`, embeddings); multiple writers (human via `app/`, agent via `mcp_server/`) for interactive tables (`watchlist`, `research_notes`, `analysis_reports`, `user_visits`).
- No ORM — hand-written parameterized SQL via `psycopg2`, `RealDictCursor` for dict-shaped rows.
- Two runtimes read the same schema through structurally identical (copy-pasted) DB helpers rather than a shared library — a deliberate deployment-isolation tradeoff (each Databricks App is synced/deployed independently and cannot import across app boundaries).
- Secrets resolved at runtime via the Databricks SDK secret scopes (`WorkspaceClient().secrets.get_secret`), never stored in code, `.env`, or `app.yaml`.
- Embedding model (`sentence-transformers/all-MiniLM-L6-v2`, dim 384) is loaded lazily and cached as a module-level global in both `app/app.py` and `mcp_server/research_mcp_server.py`.

## Layers

- Purpose: pull raw bars + news from Massive, compute technical features, join news to price signals, embed article chunks, persist to Delta and Lakebase.
- Location: `pipeline/market_pipeline_serverless.py`
- Contains: Databricks notebook cells (`# COMMAND ----------` delimited), PySpark DataFrame/window logic, a pandas UDF, a driver-side `foreachPartition`-free SQL-generation upsert routine (`emit()`).
- Depends on: Massive API, Unity Catalog volume for the staged embedding model, Lakebase secret scope.
- Used by: nothing downstream in-process; output consumed by `app/` and `mcp_server/` via Lakebase tables.
- Purpose: single source of truth read by both the app and the agent; the only place app/agent state (watchlist, notes, reports) and pipeline output (metrics, signals, embeddings) coexist.
- Location: `sql/01_schema.sql` (schema); accessed via `app/lakebase.py` / `mcp_server/lakebase.py`.
- Contains: 9 tables — `watchlist`, `ticker_news_documents`, `ticker_news_chunk_embeddings` (pgvector + HNSW), `price_bars`, `ticker_metrics`, `news_price_signals`, `research_notes`, `analysis_reports`, `user_visits`.
- Purpose: Flask REST API + server-rendered shell + vanilla JS SPA-ish frontend giving a human the same views/actions as the agent.
- Location: `app/app.py` (routes), `app/templates/index.html` (UI + inline JS/CSS), `app/static/` (present but currently empty of tracked assets beyond `.DS_Store`).
- Depends on: `app/lakebase.py`, `app/massive_client.py`, `sentence_transformers` (lazy-loaded for `/api/search`).
- Used by: end user's browser; also the demo/verification path (`/healthz`).
- Purpose: exposes the same underlying data/actions as callable MCP tools for an Agent Bricks agent.
- Location: `mcp_server/research_mcp_server.py`
- Depends on: `mcp_server/lakebase.py`, `fastmcp`, `sentence_transformers`.
- Used by: Agent Bricks agent over `streamable-http` MCP transport (deployed as its own Databricks App, separate URL from `app/`).

## Data Flow

### Pipeline run (batch)

### Human web request path

### Agent tool-call path

- No application-level session state; identity per request/tool-call is just an email string (`X-Forwarded-Email` header or explicit `email` tool argument, defaulting to `DEFAULT_EMAIL`).
- All persistent state lives in Lakebase Postgres; there is no in-memory cache layer.

## Key Abstractions

- Purpose: uniform psycopg2 access pattern — `run_query` for SELECT (returns `list[dict]` via `RealDictCursor`), `run_write` for INSERT/UPDATE/DELETE (returns row count, commits), `run_returning` for INSERT...RETURNING (commits, returns rows, rolls back on exception).
- Examples: `app/lakebase.py:46-75`, `mcp_server/lakebase.py` (identical copy).
- Pattern: context-managed connection per call (`get_connection()`), no connection pooling, secret fetched fresh from `WorkspaceClient` each call.
- Purpose: thin authenticated wrapper (`requests.Session`) around the Massive REST API for prices and news, with a generator-based `paginated_get` for cursor-paginated endpoints.
- Examples: `app/massive_client.py`, `mcp_server/massive_client.py` (identical copy).
- Pattern: API key resolved once at client construction from a Databricks secret scope; single-call helpers (`get_latest_price`, `get_news`) are used in preference to `paginated_get` to respect the free-tier rate limit.
- Purpose: each `@mcp.tool`-decorated function in `mcp_server/research_mcp_server.py` is both a Python function and an agent-callable tool, with its docstring serving as the tool description shown to the LLM.
- Examples: `search_ticker_news`, `get_ticker_metrics`, `compare_tickers`, `get_news_price_signals`, `get_watchlist`, `get_research_notes`, `flag_moves_since_last_visit` (reads); `add_to_watchlist`, `remove_from_watchlist`, `save_research_note`, `save_analysis_report` (writes).
- Pattern: every tool returns a JSON string (`_json()` wrapping `json.dumps(..., default=str, indent=2)`), never raw dicts, so the agent always receives serializable text.
- Purpose: generates a batched, driver-executed SQL `INSERT ... ON CONFLICT DO UPDATE` file per table instead of a JDBC write, working around serverless's blocked JDBC writes and psycopg2-crashes-kernel constraint.
- Location: `pipeline/market_pipeline_serverless.py:513` (`def emit`).
- Pattern: takes a DataFrame, target table, column list, conflict key, and update clause; batches rows (default 200) into generated SQL statements.

## Entry Points

- Location: `app/app.py`
- Triggers: HTTP requests to the Databricks App URL (deployed via `databricks apps deploy market-copilot`); local dev via `python app.py` (`PORT` env var, default 8000).
- Responsibilities: serves `index.html`, all `/api/*` REST routes, `/healthz` liveness check.
- Location: `mcp_server/research_mcp_server.py`
- Triggers: MCP tool calls from an Agent Bricks agent over `streamable-http`; deployed as its own Databricks App (`databricks apps deploy market-copilot-mcp`).
- Responsibilities: exposes the 10 research/watchlist/notes/reports tools listed above.
- Location: `pipeline/market_pipeline_serverless.py`; scheduled via `pipeline/resources/market_pipeline_job.yml`.
- Triggers: manual "Run All" in Databricks or the scheduled Databricks Job.
- Responsibilities: full ingest → transform → embed → Delta/Lakebase write cycle described above.
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

## Error Handling

- `app/app.py:39-42` — `@app.errorhandler(Exception)` logs and returns `{"error": str(err)}` with HTTP 500 for any unhandled exception.
- Route-level input validation returns HTTP 400 with a specific message before hitting the DB (e.g. `add_watchlist` symbol validation, `app/app.py:77-79`).
- Non-critical failures are swallowed deliberately with a comment explaining why: `add_watchlist`'s price lookup catches all exceptions so a rate-limited quote never blocks adding a ticker (`app/app.py:87-88`).
- `run_returning` explicitly rolls back on exception before re-raising (`app/lakebase.py:63-65`); `run_query`/`run_write` rely on the `with get_connection()` context manager closing the connection.
- Pipeline notebook wraps the Lakebase JDBC watchlist read in a `try/except` with a fallback to the widget ticker list, printing the exception type rather than failing the run (`pipeline/market_pipeline_serverless.py:130-143`).

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `$gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `$gsd-debug` for investigation and bug fixing
- `$gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `$gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
