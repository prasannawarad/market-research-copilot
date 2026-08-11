# Feature Research

**Domain:** Financial/market-research dashboard UI (fintech SaaS — watchlist, semantic search, signal feed, notes/reports)
**Researched:** 2026-08-10
**Confidence:** MEDIUM (cross-verified web patterns from dashboard-design references, design-system docs, and fintech UX writeups; no single authoritative spec exists for this exact combination of features, so patterns are triangulated across multiple current sources rather than pulled from one canonical doc)

## Feature Landscape

This is a **frontend-elevation** milestone, not a new-feature milestone — so "features" here means *presentation patterns for existing data*, not new backend capability. Table stakes/differentiators below are scored against "does this read as a real fintech product in a portfolio review," per `PROJECT.md`'s Core Value.

### Table Stakes (Users Expect These)

Patterns a reviewer/user assumes exist. Missing them makes the dashboard look like an unstyled data dump, not a product.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Explicit missing-data treatment (not raw `N/A` text) | Real dashboards routinely have gaps; leaving `N/A` as plain text reads as "broken" rather than "expected." Dashboard-design guidance is explicit that handling missing data, extreme values, and gaps is a first-class design concern, not an edge case to patch later. | LOW | Use a muted em-dash (`—`) or a "pending" pill instead of literal `N/A`; the app already uses `&ndash;` in some spots (`pct()`/`num()` helpers) — extend that convention consistently, add a one-line explanatory microcopy ("metrics compute after first pipeline run") rather than a bare dash with no context. |
| Right-aligned, tabular-figure numeric columns | Financial dashboards (Stripe's product UI is the reference point cited repeatedly) are built on right-aligned numerals with `font-variant-numeric: tabular-nums` so columns of numbers are scannable and comparable at a glance. | LOW | The codebase already does this (`.num` class, `tabular-nums` in the strip stat font) — table stakes already partially met, extend to any new numeric columns (e.g. sparkline value labels). |
| Color-coded up/down/neutral semantics used consistently | Universal financial-UI convention: green = positive/bullish, red = negative/bearish, gray/neutral = flat. Breaking this convention anywhere (e.g. using red for a "strong" signal that isn't actually bad) creates confusion. | LOW | Already implemented (`--up`/`--down`/`--flat` CSS vars, `cls()` helper) — keep and extend to any new badge types (strength badges, sentiment tags) rather than inventing a second color language. |
| Qualitative match-quality label for semantic search results, not a raw similarity float | Guidance on semantic-search UX is explicit: don't expose the raw similarity score as the primary signal — surface a categorical read (e.g. strong/moderate/weak match) so non-technical users can interpret it without knowing what cosine similarity means. | LOW | Bucket similarity into 2–3 tiers (e.g. `similarity > 0.6` = "strong match", `0.4–0.6` = "related", `< 0.4` = "weak") and show that as a badge; keep the raw number as secondary/tooltip detail for the technical audience this portfolio piece is aimed at (reviewers who will want to see you understand the number, not just hide it). |
| Loading / empty / error states on every async panel | Every one of the 5 tabs currently fetches data with `fetch()` and shows either a static "Loading…" string or nothing — no skeleton, no distinct empty-vs-error visual treatment. A dashboard with no loading feedback reads as unfinished, especially in a live demo. | LOW–MEDIUM | Already explicitly called out as an Active requirement in `PROJECT.md`; this is genuinely table stakes for "reads as a real product," not a nice-to-have. |
| KPI/stat strip at the top of the dashboard | The 4–6-tile metric strip (Stripe, Linear, Vercel, Notion all converge on this) is the standard entry point for a data-heavy dashboard — it answers "is everything OK / how much data do we have" in one glance before the user drills into tabs. | LOW | The app already has this (`#strip` with 6 tiles: bars/metrics/articles/chunks/signals/latest). Table stakes is largely met structurally — the elevation is visual (spacing, hierarchy, maybe icons or trend deltas), not structural. |
| Consistent badge/tag vocabulary across tabs | A dashboard where "strength" badges, "trend" badges, "sentiment" badges, and "author" badges all look and behave differently reads as stitched-together, not designed. Consistency is repeatedly cited as the #1 differentiator between dashboards users trust and ones they abandon. | LOW | The codebase already has one `.tag` component reused for trend/strength/sentiment/author (`app/templates/index.html:59-63`) — the elevation work should reinforce, not fragment, this single shared component. |
| Distinguishable author badge in a merged human+agent notes/reports view | Since `research_notes.author` already stores `human` vs `agent` and Notes/Reports mix both, a shared feed without any visual author cue is a table-stakes gap, not a differentiator — users need to know at a glance who said what before they trust it. | LOW | Already has a `.tag.agent`/`.tag.human` class distinction in CSS (accent blue vs muted) — extending this (icon, avatar-style initial, or left-border color per row) is the natural elevation, not a new pattern. |

### Differentiators (Competitive Advantage)

Patterns that go beyond "functional" into "this person clearly thought about UX," appropriate for a portfolio piece that needs to stand out among other bootcamp capstones.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Inline sparkline per watchlist row (price/volatility trend) | Sparklines are the single most-cited "looks like a real trading product" pattern (Robinhood, Bloomberg, most stock-tracking apps show a compact trend line next to every symbol) — it turns a static number into a glanceable trend without needing a separate chart panel. Directly maps to the project's stated "data visualization" goal. | MEDIUM | Feasible with the existing `/api/metrics/<ticker>` endpoint (already returns a `days` window) — render via CDN Chart.js in a tiny canvas per row, or a hand-rolled inline SVG polyline if avoiding a JS dependency per row. Highest ROI differentiator: directly extends existing "Trend" column instead of replacing anything. |
| Threshold-aware, non-binary missing-data microcopy (e.g. "Metrics pending — pipeline hasn't scored this ticker yet" vs a bare dash) | Distinguishes "we know this is empty and here's why" (looks intentional) from "the value is just missing" (looks broken) — this is explicitly called out in dashboard-design guidance as separating dashboards users abandon from ones they trust. | LOW | Since most watchlist rows currently show N/A (per `PROJECT.md`'s "Data reality" constraint), this is disproportionately high-leverage: it's the single most-visible empty state in the whole app given today's data. |
| Signal-strength badge with a visual weight gradient (not just a colored label) | Fintech alert-feed convention bundles a categorical bucket (strong/material/routine, matching the existing pipeline's own bucketing) with a visual intensity cue — e.g. filled vs outlined pill, or a intensity dot — so the eye can triage a long signal feed without reading every row. | LOW–MEDIUM | The backend already computes `signal_strength` (strong/material/routine) — this is pure presentation, zero backend change, directly satisfies the "no backend contract change" constraint. |
| Similarity badge with both qualitative tier AND the underlying score as secondary detail | Serves two audiences at once: a recruiter skimming sees "strong match / 0.82"; a technical reviewer sees you understand embeddings enough to expose the real number without over-simplifying. Splits the difference between "hide the score" (pure UX advice) and "show raw score" (what the current UI does). | LOW | Directly upgrades the existing `similarity ${num(r.similarity,3)}` text into a two-part badge — low implementation cost, high "this person understands both UX and the underlying ML" signal for an interview context. |
| Visually distinct card treatment for agent-authored vs human-authored notes/reports (not just a badge) | Beyond a badge, products distinguishing AI content increasingly use a full visual treatment — an accent-colored left border, a small model icon, or muted/desaturated styling until "verified" — so the eye doesn't need to read the tag to know the source. iA Writer's convention (AI-sourced text rendered in a visually distinct tone until a human revises it) is a good reference: the *shape* of the card communicates provenance, not just a label in the metadata line. | LOW–MEDIUM | Agent Reports tab already has `model_name`/`citations` fields it doesn't visually leverage — pairing an agent-colored left border (extending the existing `.note` left-border pattern) with the model name shown prominently (not buried in the meta line) is a low-cost, high-signal differentiator. |
| KPI tiles with a secondary delta/context line, not just a raw count | The stat-strip pattern's advanced form pairs the headline number with a small secondary line (e.g. "183 metrics · 12 tickers scored" or "2 signals · both this week") — turns a static count into a bit of insight, matching the "progressive disclosure" principle cited as the differentiator between a merely-present KPI row and a genuinely useful one. | LOW | Cheap addition to the existing 6-tile strip; needs no new API since `/api/stats` payload can be reshaped client-side or the existing fields recombined (e.g. pairing chunks/articles into one ratio). |
| Ticker detail drill-down rendered as a compact chart instead of (or alongside) the existing 20-row detail table | The current `showDetail()` panel is a second raw table; pairing it with a small line/candle-ish chart (even simple line chart of close price via Chart.js) is the single highest-visual-impact addition since it's the one place users already expect to "zoom in" on a ticker. | MEDIUM | Reuses the same `/api/metrics/<ticker>?days=20` data already fetched for the detail table — no new endpoint needed. |

### Anti-Features (Commonly Requested, Often Problematic)

Patterns that look appealing in a mockup but would hurt this specific project given its constraints (no build step, no backend changes, single Flask-rendered page, small live dataset).

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Full charting-library dashboard (multi-panel candlesticks, technical-indicator overlays, drag-resizable widgets) | "Bloomberg Terminal" is the explicit visual reference point in the question, and it's tempting to chase that fidelity | Massively over-scoped for a 5-tab data-availability-limited demo (`PROJECT.md` explicitly notes most tickers lack computed metrics); real Bloomberg-terminal density is an anti-pattern for a portfolio piece meant to be *skimmed in an interview*, not operated professionally; also risks introducing a heavier charting dependency than the "CDN Chart.js, no npm toolchain" constraint comfortably supports | One lightweight sparkline/line-chart library (Chart.js via CDN, per the existing Key Decision) used sparingly in 2 places (watchlist row + ticker detail) — density and restraint read as more senior than maximal chart coverage |
| Real-time/live-updating ticker prices (polling or websockets) | Feels "more like a real trading app" and matches the fintech reference points | Explicitly out of scope — `PROJECT.md` rules out any change to Flask route behavior or new backend endpoints, and the pipeline is batch (Spark job, not streaming); faking "live" updates against static/batch data would be misleading, not impressive | A clearly-labeled "as of [pipeline run date]" timestamp (data already includes `bar_date`) communicates batch freshness honestly — the existing `Latest bar` stat tile already does this, just needs better visual prominence |
| Auto-refresh / silent background polling across all 5 tabs | Seems like table-stakes "modern dashboard" behavior | Adds complexity and failure surface (stale UI states, race conditions between tabs, more error paths to design for) with no data-freshness benefit since the underlying data only changes on a batch pipeline run or explicit user action (add/remove watchlist, save note) | Refresh-on-tab-switch (already implemented for signals/notes/reports) plus a manual "Refresh" affordance is sufficient and matches the batch nature of the data |
| A generic AI-content disclaimer banner/consent-style label repeated everywhere agent content appears | "Label AI content" guidance from general AI-UX literature (disclosure patterns, regulatory-style labeling) suggests heavy-handed banners | This is guidance built for public-facing content-moderation/misinformation contexts (is this social post AI-written?) — inappropriate weight for an internal research tool where the user *added the agent themselves* and already knows it writes reports; a banner on every card would visually dominate the smaller, denser use case here | A quiet, consistent badge/border convention (already partially present via `.tag.agent`) is sufficient — save prominent disclosure patterns for contexts where the AI origin is not already obvious from product design |
| Redesigning the stat strip into a "hero" oversized metrics dashboard (large sparkline-backed KPI cards, e.g. Stripe's revenue-graph-style cards) | Visually striking in isolation, and Stripe/Linear are the cited reference points | These 5 metrics (`bars`/`metrics`/`articles`/`chunks`/`signals`) are pipeline-run counters, not business KPIs with trend history — there's no time-series backing them (no "signals over time" data available without a new backend endpoint, which is out of scope) | Keep the stat strip compact and count-oriented (its current role: system health/data-volume glance), reserve visual weight/trend treatment for places that do have real time-series data (watchlist sparklines, ticker detail chart) |

## Feature Dependencies

```
Consistent shared badge/tag component (single .tag pattern, extended not forked)
    └──requires──> already exists in app/templates/index.html (.tag class)
                       └──enables──> Signal-strength badges, sentiment badges, author badges,
                                     similarity-tier badges all reading as "one design system"

Watchlist sparklines
    └──requires──> /api/metrics/<ticker> (already exists, no backend change)
    └──enhances──> Missing-data microcopy (sparkline itself becomes the "N/A" visual —
                    an empty/dashed sparkline placeholder communicates "not yet computed"
                    more gracefully than a bare dash)

Loading/empty/error states
    └──requires──> nothing new (pure frontend JS/CSS around existing fetch() calls)
    └──enhances──> every other feature above (a good sparkline still needs a good loading
                    state while the metrics endpoint resolves)

Agent-vs-human visual distinction (notes/reports)
    └──requires──> existing author/model_name fields (already returned by /api/notes, /api/reports)
    └──conflicts with──> generic AI-disclaimer banner anti-feature (pick one: quiet badge
                          convention OR heavy banner, not both — they compete for the same
                          visual space and signal different levels of "is this trustworthy")

KPI stat-strip secondary delta lines
    └──requires──> existing /api/stats payload only (client-side recombination, no new fields)
    └──conflicts with──> "hero" oversized KPI redesign anti-feature (the strip's job is
                          compact glance-ability; making tiles larger works against adding
                          more of them or more secondary detail)
```

### Dependency Notes

- **Sparklines require nothing new from the backend** — `/api/metrics/<ticker>?days=N` already exists and is already called by `showDetail()`. This makes sparklines the lowest-risk, highest-impact differentiator: same data, richer presentation, zero backend-contract risk (a hard constraint per `PROJECT.md`).
- **The shared `.tag` component is the single highest-leverage table-stakes item.** Every differentiator badge (similarity tier, signal strength, sentiment, author) should extend this one component rather than introduce a second visual vocabulary — fragmenting badge styles is the fastest way to make a 5-tab app look like 5 separately-built pages.
- **Missing-data treatment and sparklines reinforce each other.** Given most watchlist rows currently show `N/A` (per `PROJECT.md`'s documented data reality), a well-designed empty/pending sparkline state *is* the missing-data treatment for that column — solving both problems with one component.
- **Agent-vs-human distinction conflicts with heavy-handed AI disclaimer patterns.** Pick the quiet-badge/border convention (fits a dense internal tool) over a banner-style disclosure (fits a public consumer app) — using both would be visually redundant and inconsistent with the existing calm, monospace-driven aesthetic.

## MVP Definition

Reframed for a frontend-elevation milestone: "launch" = what must ship for the dashboard to read as portfolio-grade; "add after" = high-value polish; "future" = explicitly deferred per `PROJECT.md`'s Out of Scope.

### Launch With (v1 — this milestone)

- [ ] Graceful missing-data treatment (dash/pending microcopy, not bare `N/A`) across Watchlist and any other table with nullable fields — essential because most current data is genuinely sparse, and this is explicitly named in `PROJECT.md`'s Active requirements
- [ ] Loading/empty/error states on all 5 tabs — essential because none exist today and their absence is the single most "unfinished" thing about the current UI
- [ ] One consistent badge/tag component extended (not forked) across trend, signal-strength, sentiment, similarity-tier, and author badges — essential for the dashboard to read as one designed system rather than 5 stitched-together tabs
- [ ] Watchlist sparklines (or minimal inline trend chart) — essential to satisfy the explicit "data visualization" requirement using data the app already fetches
- [ ] Qualitative similarity-tier badge alongside the existing raw score — essential per semantic-search UX guidance (don't lead with a raw float)
- [ ] Visual (not just textual) distinction between human- and agent-authored notes/reports — essential since this is one of the app's actual differentiators as a product (human + agent collaborating on the same data) and currently has no visual payoff

### Add After Validation (v1.x — if time remains in this milestone)

- [ ] Ticker detail drill-down chart (line chart replacing/augmenting the 20-row detail table) — add once sparklines are proven out, since it reuses the same data and rendering approach
- [ ] Secondary delta/context line on KPI stat tiles — add once the base stat strip is restyled, as a polish pass
- [ ] Signal-strength badge visual-weight gradient (filled/outlined/intensity dot) beyond flat color — refinement of the base badge component

### Future Consideration (out of scope for this milestone, per PROJECT.md)

- [ ] Real-time/live price updates — requires streaming infra explicitly out of scope
- [ ] Multi-panel technical-analysis charting (candlesticks, overlays) — over-scoped for a demo dataset with capped ticker coverage
- [ ] Any new backend endpoint for chart data — explicitly ruled out ("charts render from existing API responses only")

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Graceful missing-data treatment | HIGH | LOW | P1 |
| Loading/empty/error states | HIGH | LOW | P1 |
| Shared/extended badge component | HIGH | LOW | P1 |
| Watchlist sparklines | HIGH | MEDIUM | P1 |
| Semantic-search similarity tier badge | MEDIUM | LOW | P1 |
| Human vs agent visual distinction | MEDIUM | LOW–MEDIUM | P1 |
| Ticker detail chart | MEDIUM | MEDIUM | P2 |
| KPI tile secondary delta lines | LOW–MEDIUM | LOW | P2 |
| Signal-strength visual-weight gradient | LOW | LOW | P2 |
| Real-time price updates | LOW (misleading given batch data) | HIGH | P3 (rejected) |
| Multi-panel technical charting | LOW (over-scoped for dataset) | HIGH | P3 (rejected) |

**Priority key:**
- P1: Must have for this milestone — either explicitly required by `PROJECT.md` or directly closes the biggest visual gap ("plain bordered tables" → "modern dashboard")
- P2: Should have, add once P1 is solid and time remains
- P3: Explicitly out of scope for this milestone per `PROJECT.md`'s constraints

## Competitor Feature Analysis

Reference products informing the visual bar (per `PROJECT.md`'s explicit Linear/Vercel/Stripe reference and the question's Robinhood/Bloomberg framing):

| Feature | Stripe / Linear / Vercel (SaaS dashboard reference) | Robinhood / Bloomberg (fintech reference) | Our Approach |
|---------|-------------------------------------------------------|--------------------------------------------|--------------|
| Numeric presentation | Right-aligned, tabular-nums, muted gridlines, calm palette | Same, plus heavy use of green/red for direction | Already matches this convention (`.num`, tabular-nums, `--up`/`--down`) — keep, extend to new columns |
| KPI header | 4–6 tile strip, compact, progressive disclosure (headline number first, detail on demand) | Less common (fintech apps favor a single portfolio-value hero number) | Keep the existing 6-tile strip's SaaS-dashboard framing (data-volume/health glance) rather than reframing as a fintech "portfolio value" hero — the data (bar/metric/article counts) is a pipeline-health metric, not a financial KPI, so the SaaS pattern fits better than the fintech one |
| Trend visualization | Rare inline sparklines; more often a separate detail chart | Sparkline-per-row in every watchlist is near-universal | Adopt the fintech convention here specifically — the question and `PROJECT.md` both call out this exact gap (raw-number-only tables) |
| Color/visual restraint | Near-monochrome, hierarchy from spacing/type weight, not color | Heavier use of brand color + red/green | Stay closer to the SaaS-calm end: current CSS is already a restrained monochrome/mono-font aesthetic (`--ink`/`--soft`/`--muted`) — reinforce that identity rather than importing fintech's more saturated palette, since restraint is more defensible as an intentional, explainable design choice in an interview |
| AI/agent content | No direct analog (not an agent-facing product category) | No direct analog | Draw from general AI-UX disclosure patterns (badge/border, not banner) scaled down to fit the existing calm aesthetic |

## Sources

- [Dashboard Design UX Patterns Best Practices — Pencil & Paper](https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards) — missing-data/real-world-conditions guidance (WEB, cross-referenced)
- [Dashboard design principles: 8 rules that actually work — Setproduct](https://www.setproduct.com/blog/effective-dashboard-design-principles) — consistency, KPI-strip guidance (WEB, cross-referenced)
- [Dashboard UI design: From KPIs to layouts that convert — Setproduct](https://www.setproduct.com/blog/dashboard-ui-design) — Stripe/Linear/Vercel KPI-strip pattern, progressive disclosure (WEB, cross-referenced)
- [Dashboard Design Patterns for Modern Web Apps 2026 — artofstyleframe](https://artofstyleframe.com/blog/dashboard-design-patterns-web-apps/) — Stripe/Linear/Vercel specific design-language notes (WEB, cross-referenced)
- [AI UX Patterns | Disclosure — ShapeofAI.com](https://www.shapeof.ai/patterns/disclosure) — AI-content labeling/badge patterns (WEB, cross-referenced)
- [AI label — Carbon Design System](https://carbondesignsystem.com/components/ai-label/usage/) — production design-system precedent for AI-content labeling (WEB, cross-referenced — HIGH-credibility single source, established design system)
- [How to Label AI-Generated Content — cookie-script](https://cookie-script.com/guides/how-to-label-ai-generated-content) — dual-layer/badge disclosure pattern (WEB, cross-referenced)
- [Display Semantic Search Match Quality in a Read-Only Grid — Appian docs](https://docs.appian.com/suite/help/26.3/recipe-display-smart-search-quality-in-grid.html) — qualitative match-quality badge pattern, don't expose raw score (WEB, cross-referenced, vendor doc)
- [What metrics should I track for semantic search relevance? — Milvus](https://milvus.io/ai-quick-reference/what-metrics-should-i-track-for-semantic-search-relevance) — similarity score interpretation guidance (WEB, cross-referenced)
- [Watchlists and cards — Robinhood support](https://robinhood.com/us/en/support/articles/watchlist-and-cards/) — watchlist/sparkline convention (WEB, primary product docs)
- [Bloomberg Watchlist — Bloomberg Markets](https://www.bloomberg.com/markets/watchlist) — fintech watchlist reference (WEB, primary product)
- [Fintech UI Design: Patterns That Build User Trust & Credibility — phenomenonstudio](https://phenomenonstudio.com/article/fintech-ux-design-patterns-that-build-trust-and-credibility/) — sentiment/signal color-coding conventions (WEB, cross-referenced)
- `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`, `app/templates/index.html` — primary source, existing app ground truth (CURATED/local, HIGH confidence)

**Confidence note:** All web-sourced UI-pattern claims are tagged WEB/cross-referenced (MEDIUM confidence per this project's classify-confidence tiering — WebSearch alone is LOW, cross-verified across ≥2 independent sources raises to MEDIUM). No single source is treated as authoritative; every pattern above was corroborated across at least two independent search results before being stated as a recommendation. Claims about the existing codebase (what's already implemented) are HIGH confidence, sourced directly from reading `app/templates/index.html`.

---
*Feature research for: financial/market-research dashboard UI elevation*
*Researched: 2026-08-10*
