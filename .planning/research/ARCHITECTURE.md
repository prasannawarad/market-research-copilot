# Architecture Research

**Domain:** No-build-step vanilla-JS/CSS frontend, served as static assets by an existing Flask app (Databricks Apps deployment)
**Researched:** 2026-08-10
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser                                                              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ index.html (shell only: <head> links, tab nav markup, 5 empty   │ │
│  │ view containers, one <script type="module" src="/static/js/     │ │
│  │ main.js">)                                                       │ │
│  └───────────────────────────┬────────────────────────────────────┘ │
│                               │ ES module imports (native, no bundler)│
│  ┌────────────────────────────▼───────────────────────────────────┐ │
│  │ main.js  (boot + tab router)                                     │ │
│  │   imports → api.js, render/*.js, components/*.js, state.js       │ │
│  └───────────────────────────┬────────────────────────────────────┘ │
│         ┌─────────────────────┼─────────────────────┐                │
│         ▼                     ▼                     ▼                │
│  ┌─────────────┐     ┌────────────────┐     ┌────────────────────┐  │
│  │ api.js       │     │ components/*.js │     │ tabs/*.js           │  │
│  │ one fetch     │     │ statTile.js     │     │ watchlist.js        │  │
│  │ wrapper per   │     │ table.js        │     │ search.js           │  │
│  │ /api/* route  │     │ chart.js        │     │ signals.js          │  │
│  │               │     │ tag.js, err.js  │     │ notes.js, reports.js│  │
│  └─────────────┘     └────────────────┘     └────────────────────┘  │
│                               │                                       │
│                               ▼                                       │
│                    Chart.js (CDN <script>, global `Chart`)            │
└───────────────────────────────┬───────────────────────────────────────┘
                                 │ fetch('/api/...')  — UNCHANGED contract
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Flask app (app/app.py) — locked, out of scope this milestone         │
│  serves index.html (render_template) + /static/* (Flask's built-in    │
│  static handler) + all /api/* JSON routes                             │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|-------------------------|
| `index.html` (template) | Page shell: `<head>` (CSS `<link>`s, Chart.js CDN `<script>`), header strip markup, tab nav buttons, 5 empty `<div id="v-*">` mount points, one `<script type="module">` entry tag | Jinja-rendered once per request; Flask still injects `{{ user }}` — the only server-side data left in the template |
| `main.js` | App bootstrap: wires tab-click listeners, mounts the initial (watchlist) tab, owns the tiny in-memory "active tab" state | Native ES module, `<script type="module">`, no bundler needed for import resolution |
| `api.js` | Single `api(url, opts)` fetch wrapper (already exists as ~6 lines in the current inline JS) + one named function per endpoint (`getWatchlist()`, `addToWatchlist(symbol)`, `search(query, ticker)`, etc.) | Thin wrapper over `fetch`, throws on non-2xx, always returns parsed JSON |
| `components/*.js` | Pure render functions: take data in, return an HTML string or DOM node out. No fetch calls, no direct global-state access | `statTile(value, label)`, `dataTable(columns, rows)`, `sparkline(canvasEl, points)`, `tag(value, kind)`, `emptyState(msg)`, `errorState(msg)` |
| `tabs/*.js` (one per tab) | Orchestration for one tab: calls `api.js` functions, calls `components/*.js` renderers, writes the result into that tab's mount `<div>` | `loadWatchlist()`, `loadSignals()`, etc. — this is almost a 1:1 port of the existing `load*()` functions in the inline `<script>` today |
| `state.js` (optional, only if pitfalls demand it) | Tiny module-level object for cross-tab or cross-request state (currently: none needed — each tab re-fetches on activation) | Plain exported `const state = {}` object; no reactive framework |
| CSS files | Design tokens (`:root` custom properties) + layout/components, split by concern | `tokens.css` (colors/spacing/type scale), `layout.css` (shell/tabs/panels/grid), `components.css` (tables/tags/buttons/cards/charts) |
| Chart.js (CDN) | Renders sparklines/trend charts inside a `<canvas>` mounted by a `components/chart.js` helper | Loaded via `<script src="https://cdn.jsdelivr.net/npm/chart.js">` in `<head>`, used as a global `Chart` constructor — no `import` needed, no CORS/module concerns |

## Recommended Project Structure

```
app/
├── app.py                      # unchanged — still render_template("index.html", user=...)
├── templates/
│   └── index.html              # shell only: head, tab nav, 5 empty mounts, ONE module <script> tag
└── static/
    ├── css/
    │   ├── tokens.css           # :root custom properties — colors, spacing, type scale, radii
    │   ├── layout.css           # shell/header/strip/tabs/panel grid — structural, not component-specific
    │   └── components.css       # table, tag, button, card, chart-container, empty/error states
    ├── js/
    │   ├── main.js               # entry point: tab-switch wiring + initial mount (loaded via type="module")
    │   ├── api.js                 # fetch wrapper + one function per /api/* endpoint
    │   ├── components/
    │   │   ├── statTile.js        # renders one header-strip stat cell
    │   │   ├── table.js            # generic sortable-columns table renderer
    │   │   ├── chart.js            # Chart.js mount/destroy helper (canvas lifecycle)
    │   │   ├── tag.js               # status/sentiment/trend pill renderer
    │   │   └── states.js            # loading/empty/error state renderers
    │   └── tabs/
    │       ├── watchlist.js        # loadWatchlist, addSymbol, removeSymbol, showDetail
    │       ├── search.js            # runSearch
    │       ├── signals.js           # loadSignals
    │       ├── notes.js              # loadNotes, saveNote, delNote
    │       └── reports.js            # loadReports
    └── img/ (if any icons/logos added)
```

### Structure Rationale

- **`css/` split by concern, not by tab.** At 5 tabs sharing one visual language (tables, tags, panels, buttons repeat across every tab), a per-tab CSS split would duplicate rules. Splitting by *design layer* (tokens → layout → components) means chart/card work in Phase N can add rules to `components.css` without touching `layout.css`, and a later rebrand only touches `tokens.css`.
- **`js/tabs/` split by tab, `js/components/` split by widget.** This directly answers "one JS file per tab vs. one shared module": do **both**, but for different reasons. `tabs/*.js` mirrors the existing `load*()` functions 1:1 (low-risk, mechanical port from `index.html`'s inline `<script>`) — each tab's file is the *only* thing that changes when that tab's feature changes. `components/*.js` holds the render primitives (`table.js`, `statTile.js`, `chart.js`) that multiple tabs reuse, so a stat tile or table row layout is defined once.
- **`api.js` is one file, not one per tab.** All 5 tabs call the same handful of REST verbs against a locked backend contract (`.planning/PROJECT.md` — no Flask route changes this milestone). One file keeps every fetch call, header, and error-shape assumption in one place — if the backend contract ever needs auditing, there's exactly one file to check against `app/app.py`.
- **No `state.js` unless a pitfall demands it.** The current app has no cross-tab shared state — every tab re-fetches its own data on activation (`loadSignals()` etc. called from the tab-click handler). Introducing a state module before there's a concrete need (e.g., watchlist symbols needed by both the Watchlist tab and a future cross-tab search filter) is premature structure for a 5-tab app. Add it only if a specific feature needs it.
- **`main.js` stays thin.** It should only wire tab-switch listeners and call the right `tabs/*.js` loader — not contain rendering or fetch logic itself. This keeps the "what happens on tab click" logic in one obvious place (mirrors today's `document.querySelectorAll('.tab').forEach(...)` block).

## Architectural Patterns

### Pattern 1: Native ES modules, no bundler

**What:** Split JS into files using standard `export`/`import` syntax, loaded via a single `<script type="module" src="/static/js/main.js">` tag in `index.html`. The browser resolves and fetches each imported file natively — no Webpack/Vite/esbuild, no `package.json`.

**When to use:** Small app (5 tabs, ~10 JS files total), no npm dependency to bundle, project constraint explicitly forbids introducing a build toolchain (`.planning/PROJECT.md`: "No build step / bundler in this repo today... no npm toolchain introduction").

**Trade-offs:**
- Pro: Zero new tooling, zero new deploy step, works exactly with Flask's existing static-file serving, debuggable in devtools with real file names (no sourcemaps needed).
- Pro: Every evergreen browser (and anything Databricks Apps' embedded browser targets) supports `type="module"` natively — this is a 2017+ web-platform feature, not a framework.
- Con: One HTTP request per imported file on cold load (5-10 small files) — irrelevant at this app's traffic/scale (a portfolio demo app, not a high-traffic product); mitigated by HTTP/2 multiplexing which Databricks Apps' proxy provides.
- Con: No JSX/TypeScript/npm-package ecosystem access — not a concern here since Chart.js is loaded via CDN `<script>` as a global, not an npm import.

**Example:**
```javascript
// app/static/js/api.js
export async function api(url, opts) {
  const r = await fetch(url, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || `Request failed: ${r.status}`);
  return body;
}
export const getWatchlist = () => api('/api/watchlist');
export const addToWatchlist = (symbol) =>
  api('/api/watchlist', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol }) });
```
```javascript
// app/static/js/tabs/watchlist.js
import { getWatchlist, addToWatchlist } from '../api.js';
import { dataTable } from '../components/table.js';
import { showError } from '../components/states.js';

export async function loadWatchlist() {
  try {
    const rows = await getWatchlist();
    document.querySelector('#wl-body').innerHTML = dataTable(watchlistColumns, rows);
  } catch (e) { showError('#wl-body', e.message); }
}
```
```html
<!-- index.html -->
<script type="module" src="{{ url_for('static', filename='js/main.js') }}"></script>
```

### Pattern 2: Presentational render functions (component-lite)

**What:** Every reusable visual piece (stat tile, table, tag pill, chart mount) is a pure function: `(data) => htmlString` or `(container, data) => void`. No render function calls `fetch` or reaches into another module's DOM — data flows in as arguments, markup/DOM flows out.

**When to use:** Any markup that appears in 2+ tabs (tables appear in Watchlist/Signals/detail-drill-down; tags appear in Watchlist/Signals/Notes/Reports; stat tiles appear only in the header strip today but the pattern should hold if charts are added per-tab).

**Trade-offs:**
- Pro: Directly solves "charts/cards copy-pasted per tab" — one `table.js` replaces the near-identical `` `<table>...` `` template-literal blocks currently duplicated across `loadWatchlist`, `showDetail`, `loadSignals` in `index.html`.
- Pro: Testable in isolation (even without a test framework, they're easy to eyeball-verify since they're pure functions) and safe to change without touching fetch/tab logic.
- Con: Without TypeScript or PropTypes, there's no compile-time contract on what shape of data a render function expects — mitigate with a one-line JSDoc comment per function documenting expected fields (cheap, no tooling).

**Example:**
```javascript
// app/static/js/components/table.js
export function dataTable(columns, rows, { emptyMsg = 'No data.' } = {}) {
  if (!rows.length) return `<div class="empty">${emptyMsg}</div>`;
  const thead = columns.map(c => `<th class="${c.num ? 'num' : ''}">${c.label}</th>`).join('');
  const tbody = rows.map(r => `<tr>${columns.map(c => c.cell(r)).join('')}</tr>`).join('');
  return `<table><thead><tr>${thead}</tr></thead><tbody>${tbody}</tbody></table>`;
}
```
```javascript
// app/static/js/components/chart.js
// Mounts/destroys a Chart.js instance against a <canvas> — call destroy() before re-render
// to avoid Chart.js's "Canvas is already in use" error on tab re-activation.
const instances = new Map();
export function mountSparkline(canvasEl, points, opts = {}) {
  instances.get(canvasEl)?.destroy();
  const chart = new Chart(canvasEl, {
    type: 'line',
    data: { labels: points.map(p => p.x), datasets: [{ data: points.map(p => p.y), borderWidth: 1.5, pointRadius: 0 }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { display: false } }, ...opts },
  });
  instances.set(canvasEl, chart);
  return chart;
}
```

### Pattern 3: Direct function calls for tab-switch + data flow (no pub/sub)

**What:** Tab click → tab-switch handler in `main.js` toggles `.hide` on the 5 mount `<div>`s (exactly as today) → calls that tab's `load*()` function directly by name. No event bus, no pub/sub, no reactive store.

**When to use:** Always, at this scale. 5 tabs, no cross-tab live updates required (each tab re-fetches fresh data when activated — this already matches current behavior: `loadSignals()`/`loadNotes()`/`loadReports()` are called directly from the tab-click listener).

**Trade-offs:**
- Pro: Zero new concepts to explain in an interview — "tab click calls a function, function fetches and renders" is the whole data-flow story.
- Pro: Matches the existing, working pattern in `index.html` almost exactly — lowest-risk port.
- Con: If a future milestone needs one tab's action to update another tab's already-rendered view (e.g., adding a watchlist symbol should invalidate a cached Signals view) a pub/sub or shared-state layer would help — explicitly **not needed for this milestone** per current requirements (no cross-tab live sync in scope), and premature to build now. Flag this as a "revisit if requirements change" item, not something to build speculatively.

**Example:**
```javascript
// app/static/js/main.js
import { loadWatchlist } from './tabs/watchlist.js';
import { loadSignals } from './tabs/signals.js';
import { loadNotes } from './tabs/notes.js';
import { loadReports } from './tabs/reports.js';
import { loadStats } from './tabs/stats.js';

const TAB_LOADERS = { signals: loadSignals, notes: loadNotes, reports: loadReports };

document.querySelectorAll('.tab').forEach(t => t.onclick = () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('on'));
  t.classList.add('on');
  ['watchlist', 'search', 'signals', 'notes', 'reports'].forEach(v =>
    document.querySelector('#v-' + v).classList.toggle('hide', v !== t.dataset.view));
  TAB_LOADERS[t.dataset.view]?.();   // search has no auto-load: user triggers it explicitly
});

loadStats();
loadWatchlist();
```

## Data Flow

### Request Flow

```
[Tab click]
    ↓
main.js (tab-switch handler)
    ↓ toggles .hide, calls e.g. loadSignals()
tabs/signals.js
    ↓ calls
api.js → fetch('/api/signals?ticker=...')
    ↓
Flask app/app.py route (unchanged) → Lakebase Postgres
    ↓ JSON response
api.js (parses JSON, throws on non-2xx)
    ↓
tabs/signals.js
    ↓ calls
components/table.js (or components/chart.js) → returns HTML string / mounts canvas
    ↓
tabs/signals.js writes result into document.querySelector('#sig-body').innerHTML
```

### State Management

```
No central store. Each tabs/*.js module owns only its own DOM subtree.
main.js owns "which tab is active" (derived from the DOM's .tab.on class — not duplicated in JS state).
Server (Lakebase, via Flask) remains the single source of truth; every tab activation re-fetches.
```

### Key Data Flows

1. **Tab activation → fetch → render:** every tab except Watchlist (which loads on page boot) and Search (which requires user input) fetches on tab-click, never on page load — avoids wasted requests for tabs the user never opens, matches current behavior.
2. **Watchlist row click → drill-down:** `showDetail(ticker)` fetches `/api/metrics/<ticker>` and renders into the existing `#detail-panel` — this is a same-tab, same-module flow (`tabs/watchlist.js` owns both the list and the detail render), not a cross-tab concern.
3. **Mutations (add/remove watchlist symbol, save/delete note) → local re-fetch:** every write (`POST`/`DELETE`) is followed by the *same tab* re-calling its own `load*()` function to refresh from the server — no optimistic UI, no client-side cache invalidation logic needed (matches today's `addSymbol()` → `loadWatchlist()` pattern).

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|---------------------------|
| Current (5 tabs, single demo user, portfolio app) | Exactly the structure above — no framework, no state library, no build step. This is not under-engineering; it matches the actual requirement. |
| If tabs grow past ~8-10 or state needs to be shared live across tabs | Introduce a tiny `state.js` pub/sub (a `Map` of listeners + a `publish(event, data)`/`subscribe(event, fn)` pair, ~20 lines, still no framework) before reaching for a framework. |
| If this ever needs true SPA routing / URL-addressable tabs / offline support | That's a different architecture (framework rebuild) — explicitly out of scope per `.planning/PROJECT.md` ("Full SPA rebuild (React/Vue) — rejected"). Not a natural next step from this structure; would be a deliberate re-platform decision, not an incremental scale-up. |

### Scaling Priorities

1. **First (and only realistic) friction point at this app's scale:** copy-pasted render markup across tabs (already addressed by `components/*.js` above) — not a runtime performance concern.
2. **Second, only if it happens:** duplicated fetch/error-handling logic if new endpoints are added ad hoc outside `api.js` — prevent by convention (every new `/api/*` call goes through a named `api.js` function), not by new infrastructure.

## Anti-Patterns

### Anti-Pattern 1: One giant `app.js` (just moving the inline `<script>` verbatim into a single file)

**What people do:** Cut-paste the existing ~190-line inline `<script>` block into `app/static/js/app.js` and call the refactor done.
**Why it's wrong:** Solves the "inline vs. external file" problem but not the actual maintainability problem — table-rendering, tag-rendering, and fetch logic stay interleaved and duplicated across `loadWatchlist`, `showDetail`, `loadSignals`, exactly as today. Adding a chart later means finding-and-copying a chart snippet into 2-3 more places.
**Do this instead:** Split along the `components/` (reusable render) vs. `tabs/` (per-tab orchestration) vs. `api.js` (data access) boundaries above — each new feature (a chart, a new tab) has one obvious place to add code and one obvious place to reuse it from.

### Anti-Pattern 2: Introducing a client-side router, state-management library, or virtual DOM

**What people do:** Reach for a small framework (Alpine.js, htm+preact, a hand-rolled virtual-DOM diffing layer) "to keep it clean."
**Why it's wrong:** Explicitly contradicts the milestone's own constraint (no build step, no npm toolchain, "keeps the change explainable and low-risk" per `.planning/PROJECT.md`) and adds a dependency + a debugging surface for a 5-tab app with no complex shared state. In a job-interview context, "why did you add a state library for 5 static-ish tabs" is a harder question to answer well than "direct function calls were sufficient at this scale."
**Do this instead:** Plain `innerHTML` re-render per tab activation (current pattern, proven to work) + the render-function split above. Revisit only if a concrete future requirement (live cross-tab sync, URL-addressable tab state) demands it.

### Anti-Pattern 3: Hardcoding `/static/...` paths instead of `url_for('static', ...)`

**What people do:** Write `<link rel="stylesheet" href="/static/css/tokens.css">` and `<script src="/static/js/main.js">` directly in `index.html`.
**Why it's wrong:** Bypasses Flask's URL-building — if the app is ever served behind a path prefix (Databricks Apps can proxy an app under a workspace-specific base path in some configurations) or the static folder location changes, hardcoded paths silently 404 while `url_for` stays correct. It also loses Flask's per-request static-file caching headers wiring (see Pitfalls below), which are only correctly set when the static blueprint's endpoint is used consistently.
**Do this instead:** Always `href="{{ url_for('static', filename='css/tokens.css') }}"` / `src="{{ url_for('static', filename='js/main.js') }}"` in the Jinja template. This is a zero-cost convention, not new infrastructure.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|----------------------|-------|
| Chart.js (charting library) | CDN `<script>` tag in `<head>` (e.g. `https://cdn.jsdelivr.net/npm/chart.js@4`), used as a global `Chart` constructor from `components/chart.js` | No `import`, no npm — matches "CDN-hosted charting library... no npm toolchain" per `.planning/PROJECT.md`. Pin the version in the CDN URL (e.g. `chart.js@4.4.4`, not `@latest`) so a Chart.js breaking release doesn't silently change the live app between deploys — this repo has no lockfile/pinning mechanism for JS, so the CDN URL *is* the pin. |
| Flask static file handler (`app/static/`) | Flask's built-in `static` blueprint, unmodified — no new Flask route code needed | Already correctly scoped by `.planning/PROJECT.md`'s "Backend contract" constraint: adding files under `app/static/` and referencing them via `url_for('static', ...)` is a template/asset change, not a route change, so it does not touch the locked `app/app.py` contract. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|----------------|-------|
| `index.html` (Jinja template) ↔ `main.js` | One `<script type="module">` tag; Jinja injects only `{{ user }}` into the header markup, nothing else — no server-rendered data is threaded into JS via inline `<script>` blocks | Keeps the template a pure shell; if more server-rendered data is ever needed client-side, use a `data-*` attribute on a DOM node (e.g. `<body data-user="{{ user }}">`) rather than reintroducing an inline `<script>` block, to keep CSP-friendliness if that's ever added. |
| `tabs/*.js` ↔ `api.js` | Direct function import/call, `async`/`await` | `api.js` is the *only* module that calls `fetch()` against `/api/*` — this is the enforced boundary that keeps the JSON-contract surface auditable against `app/app.py` in one place. |
| `tabs/*.js` ↔ `components/*.js` | Direct function import/call; components take data + return markup/mount, never fetch | One-directional: `components/` never imports from `tabs/` or `api.js` — keeps render functions reusable and testable in isolation. |
| Flask (`app/app.py`) ↔ frontend | REST JSON over `/api/*`, response shapes locked this milestone | No change to request/response contract; this is a pure presentation-layer restructuring on top of an unchanged API. |

## Pitfalls Specific to Flask-on-Databricks-Apps Static Serving

These are the concrete, deployment-specific risks for this milestone (verified against Flask's documented static-file behavior and the project's own deployment description in `.planning/codebase/ARCHITECTURE.md`/`STACK.md`):

1. **No built-in cache-busting on `url_for('static', ...)`.** Flask's default static handler serves files via `send_from_directory`, which sets `ETag`/`Last-Modified` and a `Cache-Control` max-age (Werkzeug default), but `url_for('static', filename=...)` does **not** append a content hash or version query string automatically (that requires an extension like Flask-CacheBust, or Webpack-style asset hashing — both introduce tooling this project has ruled out). **Consequence:** a browser (or Databricks' front-door proxy, if it caches) may keep serving a stale `main.js`/`tokens.css` after a deploy. **Mitigation without new tooling:** append a manual version query string in the template, e.g. `?v=2026-08-10-1` or `?v={{ config.get('ASSET_VERSION', '1') }}`, bumped by hand (or from a simple env var set at deploy time) each time static assets change. This is a one-line convention, not new infrastructure — cheap enough to do every deploy of this milestone.
2. **Single-process Werkzeug dev server serves static files too — fine at this scale, but not "production-grade" static serving.** `.planning/PROJECT.md`/`STACK.md` confirm the app runs as `python app.py` under Werkzeug's built-in dev server (`app.run(...)`), not Gunicorn/nginx. Flask's static handler works correctly here (this is standard Flask behavior, not a Databricks-specific limitation), but every static request is served by the same single process handling API requests — at this app's demo/portfolio traffic level this is a non-issue; flag it only if traffic assumptions ever change (out of scope this milestone).
3. **Always use `url_for('static', filename=...)`, never a hardcoded `/static/...` path**, in case Databricks Apps' proxy layer ever serves the app under a non-root base path in some workspace configurations — `url_for` builds the correct URL regardless; a hardcoded path silently breaks if that assumption changes. (Anti-Pattern 3 above.)
4. **Chart.js CDN load must not block/break the page if the CDN is unreachable.** Since the CDN `<script>` is a hard dependency for any chart-mounting code, guard chart-mount calls with a `typeof Chart !== 'undefined'` check (or an `onerror` fallback rendering the existing plain-number/table view) so a CDN outage degrades to "no chart" rather than a JS error that breaks tab-switching for the whole page. This directly serves the project's own "must degrade gracefully for missing data" principle (`.planning/PROJECT.md`), extended to "missing chart library" as the same class of failure.
5. **`Chart.js` canvas reuse on tab re-activation.** Because tabs are toggled via `.hide` (DOM stays mounted, not destroyed/recreated), re-rendering a chart on repeated tab visits without destroying the previous `Chart` instance throws `Canvas is already in use`. `components/chart.js`'s `instances.get(canvasEl)?.destroy()` pattern above is the standard fix — this is a Chart.js-specific gotcha, not a Flask/Databricks one, but it's the most likely first bug encountered once charts are added to a tab that gets revisited.
6. **ES module `<script type="module">` is deferred by default** — it won't block HTML parsing and runs after the DOM is parsed, so (unlike the current inline `<script>` at the bottom of `<body>`) there's no need to worry about script placement relative to the DOM nodes it queries; it can safely live in `<head>` too. This is a minor simplification opportunity during the port, not a pitfall, but worth knowing so the port doesn't defensively (and needlessly) preserve the current "script at the end of body" placement out of habit.

## Sources

- `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`, `.planning/codebase/STACK.md` (this repo — HIGH confidence, verified against current code)
- `app/templates/index.html`, `app/app.py`, `app/app.yaml` (read directly — HIGH confidence, current state as of 2026-08-10)
- [Flask Static Files documentation](https://flask.palletsprojects.com/en/stable/tutorial/static/) — MEDIUM confidence (official docs, general Flask behavior, not Databricks-specific)
- [Configure Databricks app execution with app.yaml (Databricks Learn)](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/databricks-apps/app-runtime) — MEDIUM confidence (official docs; did not surface Databricks-specific static-caching behavior beyond standard Flask/Werkzeug defaults, treated as "no special Databricks override" rather than confirmed absence)
- [Deploy a Databricks app (Databricks docs)](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy) — MEDIUM confidence
- General ES modules (`<script type="module">`), Chart.js CDN usage, and Flask cache-busting extension landscape (Flask-CacheBust, Flask-Autoversion) — MEDIUM confidence, standard/stable web-platform and Flask-ecosystem knowledge cross-checked via web search 2026-08-10

---
*Architecture research for: no-build-step vanilla-JS/CSS frontend restructuring on a locked Flask backend*
*Researched: 2026-08-10*
