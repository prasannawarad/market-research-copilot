# Stack Research

**Domain:** No-build-step, Flask-rendered financial dashboard frontend elevation (charts + modern CSS, vanilla JS, CDN-only)
**Researched:** 2026-08-10
**Confidence:** MEDIUM (web-search cross-checked across multiple 2026 sources; no official-docs Context7 lookup performed — see Sources)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **lightweight-charts** (TradingView OSS) | 5.2.x | Full-size price/trend charts (Watchlist detail view, per-ticker drilldown if added) | Purpose-built for financial time series: Canvas 2D rendering, native crosshair + price-scale UX that free-tier competitors have to hand-roll, ~45KB, Apache-2.0 license, zero dependencies, ships a standalone UMD build made exactly for `<script src>` no-build-step usage. This is what an interviewer will recognize instantly as "the TradingView library" — high portfolio credibility for a market-research tool. |
| **Chart.js** | 4.5.0 | Sparklines/small multiples in table rows (Watchlist trend column, News Signals rows), any secondary bar/volatility chart | General-purpose, batteries-included, Canvas 2D, MIT-licensed, the most widely recognized "just works" charting library — huge example surface for sparkline-in-table patterns even though it has no first-class sparkline type. Good balance of capability vs config verbosity for many small charts on one page. |
| **Native CSS** (nesting, custom properties, `@property`, container queries) | Baseline 2023-2024, Widely Available | Design system (tokens, component scoping, responsive card grid) inside `index.html`'s `<style>` block, no preprocessor | All four features are Baseline "Widely Available" as of 2025/2026 (Safari 17.2+/Chrome 120+/Firefox 117+, and `@property`/container queries even further back) — the traditional reason to reach for Sass/PostCSS (nesting, variables, responsive component queries) no longer requires a build step. This directly satisfies the "no bundler" constraint while still getting a real design-token system. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lightweight-charts | 5.2.x | Same library as above, used a second way | If a later phase adds a "ticker detail" panel/modal with a larger single-series chart (price + MA5/MA20 overlay), reuse lightweight-charts rather than adding ApexCharts — one charting dependency is easier to defend in an interview than two. |
| None (plain `fetch()` + template literals) | n/a | State/DOM updates for existing tabs (Watchlist, Search, News Signals, Notes, Reports) | Default choice for this milestone. The app already works this way; a redesign pass is not the moment to introduce a new state paradigm across 5 tabs when only visual polish + charts are in scope. |
| Alpine.js (optional, deferred) | 3.x, ~15KB via CDN | Only if a later phase adds several new interactive widgets (tab-scoped filters, sortable columns, toggled panels) that would otherwise mean hand-wiring many `addEventListener` calls | Not recommended for *this* milestone — introduces a second "how do we manage UI state" pattern alongside the existing manual DOM code, adding cognitive surface without solving a problem this milestone has. Revisit only if a future milestone's interactivity requirements grow past what plain `fetch()` + template literals can handle cleanly. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Browser DevTools (Network + Performance tabs) | Manual verification of chart render cost, CDN load, CSS layout — replaces automated tests (none exist in this repo) | Confirmed no test suite/CI/lint exists (`.planning/codebase/TESTING.md`); verification must be manual against local dev server (`python app.py`) or the live Databricks Apps URL. |
| jsDelivr (CDN) | Serves both Chart.js and lightweight-charts pinned-version builds | Preferred over unpkg for this project: jsDelivr resolves version ranges cleanly and has had fewer reported CDN-path issues for lightweight-charts specifically (unpkg has open GitHub issues about broken CDN links for this package). Pin an exact version, never use `@latest` in a portfolio project (reproducibility). |

## Installation

No `npm install` — this project has no `package.json` and none should be added. Add these two `<script>` tags to `app/templates/index.html` (before the existing inline `<script>` block, since it depends on both globals):

```html
<!-- Financial time series charts (Watchlist detail / larger single-series views) -->
<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@5.2.0/dist/lightweight-charts.standalone.production.js"></script>

<!-- General-purpose charts (sparklines / small multiples in table rows) -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.min.js"></script>
```

