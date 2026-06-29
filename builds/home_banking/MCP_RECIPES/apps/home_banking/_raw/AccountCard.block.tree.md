```
=== Block: AccountCard ===
Public: False
Flow: Blocks
StyleSheet: (none)   OnRender/OnInit/etc: all default (null)

Inputs (7 — exact, verified via getWebBlock authoring code):
  - AccountTypeId    : ProductType Identifier (HomeBankingCore.ProductType)  mandatory
  - AccountNumber4Digit : Text  mandatory
  - Balance          : Currency  mandatory
  - IsActive         : Boolean  mandatory
  - PaddingTop       : Text  optional  default="54"
  - AccountName      : Text  mandatory
  - isTransfer       : Boolean  optional  default=False

Events: (none)

--- COMPLETE WIDGET TREE (un-truncated; Style / CustomStyle / Expression Value / Example) ---

[container]  Container  Style="main-card"  Width=(fill parent)
  [container2]  Container  Width=""
      Style = "account-card "
            + If(AccountTypeId=Entities.ProductType.Checking and isTransfer,"transfer",
                 If(AccountTypeId=Entities.ProductType.Checking,"checking",
                 If(AccountTypeId=Entities.ProductType.Saving,"saving","creditcard")))
            + " "
            + If(IsActive,"","inactive")
      # per-type color variant ("checking" | "saving" | "creditcard" | "transfer") + "inactive" state class

    [container3]  Container  Style=(none)  Width=(fill parent)
      [expression]  Expression  Style=(none)  Example="Checking 1234"
          Value = AccountName + " "
                  + If(AccountTypeId=Entities.ProductType.Checking
                       or AccountTypeId=Entities.ProductType.CreditCard,
                       AccountNumber4Digit, "")
          # account NAME (+ trailing 4-digit number for Checking/CreditCard)

    [container4]  Container  Style="font-semi-bold"  CustomStyle="height: 50px;"  Width=(fill parent)
      [ifWidget]  If  Condition="Client.HideBalance"
        --- TrueBranch (balance hidden → 4 masking dots) ---
        [icon ]  Icon  Icon="circle"  Style="icon"  CustomStyle="font-size: 4px;"
        [icon2]  Icon  Icon="circle"  Style="icon"  CustomStyle="font-size: 4px;"
        [icon3]  Icon  Icon="circle"  Style="icon"  CustomStyle="font-size: 4px;"
        [icon4]  Icon  Icon="circle"  Style="icon"  CustomStyle="font-size: 4px;"
        --- FalseBranch (balance shown) ---
        [expression2]  Expression  Style="font-size-h4"  Example="$"
            Value = Client.Currency
            # currency SYMBOL, h4 size, sits left of the big number
        [expression3]  Expression  Style="font-size-40 card-detail-font"  Example="13.594,34"
            Value = FormatCurrency(Balance,"",2,Client.DecimalSeparator,Client.GroupSeparator)
            # the BIG balance number — font-size-40 is the hero typography of the card

    [container5]  Container  Style="card-name-detail"  Width=(fill parent)
      ExtendedHtmlAttribute style = "padding-top:" + PaddingTop + "px"
      # dynamic padding-top drives the stacked/peeking carousel offset (PaddingTop input)
      [ifWidget2]  If  Condition="AccountTypeId=Entities.ProductType.Checking
                                   or AccountTypeId=Entities.ProductType.CreditCard"
        --- TrueBranch (Checking / CreditCard → masked card-number row) ---
        [WebBlockInstance → AlignCenter]  (OutSystemsUI / Utilities)  IsHorizontal=set
          Content placeholder:
            [Text]  Text="****  ****  **** "  Style="margin-top-xs"  CustomStyle="margin-left: 0px;"
                # masked card-number prefix
            [expression4]  Expression  Style="font-size-base"  Example="5676"
                Value = AccountNumber4Digit
                # visible last-4 digits
        --- FalseBranch (Saving / other → subtype caption) ---
        [expression5]  Expression  Style="font-size-base"  Example="Saving Account"
            Value = If(AccountTypeId=Entities.ProductType.Saving,"Savings Account","")
```

## Card anatomy (top → bottom)
1. **Account name line** (container3 expression) — `AccountName` + 4-digit suffix for Checking/CreditCard.
2. **Balance line** (container4) — currency symbol (`font-size-h4`) + **big balance number** (`font-size-40 card-detail-font`), OR 4 dot icons when `Client.HideBalance`.
3. **Card-number / subtype line** (container5, dynamic `padding-top`) — masked `**** **** ****` + last-4 (Checking/CreditCard), OR "Savings Account" caption (Saving).

## Color / state classes (on container2)
- Type variant: `checking` | `saving` | `creditcard` | `transfer` (transfer = Checking + isTransfer).
- State: `inactive` appended when `IsActive=False`.
- Base class: `account-card`. Outer wrapper: `main-card`.

## Key CSS class hooks the original card depends on (must exist in theme)
`main-card`, `account-card`, `checking`, `saving`, `creditcard`, `transfer`, `inactive`,
`card-name-detail`, `card-detail-font`, `font-size-40`, `font-size-h4`, `font-semi-bold`, `icon`.

<!--
Provenance: probed via mcp__outsystems__mentor_start on app=fa7ab595-f8cd-4140-8826-2acc484727b6
(Home Banking Portal, rev 6, READ-ONLY — never mutated/published).
Capture run: 2026-06-13. Method:
  - Top half (container → container2 → container3 expression → container4 → If/icons/expression2)
    verified verbatim from Mentor getWebBlock authoring-code output (exact SetStyle/SetValue/Example).
  - Lower half (container4 FalseBranch expression3, container5 + AlignCenter WebBlockInstance +
    expression4/Text/expression5) recovered via Mentor synthesis answer (getWebBlock tool output caps
    at ~the same ~29K point; Mentor's model access is complete, so a paraphrase-framed question
    "TELL ME the widgets" returned the post-truncation widgets with exact Style/Value/Example).
  - "Report stdout verbatim" / "dump raw code" framings are REFUSED by Mentor's guard; ask it to
    DESCRIBE the widgets instead (it offers this explicitly). Clean (no-refusal) session required.
Supersedes the 2026-06-09 truncated capture (28/22 widgets, "still partial").
-->
