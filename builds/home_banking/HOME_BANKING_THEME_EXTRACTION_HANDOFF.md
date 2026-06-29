# Home Banking Theme Extraction — Session Handoff

**Date:** 2026-05-18
**Tenant:** your-tenant-dev
**Studio binary:** Studio 1 (`/Applications/ODC Studio.app`) — regular apps + libraries, not agentic
**Status:** Discovery complete. Migration plan prompt drafted but not yet sent. Execution not started.

---

## How to resume this work

1. Load `data/MENTOR_INDEX.md` (auto via project memory rule)
2. Read this entire file
3. Open ODC Studio 1 to **`HomeBankingPortal`** app (the Studio session that was last active)
4. Verify with `Cmd+3` (Logic tab) — should show banking entities: `Account`, `Transaction`, etc.
5. Open Mentor pane (`Cmd+Shift+A`)
6. Paste the prompt in § Next prompt to run
7. Continue from there

---

## TL;DR

- Goal: extract a reusable theme library from the OutSystems **Home Banking** reference suite using Mentor, motivated by `~/Downloads/Use Theme Library for app branding - ODC Documentation.pdf`.
- Discovery surprise: an existing partial shared library (`Agents Common Resources`) already provides the base theme + i18n stack. We're filling the gap, not greenfield-building.
- The gap: layouts (8 needed), common scaffolding blocks (~6), generic UI blocks (~6), and an entire Chatbot suite (4 blocks). All live in `HomeBankingPortal` and need extraction.
- Single biggest architectural finding: `HBIcon` is a choke-point (5 elements depend on it). Solution = author a new parameterized `Icon` block in the new library; do **not** modify `Agents Common Resources` in place.
- Plan: two libraries — `Theme_Foundation` (depends on `Agents Common Resources`) + `Theme_Chatbot` (depends on `Theme_Foundation`).
- Next step: one more Mentor turn produces the formal migration plan. After that, ~70% of the execution is Portal + Studio gesture work, not Mentor.

---

## Motivation

User asked whether the new ODC could use Mentor to execute the workflow described in this PDF:

> `~/Downloads/Use Theme Library for app branding - ODC Documentation.pdf`

That PDF is a gesture-heavy playbook (Library create + cross-module copy/paste + Placeholder swaps + multi-select Public flags). Several steps sit in known Mentor failure modes (Phantom Authoring on fine-grained style edits, no verified verb for cross-module copy).

User pivoted: instead of building greenfield from spec, **extract** an existing theme from the Home Banking suite. This handoff covers that extraction discovery.

---

## What's in the tenant

Home Banking reference suite — four apps:

| App | Type | Role |
|---|---|---|
| Home Banking Core | Library | Entities + Service Actions, no UI |
| Home Banking Portal | Web App | **Consumer web UI — extraction target** |
| Home Banking Mobile | Mobile App | Consumer mobile UI (out of scope) |
| Home Banking Backoffice | Web App | Admin UI (out of scope) |

Plus a shared library:

| Module | Type | Why it matters |
|---|---|---|
| Agents Common Resources | Library | Holds the actual base theme `AgentsCommon_Theme` + i18n stack + agent icon suite. Confirmed via `Cmd+D` Manage Dependencies search. |

---

## Inventory findings — `Agents Common Resources`

11 theme-shape elements + 18 agentic-only + 1 banking-shape leak. **Zero layouts. Zero site properties.**

### Theme-shape (reusable across consumers)
- **Themes**: `AgentsCommon_Theme` (extends nothing; carries icon font + locale dropdown styling + common appearance rules; custom CSS present)
- **Blocks** (in `Widgets` UI Flow): `Locales`, `MarkdownFormat`
- **Images**: `setting`
- **Structures**: `LocaleStruct`
- **Server Actions**: `GetLabelByLocale`, `GetLocaleRecord`, `PublicLocaleStruct`
- **Client Actions**: `FormatDateLocale`, `FormatTimeLocale`, `GetLabelByLocale`

