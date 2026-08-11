# Phase 1: Static Asset Restructure & Design System Foundation - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Relocate the current inline `<script>`/`<style>` block in `app/templates/index.html` into a modular `app/static/css/{tokens,layout,components}.css` and `app/static/js/{main.js,api.js,components/*.js,tabs/*.js}` structure. In the same pass, apply the modern SaaS-dashboard visual design (typography, color, spacing, card-based layout) across the page shell (KPI stat-tile strip, tab nav) and all 5 tab content areas (Watchlist, Semantic Search, News Signals, Research Notes, Agent Reports). Establish the render-function scaffolding (table, chart-mount, tag, stat-tile, states) that Phases 2-4 will extend. No functional regression: every existing interactive action, DOM ID/class/data-attribute referenced by JS, and the Flask/API contract must remain exactly as they are today.

This phase now covers REQUIREMENT STYLE-01 (visual design system) directly, plus the structural foundation for STATE-01 through POLISH-02 (delivered in later phases). See `.planning/REQUIREMENTS.md` and the 2026-08-11 roadmap amendment note in its Traceability section.

</domain>

<decisions>
## Implementation Decisions

### Handler/module wiring strategy
- **D-01:** Load `api.js`, `components/*.js`, `tabs/*.js` as classic (non-module) `<script>` tags attaching to a shared global namespace — NOT `type="module"`. Keep all 7 existing `onclick="..."` handlers (`addSymbol`, `removeSymbol`, `showDetail`, `runSearch`, `loadSignals`, `delNote`, and `saveNote` — corrected during Phase 1 research on 2026-08-11 from an initial count of 6; `saveNote` at `index.html:159` was missed during discussion) working exactly as they do today, with no rewiring to `addEventListener`. — **Reversibility:** costly — switching to ES modules later means touching every inline `onclick` attribute across `index.html` in one coordinated change.
- **D-02:** Before marking Phase 1 done, run a full manual walkthrough of every button/tab/action against the **live deployed Databricks App** (not just local dev) — add/remove watchlist symbol, show ticker detail, run semantic search, load news signals, delete a note, save a note, plus a hard-refresh/incognito load to confirm cache-busted static assets. Use research's "Looks Done But Isn't" checklist (`.planning/research/PITFALLS.md`) as the basis.

### Theme & color direction
- **D-03:** Ship a light-only theme this milestone, but define all colors as CSS custom properties (design tokens) from the start, so a future dark mode is a token-swap, not a rewrite. No dark-mode UI or toggle is built now.
- **D-04:** Accent color direction is cool blue/indigo — reads as trustworthy/analytical for a fintech-adjacent tool, and doesn't collide with the existing red/green up-down price convention (which stays as-is; it's data semantics, not UI chrome).

### Typography & font strategy
- **D-05:** Use a system font stack (`-apple-system, "Segoe UI", Roboto, ...`) for all UI text — no CDN webfont. Keeps zero external font dependency, consistent with the "no build step, minimal external dependencies" direction already set for CDN charting libraries (Phase 3).
- **D-06:** Keep monospace/tabular numerals for data-heavy numbers (prices, metrics, volatility, drawdown) — this is a deliberate, already-validated fintech/terminal convention (right-alignment, easy scanning; see `.planning/research/FEATURES.md`). Use the sans-serif system font for labels, navigation, and prose (notes, report text).

