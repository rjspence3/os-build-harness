# Recipe 30 — Build the remaining portal screens (Pass D)

**Pass D of the V6 clone.** After the Dashboard (Pass C), build the other 7
portal screens to pixel parity. Each is simpler than the Dashboard. Same method
throughout: build ON the active theme's layout, author INTO placeholders
(Recipe 28); reference Core entities via `eSpace.References.Named("HomeBankingCore")`;
LOCAL blocks already live in the `Layouts` flow; referenced OS UI/Charts blocks via
`addReferenceToElements`. PLAIN Mentor phrasing, raw `"""..."""` literals, NEVER
cancel a mutation turn, publish + `snapshot_app.py` + CDP pixel-gate per screen.

## Precondition — clone the remaining entity-coupled tail blocks (LOCAL → `Layouts`)
Needed by Pass D screens (deferred in Pass B). Element-import the coupled entities
via `eSpace.AddDependency((sig as IModelObject).GlobalKey)` first:
- **ConfirmationPDF** (`_raw/ConfirmationPDF.block.tree.md`) — input `RequestId : LoanRequest Identifier`; block events `OnReady`/`ReturnBinary`; own stylesheet. Used by Confirmation / offer-letter.
- **TaskBox** (`_raw/TaskBox.block.tree.md`) — used by Requests.
- **DocumentItem** (`_raw/DocumentItem.block.tree.md`) — used by PersonalLoan upload + Requests.
- (AccountAccordian / LoanAccordian cloned in Pass C.)

## Screens (each: capture → build on layout → publish → pixel-gate)
| Screen | Capture | Notable deps / auth |
|---|---|---|
| **Login** | `portal-login.tree.md` | ANONYMOUS — `screen.AnonymousAccess=true`, clear Roles (V27). Username/password inputs (W-C bound vars), login button (W-D). No top-nav layout (LayoutBlank/PopupLayout per capture). |
| **Transfer** | `portal-transfer.tree.md` (+`.flat.txt`) | Input `AccountId`. Account picker, amount input (W-C), recipient, FormInfoField, confirm button → Confirmation. |
| **Requests** | `portal-requests.tree.md` | TaskBox list, DocumentItem list, request aggregates over Core. |
| **PersonalLoan** | `portal-personalloan.tree.md` (+`.flat.txt`) | Wizard/WizardItem (OS UI), DocumentItem upload, FormInfoField, ValidationError, amount/term inputs (W-C). |
| **Confirmation** | `portal-confirmation.tree.md` | ConfirmationPDF block, CheckMark (OS UI), summary fields. |
| **Wakeup** | `portal-wakeup.tree.md` | Splash/redirect screen — likely OnReady client logic + minimal UI. |
| **InvalidPermissions** | `portal-invalidpermissions.tree.md` | ANONYMOUS (V27). Minimal message screen. |

## Per-screen walls (pre-applied)
- Anonymous screens (Login, InvalidPermissions, Wakeup if public): `AnonymousAccess=true`
  + clear Roles, else Mentor auto-applies the role filter (memory: mentor_auto_applies_role_filter).
- Wizard / WizardItem / CheckMark / Sidebar are OS UI patterns (referenced, used inline) — NOT local blocks.
- Data-bound lists clone first-try: `CreateScreenAggregate(false,"GetX")` over Core entities only — do NOT author new custom-PK entities (publish crash).
- W-A..W-D on every button/link/input. `IsDesktop()` rejected in Web Style (V24) → static desktop classes.

## Pixel gate per screen
`cdp_login_screenshot.py` (same seeded user/data, width 1280, dark-mode) →
`pixel_diff.py compare/original_<screen>.png <v6_screen>.png --tol 16 --threshold 99.5`.
First capture each original screen at the target viewport if not already in `compare/`.
Heatmap bbox drives iteration; verbatim MCP error on a real attempt = candidate WALL.

## Backoffice (Pass E — only if in scope)
`backoffice-*.tree.md` (dashboard/customers/customerdetail/requestdetail/managesettings/
personalloanofferletter) are a separate module/role. Treat as Pass E after the 8 portal
screens reach pixel-parity; same method.
