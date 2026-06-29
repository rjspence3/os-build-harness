```
=== Screen: Confirmation ===
Inputs: TransactionId:Transaction Identifier (mandatory), RequestId:LoanRequest Identifier
Locals: CountDownValue:Integer=10, Message:Text, IsPDFRendered:Boolean=False, myTimerHandler:(JS timer handle)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] BlockInstance 'LayoutTopMenu' SourceBlock="LayoutTopMenu" ExtendedClass=null HasFixedHeader=null
  [1.1] PLACEHOLDER 'Header'
    [1.1.1] BlockInstance 'Menu' SourceBlock="Menu" ActiveItem=null ActiveSubItem=null
  [1.2] PLACEHOLDER 'MainContent'
    [1.2.1] Container (unnamed) CustomStyle="padding: 130px 50px 50px 50px; text-align: center;" Width="(fill parent)"
      [1.2.1.1] If (unnamed) Condition="TransactionId = NullIdentifier()"
        [TRUE BRANCH — Loan request flow]
        [1.2.1.1.T.1] BlockInstance 'Wizard' SourceBlock="Wizard" IsVertical=null ExtendedClass=null
          PLACEHOLDER 'Content'
            [1.2.1.1.T.1.1] BlockInstance 'WizardItem' SourceBlock="WizardItem" Status="Entities.Steps.Active"
              PLACEHOLDER 'Icon'
                [1.2.1.1.T.1.1.I.1] BlockInstance 'CheckMark' SourceBlock="CheckMark"
              PLACEHOLDER 'Label'
                [1.2.1.1.T.1.1.L.1] Text Text="Application Submission"
            [1.2.1.1.T.1.2] BlockInstance 'WizardItem2' SourceBlock="WizardItem" Status="Entities.Steps.Next"
              PLACEHOLDER 'Icon'
                [1.2.1.1.T.1.2.I.1] BlockInstance 'HBIcon' SourceBlock="HBIcon" Classes=null
                  PLACEHOLDER 'IconName'
                    [1.2.1.1.T.1.2.I.1.1] Text Style="\"heading5\"" Text="checklist"
              PLACEHOLDER 'Label'
                [1.2.1.1.T.1.2.L.1] Text Text="Process Validation"
            [1.2.1.1.T.1.3] BlockInstance 'WizardItem3' SourceBlock="WizardItem" Status="Entities.Steps.Next"
              PLACEHOLDER 'Icon'
                [1.2.1.1.T.1.3.I.1] Image Style="\"svg-icon\"" Image="CheckSquare" Type=Static
              PLACEHOLDER 'Label'
                [1.2.1.1.T.1.3.L.1] Text Text="Final Decision"
        [1.2.1.1.T.2] Container (unnamed) Style="\"margin-l\"" Width="(fill parent)"
          [1.2.1.1.T.2.1] Container (unnamed) Style="\"heading4\"" Width="(fill parent)"
            [1.2.1.1.T.2.1.1] Text Text="Your loan application was successfully submitted!"
          [1.2.1.1.T.2.2] Container (unnamed) Style="\"margin-top-base\"" Width="(fill parent)"
            [1.2.1.1.T.2.2.1] Text Style="\"font-size-base\"" Text="We'll review it and get back to you soon. "
          [1.2.1.1.T.2.3] Container (unnamed) Style="\"padding-top-xxl \" + If(IsPhone(), \"display-grid gap-base\", \"\")" Width="(fill parent)"
            [1.2.1.1.T.2.3.1] If (unnamed) Condition="RequestId <> NullIdentifier()" DesignMode=ShowTrueOrPreview
              [TRUE BRANCH]
              [1.2.1.1.T.2.3.1.T.1] BlockInstance 'ConfirmationPDF' SourceBlock="ConfirmationPDF" RequestId="RequestId"
                                      OnEvent:ReturnBinary→DownloadConfirmationOnClick(File=File, FileName=FileName)
                                      OnEvent:OnReady→ConfirmationPDFOnReady(IsReady=IsReady)
            [1.2.1.1.T.2.3.2] Button (unnamed) Style="\"btn btn-primary\"" Enabled="True"
              Text="Back to Home" OnClick→Destination=Dashboard
        [FALSE BRANCH — Transfer flow]
        [1.2.1.1.F.1] Container 'ConfirmationIcon' Width="(fill parent)"
          [1.2.1.1.F.1.1] BlockInstance 'CheckMark2' SourceBlock="CheckMark"
        [1.2.1.1.F.2] Container (unnamed) Style="\"margin-l\"" Width="(fill parent)"
          [1.2.1.1.F.2.1] Container (unnamed) Style="\"heading4\"" Width="(fill parent)"
            [1.2.1.1.F.2.1.1] Text Text="Success!"
          [1.2.1.1.F.2.2] Container (unnamed) Style="\"margin-top-base\"" Width="(fill parent)"
            [1.2.1.1.F.2.2.1] Text Style="\"font-size-base\"" Text="Your transfer is complete."
          [1.2.1.1.F.2.3] Container (unnamed) Style="\"margin-top-xxl\"" Width="(fill parent)"
            [1.2.1.1.F.2.3.1] Button (unnamed) Style="\"btn btn-primary\"" Enabled="True"
              Text="Back to Home" OnClick→Destination=Dashboard
            [1.2.1.1.F.2.3.2] Button (unnamed) Style="\"btn\"" Enabled="True"
              Text="Share Receipt" OnClick→Destination=ShareReceiptOnClick
      [1.2.1.2] Container 'CountDownMessage' Style="\"confirmation-counter-message\"" Width="(fill parent)"
        [1.2.1.2.1] Expression Value="Message"
```