# Requirements: Market Research Copilot — Frontend Elevation

**Defined:** 2026-08-10
**Core Value:** The app must look and feel like a real product — a visual quality bar that holds up in a job-application portfolio — while every currently-working feature keeps working exactly as it does today.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Visual Design System

- [ ] **STYLE-01**: User sees a modern SaaS-dashboard visual design (typography scale, color palette, spacing system, card-based layout) applied consistently across the page shell and all 5 tabs, replacing the current plain bordered-table look

### States (missing-data & loading/empty/error handling)

- [ ] **STATE-01**: User sees a graceful placeholder (not raw "N/A") for tickers without computed metrics yet, in the Watchlist and detail views
- [ ] **STATE-02**: User sees a loading state while any tab's data is being fetched
- [ ] **STATE-03**: User sees a clear empty state when a tab has no data yet
- [ ] **STATE-04**: User sees a clear error state if an API call fails, instead of a silently broken tab
- [ ] **STATE-05**: All status/sentiment/signal-strength/similarity/author indicators use one consistent badge component across all 5 tabs

### Visualization

- [ ] **VIZ-01**: User sees an inline sparkline showing recent price trend for each ticker in the Watchlist tab

### Attribution (search & content polish)

- [ ] **ATTR-01**: User sees a qualitative match-strength badge (e.g. strong/related/weak) alongside the raw similarity score in Semantic Search results
- [ ] **ATTR-02**: User can visually distinguish human-authored notes from agent-authored notes/reports at a glance, not just by text label

### Polish

- [ ] **POLISH-01**: Signal-strength badges in News Signals use a visual-weight gradient (e.g. filled/outlined/intensity) rather than flat color alone
- [ ] **POLISH-02**: Top-of-page KPI stat tiles show a secondary context line (e.g. "12 of 13 tickers scored") under the raw count

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Visualization

- **VIZ-02**: User can open a larger ticker-detail drill-down chart (line/area chart via lightweight-charts) instead of the current 20-row detail table — deferred because watchlist sparklines (VIZ-01) already satisfy the core data-visualization goal for this milestone

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time/live-updating prices (polling/websockets) | Dishonest against a batch Spark pipeline that runs on a schedule, not a live feed |
| Heavy AI-disclaimer banners on agent content | Wrong weight for an internal tool where the user added the agent themselves — a quiet badge (ATTR-02) is the right convention |
| Full multi-panel candlestick/technical-indicator charting | Over-scoped for a data-sparse demo dataset (max 3 tickers with full history today) |
| Any change to Flask route paths, request/response JSON shapes, Spark pipeline, or Lakebase schema | Backend contract is locked for this milestone — MCP server and Agent Bricks integration depend on it staying stable |
| Full SPA/framework rebuild (React/Vue) | Rejected in favor of polishing the existing Flask-rendered vanilla-JS page — lower risk to a verified-working live app, stays interview-explainable |
| New backend endpoints (e.g. a bulk sparkline-data endpoint) | Sparklines must be built from the existing `/api/metrics/<ticker>` endpoint per-ticker, not a new route |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STYLE-01 | Phase 1 | Pending |
| STATE-01 | Phase 2 | Pending |
| STATE-02 | Phase 2 | Pending |
| STATE-03 | Phase 2 | Pending |
| STATE-04 | Phase 2 | Pending |
| STATE-05 | Phase 4 | Pending |
| VIZ-01 | Phase 3 | Pending |
| ATTR-01 | Phase 4 | Pending |
| ATTR-02 | Phase 4 | Pending |
| POLISH-01 | Phase 4 | Pending |
| POLISH-02 | Phase 4 | Pending |

Note: STYLE-01 was added during Phase 1 discussion (2026-08-11) to close a gap — PROJECT.md's "visual design system" Active requirement had no explicit phase mapping in the original roadmap. Folded into Phase 1 since the restructure already touches every line of CSS.

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 11 (100%)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-10*
*Last updated: 2026-08-11 after roadmap creation*
