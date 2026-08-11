# Pitfalls Research

**Domain:** Frontend-only visual redesign of a live, working server-rendered app (Flask + vanilla JS on Databricks Apps) with a hard "don't touch the backend" constraint
**Researched:** 2026-08-10
**Confidence:** HIGH for codebase-specific findings (verified directly against `app/templates/index.html`, `app/app.py`, `app/app.yaml`); MEDIUM for general CDN/Chart.js/Databricks-Apps-deploy ecosystem practices (established web/platform conventions, lightly web-verified this session, not Databricks-support-confirmed)

## Critical Pitfalls

### Pitfall 1: Restructuring `<script>` scope breaks every inline `onclick="..."` handler

**What goes wrong:**
The current page wires every interactive control through inline HTML attributes calling global functions: `onclick="addSymbol()"`, `onclick="removeSymbol('${esc(r.symbol)}')"`, `onclick="showDetail('${esc(r.symbol)}')"`, `onclick="runSearch()"`, `onclick="loadSignals()"`, `onclick="delNote(${r.note_id});return false"` (`app/templates/index.html:108,159,228,235,145,228,324,341-345` etc.), plus tab click handlers wired via `document.querySelectorAll('.tab').forEach(t => t.onclick = ...)`. A design-system pass commonly "cleans up" the script — wrapping it in an IIFE, switching to `<script type="module">`, or splitting it into a separate `app/static/app.js` loaded with `type="module"` for ES-import ergonomics. Any of these silently un-expose `addSymbol`, `removeSymbol`, `showDetail`, `runSearch`, `loadSignals`, `delNote` from the global (`window`) scope. The buttons render fine, look fine, and do nothing when clicked — a failure mode invisible in a static screenshot review.

**Why it happens:**
Module scripts and IIFE-wrapped scripts do not leak top-level function declarations onto `window` the way a plain classic `<script>` block does. Developers used to modern bundler conventions reach for `type="module"` reflexively without checking what the markup depends on.

**How to avoid:**
Either (a) keep the script a classic (non-module) `<script>` block — inline or moved to `app/static/app.js` via a plain `<script src="...">` tag, no `type="module"` — so the six functions above stay on `window`; or (b) if switching to modules/an IIFE, replace every inline `onclick="..."` in the generated HTML strings and the static markup with `addEventListener` calls wired up after render, and explicitly re-attach the two `addEventListener` calls at the bottom of the script (`#new-symbol` Enter-key handler, `#q` Enter-key handler) since those also assume the DOM exists at script-execution time.

**Warning signs:**
- Clicking "Add to watchlist", a row's ticker symbol, "Remove", the search button, "Apply" (signals), or "delete" (notes) does nothing and the browser console shows `Uncaught ReferenceError: addSymbol is not defined` (or similar) on click.
- A quick `grep -o 'onclick="[a-zA-Z]*' app/templates/index.html` before and after a redesign pass should return the same six function names either way (as inline handlers) — if that grep returns nothing after the redesign, the handlers were removed/replaced and must be re-verified as `addEventListener`-wired.

**Phase to address:**
Whichever phase first touches `app/templates/index.html`'s `<script>` block (the design-system/markup pass). Should be an explicit acceptance check in that phase's UAT, not assumed to be free because "only CSS changed."

---

### Pitfall 2: Renaming/removing DOM IDs, the `.hide` class, or `data-view` attributes breaks tab switching and every `$('#...')` lookup