Both expose a global (`LightweightCharts`, `Chart`) immediately usable from the existing inline `<script>` — no module system, no import maps, no bundler needed. Optionally self-host both files under `app/static/vendor/` (copy the two files once, no build step, still no npm) if the project wants zero external-CDN runtime dependency for the live Databricks Apps deployment — worth flagging as a decision for the roadmap/plan phase, not resolved here.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| lightweight-charts for financial line/trend charts | ApexCharts | If the roadmap wants built-in `sparkline: true` mode (auto-strips axes/grid/labels, less manual config than Chart.js) and is willing to pay ~164KB gzipped vs ~45-60KB — reasonable if sparklines become the dominant visual element and dev-time savings matter more than payload size. Not recommended as primary pick here because it's the heaviest of the four options and its financial-chart affordances (crosshair, price scale) are weaker than lightweight-charts'. |
| lightweight-charts for financial line/trend charts | uPlot | If raw rendering performance at very high data density (thousands of points, real-time streaming) becomes a requirement — uPlot is smaller (~48-50KB) and faster than both alternatives, but has a much lower-level API (manual axis/scale/tooltip wiring) and a much thinner styling/theming surface, making it slower to reach a "polished SaaS dashboard" look. Given this dataset is daily/EOD bars (not tick-level streaming), the performance edge doesn't outweigh the dev-time cost. |
| Chart.js for table-row sparklines | ApexCharts sparkline mode | Same tradeoff as above — pick ApexCharts only if the team decides "less sparkline boilerplate" outweighs "one fewer total dependency" (this milestone already uses lightweight-charts, so adding ApexCharts as a third library adds size/surface for a feature Chart.js already handles adequately). |
| Native CSS (nesting/custom properties/container queries) | Tailwind CSS via CDN (Play CDN / CDN build) | Never recommended for this project: Tailwind's CDN build ships an unoptimized in-browser JIT compiler intended for prototyping only (Tailwind's own docs warn against production use), and it fights against the "one self-contained `index.html`+`static/` design system" goal by pulling in a utility-class paradigm that doesn't match the existing hand-written CSS. Native CSS gets 90% of the ergonomic win with 0% of the extra runtime cost. |
| Plain `fetch()` + template literals | Alpine.js | See Supporting Libraries — only if a future milestone adds materially more client-side interactivity (filters, sorting, multi-step forms) than "fetch JSON, re-render a table/cards." |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| Any bundler (Vite, Webpack, esbuild, Rollup) or npm toolchain | Explicit project constraint: no `package.json` today, and introducing one adds a build step to a Databricks Apps deployment whose `app.yaml` only runs `python app.py` — a build step would require a CI/deploy change that's out of scope and directly contradicts the "keep it simple/defensible in an interview" standing preference. | CDN-hosted `<script>` tags, plain ES2020+ JS (already Baseline-safe in all evergreen browsers), native CSS. |
| A frontend framework (React, Vue, Svelte) — even via CDN/UMD build (e.g. React + Babel-in-browser) | Already explicitly out of scope in PROJECT.md ("Full SPA rebuild — rejected"). Babel-in-browser transforms JSX at runtime, which is a real performance and complexity cost masquerading as "no build step." | Vanilla JS with template literals, matching the existing code style. |
| Tailwind CSS Play CDN | Tailwind's own docs mark the CDN/Play build as dev/prototype-only, not for production — ships a full JIT compiler to the browser and generates classes at runtime, which is both slower and harder to defend as a deliberate architecture choice in an interview than 200 lines of native CSS with custom properties. | Native CSS nesting + custom properties + container queries (design tokens as `--variables`, one `<style>` block or a linked `app/static/css/*.css` file, no preprocessor). |
| D3.js for these chart types | D3 is a visualization *toolkit*, not a chart library — building line/sparkline charts from D3 primitives means writing scale/axis/path code by hand for every chart type, a large time investment for a "modern dashboard" polish pass whose actual charting needs (price trend, volatility line, drawdown line, small multiples) are exactly what Chart.js/lightweight-charts already solve out of the box. | Chart.js (general) + lightweight-charts (financial). |
| Highcharts | Requires a commercial license for anything beyond strictly personal/non-commercial, non-profit use — a portfolio project deployed publicly under a company-adjacent domain is a licensing risk not worth taking when Apache-2.0/MIT alternatives (lightweight-charts, Chart.js) cover the same ground. | lightweight-charts / Chart.js (both permissively licensed). |
| `unpkg.com` as the primary CDN for lightweight-charts specifically | Multiple open GitHub issues on the `tradingview/lightweight-charts` repo report broken/stale CDN links via unpkg for this package. | jsDelivr (`cdn.jsdelivr.net/npm/...`), which resolves the same npm package reliably. |

## Stack Patterns by Variant

**If the redesign adds a "ticker detail" drilldown (single ticker, larger chart, MA overlays):**
- Use `lightweight-charts`'s `addLineSeries`/`addAreaSeries` with the existing `ma_5`/`ma_20`/price data already computed by the Spark pipeline (`ticker_metrics` table) — no new backend endpoint needed, the data already exists per PROJECT.md's "charts render from existing API responses only" constraint.
- Because the pipeline already computes exactly the series (returns, MA5/MA20, volatility, drawdown) this chart would visualize — zero backend change required.

