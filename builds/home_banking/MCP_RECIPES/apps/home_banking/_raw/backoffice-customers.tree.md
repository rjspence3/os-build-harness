```
=== Screen: Customers ===
Inputs: <none>
Locals: SearchKeyword:Text, TableSort:Text, StartIndex:Integer, MaxRecords:Integer (default=5), CategoryFilter:Text (default="All")
Aggregates: GetCustomersWithAccounts
--- WIDGETS (hierarchical) ---
[1] BlockInstance 'LayoutSideMenu' SourceBlock="LayoutSideMenu" HasFixedHeader=null ExtendedClass=null
  [1.1] Placeholder 'Navigation'
    [1.1.1] BlockInstance 'Menu' SourceBlock="Menu" ActiveItem=null ActiveSubItem=null
  [1.2] Placeholder 'Header'
    [1.2.1] BlockInstance 'Header' SourceBlock="Header" HasAIChat="False" NotificationCount=null
  [1.3] Placeholder 'Title'
    [1.3.1] Text Text="Customers"
  [1.4] Placeholder 'MainContent'
    [1.4.1] Container Style=null Visible="True" Width="(fill parent)"
      [1.4.1.1] Text Style="\"text-neutral-8\"" Text="Search by name or id number"
    [1.4.2] Container Style="\"margin-top-s\"" Visible="True" Width="(fill parent)"
      [1.4.2.1] BlockInstance 'ColumnsMediumLeft' SourceBlock="ColumnsMediumLeft" PhoneBehavior="Entities.BreakColumns.All" TabletBehavior=null GutterSize=null
        [1.4.2.1.1] Placeholder 'Column1'
          [1.4.2.1.1.1] Container Style=null Visible="True" Width="(fill parent)"
            [1.4.2.1.1.1.1] BlockInstance 'InputWithIcon' SourceBlock="InputWithIcon" AlignIconRight=null
              [1.4.2.1.1.1.1.1] Placeholder 'Icon'
                [1.4.2.1.1.1.1.1.1] BlockInstance 'HBIcon' SourceBlock="HBIcon" Classes=null
                  [1.4.2.1.1.1.1.1.1.1] Placeholder 'IconName'
                    [1.4.2.1.1.1.1.1.1.1.1] Text Text="search"
              [1.4.2.1.1.1.1.2] Placeholder 'Input'
                [1.4.2.1.1.1.1.2.1] Input 'Input_SearchKeyword' Type=Search Variable="SearchKeyword" Prompt="\"Search by Name or ID No\"" Style="\"form-control  no-border-with-shadow\"" MaxLength=50 Enabled="True" Mandatory="False" Width="(fill parent)" OnChange→Refresh(NewStartIndex=null)
        [1.4.2.1.2] Placeholder 'Column2'
          [1.4.2.1.2.1] Container Style="If(IsPhone(), \"\", \"ThemeGrid_Width6\")" Visible="True" Width="(fill parent)"
            [1.4.2.1.2.1.1] ButtonGroup 'ButtonGroup1' Variable="CategoryFilter" Style="\"button-group\"" Enabled="True" Mandatory="False" Width="(fill parent)" OnChange→Refresh(NewStartIndex=null)
              [1.4.2.1.2.1.1.1] ButtonGroupItem 'ButtonGroupItem1' Value="\"All\"" Style="\"button-group-item\"" Enabled="True" Visible="True"
                [1.4.2.1.2.1.1.1.1] Text CustomStyle="font-weight: normal;" Text="All"
              [1.4.2.1.2.1.1.2] ButtonGroupItem 'ButtonGroupItem2' Value="\"Premium\"" Style="\"button-group-item\"" Enabled="True" Visible="True"
                [1.4.2.1.2.1.1.2.1] Text CustomStyle="font-weight: normal;" Text="Premium"
              [1.4.2.1.2.1.1.3] ButtonGroupItem 'ButtonGroupItem3' Value="\"Standard\"" Style="\"button-group-item\"" Enabled="True" Visible="True"
                [1.4.2.1.2.1.1.3.1] Text CustomStyle="font-weight: normal;" Text="Standard"
    [1.4.3] Container 'IsTableLoadingOrEmpty' Style="\"margin-top-base\"" Visible="True" Width="(fill parent)"
      [1.4.3.1] If 'IsEmpty' Condition="GetCustomersWithAccounts.IsDataFetched and GetCustomersWithAccounts.List.Empty"
        [1.4.3.1.T] TrueBranch
          [1.4.3.1.T.1] Container Style="\"table-empty margin-top-m\"" Visible="True" Width="(fill parent)"
            [1.4.3.1.T.1.1] BlockInstance 'BlankSlate' SourceBlock="BlankSlate" FullHeight=null
              [1.4.3.1.T.1.1.1] Placeholder 'Icon'
                [1.4.3.1.T.1.1.1.1] BlockInstance 'HBIcon' SourceBlock="HBIcon" Classes=null
                  [1.4.3.1.T.1.1.1.1.1] Placeholder 'IconName'
                    [1.4.3.1.T.1.1.1.1.1.1] Text Text="users"
              [1.4.3.1.T.1.1.2] Placeholder 'Content'
                [1.4.3.1.T.1.1.2.1] Text Text="There aren't any customers to show."
        [1.4.3.1.F] FalseBranch
          [1.4.3.1.F.1] If 'IsLoading' Condition="not GetCustomersWithAccounts.IsDataFetched"
            [1.4.3.1.F.1.T] TrueBranch
              [1.4.3.1.F.1.T.1] Container Style="\"list-updating\"" Visible="True" Width="(fill parent)"
            [1.4.3.1.F.1.F] FalseBranch
              [1.4.3.1.F.1.F.1] Container Style="\"horizontal-scroll\"" Visible="True" Width="(fill parent)"
                [1.4.3.1.F.1.F.1.1] TableRecords Source="GetCustomersWithAccounts.List" Style="\"table\"" StyleHeader="\"table-header\"" StyleRow="\"table-row\"" ShowHeader=true OnSort→OnSort(SortBy=ClickedColumn)
                  [HEADER ROW]
                    [H1] HeaderCell SortAttribute="Name"
                      [H1.1] Text Text="Customer Name"
                    [H2] HeaderCell SortAttribute="CardID" CustomStyle="text-align: right"
                      [H2.1] Text Text="ID No"
                    [H3] HeaderCell SortAttribute="ClientSince" CustomStyle="text-align: right"
                      [H3.1] Text Text="Client Since"
                    [H4] HeaderCell SortAttribute="Mobile"
                      [H4.1] Text Text="Phone No"
                    [H5] HeaderCell SortAttribute="AmountWithSignSum" CustomStyle="text-align: right"
                      [H5.1] Text Text="Balance"
                    [H6] HeaderCell SortAttribute="CreditScore" CustomStyle="text-align: right"
                      [H6.1] Text Text="Credit worthiness"
                    [H7] HeaderCell SortAttribute="IsPremium"
                      [H7.1] Text Text="Category"
                  [DATA ROW]
                    [R1] RowCell
                      [R1.1] Link Style=null Enabled="True" Visible="True" OnClick→CustomerDetail(CustomerId="GetCustomersWithAccounts.List.Current.Id")
                        [R1.1.1] Expression Value="GetCustomersWithAccounts.List.Current.Name"
                    [R2] RowCell
                      [R2.1] Container Align=Right Visible="True" Width="(fill parent)"
                        [R2.1.1] Expression Value="GetCustomersWithAccounts.List.Current.CardID"
                    [R3] RowCell
                      [R3.1] Container Align=Right Visible="True" Width="(fill parent)"
                        [R3.1.1] Expression Value="FormatDateLocale(GetCustomersWithAccounts.List.Current.ClientSince, Client.LocaleId)"
                    [R4] RowCell
                      [R4.1] Expression Value="GetCustomersWithAccounts.List.Current.Mobile"
                    [R5] RowCell
                      [R5.1] Container Align=Right Visible="True" Width="(fill parent)"
                        [R5.1.1] Expression Value="FormatCurrencyCustom(GetCustomersWithAccounts.List.Current.AmountWithSignSum,2)"
                    [R6] RowCell
                      [R6.1] BlockInstance 'CreditCategories' SourceBlock="CreditCategories" CreditScore="GetCustomersWithAccounts.List.Current.CreditScore"
                    [R7] RowCell
                      [R7.1] If Condition="GetCustomersWithAccounts.List.Current.IsPremium" DesignMode=ShowTrueOrPreview
                        [R7.1.T] TrueBranch
                          [R7.1.T.1] BlockInstance 'Tag' SourceBlock="Tag" ExtendedClass="\"background-tag-is-premium\""
                            [R7.1.T.1.1] Placeholder 'Tag'
                              [R7.1.T.1.1.1] BlockInstance 'HBIcon' SourceBlock="HBIcon" Classes="\"margin-right-xs\""
                                [R7.1.T.1.1.1.1] Placeholder 'IconName'
                                  [R7.1.T.1.1.1.1.1] Text Text="star"
                              [R7.1.T.1.1.2] Text CustomStyle="font-weight: normal;" Text="Premium"
                        [R7.1.F] FalseBranch
                          [R7.1.F.1] BlockInstance 'Tag' SourceBlock="Tag" ExtendedClass="\"background-tag-not-premium\""
                            [R7.1.F.1.1] Placeholder 'Tag'
                              [R7.1.F.1.1.1] BlockInstance 'HBIcon' SourceBlock="HBIcon" Classes="\"margin-right-xs\""
                                [R7.1.F.1.1.1.1] Placeholder 'IconName'
                                  [R7.1.F.1.1.1.1.1] Text Text="medal"
                              [R7.1.F.1.1.2] Text CustomStyle="font-weight: normal;" Text="Standard"
              [1.4.3.1.F.1.F.2] BlockInstance 'Pagination' SourceBlock="Pagination" MaxRecords="MaxRecords" TotalCount="GetCustomersWithAccounts.Count" StartIndex="StartIndex" ShowGoToPage=null OnNavigate→Refresh(NewStartIndex="NewStartIndex")
                [PREV placeholder] Icon icon="angle-left"
                [NEXT placeholder] Icon icon="angle-right"
```