# StackedCarousel — the slide/stack EFFECT (JS) — CAPTURE

**Provenance:** CDP read-only against the live authenticated tab
`https://your-tenant-dev.outsystems.app/HomeBankingPortal/Dashboard`
(original app `fa7ab595-f8cd-4140-8826-2acc484727b6`). Capture 2026-06-13. No mutation.

## TL;DR — what drives `.slider`
The stacked-carousel effect is a **custom OutSystems UserScript named `Slider`** — a single
hand-written `class Slider {…}` (15,668 bytes, NOT minified, fully captured). It is **NOT**
Splide / Swiper / Slick. Splide *is* loaded on the page (`OutSystemsUI.UserScripts.Splide`,
global `window.Splide === 'function'`) and powers two **other** `osui-carousel__track` tracks
(`#splide01`, `#splide02` — the OutSystems-UI Carousel pattern used elsewhere on the page), but
the dashboard account-card stack is the custom `Slider` class, confirmed by the runtime DOM.

Script URL (hashed, per-deploy unstable):
`/HomeBankingPortal/scripts/HomeBankingPortal.UserScripts.Slider__CFfrFjfUGCYkMaTKdNJ5LQ.js`

The full source is saved verbatim alongside this file as **`Slider.userscript.js`**.

## How the effect works (runtime-confirmed)
The block's widget tree is just `Container > Placeholder.slider.slider-content` (see
`StackedCarousel.block.tree.md`). The visual stack comes entirely from JS that, on init,
writes inline styles onto each child slide:

Runtime DOM observed on the live Dashboard (3 account cards in the carousel):
```
slide[0]: class="OSInline slide-active slide"  style="transform: scale(1);   left: 0px;       width: 275.7px; z-index: 3;"
slide[1]: class="OSInline slide"               style="transform: scale(0.9); left: 263.264px; width: 275.7px; z-index: 2;"
slide[2]: class="OSInline slide"               style="transform: scale(0.8); ...                              z-index: 1;"
```
i.e. active card full-size on top, each subsequent card scaled down 10% and shifted right,
peeking out from behind (the 0.1 "gap"/overlap). Computed scales verified: 1.0 / 0.9 / 0.8.

`.slider` placeholder gets class `slider-horizontal` added by JS (horizontal mode).
The placeholder `id` on the live page is `b10-Content`; the inner list is
`<div class="list list-group dashboard-card-list OSFillParent">` — i.e. the carousel wraps an
OutSystems **List** widget, and `Slider` detects the `.list` child (`isList = true`) and operates
on its children as the slides.

