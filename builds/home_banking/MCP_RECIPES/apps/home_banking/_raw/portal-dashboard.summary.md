Here is the complete widget tree of the **Dashboard** screen, derived from the screen definition:

```
=== Screen: Dashboard ===
Inputs: (none)
Locals: SelectedAccountId, SelectedChartDataOptionId, Accounts, ChartHeight, TotalBalance, TotalAssets, TotalDept, IsDeptConsolidatedPositionOption, HideChart, DeptList, ChartCardsValue, IsPortrait, ChatMessages, IsWaitingForResponse, ChartOptionList
Aggregates: GetAccounts, GetAssets, GetChartDataOptions, GetCreditCardsDept, GetCustomerGoals, GetCustomerLoans, GetLastTransactions
DataActions: GetChartSampleData

--- WIDGETS ---
[1] IMobileBlockInstanceWidget 'LayoutTopMenuRightSideInstance' (LayoutTopMenuRightSide)
  [Header placeholder]
    [1] IMobileBlockInstanceWidget 'MenuInstance' (Menu)
  [Title placeholder]
    [1] IContainer ''
      [1] ITextWidget '' Text="Total Balance"
    [2] IContainer '' Style="If(IsDesktop(), "display-flex justify-content-space-between", "display-grid gap-s")"
      [1] IContainer ''
        [1] IIfWidget '' Cond="Client.HideBalance"
          [TrueBranch]
            [1] IContainer '' Style='"balance-cntr"'
              [1] IIcon '' icon="circle"
              [2] IIcon '' icon="circle"
              [3] IIcon '' icon="circle"
              [4] IIcon '' icon="circle"
          [FalseBranch]
            [1] IContainer '' Style='"balance-cntr"'
              [1] IMobileBlockInstanceWidget 'AlignCenterInstance' (AlignCenter)
                [Content placeholder]
                  [1] IContainer ''
                    [1] IExpression '' Value="Client.Currency" Example="$"
                  [2] IContainer ''
                    [1] IExpression '' Value="FormatCurrency(TotalBalance,...)" Example="13.594,34"
      [2] IContainer '' Style="If(IsDesktop(), "vertical-align gap-s", "display-grid gap-s")"
        [1] IContainer '' CustomStyle="text-align: center;"
          [1] IButton '' Style='"btn btn-no-border padding-x-none margin-top-xs"'
            [1] IIfWidget '' Cond="Client.HideBalance"
              [TrueBranch]
                [1] IContainer ''
                  [1] IMobileBlockInstanceWidget 'AlignCenterInstance2' (AlignCenter)
                    [Content placeholder]
                      [1] ITextWidget '' Text="Show Balance"
                      [2] IMobileBlockInstanceWidget 'HBIconInstance' (HBIcon)
                        [IconName placeholder]
                          [1] ITextWidget '' Text="eyeshow"
              [FalseBranch]
                [1] IContainer ''
                  [1] IMobileBlockInstanceWidget 'AlignCenterInstance3' (AlignCenter)
                    [Content placeholder]
                      [1] ITextWidget '' Text="Hide Balance"
                      [2] IMobileBlockInstanceWidget 'HBIconInstance2' (HBIcon)
                        [IconName placeholder]
                          [1] ITextWidget '' Text="eyehide"
            OnClick → ToggleHideBallanceOnClick
        [2] IContainer ''
          [1] IButton '' Style='"btn margin-top-xs"'
            [1] ITextWidget '' Text="Account Insights"
            [2] IMobileBlockInstanceWidget 'HBIconInstance3' (HBIcon)
              [IconName placeholder]
                [1] ITextWidget '' Text="insights"
            OnClick → NotImplemented
        [3] IContainer ''
          [1] IButton '' Style='"btn btn-primary margin-top-xs"'
            [1] ITextWidget '' Text="Consolidated Position"
            [2] IMobileBlockInstanceWidget 'HBIconInstance4' (HBIcon)
              [IconName placeholder]
                [1] ITextWidget '' Text="columnchart"
            OnClick → ConsolidatedPositionSidebarOpen
  [MainContent placeholder]
    [1] IContainer ''
      [1] IContainer 'Carouselcntr' Style='"margin-top-l card-carousel-container"'
        [1] IIfWidget '' Cond="not Accounts.Empty and GetAccounts.IsDataFetched"
          [TrueBranch]
            [1] IMobileBlockInstanceWidget 'StackedCarouselInstance' (StackedCarousel)
              OnClick → CarouselAccountOnSlideMoved(ItemIndex=ActiveSlide)
              [Content placeholder]
                [1] IList '' Source="Accounts" Style='"list list-group dashboard-card-list"'
                  [1] IContainer 'ListItemClickable'
                    [1] IMobileBlockInstanceWidget 'AccountCardInstance' (AccountCard)
                      Balance=Accounts.Current.AccountBalance
                      AccountNumber4Digit=Substr(...)
                      AccountName=Accounts.Current.Name
                      IsActive=Accounts.Current.Id = SelectedAccountId
                      AccountTypeId=Accounts.Current.TypeId
    [2] IContainer '' Style='"margin-top-xl"'
      [1] IContainer '' Style="If(IsDesktop(), "display-flex", "display-grid") + " gap-base""
        [1] IContainer ''
          [1] IButton '' Style='"btn btn-primary ..."'
            [1] ITextWidget '' Text="Transfer"
            [2] IMobileBlockInstanceWidget 'HBIconInstance5' (HBIcon)
              [IconName placeholder]
                [1] ITextWidget '' Text="transfer"
            OnClick → Transfer screen (AccountId=SelectedAccountId)
        [2] IContainer ''
          [1] IButton '' Style='"btn btn-primary ..."'
            [1] ITextWidget '' Text="Pay"
            [2] IMobileBlockInstanceWidget 'HBIconInstance6' (HBIcon)
              [IconName placeholder]
                [1] ITextWidget '' Text="scan"
            OnClick → NotImplemented
        [3] IContainer ''
          [1] IButton '' Style='"btn ..."'
            [1] ITextWidget '' Text="Add"
            [2] IMobileBlockInstanceWidget 'HBIconInstance7' (HBIcon)
              [IconName placeholder]
                [1] ITextWidget '' Text="plussquare"
            OnClick → NotImplemented
    [3] IContainer '' Style='"margin-top-xxl"'
      [1] IMobileBlockInstanceWidget 'ColumnsMediumLeftInstance' (ColumnsMediumLeft)
        [Column1 placeholder]
          [1] IContainer ''
            [1] IContainer ''
              [1] IMobileBlockInstanceWidget 'ColumnsMediumRightInstance' (ColumnsMediumRight)
                [Column1 placeholder]
                  [1] IContainer '' Style='"font-size-base font-semi-bold"'
                    [1] ITextWidget '' Text="Last Transactions"
                [Column2 placeholder]
                  [1] IContainer '' CustomStyle="padding: 2px 0px 0px 0px; text-align: right;"
                    [1] ILink '' → NotImplemented
                      [1] ITextWidget '' Text="View All"
            [2] IContainer '' Style='"margin-top-xs"'
              [1] IContainer 'IsTableLoadingOrEmpty'
                [1] IIfWidget 'IsEmpty' Cond="GetLastTransactions.IsDataFetched and GetLastTransactions.List.Empty"
                  [TrueBranch]
                    [1] IContainer '' Style='"table-empty margin-top-l"'
                      [1] IMobileBlockInstanceWidget 'BlankSlateInstance' (BlankSlate)
                        [Icon placeholder]
                          [1] IMobileBlockInstanceWidget 'HBIconInstance8' (HBIcon)
                            [IconName placeholder]
                              [1] ITextWidget '' Text="transfer"
                        [Content placeholder]
                          [1] ITextWidget '' Text="There aren't any transctions."
                  [FalseBranch]
                    [1] IIfWidget 'IsLoading' Cond="not GetLastTransactions.IsDataFetched"
                      [TrueBranch]
                        [1] IContainer '' Style='"list-updating"'
                      [FalseBranch]
                        [1] IList '' Source="GetLastTransactions.List" Style='"list list-group"'
                          [1] IContainer '' Style='"item-card horizontal listItem"'
                            [1] IContainer '' Width="15%"
                              [1] IMobileBlockInstanceWidget 'HBIconInstance9' (HBIcon)
                                [IconName placeholder]
                                  [1] IExpression '' Value="...TransactionType.IconNameEN"
                            [2] IContainer '' Width="50%"
                              [1] IContainer ''
                                [1] IExpression '' Value="GetLabelByLocale(TransactionType.LabelLocale,...)"
                              [2] IContainer '' Visible="Client.LocaleId = Entities.Locale2.English"
                                [1] IExpression '' Value="If(Length(Description)>14,...)"
                            [3] IContainer '' Width="35%"
                              [1] IContainer '' Style='"white-space-nowrap"' CustomStyle="text-align: right;"
                                [1] IExpression '' Value="If(IsIncrease,"+","-")" Style='"font-semi-bold text-"+Color'
                                [2] IExpression '' Value="Client.Currency" Example="$"
                                [3] IExpression '' Value="FormatCurrency(Amount,...)"
                              [2] IContainer '' CustomStyle="text-align: right;"
                                [1] IExpression '' Value="FormatDateTime(CreatedOn, "d MMM")"
        [Column2 placeholder]
          [1] IContainer '' Style='"full-height"'
            [1] IContainer '' Style="...display-flex flex-direction-column full-height"
              [1] IContainer '' Style='"margin-bottom-xs"'
                [1] IMobileBlockInstanceWidget 'Columns2Instance' (Columns2)
                  [Column1 placeholder]
                    [1] IContainer '' Style='"font-size-base font-semi-bold"'
                      [1] ITextWidget '' Text="Balance"
                  [Column2 placeholder]
                    [1] IContainer '' CustomStyle="padding: 5px 0px 0px 0px; text-align: right;"
                      [1] IContainer '' Style='"chart-option"' Width="125px"
                        [1] IDropdown 'PeroidFilterDdl' Variable="SelectedChartDataOptionId" List="ChartOptionList"
                          OnChange → PeroidFilterDdlOnChange
              [2] IContainer 'ChartCntr' Style='"margin-top-base flex-grow-1"'
                [1] IContainer '' CustomStyle="height: 256px;"
                  [1] IIfWidget '' Cond="HideChart or not GetChartSampleData.IsDataFetched"
                    [FalseBranch]
                      [1] IMobileBlockInstanceWidget 'ColumnChartInstance' (ColumnChart)
                        DataPointList=GetChartSampleData.ChartDataPoints
                        Initialized → ColumnChartInitialized(ChartWidgetId)
                        [AddOns_Placeholder]
                          [1] IMobileBlockInstanceWidget 'ChartXAxisInstance' (ChartXAxis)
                          [2] IMobileBlockInstanceWidget 'ChartYAxisInstance' (ChartYAxis)
                          [3] IMobileBlockInstanceWidget 'ChartSeriesStylingInstance' (ChartSeriesStyling)
              [3] IContainer '' Style='"margin-top-m"'
                [1] IMobileBlockInstanceWidget 'GalleryInstance' (Gallery) RowItemsDesktop=3, Phone=2, Tablet=3
                  [Content placeholder]
                    [1] IMobileBlockInstanceWidget 'ItemCardInstance' (ItemCard) Color="primary" Label=ChartCardsValue.BalanceLabel
                      [Icon placeholder]
                        [1] IMobileBlockInstanceWidget 'HBIconInstance10' (HBIcon)
                          [IconName placeholder]
                            [1] ITextWidget '' Text="banknote"
                      [Percentage placeholder]
                        [1] IExpression '' Value="If(BalancePercent>0,"+",...)+BalancePercent+"%""
                      [Range placeholder]
                        [1] IExpression '' Value="ChartCardsValue.Label"
                    [2] IMobileBlockInstanceWidget 'ItemCardInstance2' (ItemCard) Color="green" Label="Income"
                      [Icon placeholder]
                        [1] IMobileBlockInstanceWidget 'HBIconInstance11' (HBIcon)
                          [IconName placeholder]
                            [1] ITextWidget '' Text="deposit" Style='"text-green"'
                      [Percentage placeholder]
                        [1] IExpression '' Value="If(IncomePercent>0,...)..."
                      [Range placeholder]
                        [1] IExpression '' Value="ChartCardsValue.Label"
                    [3] IMobileBlockInstanceWidget 'ItemCardInstance3' (ItemCard) Color="red" Label="Expenses"
                      [Icon placeholder]
                        [1] IMobileBlockInstanceWidget 'HBIconInstance12' (HBIcon)
                          [IconName placeholder]
                            [1] ITextWidget '' Text="withdrawal" Style='"text-red"'
                      [Percentage placeholder]
                        [1] IExpression '' Value="If(ExpensesPercent>0,...)..."
                      [Range placeholder]
                        [1] IExpression '' Value="ChartCardsValue.Label"
    [4] IMobileBlockInstanceWidget 'ChatInstance' (Chat)
      UserName=Client.UserName
      IsWaitingForResponse=IsWaitingForResponse
      ChatMessages=ChatMessages
      OnSendMessage → ChatOnSendMessage(Message)
      OnFirstToggle → ChatOnFirstToggle
  [SideContent placeholder]
    [1] IContainer '' Style='"margin-top-s"'
      [1] IContainer '' Style='"font-semi-bold font-size-base"'
        [1] ITextWidget '' Text="For you"
      [2] IContainer 'PersonalLoan'
        [1] IContainer '' Style='"colored-card lightDark position-relative display-flex"'
          [1] IContainer '' Style='"wallet-img-card"'
            [1] IImage '' Image=Wallet Style='"wallet-img"'
          [2] IContainer '' Style='"align-right-content"'
            [1] IContainer '' Style='"font-size-base font-semi-bold"'
              [1] ITextWidget '' Text="Personal Loan"
            [2] IContainer '' Style='"font-size-xs margin-top-s"'
              [1] ITextWidget '' Text="Customized solutions for your financial journey"
          onclick → NewLoanOnClick
      [3] IContainer 'DefineNewGoal' Style='"tablePotraitPaddingLeft"'
        [1] IContainer '' Style='"colored-card position-relative"'
          [1] IContainer ''
            [1] IContainer '' Style='"font-size-base font-semi-bold"'
              [1] ITextWidget '' Text="Define New Goal"
            [2] IContainer '' Style='"font-size-xs margin-top-s"'
              [1] ITextWidget '' Text="Put some money aside for something incredible"
          [2] IContainer ''
            [1] IImage '' Image=Pig Style='"pig-img"'
          onclick → NotImplemented
      [4] IContainer 'RetirementPlan'
        [1] IContainer '' Style='"colored-card position-relative"'
          [1] IContainer '' Width="70%"
            [1] IContainer '' Style='"font-size-base font-semi-bold"'
              [1] ITextWidget '' Text="Retirement Plan"
            [2] IContainer '' Style='"font-size-xs margin-top-s"'
              [1] ITextWidget '' Text="Apply automatically and set aside money every month."
          [2] IContainer ''
            [1] IImage '' Image=Illustratiion Style='"umbrella-img"'
          onclick → NotImplemented
    [2] IContainer ''
      [1] IContainer 'YourGoals'
        [1] IContainer '' Style='"margin-top-xxl cards-carousel"' Visible="GetCustomerGoals.Count > 0"
          [1] IContainer '' Style='"font-semi-bold font-size-base"'
            [1] ITextWidget '' Text="Your Goals"
            [2] IExpression '' Value='"(" + GetCustomerGoals.Count + ")"'
          [2] IMobileBlockInstanceWidget 'CarouselInstance' (Carousel)
            [CarouselItems placeholder]
              [1] IList '' Source="GetCustomerGoals.List"
                [1] IContainer '' Style='"colored-card orange"'
                  [1] IContainer ''
                    [1] IMobileBlockInstanceWidget 'AlignCenterInstance4' (AlignCenter)
                      [Content placeholder]
                        [1] IContainer '' Width="8 col"
                          [1] IContainer '' Style='"font-semi-bold"'
                            [1] IExpression '' Value="GetCustomerGoals.List.Current.GoalName"
                        [2] IContainer '' Width="4 col" CustomStyle="text-align: right;"
                          [1] IButton '' Style='"btn btn-transparent-with-border"'
                            [1] ITextWidget '' Text="Add"
                            [2] IMobileBlockInstanceWidget 'HBIconInstance13' (HBIcon)
                              [IconName placeholder]
                                [1] ITextWidget '' Text="deposit"
                            OnClick → NotImplemented
                    [2] IIfWidget '' Cond="Client.LocaleId = Entities.Locale2.Arabic"
                      [TrueBranch]
                        [1] IContainer '' Style='"margin-top-s"'
                          [1] ITextWidget '' Text=" من"
                          [2] IExpression '' Value="FormatCurrencyCustom(TargetAmount)"
                          [3] ITextWidget '' Text=" دولار "
                          [4] IExpression '' Value="FormatCurrencyCustom(AmountSum)" Style='"font-semi-bold"'
                      [FalseBranch]
                        [1] IContainer '' Style='"margin-top-s"'
                          [1] IExpression '' Value="FormatCurrencyCustom(AmountSum)" Style='"font-semi-bold"'
                          [2] ITextWidget '' Text=" of "
                          [3] IExpression '' Value="FormatCurrencyCustom(TargetAmount)"
                  [2] IContainer '' Style='"margin-top-base"'
                    [1] IMobileBlockInstanceWidget 'ProgressBarInstance' (ProgressBar)
                      Progress=AmountSum/TargetAmount*100
                      ProgressColor="#FFF" TrailColor="#ffffff45" Thickness=8
      [2] IContainer 'YourLoans'
        [1] IContainer '' Style='"margin-top-xxl margin-bottom-s cards-carousel"' Visible="GetCustomerLoans.Count > 0"
          [1] IContainer '' Style='"font-semi-bold font-size-base"'
            [1] ITextWidget '' Text="Loans"
            [2] IExpression '' Value='"(" + GetCustomerLoans.List.Length + ")"'
          [2] IMobileBlockInstanceWidget 'CarouselInstance2' (Carousel)
            [CarouselItems placeholder]
              [1] IList '' Source="GetCustomerLoans.List"
                [1] IContainer '' Style='"colored-card yellow slide-mini"'
                  [1] IContainer ''
                    [1] IMobileBlockInstanceWidget 'AlignCenterInstance5' (AlignCenter)
                      [Content placeholder]
                        [1] IContainer '' Width="8 col"
                          [1] IContainer '' Style='"font-semi-bold"'
                            [1] IExpression '' Value="GetLabelByLocale(LabelLocale, Client.LocaleId)"
                        [2] IContainer '' Width="4 col" CustomStyle="text-align: right;"
                          [1] IButton '' Style='"btn btn-transparent-with-border"'
                            [1] ITextWidget '' Text="View"
                            [2] IMobileBlockInstanceWidget 'HBIconInstance14' (HBIcon)
                              [IconName placeholder]
                                [1] ITextWidget '' Text="note"
                            OnClick → RedirectToLoan
                    [2] IIfWidget '' Cond="Client.LocaleId = Entities.Locale2.Arabic"
                      [TrueBranch]
                        [1] IContainer '' Style='"margin-top-s"'
                          [1] ITextWidget '' Text=" من"
                          [2] IExpression '' Value="FormatCurrencyCustom(Amount)"
                          [3] ITextWidget '' Text=" دولار "
                          [4] IExpression '' Value="FormatCurrencyCustom(AmountSum)" Style='"font-semi-bold"'
                      [FalseBranch]
                        [1] IContainer '' Style='"margin-top-s"'
                          [1] IExpression '' Value="FormatCurrencyCustom(AmountSum)" Style='"font-semi-bold"'
                          [2] ITextWidget '' Text=" of "
                          [3] IExpression '' Value="FormatCurrencyCustom(Amount)"
                  [2] IContainer '' Style='"margin-top-base"'
                    [1] IMobileBlockInstanceWidget 'ProgressBarInstance2' (ProgressBar)
                      Progress=AmountSum/Amount*100
                      ProgressColor="#FFF" TrailColor="#ffffff45" Thickness=8
      [3] IMobileBlockInstanceWidget 'ConsolidatedPositionSidebare' (Sidebar) ExtendedClass="consolidated-position"
        [Header placeholder]
          [1] IContainer '' Style='"margin-top-base"'
            [1] IContainer '' Width="10 col"
              [1] ITextWidget '' Text="Consolidated Position" Style='"heading5"'
            [2] IContainer '' Width="2 col" CustomStyle="text-align: right;"
              [1] ILink '' → ConsolidatedPositionSidebarClose
                [1] IMobileBlockInstanceWidget 'HBIconInstance15' (HBIcon)
                  [IconName placeholder]
                    [1] ITextWidget '' Text="close"
        [Content placeholder]
          [1] IContainer ''
            [1] IContainer ''
              [1] IMobileBlockInstanceWidget 'AlignCenterInstance6' (AlignCenter)
                [Content placeholder]
                  [1] ITextWidget '' Text="My Assets" Style='"font-size-base margin-right-base"'
                  [2] IMobileBlockInstanceWidget 'TagInstance' (Tag) Color=Entities.Color.Neutral2
                    [Tag placeholder]
                      [1] ITextWidget '' Text="+23%" Style='"text-green margin-right-xs"'
                      [2] IExpression '' Value="FormatDateTime(AddMonths(...),"MMM")+"-"+..."
            [2] IContainer '' Style='"margin-top-12"'
              [1] IMobileBlockInstanceWidget 'ProgressBarInstance3' (ProgressBar)
                Progress=If(TotalAssets>TotalDept,100,TotalAssets/TotalDept)*100
                ProgressColor=Entities.Color.Green TrailColor=Entities.Color.Transparent
            [3] IContainer '' Style='"margin-top-12"'
              [1] IExpression '' Value="FormatCurrencyCustom(TotalAssets)" Style='"font-size-base font-semi-bold"'
          [2] IContainer '' Style='"margin-top-l"'
            [1] IContainer ''
              [1] ITextWidget '' Text="My Debt" Style='"font-size-base"'
            [2] IContainer '' Style='"margin-top-12"'
              [1] IMobileBlockInstanceWidget 'ProgressBarInstance4' (ProgressBar)
                Progress=If(TotalDept>TotalAssets,100,TotalDept/TotalAssets)*100
                ProgressColor=Entities.Color.Red TrailColor=Entities.Color.Transparent
            [3] IContainer '' Style='"margin-top-12"'
              [1] IExpression '' Value="FormatCurrencyCustom(TotalDept)" Style='"font-size-base font-semi-bold"'
          [3] IContainer '' Style='"margin-top-l"'
            [1] IButtonGroup 'ButtonGroup2' Variable="IsDeptConsolidatedPositionOption"
              [1] IButtonGroupItem 'ButtonGroupItem3' Value=False
                [1] ITextWidget '' Text="My Assets"
              [2] IButtonGroupItem 'ButtonGroupItem4' Value=True
                [1] ITextWidget '' Text="My Debt"
          [4] IContainer 'Assets2' Visible="not IsDeptConsolidatedPositionOption"
            [1] IContainer '' Style='"margin-top-l position-relative"'
              [1] IMobileBlockInstanceWidget 'PieChartInstance' (PieChart) Height="245px"
                DataPointList=GetAssets.List mapTo { Value: AccountBalance, Label, Color, Tooltip }
                Initialized → DonutChartInitialized(ChartWidgetId)
                [AddOns_Placeholder]
                  [1] IMobileBlockInstanceWidget 'ChartSeriesStylingInstance2' (ChartSeriesStyling)
              [2] IContainer '' Style='"total-in-chart"'
                [1] IContainer ''
                  [1] IExpression '' Value="Client.Currency" Example="$"
                  [2] IExpression '' Value="FormatCurrency(TotalAssets,...)"
            [2] IContainer '' Style='"margin-top-s"'
              [1] IMobileBlockInstanceWidget 'AccordionInstance' (Accordion)
                [Content placeholder]
                  [1] IList '' Source="GetAssets.List"
                    [1] IContainer '' Style='"margin-top-12"'
                      [1] IMobileBlockInstanceWidget 'AccountAccordianInstance' (AccountAccordian)
                        AccountTypeId=GetAssets.List.Current.ProductTypeId
                        AccountBalance=GetAssets.List.Current.AccountBalance
                        Color=GetAssets.List.Current.Color
                        Label=GetLabelByLocale(LabelLocale, Client.LocaleId)
          [5] IContainer 'Depts2' Visible=" IsDeptConsolidatedPositionOption"
            [1] IContainer '' Style='"margin-top-l position-relative"'
              [1] IMobileBlockInstanceWidget 'PieChartInstance2' (PieChart) Height="245px"
                DataPointList=DeptList mapTo { Value: Balance, Label, Color, Tooltip }
                Initialized → DonutChartInitialized(ChartWidgetId)
                [AddOns_Placeholder]
                  [1] IMobileBlockInstanceWidget 'ChartSeriesStylingInstance3' (ChartSeriesStyling)
              [2] IContainer '' Style='"total-in-chart"'
                [1] IContainer ''
                  [1] IExpression '' Value="Client.Currency" Example="$"
                  [2] IExpression '' Value="FormatCurrency(TotalDept,...)"
            [2] IContainer '' Style='"margin-top-s"'
              [1] IMobileBlockInstanceWidget 'AccordionInstance2' (Accordion)
                [Content placeholder]
                  [1] IList '' Source="DeptList"
                    [1] IContainer '' Style='"margin-top-12"'
                      [1] IIfWidget '' Cond="DeptList.Current.IsLoan"
                        [TrueBranch]
                          [1] IMobileBlockInstanceWidget 'LoanAccordianInstance' (LoanAccordian)
                            Color=DeptList.Current.Color
                            Label=DeptList.Current.Label
                            TotalLoan=DeptList.Current.Balance
                        [FalseBranch]
                          [1] IMobileBlockInstanceWidget 'AccountAccordianInstance2' (AccountAccordian)
                            Color=DeptList.Current.Color
                            AccountTypeId=Entities.ProductType.CreditCard
                            Label=DeptList.Current.Label+"s"
                            AccountBalance=DeptList.Current.Balance
```
