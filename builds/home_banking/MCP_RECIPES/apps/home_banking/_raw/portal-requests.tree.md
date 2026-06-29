```
=== Screen: Requests ===
Inputs: (none)
Locals: TableSort:Text, StartIndex:Integer, MaxRecords:Integer (default=5), MyRequestsFilters:MyRequestsFilters, LoadingDateTime:DateTime (default=CurrDateTime())
Aggregates: GetCustomerRequests, GetRequestStatuses, GetRequestTypes
DataActions: FirebaseData (outputs: Firebase_TargetIdentifier, Firebase_Token, Firebase_ProjectId, Firebase_DatabaseURL), GetCounters (outputs: ApprovedRequests, RejectedRequests, PendingRequests)

--- WIDGETS (hierarchical) ---
[1] BlockInstance 'LayoutTopMenu' Source=LayoutTopMenu
  [Header placeholder]
  [2]   BlockInstance (unnamed) Source=Menu ActiveItem=null ActiveSubItem=null
  [MainContent placeholder]
  [3]   Container 'Counters' Style="margin-top-xl dashboard-counters margin-bottom-l" Width=(fill parent)
  [4]     BlockInstance (unnamed) Source=Columns3 TabletBehavior=Entities.BreakColumns.Last PhoneBehavior=Entities.BreakColumns.All
    [Column1 placeholder]
    [5]       Container (unnamed) Style="counter-card" Width=(fill parent)
    [6]         Container (unnamed) CustomStyle="text-align: left;" Width=""
    [7]           Container (unnamed) Style="circle-bg-icon" Width=(fill parent)
    [8]             BlockInstance (unnamed) Source=HBIcon
              [IconName placeholder]
              [9]               Text "warning" Style="font-size-h4 text-wht"
    [10]         Container (unnamed) Style="margin-left-base" Width=""
    [11]           Container (unnamed) Width=(fill parent)
    [12]             Expression (unnamed) Value="GetCounters.PendingRequests" Style="heading2" Example="4"
    [13]           Container (unnamed) Width=(fill parent)
    [14]             Text "Information Requested" Style="font-size-base"
    [Column2 placeholder]
    [15]       Container (unnamed) Style="counter-card" Width=(fill parent)
    [16]         Container (unnamed) CustomStyle="text-align: left;" Width=""
    [17]           Container (unnamed) Style="circle-bg-icon" Width=(fill parent)
    [18]             BlockInstance (unnamed) Source=HBIcon
              [IconName placeholder]
              [19]               Text "checkcircle" Style="font-size-h4 text-wht"
    [20]         Container (unnamed) Style="margin-left-base" Width=""
    [21]           Container (unnamed) Width=(fill parent)
    [22]             Expression (unnamed) Value="GetCounters.ApprovedRequests" Style="heading2" Example="4"
    [23]           Container (unnamed) Width=(fill parent)
    [24]             Text "Approved Requests" Style="font-size-base"
    [Column3 placeholder]
    [25]       Container (unnamed) Style="counter-card" Width=(fill parent)
    [26]         Container (unnamed) CustomStyle="text-align: left;" Width=""
    [27]           Container (unnamed) Style="circle-bg-icon" Width=(fill parent)
    [28]             Image (unnamed) Source=closecircle Type=Static
    [29]         Container (unnamed) Style="flex-grow-1 margin-left-base" Width=""
    [30]           Container (unnamed) Width=(fill parent)
    [31]             Expression (unnamed) Value="GetCounters.RejectedRequests" Style="heading2" Example="4"
    [32]           Container (unnamed) Width=(fill parent)
    [33]             Text "Declined Requests" Style="font-size-base" CustomStyle="margin-top: 4px;"
  [34]   Container (unnamed) Width=(fill parent)
  [35]     Text "My Requests" Style="font-size-h5"
  [36]   Container (unnamed) Style="margin-top-base" Width=(fill parent)
  [37]     Container (unnamed) Style="text-neutral-8" Width=(fill parent)
  [38]       Text "Filter by" Style="font-weight-500"
  [39]     Container (unnamed) Style="display-flex" Width=(fill parent)
  [40]       If 'IsPhone()' DesignMode=ShowAll
        [TrueBranch]
        [41]         Dropdown 'Dropdown2' List="GetRequestStatuses.List" Labels="LoanRequestStatus.Label" Values="LoanRequestStatus.Id" Variable="MyRequestsFilters.RequestStatusId" EmptyValue="Request Status" Style="dropdown no-border-with-shadow" Width=(fill parent) OnChange→Refresh
        [FalseBranch]
        [42]         Container 'ALL' CustomStyle="margin-right: 16px; margin-top: 5px; padding: 0px;" Width=auto
        [43]           Container (unnamed) Width=(fill parent) onclick→StatusFilterOnClick(RequestStatusId=NullIdentifier())
        [44]             Expression (unnamed) Value="All" CustomStyle="font-size: 12px;" ExtendedProp class="status-filter "+If(…NullIdentifier()…,"status-filter-selected","status-filter-gray")
        [45]         List (unnamed) Source="GetRequestStatuses.List" Style="list list-group" Width=(fill parent)
        [46]           Container (unnamed) CustomStyle="margin-right: 16px; margin-top: 5px; padding: 0px;" Width=auto
        [47]             Container (unnamed) Width=(fill parent) onclick→StatusFilterOnClick(RequestStatusId=GetRequestStatuses.List.Current.LoanRequestStatus.Id)
        [48]               Expression (unnamed) Value="GetRequestStatuses.List.Current.LoanRequestStatus.Label" CustomStyle="font-size: 12px;" ExtendedProp class="status-filter "+If(…selected…)
  [49]     Container (unnamed) Style=If(IsPhone(),"margin-top-s","margin-top-base") Width=(fill parent)
  [50]       Container (unnamed) Width=(fill parent)
  [51]         BlockInstance (unnamed) Source=Columns2 TabletBehavior=Entities.BreakColumns.All GutterSize=Entities.GutterSize.Small PhoneBehavior=Entities.BreakColumns.All
          [Column1 placeholder]
          [52]           BlockInstance (unnamed) Source=Columns2 GutterSize=Entities.GutterSize.Small PhoneBehavior=Entities.BreakColumns.All
            [Column1 placeholder]
            [53]             Dropdown 'Dropdown1' List="GetRequestTypes.List" Labels="LoanRequestType.Label" Values="LoanRequestType.Id" Variable="MyRequestsFilters.RequestTypeId" EmptyValue="Request Type" Style="dropdown no-border-with-shadow" Width=(fill parent) OnChange→Refresh
            [Column2 placeholder]
            [54]             Input 'Input_TextVar' Type=Date Variable="MyRequestsFilters.CreationDate" Prompt="Date" Style="form-control no-border-with-shadow" Width=(fill parent) OnChange→Refresh
          [Column2 placeholder]
          [55]           Container (unnamed) Width="5 col"
          [56]             BlockInstance (unnamed) Source=InputWithIcon AlignIconRight=null
              [Icon placeholder]
              [57]               BlockInstance (unnamed) Source=HBIcon
                [IconName placeholder]
                [58]                 Text "search"
              [Input placeholder]
              [59]               Input 'Input_SearchKeyword' Type=Search Variable="MyRequestsFilters.SearchKeyword" Prompt="Search" MaxLength=50 Style="form-control no-border-with-shadow" Width=(fill parent) OnChange→Refresh
          [60]           Container (unnamed) CustomStyle="text-align: right;" Width="7 col"
          [61]             Button (unnamed) Text="Reset Filters" Style="btn" OnClick→ResetFiltersOnClick
  [62]   Container 'IsTableLoadingOrEmpty' Style="margin-top-base" Width=(fill parent)
  [63]     If 'IsEmpty' Condition="GetCustomerRequests.IsDataFetched and GetCustomerRequests.List.Empty" DesignMode=ShowAll
      [TrueBranch]
      [64]       Container (unnamed) Style="table-empty margin-top-m" Width=(fill parent)
      [65]         BlockInstance (unnamed) Source=BlankSlate
            [Icon placeholder]
            [66]             BlockInstance (unnamed) Source=HBIcon
              [IconName placeholder]
              [67]               Text "note"
            [Content placeholder]
            [68]             Text "There aren't any requests to show."
      [FalseBranch]
      [69]       If 'IsLoading' Condition="not GetCustomerRequests.IsDataFetched" DesignMode=ShowAll
          [TrueBranch]
          [70]           Container (unnamed) Style="list-updating" Width=(fill parent)
          [FalseBranch]
          [71]           TableRecords (unnamed) Source="GetCustomerRequests.List" Style="table request-table" StyleHeader="table-header" StyleRow="table-row" ShowHeader=true OnSort→OnSort(SortBy=ClickedColumn)
            [HeaderRow]
            [72]             HeaderCell (unnamed) SortAttribute="Id" Style="text-align-left"
            [73]               Text "No ID"
            [74]             HeaderCell (unnamed) SortAttribute="RequestType" Style="text-align-left"
            [75]               Text "Request Type"
            [76]             HeaderCell (unnamed) SortAttribute="PeriodMonth"
            [77]               Text "Term"
            [78]             HeaderCell (unnamed) SortAttribute="InterestRatePercentage" Style="text-align-right request-headercell"
            [79]               Text "Interest Rate"
            [80]             HeaderCell (unnamed) SortAttribute="AmountWithSignSum" Style="text-align-right request-headercell"
            [81]               Text "Amount"
            [82]             HeaderCell (unnamed) SortAttribute="CreatedOn" Style="text-align-left request-headercell"
            [83]               Text "Date Created"
            [84]             HeaderCell (unnamed) SortAttribute="StatusId"
            [85]               Text "Status"
            [Row]
            [86]             RowCell (unnamed) Style="text-align-left"
            [87]               If 'IsPersonalLoan' Condition="…TypeId=Entities.LoanRequestType.PersonalLoan" DesignMode=ShowTrueOrPreview
                [TrueBranch]
                [88]                 Link (unnamed) OnClick→PersonalLoan(RequestId=…Id, StepNo=2)
                [89]                   Expression (unnamed) Value='"#"+FormatText(…Id,4,20,True,0)' Example="#0013"
                [FalseBranch]
                [90]                 Expression (unnamed) Value='"#"+FormatText(…Id,4,20,True,0)' Example="#0013"
            [91]             RowCell (unnamed)
            [92]               Container (unnamed) Align=Right CustomStyle="text-align: left;" Width=(fill parent)
            [93]                 Expression (unnamed) Value="GetCustomerRequests.List.Current.RequestType" Example="Personal Loan"
            [94]             RowCell (unnamed)
            [95]               Container (unnamed) Align=Right CustomStyle="text-align: left;" Width=(fill parent)
            [96]                 Expression (unnamed) Value='…PeriodMonth+" months"' Example="45 months"
            [97]             RowCell (unnamed)
            [98]               Container (unnamed) CustomStyle="text-align: right;" Width=(fill parent)
            [99]                 Expression (unnamed) Value='…InterestRatePercentage+"% p.a."' Example="4.21% p.a."
            [100]             RowCell (unnamed)
            [101]               Container (unnamed) Align=Right Width=(fill parent)
            [102]                 Expression (unnamed) Value="FormatCurrencyCustom(…AmountWithSignSum)" Example="$10,000.00"
            [103]             RowCell (unnamed)
            [104]               Expression (unnamed) Value="FormatDateCustom(…CreatedOn)" Example="27-09-2024"
            [105]             RowCell (unnamed)
            [106]               Container (unnamed) Width=(fill parent)
            [107]                 If 'Approved' Condition="…StatusId=Entities.LoanRequestStatus.Approved" DesignMode=ShowTrueOrPreview
                  [TrueBranch]
                  [108]                   BlockInstance (unnamed) Source=Tag Color="TextToIdentifier(…Color)" ExtendedClass="background-tag-is-premium"
                    [Tag placeholder]
                    [109]                     Text "Approved" Style="requeststatus-tag" CustomStyle="font-weight: normal;"
                  [FalseBranch]
                  [110]                   If 'Rejected' Condition="…StatusId=Entities.LoanRequestStatus.Rejected" DesignMode=ShowAll
                      [TrueBranch]
                      [111]                     BlockInstance (unnamed) Source=Tag Color="TextToIdentifier(…Color)" ExtendedClass="background-tag-not-premium"
                        [Tag placeholder]
                        [112]                       Text "Declined" Style="requeststatus-tag" CustomStyle="font-weight: normal;"
                      [FalseBranch]
                      [113]                     If 'InfoRequested' Condition="…Pending or …WaitResubmission" DesignMode=ShowAll
                          [TrueBranch]
                          [114]                         BlockInstance (unnamed) Source=Tag Color="TextToIdentifier(…Color)" ExtendedClass="background-tag-not-premium"
                            [Tag placeholder]
                            [115]                           Text "Info Requested" Style="requeststatus-tag" CustomStyle="font-weight: normal;"
                          [FalseBranch]
                          [116]                         BlockInstance (unnamed) Source=Tag Color="Entities.Color.Blue" ExtendedClass="background-tag-not-premium"
                            [Tag placeholder]
                            [117]                           Text "Under Approval" Style="requeststatus-tag" CustomStyle="font-weight: normal;"
          [72b]           BlockInstance (unnamed) Source=Pagination StartIndex="StartIndex" TotalCount="GetCustomerRequests.Count" MaxRecords="MaxRecords" OnNavigate→Refresh(NewStartIndex=NewStartIndex)
            [Previous placeholder]
            [118]             Icon (unnamed) Icon="angle-left" IconSize=FontSize Style="icon"
            [Next placeholder]
            [119]             Icon (unnamed) Icon="angle-right" IconSize=FontSize Style="icon"
  [Footer placeholder]
  [120]   If (unnamed) Condition="False" DesignMode=ShowAll
      [FalseBranch]
      [121]     If 'Firebase_configured' Condition="FirebaseData.Firebase_ProjectId<>"" and FirebaseData.Firebase_DatabaseURL<>""" DesignMode=ShowTrueOrPreview
          [TrueBranch]
          [122]           BlockInstance (unnamed) Source=FirebaseReceiver FBDatabaseURL="FirebaseData.Firebase_DatabaseURL" Token="FirebaseData.Firebase_Token" TargetIdentifier="FirebaseData.Firebase_TargetIdentifier" ProjectId="FirebaseData.Firebase_ProjectId" AlertEventReceived→FirebaseReceiverAlertEventReceived MissingData→FirebaseReceiverMissingData
```