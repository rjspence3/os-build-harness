# Dashboard Spec Baseline — the original, captured live (CDP)

**Source**: `https://your-tenant-dev.outsystems.app/HomeBankingPortal/Dashboard`, authenticated (Andrea), 2026-06-12.
**Why**: full visual parity is the bar (Rob, 2026-06-12: "Full unless it's impossible — and that would be a big [finding]"). The CDP gate (beat 7) must assert against THESE numbers, not just "no leaks". Screenshot: `compare/original_dashboard_spec.png`.

## Runtime metrics (the gate targets)
| metric | original (spec) | clone @ rev 39 | assert? |
|---|---|---|---|
| `leaked_icons` | 0 | 1 (`banknote`) | `=0` |
| `text_stubs` | 0 | 2 | `=0` |
| `button_logout_raw` | 0 | 0 ✓ | `=0` |
| `dark_mode` | 1 | 0 | `=1` (structural) |
| `main_width` | ~1077 | ~200 | `>=1000` (structural) |
| `nav_menu` | 9 | 0 | `>=9` (structural) |
| `hb_icons` | 24 | 8 | informational (partly data-driven — account-card icons need rows) |

## Dark-mode mechanism (the biggest visual gap)
- Activated by **`class="dark-mode"` on `<html>`** (OutSystemsUI dark mode), NOT a `data-theme` attribute. Also `iconLibrary-fontawesome`.
- `body` background `rgb(4, 13, 63)` (navy). Original carries ~591KB total CSS, 908 dark-related rules; the clone theme is 41KB.
- JS-activated (the original's `InitClientVars` / Layout OnReady sets it). The clone never sets `dark-mode` → renders light. Fix = activate the class (JS) AND ensure the dark color tokens / theme rules exist in the clone theme.

## Structural gaps vs the skeleton clone (full-parity work, 0-data excepted)
1. **Dark theme** — activate `dark-mode` + sync dark color tokens. Biggest lever.
2. **Full-width layout** — the captured layout-utility CSS (`layout_utility_css.capture.md`) + the `dark-mode` theme.
3. **Account-card grid, bar chart, right sidebar** (Personal Loan / Define Goal / Retirement / Your Goals) — present in the original; the clone renders none. Some values are 0-data (OK), but the card grid / chart / sidebar STRUCTURE + styling are not data.
4. **Top nav bar** (logo · Home/Products/Locations · Welcome/avatar) — clone has no nav (`nav_menu=0`).

Anything in this list that proves un-buildable via MCP is a precisely-defined WALL = a headline finding for the mandate.
