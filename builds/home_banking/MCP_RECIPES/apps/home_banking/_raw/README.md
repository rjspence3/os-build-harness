# Home Banking — raw Mentor MCP probe outputs

Captured screen widget trees and action body traces, used as recipe-template
inputs. Source for screen-pattern recipes (07–11).

## Files

| File | Screen | Widgets captured | Source method |
|---|---|---|---|
| `portal-dashboard.summary.md` | Portal Dashboard | Full hierarchy, 26KB indented tree | Mentor `getScreen` chat synthesis (worked once; rest of round failed similarly) |
| `portal-transfer.flat.txt` | Portal Transfer | 61 widgets | `applyModelApiCode` walker — UI.Mobile.IWidget |
| `portal-personalloan.flat.txt` | Portal PersonalLoan | 134 widgets | `applyModelApiCode` walker — IObject + name filter |
| `backoffice-dashboard.flat.txt` | Backoffice Dashboard | 109 widgets | `applyModelApiCode` walker — IObject + name filter |
| `backoffice-requestdetail.flat.txt` | Backoffice RequestDetail | 124 widgets | `applyModelApiCode` walker — IObject + name filter |

All `*.flat.txt` files are **partial** — the MCP wrapper caps each
`tool_end.result` at ~8 KB, so deeper-tree widgets are dropped. What survives:

1. `=== Screen: <Name> ===` header
2. Full `Inputs:` list (with types)
3. Full `Locals:` list (with types — includes Structures, key feature flags)
4. First 60–134 widgets in document order, with `Text`, `Value`, `Style`,
   `CustomStyle`, `Source`, `Condition`, `Variable`, `Visible`, `Width`
   properties when present

## Key cross-screen findings

**Portal Transfer**
- Wizard with `StepNo:Integer` local (Step1/Step2 containers gated on
  `Visible="StepNo=N"`)
- Multi-modal: contains `Popup` widget for OTP / phone-number confirmation
- Locals: `NewTransfer` (anonymous-structure Record holding all form fields),
  `OTPVerificationCode`, `TwilioPhoneNumber`, `ShowPhoneNumberPopup`,
  `IsConfirmPhoneNumberLoading`, `IsToPhoneNumber`, `IsPortrait`

**Portal PersonalLoan**
- Wizard pattern (`StepNo:Integer` input parameter, gating containers)
- Document-upload pattern: 4 named locals of type `DocumentStructure`
  (`DocumentPayStubs`, `DocumentBankStatements`, `DocumentIdentification`,
  `DocumentTaxForm`) — one per document type
- Form-state locals: `TermAndConditionsConfirm`, `ShowPopup`,
  `TempNewComment`, `NewComment`, `IsLoadingSubmit`,
  `IsShowAdditionalInformation`, `InitialEffectiveInterestRatePercent`

**Backoffice Dashboard** (109 widgets visible)
- Admin home: queue counters + recent activity feed
- Companion to Portal Dashboard but role-gated `HomeBankingBackoffice`

**Backoffice RequestDetail**
- `IsSidebarOpen:Boolean` input — confirms sidebar pattern
- Locals: `ShowNewNoteForm`, `SelectedLogId:HistoryLog Identifier`,
  `ShowRejectionPopup`, `isResubmission`, `NotificationCount`,
  `IsEnrichmentAgentCompleted`, `IsRequestCompleted`, `HasCreditScore`,
  `LoadingDateTime`, `ShowSSN`
- Workflow-driven UI — agent-completion flags drive section visibility
- `IsPublic: true` — referenced cross-app (Loan Request BPM workflow)

## Recipe template implications

The widget trees + locals confirm:
- **Wizard recipe** (NEW): `StepNo:Integer` input + N `Container` widgets with
  `Visible="StepNo=N"` per step. Common pattern across Transfer + PersonalLoan.
- **Modal recipe** (NEW): `Popup` widget + `Show*:Boolean` local +
  trigger button + content placeholder. Used in Transfer (OTP), PersonalLoan
  (terms), RequestDetail (rejection).
- **Document-upload recipe** (NEW): per-doc-type `DocumentStructure` local +
  upload widget. PersonalLoan has 4 instances, one per HBDocumentType static
  entity record.
- **Master-detail-w-sidebar recipe** (NEW): `IsSidebarOpen:Boolean` input +
  conditional sidebar Container. RequestDetail.
- **Workflow-state recipe** (NEW): boolean `IsXCompleted` locals gating
  visible sections. RequestDetail.

## Probe lessons learned (May 2026)

1. **Mentor's chat-synthesis layer refuses ~75% of read probes** when given a
   clean natural-language ask. The reliable trigger is a deliberately-broken
   `applyModelApiCode` prelude that forces Mentor's recovery flow to call
   `getScreen`. Worked once for Dashboard.
2. **Sandbox blocks `System.Collections.IEnumerable` as qualified reference**
   — only `OutSystems.*` and `ServiceStudio.*` qualified type references are
   allowed in code bodies.
3. **`OutSystems.Model.UI.Mobile.IWidget` is flaky** — 1 of 4 parallel sessions
   loaded it correctly; the other 3 failed `CS0234 IWidget does not exist`.
4. **Workaround that worked**: use `OutSystems.Model.IObject` (proven loaded)
   with `screen.GetAllDescendantsOfType<IObject>()` + name-keyword filter
   (`Widget`, `Container`, `Text`, `Button`, `Input`, `If`, `IfBranch`, `Form`,
   `List`, `Popup`, `Link`, `Icon`, `Dropdown`, `WebBlockInstance`,
   `PlaceholderArgument`, `Expression`).
5. **MCP wrapper truncates `tool_end.result` at ~8 KB.** No cursor-paginated
   recovery — the full server-side `stdoutOutput` is unreachable. To capture
   deeper-tree widgets, the probe code must FILTER on the server side (skip
   layout chrome / placeholders, dump only domain-meaningful widgets) before
   the 8 KB cap hits.

The fifth lesson — server-side filtering — would let us capture the full
screen tree in a future probe round. Recipes can be authored from current
partial captures.