### Agentic-only (quarantined in `LottieWidgets` UI Flow)
- **Blocks**: `Agent`, `AgentIddle`, `CheckMark`, `CheckMark_Dark`, `CommunicatorAgent`, `EnrichmentAgent`, `IntakeAgent`, `UnderwriterAgent`
- **Images**: `Agent`, `Attachment`, `checkmark`, `checkmark_dark`, `checkmark_lighter`, `CheckSquare`, `CommunicatorAgent`, `EnrichmentAgent`, `IntakeAgent`, `UnderwriterAgent`

### Banking-shape leak
- **Block**: `HBIcon` — Public-exposed block that "renders Home Banking icon font classes." Domain code in a Common library. Don't propagate.

---

## Inventory findings — `HomeBankingPortal` UI Flows

7 UI Flows, 34 named UI elements. Mentor's wave-classified extraction shortlist:

### Wave 1 — zero leaks (extract verbatim)
1. `FormInfoField` (Blocks) — label/value form row
2. `NotificationsBalloon` (Blocks) — popover container
3. `StackedCarousel` (Blocks) — sliding card carousel
4. `ValidationError` (Blocks) — validation warning card
5. `MenuIcon` (Common) — hamburger toggle
6. `RedirectToURL` (Common) — URL redirect helper
7. `LayoutBaseSection` (Layouts) — section wrapper
8. `LayoutBlank` (Layouts) — minimal page shell

### Wave 2 — small cleanup
- `ItemCard` (Blocks) — leak: `FormatCurrencyCustom` client action → replace with formatter input
- `PopupLayout` (Blocks) — leaks: uses `HBIcon`, hardcoded "AI Assistant" title → use new `Icon`, parameterize title
- `ChatInput` (Chatbot) — leak: local `send` image → move image into library
- `ChatMessage` (Chatbot) — leak: local `Agent` image → move + rename to generic `assistant-avatar`
- `DisplayHTML` (Chatbot) — leak: hardcoded "Hello, I'm your AI Assistant..." copy → remove

### Wave 3 — structural decoupling
Layout shells (6) all reference `Menu` + `MenuIcon` + `ApplicationTitle`. Once `Menu` and `ApplicationTitle` are refactored in the new library, the layouts extract clean.

- `LayoutBase`, `LayoutSideMenu`, `LayoutTopMenu`, `LayoutTopMenuLeftSide`, `LayoutTopMenuLeftSideWithBanner`, `LayoutTopMenuRightSide`
- `ApplicationTitle` (Common) — uses `HBIcon` + banking-branded icon name `homebankinglogo` → parameterize icon class
- `UserInfo` (Common) — references `Get_Settings` SA, `WakeUp` screen, `HeaderActions`, `HBIcon` → convert refs to input callbacks/placeholders
- `HeaderActions` (Common) — uses `TaskBox` (banking) + `HBIcon` → placeholder for actions, drop TaskBox
- `InvalidPermissions` (Common) — uses `LayoutTopMenu` + `UserInfo` + `HBIcon` → layout selectable, uses new `Icon`

### Banking-specific (stay in Portal)
Blocks folder: `AccountAccordian`, `AccountCard`, `DocumentItem`, `LoanAccordian`, `TaskBox`
Common folder: `Login`, `Menu`
MainFlow (all screens): `Confirmation`, `Dashboard`, `PersonalLoan`, `Requests`, `Transfer`, `WakeUp`
PDF folder: `ConfirmationPDF`

