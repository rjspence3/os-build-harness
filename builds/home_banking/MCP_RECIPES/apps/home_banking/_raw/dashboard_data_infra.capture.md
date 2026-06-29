# Dashboard Data Infrastructure — Raw Capture

**App**: Home Banking Portal
**App key**: fa7ab595-f8cd-4140-8826-2acc484727b6
**Date**: 2026-06-11
**Mentor session id**: c637de68-e867-461f-b11b-102a96f03672
**Runs**: a788cf3a-255d-4ae8-9796-56f94b50578a (Turn 1, recipe — CS0234), 57a65836-ab68-42a5-ba5b-6da1fca96206 (Turn 1 fallback, aggregates), 42436a69-a182-4ea3-bd35-757edf4e3e5c (Turn 2, structure/function/static/expressions)
**Mode**: READ-ONLY capture. No mutations, no publish.

---

## Turn 1 — Recipe outcome (verbatim compilation errors)

The aggregate-introspection recipe drew CS0234 on all five interfaces:

```
(10,73): error CS0234: The type or namespace name 'IAggregate' does not exist in the namespace 'OutSystems.Model' (are you missing an assembly reference?)
(12,74): error CS0234: The type or namespace name 'IAggregateSource' does not exist in the namespace 'OutSystems.Model' (are you missing an assembly reference?)
(18,72): error CS0234: The type or namespace name 'IAggregateFilter' does not exist in the namespace 'OutSystems.Model' (are you missing an assembly reference?)
(22,74): error CS0234: The type or namespace name 'IAggregateAttribute' does not exist in the namespace 'OutSystems.Model' (are you missing an assembly reference?)
(28,73): error CS0234: The type or namespace name 'IAggregateSort' does not exist in the namespace 'OutSystems.Model' (are you missing an assembly reference?)
```

Mentor's diagnosis (terminal summary): the aggregate interfaces live in `OutSystems.Model.Logic.Aggregates`, not the `OutSystems.Model` root namespace. The Dashboard screen WAS located successfully in MainFlow before compilation stopped.

---

## Turn 1 fallback — Aggregate definitions (Mentor narrative, verbatim)

Source note: Mentor's getScreen tool dump confirmed the GetAccounts authoring code verbatim (CreateScreenAggregate / CreateSource / CreateJoin / CreateFilter / CreateCalculatedAttribute / CreateGroupByAttribute / CreateAggregatedAttribute / CreateSort / SetMaxRecords) before synthesizing this narrative. Key raw authoring facts from the tool dump: `getAccounts.SetMaxRecords("6")`, calculated attribute via `CreateCalculatedAttribute("AmountWithSign").SetValue(...)`, aggregated attribute via `CreateAggregatedAttribute("AccountBalance"); .SetAttribute("AmountWithSign"); .AggregationType = AggregationType.Sum`, sort via `CreateSort().SetAttribute("ProductType.Order")`.

Here is the complete list of all aggregates on the `Dashboard` screen:

---

### 1. GetAccounts

**Sources & Joins**

| Left | Right | Kind | Condition |
|---|---|---|---|
| *(base)* | HBAccount | — | — |
| HBAccount | ProductType | Inner | `HBAccount.ProductTypeId = ProductType.Id` |
| HBAccount | HBCustomer | Inner | `HBAccount.CustomerId = HBCustomer.Id` |
| HBAccount | Transaction | Left | `HBAccount.Id = Transaction.AcountId` |
| Transaction | TransactionType | Left | `Transaction.TypeId = TransactionType.Id` |
| HBAccount | HBAccountName | Left | `HBAccount.AccountNameId = HBAccountName.Id` |

**Filters**
- `HBCustomer.UserId = GetUserId()`
- `HBAccount.ProductTypeId = Entities.ProductType.Checking or HBAccount.ProductTypeId = Entities.ProductType.Saving or HBAccount.ProductTypeId = Entities.ProductType.CreditCard`
- `HBAccount.IsActive = True`

**Calculated Columns**
- `AmountWithSign` (calculated): `If(HBAccount.ProductTypeId=Entities.ProductType.CreditCard, If(TransactionType.IsIncrease,-Transaction.Amount,Transaction.Amount), If(TransactionType.IsIncrease,Transaction.Amount,-Transaction.Amount))`

**Group-By Columns**
- `AccountNumber` → `HBAccount.AccountNumber`
- `Id` → `HBAccount.Id`
- `LabelLocale` → `HBAccountName.LabelLocale`
- `ProductTypeId` → `HBAccount.ProductTypeId`

**Aggregated Columns**
- `AccountBalance` = Sum of `AmountWithSign`

**Sorts**
- `ProductType.Order`

**Max Records:** 6

---

### 2. GetAssets

**Sources & Joins**

| Left | Right | Kind | Condition |
|---|---|---|---|
| *(base)* | HBAccount | — | — |
| HBAccount | ProductType | Inner | `HBAccount.ProductTypeId = ProductType.Id` |
| HBAccount | HBCustomer | Inner | `HBAccount.CustomerId = HBCustomer.Id` |
| HBAccount | Transaction | Left | `HBAccount.Id = Transaction.AcountId` |
| Transaction | TransactionType | Left | `Transaction.TypeId = TransactionType.Id` |

**Filters**
- `HBCustomer.UserId = GetUserId()`
- `HBAccount.ProductTypeId = Entities.ProductType.Checking or HBAccount.ProductTypeId = Entities.ProductType.Saving or HBAccount.ProductTypeId = Entities.ProductType.Investment`

**Calculated Columns**
- `AmountWithSign` (calculated): `If(TransactionType.IsIncrease, Transaction.Amount, -Transaction.Amount)`

**Group-By Columns**
- `Color` → `ProductType.Color`
- `Label` → `ProductType.Label`
- `LabelLocale` → `ProductType.LabelLocale`
- `Order` → `ProductType.Order`
- `ProductTypeId` → `HBAccount.ProductTypeId`

**Aggregated Columns**
- `AccountBalance` = Sum of `AmountWithSign`

**Sorts (in group-by)**
- `Order`

**Max Records:** 6

---

### 3. GetChartDataOptions

**Sources**
- `ChartDataOption` (static entity)

