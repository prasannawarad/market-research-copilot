# Coding Conventions

**Analysis Date:** 2026-08-10

## Naming Patterns

**Files:**
- Lowercase snake_case module names: `app.py`, `lakebase.py`, `massive_client.py`, `research_mcp_server.py`, `setup_secrets.py`
- The three services (`app/`, `mcp_server/`, `pipeline/`) each own their own copy of shared helper modules (`lakebase.py`, `massive_client.py` are duplicated verbatim between `app/` and `mcp_server/` — see CONCERNS.md for the drift risk this creates)

**Functions:**
- snake_case throughout: `run_query`, `get_latest_price`, `flag_moves_since_last_visit`
- Private/internal helpers prefixed with a single underscore: `_embed`, `_user`, `_lakebase_url`, `_get_api_key`, `_json`, `_secret` (`pipeline/market_pipeline_serverless.py:73`)
- Route handlers and MCP tools use verb_noun naming that mirrors the HTTP/tool action: `get_watchlist`, `add_watchlist`, `remove_watchlist`, `add_to_watchlist`, `remove_from_watchlist`

**Variables:**
- snake_case for locals (`ticker`, `note_text`, `bar_date`)
- SCREAMING_SNAKE_CASE for module-level constants sourced from env or config, always with an inline default: `EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")` (`app/app.py:19`), `_SCOPE`, `_KEY`, `_BASE_URL` (`app/massive_client.py:18-20`)
- Databricks notebook widgets in `pipeline/market_pipeline_serverless.py` follow the same SCREAMING_SNAKE_CASE-from-widget pattern: `CATALOG`, `LOOKBACK_DAYS`, `MAX_RPM` (`pipeline/market_pipeline_serverless.py:41-51`)

**Types:**
- No custom classes beyond `MassiveClient` (`app/massive_client.py:31`) and Flask app/MCP server instances. Type hints use built-in generics (`list[dict]`, `dict[str, Any]`, `tuple | dict | None`) — Python 3.10+ union syntax, no `typing.Optional`/`typing.List`.

## Code Style

**Formatting:**
- No formatter config present (no `.prettierrc`, `pyproject.toml`, `black` config, or `ruff.toml`). Style is consistent by hand: 4-space indentation, double-quoted strings, trailing commas in multi-line calls.
- Section dividers use a recurring comment banner to group related routes/tools:
  ```python
  # ── Watchlist ──────────────────────────────────────────────────────────────
  ```
  Seen in both `app/app.py` (Watchlist, Metrics and signals, Semantic search, Research notes and agent reports, Pipeline stats) and `mcp_server/research_mcp_server.py` (Read tools, Write tools).

**Linting:**
- No `.eslintrc`, `ruff.toml`, `.flake8`, or `pyproject.toml` lint config found anywhere in the repo. No lint step is enforced.
- One `# noqa: BLE001` suppression comment appears for an intentionally broad `except Exception` (`app/app.py:87`), implying the author lints locally with `ruff`/`flake8` even though no config is committed — do not assume a lint gate exists in CI (there is no CI, see below).

## Import Organization

**Order:**
1. Standard library (`json`, `os`, `base64`, `datetime`)
2. Third-party packages (`flask`, `psycopg2`, `requests`, `sqlalchemy`, `databricks.sdk`, `fastmcp`)
3. Local/sibling modules (`from lakebase import run_query, run_returning, run_write`, `from massive_client import MassiveClient`)

Blank line between each group; alphabetized within a group is not strictly enforced but generally followed.

**Path Aliases:**
- None. Each service directory (`app/`, `mcp_server/`) is flat and imports siblings directly by module name (`from lakebase import ...`), relying on the process working directory rather than a package/`src` layout.

## Error Handling

