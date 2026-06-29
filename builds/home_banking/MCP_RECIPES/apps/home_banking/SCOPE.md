# Home Banking — Full Scope (Portal + Backoffice + Core)

Read-only enumeration via OutSystems MCP `context_*` tools. No Mentor sessions.
Captured: 2026-06-09.

## App tier overview

| App | assetKey | Rev | Screens | Blocks | Themes |
|---|---|---|---|---|---|
| Home Banking Portal | `fa7ab595-f8cd-4140-8826-2acc484727b6` | 6 | 8 | 29 | 2 (HomeBankingPortal + EmailTheme) |
| Home Banking Backoffice | `555cac1f-af92-4461-9750-b635d6570495` | 6 | 8 | 36 | 2 (HomeBankingBackoffice + EmailTheme) |
| Home Banking Core | `695efc5b-8f39-4a53-8d71-35c59097d245` | 6 | (entity/action producer — no screens of interest) | — | — |
| Home Banking Mobile | `03466756-800d-40d5-954a-394a99473f48` | 3 | (Mobile sibling — out of scope for visual parity v1) | — | — |
| Home Banking Loan Request | `4b4c5f81-d528-41dd-a5a6-3d75367f74d3` | 4 | (Workflow asset — orchestration only) | — | — |

DefaultScreen for both Portal and Backoffice: **Login** (UIFlow `Common`).

## Portal app — `Home Banking Portal`

- assetKey: `fa7ab595-f8cd-4140-8826-2acc484727b6`
- Revision: 6 (timestamp 2026-06-09T17:14:46Z)
- Template: `57b4b95a-7266-4ab2-8cec-aa1b46893be7`
- Portfolio: `f060491c-1aa9-4e19-941e-d38cd930b69a`
- Tag: 0.13.0

### Portal screens (8 total)

| # | Name | Key | UIFlow | Inputs | Roles |
|---|---|---|---|---|---|
| 1 | Login | `c9954689-1a97-47d4-a99a-ff2e3e29d9bc` | Common | — | (none) |
| 2 | InvalidPermissions | `2b4875e6-4842-4a90-bbe5-5e12808a4563` | Common | — | (none) |
| 3 | Dashboard | `a63a2e8d-8afc-4a65-8000-716a854e8467` | MainFlow | — | HomeBankingPortal |
| 4 | PersonalLoan | `1ef08c49-15b1-4204-80d6-11e39ba35628` | MainFlow | RequestId (LoanRequest Id, req), StepNo (Integer, req) | HomeBankingPortal |
| 5 | Transfer | `f7a07e56-0872-4b3a-9963-77e7a2b23eeb` | MainFlow | AccountId (HBAccount Id, req) | HomeBankingPortal |
| 6 | WakeUp | `af913392-48a1-4814-8525-fb1230198ac9` | MainFlow | — | HomeBankingPortal |
| 7 | Requests | `878e661d-8185-4ba8-86a7-7e9c61543b33` | MainFlow | — | HomeBankingPortal |
| 8 | Confirmation | `d6e3d62c-cc36-48c8-961b-38258942c462` | MainFlow | TransactionId (Transaction Id, req), RequestId (LoanRequest Id, opt) | HomeBankingPortal |

#### Currently captured (`_raw/`)
- `portal-confirmation.tree.md`
- `portal-requests.tree.md`
- `portal-transfer.tree.md` (+ `.flat.txt`)
- `portal-personalloan.tree.md` (+ `.flat.txt`) — low coverage per parent task
- `portal-dashboard.summary.md` (summary only, **no tree**)

#### Missing Portal-screen captures
- **Login** (`c9954689-1a97-47d4-a99a-ff2e3e29d9bc`) — login form, marketing image, theme switch
- **InvalidPermissions** (`2b4875e6-4842-4a90-bbe5-5e12808a4563`) — small error screen
- **Dashboard** (`a63a2e8d-…`) — **tree capture missing** (only summary exists); high-priority — this is the main canvas
- **WakeUp** (`af913392-…`) — auth bootstrap / session warmup
- **PersonalLoan** — re-capture; flagged low coverage

