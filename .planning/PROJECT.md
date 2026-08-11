# Market Research Copilot — Frontend Elevation

## What This Is

Market Research Copilot is a working Databricks-native market research tool: a Spark pipeline ingests price bars and news, computes technical signals, and embeds article text into Lakebase (Postgres + pgvector); a Flask web app and a FastMCP tool server both read/write that same Lakebase data — one for a human via browser, one for an Agent Bricks agent. This milestone is a frontend-only elevation: take the existing, functioning (screenshot-verified) UI from a plain bordered-table look to a modern, portfolio-grade dashboard, without touching the backend contract.

## Core Value

The app must look and feel like a real product — a visual quality bar that holds up in a job-application portfolio — while every currently-working feature (watchlist, semantic search, news signals, research notes, agent reports) keeps working exactly as it does today.

## Requirements

### Validated

- ✓ Spark pipeline ingests Massive bars/news, computes technical features (returns, MA5/MA20, volatility, drawdown, volume z-score), embeds article chunks — existing
- ✓ Lakebase (Postgres + pgvector) serves as shared state for `watchlist`, `research_notes`, `analysis_reports`, `price_bars`, `ticker_metrics`, `news_price_signals`, embeddings — existing
- ✓ Flask app (`app/app.py`, `app/templates/index.html`) exposes watchlist CRUD, semantic search (`/api/search`), news signals, research notes, agent reports over REST — existing, verified live on Databricks Apps
- ✓ MCP server (`mcp_server/research_mcp_server.py`) exposes 10 read/write tools to an Agent Bricks agent over streamable HTTP — existing
- ✓ Agent Bricks agent writes research reports back into Lakebase (`analysis_reports`), visible in the human UI — existing, verified live

### Active

- [ ] Visual design system: typography, color, spacing, and component polish — move from plain bordered tables to a modern SaaS-dashboard aesthetic (cards, hierarchy, whitespace) — Linear/Vercel/Stripe-dashboard reference point
- [ ] Data visualization: charts/sparklines for price trends, volatility, and signals in the Watchlist and News Signals tabs, replacing raw-number-only tables
- [ ] Improved handling of missing/`N/A` data (most watchlist tickers currently show `N/A` for trend/vol/drawdown because the pipeline hasn't computed metrics for them yet) — visual treatment only, not a pipeline fix
- [ ] Preserve all 5 existing tabs and their current functionality: Watchlist, Semantic Search, News Signals, Research Notes, Agent Reports
- [ ] Loading/empty/error states for API calls (currently no visible loading feedback in the UI)

### Out of Scope

- Any change to Flask route behavior, request/response JSON shapes, or URL paths in `app/app.py` — the MCP server and any external consumer depend on the current contract
- Any change to the Spark pipeline, Lakebase schema, or Massive API client — explicitly working and verified live, not part of this milestone
- Full SPA rebuild (React/Vue) — rejected in favor of polishing the existing Flask-rendered vanilla-JS page; keeps the change explainable and low-risk to the working pipeline
- Authentication/authorization changes — MCP email-trust and Flask SSO-header trust are known, documented concerns (see `.planning/codebase/CONCERNS.md`) but out of scope for a frontend-only milestone
- New backend features (e.g., server-side chart data endpoints) — charts render from existing API responses only

## Context

- Portfolio/capstone project — built for job applications. Decisions should stay simple and defensible in an interview, per the user's standing preference.
- Current UI (verified live at `market-research-copilot-*.aws.databricksapps.com`) is a single server-rendered page (`app/templates/index.html`) with inline JS/CSS, 5 tabs, monospace/black-white styling, plain HTML tables with borders. Screenshots taken 2026-08-10 show it fully functional: watchlist with live metrics, semantic search returning ranked results with similarity scores, news-signals joined to price moves, research notes (human + agent authored), and agent-written analysis reports.
- Full architecture/stack/conventions/concerns already captured in `.planning/codebase/` (mapped 2026-08-10) — use as ground truth instead of re-deriving during planning.
- No test suite, no CI, no lint config exist in the repo (confirmed in `.planning/codebase/TESTING.md`) — frontend changes must be manually verified against the live app or local dev server, not against automated tests.
- `app/static/` currently has no tracked assets beyond `.DS_Store` — any new CSS/JS/chart-library assets are net-new additions there.

## Constraints

- **Tech stack**: No build step / bundler in this repo today (no `package.json`) — frontend work stays in plain HTML/CSS/JS served by Flask; a CDN-hosted charting library (e.g. Chart.js) is acceptable, no npm toolchain introduction.
- **Backend contract**: `app/app.py` route paths, request params, and JSON response shapes must not change unless a plan explicitly calls it out and confirms the MCP server / agent integration is unaffected.
- **Deployment**: Must keep working under Databricks Apps' single-process Flask dev-server deployment (`app/app.yaml`, `command: python app.py`) — no new runtime/process requirements.
- **Data reality**: Most watchlist tickers currently lack computed metrics (pipeline ran against a capped `max_tickers`) — the UI must degrade gracefully for missing data, not assume every row is fully populated.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Polish existing Flask/vanilla-JS page in place, not a framework rebuild | Lowest risk to a verified-working live app; stays simple and interview-explainable per standing portfolio-project preference | — Pending |
| Use a CDN-hosted charting library (e.g. Chart.js) rather than zero-dependency hand-rolled SVG | Faster to build richer chart types (sparklines, trend lines) without adding a build toolchain | — Pending |
| Treat visual design system and data visualization as equally weighted goals | User explicitly chose "both equally" over prioritizing one | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-10 after initialization*