**Patterns:**
- Flask app registers one global handler that logs and returns JSON 500s: `@app.errorhandler(Exception)` → `app.logger.exception("request failed")` → `jsonify({"error": str(err)}), 500` (`app/app.py:39-42`). Individual routes generally do not use try/except; they let unexpected errors bubble to this handler.
- Deliberate exceptions to that rule are narrow and explained: `app/app.py:82-88` wraps a price lookup in `try/except Exception as exc` specifically so a rate-limited third-party call cannot block adding a ticker to the watchlist, logging a warning instead of failing the request.
- Input validation is manual and inline at the top of each write route/tool, returning a 400 (Flask) or an `{"ok": False, "error": ...}` payload (MCP), e.g. `app/app.py:78-79`, `mcp_server/research_mcp_server.py:233-235`.
- Database writes that need atomicity wrap the cursor call in `try/except Exception: conn.rollback(); raise` before re-raising to the caller — see `run_returning` in `app/lakebase.py:56-65`. Plain `run_write` does not roll back on error (no try/except around its commit).
- JSON parsing failures are caught narrowly with `json.JSONDecodeError`, not bare `except`: `app/app.py:230-233`, `mcp_server/research_mcp_server.py:287-289`.
- The Spark pipeline (`pipeline/market_pipeline_serverless.py`) implements its own retry loop for HTTP calls: `massive_get(path, params=None, _retries=2)` (`pipeline/market_pipeline_serverless.py:179`) rather than using a library like `tenacity`.

## Logging

**Framework:** Flask's built-in `app.logger` (stdlib `logging` under the hood). MCP server and pipeline have no explicit logging framework — the pipeline notebook relies on cell output/print statements characteristic of Databricks notebooks.

**Patterns:**
- Use `app.logger.exception(...)` for unexpected errors so the traceback is captured (`app/app.py:41`).
- Use `app.logger.warning(...)` with an f-string-free, `%s`-style format for expected-but-notable failures: `app.logger.warning("price lookup failed for %s: %s", symbol, exc)` (`app/app.py:88`).

## Comments

**When to Comment:**
- Module docstrings on every file explain *why* the module exists and any non-obvious constraint (e.g. why Lakebase auth uses one URL secret instead of five vars — `app/lakebase.py:1-8`; why the pipeline only runs on the driver — `pipeline/market_pipeline_serverless.py:1-19`).
- Function docstrings favor one-line summaries; multi-line docstrings are reserved for functions with non-obvious behavior or contracts callers must know (e.g. `massive_client.py:78-87` explains why `get_latest_price` avoids pagination; `research_mcp_server.py:283-284` explains that the `email` MCP arg is not trusted for ownership).
- Inline comments are used sparingly, mostly to flag security/trust boundaries (`# a rate-limited quote must not block the add`, `# Databricks Apps forwards the signed-in user in this header.`) or explain a non-obvious SQL/logic choice.

**JSDoc/TSDoc:** N/A (Python-only codebase). No `sphinx`/`mkdocs` docstring convention is enforced (no type-annotated docstring params, no `:param:`/`:return:` blocks) — docstrings are prose, not structured.

## Function Design

**Size:** Small and single-purpose; Flask routes and MCP tools are typically 5-25 lines including their SQL. The largest functions live in the Spark pipeline (`market_pipeline_serverless.py`), which trades small functions for large embedded notebook cells — expect 50-150 line blocks there.

**Parameters:** Optional filters use empty-string defaults rather than `None` so callers (especially MCP tool callers, which pass string args) don't need to special-case `None`, e.g. `def search_ticker_news(query: str, ticker: str = "", limit: int = 5)`. Optional email/user context flows through as `email: str = ""` with a fallback to `DEFAULT_EMAIL` at the point of use (`mcp_server/research_mcp_server.py:165`, `:178`, `:240`).

**Return Values:** Flask routes always return `jsonify(...)` (optionally with a status code tuple). MCP tools always return a JSON-encoded string via `_json(obj)` (`mcp_server/research_mcp_server.py:43-44`), never raw Python objects — this is required by the MCP tool contract, which expects string content.

## Module Design

**Exports:** No `__all__` lists or explicit export control; every top-level `def`/class is implicitly public. Modules are treated as small toolkits imported wholesale (`from lakebase import run_query, run_returning, run_write`).

**Barrel Files:** None — no `__init__.py` re-export layer; each service directory is a flat set of scripts, not an installable package.

## Databricks/Notebook-Specific Conventions

- `pipeline/market_pipeline_serverless.py` is a Databricks notebook exported as a `.py` file with `# COMMAND ----------` cell markers and `# DBTITLE` cell titles — treat it as notebook source, not a conventional importable module. Config comes from `dbutils.widgets` rather than argparse/env vars.
- Secrets are never read from `.env` in the app/mcp_server services; they are fetched at runtime via `WorkspaceClient().secrets.get_secret(scope=..., key=...)` and base64-decoded (`app/lakebase.py:25-28`, `app/massive_client.py:25-28`). `.env` is used only for local dev overrides (see `.env.example`).

---

*Convention analysis: 2026-08-10*
