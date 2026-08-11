# Phase 1: Static Asset Restructure & Design System Foundation - Research

**Researched:** 2026-08-11
**Domain:** No-build-step vanilla-JS/CSS restructuring of a single live Flask template into `app/static/` modules, plus a native-CSS SaaS-dashboard design-token system — brownfield, zero backend diff, zero functional regression
**Confidence:** HIGH (codebase mechanics — read directly this session); MEDIUM (design-token numeric values, general web-platform script-loading behavior — web-search cross-checked)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Load `api.js`, `components/*.js`, `tabs/*.js` as classic (non-module) `<script>` tags attaching to a shared global namespace — NOT `type="module"`. Keep all existing `onclick="..."` handlers working exactly as they do today, with no rewiring to `addEventListener`. — **Reversibility:** costly — switching to ES modules later means touching every inline `onclick` attribute across `index.html` in one coordinated change.
- **D-02:** Before marking Phase 1 done, run a full manual walkthrough of every button/tab/action against the **live deployed Databricks App** (not just local dev) — add/remove watchlist symbol, show ticker detail, run semantic search, load news signals, delete a note, plus a hard-refresh/incognito load to confirm cache-busted static assets. Use research's "Looks Done But Isn't" checklist (`.planning/research/PITFALLS.md`) as the basis.
- **D-03:** Ship a light-only theme this milestone, but define all colors as CSS custom properties (design tokens) from the start, so a future dark mode is a token-swap, not a rewrite. No dark-mode UI or toggle is built now.
- **D-04:** Accent color direction is cool blue/indigo — reads as trustworthy/analytical for a fintech-adjacent tool, and doesn't collide with the existing red/green up-down price convention (which stays as-is; it's data semantics, not UI chrome).
- **D-05:** Use a system font stack (`-apple-system, "Segoe UI", Roboto, ...`) for all UI text — no CDN webfont. Keeps zero external font dependency.
- **D-06:** Keep monospace/tabular numerals for data-heavy numbers (prices, metrics, volatility, drawdown). Use the sans-serif system font for labels, navigation, and prose (notes, report text).
- **D-07:** Additive markup changes are explicitly allowed — new wrapper `<div>`s, new CSS classes, new container elements for card-based layout are fine to add anywhere. The ONLY hard rule (tested by Phase 1's success criterion 4): no existing DOM ID, class, or `data-*` attribute that current JS queries against may be removed or renamed. Before/after ID-list diff must be clean.
- **D-08:** Restyle the page chrome (top KPI stat-tile strip, tab navigation bar) as part of Phase 1, not deferred.

### Claude's Discretion

- Exact design-token values (specific hex codes for the blue/indigo accent, spacing scale numbers, type-scale ratios, border-radius/shadow values for cards) — the direction is locked; specific numeric values are left to planning/implementation.
- Exact file split within `app/static/js/components/*.js` and `app/static/css/*.css` beyond the `{tokens,layout,components}.css` / `{main,api,components/*,tabs/*}.js` structure already recommended in `.planning/research/ARCHITECTURE.md`.
- Cache-busting mechanism mechanics (manual `?v=` query string bumped per deploy) — exact convention (e.g., where the version string lives) left to planning.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. (VIZ-02, the ticker-detail drill-down chart, was already deferred to v2 during requirements definition — not re-raised here.)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STYLE-01 | User sees a modern SaaS-dashboard visual design (typography scale, color palette, spacing system, card-based layout) applied consistently across the page shell and all 5 tabs | Design-token conventions (`## Standard Stack`, `## Code Examples`), CSS card-grid pattern, cool blue/indigo palette guidance, monospace/sans split — all below |

Also foundational (no direct REQ-ID, structural groundwork only) for STATE-01 through POLISH-02, delivered in Phases 2-4. This phase's render-function scaffolding (`components/table.js`, `components/tag.js`, `components/states.js`) is what those phases extend — see `## Architecture Patterns`.
</phase_requirements>

## Summary

This phase has two intertwined jobs: (1) mechanically relocate ~200 lines of inline `<style>` and ~190 lines of inline `<script>` out of `app/templates/index.html` into `app/static/css/{tokens,layout,components}.css` and `app/static/js/{api,components/*,tabs/*,main}.js`, and (2) restyle the page with a modern SaaS-dashboard look (cards, cool blue/indigo accent, spacing/type scale) in the same pass. Both must produce **zero functional regression** — every `onclick`, every DOM ID/class/`data-*` value the JS queries against, and the Flask/API contract stay exactly as they are today.

**Critical correction to prior project-level research:** `.planning/research/ARCHITECTURE.md` (written 2026-08-10, before this phase's `/gsd-discuss-phase` session) recommends `<script type="module">` ES-module imports for the new JS split. CONTEXT.md's **D-01, locked during this phase's discussion (2026-08-11), overrides that recommendation**: use classic (non-module) `<script src>` tags so every function stays on `window` and all `onclick="..."` attributes keep working unmodified. This is not a minor style choice — ES modules do not leak top-level function/const declarations to the global scope, so switching to `type="module"` would silently break every inline `onclick` handler in the rendered HTML (Pitfall 1 in `.planning/research/PITFALLS.md`). The planner must build the file split as classic scripts, not modules. See `## State of the Art` below.

**Second finding, newly verified this session:** CONTEXT.md's D-01 names "6 existing `onclick="..."` handlers (`addSymbol`, `removeSymbol`, `showDetail`, `runSearch`, `loadSignals`, `delNote`)". A direct read of `app/templates/index.html` this session found **7**, not 6 — `saveNote()` is also `onclick`-bound (`app/templates/index.html:159`) and was omitted from CONTEXT.md's list. The full verified inventory is in `## Common Pitfalls` below; the planner's task breakdown and D-02's manual walkthrough must include `saveNote` (Save note button, Research Notes tab), not just the 6 named.

**Primary recommendation:** Split JS into classic `<script src>` tags loaded in dependency order (`api.js` → `components/*.js` → `tabs/*.js` → `main.js`, `main.js` last since its top-level boot calls reference every other file), keep them all non-module, and build the CSS as three layered files (`tokens.css` → `layout.css` → `components.css`) using native CSS custom properties + CSS Grid for card layout — no framework, no bundler, matching the "no build step" project constraint already established in `.planning/research/STACK.md`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Page shell markup & tab routing (`.hide` toggle, `data-view`) | Browser/Client | — | Pure DOM manipulation; no server round trip on tab click (matches today's behavior exactly) |
| CSS design tokens & card-based layout | Browser/Client | — | All styling is native CSS in `app/static/css/*.css`; zero server involvement |
| Data-fetch orchestration (`api.js`) | Browser/Client | API/Backend | Client owns the `fetch()` call and JSON parsing; Flask (unchanged this phase) owns the JSON contract being fetched against |
| Presentational render functions (`components/*.js`, `tabs/*.js`) | Browser/Client | — | Pure `(data) => markup` functions; no network or server logic, matches ARCHITECTURE.md's Pattern 2 |
| Static asset delivery (serving the new `.css`/`.js` files) | API/Backend (Flask's built-in static blueprint) | — | `Flask(__name__)` auto-registers `/static/<path:filename>` from `app/static/` with zero new route code — `app/app.py:17` confirmed unmodified for this |
| Cache-busting version string | Browser/Client (literal in `index.html`) | — | Must be a hardcoded `?v=` string in the Jinja template's `<link>`/`<script>` tags, **not** sourced from a Flask config value or new `app.py` variable — Phase 1 Success Criterion 5 requires zero diff to `app/app.py` (see `.planning/ROADMAP.md` Phase 1 §Success Criteria) |

## Standard Stack

### Core

No new libraries are introduced by this phase. This phase *formalizes* stack decisions already locked at the project level:

| Technology | Version | Purpose | Why Standard |
|------------|---------|---------|---------------|
| Native CSS (custom properties, nesting, Grid) | Baseline "Widely Available" (Safari 17.2+/Chrome 120+/Firefox 117+) | Design-token system, card-based layout, no preprocessor | [CITED: `.planning/research/STACK.md`] Already the project's locked choice — satisfies the "no bundler" constraint while giving a real token system |
| Classic (non-module) JavaScript, split across files, one `<script src>` per file | ES2020+ (any evergreen browser) | Multi-file organization without a build step | [VERIFIED: app/templates/index.html — current script is already plain ES2020+ (`async`/`await`, template literals, optional chaining not used but arrow functions are); D-01 locks classic-script (not module) loading for the split] |

**Installation:** None — no `npm install`, no CDN `<script>` additions this phase (Chart.js/lightweight-charts are Phase 3's concern, not this phase's). No `pip`/`npm`/`cargo` version verification applies; nothing new is being added to `app/requirements.txt` or any package manifest.

### Supporting

Not applicable this phase — no supporting libraries introduced.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Classic multi-file `<script src>` (D-01, locked) | `<script type="module">` (project-level ARCHITECTURE.md's original recommendation) | Modules give cleaner `import`/`export` syntax and stricter scoping, but break every existing inline `onclick` attribute since module top-level declarations don't leak to `window`. Rejected by CONTEXT.md D-01 specifically because of this breakage risk, with the tradeoff noted as "costly to reverse" — a future coordinated rewrite of every `onclick` to `addEventListener` would be needed to adopt modules later. |
| Native CSS custom properties + Grid | Tailwind CDN/Play | Already rejected at project level (`.planning/research/STACK.md`) — Tailwind's CDN build is dev/prototype-only per Tailwind's own docs, and fights the single self-contained `static/` design-system goal. |

## Package Legitimacy Audit

**Not applicable this phase.** No external packages (npm, pip, CDN, or otherwise) are installed, added, or upgraded in Phase 1 — this phase relocates and restyles existing inline code using only native browser CSS/JS features already available with zero dependencies. Chart.js/lightweight-charts CDN additions belong to Phase 3 and should be re-audited there.

## Architecture Patterns

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Browser                                                                    │
│                                                                              │
│  index.html (Jinja shell)                                                   │
│   <head>: <link> tokens.css, layout.css, components.css  (?v= cache-bust)  │
│   <body>: mast/strip/tabs markup + 5 tab panels (unchanged IDs/classes)     │
│   end of <body>: classic <script src> tags, IN DEPENDENCY ORDER:           │
│      1. api.js            (no deps)                                        │
│      2. components/*.js   (no deps — pure render fns)                      │
│      3. tabs/*.js         (deps: api.js, components/*.js)                  │
│      4. main.js           (deps: tabs/*.js — boot calls + tab-click wiring)│
│                                                                              │
│  [Tab click] ──▶ main.js tab-switch handler ──▶ toggles .hide,             │
│                   calls tabs/<name>.js's load*()                            │
│                        │                                                    │
│                        ▼                                                    │
│                   tabs/<name>.js  ──▶ api.js fetch('/api/...')             │
│                        │                       │                            │
│                        │                       ▼                            │
│                        │              Flask app/app.py (UNCHANGED)         │
│                        │                       │ JSON                       │
│                        │◀──────────────────────┘                            │
│                        ▼                                                    │
│                   components/*.js render fns ──▶ innerHTML into #*-body    │
│                                                                              │
│  [onclick="addSymbol()" etc.] ──▶ resolves against window (global scope,   │
│    all classic scripts already loaded) ──▶ same tabs/*.js functions above  │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 │ fetch('/api/...') — UNCHANGED contract
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Flask app (app/app.py) — locked, zero diff this phase                     │
│  render_template("index.html", user=...) + /static/* (Flask's built-in     │
│  static handler, zero new route code) + all existing /api/* JSON routes    │
└──────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
app/
├── templates/
│   └── index.html              # shell only: head (CSS links + cache-bust), tab nav, 5 mounts,
│                                # classic <script src> tags at end of body, in dependency order
└── static/
    ├── css/
    │   ├── tokens.css           # :root custom properties — colors, spacing, type scale, radii, shadows
    │   ├── layout.css           # shell/mast/strip/tabs/panel grid — structural, not component-specific
    │   └── components.css       # table, tag, button, card, empty/error states — extends existing .tag base
    └── js/
        ├── api.js                 # fetch wrapper + api() helper (loaded first — no deps)
        ├── components/
        │   ├── table.js            # generic table renderer (replaces duplicated table template
        │   │                        # literals currently in loadWatchlist/showDetail/loadSignals)
        │   ├── tag.js               # status/sentiment/trend pill renderer (extends existing .tag CSS)
        │   └── states.js            # empty/error state renderers (showErr() port)
        └── tabs/
            ├── watchlist.js        # loadWatchlist, addSymbol, removeSymbol, showDetail
            ├── search.js            # runSearch
            ├── signals.js           # loadSignals
            ├── notes.js              # loadNotes, saveNote, delNote
            └── reports.js            # loadReports
        # main.js loaded LAST (after api.js, components/*.js, tabs/*.js):
        # tab-switch wiring (document.querySelectorAll('.tab')...) + loadStats() + loadWatchlist() boot calls
```

**Why `main.js` must load last:** classic (non-module, non-`defer`) scripts execute synchronously, in document order, as each `<script src>` tag is encountered. Function *declarations* inside an already-loaded file are available globally the instant that file finishes executing — but `main.js`'s own top-level code (the tab-click wiring block and the `loadStats(); loadWatchlist();` boot calls at the bottom of today's script) *runs immediately* when `main.js`'s tag is reached. If `main.js` is loaded before `tabs/watchlist.js`, that top-level `loadWatchlist()` call throws `ReferenceError: loadWatchlist is not defined` immediately on page load. `onclick="..."` attribute calls are different — they resolve at click time, long after every script has finished loading, so their cross-file ordering is *not* order-sensitive the same way. [CITED: web search cross-check, "classic script global scope + late binding" — MEDIUM confidence]

### Pattern 1: Classic multi-file scripts sharing one global namespace (supersedes ES-module pattern)

**What:** Split JS into files using plain top-level `function name(){...}` declarations (no `export`, no `import`, no `type="module"`). Each file is loaded via its own `<script src="...">` tag, in dependency order, at the end of `<body>` (mirroring today's placement). All functions across all files attach to the same `window` global scope, exactly as the single inline `<script>` does today.

**When to use:** Always, for this phase — this is what D-01 locks.

**Trade-offs:**
- Pro: Zero risk to the 7 `onclick="..."` handlers and 2 `addEventListener` calls already wired against global function names.
- Pro: No new concept to explain in an interview beyond "the file got split, the functions still live on `window` the same way a single `<script>` tag would put them there."
- Con: No automatic dependency enforcement — a file that calls a function from a not-yet-loaded file at top-level scope fails silently loud (`ReferenceError`) rather than at compile time. Mitigate by keeping the load order documented in `index.html`'s comments and never adding top-level (non-function-body) code to `api.js`/`components/*.js`/`tabs/*.js` — only `main.js` should have top-level executable statements (the boot calls + tab wiring), same as today's inline script.
- Con: Every global function name is a single shared namespace — a name collision between, say, `components/table.js` and `tabs/watchlist.js` silently overwrites one function with the other, with no error. Mitigate with a naming convention (e.g., prefix component-only helpers that aren't part of the public `onclick` contract, though none currently exist in this codebase).

**Example:**
```javascript
// app/static/js/api.js  (loaded first, no deps)
async function api(url, opts) {
  const r = await fetch(url, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || ('Request failed: ' + r.status));
  return body;
}
```
```javascript
// app/static/js/tabs/watchlist.js  (loaded after api.js + components/*.js)
async function loadWatchlist() {
  try {
    const rows = await api('/api/watchlist');
    // ... renders via components/table.js's dataTable() ...
  } catch (e) { $('#wl-body').innerHTML = `<div class="err">${esc(e.message)}</div>`; }
}
async function addSymbol() { /* ported mechanically from index.html:240-249 */ }
async function removeSymbol(symbol) { /* ported mechanically from index.html:251-255 */ }
async function showDetail(ticker) { /* ported mechanically from index.html:257-277 */ }
```
```html
<!-- index.html, end of <body>, exact dependency order -->
<script src="{{ url_for('static', filename='js/api.js') }}?v=1"></script>
<script src="{{ url_for('static', filename='js/components/table.js') }}?v=1"></script>
<script src="{{ url_for('static', filename='js/components/tag.js') }}?v=1"></script>
<script src="{{ url_for('static', filename='js/components/states.js') }}?v=1"></script>
<script src="{{ url_for('static', filename='js/tabs/watchlist.js') }}?v=1"></script>
<script src="{{ url_for('static', filename='js/tabs/search.js') }}?v=1"></script>
<script src="{{ url_for('static', filename='js/tabs/signals.js') }}?v=1"></script>
<script src="{{ url_for('static', filename='js/tabs/notes.js') }}?v=1"></script>
<script src="{{ url_for('static', filename='js/tabs/reports.js') }}?v=1"></script>
<script src="{{ url_for('static', filename='js/main.js') }}?v=1"></script>
```
Note the literal `?v=1` — a hand-bumped string directly in the template, NOT sourced from `app.py`/Flask config, to satisfy Phase 1's zero-backend-diff success criterion (`.planning/ROADMAP.md` Phase 1 §Success Criteria item 5). [VERIFIED: .planning/ROADMAP.md Phase 1 Success Criteria item 5: "Zero backend diff: `git diff --stat app/app.py app/lakebase.py app/massive_client.py mcp_server/ pipeline/ sql/` is empty — only `app/templates/index.html` and new files under `app/static/` changed."]

### Pattern 2: Presentational render functions (component-lite)

**What:** Every reusable visual piece (table, tag pill, empty/error state) is a pure function: `(data) => htmlString`. No render function calls `fetch()`. [CITED: `.planning/research/ARCHITECTURE.md` Pattern 2 — carries over unchanged, MEDIUM confidence via that document]

**When to use:** Any markup duplicated across tabs today — tables appear in Watchlist/detail/Signals, `.tag` pills appear in Watchlist/Signals/Notes/Reports.

**Example (extends the existing `.tag` CSS rather than replacing it — see verbatim CSS below):**
```javascript
// app/static/js/components/tag.js
function tag(value, kind) {
  return `<span class="tag ${kind}">${esc(value)}</span>`;
}
```

### Pattern 3: Direct function calls for tab-switch (no pub/sub)

**What:** Tab click toggles `.hide` on the 5 mount `<div>`s and calls that tab's `load*()` function directly by name — exactly as today. [CITED: `.planning/research/ARCHITECTURE.md` Pattern 3]

**When to use:** Always, at this scale — no cross-tab live sync in scope this milestone.

### Pattern 4: Layered native-CSS design tokens (`tokens.css` → `layout.css` → `components.css`)

**What:** `tokens.css` defines every color/spacing/radius/shadow/type value as a `:root` custom property; `layout.css` uses those tokens for shell/header/tabs/grid structure; `components.css` uses them for tables/tags/buttons/cards. No file hardcodes a raw hex/px value — everything routes through a token.

**When to use:** Always, for this phase's restyle pass — this is the mechanism that makes D-03's "light-only now, dark-mode-ready later" possible: a future dark theme only needs a second `:root[data-theme="dark"] { --ink: ...; }` block in `tokens.css`, no rewrite of `layout.css`/`components.css`.

**Example — extending the token set already present in the current inline `<style>` (verbatim, verified this session):**
```css
/* app/static/css/tokens.css */
:root{
  /* EXISTING tokens — preserve exactly, verified app/templates/index.html:8-14 */
  --ink:#131a24; --soft:#4b5661; --muted:#7b858f;
  --paper:#fbfbf9; --surface:#fff; --rule:#e4e4dd;
  --up:#2e7a55; --down:#b4362c; --flat:#7b858f; --accent:#1d6fe0;
  --mono:ui-monospace,SFMono-Regular,"SF Mono","JetBrains Mono",Menlo,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;

  /* NEW tokens for the card-based SaaS-dashboard pass — additive, D-07-compliant */
  --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px; --space-6:24px; --space-8:32px;
  --radius-sm:4px; --radius-md:8px; --radius-lg:14px;
  --shadow-sm:0 1px 2px rgba(19,26,36,.06);
  --shadow-md:0 2px 8px rgba(19,26,36,.08);
  --accent-soft:#eaf1fd; /* light tint of --accent for card/badge backgrounds */
}
```
[VERIFIED: app/templates/index.html:8-14 — the `--ink`/`--soft`/`--muted`/`--paper`/`--surface`/`--rule`/`--up`/`--down`/`--flat`/`--accent`/`--mono`/`--sans` tokens quoted above are copied verbatim from the current file and must be preserved, not renamed, since `.tag`, `.sym`, `.up`/`.down`/`.flat`, and every `td.num` reference them directly.]

The spacing/radius/shadow values above are new (`[CITED: web search cross-check — SaaS dashboard token conventions, MEDIUM confidence]`, `.planning/research/STACK.md`'s native-CSS recommendation) and are Claude's Discretion per CONTEXT.md — adjust freely, the *pattern* (token-first, no magic numbers) is what's load-bearing, not these exact pixel values.

### Pattern 5: Responsive card grid via native CSS Grid, not Flexbox-masonry

**What:** `grid-template-columns: repeat(auto-fill, minmax(240px, 1fr))` for any new card-grid container (e.g. an upgraded KPI stat-tile strip), giving equal-height, responsive cards with zero media queries. [CITED: web search cross-check, MEDIUM confidence]

**When to use:** The KPI stat-tile strip (`.strip`, currently a plain 6-column CSS Grid at `app/templates/index.html:24-29`) restyled as cards per D-08 — this is an additive class change (D-07-compliant), not a rename of `#strip`'s ID.

```css
/* app/static/css/layout.css — restyling .strip as cards, ID unchanged */
.strip{
  display:grid;
  grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); /* was: repeat(6,1fr), verified index.html:24 */
  gap:var(--space-3);
}
.strip > div{
  background:var(--surface); border:1px solid var(--rule); border-radius:var(--radius-md);
  box-shadow:var(--shadow-sm); padding:var(--space-4); /* was: padding:14px 0, verified index.html:25 */
}
```

### Anti-Patterns to Avoid

- **Wrapping the split scripts in an IIFE "for cleanliness."** An IIFE (`(function(){...})()`) creates its own scope, un-exposing every function from `window` just like `type="module"` would — same breakage as the ES-module anti-pattern, different mechanism. Do not do this even without `type="module"`.
- **One giant `app.js`.** Cut-pasting the existing inline script verbatim into one file solves "inline vs. external" but not the actual duplication problem (table-rendering logic repeated across `loadWatchlist`/`showDetail`/`loadSignals`). [CITED: `.planning/research/ARCHITECTURE.md` Anti-Pattern 1]
- **Hardcoding `/static/...` paths instead of `url_for('static', ...)`.** [CITED: `.planning/research/ARCHITECTURE.md` Anti-Pattern 3]
- **Sourcing the cache-bust `?v=` value from a new Flask config/env var.** This would touch `app/app.py`, violating the phase's zero-backend-diff success criterion. Keep it a literal string in the Jinja template.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Cross-file JS namespace sharing | A bespoke module-loader shim, a manual `window.MyApp = {}` namespace object | Plain classic-script global scope (already works, zero new infra) | The browser already does this natively for classic scripts — D-01 exists specifically because this "just works" without extra code |
| Responsive card grid | Hand-rolled Flexbox row-wrapping + manual breakpoints for card counts per row | `grid-template-columns: repeat(auto-fill, minmax(Npx, 1fr))` | Native CSS Grid auto-fill/minmax reflows column count with zero media queries — the exact problem a hand-rolled Flexbox+breakpoint solution re-solves worse |
| Design-token theming | Scattered raw hex/px values reintroduced per new component rule | Centralized `:root` custom properties in `tokens.css`, referenced everywhere | Matches D-03's stated goal (dark mode later = token swap, not rewrite) — a single un-tokenized rule anywhere defeats that goal |
| Badge/pill component | A new one-off badge CSS class per tab (duplicating `.tag`) | Extend the existing `.tag` base class (verified `app/templates/index.html:59-63`) | CONTEXT.md's `code_context` section explicitly calls out `.tag` as a reusable asset to extend, not replace, this phase — full consolidation is Phase 4's job (STATE-05) |

**Key insight:** At this scale (5 tabs, no build step, single Jinja template), every "custom solution" temptation in this phase (module loader, hand-rolled grid breakpoints, per-tab badge styles) re-solves a problem the browser or the existing codebase already solves for free. The discipline this phase requires is restraint, not new code.

## Common Pitfalls

### Verified Contract Inventory (must not break — read directly from `app/templates/index.html` this session)

**Onclick-bound global functions — 7 total, not 6.** CONTEXT.md's D-01 names 6 (`addSymbol`, `removeSymbol`, `showDetail`, `runSearch`, `loadSignals`, `delNote`); a direct read of the file found a 7th: `saveNote()`.

| Function | Onclick site (verified line) | Function definition (verified line) |
|----------|------------------------------|----------------------------------------|
| `addSymbol()` | `app/templates/index.html:108` | `app/templates/index.html:240` |
| `runSearch()` | `app/templates/index.html:129` | `app/templates/index.html:279` |
| `loadSignals()` | `app/templates/index.html:145` | `app/templates/index.html:297` |
| `saveNote()` **(missing from CONTEXT.md's D-01 list)** | `app/templates/index.html:159` | `app/templates/index.html:329` |
| `showDetail('${esc(r.symbol)}')` | `app/templates/index.html:228` | `app/templates/index.html:257` |
| `removeSymbol('${esc(r.symbol)}')` | `app/templates/index.html:235` | `app/templates/index.html:251` |
| `delNote(${r.note_id});return false` | `app/templates/index.html:324` | `app/templates/index.html:341` |

Plus 2 `addEventListener` bindings that must also keep working (not `onclick`, but equally global-scope-dependent): `#new-symbol` keydown→`addSymbol()` (`app/templates/index.html:362`), `#q` keydown→`runSearch()` (`app/templates/index.html:363`).

Plus 2 boot-time top-level calls that must run *after* their target functions are loaded: `loadStats()`, `loadWatchlist()` (`app/templates/index.html:365-366`).

**DOM IDs referenced by `$('#...')` lookups — full list, verified by direct read (line = first/defining occurrence):**
`strip`(85), `s-bars`(86), `s-metrics`(87), `s-articles`(88), `s-chunks`(89), `s-signals`(90), `s-latest`(91), `v-watchlist`(103), `new-symbol`(107), `wl-err`(110), `wl-body`(114), `detail-panel`(116), `detail-title`(117), `detail-body`(118), `v-search`(123), `q`(127), `q-ticker`(128), `q-err`(131), `q-body`(135), `v-signals`(140), `sig-ticker`(144), `sig-body`(147), `v-notes`(152), `note-ticker`(156), `note-text`(158), `note-err`(160), `notes-body`(164), `v-reports`(169), `rep-body`(172).

**`data-view` values (drive tab-switch array at `app/templates/index.html:198`):** `watchlist`(95), `search`(96), `signals`(97), `notes`(98), `reports`(99).

**Classes referenced by JS or forming the tab-switch/error contract:** `.hide` (defined `app/templates/index.html:72`, toggled by tab-switch at line 199 and used as initial state on `#v-search`/`#v-signals`/`#v-notes`/`#v-reports`/`#detail-panel`), `.tab`/`.tab.on` (94-99, 30-34), `.err` (70-71, applied at 110/131/160), `.empty` (70).

**Verify with (before AND after the restructure — outputs must match exactly on the ID list):**
```bash
grep -oE 'id="[a-zA-Z0-9_-]+"' app/templates/index.html | sort -u
grep -oE 'onclick="[a-zA-Z]+' app/templates/index.html | sort -u
grep -oE "data-view=\"[a-zA-Z]+\"" app/templates/index.html | sort -u
```

### Pitfall 1: Restructuring script scope breaks `onclick="..."` handlers

**What goes wrong:** Wrapping the split script in `type="module"` or an IIFE un-exposes the 7 functions above from `window`. Buttons render fine, do nothing on click — invisible in a screenshot review. [CITED: `.planning/research/PITFALLS.md` Pitfall 1, HIGH confidence — verified against this codebase]

**How to avoid:** Classic (non-module, non-IIFE) `<script src>` per file, per D-01. See `## Architecture Patterns` Pattern 1.

**Warning signs:** Browser console shows `Uncaught ReferenceError: <fn> is not defined` on click; the pre/post `onclick=` grep above returns a different set.

### Pitfall 2: Renaming/removing DOM IDs, `.hide`, or `data-view` breaks tab switching

**What goes wrong:** A "cleaner semantics" rename (e.g. `#wl-body` → `#watchlist-table-container`) or swapping `.hide` for a different utility class breaks the entire markup↔behavior wiring, silently — no framework enforces this contract. [CITED: `.planning/research/PITFALLS.md` Pitfall 2, HIGH confidence]

**How to avoid:** D-07 already locks this: additive-only. Run the pre/post ID diff above before considering the phase done.

**Warning signs:** A tab click shows/hides the wrong panel or nothing; a panel stays stuck on "Loading…" because its target ID no longer resolves and the `catch` block's own `$('#...-body')` write also silently fails.

### Pitfall 3: Stale cached static assets after Databricks Apps deploy

**What goes wrong:** `app/static/` currently ships zero tracked assets — this is genuinely new territory for this repo's deploy path. Flask's default static handler sets `ETag`/`Cache-Control` but does **not** auto-append a cache-busting query string; a browser (or a caching proxy in front of the Databricks Apps URL) may keep serving a stale `main.js`/`tokens.css` after redeploy. [CITED: `.planning/research/PITFALLS.md` Pitfall 5, `.planning/research/ARCHITECTURE.md` §Pitfalls item 1 — MEDIUM confidence, general Flask/Werkzeug behavior]

**How to avoid:** Manual `?v=` query string on every `<link>`/`<script>` tag, bumped by hand each deploy (see Pattern 1's code example) — this is D-02's own basis for the "hard-refresh/incognito against the live app" verification step. After first deploy of `app/static/` files, hit the asset URL directly (e.g. `https://<app-url>/static/css/tokens.css?v=1`) to confirm a 200 before trusting the visual check.

### Pitfall 4 (new this phase): Accidentally using `defer`/`async` without checking it doesn't change classic-script global scope

**What goes wrong:** A planner or implementer might reach for `<script defer src="...">` in `<head>` to "clean up" script placement (deferred scripts don't block parsing and run in order before `DOMContentLoaded`). `defer` alone does **not** change classic-script global-scope behavior (unlike `type="module"`), so it's actually safe — but it's an unforced, untested change with no benefit for this phase, since the existing pattern (scripts at the end of `<body>`, after the DOM they query already exists) already works correctly today.

**How to avoid:** Keep script tags at the end of `<body>`, mirroring today's placement exactly, unless there's a concrete reason to move them. Do not introduce `defer` as a "nice to have" without deliberate testing — it's an unverified-this-session claim `[ASSUMED]` that `defer` preserves global scope for classic scripts (well-established browser behavior, but not fetched from an authoritative source this session).

**Phase to address:** This phase, if `<head>` placement is considered — otherwise moot.

## Code Examples

### Full onclick-preserving markup port (Watchlist "Add" button, unchanged ID/class/onclick)

```html
<!-- app/templates/index.html — UNCHANGED structurally, only CSS classes may gain additive card treatment -->
<div class="panel">
  <h2>Add ticker</h2>
  <div class="row">
    <input id="new-symbol" placeholder="AAPL" maxlength="10" autocomplete="off">
    <button onclick="addSymbol()">Add to watchlist</button>
  </div>
  <div id="wl-err" class="err hide"></div>
</div>
```
[VERIFIED: app/templates/index.html:104-111 — quoted verbatim; the `id="new-symbol"`, `onclick="addSymbol()"`, `id="wl-err"`, and `class="err hide"` values must all survive the restructure unchanged.]

### Existing `.tag` base to extend (verbatim, not to be replaced)

```css
.tag{font-family:var(--mono);font-size:9px;letter-spacing:.08em;text-transform:uppercase;
  padding:2px 7px;border-radius:2px;border:1px solid currentColor}
.tag.strong{color:var(--down)} .tag.material{color:#b4670c} .tag.routine{color:var(--muted)}
.tag.positive{color:var(--up)} .tag.negative{color:var(--down)} .tag.neutral{color:var(--muted)}
.tag.agent{color:var(--accent)} .tag.human{color:var(--muted)}
```
[VERIFIED: app/templates/index.html:59-63 — quoted verbatim. `components.css`'s `.tag` rule should extend this set (e.g. add `border-radius:var(--radius-sm)` on the base `.tag` selector), not redefine the modifier class names, since `tag.strong/material/routine/positive/negative/neutral/agent/human` are all referenced from template literals in the current inline script (`app/templates/index.html:229,274,289,311,322`).]

## State of the Art

| Old Approach (project-level ARCHITECTURE.md, 2026-08-10) | Current Approach (locked this phase, 2026-08-11) | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `<script type="module" src="main.js">`, ES `import`/`export` across files | Classic `<script src="...">` per file, plain global function declarations, no `import`/`export` | CONTEXT.md D-01, discuss-phase session 2026-08-11 | Planner must NOT use module syntax anywhere in this phase's JS files — every `onclick="..."` in the rendered HTML depends on functions being global. This is the single most important divergence between prior project research and this phase's locked plan. |

**Deprecated/outdated for this phase specifically:** the ES-module file-split example code in `.planning/research/ARCHITECTURE.md` (its `## Recommended Project Structure` and Pattern 1 code samples use `export`/`import`) — structurally still a good file-split *shape* (the `api.js`/`components/*.js`/`tabs/*.js`/`main.js` directory layout is unaffected and should be reused), but every code sample's `export`/`import` keyword must be dropped when implementing.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|-----------------|
| A1 | Classic script late-binding/global-scope behavior (functions in later-loaded files are callable from `onclick` handlers regardless of file load order, since `onclick` fires after all scripts finish loading) | Architecture Patterns, Pattern 1 | Low — this is standard, decades-old browser behavior; if wrong, symptom is an immediate, obvious `ReferenceError` on first click, caught trivially by D-02's manual walkthrough |
| A2 | Specific spacing/radius/shadow token pixel values (`--space-*`, `--radius-*`, `--shadow-*`) and the `auto-fit`/`auto-fill` minmax breakpoint widths suggested | Architecture Patterns, Patterns 4-5 | Low — purely aesthetic, explicitly Claude's Discretion per CONTEXT.md; wrong values just mean a visual tweak, no functional break |
| A3 | `defer` attribute preserves classic-script global-scope behavior (only changes timing, not scoping) | Common Pitfalls, Pitfall 4 | Low-Medium — flagged explicitly as untested this session; mitigated by the recommendation to NOT use `defer` this phase (keep current end-of-body placement) unless separately verified |
| A4 | Specific indigo/blue accent hex values suggested by web search (`#4a5fd6`–`#7243ed` family) as a starting point for D-04's accent direction | Architecture Patterns / Sources | Low — the codebase already has a real, working accent value (`--accent:#1d6fe0`, verified `app/templates/index.html:11`) that already satisfies "cool blue"; treat web-sourced hex suggestions as optional inspiration for shifting toward "indigo," not a mandate to replace the existing token |

## Open Questions

1. **Should the existing `--accent:#1d6fe0` value be kept as-is or shifted toward a more purple-leaning indigo to satisfy D-04's "indigo" framing more literally?**
   - What we know: `--accent:#1d6fe0` is a cool blue already in production use (`.sym:hover`, `.hit a`, `.tag.agent`) — it already satisfies "trustworthy/analytical, not colliding with red/green," which is D-04's actual stated rationale.
   - What's unclear: whether "indigo" in D-04 was meant as a literal hue shift or just a category label for "not-green-not-red cool accent," which the current value already is.
   - Recommendation: keep `--accent` as-is (zero risk, zero regression surface) unless the planner/user specifically wants a more purple-shifted hue during implementation — this is a one-line CSS custom-property change either way, low-cost to revisit later, not worth gating the phase plan on.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Python 3 | Local Flask dev server (`python app.py`) for pre-deploy manual verification | ✓ | 3.9.6 | — |
| Flask (per `app/requirements.txt`) | Serves `app/static/` + renders `index.html` | Not verified installed in this session's environment (requires `pip install -r app/requirements.txt` in the app's own venv) | `>=3.0.3` pinned in `app/requirements.txt` | Standard `pip install` in a project venv — not a phase-blocking gap |
| `databricks` CLI | D-02's mandatory live-deployed-app verification (`databricks apps deploy`) | ✗ — not found on this research session's PATH | — | No fallback for the *live* verification D-02 requires; this is expected — D-02 already frames deploy+verify as a manual human step outside automated planning/execution, using the user's own configured Databricks CLI/credentials. Not a new gap this research introduces, just confirming the local research environment can't perform that step itself. |

**Missing dependencies with no fallback:** None blocking *planning* — the `databricks` CLI gap only affects the final manual D-02 verification step, which was already scoped as a human action, not something the phase's automated plan/execute loop performs itself.

**Missing dependencies with fallback:** Flask itself — install via the project's existing `app/requirements.txt` in a local venv for any local dev-server verification before the live-deploy check.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|-----------------|---------|---------------------|
| V2 Authentication | No | Unchanged this phase — `_user()` helper and any auth logic live in `app/app.py`, out of scope (zero backend diff) |
| V3 Session Management | No | Unchanged this phase |
| V4 Access Control | No | Unchanged this phase |
| V5 Input Validation / Output Encoding | Yes | The existing `esc()` HTML-escaping helper (`app/templates/index.html:181`, `const esc = s => (s ?? '').toString().replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));`) must be ported into the new JS split (likely into `api.js` or a small shared helper loaded first) and continued to be used for every API-sourced string interpolated into `innerHTML` — ticker symbols, headline titles, note text, sentiment labels, all ultimately API/third-party-sourced data |
| V6 Cryptography | No | Unchanged this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Reflected XSS via unescaped API-sourced content re-interpolated into a new/moved render function during the file split (e.g. `components/table.js` forgetting to call `esc()` on a cell value that the original inline code did escape) | Tampering / Information Disclosure | Every render function in `components/*.js`/`tabs/*.js` that interpolates a value originating from an `/api/*` response into an HTML string must route that value through the ported `esc()` helper — this is a mechanical port risk specific to this phase (splitting one big template-literal block into many smaller ones raises the chance one call site drops the `esc()` wrap), not a new vulnerability class. [CITED: `.planning/research/PITFALLS.md` §Security Mistakes, HIGH confidence — verified against this codebase; headline titles originate from the third-party Massive news API and are explicitly untrusted] |

## Sources

### Primary (HIGH confidence)
- `app/templates/index.html` (read in full this session) — exact IDs, classes, `data-view` values, function names/line numbers, existing CSS token set, existing `.tag`/`esc()` implementations
- `app/app.py` (grepped this session, lines 12,17,53) — confirmed `Flask(__name__)` default static registration, no custom `static_url_path`, `render_template("index.html", user=...)` unchanged
- `.planning/phases/01-static-asset-restructure-design-system-foundation/01-CONTEXT.md` — locked decisions D-01 through D-08
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` (Phase 1 section, read this session) — STYLE-01 mapping, exact Success Criteria wording including the zero-backend-diff file list
- `.planning/codebase/STRUCTURE.md` — confirmed `app/static/` currently empty of tracked assets

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` (project-level, 2026-08-10) — file-split shape reused; its ES-module recommendation is explicitly superseded by D-01 for this phase (see `## State of the Art`)
- `.planning/research/STACK.md` (project-level, 2026-08-10) — native-CSS recommendation, no-Tailwind decision
- `.planning/research/PITFALLS.md` (project-level, 2026-08-10) — Pitfalls 1, 2, 5, and the Security Mistakes table, all verified against this codebase in that document
- WebSearch: "multiple classic script src tags share global function declarations browsers load order" — cross-checked late-binding/global-scope behavior
- WebSearch: "SaaS dashboard design tokens spacing scale type scale border-radius box-shadow elevation Linear Vercel Stripe" — token-value conventions
- WebSearch: "native CSS card layout patterns CSS Grid custom properties no framework" — Grid auto-fill/minmax pattern
- WebSearch: "indigo blue accent color hex palette fintech SaaS dashboard design" — D-04 palette direction, not a locked spec

### Tertiary (LOW confidence)
- None retained as authoritative — all web-search findings above were cross-checked against multiple aggregated results (`--verified` confidence tier) before being cited.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; confirming existing project-level decisions against directly-read source
- Architecture (classic-script wiring, DOM contract inventory): HIGH — verified directly against `app/templates/index.html` this session, with exact line citations
- Design-token specific values (spacing/radius/shadow/hex numbers): MEDIUM — web-search cross-checked, explicitly Claude's Discretion per CONTEXT.md, low functional risk if adjusted
- Pitfalls: HIGH for codebase-specific findings (onclick/DOM-ID contract, verified this session and found a discrepancy in CONTEXT.md's own handler count); MEDIUM for general Flask/Databricks caching behavior

**Research date:** 2026-08-11
**Valid until:** 2026-09-10 (30 days — stable web-platform/Flask behavior; re-verify design-token numeric suggestions sooner if the visual direction changes)
