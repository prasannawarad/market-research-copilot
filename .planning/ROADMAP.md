# Roadmap: Market Research Copilot — Frontend Elevation

## Overview

This milestone takes the existing, live-verified Flask + vanilla-JS dashboard from a plain bordered-table look to a modern, portfolio-grade SaaS dashboard — without touching the Flask route contract, JSON shapes, Spark pipeline, or Lakebase schema. The journey starts with a foundation phase that safely relocates the current inline `<script>`/`<style>` block into `app/static/{css,js}/` (the riskiest step, per research/PITFALLS.md, because of onclick-handler and DOM-ID contracts nothing else enforces), then layers in the two "looks unfinished" fixes users will notice first (missing-data treatment, loading/empty/error states), then the one genuinely new capability (watchlist sparklines), and finishes with badge/attribution polish that only makes sense once every tab's markup is stable. Each phase ends with a live-app visual/functional check and a zero-backend-diff verification, so risk to the working, screenshot-verified deployment stays low throughout.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Static Asset Restructure & Design System Foundation** - Move inline CSS/JS into `app/static/{css,js}/` with zero functional regression, establishing design tokens and shared render-function scaffolding for every later phase
- [ ] **Phase 2: Missing-Data & Loading/Empty/Error States** - Replace raw `N/A` with graceful placeholders and add consistent loading/empty/error feedback across all 5 tabs
- [ ] **Phase 3: Watchlist Sparklines** - Add inline price-trend sparklines to the Watchlist tab, sourced from the existing per-ticker metrics endpoint
- [ ] **Phase 4: Badge System & Attribution Polish** - Unify all status/sentiment/signal/similarity/author indicators into one consistent badge component, add match-strength and human-vs-agent visual distinction, and finish KPI tile context lines

## Phase Details

### Phase 1: Static Asset Restructure & Design System Foundation
**Goal**: The current inline `<script>`/`<style>` block in `app/templates/index.html` is safely relocated into a modular `app/static/css/{tokens,layout,components}.css` and `app/static/js/{main.js,api.js,components/*.js,tabs/*.js}` structure, functionally identical to today, with cache-busted asset loading verified against a real deploy — establishing the foundation every subsequent phase builds on.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: None directly — foundational phase preceding all v1 requirements (STATE-01 through POLISH-02), flagged by research/SUMMARY.md as necessary before any visual/feature work can land safely given the codebase's onclick-handler and DOM-ID contract risks (see research/PITFALLS.md #1, #2, #5)
**Success Criteria** (what must be TRUE):
  1. The live app renders visually identical to the current baseline (same 5 tabs, same tables, same content) immediately after the restructure — no visible regression on first load.
  2. Every existing interactive action still works: add/remove watchlist symbol, show ticker detail, run semantic search, load news signals, delete a note — each bound to the same `onclick`-triggered global functions or explicitly re-wired via `addEventListener` in the same change.
  3. CSS and JS load from `app/static/css/` and `app/static/js/` via cache-busted URLs (`?v=`), confirmed with a hard-refresh/incognito load against the deployed Databricks App (not just local dev).
  4. No DOM ID, class, or `data-*` attribute referenced by existing lookups (`document.querySelector`/`getElementById`, tab-switch `.hide` class, `data-view`) has changed — before/after ID list diff is clean.
  5. Zero backend diff: `git diff --stat app/app.py app/lakebase.py app/massive_client.py mcp_server/ pipeline/ sql/` is empty — only `app/templates/index.html` and new files under `app/static/` changed.
**Plans**: TBD
**UI hint**: yes