### Portal blocks (29 total, all owner=Portal)

#### Currently captured (`_raw/`)
- `ConfirmationPDF.block.tree.md`
- `Menu.block.tree.md`
- `HBIcon.block.tree.md` — **NOTE: no `HBIcon` block found in Portal's owned blocks list** — likely lives in HomeBankingCore (or a sub-producer). Verify before counting.

#### Missing Portal-block captures (28 unique blocks owned by Portal)

Layout / chrome blocks:
- LayoutBase (`555912bf-fb5a-4664-a8e3-085728fdece4`)
- LayoutBaseSection (`b8029dca-6597-4348-9ac6-76ac818eb151`)
- LayoutBlank (`d1f8fc2e-cccb-4a3a-8b10-6e9f5346d872`)
- LayoutTopMenu (`2cc2a24c-0ee3-4a4e-b7ef-32c7feff1982`) — base theme layout
- LayoutTopMenuLeftSide (`7d795e5c-52cf-4746-a2d7-985f321fd565`)
- LayoutTopMenuRightSide (`b0031688-1870-4f1f-a5c6-3605672cbf99`)
- LayoutTopMenuLeftSideWithBanner (`0645eb60-dfe3-41b1-bf27-3dbb46a3a5de`)
- LayoutSideMenu (`70e6cd7e-814c-4348-835c-ae61eded75a5`)
- PopupLayout (`cc89b4b6-4afd-4077-a7c7-681bab84a426`)
- ApplicationTitle (`99261221-5631-4dea-b701-80292a8a29bf`)
- HeaderActions (`70dd56f4-18a0-4e60-a148-c1c2c6f7772d`)
- UserInfo (`18f41c4b-7610-4ab6-9a0a-e51240e94601`)
- MenuIcon (`96fa937f-c17f-436d-845d-6f1a6c743802`)

Domain content blocks (Dashboard + flows):
- AccountCard (`22aad48b-ed9d-4b99-9850-8298e9e41117`)
- AccountAccordian (`f3aac43e-8b26-4141-a70c-26bb2d15111a`)
- LoanAccordian (`162af701-3f25-4715-b5c3-a399d2e32288`)
- StackedCarousel (`43c5359f-08b7-481c-8def-fbcf814f8acd`)
- ItemCard (`9abe9cd2-08ee-433d-8d55-ca4ce0069fe1`)
- DocumentItem (`73106d9d-da93-4327-9a24-03e08cadf8f3`)
- FormInfoField (`7e5f4a2a-3a3d-42a1-befc-d14f619f2f5b`)
- ValidationError (`4586b82e-5c76-4d29-88d9-29df8103006f`)
- DisplayHTML (`3d57270c-3093-4043-9d3c-c4cffd4491a9`)
- TaskBox (`f50756af-ac1b-4c3b-81cd-f3f0603e2f74`)
- NotificationsBalloon (`a54397e7-80ec-4754-8594-742b7b60a5bb`)

AI Chat blocks:
- Chat (`f1cc40d6-27b3-4293-b14f-467b03cf3aed`)
- ChatInput (`65045fea-c454-4e58-b746-a02a9b1505d9`)
- ChatMessage (`6f7f9e2f-a24e-4fcd-89ac-f2da262e45ec`)

### Portal references (6 producers)

| Producer | assetKey | Kind |
|---|---|---|
| HomeBankingCore | `695efc5b-8f39-4a53-8d71-35c59097d245` | entities |
| OutSystemsUI | `8be17f2a-431c-4958-b894-c77b988a7271` | entities |
| OutSystemsCharts | `38b70e23-50fc-4710-80cf-3682a9dc998a` | entities |
| AgentsCommonResources | `0d6e0ed8-79f8-42c2-a664-b4656db187eb` | entities |
| AppsCommonCore | `4ba075ee-bb56-43a2-adc2-a81271fa5ee2` | entities |
| (System) | `478870b9-2d60-4f73-9eb3-7cd8b994a737` | entities |

