# Project Research Summary

**Project:** Market Research Copilot — Frontend Elevation
**Domain:** No-build-step, Flask-rendered financial/market-research dashboard (frontend-only redesign)
**Researched:** 2026-08-10
**Confidence:** MEDIUM-HIGH (architecture and pitfalls are HIGH confidence, verified directly against this codebase; stack and features are MEDIUM confidence, cross-checked web sources)

## Executive Summary

This milestone is a pure presentation-layer elevation of a working, live-verified Flask + vanilla-JS dashboard (5 tabs: Watchlist, Semantic Search, News Signals, Research Notes, Agent Reports) — not a new feature or a framework rebuild. The right way to build this, per both the explicit project constraints and cross-checked industry research, is to stay entirely in native web platform technology: two CDN-hosted, permissively-licensed charting libraries (`lightweight-charts` for financial trend/detail views, `Chart.js` for table-row sparklines), native CSS (nesting, custom properties, container queries — all Baseline "Widely Available" now, so no preprocessor is needed), and a light restructuring of the current single-file inline `<script>`/`<style>` into `app/static/{css,js}/` split by concern (design tokens → layout → components; `api.js` for data access, `components/*.js` for reusable render functions, `tabs/*.js` for per-tab orchestration). No bundler, no framework, no backend change — this is the only approach consistent with the project's "no build step, backend contract locked" constraints and the "explainable in an interview" standing preference.

The feature research confirms this app is already closer to "table stakes" than it looks — right-aligned tabular numerals, consistent up/down color coding, and a shared `.tag` badge component already exist in the codebase. The elevation work is concentrated in exactly the gaps `PROJECT.md` already names: graceful missing-data treatment (most watchlist rows currently show raw `N/A`), loading/empty/error states (currently absent on every tab), and data visualization (watchlist sparklines and a possible ticker-detail chart) — all of which are achievable using data the existing `/api/*` endpoints already return, with zero new backend surface.

The dominant risk is not technical difficulty but regression: because there is no test suite, no CI, and no framework enforcing markup-to-behavior contracts, a "just visual" pass can silently break the app by (1) restructuring the `<script>` block into a module/IIFE and un-exposing the six global functions every inline `onclick="..."` depends on, (2) renaming a DOM ID/class that dozens of `document.querySelector('#...')` calls key off of, or (3) reaching for a not-yet-existing bulk backend endpoint to make a chart "easier," which violates the hard backend-lock constraint. All three are cheap to prevent (explicit UAT checks, ID/handler diffing, and "phase plan must enumerate exact source endpoints per chart") but easy to miss without deliberate process — this is the single most important thing the roadmap must build in as a recurring, cross-phase guardrail rather than a one-time check.

## Key Findings

### Recommended Stack