## The Slider class — public API & effective config
Constructor: `new Slider(contentId, options)` → calls `init(contentId, options)`.
- `contentId` — the DOM id of the Placeholder (`b10-Content` on the live page; in V6 use the
  generated placeholder id, or wrap and pass the widget's runtime id).
- `options` — object merged over defaults via `setOptions` (any class field can be overridden).

**Default field values (and the live-confirmed effective values):**
| field | default | live | meaning |
|---|---|---|---|
| `slidesPerPage` | `3` | 3 (all 3 cards visible) | how many slides are visible/stacked |
| `scaleDown` | `0.1` | 0.1 (→ 1.0/0.9/0.8) | per-slide scale decrement |
| `gap` | `0.1` | 0.1 | overlap: fraction of a slide hidden behind the previous one |
| `isVertical` | `false` | false (`slider-horizontal`) | horizontal vs vertical stack |
| `moveOnClick` | (truthy in options) | **true** | clicking the list advances `move(true)` |
| `eventListener` | `null` | set | callback `(eventType, activeIndex)` fired on Start/End |
| `fadeInDuration` | `380` ms | — | Web Animations API fade-in |
| `fadeOutDuration` | `350` ms | — | fade-out |
| `fadeInTransition` / `fadeOutTransition` | `ease-in` | — | easing |

**Methods:** `init`, `initSlides`, `calcVars` (lays out initial scale/left/z-index/width arrays),
`move(isNext)` (animate one step, queue-aware), `goTo(newIndex, isNext?)` (queues N moves),
`setClickListener` (wires `moveOnClick`), `setOptions`, `sendEvent`, and the four keyframe builders
`nextFadeInFrames / backFadeInFrames / nextFadeOutFrames / backFadeOutFrames`.
**Events object:** `{Start:"Start", End:"End"}`. **Classes it toggles:** `slide-active`,
`animating`, `slider-animating`, `slider-horizontal`, `slider-vertical`, plus `slide`,
`hidden-slide` on individual slides.

Notable behaviors to replicate exactly:
- `calcVars` computes `baseSize = contentSize / accumulator`, sets first slide `scale(1) left:0`,
  then each visible slide `left -= baseSize*scale*gap; … left += baseSize*scale;` and z-index
  `numberSlides - i`. Slides beyond `slidesPerPage` are `display:none; scale(0); z-index:-1`.
- When `numberSlides <= slidesPerPage`, the fade-in slide is a **clone** of the fade-out slide,
  replaced back with the original after the animation (preserves listeners). This is the
  "≤3 cards" case the dashboard hits.
- Uses the **Web Animations API** (`element.animate(frames, {duration, iterations:1, easing})`).
- Waits for the OutSystems `list-loading` class to clear before laying out (`waitList` poll @50ms).
  NOTE: `waitList`/`init` reference the function bare (not `this.waitList`) — a latent bug in the
  original; reproduce as-is for byte-fidelity, or bind correctly (cosmetic, only matters while
  data is still loading).

## Block-instance inputs → Slider options (reconciliation)
`dashboard_contents_probe.capture.md` / `portal-dashboard.tree.md` show the **StackedCarousel
block instance** on the Dashboard receives these inputs:
- `Gap = If(IsPhone(), 0.8, 0.05)`  → desktop **0.05**
- `SlidesPerPage = If(IsPhone(), 2, 3)` → desktop **3**
- `FadeIn / FadeOut / ScaleDown / IsVertical / MoveOnClick = default/null`

These block inputs are passed through into `new Slider(contentId, options)`. So the **effective
desktop config** is: `slidesPerPage:3, gap:0.05, scaleDown:0.1 (default), isVertical:false`.
(The runtime-observed scales 1.0/0.9/0.8 confirm scaleDown 0.1; the live `left` offsets reflect
gap≈0.05, slightly tighter overlap than the JS default 0.1.) Also note the per-card **PaddingTop**
input (`AccountCard.PaddingTop = 54 - Order*8` for inactive cards) adds a vertical descending
offset on top of the JS stack — replicate both.

## How it is INSTANTIATED (the OnReady wiring)
The `new Slider(...)` call is **not** in any static bundle — it is compiled into the block's
client action (a JavaScript node, almost certainly the StackedCarousel block's **OnReady** /
an OnRender handler). Searched every loaded `<script src>` for `new Slider(` / option keys:
only the UserScript itself contains the field names; the call site is in the block's runtime
module (not separately fetchable). **V6 wiring plan:** add the `Slider` JS as a UserScript (or a
`<script>` in theme), then in the StackedCarousel block's **OnReady** client action run a
JavaScript node:
```js
// $parameters: ContentId (the placeholder runtime id)
new Slider($parameters.ContentId, { moveOnClick: true, eventListener: function(type, idx){ /* optional */ } });
```
(slidesPerPage/scaleDown/gap/isVertical left at defaults = live behavior.)

## Companion CSS (already captured in theme dump)
`HomeBankingPortal.Blocks.StackedCarousel` stylesheet is only ~339 bytes (6 rules) — the
positioning is inline-JS-driven; CSS just sets the `.slider` container + base transitions.
See `theme_full.capture.css` / `theme_hb_specific.capture.css`.

## GAP
- The exact `eventListener` callback body (what the block does on Start/End) was not captured —
  it lives in the block's compiled client logic. Live behavior shows no visible side-effect beyond
  the animation, so a no-op (or a dot-indicator updater) is a safe V6 default. **MINOR GAP.**
- The literal OnReady JavaScript-node source is inferred, not byte-captured (see above).