Note: refs are entity-only at this layer. Block consumption (e.g. Menu, layouts) is in-app; no InputMasks / OutSystemsMaps producers listed for Portal.

### Portal themes (2)

- **HomeBankingPortal** (`d7b27510-b69a-4c94-a613-8789fd387cc9`) — base theme `d4c81f0d-…`; layout=LayoutTopMenu; menu=Menu; grid=Fluid 12cols, gutter 20, maxWidth 1280. CSS ≈ 36 KB. **Already captured** at `theme-portal.css` (36,828 bytes).
- **EmailTheme** (`24d1715c-f265-4388-ae09-d85b11991b18`) — secondary theme for transactional email. CSS ≈ 1.5 KB. **Already captured** at `theme-email.css` (1,886 bytes).

## Backoffice app — `Home Banking Backoffice`

- assetKey: `555cac1f-af92-4461-9750-b635d6570495`
- Revision: 6 (timestamp 2026-06-09T17:18:52Z)

### Backoffice screens (8 total)

| # | Name | Key | UIFlow | Inputs | Roles |
|---|---|---|---|---|---|
| 1 | Login | `55228f79-8bb2-4c93-abc3-9403b89fdd58` | Common | — | (none) |
| 2 | InvalidPermissions | `2b4875e6-4842-4a90-bbe5-5e12808a4563` | Common | — | (none) |
| 3 | Dashboard | `5b5ab560-6ec1-49e7-aa81-1372b72a88cf` | MainFlow | — | HomeBankingBackoffice |
| 4 | Customers | `50d3d669-cb02-41ff-b93f-7e1236d1bd64` | MainFlow | — | HomeBankingBackoffice |
| 5 | CustomerDetail | `b85d3a02-9ed4-42ee-a024-33e107fcc4c3` | MainFlow | CustomerId (HBCustomer Id, req) | HomeBankingBackoffice |
| 6 | RequestDetail | `452dddbc-47cc-46cc-b373-1992e8f8ec06` | MainFlow | RequestId (LoanRequest Id, req), IsSidebarOpen (Bool, opt) | HomeBankingBackoffice (**public**) |
| 7 | ManageSettings | `2ddd0777-9300-4bbe-bb5f-e36f2271c878` | MainFlow | — | HomeBankingBackoffice |
| 8 | PersonalLoanOfferLetter | `910c1a69-b1a8-4fed-8e88-0641e8ca2ca5` | PDF | RequestId (LoanRequest Id, req) | (none) |

#### Currently captured (`_raw/`)
- `backoffice-customers.tree.md`
- `backoffice-customerdetail.tree.md`
- `backoffice-dashboard.tree.md` (+ `.flat.txt`)
- `backoffice-managesettings.tree.md`
- `backoffice-personalloanofferletter.tree.md`
- `backoffice-requestdetail.tree.md` (+ `.flat.txt`)

#### Missing Backoffice-screen captures
- **Login** (`55228f79-…`)
- **InvalidPermissions** (`2b4875e6-…`) — shares key with Portal but distinct ownerAppKey (template-cloned)

### Backoffice blocks (36 total — none yet captured)

Layout / chrome (12):
- LayoutBase (`555912bf-…`), LayoutBaseSection (`b8029dca-…`), LayoutBlank (`d1f8fc2e-…`)
- LayoutTopMenu (`2cc2a24c-…`), LayoutSideMenu (`2954bd08-5453-4868-a9d7-30452b834d9c`)
- LayoutSideMenuBanner (`d497522e-60cc-44d1-afcd-a30d30bf72bb`)
- LayoutSideMenuBannerActions (`d02248e5-abc6-4657-b08e-f2011b961e99`)
- Header (`0e1d4c7e-0aec-4b1a-8f15-ea0f1026c4cc`)
- Menu (`9f7a690d-…`), MenuLink (`d289e4a5-5d8d-42e1-b4a6-941b1962d758`), MenuIcon (`96fa937f-…`)
- ApplicationTitle (`99261221-…`), UserInfo (`b3377575-ae78-469b-bbf1-f57e02726a8c`)