**Filters**
- `ChartDataOption.Is_Active = True`

**Sorts**
- `ChartDataOption.Order`

**Max Records:** 50 (default)

---

### 4. GetCreditCardsDept

**Sources & Joins**

| Left | Right | Kind | Condition |
|---|---|---|---|
| *(base)* | HBAccount | — | — |
| HBAccount | HBCustomer | Inner | `HBAccount.CustomerId = HBCustomer.Id` |
| HBAccount | ProductType | Inner | `HBAccount.ProductTypeId = ProductType.Id` |
| HBAccount | Transaction | Left | `HBAccount.Id = Transaction.AcountId` |
| Transaction | TransactionType | Left | `Transaction.TypeId = TransactionType.Id` |

**Filters**
- `HBAccount.ProductTypeId = Entities.ProductType.CreditCard`

**Calculated Columns**
- `AmountWithSign` (calculated): `If(HBAccount.ProductTypeId=Entities.ProductType.CreditCard, If(TransactionType.IsIncrease,-Transaction.Amount,Transaction.Amount), If(TransactionType.IsIncrease,Transaction.Amount,-Transaction.Amount))`

**Group-By Columns**
- `Color` → `ProductType.Color`
- `Label` → `ProductType.Label`

**Aggregated Columns**
- `AccountBalance` = Sum of `AmountWithSign`

**Sorts:** none

**Max Records:** 6

---

### 5. GetCustomerGoals

**Sources & Joins**

| Left | Right | Kind | Condition |
|---|---|---|---|
| *(base)* | CustomerGoal | — | — |
| CustomerGoal | Transaction | Left | `CustomerGoal.Id = Transaction.CustomerGoalId` |
| CustomerGoal | HBCustomer | Left | `CustomerGoal.CustomerId = HBCustomer.Id` |

**Filters**
- `HBCustomer.UserId = GetUserId()`
- `CustomerGoal.IsActive = True`

**Having (group-by filter)**
- `AmountSum < TargetAmount`

**Calculated Columns**
- `Amount` (calculated): `If(Transaction.Id <> NullIdentifier(), Transaction.Amount, 0)`

**Group-By Columns**
- `GoalName` → `CustomerGoal.GoalName`
- `Id` → `CustomerGoal.Id`
- `TargetAmount` → `CustomerGoal.TargetAmount`

**Aggregated Columns**
- `AmountSum` = Sum of `Amount`

**Sorts**
- `CustomerGoal.TargetDate`

**Max Records:** 50 (default)

---

### 6. GetCustomerLoans

**Sources & Joins**

| Left | Right | Kind | Condition |
|---|---|---|---|
| *(base)* | CustomerLoan | — | — |
| CustomerLoan | Transaction | Left | `CustomerLoan.Id = Transaction.CustomerLoanId` |
| CustomerLoan | HBCustomer | Left | `CustomerLoan.CustomerId = HBCustomer.Id` |
| CustomerLoan | LoanRequestType | Left | `CustomerLoan.RequestTypeId = LoanRequestType.Id` |

**Filters**
- `HBCustomer.UserId = GetUserId()`
- `CustomerLoan.IsActive = True`

**Having (group-by filter)**
- `AmountSum < Amount`

**Calculated Columns**
- `Amount` (calculated): `If(Transaction.Id <> NullIdentifier(), Transaction.Amount, 0)`

**Group-By Columns**
- `Amount` → `CustomerLoan.Amount`
- `Id` → `CustomerLoan.Id`
- `LabelLocale` → `LoanRequestType.LabelLocale`
- `LoanName` → `LoanRequestType.Label`

**Aggregated Columns**
- `AmountSum` = Sum of `Amount`

**Sorts**
- `CustomerLoan.CreatedOn`

**Max Records:** 50 (default)

---

### 7. GetLastTransactions

**Sources & Joins**

| Left | Right | Kind | Condition |
|---|---|---|---|
| *(base)* | Transaction | — | — |
| Transaction | TransactionType | Inner | `Transaction.TypeId = TransactionType.Id` |

**Filters**
- `Transaction.AcountId = SelectedAccountId`

**Sorts**
- `Transaction.CreatedOn`

**Fetch mode:** On Demand

**Max Records:** 4

---

### Aggregates inside the GetChartSampleData data action

These are embedded in the screen's data action logic (not screen aggregates), but are part of the Dashboard screen:

**GetChartDataMonthly**
- Source: `ChartData`
- Group-By: `Month` → `ChartData.Month`
- Aggregated: `ExpensesSum` = Sum(`ChartData.Expenses`), `IncomeSum` = Sum(`ChartData.Income`), `OrderMin` = Min(`ChartData.Order`)
- Sort (in group-by): `OrderMin`
- Max Records: none (unlimited)

**GetChartDataWeekly**
- Source: `ChartData`
- Filter: `ChartData.Order > FromWeekNumber and ChartData.Order <= ToWeekNumber`
- Sort: `ChartData.Order`
- Max Records: none (unlimited)

**GetChartDataQuarterly**
- Source: `ChartData`
- Group-By: `Quarter` → `ChartData.Quarter`
- Aggregated: `ExpensesSum` = Sum(`ChartData.Expenses`), `IncomeSum` = Sum(`ChartData.Income`), `OrderMin` = Min(`ChartData.Order`)
- Sort (in group-by): `OrderMin`
- Max Records: none (unlimited)

**GetCurrentQuarter**
- Source: `ChartData`
- Filter: `ChartData.Month = FormatDateTime(CurrDate(), "MMM")`
- Sort: `ChartData.Quarter`
- Max Records: 1

**GetChartDataWeekly_Previous**
- Source: `ChartData`
- Sort: `ChartData.Order`
- Max Records: `Abs(FromWeekNumber)` (dynamic)

---

## Turn 2 — Structure + functions + static entity + expressions (Mentor narrative, verbatim)

### Raw FormatCurrencyCustom Model API dump (getClientAction tool output, verbatim)

