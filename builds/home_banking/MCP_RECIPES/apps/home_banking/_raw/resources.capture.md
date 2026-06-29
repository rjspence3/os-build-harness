# Resources / images / fonts — CAPTURE

**Provenance:** CDP read-only against live `…/HomeBankingPortal/Dashboard`
(app `fa7ab595`), 2026-06-13. Every binary listed below was **downloaded** to
`_raw/resources/` so V6 can re-host them (see "Re-host plan").

> **Re-host plan (critical):** Every URL is an OutSystems app **Resource/Image** with a
> per-deploy UUID hash suffix (`…__<hash>.<ext>?<hash>`). These URLs are **unstable across
> deploys** (see memory note `odc_resource_url_uuid_unstable`). For pixel-exact V6 we must
> **re-upload each file as an app Image/Resource in the V6 app** and reference by the OS image
> picker (or, for fonts, @font-face pointing at the V6 Resource path). Do NOT hardcode the
> original app's hashed URLs.

## Downloaded files (`_raw/resources/`)
| File | Bytes | Role | Where used (CSS class / widget) |
|---|---|---|---|
| `CardChecking.svg` | 58,634 | Checking card art | `.account-card.checking` bg-image |
| `CardSaving.svg` | 59,073 | Saving card art | `.account-card.saving` bg-image |
| `CardCreditCard.svg` | 89,618 | Credit-card art | `.account-card.creditcard` bg-image |
| `LoanCard.svg` | 53,356 | Loan card art | `.account-card.loancard` bg-image |
| `CardTransfer.svg` | 56,683 | Transfer card art | `.account-card.transfer` bg-image |
| `Wallet.svg` | 9,739 | Wallet illustration | `<img class="wallet-img">` (76×106) |
| `Pig.svg` | 23,838 | Piggy-bank illustration | `<img class="pig-img">` (82×99) |
| `Illustratiion_umbrella.svg` | 11,585 | Umbrella illustration | `<img class="umbrella-img">` (150×117) — note original Resource name is misspelled `Illustratiion` |
| `send.svg` | 1,659 | Send icon | `<img>` 36×36 (chat send) |
| `Agent2.svg` | 2,279 | AI agent avatar | `<img>` 16×16 |
| `Curves.svg` | 65,794 | Header decorative curve | `.header::before` bg-image |
| `CurveLoginPortal.svg` | 227,465 | Login page curve | `.login-cntr::before` bg-image (login screen) |
| `Assistant.png` | 55,260 | Floating-chat OPEN toggle | `.floating-ai-chat … .toggle-ai-chat-btn` (closed state) |
| `Close.png` | 8,546 | Floating-chat CLOSE toggle | `.floating-ai-chat .ai-chat.is--open ~ .toggle-ai-chat-btn` |
| `hb-icons.ttf` | 45,104 | **Custom icon font** | `@font-face hb-icons` (HBIcon block / `.hb-*` glyphs) |
| `Sora-Regular.ttf` | 57,800 | Body font | `@font-face Sora` weight 400 |
| `Sora-SemiBold.ttf` | 57,984 | Font | `@font-face Sora` weight 600 |
| `Sora-Bold.ttf` | 57,940 | Font | `@font-face Sora` weight 700 |

## Other fonts present (NOT app-specific — leave to framework)
- **FontAwesome** (`fontawesome-webfont.woff2`) — comes with the OutSystemsUI/ReactWidgets
  bundles. Standard; no need to re-host (ships with the platform).
- **FeedbackMessage** icon font — inline **base64 data URI** in `_Basic` stylesheet (platform
  feedback-message glyphs). Ships with platform; no action.

## @font-face details
See `theme_fontfaces.capture.json` (7 rules). The 4 app fonts to re-host:
`hb-icons` (ttf), `Sora` Regular/SemiBold/Bold (ttf). In V6, declare @font-face in the theme
StyleSheet pointing at the re-uploaded Resources, OR upload the .ttf as Resources and let the
HomeBankingPortal theme CSS (captured) reference them — the captured CSS already has the
@font-face blocks; just fix the `url(../…)` paths to V6 Resource paths.

## Avatar / user photo
The dashboard user avatar is an inline **data:image/png;base64** (a placeholder portrait baked
into the page, not a Resource). For V6 use any avatar image Resource or keep a data-URI.

## GAP
- None for the listed assets — all 18 downloaded and byte-verified. Card art SVGs are the exact
  originals. If any additional screen (Transfer/Loan/Requests/Confirmation) references an image
  not present on the Dashboard, it is NOT in this capture (Dashboard-only network/CSS scan).
  See completeness audit in `V6_BUILD_SPEC.md`. **LOW-RISK GAP.**
