# Phase 1: Static Asset Restructure & Design System Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 1-Static Asset Restructure & Design System Foundation
**Areas discussed:** Roadmap gap check, Handler/module wiring strategy, Theme & color direction, Typography & font strategy, Layout restructuring boundary

---

## Roadmap Gap Check (pre-discussion)

Before discussing Phase 1 implementation details, a gap was flagged: PROJECT.md's "visual design system" Active requirement had no explicit phase mapping — Phase 1's original success criteria required "visually identical to baseline," and Phases 2-4 only covered specific features (states, sparklines, badges), leaving the general typography/color/spacing/card-layout overhaul with no home.

| Option | Description | Selected |
|--------|-------------|----------|
| Fold into Phase 1 | Apply design tokens to the page shell as part of the restructure itself, one pass | ✓ |
| Dedicated phase between 1 and 2 | Insert a new phase purely for applying the design system | |
| Spread across Phases 2-4 | Keep Phase 1 pixel-identical, restyle incrementally per feature phase | |

**User's choice:** Fold into Phase 1.
**Notes:** REQUIREMENTS.md and ROADMAP.md were amended immediately — added STYLE-01, expanded Phase 1's goal and success criteria, relaxed "visually identical to baseline" to "restyled with the modern SaaS-dashboard design system, functionally identical." Committed as `22df319`.

---

## Handler/module wiring strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Classic scripts, keep globals | Non-module scripts attaching to shared namespace, onclick handlers untouched | ✓ |
| ES modules + rewire to addEventListener | type="module", replace every inline onclick | |

**User's choice:** Classic scripts, keep globals.

| Option | Description | Selected |
|--------|-------------|----------|
| Full manual walkthrough checklist | Every button/tab/action verified live before Phase 1 is done | ✓ |
| Spot-check only | Main happy paths only | |

**User's choice:** Full manual walkthrough checklist against the live deployed app.

---

## Theme & color direction

| Option | Description | Selected |
|--------|-------------|----------|
| Light-only, dark-ready tokens | Ship light now, CSS custom-property tokens ready for future dark mode | ✓ |
| Light-only, no dark-mode planning | Hardcode light-theme colors | |

**User's choice:** Light-only, dark-ready tokens.

| Option | Description | Selected |
|--------|-------------|----------|
| Cool blue/indigo | Trustworthy/analytical fintech-dashboard accent | ✓ |
| Neutral/monochrome + data-only color | Grayscale chrome, color reserved for data | |
| Green-forward | Growth framing, risks clashing with up/down convention | |

**User's choice:** Cool blue/indigo.

---

## Typography & font strategy

| Option | Description | Selected |
|--------|-------------|----------|
| System font stack | Zero network dependency | ✓ |
| CDN webfont | More distinctive, adds external dependency | |

**User's choice:** System font stack.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep monospace for data | Deliberate fintech convention for prices/metrics | ✓ |
| Sans-serif throughout | Unify on one typeface family | |

**User's choice:** Keep monospace for data, sans-serif for everything else.

---

## Layout restructuring boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, additive changes are fine | New wrapper divs/classes OK; never remove/rename existing IDs the JS depends on | ✓ |
| No new markup, CSS-only restyle | Restyle existing DOM shape only | |

**User's choice:** Yes, additive changes are fine.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include page chrome | Restyle KPI stat-tile strip and tab nav in Phase 1 too | ✓ |
| Tab content only, defer chrome | Leave stat-tile strip/nav for later | |

**User's choice:** Yes, include page chrome.

---

## Claude's Discretion

- Exact design-token numeric values (hex codes for the blue/indigo accent, spacing scale, type-scale ratios, border-radius/shadow values for cards)
- Exact file split within `app/static/js/components/*.js` and `app/static/css/*.css` beyond the already-recommended structure
- Cache-busting convention mechanics (manual `?v=` string placement)

## Deferred Ideas

None — discussion stayed within phase scope. VIZ-02 (ticker-detail drill-down chart) remains deferred to v2, as decided during requirements definition on 2026-08-10.
