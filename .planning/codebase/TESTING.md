# Testing Patterns

**Analysis Date:** 2026-08-10

## Test Framework

**Runner:**
- None. There is no test runner configured anywhere in this repository — no `pytest`, `unittest`, `nose`, or `tox` setup.

**Assertion Library:**
- Not applicable — no tests exist.

**Run Commands:**
```bash
# No test command exists. Confirmed by:
#   - no *.test.* or *.spec.* files
#   - no tests/ or test/ directory
#   - pytest/unittest not listed in app/requirements.txt or mcp_server/requirements.txt
#   - no pytest.ini, pyproject.toml, tox.ini, or CI workflow referencing tests
```

## Test File Organization

**Location:** N/A — no test files exist anywhere in the repository (`app/`, `mcp_server/`, `pipeline/`, `sql/`, root).

**Naming:** N/A

**Structure:** N/A

## Test Structure

Not applicable. No suites, `describe`/`it` blocks, or `TestCase` classes are present.

## Mocking

**Framework:** None used or configured (no `unittest.mock`, `pytest-mock`, or `responses`/`vcrpy` for HTTP mocking despite the codebase making live calls to the Massive API and Databricks secrets).

**Patterns:** N/A

**What to Mock (if tests are added):**
- `MassiveClient` HTTP calls (`app/massive_client.py`, `mcp_server/massive_client.py`) — external API, rate-limited, should not be hit in tests.
- `databricks.sdk.WorkspaceClient().secrets.get_secret(...)` (`app/lakebase.py:19-28`, `app/massive_client.py:16-28`) — requires a live Databricks workspace context; both `app/lakebase.py` and `app/massive_client.py` construct `_w = WorkspaceClient()` at **module import time**, so any test importing these modules needs this call mocked or stubbed before import, not just before use.
- `psycopg2.connect` / `get_connection()` (`app/lakebase.py:31-38`) — real Postgres/Lakebase connection.
- `SentenceTransformer(...)` model loading in `_embed()` (`app/app.py:25-31`, `mcp_server/research_mcp_server.py:33-40`) — downloads/loads a real embedding model; lazily instantiated as a module-level singleton (`_model` global), which a test suite would need to reset between tests.

**What NOT to Mock (if tests are added):**
- Pure SQL-string-building logic and input-validation branches (e.g. ticker symbol validation in `app/app.py:78-79`, `mcp_server/research_mcp_server.py:233-235`) — these are plain Python and can be tested directly without any mocking.

## Fixtures and Factories

None exist. No `conftest.py`, no factory/builder helpers, no sample data files for tests.

## Coverage

**Requirements:** None enforced — no coverage tool (`coverage.py`, `pytest-cov`) is configured or referenced.

**View Coverage:**
```bash
# Not applicable — no coverage tooling present.
```

## Test Types

**Unit Tests:** None present. Candidates for future unit tests: validation logic in `app/app.py` route handlers, SQL-building branches in `app/app.py` (`search`, `signals`, `list_notes`) and `mcp_server/research_mcp_server.py` (`search_ticker_news`, `get_news_price_signals`, `get_research_notes`), and `chunk_text` / `lit` / helper functions in `pipeline/market_pipeline_serverless.py`.

**Integration Tests:** None present. The natural integration surface is Flask route → Lakebase Postgres round-trips (`app/app.py` + `app/lakebase.py`) and MCP tool → Lakebase round-trips (`mcp_server/research_mcp_server.py` + `mcp_server/lakebase.py`); both currently require a live Lakebase instance to exercise (`sql/01_schema.sql` defines the schema they depend on).

**E2E Tests:** Not used. Manual verification is the current practice: `/healthz` endpoint (`app/app.py:45-48`) provides a manual liveness/DB-connectivity check but is not wired into any automated test or CI health check.

## CI/CD

No CI configuration exists (no `.github/workflows/`, no `.gitlab-ci.yml`). Deployment is manual via Databricks Apps (`app/app.yaml`, `mcp_server/app.yaml`) and the Databricks notebook job definition (`pipeline/resources/market_pipeline_job.yml`); nothing runs tests as a deploy gate because there is nothing to run.

## Common Patterns

**Async Testing:** N/A — codebase is synchronous throughout (Flask sync routes, `requests` for HTTP, no `asyncio`).

**Error Testing:** N/A — no automated tests exercise error paths. Error paths that would benefit from tests if a suite is introduced: the global Flask exception handler (`app/app.py:39-42`), the rate-limit-tolerant watchlist-add path (`app/app.py:82-88`), and `run_returning`'s rollback-on-exception behavior (`app/lakebase.py:56-65`).

## Recommendation for Adding Tests

If a test suite is introduced, the natural entry points are:
1. `pytest` + `pytest-mock` (neither currently in `app/requirements.txt` or `mcp_server/requirements.txt` — would need adding)
2. Mock `WorkspaceClient` before importing `lakebase.py`/`massive_client.py`, since both instantiate it at module scope
3. Use Flask's `app.test_client()` for `app/app.py` route tests, patching `lakebase.run_query`/`run_write`/`run_returning` rather than hitting real Postgres
4. For `mcp_server/research_mcp_server.py`, call the underlying `@mcp.tool`-decorated functions directly (FastMCP tools remain plain callables) with `lakebase` functions patched

---

*Testing analysis: 2026-08-10*
