# CDP Head-to-Head Compare — Portal4 vs Original (planned 2026-06-12)

The real acceptance gate for the framework: side-by-side rendered-DOM comparison of the MCP-built clone against the original, screen by screen.

## Subjects

| | URL | Auth state |
|---|---|---|
| **Original** | https://your-tenant-dev.outsystems.app/HomeBankingPortal/ | Has login flow + seeded users (Andrea demo user) |
| **Clone** | https://your-tenant-dev.outsystems.app/HomeBankingPortal4 | Login anonymous; business screens role-gated but role has no users — may need role-clear pass for compare |

## Tooling

Use Rob's authenticated Chrome on port 9222 (chrome-cdp skill) OR the Playwright MCP plugin (browser_navigate + browser_take_screenshot). Reference helper: `scripts/cdp_proto_inspect.py` (diagnostics pattern; cleanup uses `p.stop()`, never Browser.close).

## Screen-by-screen matrix

| Screen | Original route | Clone route | Compare focus |
|---|---|---|---|
| Login | /Login | /Login | layout, branding, form structure |
| Dashboard | / (post-login) | /Dashboard | THE main view — nav bar, balance band, account cards, transactions list, chart, promo sidebar |
| Transfer | /Transfer | /Transfer | account cards, form fields, masks, buttons |
| Requests | /Requests | /Requests | request list, tags, accordions |
| Confirmation | /Confirmation | /Confirmation | success layout, PDF block |

## Known expected gaps (don't re-litigate tomorrow — they're documented)

1. **No data**: clone has no aggregates wired + no seed data → lists/cards render empty or with placeholder "X" binds (F1/F2/F4 in GAPS.md). Compare STRUCTURE not content.
2. **FirebaseReceiver** missing (library not in tenant) — V3.
3. **InputWithIcon** markers left empty (renderer skip-list) — V1.
4. **Theme fidelity**: full 35KB portal.css dispatched, but local `url()` font/image refs were sanitized to `url('')` — fonts fall back, images blank (documented theme-sanitize behavior).
5. **Navigation not wired** (Recipe 24 renderer not built) — clicking nav items won't route.
6. **PersonalLoan screen** not authored (low-coverage capture).

## Pre-compare checklist (run before screenshots)

- [ ] app_info → confirm final rev (expect 8 after tonight's finisher)
- [ ] If business screens are role-gated with no users: dispatch a role-clear turn on Dashboard/Transfer/Requests/Confirmation so anonymous compare works (same pattern as the rev-8 Portal3 fix)
- [ ] context_screens → verify DefaultScreen + anonymous flags
- [ ] Original: log in as the demo user first (or screenshot the login wall too — it's a compare subject)

## Output format

For each screen: `compare/<screen>_original.png` + `compare/<screen>_clone.png` + a diff-notes row:

| Screen | Structural match | Styling match | Gaps observed | Verdict |

Append results to GAPS.md as the V-next entries. Each observed gap → framework feature (per the "failures become framework gaps" doctrine), prioritized into the P1/P2 ladder.

## What success looks like

NOT pixel-perfect (data + fonts are known-absent). Success = an OutSystems-literate person looking at the pair says "same app, clone just has no data yet." Specifically: layout skeleton, top nav, card shapes, section structure, color palette in the right places.
