# Phase 1: Static Asset Restructure & Design System Foundation - Pattern Map

**Mapped:** 2026-08-11
**Files analyzed:** 13 new files + 1 modified file
**Analogs found:** 13 / 13 (all sourced from the single monolithic `app/templates/index.html` — no other static assets exist yet in this repo)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `app/static/css/tokens.css` | config (design tokens) | transform (static values, no flow) | `index.html` inline `<style>` `:root{...}` block (lines 8-14) | exact — verbatim source, extract + extend |
| `app/static/css/layout.css` | config (structural CSS) | transform | `index.html` inline `<style>` shell/mast/strip/tabs/panel rules (lines 15-39, 72-74) | exact — verbatim source |
| `app/static/css/components.css` | component (CSS) | transform | `index.html` inline `<style>` table/tag/hit/note/empty/err rules (lines 40-71) | exact — verbatim source |
| `app/static/js/api.js` | service (fetch boundary) | request-response | `index.html` inline `<script>` `api()`/`showErr()`/helpers (lines 178-193) | exact — verbatim source, mechanical port |
| `app/static/js/components/table.js` | component (pure render fn) | transform | `index.html` inline table-building template literals in `loadWatchlist`/`showDetail`/`loadSignals` (lines 224-236, 264-275, 303-312) | role-match — no dedicated component exists today; extracted from 3 duplicated call sites |
| `app/static/js/components/tag.js` | component (pure render fn) | transform | `index.html` `.tag ${...}` template-literal usages (lines 229, 274, 289, 311, 322) + CSS base (lines 59-63) | role-match — extracted from repeated inline pattern |
| `app/static/js/components/states.js` | component (pure render fn) | transform | `index.html` `showErr()` (lines 190-193) + inline `.empty`/`.err` div literals (lines 221, 237, 263, 286, 294, 302, 313, 319, 326, 350, 359) | role-match — extracted from repeated inline pattern |
| `app/static/js/tabs/watchlist.js` | controller (tab handler) | CRUD | `index.html` `loadWatchlist`, `addSymbol`, `removeSymbol`, `showDetail` (lines 217-277) | exact — verbatim source, mechanical port |
| `app/static/js/tabs/search.js` | controller (tab handler) | request-response | `index.html` `runSearch` (lines 279-295) | exact — verbatim source, mechanical port |
| `app/static/js/tabs/signals.js` | controller (tab handler) | request-response | `index.html` `loadSignals` (lines 297-314) | exact — verbatim source, mechanical port |
| `app/static/js/tabs/notes.js` | controller (tab handler) | CRUD | `index.html` `loadNotes`, `saveNote`, `delNote` (lines 316-345) | exact — verbatim source, mechanical port |
| `app/static/js/tabs/reports.js` | controller (tab handler) | request-response | `index.html` `loadReports` (lines 347-360) | exact — verbatim source, mechanical port |
| `app/static/js/main.js` | controller (boot/wiring) | event-driven | `index.html` tab-switch `.tab` click wiring + `loadStats` + boot calls + 2 `addEventListener` bindings (lines 195-216, 362-366) | exact — verbatim source, mechanical port |
| `app/templates/index.html` (modified) | route/template (Jinja shell) | request-response | itself (before-state) | n/a — file is edited in place, not analog-matched |

## Pattern Assignments

### `app/static/css/tokens.css` (config, transform)

**Analog:** `index.html` lines 8-14 (existing `:root` block)

**Existing tokens to preserve verbatim** (do not rename — `.tag`, `.sym`, `.up`/`.down`/`.flat`, `td.num` reference these directly):
```css
:root{
  --ink:#131a24; --soft:#4b5661; --muted:#7b858f;
  --paper:#fbfbf9; --surface:#fff; --rule:#e4e4dd;
  --up:#2e7a55; --down:#b4362c; --flat:#7b858f; --accent:#1d6fe0;
  --mono:ui-monospace,SFMono-Regular,"SF Mono","JetBrains Mono",Menlo,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;
}
```