### Phase 2: Missing-Data & Loading/Empty/Error States
**Goal**: Users get honest, graceful visual feedback in every data state — pending metrics, in-flight fetches, empty tabs, and failed API calls — instead of raw `N/A` text or a silently broken tab.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: STATE-01, STATE-02, STATE-03, STATE-04
**Success Criteria** (what must be TRUE):
  1. A watchlist ticker without computed metrics shows a muted "pending"-style placeholder (not raw `N/A`) in both the Watchlist table and its detail view.
  2. Every tab (Watchlist, Semantic Search, News Signals, Research Notes, Agent Reports) shows a visible loading indicator while its data is being fetched, before content or an empty/error state appears.
  3. A tab with no data yet (e.g. empty watchlist, no search run, no notes) shows a clear, distinct empty-state message rather than a blank area or an empty table shell.
  4. A failed API call surfaces a clear, visible error state scoped to the affected tab (not a silent failure or a JS console-only error), and does not break other tabs.
  5. Zero backend diff: `git diff --stat app/app.py app/lakebase.py app/massive_client.py mcp_server/ pipeline/ sql/` is empty — these states are rendered entirely from existing `/api/*` response shapes (success data, empty arrays, HTTP error codes), no new fields or routes.
**Plans**: TBD
**UI hint**: yes

### Phase 3: Watchlist Sparklines
**Goal**: Users see an at-a-glance recent price trend for each watchlist ticker without leaving the Watchlist tab, built entirely from data the existing per-ticker metrics endpoint already returns.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: VIZ-01
**Success Criteria** (what must be TRUE):
  1. Each watchlist row with sufficient price history shows an inline sparkline reflecting recent price trend, rendered next to (or in place of) the raw trend number.
  2. A ticker without enough history to draw a meaningful sparkline degrades gracefully to the Phase 2 missing-data placeholder — no broken chart, no JS error, no blank canvas.
  3. The sparkline data is sourced exclusively from the existing `/api/metrics/<ticker>` endpoint (one call per visible ticker) — no new or bulk backend endpoint is introduced.
  4. The charting library is loaded from a pinned, SRI-hashed CDN URL, and a CDN failure degrades the row to numbers-only (no chart) rather than breaking the page.
  5. Zero backend diff: `git diff --stat app/app.py app/lakebase.py app/massive_client.py mcp_server/ pipeline/ sql/` is empty — sparklines are a pure frontend consumer of the existing API contract.
**Plans**: TBD
**UI hint**: yes

### Phase 4: Badge System & Attribution Polish
**Goal**: Every status/sentiment/signal-strength/similarity/author indicator across all 5 tabs reads as one consistent, at-a-glance visual language, and search results and notes/reports clearly communicate match quality and authorship without relying on raw numbers or text labels alone.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: STATE-05, ATTR-01, ATTR-02, POLISH-01, POLISH-02
**Success Criteria** (what must be TRUE):
  1. All status, sentiment, signal-strength, similarity, and author indicators across all 5 tabs render through one shared badge component with a consistent visual grammar (shape, sizing, color convention) — no second badge style anywhere in the UI.
  2. Semantic Search results show a qualitative match-strength badge (e.g. strong/related/weak) alongside the existing raw similarity score, not the raw score alone.
  3. A human-authored note/report is visually distinguishable from an agent-authored one at a glance (e.g. border treatment, icon, or badge) on both the Research Notes and Agent Reports tabs, not just by an existing text label.
  4. News Signals tab shows signal-strength badges with a visual-weight gradient (e.g. filled/outlined/intensity) rather than flat color alone.
  5. Top-of-page KPI stat tiles show a secondary context line under the raw count (e.g. "12 of 13 tickers scored").
  6. Zero backend diff: `git diff --stat app/app.py app/lakebase.py app/massive_client.py mcp_server/ pipeline/ sql/` is empty — all badge/attribution/context logic derives from fields the existing `/api/*` responses already return (similarity score, author/model fields, signal strength, stat counts).
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Static Asset Restructure & Design System Foundation | 0/TBD | Not started | - |
| 2. Missing-Data & Loading/Empty/Error States | 0/TBD | Not started | - |
| 3. Watchlist Sparklines | 0/TBD | Not started | - |
| 4. Badge System & Attribution Polish | 0/TBD | Not started | - |