### Layout restructuring boundary
- **D-07:** Additive markup changes are explicitly allowed — new wrapper `<div>`s, new CSS classes, new container elements for card-based layout are fine to add anywhere. The ONLY hard rule (tested by Phase 1's success criterion 4): no existing DOM ID, class, or `data-*` attribute that current JS queries against (`document.querySelector`/`getElementById`, the tab-switch `.hide` class, `data-view`) may be removed or renamed. Before/after ID-list diff must be clean.
- **D-08:** Restyle the page chrome (top KPI stat-tile strip, tab navigation bar) as part of Phase 1, not deferred — it's the first thing seen on load and the clearest "looks unfinished" signal if left in the old plain style while tab content gets a card treatment.

### Claude's Discretion
- Exact design-token values (specific hex codes for the blue/indigo accent, spacing scale numbers, type-scale ratios, border-radius/shadow values for cards) — the direction (modern SaaS dashboard, cool blue/indigo, system fonts, card-based) is locked; specific numeric values are left to planning/implementation, informed by `.planning/research/STACK.md`'s native-CSS (nesting/custom-properties/container-queries) recommendation.
- Exact file split within `app/static/js/components/*.js` and `app/static/css/*.css` beyond the `{tokens,layout,components}.css` / `{main,api,components/*,tabs/*}.js` structure already recommended in `.planning/research/ARCHITECTURE.md`.
- Cache-busting mechanism mechanics (manual `?v=` query string bumped per deploy, per research recommendation) — exact convention (e.g., where the version string lives) left to planning.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & requirements
- `.planning/PROJECT.md` — Core value, constraints (no build step, backend contract locked, no npm toolchain), context on current live-verified UI state
- `.planning/REQUIREMENTS.md` — STYLE-01 (this phase's primary requirement), full v1 scope, out-of-scope exclusions
- `.planning/ROADMAP.md` Phase 1 section — goal, success criteria (including the 5 explicit checks: visual design applied, all interactions work, cache-busted assets verified live, DOM ID/class list unchanged, zero backend diff)

### Research (produced 2026-08-10, still current)
- `.planning/research/ARCHITECTURE.md` — recommended `app/static/` file split (api.js as sole fetch boundary, components/*.js as pure render functions, tabs/*.js mirroring existing `load*()` functions), ES-module vs classic-script tradeoff, Flask static-serving/cache-busting guidance
- `.planning/research/STACK.md` — native CSS (nesting, custom properties, container queries) recommendation for the design-token system, explicit rejection of Tailwind CDN/Play and any bundler
- `.planning/research/PITFALLS.md` — Pitfall 1 (onclick handler breakage), Pitfall 2 (DOM ID/class contract breakage), Pitfall 5 (stale cached static assets after Databricks Apps deploy) — all three are this phase's primary risks, addressed by decisions D-01, D-07, and success criteria 3-4
- `.planning/research/FEATURES.md` — monospace/tabular-numeral convention validation (informs D-06), existing `.tag` badge component note

### Codebase maps (2026-08-10)
- `.planning/codebase/STRUCTURE.md` — current file layout (`app/templates/index.html` has everything inline today; `app/static/` exists but is empty except `.DS_Store`)
- `.planning/codebase/CONVENTIONS.md` — existing naming/style conventions to stay consistent with (snake_case Python is backend-only and irrelevant to JS/CSS; no lint config exists anywhere)
- `.planning/codebase/STACK.md` — confirms no `package.json`/bundler exists; Flask serves `app/static/` via its default static route

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing `.tag` CSS class (referenced in research/FEATURES.md as already present) — extend rather than replace when building the badge component groundwork in this phase; full badge system consolidation is Phase 4's job (STATE-05), but Phase 1's `components.css` should establish the base `.tag` styling other phases build on.
- Existing inline `fetch()` + template-literal rendering pattern in `app/templates/index.html` — port mechanically into `api.js` + `tabs/*.js`, don't redesign the data-fetching approach itself (research/ARCHITECTURE.md: "low-risk, mechanical port").

### Established Patterns
- Flask serves static files via its default `/static/` route (`app/static/`) — zero backend code change needed to add new CSS/JS files there; `app.py` doesn't need touching for this phase.
- No lint/format config exists anywhere in the repo (confirmed in `.planning/codebase/CONVENTIONS.md` and `TESTING.md`) — new CSS/JS files should follow the existing hand-consistent style (4-space-equivalent indentation, no framework-specific conventions to match) rather than introducing a new tool.

### Integration Points
- `app/app.yaml` (`command: python app.py`) — deployment mechanism unaffected; new static files are picked up automatically once synced via `databricks apps deploy`, per research/PITFALLS.md, but the first deploy of new `app/static/` assets should be explicitly verified live (D-02).
- `app/templates/index.html` — the Jinja shell stays as the single HTML entry point; it changes from "everything inline" to "head links to CSS + tab markup + one set of classic `<script src=...>` tags at the bottom," per research/ARCHITECTURE.md's recommended structure.

</code_context>

<specifics>
## Specific Ideas

- Visual reference point: Linear / Vercel / Stripe dashboard aesthetic (cards, subtle color accents, whitespace) — chosen explicitly over "Financial terminal" (dark-mode-first, dense) and "Minimal editorial" (refined black/white) during project setup questioning.
- Cool blue/indigo as the specific accent color family, distinct from the data-semantic red/green already used for price up/down.
- Monospace stays for numbers, system sans-serif for everything else — an explicit split, not a full font-family switch.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (VIZ-02, the ticker-detail drill-down chart, was already deferred to v2 during requirements definition on 2026-08-10 — not re-raised here.)

</deferred>

---

*Phase: 1-Static Asset Restructure & Design System Foundation*
*Context gathered: 2026-08-11*