### Local theme
`HomeBankingPortal` has a local theme named `HomeBankingPortal` that extends `AgentsCommon_Theme`. Custom Style Sheet content present (size not measurable from Mentor's available snapshot).

### Images
25 images in Portal. Theme-shape vs banking-shape classification not yet run — defer until extraction.

---

## The `HBIcon` choke-point insight

`HBIcon` appears as a leak in **5 elements**: `PopupLayout`, `InvalidPermissions`, `ApplicationTitle`, `UserInfo`, `HeaderActions`. Fixing it unlocks half of Wave 3.

**Fix strategy: additive, not subtractive.** Do NOT modify `Agents Common Resources` in place (memory `feedback_modify_agents_on_clones.md` — shared library elements have many consumers; in-place edits break the tenant at once). Instead, author a new parameterized `Icon` block in the new theme library that accepts an icon font class as input. Banking apps keep using `HBIcon`; new theme consumers use `Icon`.

Same pattern for `Menu`: don't try to refactor the banking-specific Menu block. Author a new placeholder-driven `Menu` in the new library.

---

## Target architecture

Two libraries. Dependency direction: `Theme_Chatbot` → `Theme_Foundation` → `Agents Common Resources`.

### `Theme_Foundation`

```
Depends on: Agents Common Resources

Themes/
└── Theme_Foundation                  (extends AgentsCommon_Theme + Portal CSS minus brand rules)

UI Flows/
├── Common/
│   ├── Icon                          (NEW — parameterized icon class input)
│   ├── Menu                          (NEW — placeholder-driven, no banking entities)
│   ├── MenuIcon                      (Wave 1: verbatim copy)
│   ├── RedirectToURL                 (Wave 1: verbatim copy)
│   ├── ApplicationTitle              (Wave 3 → 2: icon class as input param)
│   ├── UserInfo                      (Wave 3: Get_Settings + WakeUp as callback inputs)
│   ├── HeaderActions                 (Wave 3: action slots as placeholder, drop TaskBox)
│   └── InvalidPermissions            (Wave 3: layout selectable, uses new Icon)
├── Layouts/
│   ├── LayoutBaseSection             (Wave 1: verbatim)
│   ├── LayoutBlank                   (Wave 1: verbatim)
│   ├── LayoutBase                    (Wave 3: wires new Menu/ApplicationTitle)
│   ├── LayoutSideMenu                (Wave 3: wires new Menu/ApplicationTitle)
│   ├── LayoutTopMenu                 (Wave 3: wires new Menu/ApplicationTitle)
│   ├── LayoutTopMenuLeftSide         (Wave 3: wires new Menu/ApplicationTitle)
│   ├── LayoutTopMenuLeftSideWithBanner (Wave 3: wires new Menu/ApplicationTitle)
│   └── LayoutTopMenuRightSide        (Wave 3: wires new Menu/ApplicationTitle/HeaderActions)
└── Widgets/
    ├── FormInfoField                 (Wave 1: verbatim)
    ├── NotificationsBalloon          (Wave 1: verbatim)
    ├── StackedCarousel               (Wave 1: verbatim)
    ├── ValidationError               (Wave 1: verbatim)
    ├── ItemCard                      (Wave 2: formatter as input action)
    └── PopupLayout                   (Wave 2: title input param, uses new Icon)

Images/
└── (subset of Portal's 25 — classification deferred to execution phase)
```

### `Theme_Chatbot`

```
Depends on: Theme_Foundation

UI Flows/
└── Chatbot/
    ├── Chat                          (verbatim)
    ├── ChatInput                     (Wave 2: send-image moved into this library)
    ├── ChatMessage                   (Wave 2: assistant-image as input)
    └── DisplayHTML                   (Wave 2: remove hardcoded "AI Assistant" copy)

Images/
├── send                              (moved from Portal)
└── assistant-avatar                  (renamed from Agent, kept generic)
```

### Architectural rationale
- Two libraries, not one: chat suite is independently reusable. Apps that don't need chat shouldn't pull layout/menu/header machinery.
- Chatbot depends on Foundation (one direction): the only acyclic, additive-only arrangement.
- Whole-copy local CSS: copy Portal's local theme stylesheet into `Theme_Foundation` wholesale. Selective rule-by-rule extraction is premature.

---

## Next prompt to run

Studio context: **`HomeBankingPortal`** in Studio 1 (verify with `Cmd+3` — banking entities visible).

```
Produce the migration plan. Use this target structure:

Library 1: Theme_Foundation
- depends on: Agents Common Resources
- folders: Themes, Common (with new parameterized Icon and Menu blocks),
  Layouts, Widgets, Images
- includes the 6 no-leak Wave 1 blocks + the 2 no-leak Layouts +
  refactored versions of Wave 2 and Wave 3 elements (ItemCard,
  PopupLayout, ApplicationTitle, UserInfo, HeaderActions,
  InvalidPermissions, all 6 Layout shells)
- adds NEW: Icon (parameterized icon class), Menu (placeholder-driven)

Library 2: Theme_Chatbot
- depends on: Theme_Foundation
- contains: Chat, ChatInput, ChatMessage, DisplayHTML
- moves: send image, assistant-avatar image (renamed from Agent)

For each element in the plan, report:
(a) source app (HomeBankingPortal or NEW),
(b) extraction method: "copy verbatim", "copy + refactor (specify
    refactor)", or "author new",
(c) Public flag setting in the destination library,
(d) any input parameter additions or removals required vs source,
(e) any image dependencies that must be moved alongside.

Group by wave (1 / 2 / 3) and by destination library.

Use the same "Verified / Not verified" structured output format.
Do not propose elements not in the prior shortlist.
```

---

## Execution sequencing (after migration plan)

| Step | Tool | Notes |
|---|---|---|
| 1. Create `Theme_Foundation` Library | **Portal** (`Create > Library`) | Mentor Web can't generate Library apps (corpus MENTOR_STUDIO_DOCTRINE.md § 17-21) |
| 2. Wire `Agents Common Resources` dependency | **Studio gesture** (`Cmd+D`) | Cross-module dep wiring, no Mentor verb for this |
| 3. Copy Wave 1 elements verbatim from Portal | **Studio gesture** | Cross-module copy is not a verified Mentor verb |
| 4. Author new `Icon` block in `Theme_Foundation` | **Mentor (Studio)** | Authoring new blocks from a spec is wheelhouse |
| 5. Author new `Menu` block in `Theme_Foundation` | **Mentor (Studio)** | Same |
| 6. Refactor Wave 2 elements (`ItemCard`, `PopupLayout`) | **Mentor (Studio)** one element per turn | Phantom Authoring guard verbatim on each turn |
| 7. Refactor Wave 3 elements (`ApplicationTitle`, etc.) | **Mentor (Studio)** one element per turn | Same |
| 8. Copy 6 Layout shells with new Menu/AppTitle wired | **Studio gesture** + **Mentor** | Copy is gesture; rewire is Mentor |
| 9. Move theme-shape images from Portal | **Studio gesture** | Cross-module copy |
| 10. Mark Public = Yes on all extracted elements | **Mentor (Studio)** one at a time, or gesture multi-select | Both work |
| 11. `F5` Publish `Theme_Foundation` | **Studio gesture** | TrueChange must be green first |
| 12. Repeat steps 1-11 for `Theme_Chatbot` | Mixed | Serial, depends on Foundation being published |
| 13. Update Portal to consume `Theme_Foundation` | **Studio gesture** (`Cmd+D`) + **Mentor** rewire | Per-screen rewire is Mentor-shaped |

**~70% of execution is gesture work, not Mentor.** Mentor's role is authoring the new `Icon` + `Menu` blocks and per-element Wave 2/3 refactors.

---

## Mentor methodology that worked this session

Capture for re-use:

### Prompt class: structured inventory (Mentor's "introspection wins" class)

Pattern:
```
List every <category> in this <app|library>. For each:
report (a) <attr1>, (b) <attr2>, (c) <classification>.

Verify in the <Cmd+X (tab)> tree that every element you list
is visibly present. Do not report success unless each named
element appears in the tree. Use the same "Verified / Not
verified" structured output format from the previous turn.
```

### Verbatim Phantom Authoring guard

```
Verify in <surface> that <X> is visibly present. Do not report
success unless <X> appears in <surface>.
```

### "Verified / Not verified" reproducible Mentor output shape

Mentor produced this 4 turns running once first elicited. Keep asking for it on every introspection turn. It structurally separates "I saw this" from "I would have expected this but didn't see it" — defeats Phantom Authoring at the output level.

### 3-way classification scheme used

For each element: `theme-library shape` | `agentic-only` | `banking-shape`. Wave classification (1 / 2 / 3) by leak count was the synthesis output.

### Cross-reference detection prompt (closes leak-surface audit)

Pattern:
```
For each shortlist element, report cross-references — anything
inside the element's implementation that prevents clean extraction:
(a) banking entities in expressions/aggregates/action calls;
(b) banking-domain Server/Client Actions;
(c) banking-shape blocks in the widget tree;
(d) hardcoded banking copy in labels/text widgets;
(e) banking-shape image references.

Report (e) as "no leaks", (f) "1 leak: <description>", or
(g) "multiple leaks: <list>".
```

---

## Turn-by-turn log (verbatim Mentor outputs preserved)

For audit / replay purposes — the actual exchange that produced this handoff.

### Turn 1 — `HomeBankingPortal` Themes inventory

Mentor returned:
- `EmailTheme` (Base: None, Public: No, custom CSS: Yes)
- `HomeBankingPortal` (Base: `AgentsCommon_Theme`, Public: No, custom CSS: Yes)

Critical discovery: no `OutSystemsUI` direct base. `AgentsCommon_Theme` is a cross-module dependency.

### Turn 1.5 — Side-quest: `AgentsCommon_Theme` source

Resolved via `Cmd+D` Manage Dependencies (gesture, not Mentor). Source = `Agents Common Resources` (Library type, multi-color swirl icon).

### Turn 2 — `Agents Common Resources` full Public surface

11 theme-shape, 18 agentic-only, 1 banking-shape leak (`HBIcon`). Zero layouts. Zero site properties.

### Turn 3 — Wrong-app turn (Mentor read Agents Common Resources again)

App-context not switched. Mentor faithfully returned `Agents Common Resources` UI Flows: `LottieWidgets` (8 agentic blocks) + `Widgets` (3 utility blocks). Lesson: pre-flight check that Studio is on the right app before every introspection turn.

### Turn 4 — `HomeBankingPortal` UI Flows inventory (correct app)

7 UI Flows, 34 named UI elements. Wave-classifiable set established.

### Turn 5 — Cross-reference detection (leak surface)

23 candidate elements analyzed. Wave 1 (8), Wave 2 (5), Wave 3 (10) emerged. `HBIcon` choke-point identified.

### Turn 6 — NOT YET RUN — migration plan synthesis

This is the next prompt (see § Next prompt to run).

---

## Open decisions for future session

1. **Image partition**: which of Portal's 25 images are theme-shape vs banking-shape? Defer until execution phase — running Mentor on this is cheap. Sketch a brand-vs-generic classification turn before step 9.
2. **CSS partition strategy**: confirm whole-copy is right, or selective-extract if banking-branded rules cause visual bleeding. Decide after the first test render with the new library against a non-banking consumer.
3. **Library naming**: `Theme_Foundation` is a placeholder. Confirm with user — possible alternatives: `Reactive_Foundation`, `OutSystems_Foundation`, `Branded_Foundation`. Same for `Theme_Chatbot`.
4. **Consumer for testing**: which app gets re-themed first to validate the extraction? Likely a kyleAccounts cohort prototype. Confirm with user.
5. **`HBIcon` deprecation path**: long-term, banking apps should also migrate to the new `Icon` block. Out of scope for this extraction, but worth flagging in `Agents Common Resources`.

---

## References

- PDF source: `~/Downloads/Use Theme Library for app branding - ODC Documentation.pdf`
- Doctrine loaded this session: `data/MENTOR_INDEX.md`, `data/MENTOR_STUDIO_DOCTRINE.md`
- Memory entries referenced: `mentor_phantom_authoring.md`, `mentor_studio_ui_gesture_verbs.md`, `feedback_modify_agents_on_clones.md`, `odc_deps_search_indexes_elements_only.md`
- Corpus walls relevant: Phantom Authoring (line 322), Verb-Reflex Drift (line 322), Plan-Without-Execute (auto-confirm cascade)
- Tenant: `your-tenant-dev`
