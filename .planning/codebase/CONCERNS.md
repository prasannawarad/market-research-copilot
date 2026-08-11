# Codebase Concerns

**Analysis Date:** 2026-08-10

## Tech Debt

**Byte-identical duplicated modules between `app/` and `mcp_server/`:**
- Issue: `app/lakebase.py` / `mcp_server/lakebase.py` and `app/massive_client.py` / `mcp_server/massive_client.py` are exact duplicates (confirmed via `diff`, zero output). Any bug fix, secret-scope rename, or retry-logic change made in one copy silently does not propagate to the other.
- Files: `app/lakebase.py`, `mcp_server/lakebase.py`, `app/massive_client.py`, `mcp_server/massive_client.py`
- Impact: Two Databricks Apps (`app/`, `mcp_server/`) can drift out of sync on connection handling, retry behavior, or secret scope/key names without any signal.
- Fix approach: Extract a shared internal package (e.g. `shared/lakebase.py`, `shared/massive_client.py`) and have both apps import it, or symlink one into the other's directory at deploy time. Given both are deployed independently as Databricks Apps with separate `requirements.txt`, a small installable package (`pip install -e ./shared`) is the cleanest fix.

**Manual, non-automated Lakebase load step despite a scheduled job:**
- Issue: `pipeline/resources/market_pipeline_job.yml` schedules `market_pipeline_serverless.py` to run weekdays at 18:30 UTC, but section 8 of the notebook (`pipeline/market_pipeline_serverless.py:488-585`) only *writes a SQL file* to a UC Volume (`lakebase_load.sql`) — actually loading Lakebase requires a human to open the Catalog, download the file, paste it into the Lakebase SQL editor, and run it.
- Files: `pipeline/market_pipeline_serverless.py:488-585`, `pipeline/resources/market_pipeline_job.yml`
- Impact: The scheduled job does not keep Lakebase (and therefore the app/MCP server, which only read from Lakebase) up to date unless someone manually completes the paste-and-run step every time it fires. This is explained as a serverless limitation (JDBC/`psycopg2`/`foreachPartition` writes are all blocked) but the job config gives the false impression of a fully automated pipeline.
- Fix approach: Either add a second lightweight job/task (a plain Python job cluster or a workflow step outside serverless) that runs `psycopg2`/JDBC against Lakebase directly, or add a Databricks SQL Warehouse task to the job that executes the generated file automatically instead of relying on manual copy-paste.

**Job cluster config contradicts the pipeline's own "serverless only" premise:**
- Issue: `pipeline/resources/market_pipeline_job.yml:30-36` defines `job_clusters` with `new_cluster` (`node_type_id: i3.xlarge`, `num_workers: 2`), i.e. a provisioned cluster — but the notebook's header explicitly says "serverless is the only compute available" and every design decision (no `.cache()`, driver-only network calls, staged model in a Volume) follows from that constraint.
- Files: `pipeline/resources/market_pipeline_job.yml:30-36`
- Impact: If this job definition is the one actually deployed, the pipeline runs on a classic cluster where the serverless workarounds are unnecessary overhead; if it's stale/aspirational, it's misleading to anyone reading the repo to understand the deployed architecture.
- Fix approach: Align the job YAML with actual deployment target — use `serverless: true` / no `job_clusters` block if serverless, or delete the "serverless only" framing from the notebook docstring if a classic cluster is actually used.