```csharp
(OutSystems.Model.IESpace homeBankingPortal) => {

    /*** creating IClientAction 'FormatCurrencyCustom' ***/
    var formatCurrencyCustom = homeBankingPortal.CreateClientAction("FormatCurrencyCustom");
    formatCurrencyCustom.Description = null; // default value
    var utils = homeBankingPortal.Folders.Named("Utils");
    formatCurrencyCustom.Folder = utils;
    formatCurrencyCustom.Function = true;
    formatCurrencyCustom.Icon = null; // default value
    formatCurrencyCustom.Public = false; // default value

    var amount = formatCurrencyCustom.CreateInputParameter("Amount");
    amount.DataType = homeBankingPortal.CurrencyType;
    amount.Description = null; // default value
    amount.IsMandatory = true; // default value

    var startNode = formatCurrencyCustom.CreateNode<OutSystems.Model.Logic.Nodes.IStartNode>();
    startNode.IsDisabled = false; // default value

    var assignNode = formatCurrencyCustom.CreateNode<OutSystems.Model.Logic.Nodes.IAssignNode>();
    assignNode.HorizontalPosition = 3192;
    assignNode.IsDisabled = false; // default value
    assignNode.Label = null; // default value
    assignNode.VerticalPosition = 2964;

    var assignment = assignNode.CreateAssignment("FormatedAmount", "FormatCurrency(Amount,Client.Currency,2,Client.DecimalSeparator,Client.GroupSeparator)");
    startNode.Target = assignNode;

    var endNode = formatCurrencyCustom.CreateNode<OutSystems.Model.Logic.Nodes.IEndNode>();
    endNode.HorizontalPosition = 3196;
    endNode.IsDisabled = false; // default value
    endNode.VerticalPosition = 5120;
    assignNode.Target = endNode;

    var formatedAmount = formatCurrencyCustom.CreateOutputParameter("FormatedAmount");
    formatedAmount.DataType = homeBankingPortal.TextType;
    formatedAmount.SetDefaultValue(null); // default value
    formatedAmount.Description = null; // default value
}
```

### Raw Locale2 probe stdout (applyModelApiCode, verbatim, trimmed of expression-wrapper noise markers `[Value[ServiceStudio.Expressions.AbstractExpression]]`)

```
=== LOCALE2 ATTRIBUTES ===
  Attr: Id | Type: Text (BasicTypes.Text:uROOBXPvQEyU76NWO+1uxQ) | Mandatory: True
  Attr: Label | Type: Text (BasicTypes.Text:uROOBXPvQEyU76NWO+1uxQ) | Mandatory: True
  Attr: Order | Type: Integer (BasicTypes.Integer:j2Lc0phK0kuggij4gQYfAw) | Mandatory: True
  Attr: Is_Active | Type: Boolean (BasicTypes.Boolean:oD0fxvc7hUOX_305zIXIlg) | Mandatory: True
  Attr: CodeDisplay | Type: Text (BasicTypes.Text:uROOBXPvQEyU76NWO+1uxQ) | Mandatory: False

=== LOCALE2 RECORDS === (record: Id / Label / Order / Is_Active / CodeDisplay)
  Chinese:    "zh-Hant" / "中文 (Chinese)" / 8 / True / "CN"
  English:    "en-US" / "English (English)" / 5 / True / "EN"
  Korean:     "ko-KR" / "한국어 (Korean)" / 15 / True / "KR"
  German:     "de-DE" / "Deutsch (German)" / 11 / True / "DE"
  Spanish:    "es" / "Español (Spanish)" / 2 / True / "ES"
  Thai:       "th-TH" / "ไทย (Thai)" / 7 / True / "TH"
  Arabic:     "ar-SA" / "العربية (Arabic)" / 1 / True / "AR"
  Dutch:      "nl-NL" / "Nederlands (Dutch)" / 12 / True / "NL"
  Portuguese: "pt-PT" / "Português (Portuguese)" / 4 / True / "PT"
  Indonesian: "id-ID" / "Bahasa Indonesia (Indonesian)" / 10 / True / "ID"
  Japanese:   "ja-JP" / "日本語 (Japanese)" / 3 / True / "JP"
  Russian:    "ru-RU" / "русский (Russian)" / 13 / True / "RU"
  Swedish:    "sv-SE" / "Svenska (Swedish)" / 14 / True / "SE"
  Italian:    "it-IT" / "Italiano (Italian)" / 9 / True / "IT"
  French:     "fr-FR" / "Français (French)" / 6 / True / "FR"
```

### Turn 2 terminal narrative (verbatim)

All four pieces are now fully gathered. Here is the complete diagnosis:

---

## 1. ChartCardsValue — Full Definition

