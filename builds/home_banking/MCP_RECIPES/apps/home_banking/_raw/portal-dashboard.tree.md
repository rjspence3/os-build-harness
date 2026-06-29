=== Screen: Dashboard ===
Inputs: (none)
Locals: SelectedAccountId:HBAccount Identifier, SelectedChartDataOptionId:Text, Accounts:List, ChartHeight:Integer, TotalBalance:Currency, TotalAssets:Currency, TotalDept:Currency, IsDeptConsolidatedPositionOption:Boolean, HideChart:Boolean, DeptList:List, ChartCardsValue:Record, IsPortrait:Boolean, ChatMessages:ChatMessage List, IsWaitingForResponse:Boolean, ChartOptionList:DropdownItem List
Aggregates: GetAccounts (source=HBAccount), GetAssets (source=HBAccount), GetChartDataOptions (source=ChartDataOption), GetCreditCardsDept (source=HBAccount), GetCustomerGoals (source=CustomerGoal), GetCustomerLoans (source=CustomerLoan), GetLastTransactions (source=Transaction)
--- WIDGETS (hierarchical) ---
[1] BlockInstance (unnamed) SourceBlock="LayoutTopMenuRightSide" ExtendedClass=null EnableAccessibilityFeatures=null HasFixedHeader=null
  [1.1] BlockInstance (unnamed) PlaceholderName="Header" SourceBlock="Menu" ActiveSubItem=null ActiveItem=null
  [1.2] Container (unnamed) PlaceholderName="Title"
    [1.2.1] Container (unnamed)
      [1.2.1.1] Text (unnamed) Text="Total Balance"
    [1.2.2] Container (unnamed) Style="If(IsDesktop(), \"display-flex justify-content-space-between\", \"display-grid gap-s\")"
      [1.2.2.1] Container (unnamed) Width=""
        [1.2.2.1.1] If (unnamed) Condition="Client.HideBalance"
          [1.2.2.1.1.T.1] Container (unnamed) PlaceholderName="TrueBranch" Style="\"balance-cntr\""
            [1.2.2.1.1.T.1.1] Icon (unnamed) Icon="circle" CustomStyle="font-size: 8px;" Style="\"icon\""
            [1.2.2.1.1.T.1.2] Icon (unnamed) Icon="circle" CustomStyle="font-size: 8px;" Style="\"icon\""
            [1.2.2.1.1.T.1.3] Icon (unnamed) Icon="circle" CustomStyle="font-size: 8px;" Style="\"icon\""
            [1.2.2.1.1.T.1.4] Icon (unnamed) Icon="circle" CustomStyle="font-size: 8px;" Style="\"icon\""
          [1.2.2.1.1.F.1] Container (unnamed) PlaceholderName="FalseBranch" Style="\"balance-cntr\""
            [1.2.2.1.1.F.1.1] BlockInstance (unnamed) SourceBlock="AlignCenter" IsHorizontal=null ExtendedClass=null
              [1.2.2.1.1.F.1.1.1] Container (unnamed) PlaceholderName="Content"
                [1.2.2.1.1.F.1.1.1.1] Expression (unnamed) Value="Client.Currency" Style="\"font-size-h5  margin-top-xs\""
              [1.2.2.1.1.F.1.1.2] Container (unnamed) PlaceholderName="Content"
                [1.2.2.1.1.F.1.1.2.1] Expression (unnamed) Value="FormatCurrency(TotalBalance,\"\",2,Client.DecimalSeparator,Client.GroupSeparator)" Style="\"font-size-h1 white-space-nowrap\"" Width="auto"
      [1.2.2.2] Container (unnamed) Style="If(IsDesktop(), \"vertical-align gap-s\", \"display-grid gap-s\")" Width="(fill parent)"
        [1.2.2.2.1] Container (unnamed) Width="" CustomStyle="text-align: center;"
          [1.2.2.2.1.1] Button (unnamed) Style="\"btn btn-no-border padding-x-none margin-top-xs\"" Width="(fill parent)" OnClick→Destination="ToggleHideBallanceOnClick"
            [1.2.2.2.1.1.1] If (unnamed) Condition="Client.HideBalance"
              [1.2.2.2.1.1.1.T.1] Container (unnamed) PlaceholderName="TrueBranch" Width=""
                [1.2.2.2.1.1.1.T.1.1] BlockInstance (unnamed) SourceBlock="AlignCenter" ExtendedClass=null IsHorizontal=null
                  [1.2.2.2.1.1.1.T.1.1.1] Text (unnamed) PlaceholderName="Content" Text="Show Balance"
                  [1.2.2.2.1.1.1.T.1.1.2] BlockInstance (unnamed) PlaceholderName="Content" SourceBlock="HBIcon" Classes=null
                    [1.2.2.2.1.1.1.T.1.1.2.1] Text (unnamed) PlaceholderName="IconName" Style="\"margin-left-s\"" Text="eyeshow"
              [1.2.2.2.1.1.1.F.1] Container (unnamed) PlaceholderName="FalseBranch" Width=""
                [1.2.2.2.1.1.1.F.1.1] BlockInstance (unnamed) SourceBlock="AlignCenter" IsHorizontal=null ExtendedClass=null
                  [1.2.2.2.1.1.1.F.1.1.1] Text (unnamed) PlaceholderName="Content" Text="Hide Balance"
                  [1.2.2.2.1.1.1.F.1.1.2] BlockInstance (unnamed) PlaceholderName="Content" SourceBlock="HBIcon" Classes=null
                    [1.2.2.2.1.1.1.F.1.1.2.1] Text (unnamed) PlaceholderName="IconName" Style="\"margin-left-s\"" Text="eyehide"
        [1.2.2.2.2] Container (unnamed) Width="(fill parent)"
          [1.2.2.2.2.1] Button (unnamed) Style="\"btn margin-top-xs\"" Width="(fill parent)" OnClick→Destination="NotImplemented"
            [1.2.2.2.2.1.1] Text (unnamed) Text="Account Insights"
            [1.2.2.2.2.1.2] BlockInstance (unnamed) SourceBlock="HBIcon" Classes=null
              [1.2.2.2.2.1.2.1] Text (unnamed) PlaceholderName="IconName" Style="\"margin-left-s\"" Text="insights"
        [1.2.2.2.3] Container (unnamed) Width="(fill parent)"
          [1.2.2.2.3.1] Button (unnamed) Style="\"btn  btn-primary margin-top-xs\"" Width="(fill parent)" OnClick→Destination="ConsolidatedPositionSidebarOpen"
            [1.2.2.2.3.1.1] Text (unnamed) Text="Consolidated Position"
            [1.2.2.2.3.1.2] BlockInstance (unnamed) SourceBlock="HBIcon" Classes=null
              [1.2.2.2.3.1.2.1] Text (unnamed) PlaceholderName="IconName" Style="\"margin-left-s\"" Text="columnchart"
  [1.3] Container (unnamed) PlaceholderName="MainContent"
    [1.3.1] Container 'Carouselcntr' Style="\"margin-top-l card-carousel-container\""
      [1.3.1.1] If (unnamed) Condition="not Accounts.Empty and GetAccounts.IsDataFetched"
        [1.3.1.1.T.1] BlockInstance (unnamed) PlaceholderName="TrueBranch" SourceBlock="StackedCarousel" FadeOutEasing=null FadeOutDuration=null ScaleDown=null Gap="If(IsPhone(),0.8,0.05)" FadeInDuration=null IsVertical=null MoveOnClick=null SlidesPerPage="If(IsPhone(),2,3)" FadeInEasing=null
          [1.3.1.1.T.1.1] List (unnamed) PlaceholderName="Content" Source="Accounts" Style="\"list list-group dashboard-card-list\""
            [1.3.1.1.T.1.1.1] Container 'ListItemClickable' Width="fill"
              [1.3.1.1.T.1.1.1.1] BlockInstance (unnamed) SourceBlock="AccountCard" isTransfer=null Balance="Accounts.Current.AccountBalance" AccountNumber4Digit="Substr(Accounts.Current.AccountNumber,\nLength(Accounts.Current.AccountNumber)-4,\n4)" AccountName="Accounts.Current.Name" IsActive="Accounts.Current.Id = SelectedAccountId" AccountTypeId="Accounts.Current.TypeId" PaddingTop="If(Accounts.Current.Id=SelectedAccountId,54, 54 - (Accounts.Current.Order*8))"
    [1.3.2] Container (unnamed) Style="\"margin-top-xl\""
      [1.3.2.1] Container (unnamed) Style="If(IsDesktop(), \"display-flex\", \"display-grid\") + \" gap-base\"" Width=""
        [1.3.2.1.1] Container (unnamed) Width="(fill parent)"
          [1.3.2.1.1.1] Button (unnamed) Style="\"btn btn-primary \" + If(IsPhone() or IsTablet(), \"\", \"width-fit-content\")" Width="(fill parent)" OnClick→Destination="Transfer" OnClick.AccountId="SelectedAccountId"
            [1.3.2.1.1.1.1] Text (unnamed) Text="Transfer"
            [1.3.2.1.1.1.2] BlockInstance (unnamed) SourceBlock="HBIcon" Classes=null
              [1.3.2.1.1.1.2.1] Text (unnamed) PlaceholderName="IconName" Style="\"margin-left-s\"" Text="transfer"
        [1.3.2.1.2] Container (unnamed) Width="(fill parent)"
          [1.3.2.1.2.1] Button (unnamed) Style="\"btn btn-primary \" + If(IsPhone() or IsTablet(), \"\", \"width-fit-content\")" Width="(fill parent)" OnClick→Destination="NotImplemented"
            [1.3.2.1.2.1.1] Text (unnamed) Text="Pay"
            [1.3.2.1.2.1.2] BlockInstance (unnamed) SourceBlock="HBIcon" Classes=null
              [1.3.2.1.2.1.2.1] Text (unnamed) PlaceholderName="IconName" Style="\"margin-left-s\"" Text="scan"
        [1.3.2.1.3] Container (unnamed) Width="(fill parent)"
          [1.3.2.1.3.1] Button (unnamed) Style="\"btn \" + If(IsPhone()  or IsTablet(), \"\", \"width-fit-content\")" Width="(fill parent)" OnClick→Destination="NotImplemented"
            [1.3.2.1.3.1.1] Text (unnamed) Text="Add"
            [1.3.2.1.3.1.2] BlockInstance (unnamed) SourceBlock="HBIcon" Classes=null
              [1.3.2.1.3.1.2.1] Text (unnamed) PlaceholderName="IconName" Style="\"margin-left-s\"" Text="plussquare"
    [1.3.3] Container (unnamed) Style="\"margin-top-xxl\""
      [1.3.3.1] BlockInstance (unnamed) SourceBlock="ColumnsMediumLeft" GutterSize=null TabletBehavior=null ExtendedClass=null PhoneBehavior="Entities.BreakColumns.All"
        [1.3.3.1.1] Container (unnamed) PlaceholderName="Column1"
          [1.3.3.1.1.1] Container (unnamed)
            [1.3.3.1.1.1.1] BlockInstance (unnamed) SourceBlock="ColumnsMediumRight" ExtendedClass=null TabletBehavior=null GutterSize=null PhoneBehavior=null
              [1.3.3.1.1.1.1.1] Container (unnamed) PlaceholderName="Column1" Style="\"font-size-base font-semi-bold\""
                [1.3.3.1.1.1.1.1.1] Text (unnamed) Text="Last Transactions"
              [1.3.3.1.1.1.1.2] Container (unnamed) PlaceholderName="Column2" CustomStyle="padding: 2px 0px 0px 0px; text-align: right;"
                [1.3.3.1.1.1.1.2.1] Link (unnamed) OnClick→Destination="NotImplemented"
                  [1.3.3.1.1.1.1.2.1.1] Text (unnamed) Text="View All"
          [1.3.3.1.1.2] Container (unnamed) Style="\"margin-top-xs\""
            [1.3.3.1.1.2.1] Container 'IsTableLoadingOrEmpty'
              [1.3.3.1.1.2.1.1] If 'IsEmpty' Condition="GetLastTransactions.IsDataFetched and GetLastTransactions.List.Empty"
                [1.3.3.1.1.2.1.1.T.1] Container (unnamed) PlaceholderName="TrueBranch" Style="\"table-empty margin-top-l\""
                  [1.3.3.1.1.2.1.1.T.1.1] BlockInstance (unnamed) SourceBlock="BlankSlate" ExtendedClass=null FullHeight=null
                    [1.3.3.1.1.2.1.1.T.1.1.1] BlockInstance (unnamed) PlaceholderName="Icon" SourceBlock="HBIcon" Classes=null
                      [1.3.3.1.1.2.1.1.T.1.1.1.1] Text (unnamed) PlaceholderName="IconName" Style="\"margin-left-s\"" Text="transfer"
                    [1.3.3.1.1.2.1.1.T.1.1.2] Text (unnamed) PlaceholderName="Content" Text="There aren't any transctions."
                [1.3.3.1.1.2.1.1.F.1] If 'IsLoading' PlaceholderName="FalseBranch" Condition="not GetLastTransactions.IsDataFetched"
                  [1.3.3.1.1.2.1.1.F.1.T.1] Container (unnamed) PlaceholderName="TrueBranch" Style="\"list-updating\""
                  [1.3.3.1.1.2.1.1.F.1.F.1] List (unnamed) PlaceholderName="FalseBranch" Source="GetLastTransactions.List" Style="\"list list-group\""
                    [1.3.3.1.1.2.1.1.F.1.F.1.1] Container (unnamed) Style="\"item-card horizontal listItem\""
                      [1.3.3.1.1.2.1.1.F.1.F.1.1.1] Container (unnamed) Width="15%" Style="\"text-neutral-8\""
                        [1.3.3.1.1.2.1.1.F.1.F.1.1.1.1] BlockInstance (unnamed) SourceBlock="HBIcon" Classes=null
                          [1.3.3.1.1.2.1.1.F.1.F.1.1.1.1.1] Expression (unnamed) PlaceholderName="IconName" Value="GetLastTransactions.List.Current.TransactionType.IconNameEN"
                      [1.3.3.1.1.2.1.1.F.1.F.1.1.2] Container (unnamed) Width="50%"
                        [1.3.3.1.1.2.1.1.F.1.F.1.1.2.1] Container (unnamed)
                          [1.3.3.1.1.2.1.1.F.1.F.1.1.2.1.1] Expression (unnamed) Value="GetLabelByLocale(GetLastTransactions.List.Current.TransactionType.LabelLocale,Client.LocaleId)"
                        [1.3.3.1.1.2.1.1.F.1.F.1.1.2.2] Container (unnamed) Visible="Client.LocaleId = Entities.Locale2.English"
                          [1.3.3.1.1.2.1.1.F.1.F.1.1.2.2.1] Expression (unnamed) Style="\"font-size-xs text-neutral-7\"" Value="If(Length(GetLastTransactions.List.Current.Transaction.Description)>14,Substr(GetLastTransactions.List.Current.Transaction.Description,0,14)+\" ...\", GetLastTransactions.List.Current.Transaction.Description)"
                      [1.3.3.1.1.2.1.1.F.1.F.1.1.3] Container (unnamed) Width="35%"
                        [1.3.3.1.1.2.1.1.F.1.F.1.1.3.1] Container (unnamed) Style="\"white-space-nowrap\"" CustomStyle="text-align: right;"
                          [1.3.3.1.1.2.1.1.F.1.F.1.1.3.1.1] Expression (unnamed) Style="\"font-semi-bold text-\"+GetLastTransactions.List.Current.TransactionType.Color" Value="If(GetLastTransactions.List.Current.TransactionType.IsIncrease,\"+\",\"-\")" Width="auto"
                          [1.3.3.1.1.2.1.1.F.1.F.1.1.3.1.2] Expression (unnamed) Style="\"font-semi-bold text-\"+GetLastTransactions.List.Current.TransactionType.Color" Value="Client.Currency"
                          [1.3.3.1.1.2.1.1.F.1.F.1.1.3.1.3] Expression (unnamed) Style="\"font-semi-bold text-\"+GetLastTransactions.List.Current.TransactionType.Color" Value="FormatCurrency(GetLastTransactions.List.Current.Transaction.Amount,\"\",2,Client.DecimalSeparator,Client.GroupSeparator)"
                        [1.3.3.1.1.2.1.1.F.1.F.1.1.3.2] Container (unnamed) CustomStyle="text-align: right;"
                          [1.3.3.1.1.2.1.1.F.1.F.1.1.3.2.1] Expression (unnamed) Style="\"font-size-xs text-neutral-7\"" Value="FormatDateTime(GetLastTransactions.List.Current.Transaction.CreatedOn, \"d MMM\")" Width="(fill parent)"
        [1.3.3.1.2] Container (unnamed) PlaceholderName="Column2" Style="\"full-height\""
          [1.3.3.1.2.1] Container (unnamed) Style="If(IsPhone(), \"\", \"margin-left-s\") + \" display-flex flex-direction-column full-height\""
            [1.3.3.1.2.1.1] Container (unnamed) Style="\"margin-bottom-xs\""
              [1.3.3.1.2.1.1.1] BlockInstance (unnamed) SourceBlock="Columns2" GutterSize=null TabletBehavior=null PhoneBehavior=null ExtendedClass=null
                [1.3.3.1.2.1.1.1.1] Container (unnamed) PlaceholderName="Column1" Style="\"font-size-base font-semi-bold\""
                  [1.3.3.1.2.1.1.1.1.1] Text (unnamed) Text="Balance"
                [1.3.3.1.2.1.1.1.2] Container (unnamed) PlaceholderName="Column2" CustomStyle="padding: 5px 0px 0px 0px; text-align: right;"
                  [1.3.3.1.2.1.1.1.2.1] Container (unnamed) Style="\"chart-option\"" Width="125px" CustomStyle="text-align: right;"
                    [1.3.3.1.2.1.1.1.2.1.1] Dropdown 'PeroidFilterDdl' Variable="SelectedChartDataOptionId" Style="\"dropdown \"" List="ChartOptionList" Labels="Text" Values="Value" OnChange→Destination="PeroidFilterDdlOnChange"
            [1.3.3.1.2.1.2] Container 'ChartCntr' Style="\"margin-top-base flex-grow-1\""
              [1.3.3.1.2.1.2.1] Container (unnamed) CustomStyle="height: 256px;"
                [1.3.3.1.2.1.2.1.1] If (unnamed) Condition="HideChart or not GetChartSampleData.IsDataFetched "
                  [1.3.3.1.2.1.2.1.1.F.1] BlockInstance (unnamed) PlaceholderName="FalseBranch" SourceBlock="ColumnChart" Height="If(ChartHeight>200,ChartHeight,200)+\"px\"" ExtendedClass=null OptionalConfigs=null StackingType=null DataPointList="GetChartSampleData.ChartDataPoints" ValuesType="If(SelectedChartDataOptionId = Entities.ChartDataOption.Monthly , Entities.ValuesType.Datetime, Entities.ValuesType.Text)"
                    [1.3.3.1.2.1.2.1.1.F.1.1] BlockInstance (unnamed) PlaceholderName="AddOns_Placeholder" SourceBlock="ChartXAxis" ExtendedClass=null GridLines="{ LinesColor: \"#B9BBC7\" }" Styling=null Label="{ LabelColor: If(Client.IsDarkMode,\"#ffffff\",\"#000000\"), LabelRotation: If(IsPhone(),-75,0) }" Visible=null MinValue=null MaxValue=null OptionalConfigs="{ ValuesType: If(SelectedChartDataOptionId = Entities.ChartDataOption.Monthly, Entities.AxisValuesType.Datetime, Entities.AxisValuesType.Category) }" Title=null
                    [1.3.3.1.2.1.2.1.1.F.1.2] BlockInstance (unnamed) PlaceholderName="AddOns_Placeholder" SourceBlock="ChartYAxis" ExtendedClass=null MinValue=null OptionalConfigs="{  }" Label="{ LabelColor: If(Client.IsDarkMode,\"#ffffff\",\"#000000\") }" Styling=null Title=null MaxValue=null Visible=null GridLines="{ LinesColor: If(Client.IsDarkMode,\"#565D88\",\"#B9BBC7\"), LinesWidth: 1 }"
                    [1.3.3.1.2.1.2.1.1.F.1.3] BlockInstance (unnamed) PlaceholderName="AddOns_Placeholder" SourceBlock="ChartSeriesStyling" ExtendedClass=null OptionalConfigs=null SeriesType=null SeriesName=null Marker=null Styling=null ShowDataPointValues=null
            [1.3.3.1.2.1.3] Container (unnamed) Style="\"margin-top-m\""
              [1.3.3.1.2.1.3.1] BlockInstance (unnamed) SourceBlock="Gallery" RowItemsDesktop="3" ItemsGap=null ExtendedClass=null RowItemsTablet="3" RowItemsPhone="2"
                [1.3.3.1.2.1.3.1.1] BlockInstance (unnamed) PlaceholderName="Content" SourceBlock="ItemCard" Color="\"primary\"" Label="ChartCardsValue.BalanceLabel" Balance="ChartCardsValue.Balance"
                  [1.3.3.1.2.1.3.1.1.1] BlockInstance (unnamed) PlaceholderName="Icon" SourceBlock="HBIcon" Classes=null
                    [1.3.3.1.2.1.3.1.1.1.1] Text (unnamed) PlaceholderName="IconName" Text="banknote"
                  [1.3.3.1.2.1.3.1.1.2] Expression (unnamed) PlaceholderName="Percentage" Value="If(ChartCardsValue.BalancePercent>0,\"+\",\"\")+ChartCardsValue.BalancePercent+\"%\""
                  [1.3.3.1.2.1.3.1.1.3] Expression (unnamed) PlaceholderName="Range" Value="ChartCardsValue.Label"
                [1.3.3.1.2.1.3.1.2] BlockInstance (unnamed) PlaceholderName="Content" SourceBlock="ItemCard" Color="\"green\"" Label="\"Income\"" Balance="ChartCardsValue.Income"
                  [1.3.3.1.2.1.3.1.2.1] BlockInstance (unnamed) PlaceholderName="Icon" SourceBlock="HBIcon" Classes=null
                    [1.3.3.1.2.1.3.1.2.1.1] Text (unnamed) PlaceholderName="IconName" Style="\"text-green\"" Text="deposit"
                  [1.3.3.1.2.1.3.1.2.2] Expression (unnamed) PlaceholderName="Percentage" Value="If(ChartCardsValue.IncomePercent>0,\"+\",\"\")+ChartCardsValue.IncomePercent+\"%\""
                  [1.3.3.1.2.1.3.1.2.3] Expression (unnamed) PlaceholderName="Range" Value="ChartCardsValue.Label"
                [1.3.3.1.2.1.3.1.3] BlockInstance (unnamed) PlaceholderName="Content" SourceBlock="ItemCard" Balance="ChartCardsValue.Expenses" Label="\"Expenses\"" Color="\"red\""
                  [1.3.3.1.2.1.3.1.3.1] BlockInstance (unnamed) PlaceholderName="Icon" SourceBlock="HBIcon" Classes=null
                    [1.3.3.1.2.1.3.1.3.1.1] Text (unnamed) PlaceholderName="IconName" Style="\"text-red\"" Text="withdrawal"
                  [1.3.3.1.2.1.3.1.3.2] Expression (unnamed) PlaceholderName="Percentage" Value="If(ChartCardsValue.ExpensesPercent>0,\"+\",\"\")+ChartCardsValue.ExpensesPercent+\"%\""
                  [1.3.3.1.2.1.3.1.3.3] Expression (unnamed) PlaceholderName="Range" Value="ChartCardsValue.Label"
    [1.3.4] BlockInstance (unnamed) SourceBlock="Chat" UserName="Client.UserName" AssistantName=null IsWaitingForResponse="IsWaitingForResponse" ChatMessages="ChatMessages" IsEnabled=null
  [1.5] Container (unnamed) PlaceholderName="SideContent"
    [1.5.1] Container (unnamed) Style="\"margin-top-s\""
      [1.5.1.1] Container (unnamed) Style="\"font-semi-bold font-size-base\""
        [1.5.1.1.1] Text (unnamed) Text="For you"
      [1.5.1.2] Container 'PersonalLoan'
        [1.5.1.2.1] Container (unnamed) Style="\"colored-card lightDark position-relative display-flex\""
          [1.5.1.2.1.1] Container (unnamed) Style="\"wallet-img-card\"" Width=""
            [1.5.1.2.1.1.1] Image (unnamed) Source="Wallet" Style="\"wallet-img\""
          [1.5.1.2.1.2] Container (unnamed) Style="\"align-right-content\"" Width=""
            [1.5.1.2.1.2.1] Container (unnamed) Style="\"font-size-base font-semi-bold\""
              [1.5.1.2.1.2.1.1] Text (unnamed) Text="Personal Loan"
            [1.5.1.2.1.2.2] Container (unnamed) Style="\"font-size-xs margin-top-s\""
              [1.5.1.2.1.2.2.1] Text (unnamed) Text="Customized solutions for your financial journey"
      [1.5.1.3] Container 'DefineNewGoal' Style="\"tablePotraitPaddingLeft\""
        [1.5.1.3.1] Container (unnamed) Style="\"colored-card position-relative\""
          [1.5.1.3.1.1] Container (unnamed) Width=""
            [1.5.1.3.1.1.1] Container (unnamed) Style="\"font-size-base font-semi-bold\""
              [1.5.1.3.1.1.1.1] Text (unnamed) Text="Define New Goal"
            [1.5.1.3.1.1.2] Container (unnamed) Style="\"font-size-xs margin-top-s\""
              [1.5.1.3.1.1.2.1] Text (unnamed) Text="Put some money aside for something incredible"
          [1.5.1.3.1.2] Container (unnamed) Width="auto"
            [1.5.1.3.1.2.1] Image (unnamed) Source="Pig" Style="\"pig-img\""
      [1.5.1.4] Container 'RetirementPlan'
        [1.5.1.4.1] Container (unnamed) Style="\"colored-card position-relative\""
          [1.5.1.4.1.1] Container (unnamed) Width="70%"
            [1.5.1.4.1.1.1] Container (unnamed) Style="\"font-size-base font-semi-bold\""
              [1.5.1.4.1.1.1.1] Text (unnamed) Text="Retirement Plan"
            [1.5.1.4.1.1.2] Container (unnamed) Style="\"font-size-xs margin-top-s\""
              [1.5.1.4.1.1.2.1] Text (unnamed) Text="Apply automatically and set aside money every month."
          [1.5.1.4.1.2] Container (unnamed) Width="auto"
            [1.5.1.4.1.2.1] Image (unnamed) Source="Illustratiion" Style="\"umbrella-img\""
    [1.5.2] Container (unnamed)
      [1.5.2.1] Container 'YourGoals'
        [1.5.2.1.1] Container (unnamed) Style="\"margin-top-xxl cards-carousel\"" Visible="GetCustomerGoals.Count > 0"
          [1.5.2.1.1.1] Container (unnamed) Style="\"font-semi-bold font-size-base\""
            [1.5.2.1.1.1.1] Text (unnamed) Text="Your Goals"
            [1.5.2.1.1.1.2] Expression (unnamed) Value="\"(\" + GetCustomerGoals.Count + \")\"" Width=""
          [1.5.2.1.1.2] BlockInstance (unnamed) SourceBlock="Carousel" OptionalConfigs="{ AutoPlay: False, Loop: False, ItemsGap: If(GetCustomerGoals.List.Length>1,\"5px\",\"0px\") }" Height=null Navigation="If(GetCustomerGoals.List.Length > 1, Entities.CarouselNavigation.Dots,Entities.CarouselNavigation.None)" ExtendedClass=null ItemsPerSlide=null
            [1.5.2.1.1.2.1] List (unnamed) PlaceholderName="CarouselItems" Source="GetCustomerGoals.List" Style="\"list list-group\""
              [1.5.2.1.1.2.1.1] Container (unnamed) Style="\"colored-card orange\"" CustomStyle="margin-top: var(--space-base);"
                [1.5.2.1.1.2.1.1.1] Container (unnamed)
                  [1.5.2.1.1.2.1.1.1.1] BlockInstance (unnamed) SourceBlock="AlignCenter" ExtendedClass=null IsHorizontal=null
                    [1.5.2.1.1.2.1.1.1.1.1] Container (unnamed) PlaceholderName="Content" Width="8 col"
                      [1.5.2.1.1.2.1.1.1.1.1.1] Container (unnamed) Style="\"font-semi-bold\""
                        [1.5.2.1.1.2.1.1.1.1.1.1.1] Expression (unnamed) Value="GetCustomerGoals.List.Current.GoalName"
                    [1.5.2.1.1.2.1.1.1.1.2] Container (unnamed) PlaceholderName="Content" Width="4 col" CustomStyle="text-align: right;"
                      [1.5.2.1.1.2.1.1.1.1.2.1] Button (unnamed) Style="\"btn btn-transparent-with-border\"" OnClick→Destination="NotImplemented"
                        [1.5.2.1.1.2.1.1.1.1.2.1.1] Text (unnamed) Text="Add"
                        [1.5.2.1.1.2.1.1.1.1.2.1.2] BlockInstance (unnamed) SourceBlock="HBIcon" Classes=null
                          [1.5.2.1.1.2.1.1.1.1.2.1.2.1] Text (unnamed) PlaceholderName="IconName" Style="\"margin-left-s  font-size-h6\"" Text="deposit"
                  [1.5.2.1.1.2.1.1.1.2] If (unnamed) Condition="Client.LocaleId = Entities.Locale2.Arabic"
                    [1.5.2.1.1.2.1.1.1.2.T.1] Container (unnamed) PlaceholderName="TrueBranch" Style="\"margin-top-s\""
                      [1.5.2.1.1.2.1.1.1.2.T.1.1] Text (unnamed) Text=" من"
                      [1.5.2.1.1.2.1.1.1.2.T.1.2] Expression (unnamed) Value="FormatCurrencyCustom(GetCustomerGoals.List.Current.TargetAmount)"
                      [1.5.2.1.1.2.1.1.1.2.T.1.3] Text (unnamed) Text=" دولار "
                      [1.5.2.1.1.2.1.1.1.2.T.1.4] Expression (unnamed) Value="FormatCurrencyCustom(GetCustomerGoals.List.Current.AmountSum)" Style="\"font-semi-bold\""
                    [1.5.2.1.1.2.1.1.1.2.F.1] Container (unnamed) PlaceholderName="FalseBranch" Style="\"margin-top-s\""
                      [1.5.2.1.1.2.1.1.1.2.F.1.1] Expression (unnamed) Value="FormatCurrencyCustom(GetCustomerGoals.List.Current.AmountSum)" Style="\"font-semi-bold\""
                      [1.5.2.1.1.2.1.1.1.2.F.1.2] Text (unnamed) Text=" of "
                      [1.5.2.1.1.2.1.1.1.2.F.1.3] Expression (unnamed) Value="FormatCurrencyCustom(GetCustomerGoals.List.Current.TargetAmount)"
                [1.5.2.1.1.2.1.1.2] Container (unnamed) Style="\"margin-top-base\""
                  [1.5.2.1.1.2.1.1.2.1] BlockInstance (unnamed) SourceBlock="ProgressBar" ProgressColor="TextToIdentifier(\"#FFF\")" OptionalConfigs=null TrailColor="TextToIdentifier(\"#ffffff45\")" ExtendedClass=null Progress="GetCustomerGoals.List.Current.AmountSum/GetCustomerGoals.List.Current.TargetAmount*100" Thickness="8"
      [1.5.2.2] Container 'YourLoans'
        [1.5.2.2.1] Container (unnamed) Style="\"margin-top-xxl margin-bottom-s cards-carousel\"" Visible="GetCustomerLoans.Count > 0"
          [1.5.2.2.1.1] Container (unnamed) Style="\"font-semi-bold font-size-base\""
            [1.5.2.2.1.1.1] Text (unnamed) Text="Loans"
            [1.5.2.2.1.1.2] Expression (unnamed) Value="\"(\" + GetCustomerLoans.List.Length + \")\"" Width=""
          [1.5.2.2.1.2] BlockInstance (unnamed) SourceBlock="Carousel" Navigation="If(GetCustomerLoans.List.Length > 1, Entities.CarouselNavigation.Dots,Entities.CarouselNavigation.None)" OptionalConfigs="{ AutoPlay: False, Loop: False, ItemsGap: \"5px\" }" Height=null ExtendedClass=null ItemsPerSlide=null
            [1.5.2.2.1.2.1] List (unnamed) PlaceholderName="CarouselItems" Source="GetCustomerLoans.List" Style="\"list list-group\""
              [1.5.2.2.1.2.1.1] Container (unnamed) Style="\"colored-card yellow slide-mini\"" CustomStyle="margin-top: var(--space-base);"
                [1.5.2.2.1.2.1.1.1] Container (unnamed)
                  [1.5.2.2.1.2.1.1.1.1] BlockInstance (unnamed) SourceBlock="AlignCenter" ExtendedClass=null IsHorizontal=null
                    [1.5.2.2.1.2.1.1.1.1.1] Container (unnamed) PlaceholderName="Content" Width="8 col"
                      [1.5.2.2.1.2.1.1.1.1.1.1] Container (unnamed) Style="\"font-semi-bold\""
                        [1.5.2.2.1.2.1.1.1.1.1.1.1] Expression (unnamed) Value="GetLabelByLocale(GetCustomerLoans.List.Current.LabelLocale, Client.LocaleId) "
                    [1.5.2.2.1.2.1.1.1.1.2] Container (unnamed) PlaceholderName="Content" Width="4 col" CustomStyle="text-align: right;"
                      [1.5.2.2.1.2.1.1.1.1.2.1] Button (unnamed) Style="\"btn btn-transparent-with-border\"" OnClick→Destination="RedirectToLoan"
                        [1.5.2.2.1.2.1.1.1.1.2.1.1] Text (unnamed) Text="View"
                        [1.5.2.2.1.2.1.1.1.1.2.1.2] BlockInstance (unnamed) SourceBlock="HBIcon" Classes=null
                          [1.5.2.2.1.2.1.1.1.1.2.1.2.1] Text (unnamed) PlaceholderName="IconName" Style="\"margin-left-s  font-size-h6\"" Text="note"
                  [1.5.2.2.1.2.1.1.1.2] If (unnamed) Condition="Client.LocaleId = Entities.Locale2.Arabic"
                    [1.5.2.2.1.2.1.1.1.2.T.1] Container (unnamed) PlaceholderName="TrueBranch" Style="\"margin-top-s\""
                      [1.5.2.2.1.2.1.1.1.2.T.1.1] Text (unnamed) Text=" من"
                      [1.5.2.2.1.2.1.1.1.2.T.1.2] Expression (unnamed) Value="FormatCurrencyCustom(GetCustomerLoans.List.Current.Amount)"
                      [1.5.2.2.1.2.1.1.1.2.T.1.3] Text (unnamed) Text=" دولار "
                      [1.5.2.2.1.2.1.1.1.2.T.1.4] Expression (unnamed) Value="FormatCurrencyCustom(GetCustomerLoans.List.Current.AmountSum)" Style="\"font-semi-bold\""
                    [1.5.2.2.1.2.1.1.1.2.F.1] Container (unnamed) PlaceholderName="FalseBranch" Style="\"margin-top-s\""
                      [1.5.2.2.1.2.1.1.1.2.F.1.1] Expression (unnamed) Value="FormatCurrencyCustom(GetCustomerLoans.List.Current.AmountSum)" Style="\"font-semi-bold\""
                      [1.5.2.2.1.2.1.1.1.2.F.1.2] Text (unnamed) Text=" of "
                      [1.5.2.2.1.2.1.1.1.2.F.1.3] Expression (unnamed) Value="FormatCurrencyCustom(GetCustomerLoans.List.Current.Amount)"
                [1.5.2.2.1.2.1.1.2] Container (unnamed) Style="\"margin-top-base\""
                  [1.5.2.2.1.2.1.1.2.1] BlockInstance (unnamed) SourceBlock="ProgressBar" ProgressColor="TextToIdentifier(\"#FFF\")" OptionalConfigs=null Progress="GetCustomerLoans.List.Current.AmountSum/GetCustomerLoans.List.Current.Amount*100" Thickness="8" ExtendedClass=null TrailColor="TextToIdentifier(\"#ffffff45\")"
    [1.5.3] BlockInstance 'ConsolidatedPositionSidebare' SourceBlock="Sidebar" Width=null Direction=null ExtendedClass="\"consolidated-position\"" StartsOpen=null HasOverlay="True"
      [1.5.3.1] Container (unnamed) PlaceholderName="Header" Style="\"margin-top-base\""
        [1.5.3.1.1] Container (unnamed) Width="10 col"
          [1.5.3.1.1.1] Text (unnamed) Style="\"heading5\"" Text="Consolidated Position"
        [1.5.3.1.2] Container (unnamed) Width="2 col" CustomStyle="text-align: right;"
          [1.5.3.1.2.1] Link (unnamed) OnClick→Destination="ConsolidatedPositionSidebarClose"
            [1.5.3.1.2.1.1] BlockInstance (unnamed) SourceBlock="HBIcon" Classes=null
              [1.5.3.1.2.1.1.1] Text (unnamed) PlaceholderName="IconName" Text="close"
      [1.5.3.2] Container (unnamed) PlaceholderName="Content"
        [1.5.3.2.1] Container (unnamed)
          [1.5.3.2.1.1] Container (unnamed)
            [1.5.3.2.1.1.1] BlockInstance (unnamed) SourceBlock="AlignCenter" ExtendedClass=null IsHorizontal=null
              [1.5.3.2.1.1.1.1] Text (unnamed) PlaceholderName="Content" Style="\"font-size-base margin-right-base\"" Text="My Assets"
              [1.5.3.2.1.1.1.2] BlockInstance (unnamed) PlaceholderName="Content" SourceBlock="Tag" Size=null Color="Entities.Color.Neutral2" Shape=null IsLight=null ExtendedClass=null
                [1.5.3.2.1.1.1.2.1] Text (unnamed) PlaceholderName="Tag" Style="\"text-green margin-right-xs\"" Text="+23%"
                [1.5.3.2.1.1.1.2.2] Expression (unnamed) PlaceholderName="Tag" Style="\"font-regular font-size-xs text-neutral-7 white-space-nowrap\"" Value="FormatDateTime(AddMonths(CurrDate(),-1),\"MMM\")+\"-\"+FormatDateTime(CurrDate(),\"MMM\")"
          [1.5.3.2.1.2] Container (unnamed) Style="\"margin-top-12\""
            [1.5.3.2.1.2.1] BlockInstance (unnamed) SourceBlock="ProgressBar" Thickness=null OptionalConfigs=null ExtendedClass=null Progress="If(TotalAssets>TotalDept,100,TotalAssets/TotalDept) *100" ProgressColor="Entities.Color.Green" TrailColor="Entities.Color.Transparent"
          [1.5.3.2.1.3] Container (unnamed) Style="\"margin-top-12\""
            [1.5.3.2.1.3.1] Expression (unnamed) Style="\"font-size-base font-semi-bold\"" Value="FormatCurrencyCustom(TotalAssets)"
        [1.5.3.2.2] Container (unnamed) Style="\"margin-top-l\""
          [1.5.3.2.2.1] Container (unnamed)
            [1.5.3.2.2.1.1] Text (unnamed) Style="\"font-size-base\"" Text="My Debt"
          [1.5.3.2.2.2] Container (unnamed) Style="\"margin-top-12\""
            [1.5.3.2.2.2.1] BlockInstance (unnamed) SourceBlock="ProgressBar" ProgressColor="Entities.Color.Red" Thickness=null OptionalConfigs=null ExtendedClass=null TrailColor="Entities.Color.Transparent" Progress="If(TotalDept>TotalAssets,100,TotalDept/TotalAssets)*100"
          [1.5.3.2.2.3] Container (unnamed) Style="\"margin-top-12\""
            [1.5.3.2.2.3.1] Expression (unnamed) Style="\"font-size-base font-semi-bold\"" Value="FormatCurrencyCustom(TotalDept)"
        [1.5.3.2.3] Container (unnamed) Style="\"margin-top-l\""
          [1.5.3.2.3.1] ButtonGroup 'ButtonGroup2' Variable="IsDeptConsolidatedPositionOption" Style="\"button-group\""
            [1.5.3.2.3.1.1] ButtonGroupItem 'ButtonGroupItem3' Style="\"button-group-item\"" Value="False"
              [1.5.3.2.3.1.1.1] Text (unnamed) Text="My Assets"
            [1.5.3.2.3.1.2] ButtonGroupItem 'ButtonGroupItem4' Style="\"button-group-item\"" Value="True"
              [1.5.3.2.3.1.2.1] Text (unnamed) Text="My Debt"
        [1.5.3.2.4] Container 'Assets2' Visible="not IsDeptConsolidatedPositionOption"
          [1.5.3.2.4.1] Container (unnamed) Style="\"margin-top-l position-relative\""
            [1.5.3.2.4.1.1] BlockInstance (unnamed) SourceBlock="PieChart" Height="\"245px\"" ExtendedClass=null OptionalConfigs=null DataPointList="GetAssets.List mapTo { Value: AccountBalance, Label: Label, Color: Color, Tooltip: Label+\": \"+FormatCurrencyCustom(AccountBalance) }"
              [1.5.3.2.4.1.1.1] BlockInstance (unnamed) PlaceholderName="AddOns_Placeholder" SourceBlock="ChartSeriesStyling" SeriesType=null OptionalConfigs=null Styling=null SeriesName=null ExtendedClass=null ShowDataPointValues=null Marker=null
            [1.5.3.2.4.1.2] Container (unnamed) Style="\"total-in-chart\""
              [1.5.3.2.4.1.2.1] Container (unnamed)
                [1.5.3.2.4.1.2.1.1] Expression (unnamed) Style="\"font-size-base \"" Value="Client.Currency" Width="auto"
                [1.5.3.2.4.1.2.1.2] Expression (unnamed) Value="FormatCurrency(TotalAssets,\"\",2,Client.DecimalSeparator,Client.GroupSeparator)" Width="auto"
          [1.5.3.2.4.2] Container (unnamed) Style="\"margin-top-s\""
            [1.5.3.2.4.2.1] BlockInstance (unnamed) SourceBlock="Accordion" MultipleItems=null ExtendedClass=null
              [1.5.3.2.4.2.1.1] List (unnamed) PlaceholderName="Content" Source="GetAssets.List" Style="\"list list-group\""
                [1.5.3.2.4.2.1.1.1] Container (unnamed) Style="\"margin-top-12\""
                  [1.5.3.2.4.2.1.1.1.1] BlockInstance (unnamed) SourceBlock="AccountAccordian" AccountTypeId="GetAssets.List.Current.ProductTypeId" AccountBalance="GetAssets.List.Current.AccountBalance" Color="GetAssets.List.Current.Color" Label="GetLabelByLocale(GetAssets.List.Current.LabelLocale, Client.LocaleId)"
        [1.5.3.2.5] Container 'Depts2' Visible=" IsDeptConsolidatedPositionOption"
          [1.5.3.2.5.1] Container (unnamed) Style="\"margin-top-l position-relative\""
            [1.5.3.2.5.1.1] BlockInstance (unnamed) SourceBlock="PieChart" Height="\"245px\"" DataPointList="DeptList mapTo { Value: Balance, Label: Label, Color: Color, Tooltip: Label+\": \"+FormatCurrencyCustom(Balance) }" ExtendedClass=null OptionalConfigs=null
              [1.5.3.2.5.1.1.1] BlockInstance (unnamed) PlaceholderName="AddOns_Placeholder" SourceBlock="ChartSeriesStyling" SeriesName=null Marker=null ShowDataPointValues=null Styling=null ExtendedClass=null OptionalConfigs=null SeriesType=null
            [1.5.3.2.5.1.2] Container (unnamed) Style="\"total-in-chart\""
              [1.5.3.2.5.1.2.1] Container (unnamed)
                [1.5.3.2.5.1.2.1.1] Expression (unnamed) Style="\"font-size-base \"" Value="Client.Currency" Width="auto"
                [1.5.3.2.5.1.2.1.2] Expression (unnamed) Value="FormatCurrency(TotalDept,\"\",2,Client.DecimalSeparator,Client.GroupSeparator)" Width="auto"
          [1.5.3.2.5.2] Container (unnamed) Style="\"margin-top-s\""
            [1.5.3.2.5.2.1] BlockInstance (unnamed) SourceBlock="Accordion" ExtendedClass=null MultipleItems=null
              [1.5.3.2.5.2.1.1] List (unnamed) PlaceholderName="Content" Source="DeptList" Style="\"list list-group\""
                [1.5.3.2.5.2.1.1.1] Container (unnamed) Style="\"margin-top-12\""
                  [1.5.3.2.5.2.1.1.1.1] If (unnamed) Condition="DeptList.Current.IsLoan"
                    [1.5.3.2.5.2.1.1.1.1.T.1] BlockInstance (unnamed) PlaceholderName="TrueBranch" SourceBlock="LoanAccordian" Color="DeptList.Current.Color" Label="DeptList.Current.Label" TotalLoan="DeptList.Current.Balance"
                    [1.5.3.2.5.2.1.1.1.1.F.1] BlockInstance (unnamed) PlaceholderName="FalseBranch" SourceBlock="AccountAccordian" Color="DeptList.Current.Color" AccountTypeId="Entities.ProductType.CreditCard" Label="DeptList.Current.Label+\"s\"" AccountBalance="DeptList.Current.Balance"