**Global lazy-loaded embedding model without thread safety:**
- Issue: `_embed()` in both `app/app.py:25-31` and `mcp_server/research_mcp_server.py:33-40` lazily initializes a module-level `_model` global on first call with no lock. Flask (multi-threaded by default) and FastMCP (async/streamable-HTTP, potentially concurrent requests) can both trigger concurrent first-calls.
- Files: `app/app.py:22-31`, `mcp_server/research_mcp_server.py:30-40`
- Impact: Concurrent cold-start requests can race to construct `SentenceTransformer` simultaneously, wasting memory/CPU or (depending on the underlying library's thread-safety) risking a corrupted partial-init object being read by another thread.
- Fix approach: Initialize the model at process startup (module import time) instead of lazily, or guard the lazy-init with a `threading.Lock`.

**`WorkspaceClient()` instantiated at import time:**
- Issue: `lakebase.py:19` (`_w = WorkspaceClient()`) runs Databricks SDK auth resolution as a side effect of importing the module, in both `app/lakebase.py` and `mcp_server/lakebase.py`.
- Files: `app/lakebase.py:19`, `mcp_server/lakebase.py:19`
- Impact: Makes the module impossible to import (let alone unit test) outside a Databricks Apps runtime or without valid Databricks credentials in the environment — there is no way to import `app.py` for a local test without live Databricks auth succeeding.
- Fix approach: Defer `WorkspaceClient()` construction into `_lakebase_url()` (lazy singleton) so the module is importable without credentials present.

## Known Bugs

**None identified.** No open bug reports, no `TODO`/`FIXME`/`HACK`/`XXX` markers exist anywhere in the Python source (`grep` across the repo returned zero matches).

## Security Considerations

**MCP write/read tools trust a caller-supplied `email` argument for identity, with no authentication:**
- Risk: Every MCP tool that touches per-user data (`get_watchlist`, `get_research_notes`, `flag_moves_since_last_visit`, `add_to_watchlist`, `remove_from_watchlist`, `save_research_note`) accepts `email: str = ""` as a plain parameter and uses it directly as the row owner (`mcp_server/research_mcp_server.py:161-268`). Any agent (or anyone able to reach the MCP endpoint) can pass an arbitrary email string and read or mutate another user's watchlist, notes, or visit timestamp — there is no session/auth binding between the MCP transport and the `email` value.
- Files: `mcp_server/research_mcp_server.py:160-268`
- Current mitigation: `save_analysis_report` (`mcp_server/research_mcp_server.py:270-306`) explicitly ignores the caller-supplied `email` and hardcodes `DEFAULT_EMAIL`, with a comment noting "not trusted for ownership" — proving the author is aware of the risk for that one tool but did not apply the same fix to the other five tools that accept `email`.
- Recommendations: Either derive identity server-side (e.g. from the MCP transport's authenticated session, mirroring how `app/app.py:34-36` reads `X-Forwarded-Email` from Databricks Apps' own auth header) for every tool, or explicitly document that this MCP server is single-tenant/demo-only and the `email` parameter is a convenience field, not an authorization boundary. Given the capstone context (all data belongs to one demo user), this is lower real-world risk today but is a genuine multi-tenant vulnerability if the pattern is reused.

**Raw exception messages returned to HTTP clients:**
- Risk: `app/app.py:39-42` (`handle_exception`) returns `str(err)` directly in the JSON error body for any unhandled exception, including database driver errors (which can include connection strings, table/column names, or query fragments from `psycopg2`).
- Files: `app/app.py:39-42`
- Current mitigation: None — this is the default 500 handler for the whole Flask app.
- Recommendations: Log the full exception server-side (already done via `app.logger.exception`) but return a generic message to the client; reserve detail for logs only.

**Manual SQL string construction in the pipeline's Lakebase loader:**
- Risk: `pipeline/market_pipeline_serverless.py:507-517` (`lit()`) hand-builds SQL literals via string formatting and manual quote-escaping (`str(v).replace("'", "''")`) rather than using parameterized queries, because the write path can't use `psycopg2`/JDBC on serverless (see Tech Debt above).
- Files: `pipeline/market_pipeline_serverless.py:507-546`
- Current mitigation: All values originate from the Massive API (a trusted third-party feed) rather than user input, and single-quote escaping is applied consistently. No SQL injection path from an end user exists today.
- Recommendations: If any field sourced from user input (e.g. a future watchlist-driven ticker filter) is ever threaded into `emit()`/`lit()`, treat it as untrusted before it reaches this code path. Today the risk is latent, not exploitable.

**No rate limiting / abuse protection on Flask or MCP endpoints:**
- Risk: `/api/search`, `/api/watchlist` (POST), and the MCP write tools have no per-user or per-IP rate limiting. `add_watchlist` (`app/app.py:75-98`) calls `MassiveClient()` synchronously per request with no caching, so a scripted burst of requests could exhaust the Massive free-tier quota (5 req/min, called out in `README.md` and the pipeline notebook) shared by the ingestion pipeline.
- Files: `app/app.py:75-98`, `mcp_server/research_mcp_server.py`
- Current mitigation: None.
- Recommendations: Low priority for a portfolio/demo project; note if productionizing.

## Performance Bottlenecks

**Per-request embedding model inference with no batching or caching:**
- Problem: `/api/search` (`app/app.py:147-171`) and `search_ticker_news` (`mcp_server/research_mcp_server.py:49-77`) call `SentenceTransformer.encode()` synchronously on every request with a single-item batch (`[text]`), on whatever CPU the Databricks App container has. No query-embedding cache exists even for repeated identical searches.
- Files: `app/app.py:25-31,147-171`, `mcp_server/research_mcp_server.py:33-40,49-77`
- Cause: Model inference is on the hot path with no memoization layer.
- Improvement path: Cache embeddings for repeated/recent queries (e.g. an LRU cache keyed on normalized query text), or move to a hosted embedding endpoint if latency becomes an issue at higher traffic.

**Massive API ingestion throttled to 5 requests/minute, hard-capped to `max_tickers` (default 3):**
- Problem: `pipeline/market_pipeline_serverless.py:171-181` deliberately caps the ticker universe (`TICKERS = TICKERS[:MAX_TICKERS]`) because the free-tier Massive API allows only 5 req/min, costing ~24s of throttle per ticker.
- Files: `pipeline/market_pipeline_serverless.py:150-181`
- Cause: External API rate limit on the free tier, not a code inefficiency.
- Improvement path: This is by design and documented in `README.md` ("the Massive free tier is 5 requests/minute, so ingest is throttled on purpose"). Upgrading the Massive plan is the only path to a larger ticker universe; not a bug.

## Fragile Areas

**Fallback ticker-universe read from Lakebase inside the Spark pipeline:**
- Files: `pipeline/market_pipeline_serverless.py:118-138`
- Why fragile: The pipeline attempts a Spark JDBC read against Lakebase to derive the ticker universe from the `watchlist` table, wrapped in a bare `except Exception as e` that silently falls back to the widget-supplied ticker list on *any* failure (auth error, network error, schema drift, malformed rows). A schema change to `watchlist` (e.g. renaming `symbol`) would silently degrade to the fallback list rather than failing loudly.
- Safe modification: Any change to the `watchlist` table schema must be tested against this JDBC read path specifically (not just the pgvector app path), since a silent except swallows regressions.
- Test coverage: None — no automated tests exist for this or any other part of the pipeline (see Test Coverage Gaps).

**Two independent embedding paths in the pipeline (distributed pandas UDF + driver fallback):**
- Files: `pipeline/market_pipeline_serverless.py:460-475`
- Why fragile: If the distributed pandas UDF embedding write fails for any reason, the pipeline catches the exception and falls back to embedding the entire chunk set on the driver via `.toPandas()` (`pipeline/market_pipeline_serverless.py:464-475`), which could exhaust driver memory for a large chunk set and defeats the stated purpose of using a pandas UDF ("Spark requirement" per the notebook's own docstring).
- Safe modification: Any change to chunk volume or embedding dimensionality should be checked against driver-side OOM risk in the fallback path, since it has no size guard.
- Test coverage: None.

**Notebook-as-script pipeline has no unit-testable functions:**
- Files: `pipeline/market_pipeline_serverless.py` (entire 611-line file)
- Why fragile: The whole pipeline is written as a linear sequence of Databricks notebook cells (`# COMMAND ----------` delimited) operating on module-level globals (`TICKERS`, `bars`, `metrics`, `news`, `signals`, `emb`), not as importable/testable functions. Any change requires a full manual "Run All" against a live Databricks workspace with real secrets and a real Massive API key to verify.
- Safe modification: Changes should be smoke-tested end-to-end in a workspace before merging; there is no way to unit-test the window-function logic, the join, or the chunking logic in isolation today.
- Test coverage: None.

## Scaling Limits

**Generated SQL load file size:**
- Current capacity: The pipeline itself warns at >2MB (`pipeline/market_pipeline_serverless.py:583-585`, "the SQL editor may struggle. Split on the '-- table:' comments").
- Limit: With `MAX_TICKERS` capped at 3 and `NEWS_LIMIT` at 10 articles/ticker by default, current runs are well under this, but raising `max_tickers` (as the README suggests: "Raise max_tickers once you are not against a deadline") without also revisiting the manual paste-and-run Lakebase load step compounds the automation gap noted under Tech Debt.
- Scaling path: Automate the Lakebase load (see Tech Debt fix) before raising ticker/article limits meaningfully.

## Dependencies at Risk

**`sentence-transformers` and Hugging Face model download require workaround staging:**
- Risk: `pipeline/market_pipeline_serverless.py:88-107` requires manually staging the embedding model into a UC Volume because Databricks serverless executors have a read-only filesystem and no outbound internet, and `os.environ["HF_HUB_DISABLE_XET"]` is explicitly set to work around an Xet-cache crash on read-only filesystems (comment: "xet cache is what blows up on read-only FS"). This is a workaround for current `huggingface_hub`/`sentence-transformers` internals, not a stable public API contract.
- Impact: A future `sentence-transformers`/`huggingface_hub` release changing cache behavior could silently break model staging on Databricks Free Edition serverless.
- Migration plan: Pin `sentence-transformers` and its `huggingface_hub` dependency to known-working versions in `requirements.txt` (currently `sentence-transformers>=2.2.0` is unbounded above) rather than allowing floating upgrades.

**No dependency pinning (all `requirements.txt` entries use `>=`):**
- Risk: Both `app/requirements.txt` and `mcp_server/requirements.txt` pin every dependency with `>=` only (e.g. `databricks-sdk>=0.30.0`, `sentence-transformers>=2.2.0`), so a fresh deploy can silently pull a newer, potentially breaking major version.
- Impact: A deploy today could behave differently than a deploy next month with identical source code, with no lockfile to diff against.
- Migration plan: Add upper bounds or a lockfile (`pip-compile`/`uv pip compile`) per app, especially given the fragile HF staging workaround above.

## Missing Critical Features

**No local/offline development path:**
- Problem: `WorkspaceClient()` at import time (see Tech Debt) and `dbutils`/`spark` globals used directly in the pipeline notebook mean neither the Flask app, the MCP server, nor the pipeline can be exercised locally without a live Databricks workspace, valid secrets, and (for the pipeline) a Databricks cluster/serverless compute. There's a `.env.example` present, suggesting local env-var-based config was at least partially intended, but the actual code path (`WorkspaceClient().secrets.get_secret(...)`) doesn't read from `.env` at all — it always calls the Databricks Secrets API.
- Blocks: Any local iteration on `app.py`/`research_mcp_server.py` logic without deploying to a Databricks App first.

## Test Coverage Gaps

**No test suite exists anywhere in the repository:**
- What's not tested: Every code path — the Flask routes in `app/app.py`, all 10 MCP tools in `mcp_server/research_mcp_server.py`, and the entire Spark pipeline in `pipeline/market_pipeline_serverless.py`. `find . -iname "*test*"` across the repo returns nothing, and `.gitignore` even lists `.pytest_cache/` despite no pytest config or test files existing.
- Files: entire repository
- Risk: Any refactor (e.g. deduplicating `lakebase.py`, fixing the MCP email-trust issue, or changing the pipeline's window-function logic) has no automated safety net; correctness relies entirely on manual end-to-end verification in a live Databricks workspace.
- Priority: Medium — reasonable for a capstone/portfolio project scored on feature completeness, but worth calling out explicitly (per this project's own CLAUDE.md convention of documenting "no test suite" rather than leaving it undiscovered) if this repo is extended further.

---

*Concerns audit: 2026-08-10*
