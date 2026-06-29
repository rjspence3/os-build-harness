```
=== Screen: Dashboard ===
Inputs: <none>
Locals: RequestStatusIdFilter:LoanRequestStatus Identifier, TableSort:Text, StartIndex:Integer, MaxRecords:Integer="5", RequestTypeIdFilter:LoanRequestType Identifier, EmployeeIdAssignedFilter:Employee Identifier, DateFilter:Date, SearchKeyword:Text, SelectedAll:Boolean, EnableAssignSelected:Boolean, ShowAssigningPopup:Boolean, SelectedEmployeeIdToAssign:Employee Identifier, SelectedRequestIdsToAssignEmp:LoanRequest Identifier List, EnableSelectAll:Boolean="False", ChatMessages:ChatMessage List, LoadingDateTime:DateTime="CurrDateTime()"
Aggregates: GetAssignedEmployees, GetLoginUserPicture, GetRequests, GetRequestStatuses, GetRequestTypes
DataActions: FirebaseData, GetCounters, GetDonutChartData, GetEmployeeTasks, GetLineChartSampleData, GetSampleUserEmpId

--- WIDGETS (hierarchical) ---

[1] BlockInstance 'LayoutSideMenuInstance' SourceBlock="LayoutSideMenu"
  [Placeholder: Navigation]
    [2] BlockInstance 'MenuInstance' SourceBlock="Menu" ActiveItem="0"
  [Placeholder: Header]
    [3] BlockInstance 'HeaderInstance' SourceBlock="Header" HasAIChat="True" NotificationCount="GetEmployeeTasks.EmployeeTasks.Length"
  [Placeholder: Title]
    [4] Expression Value="\"Welcome back, \"+Client.UserName+\"!\"" Example="Welcome back, Patricia!"
  [Placeholder: Actions]
    [5] Button Style="\"btn btn-primary\"" Enabled="True" OnClick=NotImplemented
      [6] BlockInstance 'HBIconInstance' SourceBlock="HBIcon"
        [Placeholder: IconName]
          [7] Text StyleClasses="\"bold font\"" Text="plus"
      [8] Text StyleClasses="\"margin-left-s\"" Text="New Simulation"
  [Placeholder: MainContent]
    [9] Container 'Counters' Style="\"dashboard-counters\""
      [10] BlockInstance 'Columns2Instance' SourceBlock="Columns2" GutterSize="If(IsPhone(), Entities.GutterSize.Medium, Entities.GutterSize.Base)" TabletBehavior="Entities.BreakColumns.Last" PhoneBehavior="Entities.BreakColumns.All"
        [Placeholder: Column1]
          [11] BlockInstance 'Columns2Instance2' SourceBlock="Columns2" PhoneBehavior="Entities.BreakColumns.All"
            [Placeholder: Column1]
              [12] BlockInstance 'CounterInstance' SourceBlock="Counter"
                [Placeholder: Number]
                  [13] Expression Value="GetCounters.PendingRequests" Example="4"
                [Placeholder: Tag]
                  [14] BlockInstance 'CounterTagInstance' SourceBlock="CounterTag" Percentage="GetCounters.PendingDiff" IsReversed="True"
                [Placeholder: Label]
                  [15] Text Text="Pending Requests"
            [Placeholder: Column2]
              [16] BlockInstance 'CounterInstance2' SourceBlock="Counter"
                [Placeholder: Number]
                  [17] Expression Value="GetCounters.CompletedRequests" Example="9"
                [Placeholder: Tag]
                  [18] BlockInstance 'CounterTagInstance2' SourceBlock="CounterTag" Percentage="GetCounters.CompletedDiff"
                [Placeholder: Label]
                  [19] Text Text="Completed Requests"
        [Placeholder: Column2]
          [20] BlockInstance 'CounterInstance3' SourceBlock="Counter"
            [Placeholder: Number]
              [21] Expression Value="GetCounters.Progress + \"%\"" Example="100%"
            [Placeholder: Extra]
              [22] Text StyleClasses="\"font-size-s\"" Text="Monthly Goal Progress"
            [Placeholder: Tag]
              [23] BlockInstance 'CounterTagInstance3' SourceBlock="CounterTag" Percentage="GetCounters.ProgressDiff"
            [Placeholder: Label]
              [24] BlockInstance 'ProgressBarInstance' SourceBlock="ProgressBar" Progress="GetCounters.Progress" ProgressColor="TextToIdentifier(GetCounters.ProgressColor)"
    [25] Container Style="\"margin-top-xxl\""
      [26] Text StyleClasses="\"heading5\"" Text="All Requests"
    [27] Container Style="\"margin-top-base\""
      [28] Container Style="\"text-neutral-8\""
        [29] Text StyleClasses="\"font-weight-500\"" Text="Filter By"
      [30] Container (no style)
        [31] List Source="GetRequestStatuses.List" Style="\"list list-group\""
          [32] Container CustomStyle="margin-right: 16px; margin-top: 5px; padding: 0px;" Width="auto"
            [33] Container (no style)
              [34] Expression Value="If(GetRequestStatuses.List.CurrentRowNumber = 0 or GetRequestStatuses.List.CurrentRowNumber = GetRequestStatuses.List.Length - 1, GetRequestStatuses.List.Current.LoanRequestStatus.Label, GetLabelByLocale(GetRequestStatuses.List.Current.LoanRequestStatus.LabelLocale, Client.LocaleId))" Example="Submitted" CustomStyle="font-size: 12px;" ExtendedProperty[class]="\"status-filter \" + If(RequestStatusIdFilter = GetRequestStatuses.List.Current.LoanRequestStatus.Id, \"status-filter-selected\", \"status-filter-gray\")" OnClick=StatusFilterOnClick(RequestStatusId=GetRequestStatuses.List.Current.LoanRequestStatus.Id)
      [35] Container 'container7' Style="\"dashboard filters-wrapper margin-top-base\""
        [36] Dropdown 'Dropdown1' Style="\"dropdown no-border-with-shadow\" + If(IsPhone(),\" margin-bottom-s\",\"\")" List="GetRequestTypes.List" Values="LoanRequestType.Id" Variable="RequestTypeIdFilter" EmptyValue="\"Request Type\"" Mandatory="False" Enabled="True" Width="(fill parent)" OnChange=Refresh(NewStartIndex=null)
          [37] Expression Value="GetLabelByLocale(GetRequestTypes.List.Current.LoanRequestType.LabelLocale, Client.LocaleId)"
        [38] Dropdown 'Dropdown2' Style="\"dropdown no-border-with-shadow\" + If(IsPhone(),\" margin-bottom-s\",\"\")" List="GetAssignedEmployees.List" Values="EmployeeId" Variable="EmployeeIdAssignedFilter" EmptyValue="\"Assigned To\"" Enabled="not GetAssignedEmployees.List.Empty" Width="(fill parent)" OnChange=Refresh(NewStartIndex=null)
          [39] Expression Value="GetAssignedEmployees.List.Current.EmployeeName"
        [40] Input 'Input_TextVar' Type=Date Style="\"form-control no-border-with-shadow\" + If(IsPhone(),\" margin-bottom-s\",\"\")" Variable="DateFilter" Prompt="\"Date\"" Mandatory="False" OnChange=Refresh(NewStartIndex=null)
        [41] BlockInstance 'InputWithIconInstance' SourceBlock="InputWithIcon" ExtendedClass=" If(IsPhone(),\" margin-bottom-s\",\"\")"
          [Placeholder: Icon]
            [42] BlockInstance 'HBIconInstance2' SourceBlock="HBIcon"
              [Placeholder: IconName]
                [43] Text Text="search"
          [Placeholder: Input]
            [44] Input 'Input_SearchKeyword' Type=Search Style="\"form-control no-border-with-shadow\"" Variable="SearchKeyword" Prompt="\"Search for id or name\"" MaxLength=50 OnChange=Refresh(NewStartIndex=null)
        [45] Button Style="\"btn\"" Text="Reset Filters" OnClick=ResetFiltersOnClick
        [46] Container (no style)
          [47] Button Style="\"btn hide-on-sidebar\"" Enabled="EnableAssignSelected" OnClick=AssignSelectedRequestsOnClick
            [48] BlockInstance 'HBIconInstance3' SourceBlock="HBIcon"
              [Placeholder: IconName]
                [49] Text Text="profile"
            [50] Text StyleClasses="\"margin-left-s\"" Text="Assign Selected"
    [51] Container 'IsTableLoadingOrEmpty' Style="\"margin-top-base\""
      [52] If 'IsEmpty' Condition="GetRequests.IsDataFetched and GetRequests.List.Empty"
        [TrueBranch]
          [53] Container Style="\"table-empty\""
            [54] BlockInstance 'BlankSlateInstance' SourceBlock="BlankSlate" FullHeight=null
              [Placeholder: Icon]
                [55] BlockInstance 'HBIconInstance4' SourceBlock="HBIcon"
                  [Placeholder: IconName]
                    [56] Text Text="note"
              [Placeholder: Content]
                [57] Text Text="There aren't any requets to show."
        [FalseBranch]
          [58] If 'IsLoading' Condition="not GetRequests.IsDataFetched"
            [TrueBranch]
              [59] Container Style="\"list-updating\""
            [FalseBranch]
              [60] Container Style="\"horizontal-scroll\""
                [61] TableRecords Source="GetRequests.List" Style="\"table\"" StyleHeader="\"table-header\"" StyleRow="\"table-row\"" ShowHeader=True OnSort=OnSort(SortBy=ClickedColumn)
                  [HeaderRow]
                    [62] HeaderCell Style="\"hide-on-sidebar\""
                      [63] Checkbox 'Checkbox1' Variable="SelectedAll" Enabled="EnableSelectAll" OnChange=SelectAllOnChange
                    [64] HeaderCell SortAttribute="LoanRequest.Id"
                      [65] Text Text="No ID"
                    [66] HeaderCell SortAttribute="LoanRequest.TypeId"
                      [67] Text Text="Request Type"
                    [68] HeaderCell SortAttribute="LoanRequest.CustomerId"
                      [69] Text Text="Customer Name"
                    [70] HeaderCell SortAttribute="LoanRequest.CreatedOn" CustomStyle="text-align: right"
                      [71] Text Text="Created On"
                    [72] HeaderCell (no sort)
                      [73] Text Text="SLA"
                    [74] HeaderCell SortAttribute="LoanRequest.AssignedToEmpId"
                      [75] Text Text="Assigned To"
                    [76] HeaderCell SortAttribute="LoanRequest.StatusId"
                      [77] Text Text="Status"
                  [Row]
                    [78] RowCell Style="\"hide-on-sidebar\""
                      [79] Checkbox 'Checkbox2' Variable="GetRequests.List.Current.IsSelected" Enabled="GetRequests.List.Current.LoanRequest.AssignedToEmpId = NullIdentifier() and GetRequests.List.Current.LoanRequest.StatusId <> Entities.LoanRequestStatus.Approved and GetRequests.List.Current.LoanRequest.StatusId <> Entities.LoanRequestStatus.Rejected" OnChange=SelectOnChange
                    [80] RowCell
                      [81] Link Enabled="True" OnClick=RequestDetail(RequestId=GetRequests.List.Current.LoanRequest.Id, IsSidebarOpen=IsPhone()=False)
                        [82] Expression Value="\"#\"+FormatText(GetRequests.List.Current.LoanRequest.Id,4,20,True,0)"
                    [83] RowCell
                      [84] Expression Value="GetLabelByLocale(GetRequests.List.Current.LoanRequestType.LabelLocale, Client.LocaleId)" Example="Car Loan"
                    [85] RowCell
                      [86] Expression Value="GetRequests.List.Current.HBCustomer.Name"
                    [87] RowCell
                      [88] Container Align=Right
                        [89] Expression Value="FormatDateLocale(GetRequests.List.Current.LoanRequest.CreatedOn, Client.LocaleId)"
                    [90] RowCell
                      [91] BlockInstance 'AlignCenterInstance' SourceBlock="AlignCenter"
                        [Placeholder: Content]
                          [92] Icon Icon="circle" Style="\"icon margin-right-s \" + If(GetRequests.List.Current.SLA > 2, \"text-green\", If(GetRequests.List.Current.SLA > 0, \"text-orange\", \"text-red\"))" CustomStyle="font-size: 8px;"
                          [93] Expression Value="GetRequests.List.Current.SLA + \" days\"" Style="\"white-space-nowrap\"" Example="10 days"
                    [94] RowCell
                      [95] If 'HasAssignedEmployee' Condition="GetRequests.List.Current.LoanRequest.AssignedToEmpId <> NullIdentifier()"
                        [TrueBranch]
                          [96] BlockInstance 'EmployeePhotoInstance' SourceBlock="EmployeePhoto" EmployeeId="GetRequests.List.Current.Employee.Id" IsSmallSize="True"
                        [FalseBranch]
                          [97] Button Style="\"btn\"" Enabled="not EnableAssignSelected" OnClick=AssignEmployeeOnClick(RequestId=GetRequests.List.Current.LoanRequest.Id)
                            [98] BlockInstance 'HBIconInstance5' SourceBlock="HBIcon"
                              [Placeholder: IconName]
                                [99] Text Text="profile"
                            [100] Text StyleClasses="\"margin-left-s\"" Text="Assign"
                    [101] RowCell
                      [102] BlockInstance 'TagInstance' SourceBlock="Tag" Color="TextToIdentifier(GetRequests.List.Current.LoanRequestStatus.Color)"
                        [Placeholder: Tag]
                          [103] Expression Value="GetLabelByLocale(GetRequests.List.Current.LoanRequestStatus.LabelLocale, Client.LocaleId)" Style="\"white-space-nowrap\"" CustomStyle="font-weight: normal;"
              [104] BlockInstance 'PaginationInstance' SourceBlock="Pagination" MaxRecords="MaxRecords" StartIndex="StartIndex" TotalCount="GetRequests.Count" OnNavigate=Refresh(NewStartIndex=NewStartIndex)
                [Placeholder: Previous]
                  [105] Icon Icon="angle-left" IconSize=FontSize Style="\"icon\""
                [Placeholder: Next]
                  [106] Icon Icon="angle-right" IconSize=FontSize Style="\"icon\""
    [107] Container Style="\"margin-top-xxl\""
      [108] BlockInstance 'Columns2Instance3' SourceBlock="Columns2" TabletBehavior="Entities.BreakColumns.Middle" PhoneBehavior="Entities.BreakColumns.Middle"
        [Placeholder: Column1]
          [109] Container Style="\"card\""
            [110] Container Style="\"heading6\""
              [111] Text Text="Request Type Performance"
            [112] Container Style="\"margin-top-base\""
              [113] If Condition="GetLineChartSampleData.IsDataFetched"
                [TrueBranch]
                  [114] BlockInstance 'LineChartInstance' SourceBlock="LineChart" DataPointList="GetLineChartSampleData.ChartDataPoints" ValuesType="Entities.ValuesType.Datetime" Initialized=LineChartInitialized(ChartWidgetId=ChartWidgetId)
                    [Placeholder: AddOns_Placeholder]
                      [115] BlockInstance 'ChartXAxisInstance' SourceBlock="ChartXAxis" OptionalConfigs="{ ValuesType: Entities.AxisValuesType.Datetime }" GridLines="{ LinesColor: \"#F1F3F7\", LinesWidth: 1 }"
                      [116] BlockInstance 'ChartYAxisInstance' SourceBlock="ChartYAxis" GridLines="{ LinesColor: \"#F1F3F7\", LinesWidth: 1 }"
                      [117] BlockInstance 'ChartSeriesStylingInstance' SourceBlock="ChartSeriesStyling" SeriesName="\"Insurance Products\"" Styling="{ LineColor: \"#F76707\" }" Marker="{ FillColor: \"#F76707\", Radius: 2, MarkerSymbol: \"circle\" }"
                      [118] BlockInstance 'ChartLegendInstance' SourceBlock="ChartLegend" Styling="{ ItemsDistance: 40 }"
                      [119] BlockInstance 'ChartSeriesStylingInstance2' SourceBlock="ChartSeriesStyling" SeriesName="\"Loan Products\"" Styling="{ LineColor: \"#AE3EC9\" }" Marker="{ FillColor: \"#AE3EC9\", Radius: 2, MarkerSymbol: \"circle\" }"
                      [120] BlockInstance 'ChartSeriesStylingInstance3' SourceBlock="ChartSeriesStyling" SeriesName="\"Account Services\"" Styling="{ LineColor: \"#4263EB\" }" Marker="{ FillColor: \"#4263EB\", Radius: 2, MarkerSymbol: \"circle\" }"
                      [121] BlockInstance 'ChartSeriesStylingInstance4' SourceBlock="ChartSeriesStyling" SeriesName="\"Investment Products\"" Styling="{ LineColor: \"#0D8091\" }" Marker="{ FillColor: \"#0D8091\", Radius: 2, MarkerSymbol: \"circle\" }"
        [Placeholder: Column2]
          [122] Container Style="\"card\""
            [123] Container Style="\"heading6\""
              [124] Text Text="Requests by Type"
            [125] Container Style="\"margin-top-base donut-chart-cntr \""
              [126] If Condition="GetDonutChartData.IsDataFetched"
                [TrueBranch]
                  [127] BlockInstance 'DonutChartInstance' SourceBlock="DonutChart" DataPointList="GetDonutChartData.ChartDataPoints" Height="250" InnerSize="\"85%\"" Initialized=DonutChartInitialized(ChartWidgetId=ChartWidgetId)
                    [Placeholder: AddOns_Placeholder]
                      [128] BlockInstance 'ChartLegendInstance2' SourceBlock="ChartLegend" Position="Entities.LegendPosition.Right"
                      [129] BlockInstance 'ChartSeriesStylingInstance5' SourceBlock="ChartSeriesStyling" Styling="{  }"
              [130] Container CustomStyle="text-align: center;" Style="\"chart-total-value\""
                [131] Container
                  [132] Expression Value="GetDonutChartData.Total" Style="\"heading5\"" Example="123"
                [133] Container
                  [134] Text StyleClasses="\"text-neutral-7\"" Text="Total"
    [135] BlockInstance 'AgentSidebarInstance' SourceBlock="AgentSidebar" InputPrompt="\"Ask about loan requests\""
      [Placeholder: Subtitle]
        [136] Expression Value="\"You have \"+GetEmployeeTasks.EmployeeTasks.Length+\" new tasks\"" Example="You have 3 new tasks"
      [Placeholder: Content]
        [137] BlockInstance 'SidebarTaskInstance' SourceBlock="SidebarTask" EmployeeTasks="GetEmployeeTasks.EmployeeTasks"
        [138] BlockInstance 'SidebarChatInstance' SourceBlock="SidebarChat" UserPicture="GetLoginUserPicture.List.Current.EmployeePicture.PictureBinary"
  [Placeholder: Footer]
    [139] Popup 'AssigningPopup' ShowPopup="ShowAssigningPopup" Style="\"popup-dialog\""
      [140] Container
        [141] Container Style="\"heading4\"" Width="11 col"
          [142] Text CustomStyle="font-size: 20px;" Text="Assign Request"
        [143] Container CustomStyle="text-align: right;" Width="1 col"
          [144] Link OnClick=ToggleAssigningPopup Transition=Fade
            [145] BlockInstance 'HBIconInstance6' SourceBlock="HBIcon"
              [Placeholder: IconName]
                [146] Text Text="close"
      [147] Container Style="\"margin-top-m\""
        [148] Label TargetWidget=Dropdown3
          [149] Text Text="Assign to"
        [150] Dropdown 'Dropdown3' Mode=Text List="GetAssignedEmployees.List" Values="EmployeeId" Labels="EmployeeName" Variable="SelectedEmployeeIdToAssign" EmptyValue="\"Select\"" OnChange=AssigningEmpOnChange Transition=Fade
      [151] Container CustomStyle="text-align: right;" Style="\"margin-top-xxl\""
        [152] Button Style="\"btn\"" Text="Cancel" OnClick=ToggleAssigningPopup Transition=Fade
        [153] Button Style="\"btn btn-primary\"" Text="Assign" OnClick=SubmitAssigningOnClick Transition=Fade
    [154] If Condition="False"
      [FalseBranch]
        [155] If 'Firebase_configured' Condition="FirebaseData.Firebase_ProjectId <> \"\" and FirebaseData.Firebase_DatabaseURL <> \"\""
          [TrueBranch]
            [156] BlockInstance 'FirebaseReceiverInstance' SourceBlock="FirebaseReceiver" TargetIdentifier="FirebaseData.Firebase_TargetIdentifier+\"_\"+GetUserId()" Token="FirebaseData.Firebase_Token" FBDatabaseURL="FirebaseData.Firebase_DatabaseURL" ProjectId="FirebaseData.Firebase_ProjectId" AlertEventReceived=FirebaseReceiverAlertEventReceived(FirebaseEvent=FirebaseEvent, IsAgents=False) MissingData=FirebaseReceiverMissingData
            [157] BlockInstance 'FirebaseReceiverInstance2' SourceBlock="FirebaseReceiver" TargetIdentifier="FirebaseData.Firebase_TargetIdentifier+\"_\"+GetUserId()+\"_agents\"" Token="FirebaseData.Firebase_Token" ProjectId="FirebaseData.Firebase_ProjectId" FBDatabaseURL="FirebaseData.Firebase_DatabaseURL" AlertEventReceived=FirebaseReceiverAlertEventReceived(FirebaseEvent=FirebaseEvent, IsAgents=True) MissingData=FirebaseReceiverMissingData
```