No `npm`/bundler; add two pinned, SRI-hashed CDN `<script>` tags: `lightweight-charts@5.2.0` (financial-grade trend/detail charts, Apache-2.0, ~45KB) and `chart.js@4.5.0` (general-purpose sparklines/small multiples, MIT, batteries-included). Both are recommended over ApexCharts (heavier, weaker financial-chart affordances), uPlot (lower-level API, slower to reach "polished SaaS" look), D3 (toolkit not chart library — too much hand-rolled work), and Highcharts (commercial-license risk for a public portfolio deployment). Styling uses native CSS nesting/custom-properties/`@property`/container queries — all Baseline "Widely Available" as of 2025/2026 — explicitly rejecting Tailwind's CDN/Play build (marked dev-only by Tailwind's own docs). State management stays plain `fetch()` + template literals; Alpine.js is explicitly deferred (not needed at this milestone's interactivity level).

**Core technologies:**
- `lightweight-charts@5.2.0` (CDN, jsDelivr): financial trend/ticker-detail charts — purpose-built OHLC/line financial charting, zero dependencies, interview-recognizable ("the TradingView library")
- `chart.js@4.5.0` (CDN, jsDelivr): table-row sparklines and small multiples — most widely documented sparkline-in-table pattern, well-trodden config
- Native CSS (nesting, custom properties, container queries): design tokens + responsive layout — Baseline-safe, no preprocessor, keeps the "no build step" constraint intact

### Expected Features

This is a presentation-elevation milestone, not new capability — "features" means richer presentation of existing data.

**Must have (table stakes):**
- Graceful missing-data treatment (muted dash/pending microcopy, not raw `N/A` text) — the current dominant data reality
- Loading/empty/error states on all 5 tabs — currently entirely absent
- One consistently extended `.tag` badge component across trend/signal-strength/sentiment/similarity-tier/author badges — avoid a second visual vocabulary
- Watchlist sparklines (or minimal inline trend) — the explicit "data visualization" requirement, achievable from existing `/api/metrics/<ticker>` data
- Qualitative similarity-tier badge alongside the existing raw similarity float (don't lead with a raw number)
- Visual (not just textual) distinction between human- and agent-authored notes/reports

**Should have (competitive differentiators):**
- Ticker-detail drill-down chart replacing/augmenting the existing 20-row detail table
- KPI stat-tile secondary delta/context lines (e.g. "183 metrics · 12 tickers scored")
- Signal-strength badge visual-weight gradient (filled/outlined/intensity dot, not just flat color)

**Defer / explicitly rejected (anti-features):**
- Full multi-panel candlestick/technical-indicator charting — over-scoped for a data-sparse demo dataset
- Real-time/live-updating prices (polling/websockets) — dishonest against a batch pipeline, explicitly out of scope
- Auto-refresh/background polling across tabs — adds failure surface with no data-freshness benefit
- Heavy AI-disclaimer banners — wrong weight for an internal tool where the user added the agent themselves; quiet badge convention is correct
- "Hero" oversized KPI cards with fake trend history — the 5 stat-strip metrics are pipeline-health counters, not business KPIs with time-series backing

### Architecture Approach

Split the current single-file inline `<script>`/`<style>` `index.html` into `app/static/css/{tokens,layout,components}.css` and `app/static/js/{main.js, api.js, components/*.js, tabs/*.js}`, loaded via one `<script type="module" src=".../main.js">` tag. `api.js` is the sole module allowed to call `fetch()` against `/api/*` (auditable backend-contract boundary); `components/*.js` holds pure render functions (`table.js`, `chart.js`, `tag.js`, `statTile.js`, `states.js`) taking data in and returning markup/DOM out, reused across tabs; `tabs/*.js` mirrors the existing per-tab `load*()` functions 1:1 (low-risk, mechanical port). Tab switching stays direct function calls (no pub/sub, no state library) — matches the existing, working pattern exactly and is the only approach that stays "explainable in an interview" at this scale (5 tabs, no cross-tab live sync requirement).

**Major components:**
1. `index.html` (Jinja shell) — head links, tab nav, 5 empty mount `<div>`s, one module `<script>` tag; no more inline logic
2. `main.js` + `api.js` — app bootstrap/tab-switch wiring, and the single fetch-wrapper boundary against the locked Flask `/api/*` contract
3. `components/*.js` — reusable presentational render functions (table, chart mount/destroy, tag/badge, stat tile, loading/empty/error states)
4. `tabs/*.js` — one file per tab, orchestrates fetch → render for that tab's mount point only

### Critical Pitfalls

1. **Restructuring `<script>` scope (module/IIFE) silently breaks every inline `onclick="..."` handler** — six global functions (`addSymbol`, `removeSymbol`, `showDetail`, `runSearch`, `loadSignals`, `delNote`) currently rely on classic-script global scope; switching to `type="module"` un-exposes them with no visible error until a button is clicked. Avoid by either keeping the script classic-scoped or replacing every inline `onclick` with `addEventListener` wiring in the same edit.
2. **Renaming DOM IDs, the `.hide` class, or `data-view` attributes breaks tab switching and all `$('#...')` lookups** — there is no framework binding, only string-based DOM queries; treat every referenced ID/class as a fixed contract this milestone, diff the ID list before/after any markup pass.
3. **A chart needing a data shape the current API doesn't return tempts an unplanned backend change** — e.g. watchlist sparklines need a time series but `/api/watchlist` only returns a snapshot; the backend-safe answer is N calls to the existing per-ticker `/api/metrics/<ticker>?days=N` endpoint, not a new bulk route. Every phase plan must enumerate its exact source endpoint(s)/field(s) before implementation.
4. **Unpinned/no-SRI CDN chart library becomes a silent single point of failure** — pin exact versions in the CDN URL (the only "lockfile" this repo has), add SRI + `crossorigin`, and guard chart-mount code so a CDN outage degrades to "no chart" rather than a page-breaking JS error.
5. **Stale cached static assets after a Databricks Apps deploy** — Flask's `url_for('static', ...)` doesn't cache-bust automatically; append a manual `?v=` query string bumped per deploy, and verify the first `app/static/` asset round-trips correctly (hard refresh/incognito + direct URL hit) before relying on the pattern for later phases.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Static Asset Restructure + Design System Foundation
**Rationale:** Everything else (charts, badges, states) needs a place to live and a safe migration path off the current inline `<script>`/`<style>` block; this is also where Pitfalls 1, 2, and 5 are highest-risk and must be explicitly guarded, so it should be isolated and fully UAT'd before any visual/feature work lands on top of it.
**Delivers:** `app/static/css/{tokens,layout,components}.css` and `app/static/js/{main.js,api.js,components/*.js,tabs/*.js}` extracted from `index.html`, functionally identical to today (same IDs, same global handler exposure or explicit `addEventListener` re-wiring), first cache-busting (`?v=`) convention verified against a real deploy.
**Addresses:** Shared `.tag` badge component consolidation (table-stakes), sets up the render-function split needed for sparklines/charts.
**Avoids:** Pitfall 1 (broken onclick handlers), Pitfall 2 (renamed IDs breaking tab switching), Pitfall 5 (stale cached assets) — all three are cheapest to catch here, before other phases build on top of this structure.

### Phase 2: Missing-Data Treatment + Loading/Empty/Error States
**Rationale:** These are pure-frontend, zero-new-dependency, explicitly named as "Active" requirements in PROJECT.md, and have the highest "looks unfinished" visual impact per user of any single change — should land before charts so chart empty-states can reuse the same pattern.
**Delivers:** Consistent muted dash/pending microcopy replacing raw `N/A`; loading/empty/error UI applied uniformly across all 5 tabs' `load*()` functions.
**Addresses:** Table-stakes features — graceful missing-data treatment, loading/empty/error states (FEATURES.md P1 items).
**Uses:** `components/states.js` and the extended `components/table.js` from Phase 1.

### Phase 3: Data Visualization (Sparklines + Ticker Detail Chart)
**Rationale:** Highest-complexity, highest-risk phase (introduces two new CDN dependencies, N+1 fetch pattern, canvas lifecycle management) — sequenced after the design-system foundation and empty-state patterns exist so charts can reuse both (chart-load-failure UX, missing-data placeholder rendering).
**Delivers:** Watchlist row sparklines (Chart.js, via existing `/api/metrics/<ticker>?days=N`), optionally a ticker-detail line/area chart (lightweight-charts, same endpoint, larger view), both with graceful degradation for `N/A` rows.
**Addresses:** Data visualization requirement (PROJECT.md Active), Watchlist sparklines + ticker-detail chart differentiators (FEATURES.md).
**Avoids:** Pitfall 3 (backend scope creep — must map each chart to an existing endpoint before implementation, verify `git diff --stat app/app.py app/lakebase.py mcp_server/*` is empty), Pitfall 4 (unpinned/no-SRI CDN dependency — pin + SRI both libraries here).

### Phase 4: Badge/Signal Polish + Human-vs-Agent Visual Distinction
**Rationale:** Lower risk, lower complexity, pure extension of the Phase 1 `.tag` component and Phase 2 state patterns — sequenced last as refinement once the structural/data-viz risk is retired, and easiest to descope/timebox if the milestone runs long.
**Delivers:** Similarity-tier badge (qualitative + raw score), signal-strength visual-weight gradient, agent-vs-human card treatment (left border/model-name prominence) on Notes/Reports tabs, optional KPI stat-tile secondary delta lines.
**Addresses:** Remaining FEATURES.md P1/P2 differentiators (similarity tier, author distinction) and P2 polish items (KPI deltas, strength gradient).

### Phase Ordering Rationale

- Structural/foundation work (Phase 1) must precede all visual/feature phases because it is the riskiest to retrofit later (moving IDs/handlers after other phases have built on top of them multiplies the blast radius of Pitfalls 1–2).
- Missing-data + loading-state patterns (Phase 2) are sequenced before charts (Phase 3) because charts need the same "how do we show absence gracefully" pattern — building it once and reusing it avoids two divergent empty-state implementations (PITFALLS.md UX section explicitly warns against inconsistent per-tab loading treatment).
- Data visualization (Phase 3) is isolated as its own phase because it is the only phase introducing new external dependencies (CDN libraries) and the only phase where backend-scope-creep (Pitfall 3) is a live risk — keeping it separate makes the "zero backend diff" verification (`git diff --stat`) a clean per-phase gate.
- Badge/polish work (Phase 4) is sequenced last because it's the lowest-risk, highest-flexibility phase — first to cut if the milestone timebox is tight, since PROJECT.md's Active requirements are already satisfied by Phases 1–3.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Data Visualization):** Needs a `--research-phase` pass to confirm exact lightweight-charts v5.x API shape (chainable API differs materially from older v3/v4 tutorials still circulating), verify current pinned versions against `chartjs.org`/`tradingview.github.io/lightweight-charts/docs` directly (STACK.md flags this as not yet spot-checked against official docs), and enumerate the exact endpoint/field mapping for each planned chart before implementation (per Pitfall 3's explicit prevention step).

Phases with standard patterns (skip research-phase):
- **Phase 1 (Static Asset Restructure):** Native ES modules + Flask static serving is a well-documented, standard web-platform pattern; the codebase-specific pitfalls (onclick/ID contracts) are already fully enumerated in PITFALLS.md.
- **Phase 2 (Missing-Data + Loading States):** Pure frontend JS/CSS around existing `fetch()` calls, no new libraries or APIs — implementation guidance is already complete in FEATURES.md and PITFALLS.md.
- **Phase 4 (Badge Polish):** Extends an already-existing `.tag` component with well-understood CSS/markup patterns — no new technical unknowns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Web-searched and cross-checked across 2-3 independent sources per topic; no official-docs/Context7 lookup performed — recommend a quick version spot-check against chartjs.org / tradingview.github.io during Phase 3 planning |
| Features | MEDIUM | Cross-verified dashboard-design and fintech UX references (Stripe/Linear/Vercel/Robinhood/Bloomberg patterns); no single authoritative spec for this exact feature combination, so patterns are triangulated, not sourced from one canonical doc |
| Architecture | HIGH | Verified directly against this repo's actual code (`app/templates/index.html`, `app/app.py`, `app/app.yaml`) plus official Flask static-file docs |
| Pitfalls | HIGH (codebase-specific) / MEDIUM (general CDN/Databricks-deploy ecosystem practices) | Codebase-specific findings verified by direct source read; general CDN/caching/Databricks-Apps-deploy conventions are standard web-platform knowledge, lightly web-verified this session, not Databricks-support-confirmed |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- Exact current lightweight-charts v5.x API surface (chainable series methods) should be spot-checked against official docs during Phase 3 planning, not assumed from cross-referenced blog posts — flagged explicitly in STACK.md's confidence note.
- Whether to self-host the CDN libraries under `app/static/vendor/` (zero external-CDN runtime dependency for the live Databricks Apps deployment) vs. keep them CDN-hosted is an open decision noted in STACK.md, not resolved by research — should be decided explicitly during Phase 1 or Phase 3 planning, not left implicit.
- Whether Databricks Apps' front-door proxy applies its own caching layer beyond standard Flask/Werkzeug defaults was not confirmed by official docs (ARCHITECTURE.md notes this as "no special Databricks override confirmed, treated as absence rather than proven absence") — the manual `?v=` cache-busting mitigation is recommended regardless, but the underlying assumption should be verified once, early, during Phase 1's first `app/static/` deploy.

## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md`, `.planning/codebase/{ARCHITECTURE,STRUCTURE,STACK,TESTING,CONCERNS}.md` — this project's own ground truth, verified against live code
- `app/templates/index.html`, `app/app.py`, `app/app.yaml` — direct source reads, current state as of 2026-08-10
- [Flask Static Files documentation](https://flask.palletsprojects.com/en/stable/tutorial/static/) — official docs

### Secondary (MEDIUM confidence)
- WebSearch cross-referenced (2-3 independent sources each): Chart.js vs lightweight-charts vs uPlot vs ApexCharts bundle-size/use-case comparison; lightweight-charts license/CDN details; native CSS Baseline support (nesting, `@property`, container queries, `@scope`, Popover API, View Transitions)
- Dashboard/fintech UX pattern references: Pencil & Paper, Setproduct, artofstyleframe (Stripe/Linear/Vercel dashboard-design conventions); Robinhood/Bloomberg (watchlist/sparkline conventions); Shape of AI, Carbon Design System, cookie-script (AI-content disclosure/badge patterns); Appian docs, Milvus (semantic-search match-quality/similarity-tier UX)
- [Configure Databricks app execution with app.yaml](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/app-runtime), [Deploy a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy) — official docs, general behavior confirmed, no Databricks-specific static-caching override surfaced

### Tertiary (LOW confidence)
- None — all findings were cross-verified across at least two sources or grounded directly in this codebase before being stated as recommendations.

---
*Research completed: 2026-08-10*
*Ready for roadmap: yes*
