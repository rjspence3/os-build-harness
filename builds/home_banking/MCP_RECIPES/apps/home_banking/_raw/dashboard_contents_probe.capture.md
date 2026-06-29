# Dashboard CONTENTS deep-probe — original Home Banking Portal (fa7ab595, rev 6)

**Purpose**: Portal5's account cards are thin (name + number + balance) and the dashboard is "not that close."
This capture pins the THREE rich zones — account-card carousel, balance band + chart, right sidebar — with
exact widget structure + bindings, and gives a per-element DELTA of what Portal5 must add.

**Sources** (all READ-ONLY against fa7ab595; never mutated/published):
- `AccountCard.block.tree.md` (re-captured 2026-06-13, complete) — the card contents.
- `portal-dashboard.tree.md` (hierarchical screen tree, complete) — carousel/chart/sidebar placement + bindings.
- Mentor getWebBlock + synthesis answers, 2026-06-13.

---

## ZONE 1 — Account-card carousel (MainContent → Carouselcntr)

**Container 'Carouselcntr'** Style="margin-top-l **card-carousel-container**"
  → If `not Accounts.Empty and GetAccounts.IsDataFetched`
    → **WebBlockInstance → `StackedCarousel`** (CUSTOM local block, NOT the OS UI Carousel pattern)
        Gap = If(IsPhone(),0.8,0.05)
        SlidesPerPage = If(IsPhone(),2,3)
        (FadeIn/FadeOut/ScaleDown/IsVertical/MoveOnClick = default/null)
      → **List** Source="**Accounts**" Style="list list-group **dashboard-card-list**"
        → Container 'ListItemClickable' Width="fill"
          → **WebBlockInstance → `AccountCard`** with per-row bindings:
              Balance            = Accounts.Current.AccountBalance
              AccountNumber4Digit= Substr(Accounts.Current.AccountNumber, Length(...)-4, 4)
              AccountName        = Accounts.Current.Name
              IsActive           = Accounts.Current.Id = SelectedAccountId
              AccountTypeId      = Accounts.Current.TypeId
              PaddingTop         = If(Accounts.Current.Id=SelectedAccountId, 54, 54 - (Accounts.Current.Order*8))

**Carousel verdict**:
- It is the **custom `StackedCarousel` web block**, NOT an OutSystemsUI Carousel pattern.
- `StackedCarousel` itself is trivially clonable in static markup: its only widget tree is
  `Container > Placeholder 'Content' Style="slider slider-content"` (see StackedCarousel.block.tree.md).
  The stacked/peeking 3-D effect is delivered by **JS bound to `.slider` + the per-card dynamic
  `padding-top` (PaddingTop input → `54 - Order*8`)**, plus CSS on `card-carousel-container` /
  `dashboard-card-list` / `slider-content`. To match: replicate the per-card padding-top offset and
  the `account-card` color classes; the "stack" look is mostly CSS + the descending padding-top.
- Cards shown: SlidesPerPage 3 (desktop) / 2 (phone); source is the full `Accounts` list.

---

## ZONE 2 — Balance band + chart

### 2a. Balance band (Title placeholder, top of page)
- "Total Balance" Text label.
- If `Client.HideBalance`: 4 dot Icons (Icon="circle", font-size: 8px, Style="icon") in a `balance-cntr`.
- Else: `balance-cntr` → AlignCenter →
    Expression `Client.Currency` Style="font-size-h5 margin-top-xs"  +
    Expression `FormatCurrency(TotalBalance,"",2,Client.DecimalSeparator,Client.GroupSeparator)`
               Style="**font-size-h1** white-space-nowrap"  (hero total-balance number)
- Action buttons beside it: **Show/Hide Balance** toggle (ToggleHideBallanceOnClick, eyeshow/eyehide HBIcon),
  **Account Insights** (NotImplemented, insights icon), **Consolidated Position** (btn-primary, opens sidebar, columnchart icon).
- Quick-actions row below carousel: **Transfer** (→Transfer screen, transfer icon), **Pay** (NotImplemented, scan icon),
  **Add** (NotImplemented, plussquare icon).

