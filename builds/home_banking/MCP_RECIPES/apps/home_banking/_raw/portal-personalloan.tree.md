```
=== Screen: PersonalLoan ===
Inputs: RequestId:LoanRequest Identifier, StepNo:Integer
Locals: SelectedAccountLabel:Text, TermAndConditionsConfirm:Boolean,
        InitialEffectiveInterestRatePercent:Decimal (default=5.99),
        Title:Text, ShowPopup:Boolean, TempNewComment:Text, NewComment:Text,
        IsPortrait:Boolean, IsShowAdditionalInformation:Boolean,
        DocumentPayStubs:DocumentStructure, DocumentBankStatements:DocumentStructure,
        DocumentIdentification:DocumentStructure, DocumentTaxForm:DocumentStructure,
        IsLoadingSubmit:Boolean
Aggregates: GetAccounts, GetDocuments, GetLoanRequestById, GetLoggedInCustomers
DataActions: FirebaseData (outputs: Firebase_TargetIdentifier, Firebase_Token, Firebase_ProjectId, Firebase_DatabaseURL)
--- WIDGETS (hierarchical) ---
[1] BlockInstance 'LayoutTopMenuLeftSideWithBanner' (LayoutTopMenuLeftSideWithBanner)
      Args: ShowBanner="RequestId <> NullIdentifier()", ExtendedClass="\"loan\""
  [1.Header] BlockInstance 'Menu' (Menu)
  [1.BannerContent] Container CustomStyle="text-align: center;"
    [1.BannerContent.1] Container Style="\"progress-wizard\"" Width="7 col"
      [1.BannerContent.1.1] BlockInstance 'Wizard' (Wizard) Args: IsVertical=null
        [1.BannerContent.1.1.Content]
          [WizardItem 1] BlockInstance (WizardItem) Status="Entities.Steps.Past"
            [Icon] Image CustomStyle="max-width: 40px;" Source=checkmark (static)
            [Label] Text "Application Submission"
          [WizardItem 2] BlockInstance (WizardItem)
              Status=If(StatusId=Submitted→Active, Pending/WaitResubmission→Next, else Past)
            [Icon] IfWidget Condition="StatusId=Submitted or WaitResubmission"
              [True]  BlockInstance HBIcon → Text "checklist" Style="\"heading5\"" CustomStyle="color:#fff"
              [False] Image CustomStyle="max-width: 40px;" Source=checkmark (static)
            [Label] Text "Process Validation"
          [WizardItem 3] BlockInstance (WizardItem)
              Status=If(StatusId=InProgress→Active, Submitted/WaitResubmission→Next, else Past)
            [Icon] IfWidget Condition="StatusId=Approved or Rejected"
              [True]  Image CustomStyle="max-width: 40px;" Source=checkmark (static)
              [False] Image CustomStyle="color:#fff" Source=CheckSquare Style="\"svg-wht\""
            [Label] Text "Final Decision"
  [1.MainContent] Container Style="\"left-side-content\""
    [1.MC.1] Container Style="\"margin-bottom-l\""
      Expression Style="\"font-size-h4 font-semi-bold\"" Value="Title" Example="Personal Loan"
    [1.MC.2] Container Style="\"account-card-hight\""
      Container Style="\"position-absolute\""
        Container Style="\"account-card loancard account-card-width\""
          Container (fill parent)
            Expression Value="Title"
          Container CustomStyle="height:50px" Style="\"font-semi-bold margin-bottom-l\""
            Expression Style="\"font-size-h4\"" Value="Client.Currency" Example="$"
            Expression Style="\"font-size-40\"" Value="FormatCurrency(CustomerLoan.Amount,...)" Example="13.594,34"
          Container Style="\"margin-top-xl\""
            Container Style="\"font-size-xs\""
              Text "Monthly payment"
            Container
              Expression Value="Client.Currency" Example="$"
              Expression Style="\"font-size-h4\"" Value="FormatCurrency(monthly payment formula,...)" Example="13.594,34"
    [1.MC.3] Container Style="\"item-card\""
      Container (Interest rate row)
        Label Style="\"font-size-xs\"" CustomStyle="margin-bottom:0px"
          BlockInstance AlignCenter
            [Content]
              Text "Interest rate"
              Container Style="\"margin-left-s\""
                BlockInstance Tooltip Position=Right Trigger=OnHover
                  [Content] BlockInstance HBIcon → Text "info"
                  [Tooltip] Text "Interest rates are affected by..."
              IfWidget Condition="CustomerLoan.HasSpecialRate"
                [True] BlockInstance Tag Size=Small Color=Cyan ExtendedClass="\"margin-left-12\""
                  [Tag] Text "Discount Rate" Style="\"white-space-nowrap text-wht\""
        Expression Style=If(not HasSpecialRate,"","text-line-through") Value=InterestRatePercentage+"% p.a." Example="2.68% p.a."
        IfWidget Condition="CustomerLoan.HasSpecialRate"
          [True] Expression Style="\"margin-left-s\"" Value="InterestRatePercentage - 0.4 + \"% p.a.\""
      Container Style="\"margin-top-m\"" (Effective Interest rate row)
        Label Style="\"font-size-xs\"" Text "Effective Interest rate"
        Expression Value="EffectiveInterestRatePercent+\"% p.a.\"" Example="5.99% p.a."
      Container Style="\"margin-top-m\"" (Processing fee row)
        Label Style="\"font-size-xs\"" Text "One-time processing fee (1.0%)"
        Expression Value="FormatCurrencyCustom(Amount*(ProcessingFeePercentage/100))" Example="$20.00"
    [1.MC.4] Container Style="\"item-card\"" Visible="False" (Credit Score — hidden)
      Container
        BlockInstance AlignCenter
          [Content]
            Container Style="\"flex-grow-1\""
              Label Style="\"font-size-xs\"" Text "Your Credit Score"
              Expression Value="CreditScore+\" (\"+GetCreditRank(...)+\")\""
            Container CustomStyle="text-align:right"
              BlockInstance ProgressCircle Size="48px" Progress="(CreditScore/850)*100" ProgressColor=Green Thickness=2
                [Content] Expression Style="\"margin-top-xs\"" Value="CreditScore"
      Container Style="\"margin-top-m\""
        Button Style="\"btn btn-transparent-with-border\"" Enabled="True"
          Text "Improve Score"
          BlockInstance HBIcon → Text "improvescore" Style="\"font-size-h4 margin-left-s\""
          OnClick → NotImplemented
    [1.MC.5] IfWidget Condition="False" (Firebase block gate — always False)
      [False] IfWidget 'Firebase_configured' Condition="Firebase_ProjectId<>\"\" and Firebase_DatabaseURL<>\"\""
        [True] BlockInstance FirebaseReceiver
                 Token=FirebaseData.Firebase_Token
                 FBDatabaseURL=FirebaseData.Firebase_DatabaseURL
                 TargetIdentifier=FirebaseData.Firebase_TargetIdentifier
                 ProjectId=FirebaseData.Firebase_ProjectId
                 OnMissingData→FirebaseReceiverMissingData
                 OnAlertEventReceived→FirebaseReceiverAlertEventReceived
  [1.SideContent]
    IfWidget 'PhoneOrTabletPortrait' Condition="If(IsPhone() or (IsTablet() and IsPortrait),True,False)"
      [True] Container 'PhoneView' Style="\"margin-bottom-l\""
        Container Style="\"margin-bottom-l\""
          Expression Style="\"font-size-h4 font-semi-bold\"" Value="Title" Example="Personal Loan"
        Container
          Container 'Card' Style="\"account-card-hight-phone\""
            Container
              Container Style="\"account-card loancard account-card-width\""
                Container → Expression Value="Title"
                Container CustomStyle="height:50px" Style="\"font-semi-bold margin-bottom-l\""
                  Expression Style="\"font-size-h4\"" Value="Client.Currency"
                  Expression Style="\"font-size-40\"" Value="FormatCurrency(Amount,...)"
                Container Style="\"margin-top-xl\""
                  Container Style="\"font-size-xs\"" → Text "Monthly payment"
                  Container
                    Expression Value="Client.Currency"
                    Expression Style="\"font-size-h4\"" Value="FormatCurrency(monthly payment formula,...)"
    Container Width="9 col"
      Container 'Step1' Visible="StepNo=1 and RequestId=NullIdentifier()" Animate=true
        Container
          Container Width="6 col" Style="\"margin-bottom-l\""
            Text "Loan Details" Style="\"font-size-base font-semi-bold\""
          Container Width="6 col" CustomStyle="text-align:right" (empty — placeholder for right-side header)
        Form 'Form1'
          Container 'AmountRange'
            Label "How much do you want to request?"
            Container Style="\"font-semi-bold margin-top-base\""
              Expression Value="Client.Currency" Example="$"
              Expression Style="\"font-size-h4\"" Value="FormatCurrency(Amount,...)" Example="13.594,34"
            Container
              BlockInstance 'AmountRangeSlide' (RangeSlider) Min=500 Max=50000
                OptionalConfigs={Step:100, IsDisabled:Pending/WaitResubmission}
                StartingValue=CustomerLoan.Amount
                OnValueChange→AmountRangeSliderOnValueChange(Value)
              BlockInstance Columns2
                [Column1] Container Style="\"amount-slider-ranges\""
                  Expression Value="FormatCurrencyCustom(500)"
                [Column2] Container Style="\"amount-slider-ranges\"" CustomStyle="text-align:right"
                  Expression Value="FormatCurrencyCustom(50000)"
          Container 'MonthRange' Style="\"margin-top-xxl\""
            Label "For how long?"
            Container Style="\"font-semi-bold margin-top-base\""
              Expression Style="\"font-size-h4 margin-right-xs\"" Value="PeriodMonth" Example="24"
              Text "months"
            Container
              BlockInstance 'MonthRangeSlide' (RangeSlider) Min=12 Max=84
                OptionalConfigs={Step:3, IsDisabled:Pending/WaitResubmission}
                StartingValue=CustomerLoan.PeriodMonth
                OnValueChange→MonthRangeSlideOnValueChange(Value)
              BlockInstance Columns2
                [Column1] Container Style="\"amount-slider-ranges\"" → Expression Value="12"
                [Column2] Container Style="\"amount-slider-ranges\"" CustomStyle="text-align:right" → Expression Value="84"
          Container Style="\"margin-top-xxl\"" (Account dropdown)
            Label "Select the preferred account for the loan transfer."
            Dropdown 'Dropdown5' List="GetAccounts.List" Variable=CustomerLoan.TransferAccountId
              Values="Id" Enabled=not(Pending/WaitResubmission)
              Expression Value="GetLabelByLocale(LabelLocale,LocaleId)+\" \"+last4(AccountNumber)"
          Container Style="\"margin-top-l\"" (Life insurance checkbox)
            Label (AlignCenter)
              [Content]
                Text "Do you want to add some extra coverage?"
                BlockInstance Tooltip ExtendedClass="\"margin-left-s\""
                  [Content] BlockInstance HBIcon → Text "info"
                  [Tooltip] Text "You are not required to purchase additional coverage..."
            Container CustomStyle="padding:10px 16px" Style="\"form-info-field padding-base margin-top-s\""
              BlockInstance AlignCenter
                [Content]
                  Checkbox 'Checkbox1' Variable=CustomerLoan.IncludeLifeInsurance
                    Style="\"checkbox \"+If(CheckRTL()=False,\"\",\"margin-right-s\")"
                    Enabled=not(Pending/WaitResubmission)
                  Container Style="\"white-space-nowrap\""
                    Container Width="auto" → Text "Life insurance" Style="\"margin-right-xs\""
                    Container Width="auto"
                      Expression Style="\"text-neutral-7\"" Value="\" + \"+FormatCurrencyCustom(3)+\"/month\"" Example=" + $3.00/month"
          Container Style="\"margin-top-l\"" (Documents upload section)
            Label "To finalise, we just need a few documents:"
            Container Style="\"document-upload\""
              Container (Pay Stub row)
                BlockInstance ColumnsMediumLeft PhoneBehavior=BreakAll
                  [Column1] Container Style="\"lbl-flex\""
                    Label CustomStyle="margin-bottom:0px"
                      BlockInstance AlignCenter
                        [Content]
                          Text "Pay Stub"
                          BlockInstance Tooltip ExtendedClass="\"margin-left-s\""
                            [Content] BlockInstance HBIcon → Text "info"
                            [Tooltip] Text "Please upload the most recent pay stub."
                  [Column2] Container Style="\"display-flex flex-direction-column\""
                    IfWidget Condition="DocumentPayStubs.ValidationProgressId=Validated and not IsValid"
                      [True] BlockInstance ValidationError ValidationMessage=DocumentPayStubs.ValidationMessage
                    IfWidget Condition="DocumentPayStubs.Binary=NullBinary()"
                      [True] Upload 'UploadPayStubs' FileContent=DocumentPayStubs.Binary FileName=DocumentPayStubs.Filename
                               OnChange→UploadOnChange(DocumentTypeId=PayStubs, Filename, Binary)
                               Expression Value=If(Filename="","Select file",Filename) Style="\"margin-right-base\""
                               Image Source=Attachment Style="\"svg-icon\""
                      [False] BlockInstance DocumentItem FileStructure=DocumentPayStubs
                                OnDeleteFile→DeleteAttachmentOnClick(LoanAttachmentTypeId=PayStubs)
                                OnDownloadFile→DownloadAttachmentOnClick(DocumentId=NullIdentifier(), LoanAttachmentTypeId=PayStubs)
              BlockInstance Separator
              Container (Bank Statement row)
                BlockInstance ColumnsMediumLeft PhoneBehavior=BreakAll
                  [Column1] Container Style="\"lbl-flex\""
                    Label CustomStyle="margin-bottom:0px"
                      BlockInstance AlignCenter
                        [Content]
                          Text "Bank Statement"
                          BlockInstance Tooltip ExtendedClass="\"margin-left-s\""
                            [Content] BlockInstance HBIcon → Text "info"
                            [Tooltip] Text "Please upload the most recent Bank Statement."
                  [Column2] Container Style="\"display-flex flex-direction-column\""
                    IfWidget Condition="DocumentBankStatements.ValidationProgressId=Validated and not IsValid"
                      [True] BlockInstance ValidationError ValidationMessage=DocumentBankStatements.ValidationMessage
                    IfWidget Condition="DocumentBankStatements.Binary=NullBinary()"
                      [True] Upload 'Upload2' FileContent=DocumentBankStatements.Binary
                               OnChange→UploadOnChange(DocumentTypeId=BankStatements, Filename, Binary)
                               Expression Value=If(Filename="","Select file",Filename)
                               Image Source=Attachment Style="\"svg-icon\""
                      [False] BlockInstance DocumentItem FileStructure=DocumentBankStatements
                                OnDeleteFile→DeleteAttachmentOnClick(LoanAttachmentTypeId=BankStatements)
                                OnDownloadFile→DownloadAttachmentOnClick(DocumentId=NullIdentifier(), LoanAttachmentTypeId=BankStatements)
              BlockInstance Separator
              Container (Identification row)
                BlockInstance ColumnsMediumLeft PhoneBehavior=BreakAll
                  [Column1] Container Style="\"lbl-flex\""
                    Label CustomStyle="margin-bottom:0px"
                      BlockInstance AlignCenter
                        [Content]
                          Text "Identification"
                          BlockInstance Tooltip ExtendedClass="\"margin-left-s\""
                            [Content] BlockInstance HBIcon → Text "info"
                            [Tooltip] Text "Upload a copy of a valid ID (e.g., driver license or passport)"
                  [Column2] Container Style="\"display-flex flex-direction-column\""
                    IfWidget Condition="DocumentIdentification.ValidationProgressId=Validated and not IsValid"
                      [True] BlockInstance ValidationError ValidationMessage=DocumentIdentification.ValidationMessage
                    IfWidget Condition="DocumentIdentification.Binary=NullBinary()"
                      [True] Upload 'Upload3' FileContent=DocumentIdentification.Binary
                               OnChange→UploadOnChange(DocumentTypeId=Identification, Filename, Binary)
                               Expression Value=If(Filename="","Select file",Filename)
                               Image Source=Attachment Style="\"svg-icon\""
                      [False] BlockInstance DocumentItem FileStructure=DocumentIdentification
                                OnDeleteFile→DeleteAttachmentOnClick(LoanAttachmentTypeId=Identification)
                                OnDownloadFile→DownloadAttachmentOnClick(DocumentId=NullIdentifier(), LoanAttachmentTypeId=Identification)
              BlockInstance Separator
              Container (Tax Form row)
                BlockInstance ColumnsMediumLeft PhoneBehavior=BreakAll
                  [Column1] Container Style="\"lbl-flex\""
                    Label CustomStyle="margin-bottom:0px"
                      BlockInstance AlignCenter
                        [Content]
                          Text "Tax Form"
                          BlockInstance Tooltip ExtendedClass="\"margin-left-s\""
                            [Content] BlockInstance HBIcon → Text "info"
                            [Tooltip] Text "Upload last year's tax return (form 1040)"
                  [Column2] Container Style="\"display-flex flex-direction-column\""
                    IfWidget Condition="DocumentTaxForm.ValidationProgressId=Validated and not IsValid"
                      [True] BlockInstance ValidationError ValidationMessage=DocumentTaxForm.ValidationMessage
                    IfWidget Condition="DocumentTaxForm.Binary=NullBinary()"
                      [True] Upload 'Upload4' FileContent=DocumentTaxForm.Binary
                               OnChange→UploadOnChange(DocumentTypeId=TaxForm, Filename, Binary)
                               Expression Value=If(Filename="","Select file",Filename)
                               Image Source=Attachment Style="\"svg-icon\""
                      [False] BlockInstance DocumentItem FileStructure=DocumentTaxForm
                                OnDeleteFile→DeleteAttachmentOnClick(LoanAttachmentTypeId=TaxForm)
                                OnDownloadFile→DownloadAttachmentOnClick(DocumentId=NullIdentifier(), LoanAttachmentTypeId=TaxForm)
          Container 'AdditionalInformationPhoneTablet' Style="\"margin-top-base\""
              Visible="If(IsPhone() or (IsTablet() and IsPortrait),True,False)" Animate=true
            Container CustomStyle="text-align:right"
              Link OnClick→ToggleAdditionalInformation (ValidateAndContinue)
                IfWidget Condition="IsShowAdditionalInformation"
                  [True]  Text "Hide Additional Information"
                  [False] Text "Show Additional Information"
            Container Visible="IsShowAdditionalInformation" Animate=true
              Container Style="\"item-card\"" (Interest rate card — phone)
                Container
                  Label Style="\"font-size-xs\""
                    BlockInstance AlignCenter
                      [Content]
                        Text "Interest rate"
                        BlockInstance Tooltip ExtendedClass="\"margin-left-s\""
                          [Content] BlockInstance HBIcon → Text "info"
                          [Tooltip] Text "Interest rates are affected by..."
                  Expression Value="InterestRatePercentage+\"% p.a.\"" Example="2.68% p.a."
                Container Style="\"margin-top-m\""
                  Label Style="\"font-size-xs\"" Text "Effective Interest rate"
                  Expression Value="EffectiveInterestRatePercent+\"% p.a.\"" Example="5.99% p.a."
                Container Style="\"margin-top-m\""
                  Label Style="\"font-size-xs\"" Text "One-time processing fee (1.0%)"
                  Expression Value="FormatCurrencyCustom(Amount*(ProcessingFeePercentage/100))" Example="$20.00"
              Container Style="\"item-card\"" (Credit score card — phone)
                Container
                  BlockInstance AlignCenter
                    [Content]
                      Container Style="\"flex-grow-1\""
                        Label Style="\"font-size-xs\"" Text "Your Credit Score"
                        Expression Value="CreditScore+\" (\"+GetCreditRank(...)+\")\""
                      Container CustomStyle="text-align:right"
                        BlockInstance ProgressCircle Size="48px" Progress="(CreditScore/850)*100" ProgressColor=Green Thickness=2
                          [Content] Expression Style="\"margin-top-xs\"" Value="CreditScore"
                Container Style="\"margin-top-m\""
                  Button Style="\"btn btn-transparent-with-border\""
                    Text "Improve Score"
                    BlockInstance HBIcon → Text "improvescore"
                    OnClick → NotImplemented
          Container Style="\"margin-top-l\"" (Step 1 action buttons)
            Button 'Continue' Style="\"btn btn-primary\"" IsDefault=true
              Enabled=(all 4 docs have Binary<>Null and ValidationProgressId=Validated)
              Text "Continue"
              OnClick→ContinueOnClick (ValidateAndContinue)
            Button 'Cancel' Style="\"btn\""
              Text "Cancel"
              OnClick→Dashboard
      Container 'Step2' Visible="StepNo=2 or RequestId<>NullIdentifier()" Animate=true
        Container Style="\"alert-card\"" Animate=true
            Visible="StatusId=WaitResubmission or Rejected"
          Container Style="\"display-flex\""
            Container Style="\"margin-right-base\""
              IfWidget Condition="StatusId=Rejected"
                [True]  Image Source=infocircle CustomStyle="min-height:24px;min-width:24px"
                [False] BlockInstance HBIcon → Text "alert" CustomStyle="color:#F8BC4C" Style="\"font-size-h4 bold\""
            Container Style="\"flex-grow-1\""
              IfWidget Condition="StatusId=Rejected"
                [True]
                  Label CustomStyle="margin-bottom:4px" Text "Your loan application was declined" Style="\"font-semi-bold font-size-base\""
                  Container → Text "We understand this can be disappointing..."
                [False]
                  Label CustomStyle="margin-bottom:4px" Text "More Information Required" Style="\"font-semi-bold font-size-base\""
                  Container
                    Container → Expression Value="LoanRequest.ApprovalReason" Example="More info"
                    Container Style="\"margin-top-base\""
                      IfWidget 'MissingDocument2' Condition="RequestInfoOptionId=ExplainRequest"
                        [True] IfWidget 'EmptyComment3' Condition="NewComment=\"\""
                          [True] Container CustomStyle="text-align:left"
                            BlockInstance AlignCenter
                              [Content]
                                BlockInstance HBIcon → Text "editsquare" Style="\"font-size-h4\""
                                Link OnClick→TogglePopup
                                  Text "Add comment" CustomStyle="text-decoration:underline" Style="\"white-space-nowrap\""
                          [False] Container Style="\"alert-answer-card\""
                            BlockInstance AlignCenter ExtendedClass="\"align-items-flex-start\""
                              [Content]
                                Container Style="\"flex-grow-1\""
                                  Expression Value="Substr(NewComment,0,120)+If(Length>120,\" ...\",\"\")" Width="auto"
                                    ExtendedProperty title=If(Length>120,NewComment,"")
                                Link OnClick→EditCommentOnClick
                                  BlockInstance HBIcon → Text "delete" Style="\"font-size-h4\""
        IfWidget Condition="RequestId=NullIdentifier()"
          [True]
            Container Style="\"margin-bottom-l\""
              Text "Review and Confirm" Style="\"font-size-base font-semi-bold\""
            Container → Text "Please review all the information bellow before submitting..."
          [False]
            Container Style="\"margin-bottom-l\""
              Text "Loan Details" Style="\"font-size-base font-semi-bold\""
        Container (Loan details summary table)
          Container Style="\"margin-top-base\""
            BlockInstance Columns2
              [Column1] Container → Text "Amount"
              [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
                Expression Value="FormatCurrencyCustom(Amount)" Example="$2.000"
          BlockInstance Separator
          BlockInstance ColumnsMediumRight
            [Column1] Container → Text "Term"
            [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
              Expression Value="PeriodMonth+\" months\"" Example="24 months"
          BlockInstance Separator
          BlockInstance ColumnsMediumRight
            [Column1] Container → Text "Interest rate"
            [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
              Expression Style=If(not HasSpecialRate,"","text-line-through") Value=InterestRatePercentage+"% p.a." Example="2.68% p.a."
              IfWidget Condition="HasSpecialRate"
                [True] Expression Style="\"margin-left-s\"" Value="InterestRatePercentage - 0.4 + \"% p.a.\""
          BlockInstance Separator
          BlockInstance ColumnsMediumRight
            [Column1] Container → Text "Monthly payment"
            [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
              Expression Value="FormatCurrencyCustom(monthly payment formula)" Example="$87.80"
          BlockInstance Separator
          BlockInstance ColumnsMediumRight
            [Column1] Container → Text "Total amount to pay"
            [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
              Expression Value="FormatCurrencyCustom(total formula)" Example="$2,127.20"
          BlockInstance Separator
          BlockInstance ColumnsMediumRight
            [Column1] Container → Text "Effective Interest rate"
            [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
              Expression Value="EffectiveInterestRatePercent+\"% p.a.\"" Example="5.99% p.a."
          BlockInstance Separator
          BlockInstance ColumnsMediumRight
            [Column1] Container → Text "One-time processing fee (1.0%)"
            [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
              Expression Value="FormatCurrencyCustom(Amount*(ProcessingFeePercentage/100))" Example="$20.00"
          BlockInstance Separator
          BlockInstance ColumnsMediumRight
            [Column1] Container → Text "Account destination"
            [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
              Expression Value="SelectedAccountLabel" Example="Checking 4-389"
          BlockInstance Separator
          BlockInstance ColumnsMediumRight
            [Column1] Container → Text "Life Insurance"
            [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
              Expression Value="If(IncludeLifeInsurance,\"+ \"+FormatCurrencyCustom(3),0)+\"/month\"" Example="+ $3.00/month"
          IfWidget Condition="StatusId=WaitResubmission and RequestInfoOptionId=MissingDocument"
            [True] Container Style="\"margin-top-l alert-card\""
              Container → Label "Replace the required documents:"
              Container → Expression Value="LoanRequest.ApprovalReason" Style="\"text-neutral-7\""
              Container Style="\"document-upload margin-top-m\""
                Container (Pay Stub re-upload)
                  BlockInstance ColumnsMediumLeft PhoneBehavior=BreakAll
                    [Column1] Label "Pay Stub" + Tooltip
                    [Column2]
                      IfWidget Condition="DocumentPayStubs.ValidationProgressId=Validated and not IsValid"
                        [True] BlockInstance ValidationError
                      IfWidget Condition="DocumentPayStubs.DocumentId<>Null or Binary<>Null"
                        [True] BlockInstance DocumentItem FileStructure=DocumentPayStubs
                                 OnDeleteFile→DeleteDocumentOnClick(DocumentId=DocumentPayStubs.DocumentId, LoanAttachmentTypeId=PayStubs)
                                 OnDownloadFile→DownloadAttachmentOnClick(DocumentId=DocumentPayStubs.DocumentId, LoanAttachmentTypeId=PayStubs)
                        [False] Upload 'Upload5' OnChange→UploadOnChange(DocumentTypeId=PayStubs)
                  BlockInstance Separator Color=Neutral7
                Container (Bank Statement re-upload)
                  BlockInstance ColumnsMediumLeft PhoneBehavior=BreakAll
                    [Column1] Label "Bank Statement" + Tooltip
                    [Column2]
                      IfWidget Condition="DocumentBankStatements.ValidationProgressId=Validated and not IsValid"
                        [True] BlockInstance ValidationError
                      IfWidget Condition="DocumentBankStatements.DocumentId<>Null or Binary<>Null"
                        [True] BlockInstance DocumentItem FileStructure=DocumentBankStatements
                                 OnDeleteFile→DeleteDocumentOnClick(DocumentId=DocumentBankStatements.DocumentId, LoanAttachmentTypeId=BankStatements)
                                 OnDownloadFile→DownloadAttachmentOnClick(DocumentId=DocumentBankStatements.DocumentId, LoanAttachmentTypeId=BankStatements)
                        [False] Upload 'Upload6' OnChange→UploadOnChange(DocumentTypeId=BankStatements)
                  BlockInstance Separator Color=Neutral7
                Container (Identification re-upload)
                  BlockInstance ColumnsMediumLeft PhoneBehavior=BreakAll
                    [Column1] Label "Identification" + Tooltip
                    [Column2]
                      IfWidget Condition="DocumentIdentification.ValidationProgressId=Validated and not IsValid"
                        [True] BlockInstance ValidationError
                      IfWidget Condition="DocumentIdentification.DocumentId<>Null or Binary<>Null"
                        [True] BlockInstance DocumentItem FileStructure=DocumentIdentification
                                 OnDeleteFile→DeleteDocumentOnClick(DocumentId=DocumentIdentification.DocumentId, LoanAttachmentTypeId=Identification)
                                 OnDownloadFile→DownloadAttachmentOnClick(DocumentId=DocumentIdentification.DocumentId, LoanAttachmentTypeId=Identification)
                        [False] Upload 'Upload7' OnChange→UploadOnChange(DocumentTypeId=Identification)
                  BlockInstance Separator Color=Neutral7
                Container (Tax Form re-upload)
                  BlockInstance ColumnsMediumLeft PhoneBehavior=BreakAll
                    [Column1] Label "Tax Form" + Tooltip
                    [Column2]
                      IfWidget Condition="DocumentTaxForm.ValidationProgressId=Validated and not IsValid"
                        [True] BlockInstance ValidationError
                      IfWidget Condition="DocumentTaxForm.DocumentId<>Null or Binary<>Null"
                        [True] BlockInstance DocumentItem FileStructure=DocumentTaxForm
                                 OnDeleteFile→DeleteDocumentOnClick(DocumentId=DocumentTaxForm.DocumentId, LoanAttachmentTypeId=TaxForm)
                                 OnDownloadFile→DownloadAttachmentOnClick(DocumentId=DocumentTaxForm.DocumentId, LoanAttachmentTypeId=TaxForm)
                        [False] Upload 'Upload8' OnChange→UploadOnChange(DocumentTypeId=TaxForm)
            [False] Container (Read-only document links)
              BlockInstance Separator
              BlockInstance ColumnsMediumRight
                [Column1] Container → Text "Pay Stub"
                [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
                  IfWidget Condition="DocumentPayStubs.DocumentId<>Null or Binary<>Null"
                    [True] Link OnClick→DownloadAttachmentOnClick(LoanAttachmentTypeId=PayStubs, DocumentId=DocumentPayStubs.DocumentId)
                             Expression Value="DocumentPayStubs.Filename" CustomStyle="text-decoration:underline"
                    [False] Text "None"
              BlockInstance Separator
              BlockInstance ColumnsMediumRight
                [Column1] Container → Text "Bank Statement"
                [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
                  IfWidget Condition="DocumentBankStatements.DocumentId<>Null or Binary<>Null"
                    [True] Link OnClick→DownloadAttachmentOnClick(LoanAttachmentTypeId=BankStatements, DocumentId=DocumentBankStatements.DocumentId)
                             Expression Value="DocumentBankStatements.Filename" CustomStyle="text-decoration:underline"
                    [False] Text "None"
              BlockInstance Separator
              BlockInstance ColumnsMediumRight
                [Column1] Container → Text "Identification"
                [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
                  IfWidget Condition="DocumentIdentification.DocumentId<>Null or Binary<>Null"
                    [True] Link OnClick→DownloadAttachmentOnClick(LoanAttachmentTypeId=Identification, DocumentId=DocumentIdentification.DocumentId)
                             Expression Value="DocumentIdentification.Filename" CustomStyle="text-decoration:underline"
                    [False] Text "None"
              BlockInstance Separator
              BlockInstance ColumnsMediumRight
                [Column1] Container → Text "Tax Form"
                [Column2] Container CustomStyle="text-align:right" Style="\"font-semi-bold\""
                  IfWidget Condition="DocumentTaxForm.DocumentId<>Null or Binary<>Null"
                    [True] Link OnClick→DownloadAttachmentOnClick(LoanAttachmentTypeId=TaxForm, DocumentId=DocumentTaxForm.DocumentId)
                             Expression Value="DocumentTaxForm.Filename" CustomStyle="text-decoration:underline"
                    [False] Text "None"
        IfWidget Condition="GetLoanRequestById.IsDataFetched and (StatusId=NullIdentifier() or StatusId=WaitResubmission)"
          [True]
            Container Style="\"margin-top-xl\""
              Text "Before submitting your loan application, please take some time to read our "
              Link Style="\"font-semi-bold\"" CustomStyle="text-decoration:underline" OnClick→NotImplemented
                Text "Terms & Conditions"
              Text "."
            Container Style="\"margin-top-xl\""
              BlockInstance AlignCenter
                [Content]
                  Checkbox 'Checkbox2' Variable=TermAndConditionsConfirm Style="\"checkbox \""
                  Text "I've read the terms & conditions" Style="\"margin-left-s\""
                  Expression Value="LoanRequestStatus.Label"
            Container Style="\"margin-top-base\""
              BlockInstance ButtonLoading IsLoading=IsLoadingSubmit ShowLabelOnLoading=True ExtendedClass="\"margin-top-base\""
                [Button]
                  Button Enabled=(TermAndConditionsConfirm and (RequestId=Null or StatusId=WaitResubmission) and all 4 filenames<>"")
                         Style="\"btn \"+If(TermAndConditionsConfirm,\"btn-green\",\"\")" Width="(fill parent)"
                    Container Style="\"osui-btn-loading__spinner-animation\""
                    IfWidget Condition="RequestId<>NullIdentifier()"
                      [True]  Text "Resubmit Application" Style="\"text-neutral-0\""
                      [False] Text "Submit Loan Application" Style="\"text-neutral-0\""
                    OnClick→SubmitOnClick
              Button Style="\"btn margin-top-base\""
                Visible="StatusId<>Pending and StatusId<>WaitResubmission"
                Text "Redo Loan Application"
                OnClick→RedoLoanApplicationOnClick
  [1.Footer] Popup ShowPopup="ShowPopup" Style="\"popup-dialog\""
    Container
      Container Width="11 col" → Text "Comment"
      Container Width="1 col" CustomStyle="text-align:right"
        Link OnClick→TogglePopup Transition=Fade
          BlockInstance HBIcon → Text "close"
    Container Style="\"margin-top-base\""
      TextArea 'TextArea_TempNewComment' Variable=TempNewComment MaxLength=500
        Prompt="\"Type your comment here..\""
    Container Style="\"margin-top-m\"" CustomStyle="text-align:right"
      Button Style="\"btn btn-no-border\"" OnClick→TogglePopup Transition=Fade
        Text "Cancel"
      Button Style="\"btn\"" Width="3 col" Enabled="TempNewComment<>\"\""
        Text "Add"
        OnClick→AddCommentOnClick Transition=Fade
```