**If most sparklines only need "shape, not precision" (Watchlist trend column):**
- Use Chart.js with a `type: 'line'` chart, `scales: { x: { display: false }, y: { display: false } }`, `plugins: { legend: { display: false }, tooltip: { enabled: false } }`, small fixed-height `<canvas>` per table cell.
- Because this is the standard, widely-documented Chart.js sparkline pattern (no first-class type exists, but the config is well-trodden) and keeps every chart on the page using the same two libraries rather than adding ApexCharts just for its built-in `sparkline: true` shortcut.

**If a watchlist row has no computed metrics yet (the known `N/A` data-reality constraint from PROJECT.md):**
- Render a flat, muted-gray placeholder line (or a "—" badge) instead of an empty/broken canvas — both Chart.js and lightweight-charts render fine with a single data point or a synthetic flat series; guard in JS before chart construction rather than trying to chart `null`/`undefined` arrays.
- Because PROJECT.md explicitly calls this out as a UI-only (not pipeline) fix — the chart library choice must degrade gracefully, and both candidates support this without extra plugins.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `chart.js@4.5.0` | Any evergreen browser (Chrome/Edge/Firefox/Safari, last 2 years) | No peer dependencies when loaded via the UMD build; requires `Chart.register(...)` only if tree-shaking a modular build — not applicable here since the UMD build auto-registers everything. |
| `lightweight-charts@5.2.0` | Any evergreen browser; Apache-2.0, no dependencies | v5.x has a materially different (chainable) API from v3.x/v4.x tutorials still circulating online — verify examples against the v5 docs (`tradingview.github.io/lightweight-charts/docs`) during implementation, not older blog posts. |
| Native CSS nesting / `@property` / container queries | Safari 17.2+, Chrome 120+, Edge 120+, Firefox 117+ (nesting); broader for `@property` and container queries (2023+) | No compatibility conflicts between these three features — they compose freely in the same stylesheet. Databricks Apps' live URL has no browser-support telemetry in this repo; assume standard evergreen-browser portfolio-viewer traffic (recruiters/interviewers on current Chrome/Safari/Edge), which is safely covered. |
| jsDelivr CDN URLs | No SRI (Subresource Integrity) hash pinned in examples above | Recommend adding `integrity="sha384-..."` + `crossorigin="anonymous"` attributes when implementing, generated via jsDelivr's own SRI hash tool — cheap security hardening for a public-facing portfolio app with no CSP currently configured in `app/app.py`. |

## Sources

- WebSearch: "Chart.js vs uPlot vs ApexCharts vs lightweight-charts financial time series performance bundle size comparison" — cross-checked bundle sizes and use-case fit (MEDIUM confidence, multiple independent 2026 sources agreeing)
- WebSearch: "lightweight-charts TradingView open source library CDN unpkg version license" — confirmed Apache-2.0 license, ~45KB size, jsdelivr/unpkg availability, current major version 5.x, and the known unpkg CDN-link GitHub issues
- WebSearch: "Chart.js sparkline small multiples table row chart example minimal axes" — confirmed no first-class sparkline type in Chart.js, standard manual-config pattern, contrasted with ApexCharts' built-in `sparkline: true`
- WebSearch: "Chart.js latest version 2026 jsdelivr cdn chart.umd.js" — confirmed 4.5.0 as latest stable (June 2025) and exact jsDelivr UMD path
- WebSearch: "uPlot bundle size features vs Chart.js small tooltip financial charting" — confirmed uPlot's smaller size (~48-50KB) and OHLC/bar support, weighed against its lower-level API
- WebSearch: "native CSS nesting custom properties container queries browser support baseline 2025" — confirmed Baseline Widely Available status for nesting, `@property`, and container queries
- WebSearch: "Alpine.js vs petite-vue vs vanilla JS no bundler lightweight reactive state 2025" — confirmed both are CDN/no-build-step compatible, compared sizes (~15KB vs ~6KB) and reactivity models
- WebSearch: "CSS @scope popover API view transitions browser support 2025 baseline" — confirmed Baseline status timelines for `@scope`, Popover API, and View Transitions API as of late 2025/2026
- Codebase ground truth: `.planning/codebase/STACK.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/PROJECT.md` (all dated 2026-08-10) — confirmed no `package.json`/bundler exists today, no CSP headers in `app/app.py` (CDN scripts unrestricted), `app/static/` currently empty of tracked assets

**Confidence note:** All web-sourced claims above are MEDIUM confidence (cross-checked across 2-3 independent search results per topic, no official-docs/Context7 lookup performed for this pass). Recommend a quick spot-check against `chartjs.org` and `tradingview.github.io/lightweight-charts/docs` during the plan/execute phase to confirm exact current version numbers before pinning in code, since chart library releases move faster than this research's cache TTL.

---
*Stack research for: no-build-step vanilla-JS/CSS financial dashboard frontend elevation*
*Researched: 2026-08-10*