### 2b. Chart (left of the Last-Transactions/Balance columns block)
- "Balance" label + **Dropdown 'PeroidFilterDdl'** Variable=SelectedChartDataOptionId, List=ChartOptionList
  (Weekly / Monthly / Quarterly), OnChange=PeroidFilterDdlOnChange.
- Container 'ChartCntr' → Container CustomStyle="height: 256px;" →
  If `HideChart or not GetChartSampleData.IsDataFetched` → FalseBranch:
    **WebBlockInstance → `ColumnChart`** (OutSystemsCharts) — THIS IS the OutSystemsCharts wall surface.
      Height = If(ChartHeight>200,ChartHeight,200)+"px"
      DataPointList = GetChartSampleData.ChartDataPoints
      ValuesType = If(SelectedChartDataOptionId=Monthly, Datetime, Text)
      AddOns: **ChartXAxis** (gridlines #B9BBC7, label rotation -75 on phone),
              **ChartYAxis** (gridlines dark/light aware), **ChartSeriesStyling**.
- Below chart: **Gallery** (3 desktop / 3 tablet / 2 phone) of 3 **ItemCard** blocks:
    Balance card (primary, banknote icon, ChartCardsValue.Balance + BalancePercent% + Label range),
    Income card (green, deposit icon, ChartCardsValue.Income + IncomePercent%),
    Expenses card (red, withdrawal icon, ChartCardsValue.Expenses + ExpensesPercent%).

**Chart verdict**: It is **`ColumnChart` from OutSystemsCharts** with X/Y axis + series-styling add-on blocks.
This is the OutSystemsCharts capability — adding it to Portal5 means depending on OutSystemsCharts and wiring
DataPointList + the 3 add-on blocks. (PieChart is also used in the sidebar — see Zone 3.)

### 2c. Last Transactions list (right column of the same block)
- "Last Transactions" header + "View All" link.
- Empty/loading/list states; each row: HBIcon (TransactionType.IconNameEN) + localized type label +
  truncated description (English locale) + signed colored amount (text-<TransactionType.Color>) + date (d MMM).
- Source = GetLastTransactions.List.

### 2d. Chat
- **WebBlockInstance → `Chat`** (UserName, ChatMessages, IsWaitingForResponse) — AI assistant panel at MainContent bottom.

---

## ZONE 3 — Right SideContent

### 3a. "For you" promo cards (static content, `colored-card`)
- **Personal Loan** — `colored-card lightDark`, Wallet image (`wallet-img`), "Personal Loan" / "Customized solutions for your financial journey".
- **Define New Goal** — `colored-card`, Pig image (`pig-img`), "Define New Goal" / "Put some money aside for something incredible".
- **Retirement Plan** — `colored-card`, Umbrella/Illustration image (`umbrella-img`), "Retirement Plan" / "Apply automatically and set aside money every month."

### 3b. Your Goals (data-driven carousel) — visible when GetCustomerGoals.Count>0
- Header "Your Goals (N)".
- **WebBlockInstance → `Carousel`** (OutSystemsUI Carousel pattern — Dots navigation when >1, AutoPlay False, Loop False)
  → List Source=GetCustomerGoals.List
    → `colored-card orange` per goal: AlignCenter (GoalName + "Add" btn) + amount-of-target line +
      **ProgressBar** (white on translucent white, Progress = AmountSum/TargetAmount*100, Thickness 8).

### 3c. Loans (data-driven carousel) — visible when GetCustomerLoans.Count>0
- Header "Loans (N)".
- **WebBlockInstance → `Carousel`** (OS UI, Dots when >1)
  → List Source=GetCustomerLoans.List
    → `colored-card yellow slide-mini` per loan: localized label + "View" btn (RedirectToLoan) +
      amount-of line + **ProgressBar** (Progress = AmountSum/Amount*100, Thickness 8).

### 3d. Consolidated Position sidebar (BlockInstance 'ConsolidatedPositionSidebare' → `Sidebar`)
- Header "Consolidated Position" + close link.
- "My Assets" + Tag "+23%" + month-range expression; **ProgressBar** (green) Progress=TotalAssets/TotalDept-ish.
- "My Debt" + **ProgressBar** (red).
- **ButtonGroup** (My Assets / My Debt) bound to IsDeptConsolidatedPositionOption.
- Assets view: **PieChart** (GetAssets.List mapTo {Value,Label,Color,Tooltip}) + total-in-chart overlay +
  **Accordion** of **AccountAccordian** blocks per asset.
- Debt view: **PieChart** (DeptList) + total-in-chart + **Accordion** of **LoanAccordian** / **AccountAccordian** per debt.

**Sidebar verdict**: rich — two PieCharts (OutSystemsCharts), ProgressBars, ButtonGroup, Accordion + custom
AccountAccordian/LoanAccordian blocks. High-effort zone; the promo cards (3a) are pure static markup and cheap.

---

# DELTA — "Portal5 has X, the original has Y" (concrete add-list)

Portal5 today: thin account cards (name + number + balance), no carousel, no chart, no right sidebar.

| Element | Portal5 has | Original has | To add |
|---|---|---|---|
| **Account card body** | name + 4-digit + balance, flat | 3 stacked lines: name(+suffix); currency-symbol(h4)+**big balance number font-size-40 card-detail-font**; masked `**** **** ****`+last-4 (Checking/CC) OR "Savings Account" caption | Add the `card-detail-font`/`font-size-40` hero number, the masked card-number row (AlignCenter+Text+last-4), and the Saving caption branch |
| **Card color variants** | (likely one style) | `checking`/`saving`/`creditcard`/`transfer` + `inactive` classes on `account-card`, selected via AccountTypeId | Add per-type class expression on the card wrapper + the matching CSS color variants |
| **Card hide-balance** | (likely none) | 4 dot icons (circle, font-size:4px) when `Client.HideBalance` | Add HideBalance If with dot icons |
| **Card stacking offset** | flat list | dynamic `padding-top = 54 - Order*8` (peeking stack) | Pass PaddingTop per card; add the padding-top inline style |
| **Carousel** | none | custom `StackedCarousel` block (Container>Placeholder `slider slider-content`) + `card-carousel-container`/`dashboard-card-list` CSS + JS on `.slider`; 3 slides desktop/2 phone | Clone StackedCarousel markup + the 3 CSS classes; the stack look is CSS + padding-top, effect JS optional |
| **Balance band hero** | (check) | "Total Balance" + currency(h5) + **FormatCurrency(TotalBalance) font-size-h1** + Show/Hide toggle + Insights + Consolidated buttons | Add the h1 total + currency + the 3 CTAs |
| **Chart** | none | `ColumnChart` (OutSystemsCharts) + ChartXAxis/ChartYAxis/ChartSeriesStyling add-ons, period Dropdown (Weekly/Monthly/Quarterly), 256px container | Add OutSystemsCharts dependency + ColumnChart wired to ChartDataPoints + 3 add-ons + the dropdown |
| **Chart KPI cards** | none | Gallery of 3 `ItemCard` (Balance/Income/Expenses, colored, +%/range) | Add the 3 ItemCards in a Gallery |
| **Last Transactions** | (check) | list with HBIcon + localized type + signed colored amount + date | Add the transactions list if absent |
| **Right sidebar promos** | none | 3 static `colored-card`s (Personal Loan / Define New Goal / Retirement) with images | Add 3 colored promo cards (cheap, static) |
| **Your Goals / Loans** | none | OS UI `Carousel` + ProgressBars per goal/loan | Add when data exists (data-gated, lower priority) |
| **Consolidated Position** | none | `Sidebar` w/ 2 PieCharts + ButtonGroup + Accordion | High-effort; defer unless parity demands |

<!--
READ-ONLY probe of fa7ab595 (rev 6). Never mutated/published.
Carousel/chart/sidebar structure taken from the complete portal-dashboard.tree.md (already on disk).
AccountCard contents from the 2026-06-13 complete re-capture (AccountCard.block.tree.md).
-->