**New tokens to add** (per UI-SPEC.md Spacing Scale / Radius & Elevation sections — Claude's Discretion values, additive only):
```css
--space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px;
--space-6:24px; --space-8:32px; --space-12:48px; --space-16:64px;
--radius-sm:4px; --radius-md:8px; --radius-lg:14px;
--shadow-sm:0 1px 2px rgba(19,26,36,.06);
--shadow-md:0 2px 8px rgba(19,26,36,.08);
```
Do not shift `--accent` (kept as `#1d6fe0` per UI-SPEC.md Color section — Open Question resolved to "keep as-is").

---

### `app/static/css/layout.css` (config, transform)

**Analog:** `index.html` lines 15-39, 73-74 (shell/mast/strip/tabs/panel structural rules + the `@media(max-width:760px)` block)

**Core pattern — verbatim rules to relocate and restyle additively** (IDs/classes unchanged, only property values change per UI-SPEC.md):
```css
*{box-sizing:border-box}
body{margin:0;padding:0 20px 80px;background:var(--paper);color:var(--ink);
  font-family:var(--sans);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
.shell{max-width:1040px;margin:0 auto}
.mast{display:flex;align-items:baseline;justify-content:space-between;gap:16px;
  padding:26px 0 12px;border-bottom:1px solid var(--ink);flex-wrap:wrap}
.strip{display:grid;grid-template-columns:repeat(6,1fr);border-bottom:1px solid var(--rule)}
.tabs{display:flex;gap:4px;padding:14px 0;flex-wrap:wrap}
.tab{...} .tab.on{background:var(--ink);border-color:var(--ink);color:var(--paper)}
.panel{background:var(--surface);border:1px solid var(--rule);border-radius:2px;
  padding:18px 20px;margin-bottom:14px}
@media(max-width:760px){.strip{grid-template-columns:repeat(3,1fr)}
  .strip div:nth-child(4){border-left:none;padding-left:0}}
```

**Card restyle target (Pattern 5 from RESEARCH.md)** — `.strip` and `.panel` get card treatment (`--radius-md`, `--shadow-sm`, `border:1px solid var(--rule)` kept):
```css
.strip{
  display:grid;
  grid-template-columns:repeat(auto-fit, minmax(140px, 1fr));
  gap:var(--space-3);
}
.strip > div{
  background:var(--surface); border:1px solid var(--rule); border-radius:var(--radius-md);
  box-shadow:var(--shadow-sm); padding:var(--space-4);
}
.panel{
  border-radius:var(--radius-md); box-shadow:var(--shadow-sm);
}
```

**Hard rule:** `#strip`, `.strip`, `.tabs`, `.tab`, `.tab.on`, `.panel`, `.hide` selectors/IDs must not be renamed — only property values change (D-07).

---

### `app/static/css/components.css` (component, transform)

**Analog:** `index.html` lines 40-71 (input/button/table/tag/hit/note/empty/err rules)

**Verbatim rules to relocate:**
```css
input,select,textarea{...} button{...} button.ghost{...} button.x{...}
table{width:100%;border-collapse:collapse;font-size:14px}
th{...} td{...} td.num,th.num{...}
.sym{font-family:var(--mono);font-weight:600;cursor:pointer}
.sym:hover{color:var(--accent)}
.up{color:var(--up)} .down{color:var(--down)} .flat{color:var(--flat)}
.tag{font-family:var(--mono);font-size:9px;letter-spacing:.08em;text-transform:uppercase;
  padding:2px 7px;border-radius:2px;border:1px solid currentColor}
.tag.strong{color:var(--down)} .tag.material{color:#b4670c} .tag.routine{color:var(--muted)}
.tag.positive{color:var(--up)} .tag.negative{color:var(--down)} .tag.neutral{color:var(--muted)}
.tag.agent{color:var(--accent)} .tag.human{color:var(--muted)}
.hit{...} .note{...} .empty,.err{...}
```

**Extend, don't replace** the `.tag` base (UI-SPEC.md Typography/Color): add `border-radius:var(--radius-sm)` to base `.tag`, switch default `button` background from `--ink` to `--accent` (Color section — accent reserved list item 1), keep all `.tag.*` modifier class names exactly as-is (referenced from render functions in `components/tag.js`).

**Long-text backstop (UI-SPEC.md UI Considerations row):** add `word-wrap:break-word;overflow-wrap:anywhere` to `.note` and `.hit .txt` — untruncated `note_text`/report `answer` text must wrap inside the new card border/shadow.

---

### `app/static/js/api.js` (service, request-response)

**Analog:** `index.html` lines 178-189 (verbatim source, only file with no split needed — one function + helpers)

**Core pattern to port verbatim:**
```javascript
const $ = s => document.querySelector(s);
const pct = v => v == null ? '&ndash;' : (v*100).toFixed(2) + '%';
const num = (v,d=2) => v == null ? '&ndash;' : Number(v).toFixed(d);
const esc = s => (s ?? '').toString().replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
const cls = v => v == null ? 'flat' : (v > 0 ? 'up' : v < 0 ? 'down' : 'flat');

async function api(url, opts) {
  const r = await fetch(url, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || ('Request failed: ' + r.status));
  return body;
}
```
Note: `$`, `pct`, `num`, `esc`, `cls` are shared helpers referenced by every tab/component file — RESEARCH.md recommends housing them here since `api.js` loads first (no deps). Do NOT wrap in an IIFE or module — must stay global (D-01).

**Security note (V5 Input Validation):** `esc()` must be reused in every render function that interpolates API-sourced strings — see Shared Patterns below.

---

### `app/static/js/components/table.js` (component, transform)

**Analog:** duplicated table-building logic across 3 sites in `index.html`:
- `loadWatchlist` table (lines 224-236)
- `showDetail` table (lines 264-275)
- `loadSignals` table (lines 303-312)

**Pattern to extract (currently duplicated, RESEARCH.md Anti-Pattern flag):** a generic `(columns, rows, rowRenderer) => htmlString` or per-table render function pulled out of each `tabs/*.js` call site. Example source excerpt (Watchlist table, to generalize):
```javascript
`<table><thead><tr>
  <th>Symbol</th><th>Trend</th><th class="num">Close</th>...
  </tr></thead><tbody>` + rows.map(r => `<tr>
    <td class="sym" onclick="showDetail('${esc(r.symbol)}')">${esc(r.symbol)}</td>
    ...
  </tr>`).join('') + '</tbody></table>'
```
Each of the 3 tables has different columns — table.js should expose either one generic table-shell helper (header+rows wrapper) called by each `tabs/*.js` file with its own row-mapping logic, or 3 named functions. Exact decomposition is Claude's Discretion (CONTEXT.md) as long as `onclick="showDetail(...)"` / `onclick="removeSymbol(...)"` markup and every `esc()` call survive unchanged.

---

### `app/static/js/components/tag.js` (component, transform)

**Analog:** repeated inline template literal, e.g. `index.html:229`:
```javascript
`<span class="tag ${r.trend === 'up' ? 'positive' : r.trend === 'down' ? 'negative' : 'neutral'}">${esc(r.trend || 'n/a')}</span>`
```
and `index.html:311`: `<span class="tag ${esc(r.signal_strength)}">${esc(r.signal_strength)}</span>`, and `index.html:322`: `<span class="tag ${esc(r.author)}">${esc(r.author)}</span>`.

**Pattern to extract:**
```javascript
// app/static/js/components/tag.js
function tag(value, kind) {
  return `<span class="tag ${kind}">${esc(value)}</span>`;
}
function trendTag(trend) {
  const kind = trend === 'up' ? 'positive' : trend === 'down' ? 'negative' : 'neutral';
  return tag(trend || 'n/a', kind);
}
```
Modifier class names (`strong`, `material`, `routine`, `positive`, `negative`, `neutral`, `agent`, `human`) are locked — CSS in `components.css` already defines them (lines 61-63); do not introduce new modifier names.

---

### `app/static/js/components/states.js` (component, transform)

**Analog:** `index.html` lines 190-193 (`showErr`) plus inline `.empty`/`.err` div literals at lines 221, 237, 263, 286, 294, 302, 313, 319, 326, 350, 359.

**Core pattern to port verbatim (`showErr`):**
```javascript
function showErr(id, msg) {
  const el = $(id); el.textContent = msg; el.classList.remove('hide');
  setTimeout(() => el.classList.add('hide'), 6000);
}
```

**Pattern to extract for empty/error innerHTML states** (currently duplicated per-tab):
```javascript
function emptyState(msg) { return `<div class="empty">${msg}</div>`; }
function errState(err) { return `<div class="err">${esc(err.message)}</div>`; }
```
Copy text for each empty state is locked verbatim per UI-SPEC.md Copywriting Contract (e.g. "No tickers yet. Add one above, then run the Spark pipeline." at `index.html:221`) — states.js should accept the message as a parameter, not hardcode copy, so each `tabs/*.js` call site supplies its own locked string.

---

### `app/static/js/tabs/watchlist.js` (controller, CRUD)

**Analog:** `index.html` lines 217-277 (`loadWatchlist`, `addSymbol`, `removeSymbol`, `showDetail`) — verbatim source, mechanical port only.

**onclick contract preserved:** `onclick="addSymbol()"` (`index.html:108`), `onclick="showDetail('${esc(r.symbol)}')"` (`index.html:228`), `onclick="removeSymbol('${esc(r.symbol)}')"` (`index.html:235`).

**Core CRUD pattern (addSymbol, verbatim):**
```javascript
async function addSymbol() {
  const symbol = $('#new-symbol').value.trim().toUpperCase();
  if (!symbol) return showErr('#wl-err', 'Enter a ticker symbol.');
  try {
    await api('/api/watchlist', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({symbol})});
    $('#new-symbol').value = '';
    loadWatchlist();
  } catch (e) { showErr('#wl-err', e.message); }
}
```

**Error handling pattern (verbatim):**
```javascript
} catch (e) { $('#wl-body').innerHTML = `<div class="err">${esc(e.message)}</div>`; }
```

---

### `app/static/js/tabs/search.js` (controller, request-response)

**Analog:** `index.html` lines 279-295 (`runSearch`) — verbatim source.

**onclick contract preserved:** `onclick="runSearch()"` (`index.html:129`), plus `addEventListener('keydown', ...)` on `#q` (`index.html:363`, wired in `main.js` not here).

---

### `app/static/js/tabs/signals.js` (controller, request-response)

**Analog:** `index.html` lines 297-314 (`loadSignals`) — verbatim source.

**onclick contract preserved:** `onclick="loadSignals()"` (`index.html:145`).

---

### `app/static/js/tabs/notes.js` (controller, CRUD)

**Analog:** `index.html` lines 316-345 (`loadNotes`, `saveNote`, `delNote`) — verbatim source.

**onclick contract preserved:** `onclick="saveNote()"` (`index.html:159` — the handler CONTEXT.md's D-01 initially missed, corrected during research), `onclick="delNote(${r.note_id});return false"` (`index.html:324`).

---

### `app/static/js/tabs/reports.js` (controller, request-response)

**Analog:** `index.html` lines 347-360 (`loadReports`) — verbatim source, no onclick handler (called only from tab-switch and boot wiring in `main.js`).

---

### `app/static/js/main.js` (controller, event-driven — loaded LAST)

**Analog:** `index.html` lines 195-216 (tab-switch wiring + `loadStats`), 362-366 (`addEventListener` bindings + boot calls) — verbatim source.

**Core wiring pattern (verbatim):**
```javascript
document.querySelectorAll('.tab').forEach(t => t.onclick = () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('on'));
  t.classList.add('on');
  ['watchlist','search','signals','notes','reports'].forEach(v =>
    $('#v-' + v).classList.toggle('hide', v !== t.dataset.view));
  if (t.dataset.view === 'signals') loadSignals();
  if (t.dataset.view === 'notes') loadNotes();
  if (t.dataset.view === 'reports') loadReports();
});
```

**Boot pattern (verbatim, must stay last in file/execution order per RESEARCH.md Pattern 1):**
```javascript
$('#new-symbol').addEventListener('keydown', e => { if (e.key === 'Enter') addSymbol(); });
$('#q').addEventListener('keydown', e => { if (e.key === 'Enter') runSearch(); });

loadStats();
loadWatchlist();
```
**Critical ordering constraint:** `main.js` must be the LAST `<script src>` tag in `index.html` — its top-level `loadWatchlist()`/`loadStats()` calls run synchronously the instant the tag is parsed, and will throw `ReferenceError` if `tabs/watchlist.js` hasn't loaded yet.

---

### `app/templates/index.html` (modified — Jinja shell)

**Before/after contract (must diff clean on):**
```bash
grep -oE 'id="[a-zA-Z0-9_-]+"' app/templates/index.html | sort -u
grep -oE 'onclick="[a-zA-Z]+' app/templates/index.html | sort -u
grep -oE "data-view=\"[a-zA-Z]+\"" app/templates/index.html | sort -u
```
Full locked ID/class/data-view inventory is in RESEARCH.md `## Common Pitfalls` → `### Verified Contract Inventory` — do not re-derive, use that table directly.

**New `<head>` pattern:**
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/tokens.css') }}?v=1">
<link rel="stylesheet" href="{{ url_for('static', filename='css/layout.css') }}?v=1">
<link rel="stylesheet" href="{{ url_for('static', filename='css/components.css') }}?v=1">
```

**New end-of-`<body>` script pattern (exact order):**
```html
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
`?v=1` is a hand-bumped literal in the template, NOT sourced from `app.py`/Flask config (zero-backend-diff success criterion).

## Shared Patterns

### `esc()` HTML-escaping (Security, V5)
**Source:** `index.html:181`, ported to `api.js`
```javascript
const esc = s => (s ?? '').toString().replace(/[<>&"]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
```
**Apply to:** every render function in `components/*.js` and `tabs/*.js` that interpolates an API-sourced string into `innerHTML` (ticker symbols, headlines, note text, sentiment/signal labels). This is the phase's #1 security-mistake risk per RESEARCH.md — splitting one template-literal block into many raises the chance a call site drops the `esc()` wrap.

### `api()` fetch wrapper
**Source:** `index.html:184-189`, ported to `api.js`
**Apply to:** every `tabs/*.js` file's network calls — no file besides `api.js` should call `fetch()` directly.

### `showErr()` transient error banner
**Source:** `index.html:190-193`, ported to `states.js` (or `api.js` alongside other shared helpers — Claude's Discretion)
**Apply to:** `watchlist.js` (`addSymbol`/`removeSymbol`), `search.js` (`runSearch`), `notes.js` (`saveNote`/`delNote`)

### Design tokens (colors/spacing/radius/shadow)
**Source:** `tokens.css` (see above)
**Apply to:** `layout.css` and `components.css` — no raw hex/px values permitted outside `tokens.css` (RESEARCH.md Pattern 4 discipline).

### `.tag` badge base class
**Source:** `index.html:59-63`
**Apply to:** `components.css` (base rule) + `components/tag.js` (render function) — extend, do not redefine modifier class names.

## No Analog Found

None — every planned file has direct source material in the single existing `index.html` (either a verbatim block to relocate, or a duplicated inline pattern to extract into a shared function).

## Metadata

**Analog search scope:** `app/templates/index.html` (only pre-existing frontend source file in the repo; `app/static/` confirmed empty except `.DS_Store` per CONTEXT.md/STRUCTURE.md)
**Files scanned:** 1 (monolithic source), cross-referenced against CONTEXT.md, RESEARCH.md, UI-SPEC.md
**Pattern extraction date:** 2026-08-11