`ChartCardsValue` is **not a named Structure** — it is a **local variable on the Dashboard screen** whose type is an anonymous inline structure. Its definition (derived from the screen's local variable declaration):

| Attribute | Data Type | Default |
|---|---|---|
| `Balance` | Currency | (none) |
| `BalanceLabel` | Text | (none) |
| `BalancePercent` | Integer | (none) |
| `Expenses` | Currency | (none) |
| `ExpensesPercent` | Integer | (none) |
| `Income` | Currency | (none) |
| `IncomePercent` | Integer | (none) |
| `Label` | Text | (none) |

All attributes have no default value set. The variable itself has no default value.

---

## 2. FormatCurrencyCustom — Full Implementation

**Inputs**
- `Amount` (Currency, mandatory)

**Outputs**
- `FormatedAmount` (Text)

**Logic flow**

1. **Start**
2. **Assign** — sets `FormatedAmount`:
   ```
   FormatCurrency(Amount, Client.Currency, 2, Client.DecimalSeparator, Client.GroupSeparator)
   ```
3. **End**

That's the entire action — a single assignment wrapping the built-in `FormatCurrency` with the client-side currency symbol, decimal separator, and group separator.

(Capture note: the action lives in folder `Utils`, `Function = true`, `Public = false` — see raw Model API dump above.)

---

## 3. Locale2 Static Entity — Full Definition

**Attributes**

| Name | Data Type | Mandatory |
|---|---|---|
| `Id` | Text | Yes |
| `Label` | Text | Yes |
| `Order` | Integer | Yes |
| `Is_Active` | Boolean | Yes |
| `CodeDisplay` | Text | No |

**Records** (sorted by Order value)

| Record Name | Id | Label | Order | Is_Active | CodeDisplay |
|---|---|---|---|---|---|
| Arabic | `ar-SA` | العربية (Arabic) | 1 | True | AR |
| Spanish | `es` | Español (Spanish) | 2 | True | ES |
| Japanese | `ja-JP` | 日本語 (Japanese) | 3 | True | JP |
| Portuguese | `pt-PT` | Português (Portuguese) | 4 | True | PT |
| English | `en-US` | English (English) | 5 | True | EN |
| French | `fr-FR` | Français (French) | 6 | True | FR |
| Thai | `th-TH` | ไทย (Thai) | 7 | True | TH |
| Chinese | `zh-Hant` | 中文 (Chinese) | 8 | True | CN |
| Italian | `it-IT` | Italiano (Italian) | 9 | True | IT |
| Indonesian | `id-ID` | Bahasa Indonesia (Indonesian) | 10 | True | ID |
| German | `de-DE` | Deutsch (German) | 11 | True | DE |
| Dutch | `nl-NL` | Nederlands (Dutch) | 12 | True | NL |
| Russian | `ru-RU` | русский (Russian) | 13 | True | RU |
| Swedish | `sv-SE` | Svenska (Swedish) | 14 | True | SE |
| Korean | `ko-KR` | 한국어 (Korean) | 15 | True | KR |

(Capture note: Locale2 is a referenced static entity from producer module `AgentsCommonResources`, not local to HomeBankingPortal.)

---

## 4. Dashboard Expressions Referencing the Target Symbols

All expressions are verbatim as defined in the screen. Widget paths use `>` to denote nesting.

---

### ChartCardsValue references

**SetChartCards screen action — Assign "ChartCardsValue" node**
- `ChartCardsValue.Expenses` ← `GetChartSampleData.ChartDataList[SelectedIndex].Expenses`
- `ChartCardsValue.ExpensesPercent` ← `(GetChartSampleData.ChartDataList[SelectedIndex].Expenses - GetChartSampleData.ChartDataList[PreviousIndex].Expenses)/GetChartSampleData.ChartDataList[SelectedIndex].Expenses * 100`
- `ChartCardsValue.Income` ← `GetChartSampleData.ChartDataList[SelectedIndex].Income`
- `ChartCardsValue.IncomePercent` ← `(GetChartSampleData.ChartDataList[SelectedIndex].Income - GetChartSampleData.ChartDataList[PreviousIndex].Income)/GetChartSampleData.ChartDataList[SelectedIndex].Income * 100`
- `ChartCardsValue.Label` ← `PreviousLabel + "-" + CurrentLabel`
- `ChartCardsValue.Balance` ← `0`
- `ChartCardsValue.BalancePercent` ← `0`
- `ChartCardsValue.BalanceLabel` ← `"Balance "`

**SetChartCards — ForEach cycle Assign node**
- `ChartCardsValue.Balance` ← `ChartCardsValue.Balance + GetChartSampleData.ChartDataList.Current.Income - GetChartSampleData.ChartDataList.Current.Expenses`

**SetChartCards — Assign after ForEach**
- `ChartCardsValue.BalancePercent` ← `(ChartCardsValue.Balance - (ChartCardsValue.Balance - (GetChartSampleData.ChartDataList[SelectedIndex].Income - GetChartSampleData.ChartDataList[SelectedIndex].Expenses)))/ChartCardsValue.Balance * 100`

**UI — SideContent > container44 > container61 > container36 > container37 > container43 > Gallery > ItemCard #1 (Balance card)**
- `Label` argument: `ChartCardsValue.BalanceLabel`
- `Balance` argument: `ChartCardsValue.Balance`
- Percentage expression: `If(ChartCardsValue.BalancePercent>0,"+","")+ChartCardsValue.BalancePercent+"%"`
- Range expression: `ChartCardsValue.Label`

**UI — … > Gallery > ItemCard #2 (Income card)**
- `Balance` argument: `ChartCardsValue.Income`
- Percentage expression: `If(ChartCardsValue.IncomePercent>0,"+","")+ChartCardsValue.IncomePercent+"%"`
- Range expression: `ChartCardsValue.Label`

**UI — … > Gallery > ItemCard #3 (Expenses card)**
- `Balance` argument: `ChartCardsValue.Expenses`
- Percentage expression: `If(ChartCardsValue.ExpensesPercent>0,"+","")+ChartCardsValue.ExpensesPercent+"%"`
- Range expression: `ChartCardsValue.Label`

---

### TransactionType references

**UI — MainContent > container14 > container20 > ColumnsMediumLeft > Column1 > container21 > container25 > IsTableLoadingOrEmpty > IsEmpty (False) > IsLoading (False) > List (GetLastTransactions.List) > container28 > container29 > HBIcon placeholder**
- Expression: `GetLastTransactions.List.Current.TransactionType.IconNameEN`

**Same list > container28 > container30 > container31**
- Expression: `GetLabelByLocale(GetLastTransactions.List.Current.TransactionType.LabelLocale, Client.LocaleId)`

**Same list > container28 > container33 > container34**
- Style expression on amount sign: `"font-semi-bold text-"+GetLastTransactions.List.Current.TransactionType.Color`
- Value expression (sign): `If(GetLastTransactions.List.Current.TransactionType.IsIncrease,"+","-")`
- Style on currency symbol: `"font-semi-bold text-"+GetLastTransactions.List.Current.TransactionType.Color`
- Style on amount: `"font-semi-bold text-"+GetLastTransactions.List.Current.TransactionType.Color`

---

### AmountSum references

**UI — SideContent > container61 > YourGoals > container62 > Carousel > List (GetCustomerGoals.List) > container64 > container65 > AlignCenter > container69 (Arabic branch)**
- Expression: `FormatCurrencyCustom(GetCustomerGoals.List.Current.AmountSum)`

**Same list > container65 > AlignCenter > container70 (non-Arabic branch)**
- Expression: `FormatCurrencyCustom(GetCustomerGoals.List.Current.AmountSum)`

**ProgressBar in container71**
- `Progress` argument: `GetCustomerGoals.List.Current.AmountSum/GetCustomerGoals.List.Current.TargetAmount*100`

**UI — SideContent > container61 > YourLoans > container72 > Carousel > List (GetCustomerLoans.List) > container74 > container75 > AlignCenter > container79 (Arabic branch)**
- Expression: `FormatCurrencyCustom(GetCustomerLoans.List.Current.AmountSum)`

**Same list > container75 > AlignCenter > container80 (non-Arabic branch)**
- Expression: `FormatCurrencyCustom(GetCustomerLoans.List.Current.AmountSum)`

**ProgressBar in container81**
- `Progress` argument: `GetCustomerLoans.List.Current.AmountSum/GetCustomerLoans.List.Current.Amount*100`

**ConsolidatedPositionSidebarOpen screen action — ForEach Assign**
- `TotalLoan` ← `TotalLoan + GetCustomerLoans.List.Current.Amount - GetCustomerLoans.List.Current.AmountSum`

---

### GoalName references

**UI — YourGoals > Carousel > List (GetCustomerGoals.List) > container64 > container65 > AlignCenter > container66 > container67**
- Expression: `GetCustomerGoals.List.Current.GoalName`

---

### TargetAmount references

**UI — YourGoals > … > container69 (Arabic branch)**
- Expression: `FormatCurrencyCustom(GetCustomerGoals.List.Current.TargetAmount)`

**UI — YourGoals > … > container70 (non-Arabic branch)**
- Expression: `FormatCurrencyCustom(GetCustomerGoals.List.Current.TargetAmount)`

**ProgressBar in container71**
- `Progress` argument: `GetCustomerGoals.List.Current.AmountSum/GetCustomerGoals.List.Current.TargetAmount*100`

---

### LabelLocale references

**GetAccountsOnAfterFetch screen action — ListAppendAccounts**
- `Name` field in mapTo: `GetLabelByLocale(LabelLocale, Client.LocaleId)`

**GetChartDataOptionsOnAfterFetch screen action — ListAppendAll**
- `Text` field in mapTo: `GetLabelByLocale(ChartDataOption.LabelLocale, Client.LocaleId)`

**UI — MainContent > List (GetLastTransactions.List) > container28 > container30 > container31**
- Expression: `GetLabelByLocale(GetLastTransactions.List.Current.TransactionType.LabelLocale, Client.LocaleId)`

**UI — YourLoans > Carousel > List (GetCustomerLoans.List) > container74 > container75 > AlignCenter > container76 > container77**
- Expression: `GetLabelByLocale(GetCustomerLoans.List.Current.LabelLocale, Client.LocaleId)`

**UI — SideContent > Assets2 > Accordion > List (GetAssets.List) > AccountAccordian**
- `Label` argument: `GetLabelByLocale(GetAssets.List.Current.LabelLocale, Client.LocaleId)`

---

### Amount references (CustomerLoan.Amount)

**UI — YourLoans > … > container79 (Arabic branch)**
- Expression: `FormatCurrencyCustom(GetCustomerLoans.List.Current.Amount)`

**UI — YourLoans > … > container80 (non-Arabic branch)**
- Expression: `FormatCurrencyCustom(GetCustomerLoans.List.Current.Amount)`

**ProgressBar in container81**
- `Progress` argument: `GetCustomerLoans.List.Current.AmountSum/GetCustomerLoans.List.Current.Amount*100`

**ConsolidatedPositionSidebarOpen — ForEach Assign**
- `TotalLoan` ← `TotalLoan + GetCustomerLoans.List.Current.Amount - GetCustomerLoans.List.Current.AmountSum`

---

### FormatCurrencyCustom call sites on Dashboard

| Location | Expression |
|---|---|
| GetChartSampleData data action — ServiceFormatCurrencyCustomIncome node | `ChartDataList[index].Income` (passed as Amount) |
| GetChartSampleData data action — ServiceFormatCurrencyCustomExpenses node | `ChartDataList[index].Expenses` (passed as Amount) |
| YourGoals list > container69 (Arabic) | `FormatCurrencyCustom(GetCustomerGoals.List.Current.AmountSum)` |
| YourGoals list > container70 (non-Arabic) | `FormatCurrencyCustom(GetCustomerGoals.List.Current.AmountSum)` |
| YourGoals list > container69 (Arabic) | `FormatCurrencyCustom(GetCustomerGoals.List.Current.TargetAmount)` |
| YourGoals list > container70 (non-Arabic) | `FormatCurrencyCustom(GetCustomerGoals.List.Current.TargetAmount)` |
| YourLoans list > container79 (Arabic) | `FormatCurrencyCustom(GetCustomerLoans.List.Current.AmountSum)` |
| YourLoans list > container80 (non-Arabic) | `FormatCurrencyCustom(GetCustomerLoans.List.Current.AmountSum)` |
| YourLoans list > container79 (Arabic) | `FormatCurrencyCustom(GetCustomerLoans.List.Current.Amount)` |
| YourLoans list > container80 (non-Arabic) | `FormatCurrencyCustom(GetCustomerLoans.List.Current.Amount)` |
| ConsolidatedPosition sidebar > Assets2 > container88 | `FormatCurrencyCustom(TotalAssets)` |
| ConsolidatedPosition sidebar > Depts2 > container92 | `FormatCurrencyCustom(TotalDept)` |

*(Note: the two GetChartSampleData calls go through a service action `ServiceFormatCurrencyCustom` from HomeBankingCore, not the local `FormatCurrencyCustom` client action — they are distinct.)*

---

### Locale2 references

**UI — YourGoals list > container65 > IfWidget (condition)**
- `Client.LocaleId = Entities.Locale2.Arabic`

**UI — YourLoans list > container75 > IfWidget (condition)**
- `Client.LocaleId = Entities.Locale2.Arabic`

**UI — MainContent > List (GetLastTransactions.List) > container28 > container32 (Visible expression)**
- `Client.LocaleId = Entities.Locale2.English`

**SetChartCards screen action — Assign "Labels" node**
- `If(TextToInteger(SelectedChartDataOptionId) = Entities.ChartDataOption.Monthly, FormatDateLocale(TextToDate(GetChartSampleData.ChartDataList[PreviousIndex].Label), Client.LocaleId, Entities.DateFormat.MMM), GetChartSampleData.ChartDataList[PreviousIndex].Label)`
- `If(TextToInteger(SelectedChartDataOptionId) = Entities.ChartDataOption.Monthly, FormatDateLocale(TextToDate(GetChartSampleData.ChartDataList[SelectedIndex].Label), Client.LocaleId, Entities.DateFormat.MMM), GetChartSampleData.ChartDataList[SelectedIndex].Label)`

*(These pass `Client.LocaleId` which is of type `Locale2 Identifier`, so they implicitly reference `Locale2`.)*

---

## Capture deviations

1. Turn 1 recipe failed compile (CS0234 × 5) — fallback natural-language turn used per playbook. Errors recorded verbatim above.
2. ChartCardsValue is NOT a named Structure (it is a Dashboard screen local variable with an anonymous inline structure type) — a rebuild must declare it as a screen local var, not via CreateStructure.
3. Locale2 record probe needed one self-corrected retry inside the mentor run (CS1061: IStaticEntityRecordSignature has no Name; mentor used reflection). Final stdout is complete.
4. GetAccounts raw authoring dump was captured from getScreen tool output (truncated at 277,912 chars by the event buffer); aggregates 2-7 + data-action aggregates come from the mentor terminal narrative, which is byte-complete in the run summary.

## Turn 3 — Screen action bodies + GetLabelByLocale (2026-06-11)

Source: fresh mentor session aac15f0c-474b-4055-8a92-f5cceb38787c on ORIGINAL Home Banking Portal (fa7ab595-f8cd-4140-8826-2acc484727b6), run 74f26c5f-2def-4e22-8b75-3c6e019c8341, diagnose-only, no publish. Terminal narrative verbatim below.

The `GetLabelByLocale` client action lives in `AgentsCommonResources`, which is a referenced library — its internal logic is not accessible from this application. I have all the information needed for the full diagnosis. Here is the complete breakdown:

---

## Dashboard Screen — Diagnostic Report

### Local Variables Involved

| Variable | Type | Default |
|---|---|---|
| `TotalBalance` | Currency | 0 |
| `TotalAssets` | Currency | 0 |
| `TotalDept` | Currency | 0 |
| `ChartCardsValue` | Anonymous record (Balance, BalanceLabel, BalancePercent, Expenses, ExpensesPercent, Income, IncomePercent, Label) | all zeroes/empty |

---

### `TotalBalance` — Assigned in `GetAccountsOnAfterFetch`

**Wired to:** `GetAccounts` aggregate → `OnAfterFetch`

**Flow:**

1. **Start**
2. **Assign** → `SelectedAccountId = GetAccounts.List.Current.Id`
3. **Assign** → `TotalBalance = 0`
4. **ListClear** → clears `Accounts`
5. **ForEach** over `GetAccounts.List`
   - **CycleTarget → ListAppend** to `Accounts`:
     ```
     GetAccounts.List.Current mapTo {
       AccountBalance: AccountBalance,
       AccountNumber: AccountNumber,
       Id: Id,
       Name: GetLabelByLocale(LabelLocale, Client.LocaleId),
       Order: GetAccounts.List.CurrentRowNumber,
       TypeId: ProductTypeId
     }
     ```
   - **If** `GetAccounts.List.Current.ProductTypeId = Entities.ProductType.Checking`
     `or GetAccounts.List.Current.ProductTypeId = Entities.ProductType.Saving`
     - **True →** **Assign** → `TotalBalance = TotalBalance + GetAccounts.List.Current.AccountBalance` → back to ForEach
     - **False →** back to ForEach (credit cards are excluded from TotalBalance)
6. **ForEach.Target →** **RefreshData** `GetLastTransactions` (max 4)
7. **End**

**Key point:** `TotalBalance` accumulates only Checking and Saving account balances. Credit cards are excluded.

---

### `TotalAssets` — Assigned in `GetAssetsOnAfterFetch`

**Wired to:** `GetAssets` aggregate → `OnAfterFetch`

**Flow:**

1. **Start**
2. **Assign** → `TotalAssets = 0`
3. **ForEach** over `GetAssets.List`
   - **CycleTarget → Assign** → `TotalAssets = TotalAssets + GetAssets.List.Current.AccountBalance` → back to ForEach
4. **ForEach.Target → End**

**Key point:** `TotalAssets` sums the `AccountBalance` aggregated attribute from `GetAssets`, which covers Checking, Saving, and Investment accounts (credit cards excluded). The `AmountWithSign` calculated attribute in `GetAssets` uses `If(TransactionType.IsIncrease, Transaction.Amount, -Transaction.Amount)` — no credit-card sign flip.

---

### `TotalDept` — Assigned in `ConsolidatedPositionSidebarOpen` (screen action, triggered by button click)

**Not wired to any aggregate OnAfterFetch.** It is computed on demand when the user opens the Consolidated Position sidebar.

**Flow:**

1. **Start**
2. **Assign** → `IsDeptConsolidatedPositionOption = False`
3. **ListClear** → `DeptList`
4. **ListAppend** to `DeptList`:
   ```
   { Balance: GetCreditCardsDept.List.Current.AccountBalance,
     Color: GetCreditCardsDept.List.Current.Color,
     IsLoan: False,
     Label: GetCreditCardsDept.List.Current.Label }
   ```
   *(iterates over the already-fetched `GetCreditCardsDept` list — no ForEach, uses `.Current` which is the last/current record)*
5. **Assign** → `TotalDept = GetCreditCardsDept.List.Current.AccountBalance`
6. **Assign** → `TotalLoan = 0` (local variable)
7. **ForEach** over `GetCustomerLoans.List`
   - **CycleTarget → Assign** → `TotalLoan = TotalLoan + GetCustomerLoans.List.Current.Amount - GetCustomerLoans.List.Current.AmountSum` → back to ForEach
8. **ForEach.Target → Assign** → `TotalDept = TotalDept + TotalLoan`
9. **ListAppend** to `DeptList`:
   ```
   { Balance: TotalLoan, Color: "#3AA4FF", IsLoan: True, Label: "Loans" }
   ```
10. **SidebarOpen** → opens `ConsolidatedPositionSidebare`
11. **End**

**Key point:** `TotalDept` = credit card debt (from `GetCreditCardsDept`) + remaining loan principal (loan `Amount` minus payments `AmountSum`). Note that step 4 uses `.Current` without a ForEach — this means only the **last record** in `GetCreditCardsDept.List` contributes to the initial `TotalDept` value (potential bug: if there are multiple credit card types, only the last one is captured before the ForEach adds loans).

---

### `ChartCardsValue` — Assigned in `SetChartCards` (screen action)

**Wired to:** `GetChartSampleData` data action → `OnAfterFetch` → calls `SetChartCards(SelectedIndex: GetChartSampleData.SelectedIndex)`. Also called directly from `ColumnChartLabelOnClick(ClickedIndex)` when the user clicks a chart bar label.

#### `SetChartCards` — Inputs: `SelectedIndex (Integer, mandatory)`; Locals: `PreviousIndex`, `PreviousLabel`, `CurrentLabel`

**Flow:**

1. **Start**
2. **Assign** (no label):
   - `PreviousIndex = If(SelectedIndex = 0, GetChartSampleData.ChartDataList.Length - 1, SelectedIndex - 1)`
3. **Assign** (label: "Labels"):
   - `PreviousLabel = If(TextToInteger(SelectedChartDataOptionId) = Entities.ChartDataOption.Monthly, FormatDateLocale(TextToDate(GetChartSampleData.ChartDataList[PreviousIndex].Label), Client.LocaleId, Entities.DateFormat.MMM), GetChartSampleData.ChartDataList[PreviousIndex].Label)`
   - `CurrentLabel = If(TextToInteger(SelectedChartDataOptionId) = Entities.ChartDataOption.Monthly, FormatDateLocale(TextToDate(GetChartSampleData.ChartDataList[SelectedIndex].Label), Client.LocaleId, Entities.DateFormat.MMM), GetChartSampleData.ChartDataList[SelectedIndex].Label)`
4. **Assign** (label: "ChartCardsValue"):
   - `ChartCardsValue.Expenses = GetChartSampleData.ChartDataList[SelectedIndex].Expenses`
   - `ChartCardsValue.ExpensesPercent = (ChartDataList[SelectedIndex].Expenses - ChartDataList[PreviousIndex].Expenses) / ChartDataList[SelectedIndex].Expenses * 100`
   - `ChartCardsValue.Income = GetChartSampleData.ChartDataList[SelectedIndex].Income`
   - `ChartCardsValue.IncomePercent = (ChartDataList[SelectedIndex].Income - ChartDataList[PreviousIndex].Income) / ChartDataList[SelectedIndex].Income * 100`
   - `ChartCardsValue.Label = PreviousLabel + "-" + CurrentLabel`
   - `ChartCardsValue.Balance = 0`
   - `ChartCardsValue.BalancePercent = 0`
   - `ChartCardsValue.BalanceLabel = "Balance "`
5. **If** `SelectedIndex = 0`
   - **True →** **End** (Balance stays 0)
   - **False →** ForEach
6. **ForEach** over `GetChartSampleData.ChartDataList`, MaxIterations = `SelectedIndex`
   - **CycleTarget → Assign** → `ChartCardsValue.Balance = ChartCardsValue.Balance + GetChartSampleData.ChartDataList.Current.Income - GetChartSampleData.ChartDataList.Current.Expenses` → back to ForEach
7. **ForEach.Target → Assign**:
   - `ChartCardsValue.BalancePercent = (ChartCardsValue.Balance - (ChartCardsValue.Balance - (ChartDataList[SelectedIndex].Income - ChartDataList[SelectedIndex].Expenses))) / ChartCardsValue.Balance * 100`
   *(simplifies to: current period net / cumulative balance × 100)*
8. **End**

**Key point:** `ChartCardsValue.Balance` is the **cumulative net** (income − expenses) from index 0 up to (but not including) `SelectedIndex`. The `BalancePercent` is the current period's net as a percentage of that cumulative balance.

---

### `GetChartSampleDataOnAfterFetch` — The OnAfterFetch Handler

**Wired to:** `GetChartSampleData` data action

**Flow:**

1. **Start**
2. **ExecuteClientAction** → `SetChartCards(SelectedIndex: GetChartSampleData.SelectedIndex)`
3. **End**

This is the sole bridge between the chart data action completing and the `ChartCardsValue` record being populated.

---

### `GetLabelByLocale` — Referenced from `AgentsCommonResources`

**Signature:**
- **Inputs:** `LocaleString (Text, mandatory)`, `LocaleId (Locale2 Identifier, mandatory)`
- **Output:** `Label (Text)`
- **Type:** Client action, also available as a server action in the same module

**Internal logic is not accessible** — it lives in the `AgentsCommonResources` library module and is read-only from this application. Based on its signature and usage throughout the Dashboard (e.g., `GetLabelByLocale(LabelLocale, Client.LocaleId)`, `GetLabelByLocale(ChartDataOption.LabelLocale, Client.LocaleId)`), it parses a locale-keyed string (likely a JSON or delimited string stored in `LabelLocale` attributes) and returns the label for the given locale identifier.

---

### Summary of Wiring

| Variable | Set by | Triggered by |
|---|---|---|
| `TotalBalance` | `GetAccountsOnAfterFetch` | `GetAccounts` OnAfterFetch |
| `TotalAssets` | `GetAssetsOnAfterFetch` | `GetAssets` OnAfterFetch |
| `TotalDept` | `ConsolidatedPositionSidebarOpen` | User clicks "Consolidated Position" button |
| `ChartCardsValue` | `SetChartCards` | `GetChartSampleData` OnAfterFetch → `GetChartSampleDataOnAfterFetch`; also on chart label click via `ColumnChartLabelOnClick` |

### GetLabelByLocale raw read-back (getClientAction tool output, verbatim)

```json
{
  "Name": "GetLabelByLocale",
  "Object": "IClientActionSignature",
  "Function": "True",
  "InputParameters": [
    { "Name": "LocaleString", "Object": "IInputParameterSignature", "DataType": "Text", "IsMandatory": "True" },
    { "Name": "LocaleId", "Object": "IInputParameterSignature", "DataType": "Locale2 Identifier", "IsMandatory": "True" }
  ],
  "OutputParameters": [
    { "Name": "Label", "Object": "IOutputParameterSignature", "DataType": "Text" }
  ]
}
```
GlobalKey (producer*element): `2A5uDfh5wkKmZLRlbbGH6w*RqhsG84kiECGEOl_4g_2_Q` (AgentsCommonResources/GetLabelByLocale).

### Supplemental capture — GetLabelByLocale body from AgentsCommonResources (0d6e0ed8-79f8-42c2-a664-b4656db187eb, session ac4a87e4-6b20-4979-8f4d-6de4bd1887ef, run 228c46e6, read-only, cancelled after tool_end)

Module context (from get_app_summary stdout): AgentsCommonResources is a LowCodeLibrary. Local static entity **Locale** (records: Indonesian, Japanese, English, Italian, Swedish, Russian, Arabic, Portuguese, German, Thai, Korean, French, Chinese, Dutch, Spanish). Local structure **LocaleStruct**: AR (Text), DE (Text — German Language), EN (Text), ES (Text), JAJP (Text), KR (Text), PT (Text). NOTE: inside its home module the static entity is named `Locale`; consumer apps see it as `Locale2`.

**Client action `GetLabelByLocale` — raw getClientAction read-back, verbatim:**

```csharp
(OutSystems.Model.IESpace agentsCommonResources) => {

    /*** creating IClientAction 'GetLabelByLocale' ***/
    var getLabelByLocale = agentsCommonResources.CreateClientAction("GetLabelByLocale");
    getLabelByLocale.Description = null; // default value
    getLabelByLocale.Folder = null; // default value
    getLabelByLocale.Function = true;
    getLabelByLocale.Icon = null; // default value
    getLabelByLocale.Public = true;

    var localeString = getLabelByLocale.CreateInputParameter("LocaleString");
    localeString.DataType = agentsCommonResources.TextType;
    localeString.Description = null; // default value
    localeString.IsMandatory = true; // default value

    var localeId = getLabelByLocale.CreateInputParameter("LocaleId");
    var locale = agentsCommonResources.Entities.OfType<OutSystems.Model.Data.IStaticEntity>().Named("Locale");
    localeId.DataType = locale.IdentifierType;
    localeId.Description = null; // default value
    localeId.IsMandatory = true; // default value

    var startNode = getLabelByLocale.CreateNode<OutSystems.Model.Logic.Nodes.IStartNode>();
    startNode.IsDisabled = false; // default value

    var ifNode = getLabelByLocale.CreateNode<OutSystems.Model.Logic.Nodes.IIfNode>();
    ifNode.SetCondition("LocaleId = NullTextIdentifier()");
    ifNode.HorizontalPosition = 3192;
    ifNode.IsDisabled = false; // default value
    ifNode.Label = null; // default value
    ifNode.VerticalPosition = 2964;
    startNode.Target = ifNode;

    var jSONDeserializeLocaleStruct = getLabelByLocale.CreateNode<OutSystems.Model.Logic.Nodes.IJSONDeserializeNode>("JSONDeserializeLocaleStruct").Below(ifNode, 1824);
    var localeStruct = agentsCommonResources.Structures.Named("LocaleStruct");
    jSONDeserializeLocaleStruct.DataType = localeStruct;
    jSONDeserializeLocaleStruct.DateFormat = OutSystems.Model.Enumerations.JSONDateFormat.ISO; // default value
    jSONDeserializeLocaleStruct.Description = null; // default value
    jSONDeserializeLocaleStruct.IsDisabled = false; // default value
    jSONDeserializeLocaleStruct.SetJSONString("LocaleString");
    ifNode.FalseTarget = jSONDeserializeLocaleStruct;

    var assignNode = getLabelByLocale.CreateNode<OutSystems.Model.Logic.Nodes.IAssignNode>().ToTheRightOf(ifNode, 1596);
    assignNode.IsDisabled = false; // default value
    assignNode.Label = null; // default value
    assignNode.Target = jSONDeserializeLocaleStruct;

    var assignment = assignNode.CreateAssignment("LocaleId", "Entities.Locale.English");
    ifNode.TrueTarget = assignNode;

    var assignNode2 = getLabelByLocale.CreateNode<OutSystems.Model.Logic.Nodes.IAssignNode>().ConnectedBelow(jSONDeserializeLocaleStruct, 1824);
    assignNode2.IsDisabled = false; // default value
    assignNode2.Label = null; // default value

    var assignment2 = assignNode2.CreateAssignment("Label", "If(LocaleId = Entities.Locale.English, JSONDeserializeLocaleStruct.Data.EN,\nIf(LocaleId = Entities.Locale.Portuguese, JSONDeserializeLocaleStruct.Data.PT,\nIf(LocaleId = Entities.Locale.German, JSONDeserializeLocaleStruct.Data.DE,\nIf(LocaleId = Entities.Locale.Japanese, JSONDeserializeLocaleStruct.Data.JAJP, \nIf(LocaleId = Entities.Locale.Arabic, JSONDeserializeLocaleStruct.Data.AR, \nIf(LocaleId = Entities.Locale.Korean, JSONDeserializeLocaleStruct.Data.KR, \nIf(LocaleId = Entities.Locale.Spanish, JSONDeserializeLocaleStruct.Data.ES, \nJSONDeserializeLocaleStruct.Data.EN)))))))");

    var endNode = getLabelByLocale.CreateNode<OutSystems.Model.Logic.Nodes.IEndNode>();
    endNode.HorizontalPosition = 3196;
    endNode.IsDisabled = false; // default value
    endNode.VerticalPosition = 8436;
    assignNode2.Target = endNode;

    var label = getLabelByLocale.CreateOutputParameter("Label");
    label.DataType = agentsCommonResources.TextType;
    label.SetDefaultValue(null); // default value
    label.Description = null; // default value
}
```

**Server action `GetLabelByLocale` (same module) — identical deserialize + If-chain, but NO null-LocaleId guard branch:** Start → JSONDeserializeLocaleStruct(LocaleString → LocaleStruct) → Assign Label = (same nested If chain) → End. Signature identical (Function, Public).