Dashboard / domain (10):
- Counter (`8ff41cd9-cdbf-45d0-9f00-ea768cc37a6e`), CounterTag (`5e6519c7-…`), KPICounters (`ef0bdd7b-cff1-41d3-9571-eb87092eed79`)
- CreditCategories (`652abdf7-…`), CreditRating (`8b1b19a8-…`), CreditScore (`30782315-0aad-458e-995c-abd817c51fbd`), DebtGraph (`46935bef-…`)
- Activity (`750ecb3c-…`), AccountCard (`c0089e20-f871-438f-8ff4-a0a0a6b5683e`), PortfolioItemCard (`d5f4963c-…`)

AI Sidebar / chat (9):
- AgentSidebar (`0eb06719-…`), AgentIcon (`61f29655-…`), AgentLottie (`9b189d6a-…`)
- SidebarCard (`09ca95dd-…`), SidebarActivity (`26f32ffa-…`), SidebarTask (`29914b77-…`), SidebarChat (`012c21e4-…`)
- ChatInput (`9a5afe70-685f-412f-a3ae-a1e4edb39e70`), ChatMessage (`61ad7449-7ad5-4e7e-acc8-4f53db1823c7`)

Loan workflow / misc (5):
- ProgressStep (`725265b7-…`), LogDocuments (`ceecf296-…`), RequestNotification (`dba89293-…`), EmployeePhoto (`efac13d2-…`)

### Backoffice references (8 producers)

Same 6 as Portal, plus:
- **UltimatePDF** (`5be86d03-32b8-4d45-b8c8-b87a417f1574`) — for PersonalLoanOfferLetter
- **OutSystemsMaps** (`95bb31d1-f079-4fd6-ab2e-5c8326855aaa`) — for CustomerDetail

### Backoffice themes (2)
- **HomeBankingBackoffice** (`d7b27510-…`) — base theme `6ac3c96d-…`; layout=LayoutSideMenu; menu=Menu; grid Fluid 12/20/maxWidth 1280. CSS ≈ 31 KB. **Already captured** at `theme-backoffice.css` (31,069 bytes).
- **EmailTheme** (`24d1715c-…`) — same content as Portal's EmailTheme.

## Aggregate gap summary

| Surface | Total | Captured | Missing |
|---|---|---|---|
| Portal screens | 8 | 4 (one summary-only) | 4 (Login, InvalidPermissions, WakeUp, Dashboard tree + re-cap PersonalLoan) |
| Portal blocks | 29 | 2 confirmed (Menu, ConfirmationPDF) — HBIcon likely from Core, not Portal | 27 |
| Backoffice screens | 8 | 6 | 2 (Login, InvalidPermissions) |
| Backoffice blocks | 36 | 0 | 36 |
| Themes | 4 (2 per app, EmailTheme shared) | All 3 unique CSS files | 0 |

**Total missing screen captures:** 6 (4 Portal + 2 Backoffice)
**Total missing block captures:** 63 (27 Portal + 36 Backoffice)

## Effort estimate

Assumptions (from existing capture cadence): one Mentor `context_search` + `widget tree` round-trip per screen/block ≈ 5–10 min including retries on Mentor session-context wall (per `[[odc_mcp_session_context_wall]]`).

| Phase | Items | Per-item | Subtotal |
|---|---|---|---|
| Capture missing screens | 6 | ~7 min avg | ~45 min |
| Capture missing blocks (layouts heavy) | 63 | ~6 min avg (layouts large, simple blocks fast) | ~6 h 20 min |
| Render to HTML / dispatch to prototype shell | full set | ~2–3 h |  |
| Visual reconciliation + alert/walls retries | 1–2 h buffer |  |  |

**Estimated total to full visual parity (Portal + Backoffice): ~10–12 hours of capture + render work.**

Practical optimization: prioritize the **27 Portal-owned blocks** + the **4 missing Portal screens** first (~4 hours); they cover the entire customer-facing surface. Backoffice can be a second pass.

## Scope file

Written to `data/MCP_RECIPES/apps/home_banking/SCOPE.md`.