**What goes wrong:**
All data rendering is keyed by ID lookups through a `$ = s => document.querySelector(s)` helper: `#wl-body`, `#q-body`, `#sig-body`, `#notes-body`, `#rep-body`, `#detail-panel`, `#detail-title`, `#detail-body`, `#s-bars`/`#s-metrics`/`#s-articles`/`#s-chunks`/`#s-signals`/`#s-latest`, `#wl-err`/`#q-err`/`#note-err`, `#new-symbol`, `#q`, `#q-ticker`, `#sig-ticker`, `#note-ticker`, `#note-text`. Tab switching depends on two more contracts: each tab button's `data-view="watchlist|search|signals|notes|reports"` attribute, and each panel's ID following the `#v-<view>` pattern (`#v-watchlist`, `#v-search`, `#v-signals`, `#v-notes`, `#v-reports`), toggled via the `.hide` CSS class (`app/templates/index.html:195-203`, `.hide{display:none}` at line 72). A visual redesign that renames a container div for cleaner semantics (e.g. `#wl-body` → `#watchlist-table-container`), swaps `.hide` for a different utility class name (e.g. adopting a small CSS framework's own `.d-none` or `hidden` attribute), or renumbers/renames `data-view` values without updating the JS constant array `['watchlist','search','signals','notes','reports']` in the tab-click handler breaks that surface — with no error thrown in most cases, just silently-empty panels or a tab that never highlights/shows content.

**Why it happens:**
IDs and utility classes look like presentation details during a redesign pass, but here they are the entire wiring between markup and behavior — there is no framework-level binding (no React refs, no Vue `ref`, no data-binding library) enforcing the contract; it's pure string-based DOM lookup.

**How to avoid:**
Treat every `id="..."`, `data-view="..."`, and the `.hide` class name as a fixed contract for this milestone — cosmetic changes (spacing, colors, fonts, layout) are safe; renaming any ID/class referenced from the `<script>` block is not, unless the corresponding JS is updated in the same edit. Before/after a markup pass, run `grep -oE "id=\"[a-zA-Z0-9_-]+\"" app/templates/index.html | sort -u` and diff the ID list — any ID that disappears must be traced to its `$('#...')` reference and confirmed either removed intentionally (with the JS updated) or preserved.

**Warning signs:**
- A tab click no longer shows/hides the right panel, or shows all panels at once, or none.
- A panel permanently shows "Loading…" (the initial placeholder HTML) because the `load*()` function's `$('#...-body')` selector no longer matches anything and threw inside a `try` block that's swallowed by the `catch` (e.g. `loadWatchlist`, `loadSignals`, `loadNotes`, `loadReports` all wrap in try/catch and only write to `.err` inside `catch` — if the target ID itself is gone, `$('#wl-body').innerHTML = ...` throws `TypeError: Cannot set properties of null`, caught, and written to `#wl-body` again, which also fails and is silently swallowed by the browser's unhandled-in-catch behavior, i.e. blank screen with no visible error).

**Phase to address:**
Design-system/markup phase. Add "tab switching still works for all 5 tabs" and "every panel populates on first load" to that phase's UAT checklist explicitly (see the manual verification checklist in this document).

---

### Pitfall 3: A chart needs a data shape the current API doesn't return, tempting an unplanned backend change mid-phase

**What goes wrong:**
`GET /api/watchlist` (`app/app.py:58-72`) returns exactly one row per ticker — the latest `ticker_metrics` row joined via `LEFT JOIN LATERAL ... LIMIT 1` — so it has no historical series, only a single point-in-time snapshot (close, daily_return, trend, volatility_20d, drawdown_from_high, bar_date). A sparkline or trend chart per watchlist row needs a time series. The only endpoint that returns a series is `GET /api/metrics/<ticker>?days=N` (`app/app.py:110-120`), which is per-ticker, not bulk. Building watchlist sparklines is achievable without touching the backend — call `/api/metrics/<ticker>?days=20` once per visible row (N+1 client-side fetches, bounded by however many tickers are on one user's watchlist, realistically single digits per CONCERNS.md's `max_tickers` cap) — but it is easy to instead reach for "let's just add a bulk `/api/watchlist/history` endpoint that returns all series in one call," which is exactly the kind of backend change PROJECT.md rules out ("New backend features... out of scope," "charts render from existing API responses only").
Similarly, News Signals tab charts (e.g. a volume-z-score or move-size visualization) can only use the fields `GET /api/signals` already returns (`ticker, bar_date, title, sentiment, daily_return, volume_zscore_20d, signal_strength`); anything not in that list (e.g. a full OHLC candle for the signal date) would require a new join server-side.

**Why it happens:**
Chart/visualization requirements are usually specified as "show a trend line for X" without first checking whether an endpoint returns X as a series versus a snapshot. The gap is invisible until someone is mid-implementation of the chart component and reaches for `r.history` on a row object that doesn't have it.

**How to avoid:**
Before the data-visualization phase is planned, explicitly map each planned chart to the exact existing endpoint(s) and field(s) it will consume, and note the fetch pattern (single bulk call vs. N calls to an existing per-item endpoint) in that phase's plan. If a desired chart genuinely has no data path without a new endpoint or new field, treat that as a signal to change scope (simpler chart type, aggregate differently client-side, or explicitly flag it as a phase to discuss with the user rather than quietly adding a route). The watchlist-sparkline-via-N-calls-to-`/api/metrics/<ticker>` pattern above is the concrete, backend-safe path for the most obviously-wanted chart (Watchlist trend/volatility) and should be the default plan, not a fallback.

**Warning signs:**
- Mid-implementation, a `git diff app/app.py` or `git diff app/lakebase.py` in a "just visual" phase is the clearest tripwire — those two files should show zero diff lines for the entire milestone unless a plan explicitly calls it out (per PROJECT.md's own constraint framing).
- A chart spec that references a field name not present in the JSON shapes documented in `app/app.py`'s route bodies above.

**Phase to address:**
Data-visualization phase, at planning time (before implementation) — the phase plan should enumerate each chart's exact source endpoint(s)/field(s) as part of its spec, and the phase's own success criteria should include "no changes to `app/app.py`, `app/lakebase.py`, `mcp_server/*`."

---

### Pitfall 4: A CDN-hosted chart library becomes an unpinned, unmonitored single point of failure with no local fallback

**What goes wrong:**
There is no build step and no `package.json`/lockfile in this repo (confirmed in `.planning/PROJECT.md` and `.planning/codebase/ARCHITECTURE.md`), so a chart library is added as a `<script src="https://cdn.jsdelivr.net/npm/chart.js@X.Y.Z/...">` (or cdnjs equivalent) tag directly in `index.html` or referenced from a new `app/static/app.js`. Two related risks compound here: (1) if the URL uses a floating tag (`@latest`, or no version at all) rather than a pinned semver, a future breaking major-version release on the CDN silently changes the app's behavior on next page load with zero code change on this repo's side — impossible to reproduce locally without noticing the CDN itself changed; (2) if the CDN is down, rate-limited, or blocked by the viewer's network (both jsDelivr and cdnjs are generally reliable but not infallible, and corporate/interview-review networks sometimes block third-party CDNs), every chart-bearing tab breaks with no chart rendering and, if the script tag isn't guarded, a JS error that can halt execution of any inline script below it depending on load order.

**Why it happens:**
CDN script tags feel "free" compared to introducing a bundler, and pinning discipline is easy to skip when copy-pasting a quickstart snippet from the library's own docs (which sometimes shows an unpinned or `@latest` URL for brevity).

**How to avoid:**
- Pin an exact version in the CDN URL (e.g. `chart.js@4.4.1`, not `@4` or `@latest`) — this project's "no lockfile" constraint means the URL itself is the only version pin that exists; treat it as such.
- Add a Subresource Integrity (`integrity="sha384-..."`) attribute and `crossorigin="anonymous"` on the `<script>` tag — the CDN's own site (jsdelivr.net, cdnjs.com) publishes the correct hash for each pinned version; this also guards against a compromised/tampered CDN response.
- Load the script with plain `<script src="...">` (not `defer`/`async` unless the chart-rendering code that depends on it is also deferred to run after `DOMContentLoaded`/`load`), placed before the code that calls `new Chart(...)`, so load-order failures are deterministic rather than a race.
- Because there's no CI/test suite to catch a future CDN outage, this is a "verify once at ship time, re-verify occasionally" risk, not a solved one — document the exact pinned version and CDN provider chosen in the phase's implementation notes so a future incident is fast to diagnose ("charts broken — check if cdn.jsdelivr.net is reachable and the pinned version still resolves").

**Warning signs:**
- Charts render locally during dev but fail after deploy (different network path/proxy behavior between local machine and the Databricks Apps container).
- Browser console shows `Chart is not defined` (script failed to load or loaded after the code that uses it) or a CORS/opaque-response error (missing `crossorigin` attribute alongside SRI).

**Phase to address:**
Data-visualization phase, at the point the chart library is first added — pin + SRI should be part of that phase's implementation, not a follow-up.

---

### Pitfall 5: Databricks Apps deploy syncs the source tree, but browsers aggressively cache static assets with no cache-busting mechanism in this repo today

**What goes wrong:**
`app/static/` currently has no tracked assets (confirmed in PROJECT.md: "currently has no tracked assets beyond `.DS_Store`"), so Flask's default static-file serving (`/static/<path:filename>` — auto-registered by `Flask(__name__)` since no custom `static_url_path` is set in `app/app.py`) has never been exercised in this app. Two distinct risks appear once real CSS/JS files land there: (1) `databricks apps deploy` needs to actually sync new files under `app/static/` to the deployed app's source tree on every deploy — this should work the same as any other tracked file in the app's directory (Databricks Apps deploy syncs the whole source path), but because this is genuinely new territory for this repo, it should be verified once rather than assumed; (2) even once deployed correctly, Flask's default static handler does not fingerprint filenames or set aggressive cache-busting query strings — if `style.css`/`app.js` are referenced with a plain `<link href="/static/style.css">`/`<script src="/static/app.js">` and no version query string, a browser (or the Databricks Apps front-door proxy, if it applies its own caching) that already cached an old copy from a previous visit may keep serving stale CSS/JS after a redeploy, producing an inconsistent "half old, half new" UI that's hard to reproduce and easy to misdiagnose as a code bug.

**Why it happens:**
With no build step there's no automatic content-hashed filename (`app.a3f9c1.js`) the way a bundler would produce — the burden of cache-busting falls on the developer to add manually, and it's easy to forget because local dev (`python app.py` + hard-refresh habits) doesn't surface the staleness the way a first-time visitor's cached browser would after a production redeploy.

**How to avoid:**
- Append a manual version query string to every static asset reference — e.g. `<link rel="stylesheet" href="/static/style.css?v=1">`, bumping `?v=` on every deploy that changes that file's content. This is a one-line-per-file discipline, not a tooling change, and stays consistent with "no build step."
- After the first deploy that introduces `app/static/` assets, explicitly verify (not assume) that `databricks apps deploy` picked up the new files: hit `/static/style.css` (or whatever filename) directly in the browser against the deployed app URL and confirm it 200s with expected content, in addition to visually checking the page.
- Treat every subsequent deploy during this milestone with a hard-refresh (Cmd+Shift+R) or private/incognito window when verifying, to rule out the developer's own browser cache masking a real staleness bug.

**Warning signs:**
- Visual changes don't appear after a `databricks apps deploy`, but a hard refresh / incognito window shows them correctly — confirms browser caching, not a deploy failure.
- Visual changes don't appear even after a hard refresh / incognito window — confirms a deploy-sync problem (new file didn't reach the deployed source tree, or `app/app.yaml`/`app.py` isn't serving it), not a caching problem. Diagnose by hitting `/static/<file>` directly.

**Phase to address:**
First phase that adds any file under `app/static/` — verify the deploy-and-cache round trip once, early, rather than discovering it during a later, harder-to-isolate phase.

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|-----------------|
| Leaving all CSS/JS inline in `index.html` instead of moving to `app/static/` | No new deploy-sync/caching surface to verify (Pitfall 5 doesn't apply) | Harder to diff, harder to reason about what changed per phase, no browser caching benefit for repeat visits | Acceptable for this milestone's scope (single page, no build step) — moving to `app/static/` is a nice-to-have, not required, unless the chart library itself needs a separate file for size/readability reasons |
| Skipping SRI hashes on the CDN `<script>` tag | Faster to wire up | If the CDN is ever compromised, or the pinned version's file is mutated at the CDN edge, the app silently executes different code with no repo-side signal | Never acceptable once a specific version is pinned — SRI is a one-time copy-paste from the CDN provider's own site, effectively free |
| Adding chart rendering logic directly inline in the existing `<script>` block rather than a separate file | Fewer new files, one less deploy-sync surface | `index.html`'s script block grows past ~370 lines into "hard to scan" territory, increasing the odds of an accidental ID/handler breakage (Pitfalls 1–2) going unnoticed in review | Acceptable if the chart logic stays small (a handful of `new Chart(...)` calls); reconsider if it grows past a couple hundred lines |
| Reusing `esc()` for chart tooltip/label text instead of trusting the library's own escaping | One extra function call per label | None — this is strictly correct and should always be done, since Chart.js and most JS chart libs do not HTML-escape by default when rendering into custom tooltip callbacks | Always acceptable; treat as required, not optional (see Security Mistakes below) |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| CDN-hosted chart library (Chart.js or similar) | Floating version (`@latest` or no version) in the `<script src>` URL | Pin an exact semver in the URL; treat the URL as the project's only "lockfile" (Pitfall 4) |
| CDN-hosted chart library | No SRI hash, no `crossorigin` attribute | Copy the `integrity="sha384-..."` hash the CDN provider publishes for the pinned version alongside `crossorigin="anonymous"` |
| Flask static file serving | Assuming a custom static route/config is needed to serve new `app/static/` files | Flask's default `Flask(__name__)` already auto-registers `/static/<path:filename>` from the `app/static/` directory with zero route changes needed — do not add a custom `/static` route or touch `app/app.py` for this |
| Databricks Apps deploy | Assuming a redeploy always shows changes immediately in the browser | Browser and possibly proxy-level caching can mask a successful deploy; verify with a hard refresh/incognito window and a direct hit on the asset URL (Pitfall 5) |
| Chart library + existing tab-switch/`.hide` mechanism | Initializing a `Chart` instance on a `<canvas>` inside a currently-hidden (`display:none`) tab panel | Chart.js (and most canvas-based libs) cannot correctly size a chart in a `display:none` container — either lazy-initialize the chart the first time its tab is shown (mirroring the existing `loadSignals()`/`loadNotes()`/`loadReports()` on-tab-click pattern at `app/templates/index.html:200-202`), or call the library's `.resize()` method when the tab becomes visible |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| N+1 client-side fetches for watchlist sparklines (one `/api/metrics/<ticker>?days=20` call per row) | Watchlist tab feels slow to populate, more so as watchlist grows | Fine at the realistic scale here (a handful of tickers, per `max_tickers` cap in CONCERNS.md); if this ever needs to scale to dozens of tickers, that's a signal for a genuinely new bulk endpoint — which is an explicit, discussed scope change, not something to sneak in | Only matters if watchlist size grows well past single digits; not a concern for this milestone's actual data |
| Re-creating a `Chart` instance on every re-render instead of calling `.update()`/`.destroy()` first | Memory grows on repeated tab switches or watchlist refreshes; old canvas overlays can visually "ghost" behind new ones | Always `chart.destroy()` (or keep a reference and call `.update(newData)`) before re-rendering a chart into the same canvas | Noticeable after a handful of tab switches in one browser session — easy to miss in a single manual-test pass, so include "switch tabs 5+ times" in the verification checklist |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Rendering chart tooltip/label text (ticker symbols, headline titles, sentiment labels) without the existing `esc()` helper | Every other place in this app HTML-escapes user/API-sourced strings before interpolating into innerHTML (`app/templates/index.html:181`, used throughout); chart tooltip callbacks are a new interpolation surface that's easy to forget to escape, reopening an XSS path that doesn't exist today (headline titles ultimately originate from the Massive news API — untrusted third-party content) | Route every chart label/tooltip string that comes from API data through the same `esc()` function before it reaches the DOM; if the chart library escapes automatically in its own tooltip rendering (many do, via `textContent` rather than `innerHTML`), verify that's actually the case for the specific tooltip customization used, don't assume |
| Introducing a CDN script tag without SRI | A compromised or MITM'd CDN response could inject arbitrary JS into a page that has access to the same `fetch()`-reachable API surface as the legitimate app (watchlist writes, notes writes) | SRI hash + `crossorigin="anonymous"` (Pitfall 4) |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Adding chart/loading polish but leaving the existing `alert()`-free but silent error pattern unchanged for chart-specific failures (e.g. chart library fails to load) | User sees a blank space where a chart should be, no `.err` message, no indication anything went wrong — worse than the current all-tables state, which at least shows a text error via `.err` divs | Wrap chart initialization in the same try/catch + `.err`-div pattern already used for every other async data load in this file, so a chart failure degrades to a visible message, not silence |
| Charts that don't account for the "most tickers show N/A for trend/vol/drawdown" reality (per PROJECT.md's Data reality constraint) | A trend chart fed `null`/`undefined` values for most points either throws, renders a flat zero line (misleading — looks like real data), or renders nothing with no explanation | Explicitly design the "sparse/mostly-missing" chart state before implementation: either render a clear "not enough data yet" placeholder per row/chart when data is missing, or only render a chart when a minimum number of real data points exist, falling back to the existing plain-text/N/A treatment otherwise |
| Adding loading spinners/skeletons for one tab's data fetches but not others, so the app feels visually inconsistent | Confusing, feels unfinished/partially polished — worse for "portfolio-grade" perception than uniformly plain | Apply the same loading-state treatment to all five tabs' data loads (`loadWatchlist`, `runSearch`, `loadSignals`, `loadNotes`, `loadReports`) in the same phase, not incrementally across phases |

## "Looks Done But Isn't" Checklist

- [ ] **Tab switching:** Every one of the 5 tabs (Watchlist, Semantic search, News signals, Research notes, Agent reports) shows/hides correctly and its data loads on click — verify by clicking through all 5 in order, then in reverse order (catches accidental duplicate-view bugs from `.hide` class mismatches).
- [ ] **All write actions still work:** Add a ticker to the watchlist, remove a ticker, save a research note, delete a research note, run a semantic search — each of these hits a real `/api/*` POST/DELETE route; a visual-only change must not silently break the click handler wiring (Pitfall 1) or the request body shape.
- [ ] **Missing-data rendering:** At least one watchlist row with `trend`/`volatility_20d`/`drawdown_from_high` as `N/A` (the current real-data majority case per PROJECT.md) renders sensibly — not a broken chart, not a JS error, not a misleading zero.
- [ ] **Chart library load failure is non-fatal:** Simulate the CDN being unreachable (browser devtools → block the CDN's request URL, or throttle to offline mid-load) and confirm the rest of the page (tables, tabs, forms) still functions — a chart failure should never take down the whole page.
- [ ] **No `app/app.py`, `app/lakebase.py`, `app/massive_client.py`, or `mcp_server/*` diff** for any phase in this milestone unless a plan explicitly calls it out — check with `git diff --stat` before each phase's commit.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|-----------------|
| Broken inline `onclick` handlers after a script-scope change (Pitfall 1) | LOW | Revert the `type="module"`/IIFE wrapping, or re-attach handlers via `addEventListener` in a `DOMContentLoaded` block; both are localized to `index.html`'s `<script>` section, no data/DB impact |
| Renamed DOM ID/class breaks tab or data rendering (Pitfall 2) | LOW | `git diff` the specific commit that renamed the ID/class, cross-reference against the `$('#...')` call sites listed in Pitfall 2, restore either the ID or the JS reference |
| Backend scope creep discovered mid-phase (Pitfall 3) | MEDIUM | Stop, do not merge the backend change silently; either descope the specific chart to fit existing data, or explicitly flag the needed backend addition to the user as an out-of-milestone decision per PROJECT.md's Out of Scope section |
| Stale cached assets after deploy (Pitfall 5) | LOW | Bump the `?v=` query string on the affected `<link>`/`<script>` tag and redeploy; instruct verification to always use a hard refresh/incognito window |
| CDN outage/version drift breaks all charts in production (Pitfall 4) | MEDIUM | Swap the CDN URL to an alternate provider (jsDelivr ↔ cdnjs) hosting the same pinned version as a fast mitigation; longer-term, vendor the pinned library file into `app/static/` as a local fallback (still no build step required — it's just a static `.js` file checked into the repo) |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|--------------------|----------------|
| Broken inline `onclick` handlers from script-scope changes | Design-system/markup phase (first phase touching `index.html`'s `<script>` block) | Click every button/link that has an inline `onclick` in the original file (add, remove, ticker-click, search, apply signals filter, delete note) and confirm each still triggers its action |
| Renamed DOM ID/class/`data-view` breaks tab switching or data rendering | Design-system/markup phase | Diff the ID/class list before and after (`grep -oE 'id="[a-zA-Z0-9_-]+"'`); click through all 5 tabs twice |
| Chart needs data the current API doesn't return, tempting a backend change | Data-visualization phase, at planning time | `git diff --stat` shows zero changes to `app/app.py`/`app/lakebase.py`/`mcp_server/*` for the whole phase |
| CDN chart library unpinned/no SRI/no fallback | Data-visualization phase, when the library is first added | Confirm the `<script>` tag has an exact pinned version and an `integrity` attribute before the phase is marked complete |
| Stale cached static assets after Databricks Apps deploy | First phase that adds a file under `app/static/` | Hard-refresh/incognito verification against the live deployed URL, plus a direct hit on the new asset's `/static/...` path |
| Charts silently misrepresent sparse/missing data | Data-visualization phase (or the dedicated missing-data-handling phase, if separated) | Verify against a real watchlist row known to have `N/A` metrics (per PROJECT.md's documented current data reality) |
| No automated tests to catch regressions in watchlist/search/notes | Every phase (cross-cutting) | Run the full manual "Looks Done But Isn't" checklist above before each phase's commit, not just at milestone end |

## Sources

- `.planning/PROJECT.md` (this project — scope, constraints, data reality) — HIGH confidence, primary source
- `.planning/codebase/CONCERNS.md` (this project — tech debt, no test suite, module-level globals) — HIGH confidence, primary source
- `.planning/codebase/ARCHITECTURE.md` (this project — component boundaries, deployment model) — HIGH confidence, primary source
- `.planning/codebase/TESTING.md` (this project — confirms zero test infrastructure) — HIGH confidence, primary source
- `app/templates/index.html`, `app/app.py`, `app/app.yaml` (direct source read, this session) — HIGH confidence, primary source
- General web search on Databricks Apps deploy/sync behavior (docs.databricks.com "Deploy a Databricks app") — MEDIUM confidence, confirms redeploy-required and sync-based deployment model but did not surface Databricks-specific cache-busting guidance; the cache-busting recommendation itself is standard web-platform practice, not Databricks-specific
- General web search on Chart.js CDN version-pinning conventions (jsDelivr/cdnjs package pages, chartjs.org installation docs) — MEDIUM confidence, confirms pinned-version URL syntax is supported by both major CDNs

---
*Pitfalls research for: Frontend-only redesign of a live Flask/vanilla-JS + Databricks Apps app with a locked backend contract*
*Researched: 2026-08-10*
