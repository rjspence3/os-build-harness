```
=== Screen: RequestDetail ===
Inputs: RequestId:LoanRequest Identifier (mandatory), IsSidebarOpen:Boolean (default=True)
Locals: ShowNewNoteForm:Boolean, SelectedLogId:HistoryLog Identifier, ShowRejectionPopup:Boolean,
        isResubmission:Boolean (default=False), NotificationCount:Integer, IsEnrichmentAgentCompleted:Boolean (default=True),
        IsRequestCompleted:Boolean, HasCreditScore:Boolean, LoadingDateTime:DateTime (default=CurrDateTime()), ShowSSN:Boolean (default=False)
Aggregates: GetAgentsResponsesByRequestId, GetCustomerLoansById, GetDocuments, GetLogById (OnDemand),
            GetLoginUserPicture, GetLogsByRequestId, GetLogsNotes, GetRequestById
--- WIDGETS (hierarchical) ---
[1] BlockInstance 'LayoutSideMenuBanner' Source=LayoutSideMenuBanner
  [Navigation placeholder]
    [2] BlockInstance 'Menu' Source=Menu
  [Header placeholder]
    [3] BlockInstance 'Header' Source=Header HasAIChat="True" NotificationCount="NotificationCount"
  [Breadcrumbs placeholder]
    [4] BlockInstance 'Breadcrumbs' Source=Breadcrumbs
      [Content placeholder]
        [5] BlockInstance 'BreadcrumbsItem' Source=BreadcrumbsItem
          [Title placeholder]
            [6] Link OnClick→Dashboard
              [7] Text "Home"
          [Icon placeholder]
            [8] Icon icon="angle-right"
        [9] BlockInstance 'BreadcrumbsItem' Source=BreadcrumbsItem
          [Title placeholder]
            [10] Expression Value="GetLabelByLocale(GetRequestById.List.Current.LoanRequestType.LabelLocale, Client.LocaleId) +\" Request \"+FormatText(LongIntegerToText(RequestId),4,20,True,0)"
  [Title placeholder]
    [11] Container
      [12] BlockInstance 'AlignCenter' Source=AlignCenter ExtendedClass="\"flex-wrap gap-base\""
        [Content placeholder]
          [13] Container Width="(fill parent)"
            [14] Expression Style="\"heading4 margin-right-s white-space-nowrap\"" Value="GetRequestById.List.Current.HBCustomer.Name"
            [15] Expression Style="\"text-neutral-7 line-height1\"" Value="\"Request ID \"+FormatText(LongIntegerToText(GetRequestById.List.Current.LoanRequest.Id),4,20,True,0)"
          [16] BlockInstance 'Tag' Source=Tag Color="Entities.Color.Neutral4"
            [Tag placeholder]
              [17] Expression Style="\"text-neutral-8 white-space-nowrap\"" Value="GetLabelByLocale(GetRequestById.List.Current.LoanRequestType.LabelLocale, Client.LocaleId)"
          [18] BlockInstance 'Tag' Source=Tag Color="TextToIdentifier(GetRequestById.List.Current.LoanRequestStatus.Color)"
            [Tag placeholder]
              [19] Expression Style="\"white-space-nowrap\"" Value="GetLabelByLocale(GetRequestById.List.Current.LoanRequestStatus.LabelLocale, Client.LocaleId)"
  [Details placeholder]
    [20] Container Style="\"margin-right-l margin-top-s\""
      [21] Label Text="Card ID"
      [22] Expression Style="\"font-semi-bold\"" Value="GetRequestById.List.Current.HBCustomer.CardID"
    [23] Container Style="\"margin-right-l margin-top-s\""
      [24] Label Text="SSN"
      [25] BlockInstance 'AlignCenter' Source=AlignCenter
        [Content placeholder]
          [26] Expression Style="\"font-semi-bold\"" Value="If(ShowSSN, HBCustomer.SSN, \"***-**-\"+Substr(...))"
          [27] Link Style="\"margin-left-xs\"" OnClick→ToggleHideSSNOnClick
            [28] IfWidget Condition="ShowSSN"
              [TrueBranch]
                [29] BlockInstance 'HBIcon' Source=HBIcon
                  [IconName placeholder] Text="eyehide"
              [FalseBranch]
                [30] BlockInstance 'HBIcon' Source=HBIcon
                  [IconName placeholder] Text="eyeshow"
    [31] Container Style="\"margin-right-l margin-top-s\""
      [32] Label Text="Birth Date"
      [33] Expression Style="\"font-semi-bold\"" Value="FormatDateLocale(GetRequestById.List.Current.HBCustomer.BirthDate, Client.LocaleId)"
    [34] Container Style="\"margin-right-l margin-top-s\""
      [35] Label Text="Phone"
      [36] Expression Style="\"font-semi-bold\"" Value="GetRequestById.List.Current.HBCustomer.Mobile"
    [37] Container Style="\"margin-right-l margin-top-s\""
      [38] Label Text="Email"
      [39] Link OnClick→RedirectToURL URL="\"mailto:\"+HBCustomer.Email"
        [40] Expression Style="\"font-semi-bold\"" Value="GetRequestById.List.Current.HBCustomer.Email"
    [41] Container Style="\" margin-top-s\""
      [42] Label Text="Address"
      [43] Expression Style="\"font-semi-bold\"" Value="\"{ADDRESS}\""
  [Wizard placeholder]
    [44] BlockInstance 'Wizard' Source=Wizard IsVertical=null
      [Content placeholder]
        [45] BlockInstance 'WizardItem' Source=WizardItem Status="If(Pending or WaitResubmission, Active, Past)"
          [Icon placeholder]
            [46] IfWidget Condition="StatusId=Pending or WaitResubmission"
              [TrueBranch] Text "1"
              [FalseBranch] Image Source=ChekMarkGreen Width="24px"
          [Label placeholder] Text "Application Submission"
        [47] BlockInstance 'WizardItem' Source=WizardItem Status="If(Pending/WaitResubmission→Next, Submitted→Active, else Past)"
          [Icon placeholder]
            [48] IfWidget Condition="Submitted or Pending or WaitResubmission"
              [TrueBranch] Text "2"
              [FalseBranch] Image Source=ChekMarkGreen Width="24px"
          [Label placeholder] Text "Intake Validation"
        [49] BlockInstance 'WizardItem' Source=WizardItem Status="If(Pending/Submitted/WaitResubmission→Next, InProgress+notEnrichment→Active, else Past)"
          [Icon placeholder]
            [50] IfWidget Condition="Pending/WaitResubmission/Submitted or (InProgress and not IsEnrichmentAgentCompleted)"
              [TrueBranch] Text "3"
              [FalseBranch] Image Source=ChekMarkGreen Width="24px"
          [Label placeholder] Text "Enrich Profile"
        [51] BlockInstance 'WizardItem' Source=WizardItem Status="If(Pending/Submitted/WaitResubmission/InProgress+notEnrichment→Next, Approved/Rejected→Past, else Active)"
          [Icon placeholder]
            [52] IfWidget Condition="not (Approved or Rejected)"
              [TrueBranch] Text "4"
              [FalseBranch] Image Source=ChekMarkGreen Width="24px"
          [Label placeholder] Text "Underwriter Policies"
        [53] BlockInstance 'WizardItem' Source=WizardItem Status="If(IsRequestCompleted→Past, Approved/Rejected→Active, else Next)"
          [Icon placeholder]
            [54] IfWidget Condition="not IsRequestCompleted"
              [TrueBranch] Text "5"
              [FalseBranch] Image Source=ChekMarkGreen Width="24px"
          [Label placeholder] Text "Communicate Decision"
  [MainContent placeholder]
    [55] IfWidget Condition="StatusId=Pending or WaitResubmission or (Submitted and isResubmission)"
      [TrueBranch]
        [56] Container Style="\"margin-bottom-xl\""
          [57] BlockInstance 'RequestNotification' Source=RequestNotification isResubmission="isResubmission" RequestStatusId="...StatusId"
      [FalseBranch] (empty)
    [58] BlockInstance 'tabs' Source=Tabs OptionalConfigs="{ ContentAutoHeight: True, JustifyHeaders: True }"
      [Header placeholder]
        [59] BlockInstance 'TabsHeaderItem' Source=TabsHeaderItem ExtendedClass="If(HasCreditScore,\"\",\"display-none\")"
          [Title placeholder] Text "Credit Profile"
        [60] BlockInstance 'TabsHeaderItem' Source=TabsHeaderItem
          [Title placeholder] Text "General Information"
        [61] BlockInstance 'TabsHeaderItem' Source=TabsHeaderItem
          [Title placeholder] Text "Documents"
        [62] BlockInstance 'TabsHeaderItem' Source=TabsHeaderItem
          [Title placeholder] Text "Notes"
        [63] BlockInstance 'TabsHeaderItem' Source=TabsHeaderItem
          [Title placeholder] Text "History Log"
      [Content placeholder]
        --- TAB 1: Credit Profile ---
        [64] BlockInstance 'TabsContentItem' Source=TabsContentItem
          [Content placeholder]
            [65] Container Style="\"display-grid \"+If(IsPhone(),\"gap-base\",\"gap-mbase\")"
              [66] Container (row 1)
                [67] BlockInstance 'Columns3' Source=Columns3 PhoneBehavior=BreakAll GutterSize=Base
                  [Column1]
                    [68] Container Style="\"card\""
                      [69] Container Style="\"heading6\"" Text="Credit Score"
                      [70] Container CustomStyle="height:220px"
                        [71] Container
                          [72] IfWidget Condition="HasCreditScore"
                            [TrueBranch]
                              [73] BlockInstance 'CreditScore' Source=CreditScore CreditScore="...LoanRequest.CreditScore"
                                [Legend placeholder]
                                  [74] BlockInstance 'Columns2' Source=Columns2
                                    [Column1]
                                      [75] Container Style="\"text-neutral-7 white-space-nowrap\"" CustomStyle="text-align:left"
                                        [76] BlockInstance 'HBIcon' [IconName="location"]
                                        [77] Text "City Peers" Style="\"margin-left-xs\""
                                      [78] Container Style="\"loan-percentage\""
                                        [79] Text "645 "
                                        [80] Text "Fair" Style="\"text-blue font-regular font-size-s\""
                                    [Column2]
                                      [81] Container Style="\"text-neutral-7\""
                                        [82] BlockInstance 'AlignCenter'
                                          [Content placeholder]
                                            [83] BlockInstance 'HBIcon' [IconName="global"]
                                            [84] Text "National Average" Style="\"margin-left-xs white-space-nowrap\""
                                      [85] Container Style="\"loan-percentage\"" CustomStyle="text-align:left"
                                        [86] Text "590 "
                                        [87] Text "Fair" Style="\"text-blue font-regular font-size-s\""
                            [FalseBranch] (empty)
                  [Column2]
                    [88] Container Style="\"card\""
                      [89] Container Style="\"heading6\"" Text="Debt Graph"
                      [90] Container CustomStyle="height:220px"
                        [91] Container
                          [92] IfWidget Condition="HasCreditScore"
                            [TrueBranch]
                              [93] BlockInstance 'DebtGraph' Source=DebtGraph CreditCard=CreditCardDebtPercentage Mortgage=MortgageDebtPercentage CarLoan=AutoLoanDebtPercentage TotalDebt=TotalDept
                                [Legend placeholder]
                                  [94] Container
                                    [95] Container Width="4 col" CustomStyle="text-align:left"
                                      [96] Container
                                        [97] BlockInstance 'AlignCenter'
                                          [Content placeholder]
                                            [98] Icon icon="circle" Style="\"icon font-size-xs margin-right-xs text-violet\""
                                            [99] Text "Mortgage" Style="\"white-space-nowrap\""
                                        [100] Container Style="\"loan-percentage\"" CustomStyle="text-align:left"
                                          [101] Expression Value="MortgageDebtPercentage+\"%\""
                                    [102] Container Width="4 col"
                                      [103] Container CustomStyle="text-align:left"
                                        [104] BlockInstance 'AlignCenter'
                                          [Content placeholder]
                                            [105] Icon icon="circle" Style="\"icon font-size-xs margin-right-xs text-cyan\""
                                            [106] Text "Car Loan" Style="\"white-space-nowrap\""
                                        [107] Container Style="\"loan-percentage\"" CustomStyle="text-align:left"
                                          [108] Expression Value="AutoLoanDebtPercentage+\"%\""
                                    [109] Container Width="4 col" CustomStyle="text-align:left"
                                      [110] BlockInstance 'AlignCenter'
                                        [Content placeholder]
                                          [111] Icon icon="circle" Style="\"icon font-size-xs margin-right-xs text-orange\""
                                          [112] Text "Credit Card" Style="\"white-space-nowrap\""
                                      [113] Container Style="\"loan-percentage\"" CustomStyle="text-align:left"
                                        [114] Expression Value="CreditCardDebtPercentage+\"%\""
                            [FalseBranch] (empty)
                  [Column3]
                    [115] Container Style="\"card\""
                      [116] Container Style="\"heading6\"" Text="Overview"
                      [117] Container 'Mortgage' Style="\"margin-top-base\""
                        [118] Container
                          [119] Container Width="10 col" Text="Mortgage"
                          [120] Container Width="2 col" CustomStyle="text-align:right"
                            [121] Expression Style="\"font-semi-bold\"" Value="MortgageDebtPercentage+\"%\""
                        [122] Container Style="\"margin-y-s\""
                          [123] BlockInstance 'ProgressBar' Source=ProgressBar Progress=MortgageDebtPercentage Color=Violet Thickness="4" ExtendedClass="\"overview-progress-bar\""
                        [124] Container Style="\"font-size-xs\""
                          [125] BlockInstance 'Columns2' GutterSize=None
                            [Column1] Text "26% less" + " than city avg"
                            [Column2] Text "52% less " + "than national avg"
                      [126] Container 'CarLoan' Style="\"margin-top-20\""
                        [127] Container
                          [128] Container Width="10 col" Text="Car Loan"
                          [129] Container Width="2 col" CustomStyle="text-align:right"
                            [130] Expression Style="\"font-semi-bold\"" Value="AutoLoanDebtPercentage+\"%\""
                        [131] Container Style="\"margin-y-s\""
                          [132] BlockInstance 'ProgressBar' Source=ProgressBar Progress=AutoLoanDebtPercentage Color=Cyan Thickness="4" ExtendedClass="\"overview-progress-bar\""
                        [133] Container Style="\"font-size-xs\""
                          [134] BlockInstance 'Columns2' GutterSize=None
                            [Column1] Text "25% more" + " than city avg"
                            [Column2] Text "33% less " + "than national avg"
                      [135] Container 'CreditCard' Style="\"margin-top-20\""
                        [136] Container
                          [137] Container Width="10 col" Text="Credit Card"
                          [138] Container Width="2 col" CustomStyle="text-align:right"
                            [139] Expression Style="\"font-semi-bold\"" Value="CreditCardDebtPercentage+\"%\""
                        [140] Container Style="\"margin-y-s\""
                          [141] BlockInstance 'ProgressBar' Source=ProgressBar Progress=CreditCardDebtPercentage Color=Orange Thickness="4" ExtendedClass="\"overview-progress-bar\""
                        [142] Container Style="\"font-size-xs\""
                          [143] BlockInstance 'Columns2' GutterSize=None
                            [Column1] Text "15% more" + " than city avg"
                            [Column2] Text "48% less " + "than national avg"
              [144] Container (row 2)
                [145] BlockInstance 'Columns3' Source=Columns3 PhoneBehavior=BreakAll GutterSize=Base
                  [Column1]
                    [146] Container Style="\"card\""
                      [147] Container
                        [148] Container Width="7 col" Style="\"heading6\""
                          [149] Container Text="Payment History"
                          [150] Container Style="\"font-size-base margin-top-s\""
                            [151] Expression Value="OnTimePaymentPercentage+\"%\""
                        [152] Container Width="5 col" CustomStyle="text-align:right"
                          [153] BlockInstance 'Tag' Color=Green IsLight=True Size=Small
                            [Tag placeholder] Text "Low Impact"
                      [154] BlockInstance 'Separator'
                      [155] Container Style="\"text-neutral-7\"" Text="Payment history tracks past payments..."
                  [Column2]
                    [156] Container Style="\"card\""
                      [157] Container
                        [158] Container Width="7 col" Style="\"heading6\""
                          [159] Container Text="Credit Card Use"
                          [160] Container Style="\"font-size-base margin-top-s\""
                            [161] Expression Value="CreditCardUsePercentage+\"%\""
                        [162] Container Width="5 col" CustomStyle="text-align:right"
                          [163] BlockInstance 'Tag' Color=Yellow IsLight=True Size=Small
                            [Tag placeholder] Text "Medium Impact"
                      [164] BlockInstance 'Separator'
                      [165] Container Style="\"text-neutral-7\"" Text="Credit card use is borrowing funds..."
                  [Column3]
                    [166] Container Style="\"card\""
                      [167] Container
                        [168] Container Width="7 col" Style="\"heading6\""
                          [169] Container Text="Derogatory Marks"
                          [170] Container Style="\"font-size-base margin-top-s\""
                            [171] Expression Value="DerogatoryMarksCount"
                        [172] Container Width="5 col" CustomStyle="text-align:right"
                          [173] BlockInstance 'Tag' Color=Green IsLight=True Size=Small
                            [Tag placeholder] Text "Low Impact"
                      [174] BlockInstance 'Separator'
                      [175] Container Style="\"text-neutral-7\"" Text="Derogatory marks are negative items..."
              [176] Container (row 3)
                [177] BlockInstance 'Columns3' Source=Columns3 PhoneBehavior=BreakAll GutterSize=Base
                  [Column1]
                    [178] Container Style="\"card\""
                      [179] Container
                        [180] Container Width="7 col" Style="\"heading6\""
                          [181] Container Text="Account Age"
                          [182] Container Style="\"font-size-base margin-top-s\""
                            [183] Expression Value="AverageAccountAgeYears+\"y\""
                        [184] Container Width="5 col" CustomStyle="text-align:right"
                          [185] BlockInstance 'Tag' Color=Yellow IsLight=True Size=Small
                            [Tag placeholder] Text "Medium Impact"
                      [186] BlockInstance 'Separator'
                      [187] Container Style="\"text-neutral-7\"" Text="Account age is the length of time..."
                  [Column2]
                    [188] Container Style="\"card\""
                      [189] Container
                        [190] Container Width="7 col" Style="\"heading6\""
                          [191] Container Text="Total Account"
                          [192] Container Style="\"font-size-base margin-top-s\""
                            [193] Expression Value="TotalInquiriesCount"
                        [194] Container Width="5 col" CustomStyle="text-align:right"
                          [195] BlockInstance 'Tag' Color=Red IsLight=True Size=Small
                            [Tag placeholder] Text "High Impact"
                      [196] BlockInstance 'Separator'
                      [197] Container Style="\"text-neutral-7\"" Text="Total accounts are the number of credit accounts..."
                  [Column3]
                    [198] Container Style="\"card\""
                      [199] Container
                        [200] Container Width="7 col" Style="\"heading6\""
                          [201] Container Text="Inquiries"
                          [202] Container Style="\"font-size-base margin-top-s\""
                            [203] Expression Value="CreditInquiries"
                        [204] Container Width="5 col" CustomStyle="text-align:right"
                          [205] BlockInstance 'Tag' Color=Green IsLight=True Size=Small
                            [Tag placeholder] Text "Low Impact"
                      [206] BlockInstance 'Separator'
                      [207] Container Style="\"text-neutral-7\"" Text="Inquiries are requests to check your credit report..."
        --- TAB 2: General Information ---
        [208] BlockInstance 'TabsContentItem' Source=TabsContentItem
          [Content placeholder]
            [209] IfWidget Condition="LoanRequest.CustomerLoanId <> NullIdentifier()"
              [TrueBranch]
                [210] Container Style="\"margin-bottom-l\""
                  [211] Container Text="Loan Details" Style="\"heading6\""
                  [212] Container Style="\"card margin-top-m\""
                    [213] Container
                      [214] BlockInstance 'Columns5' PhoneBehavior=BreakAll
                        [Column1] Label="Loan " + Expression Value="LoanRequestType.LabelLocale"
                        [Column2] Label="Loan Amount" + Expression Value="FormatCurrencyCustom(CustomerLoan.Amount,2)"
                        [Column3] Label="Term" + Expression Value="PeriodMonth+\" months\""
                        [Column4] Label="Interest rate" + Expression Value="InterestRatePercentage+\"% p.a.\""
                        [Column5] Label="Monthly Payment" + Expression Value="FormatCurrency(...)"
                    [215] Container Style="If(IsPhone(),\"margin-top-base\",\"margin-top-l\")"
                      [216] BlockInstance 'Columns5' PhoneBehavior=BreakAll
                        [Column1] Label="Total Amount to Pay" + Expression Value="FormatCurrencyCustom(...)"
                        [Column2] Label="Account Destination" + Expression Value="ProductType.LabelLocale+\" \"+Substr(AccountNumber,...)"
                        [Column3] Label="Life Insurance" + Expression Value="If(IncludeLifeInsurance,...)"
              [FalseBranch] (empty)
            [217] Container
              [218] Container Text="Financial Information" Style="\"heading6\""
              [219] Container Style="\"card margin-top-m\""
                [220] Container
                  [221] BlockInstance 'Columns5' PhoneBehavior=BreakAll
                    [Column1] Label="Client Since" + Expression Value="FormatDateLocale(HBCustomer.ClientSince,...)"
                    [Column2] Label="Branch" + Expression Value="HBBranch.Name"
                    [Column3] Label="Employment Status" + Expression Value="HBCustomer.EmploymentStatus"
                    [Column4] Label="Employer Name" + Expression Value="HBCustomer.EmployerName"
                    [Column5] Label="Position" + Expression Value="HBCustomer.Position"
                [222] Container Style="If(IsPhone(),\"margin-top-base\",\"margin-top-l\")"
                  [223] BlockInstance 'Columns5' PhoneBehavior=BreakAll
                    [Column1] Label="Employment Start Date" + Expression Value="FormatDateLocale(HBCustomer.EmploymentStartDate,...)"
                    [Column2] Label="Annual Income" + Expression Value="FormatCurrencyCustom(HBCustomer.AnnualIncome,2)"
                    [Column3] Label="Other Source of Income" + Expression Value="HBCustomer.OtherSourceofIncome"
                    [Column4] Label="Home Ownership" + Expression Value="HBCustomer.HomeOwnership"
                    [Column5] Label="Credit Category"
                      [224] BlockInstance 'CreditCateg{NAME}' Source=CreditCategories CreditScore="HBCustomer.CreditScore"
        --- TAB 3: Documents ---
        [225] BlockInstance 'TabsContentItem' Source=TabsContentItem
          [Content placeholder]
            [226] Container Text="Documents" Style="\"heading6\""
            [227] Container Style="\"card margin-top-m\"" Width="7 col"
              [228] IfWidget Condition="GetDocuments.List.Empty"
                [TrueBranch]
                  [229] Container Style="\"margin-top-m\""
                    [230] BlockInstance 'BlankSlate' Source=BlankSlate
                      [Icon placeholder]
                        [231] BlockInstance 'HBIcon' [IconName="document"]
                      [Content placeholder] Text "There aren't any documents to show."
                [FalseBranch]
                  [232] List Source="GetDocuments.List" Style="\"list list-group\""
                    [233] ListItem 'ListItem2'
                      [Content]
                        [234] Container Width="6 col"
                          [235] Link Style="text-decoration:underline" OnClick→DownloadDocumentOnClick DocumentId="GetDocuments.List.Current.HBDocument.Id"
                            [236] Expression Value="HBDocument.FileName"
                        [237] Container Width="6 col" CustomStyle="text-align:right"
                          [238] Expression Style="\"text-neutral-7\"" Value="\"Uploaded: \"+FormatDateLocale(...)+\" \"+FormatTimeLocale(...)"
        --- TAB 4: Notes ---
        [239] BlockInstance 'TabsContentItem' Source=TabsContentItem
          [Content placeholder]
            [240] Container Width="7 col"
              [241] Container Text="Notes" Style="\"heading5\""
              [242] Container Style="\"card margin-top-m\""
                [243] Container Style="\"font-semi-bold text-primary display-flex justify-content-space-between\""
                  [244] Container Style="\"display-flex gap-base\""
                    [245] Container
                      [246] Link Style="\"no-text-decoration\"" OnClick→NotImplemented
                        [247] BlockInstance 'AlignCenter'
                          [Content placeholder]
                            [248] BlockInstance 'HBIcon' [IconName="filtersearch"]
                            [249] Text "Filter" Style="\"margin-left-xs\""
                    [250] Container
                      [251] Link Style="\"no-text-decoration\"" OnClick→NotImplemented
                        [252] BlockInstance 'AlignCenter'
                          [Content placeholder]
                            [253] BlockInstance 'HBIcon' [IconName="search"]
                            [254] Text "Search" Style="\"margin-left-xs\""
                  [255] Container CustomStyle="text-align:right"
                    [256] Link Style="\"no-text-decoration\"" Enabled="not ShowNewNoteForm" OnClick→AddNewNoteOnClick
                      [257] BlockInstance 'AlignCenter'
                        [Content placeholder]
                          [258] BlockInstance 'HBIcon' [IconName="plus"]
                          [259] Text "New Note" Style="\"margin-left-xs\""
                [260] BlockInstance 'Separator'
                [261] Container Visible="ShowNewNoteForm" Animate=true
                  [262] Form 'Form1' Style="\"form card\""
                    [263] Container
                      [264] Container
                        [265] Container Width="6 col"
                          [266] BlockInstance 'AlignCenter'
                            [Content placeholder]
                              [267] BlockInstance 'UserAvatar' Image="EmployeePicture.PictureBinary" Name="Client.UserName" Size=Small
                              [268] Expression Style="\"white-space-nowrap\"" Value="Client.UserName"
                        [269] Container Width="6 col" CustomStyle="text-align:right"
                          [270] Expression Style="\"text-neutral-7\"" Value="FormatDateLocale(CurrDate(),...)+\" \"+FormatTimeLocale(...)"
                      [271] Container Style="\"margin-top-s\""
                        [272] TextArea 'TextArea_Comment' Variable="GetLogById.List.Current.HistoryLog.Comment" MaxLength=1500 Prompt="\"Type your comment here\""
                    [273] Container CustomStyle="text-align:right"
                      [274] Container
                        [275] Button Style="\"btn btn-transparent\"" IsDefault=true OnClick→ToggleAddNoteOnClick Text="Cancel"
                        [276] Button Style="\"btn btn-primary\"" Enabled="GetLogById.List.Current.HistoryLog.Comment<>\"\"" OnClick→RequestAddNote Text="Submit"
                  [277] BlockInstance 'Separator'
                [278] IfWidget Condition="GetLogsNotes.List.Empty"
                  [TrueBranch]
                    [279] Container Style="\"margin-top-m\""
                      [280] BlockInstance 'BlankSlate'
                        [Icon placeholder]
                          [281] BlockInstance 'HBIcon' [IconName="contactus"]
                        [Content placeholder] Text "There aren't any comments to show."
                  [FalseBranch]
                    [282] List Source="GetLogsNotes.List" Style="\"list list-group\""
                      [283] ListItem 'ListItem1'
                        [Content]
                          [284] Container Width="6 col"
                            [285] IfWidget 'IsHuman' Condition="User.Id <> NullTextIdentifier()"
                              [TrueBranch]
                                [286] BlockInstance 'AlignCenter'
                                  [Content placeholder]
                                    [287] BlockInstance 'UserAvatar' Image="EmployeePicture.PictureBinary" Name="User.Name" Size=Small
                                    [288] Expression Style="\"white-space-nowrap\"" Value="User.Name"
                              [FalseBranch]
                                [289] BlockInstance 'AlignCenter'
                                  [Content placeholder]
                                    [290] Container Style="\"avatar avatar-small border-radius-rounded background-primary\""
                                      [291] BlockInstance 'AgentIcon' AgentTypeId="HistoryLog.AgentTypeId"
                                    [292] Expression Style="\"margin-left-s\"" Value="GetLabelByLocale(HBAgentType.LabelLocale,...)"
                          [293] Container Width="6 col" CustomStyle="text-align:right"
                            [294] Expression Style="\"text-neutral-7\"" Value="FormatDateLocale(HistoryLog.CreatedOn,...)+\" \"+FormatTimeLocale(...)"
                          [295] Container Style="\"margin-top-s\""
                            [296] IfWidget Condition="HistoryLog.AgentTypeId <> NullIdentifier()"
                              [TrueBranch]
                                [297] BlockInstance 'MarkdownFormat' Text="GetLogsNotes.List.Current.Note"
                              [FalseBranch]
                                [298] Expression Value="GetLogsNotes.List.Current.Note"
                            [299] Link Visible="HistoryLog.CreatedBy=GetUserId()" Enabled="not ShowNewNoteForm" OnClick→EditNoteOnClick LogId="HistoryLog.Id"
                              [300] Container CustomStyle="padding:3px 0px 0px 0px"
                                [301] BlockInstance 'HBIcon' [IconName="edit"]
        --- TAB 5: History Log ---
        [302] BlockInstance 'TabsContentItem' Source=TabsContentItem
          [Content placeholder]
            [303] Container Width="7 col"
              [304] Container Text="History Log" Style="\"heading5\""
              [305] Container Style="\"card margin-top-m\""
                [306] List Source="GetLogsByRequestId.List" Style="\"list list-group\""
                  [307] BlockInstance 'TimelineItem' Source=TimelineItem
                    [Title placeholder]
                      [308] Expression Style="\"text-neutral-8 font-regular\"" Value="FormatDateLocale(HistoryLog.CreatedOn,...)+\" - \"+FormatTimeLocale(...)"
                    [Content placeholder]
                      [309] Expression Style="\"font-semi-bold margin-right-s\"" Value="[loan/account type + status label]"
                      [310] Container
                        [311] Expression Style="\"text-neutral-8\"" Value="[assigned/closed/comment/agent description]"
                        [312] IfWidget Condition="HistoryLog.AgentTypeId <> NullIdentifier()"
                          [TrueBranch]
                            [313] Container Style="\"activity-item__agent ...\""
                              [314] BlockInstance 'AgentIcon' AgentTypeId="HistoryLog.AgentTypeId"
                              [315] Expression Value="GetLabelByLocale(HBAgentType.LabelLocale,...)"
                          [FalseBranch]
                            [316] Expression Style="\"font-semi-bold text-primary\"" Value="If(User.Id<>Null, User.Name, \"\")"
                      [317] Container 'Comment' Visible="HistoryLog.Comment <> \"\"" Animate=true Style="\"margin-top-20\""
                        [318] Container Style="\"font-semi-bold\""
                          [319] Expression Value="If(IsEmailSent,\"Email\",If(AgentTypeId<>Null,\"Response\",\"Comment\"))"
                        [320] Container
                          [321] IfWidget Condition="HistoryLog.AgentTypeId <> NullIdentifier()"
                            [TrueBranch]
                              [322] BlockInstance 'MarkdownFormat' Text="HistoryLog.Comment"
                            [FalseBranch]
                              [323] Expression Value="HistoryLog.Comment"
                      [324] BlockInstance 'LogDocuments' HistoryLogId="HistoryLog.Id"
    [325] IfWidget Condition="GetFirebaseData.IsDataFetched"
      [TrueBranch]
        [326] BlockInstance 'FirebaseReceiver' Source=FirebaseReceiver Token="GetFirebaseData.Token" FBDatabaseURL="..." TargetIdentifier="..." ProjectId="..."
             OnAlertEventReceived→FirebaseReceiverAlertEventReceived  OnMissingData→FirebaseReceiverMissingData
      [FalseBranch] (empty)

    *** SIDEBAR SUBTREE (IsSidebarOpen input controls StartOpen) ***
    [327] BlockInstance 'AgentSidebar' Source=AgentSidebar RequestId="RequestId" StartOpen="IsSidebarOpen" InputPrompt="\"Ask about this request\""
      [Subtitle placeholder]
        [328] Expression Value="\"Request #\" + RequestId + \" activity\""
      [Content placeholder]
        [329] BlockInstance 'SidebarActivity' Source=SidebarActivity RequestId="RequestId" RequestStatusId="...LoanRequest.StatusId"
             RequestApprovalReason="...LoanRequest.ApprovalReason" AIResponseItems="GetAgentsResponsesByRequestId.List mapTo {...}"
             RequestInfoOptionId="...LoanRequest.RequestInfoOptionId"  OnRefresh→SidebarActivityRefresh
        [330] BlockInstance 'SidebarChat' Source=SidebarChat UserPicture="EmployeePicture.PictureBinary"

    *** MOBILE SIDEBAR SUBTREE (IsPhone=False/disabled, condition hardcoded False) ***
    [331] IfWidget 'IsPhone' Condition="False// isPhone()" DesignMode=ShowFalse
      [TrueBranch]
        [332] Container 'MobileSidebar' Style="\"mobile-sidebar\""
          [333] BlockInstance 'AgentSidebar' Source=Sidebar (OutSystemsUI) StartsOpen=null Direction=null
            [Content placeholder]
              [334] BlockInstance 'AgentSidebar' Source=AgentSidebar RequestId="RequestId" StartOpen="True"
                [Subtitle placeholder]
                  [335] Expression Value="\"Request #\" + RequestId + \" activity\""
                [Content placeholder]
                  [336] BlockInstance 'SidebarActivity' Source=SidebarActivity RequestId="RequestId" ...  OnRefresh→SidebarActivityRefresh
                  [337] BlockInstance 'SidebarChat' Source=SidebarChat UserPicture="EmployeePicture.PictureBinary"
      [FalseBranch] (empty)

  [Footer placeholder]
    [338] Popup 'RejectionPopup' ShowPopup="ShowRejectionPopup" Style="\"popup-dialog\""
      [339] Container
        [340] Container Width="11 col" Style="\"heading6\"" Text="Are you sure you want to reject?"
        [341] Container Width="1 col" CustomStyle="text-align:right"
          [342] Link OnClick→ToggleRejectionPopup (Fade)
            [343] BlockInstance 'HBIcon' [IconName="close"]
      [344] Form 'FormRejection2' Style="\"form\""
        [345] Container Style="\"margin-top-m\""
          [346] Container Style="\"margin-top-s\""
            [347] Label Text="Comment" TargetWidget=TextArea_ApprovalReason
            [348] TextArea 'TextArea_ApprovalReason' Variable="GetRequestById.List.Current.LoanRequest.ApprovalReason" MaxLength=500 Prompt="\"Type details here..\""
      [349] Container Style="\"margin-top-m\"" CustomStyle="text-align:right"
        [350] Link Text="Cancel" OnClick→ToggleRejectionPopup (Fade)
        [351] Button Style="\"btn btn-error\"" OnClick→RequestRejected (ValidateAndContinue, Fade) Text="Reject"
```