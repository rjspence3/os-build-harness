```
=== Screen: Transfer ===
Inputs: AccountId:HBAccount Identifier
Locals: NewTransfer:{Amount:Currency, Date:Date, OrginAccountId:HBAccount Identifier, SelectedTransferDateOptionId:TransferDateOption Identifier, ToAccountId:HBAccount Identifier, ToAccountNumber:Long Integer, ToContact:HBCustomer Identifier, ToIBAN:Text, ToPhoneNumber:Phone Number}, StepNo:Integer=1, OTPVerificationCode:Integer, IsToPhoneNumber:Boolean, IsConfirmPhoneNumberLoading:Boolean, TwilioPhoneNumber:Phone Number, ShowPhoneNumberPopup:Boolean, IsPortrait:Boolean
Aggregates: GetAccounts, GetAllAccounts, GetCustomers, GetOriginAccountByAccountId (OnDemand), GetSelectedCustomers (OnDemand)
--- WIDGETS (hierarchical) ---
[1] BlockInstance 'LayoutTopMenuLeftSide' Source=LayoutTopMenuLeftSide
  [1.H] Placeholder 'Header'
    [1.H.1] BlockInstance 'Menu' Source=Menu
  [1.M] Placeholder 'MainContent'
    [1.M.1] Container Style="left-side-content"
      [1.M.1.1] Container Style="margin-bottom-l"
        [1.M.1.1.1] Text Text="New Transfer" Style="font-size-h4 font-semi-bold"
      [1.M.1.2] Container Style="account-card-cntr-transfer"
        [1.M.1.2.1] IfWidget 'StepNo1' Condition="StepNo=1"
          [TRUE]
            [1.M.1.2.1.T.1] IfWidget 'IsDataFetched' Condition="GetAccounts.IsDataFetched"
              [TRUE]
                [1.M.1.2.1.T.1.T.1] BlockInstance 'Slider' Source=StackedCarousel IsVertical="True" OnClick→AccountOnSelect(AccountIdIn=GetAccounts.List[ActiveSlide].Id)
                  [Placeholder 'Content']
                    [1.M.1.2.1.T.1.T.1.C.1] List Source="GetAccounts.List" Style="list list-group transfer-card-list"
                      [1.M.1.2.1.T.1.T.1.C.1.1] Container
                        [1.M.1.2.1.T.1.T.1.C.1.1.1] BlockInstance 'AccountCard' Source=AccountCard IsActive="AccountId = GetAccounts.List.Current.Id" IsTransfer="True" AccountTypeId="GetAccounts.List.Current.ProductTypeId" Balance="GetAccounts.List.Current.AccountBalance" AccountName="GetLabelByLocale(...)" AccountNumber4Digit="Substr(...)"
          [FALSE]
            [1.M.1.2.1.F.1] BlockInstance 'AccountCard' Source=AccountCard IsActive="True" IsTransfer="True" AccountTypeId="GetOriginAccountByAccountId.List.Current.ProductTypeId" Balance="GetOriginAccountByAccountId.List.Current.AccountBalance" AccountName="GetLabelByLocale(...)" AccountNumber4Digit="Substr(...)"
  [1.S] Placeholder 'SideContent'
    [1.S.1] IfWidget 'PhoneOrTabletPortrait' Condition="If(IsPhone() or (IsTablet() and IsPortrait),True,False)" DesignMode=ShowFalse
      [TRUE]
        [1.S.1.T.1] Container Style="margin-bottom-m"
          [1.S.1.T.1.1] Container Style="margin-bottom-l"
            [1.S.1.T.1.1.1] Text Text="New Transfer" Style="font-size-h4 font-semi-bold"
          [1.S.1.T.1.2] Container Style="account-card-cntr-transfer-phone"
            [1.S.1.T.1.2.1] IfWidget 'PhoneStepNo1' Condition="StepNo=1"
              [TRUE]
                [1.S.1.T.1.2.1.T.1] IfWidget 'IsPhoneDataFetched' Condition="GetAccounts.IsDataFetched"
                  [TRUE]
                    [1.S.1.T.1.2.1.T.1.T.1] Container
                      [1.S.1.T.1.2.1.T.1.T.1.1] BlockInstance 'StackedCarouselInstance' Source=StackedCarousel SlidesPerPage="If(IsPhone(),2,3)" Gap="If(IsPhone(),0.8,0.05)" OnClick→CarouselAccountOnSlideMoved(ItemIndex=ActiveSlide)
                        [Placeholder 'Content']
                          [1.S.1.T.1.2.1.T.1.T.1.1.C.1] List Source="GetAccounts.List" Style="list dashboard-card-list"
                            [1.S.1.T.1.2.1.T.1.T.1.1.C.1.1] Container 'ListItemClickable'
                              [1.S.1.T.1.2.1.T.1.T.1.1.C.1.1.1] BlockInstance 'AccountCard' Source=AccountCard IsActive="AccountId = GetAccounts.List.Current.Id" IsTransfer="True" Balance="GetAccounts.List.Current.AccountBalance" AccountTypeId="GetAccounts.List.Current.ProductTypeId" AccountNumber4Digit="Substr(...)" AccountName="GetLabelByLocale(...)"
              [FALSE]
                [1.S.1.T.1.2.1.F.1] Container
                  [1.S.1.T.1.2.1.F.1.1] BlockInstance 'AccountCard' Source=AccountCard IsActive="True" AccountTypeId="GetOriginAccountByAccountId.List.Current.ProductTypeId" AccountNumber4Digit="Substr(...)" AccountName="GetLabelByLocale(...)" Balance="GetOriginAccountByAccountId.List.Current.AccountBalance"
    [1.S.2] Container Width="9 col"
      [1.S.2.1] Container 'Step1' Visible="StepNo=1" Animate=true
        [1.S.2.1.1] Container Style="margin-bottom-l"
          [1.S.2.1.1.1] Text Text="Transfer Details" Style="font-size-base font-semi-bold"
        [1.S.2.1.2] Form 'Form1'
          [1.S.2.1.2.1] Container
            [1.S.2.1.2.1.1] Label Text="Origin Account" → Dropdown5
            [1.S.2.1.2.1.2] Dropdown 'Dropdown5' Variable="NewTransfer.OrginAccountId" List="GetAccounts.List" Values="Id" Mandatory="True" OnChange→AccountDropdownOnChange
              [1.S.2.1.2.1.2.1] Expression Value="GetLabelByLocale(GetAccounts.List.Current.LabelLocale, Client.LocaleId)+\" \"+If(...)"
          [1.S.2.1.2.2] Container Style="margin-top-l transfer-to-btn-grp"
            [1.S.2.1.2.2.1] Label Text="To" → DropdownToContact
            [1.S.2.1.2.2.2] ButtonGroup 'ButtonGroup1' Variable="IsToPhoneNumber" Mandatory="False"
              [1.S.2.1.2.2.2.1] ButtonGroupItem 'ButtonGroupItem1' Value="False" Text="Account Number"
              [1.S.2.1.2.2.2.2] ButtonGroupItem 'ButtonGroupItem2' Value="True" Text="Phone Number"
          [1.S.2.1.2.3] Container Style="margin-top-l"
            [1.S.2.1.2.3.1] Label Text="Contact" → DropdownToContact
            [1.S.2.1.2.3.2] Dropdown 'DropdownToContact' Variable="NewTransfer.ToContact" List="GetCustomers.List" Labels="Name" Values="Id" EmptyValue="Select contact" Mandatory="(IsToPhoneNumber and ...)" OnChange→DropdownToContactOnChange
          [1.S.2.1.2.4] Container Style="margin-top-l"
            [1.S.2.1.2.4.1] IfWidget Condition="IsToPhoneNumber"
              [TRUE]
                [1.S.2.1.2.4.1.T.1] Label Text="Or" → Input_ToPhoneNumber
                [1.S.2.1.2.4.1.T.2] Input 'Input_ToPhoneNumber' Variable="NewTransfer.ToPhoneNumber" Type=Phone Prompt="Enter phone number" OnChange→Input_ToPhoneNumberOnChange
              [FALSE]
                [1.S.2.1.2.4.1.F.1] Label Text="Or" → Input_ToAccountNumber
                [1.S.2.1.2.4.1.F.2] Input 'Input_ToAccountNumber' Variable="NewTransfer.ToIBAN" Type=Text Prompt="Enter IBAN" OnChange→Input_ToAccountNumberOnChange
          [1.S.2.1.2.5] BlockInstance 'MaskText' Source=MaskText InputId="Input_ToAccountNumber.Id" MaskPattern="AA 99 **** ****** ********"
          [1.S.2.1.2.6] Container Style="margin-top-l"
            [1.S.2.1.2.6.1] Label Text="Date" → Input_Date
            [1.S.2.1.2.6.2] Container Style="margin-top-base" Visible="NewTransfer.SelectedTransferDateOptionId=Entities.TransferDateOption.Schedule" Animate=true
              [1.S.2.1.2.6.2.1] Input 'Input_Date' Variable="NewTransfer.Date" Type=Date Mandatory="True"
            [1.S.2.1.2.6.3] Container
              [1.S.2.1.2.6.3.1] Button Style="btn "+If(SelectedTransferDateOptionId=Regular1to2workingdays,"btn-primary","") Text="Regular - 1 to 2 working days" OnClick→DateOptionOnClick(TransferDateOptionId=Regular1to2workingdays)
              [1.S.2.1.2.6.3.2] Button Style="btn "+If(SelectedTransferDateOptionId=Immediate,"btn-primary","") Text="Immediate" OnClick→DateOptionOnClick(TransferDateOptionId=Immediate)
            [1.S.2.1.2.6.4] Container Style="margin-top-base"
              [1.S.2.1.2.6.4.1] Button Style="btn "+If(SelectedTransferDateOptionId=Schedule,"btn-primary","") OnClick→DateOptionOnClick(TransferDateOptionId=Schedule)
                [1.S.2.1.2.6.4.1.1] Text Text="Schedule"
                [1.S.2.1.2.6.4.1.2] BlockInstance 'HBIcon' Source=HBIcon
                  [Placeholder 'IconName'] Text Text="calendar" Style="margin-left-s"
          [1.S.2.1.2.7] Container Style="margin-top-l"
            [1.S.2.1.2.7.1] Link CustomStyle="text-decoration: underline;" Text="Check transfer costs and fees" OnClick→NotImplemented
          [1.S.2.1.2.8] Container Style="margin-top-l"
            [1.S.2.1.2.8.1] Label Text="Amount" → Input_Amount
            [1.S.2.1.2.8.2] Input 'Input_Amount' Variable="NewTransfer.Amount" Type=Number Mandatory="True" Prompt="Enter Amount" OnChange=(none)
            [1.S.2.1.2.8.3] BlockInstance 'MaskCurrency' Source=MaskCurrency InputId="Input_Amount.Id" DecimalDigits="2" GroupSeparator="," DecimalSeparator="." PrefixText="$"
          [1.S.2.1.2.9] Container Style="margin-top-l"
            [1.S.2.1.2.9.1] Button 'Continue' Style="btn btn-primary" IsDefault=true OnClick→ContinueOnClick (ValidateAndContinue)
            [1.S.2.1.2.9.2] Button 'Cancel' Style="btn" OnClick→Dashboard
      [1.S.2.2] Container 'Step2' Visible="StepNo=2" Animate=true
        [1.S.2.2.1] Container Style="margin-bottom-l"
          [1.S.2.2.1.1] Text Text="Review and Confirm" Style="font-size-base font-semi-bold"
        [1.S.2.2.2] Container
          [1.S.2.2.2.1] Container
            [1.S.2.2.2.1.1] Label Text="From"
            [1.S.2.2.2.1.2] BlockInstance 'FormInfoField' Source=FormInfoField
              [Placeholder 'Icon'] BlockInstance 'HBIcon' Source=HBIcon
                [Placeholder 'IconName'] Text Text="cardout" Style="font-size-h4"
              [Placeholder 'Label'] Expression Value="GetOriginAccountByAccountId.List.Current.Type+\" \"+Substr(...)"
              [Placeholder 'Value'] BlockInstance 'AlignCenter' Source=AlignCenter
                [Placeholder 'Content']
                  [Text] Text="Available: " Style="text-neutral-7"
                  [Expression] Value="FormatCurrencyCustom(GetOriginAccountByAccountId.List.Current.AccountBalance)" Style="If(AccountBalance>0,\"text-green\",\"text-red\")"
          [1.S.2.2.2.2] Container Style="margin-top-l"
            [1.S.2.2.2.2.1] Label Text="To"
            [1.S.2.2.2.2.2] BlockInstance 'FormInfoField' Source=FormInfoField
              [Placeholder 'Icon'] BlockInstance 'HBIcon' Source=HBIcon
                [Placeholder 'IconName'] Text Text="profilesquare" Style="font-size-h4"
              [Placeholder 'Label'] IfWidget Condition="not GetSelectedCustomers.List.Empty"
                [TRUE] Expression Value="GetSelectedCustomers.List.Current.HBCustomer.Name"
                [FALSE] Expression Value="If(IsToPhoneNumber,NewTransfer.ToPhoneNumber,NewTransfer.ToAccountNumber)"
              [Placeholder 'Value'] IfWidget Condition="not GetSelectedCustomers.List.Empty" DesignMode=ShowTrueOrPreview
                [TRUE] BlockInstance 'AlignCenter' Source=AlignCenter
                  [Placeholder 'Content'] Expression Value="GetSelectedCustomers.List.Current.ProductType.Label+\" \"+Substr(...)" Style="text-neutral-7"
          [1.S.2.2.2.3] Container Style="margin-top-l"
            [1.S.2.2.2.3.1] Label Text="Date"
            [1.S.2.2.2.3.2] BlockInstance 'FormInfoField' Source=FormInfoField
              [Placeholder 'Icon'] BlockInstance 'HBIcon' Source=HBIcon
                [Placeholder 'IconName'] Text Text="calendar" Style="font-size-h4"
              [Placeholder 'Label'] Expression Value="If(NewTransfer.Date=CurrDate(),\"Today\",\"Scheduled For\")"
              [Placeholder 'Value'] BlockInstance 'AlignCenter' Source=AlignCenter
                [Placeholder 'Content'] Expression Value="FormatDateCustom(NewTransfer.Date)" Style="text-neutral-7"
          [1.S.2.2.2.4] Container Style="margin-top-l"
            [1.S.2.2.2.4.1] Label Text="Amount"
            [1.S.2.2.2.4.2] BlockInstance 'FormInfoField' Source=FormInfoField
              [Placeholder 'Icon'] BlockInstance 'HBIcon' Source=HBIcon
                [Placeholder 'IconName'] Text Text="moneysymbol" Style="font-size-h4"
              [Placeholder 'Label'] Expression Value="FormatCurrencyCustom(NewTransfer.Amount)"
          [1.S.2.2.2.5] Container Style="margin-top-m"
            [1.S.2.2.2.5.1] BlockInstance 'AlignCenter' Source=AlignCenter
              [Placeholder 'Content']
                [Text] Text="This operation will cost you $0,00"
                [BlockInstance 'Tooltip'] Source=Tooltip ExtendedClass="margin-left-s"
                  [Placeholder 'Content'] BlockInstance 'HBIcon' Source=HBIcon
                    [Placeholder 'IconName'] Text Text="info" Style="font-size-h5"
                  [Placeholder 'Tooltip'] Text Text="Cost can differ depending on the account, channel, and location."
          [1.S.2.2.2.6] Container Style="margin-top-l"
            [1.S.2.2.2.6.1] Text Text="You're going to receive an SMS code on your mobile (e.g. 1234), insert it below to confirm the transfer."
          [1.S.2.2.2.7] Container Style="margin-top-base"
            [1.S.2.2.2.7.1] BlockInstance 'AlignCenter' Source=AlignCenter
              [Placeholder 'Content']
                [1.S.2.2.2.7.1.C.1] Container Width="5 col"
                  [1.S.2.2.2.7.1.C.1.1] BlockInstance 'InputWithIcon' Source=InputWithIcon AlignIconRight="True"
                    [Placeholder 'Icon'] BlockInstance 'HBIcon' Source=HBIcon
                      [Placeholder 'IconName'] Text Text="smscode" Style="font-size-h4"
                    [Placeholder 'Input'] Input 'Input_SmsCode' Variable="OTPVerificationCode" Type=Number Prompt="Insert SMS code"
                [1.S.2.2.2.7.1.C.2] Link Style="margin-left-s" Text="Didn't get a code? Resend" OnClick→SendCodeOnClick
          [1.S.2.2.2.8] Container Style="margin-top-l"
            [1.S.2.2.2.8.1] Button 'Confirm' Style="btn btn-primary" Enabled="Length(IntegerToText(OTPVerificationCode))>3" OnClick→ConfirmOnClick
            [1.S.2.2.2.8.2] Button 'Back' Style="btn" OnClick→BackOnClick
            [1.S.2.2.2.8.3] Button 'Cancel' Style="btn btn-no-border" OnClick→Dashboard
  [1.F] Placeholder 'Footer'
    [1.F.1] Popup ShowPopup="ShowPhoneNumberPopup" Style="popup-dialog"
      [1.F.1.1] Container
        [1.F.1.1.1] Container Width="11 col"
          [1.F.1.1.1.1] Text Text="Insert a valid phone number in order to recive a OTP verification code"
        [1.F.1.1.2] Container Width="1 col" CustomStyle="text-align: right;"
          [1.F.1.1.2.1] Link OnClick→TogglePhonePopup (Fade)
            [1.F.1.1.2.1.1] BlockInstance 'HBIcon' Source=HBIcon
              [Placeholder 'IconName'] Text Text="close"
      [1.F.1.2] Container Style="margin-top-base"
        [1.F.1.2.1] Input 'Input_PhoneNumber' Variable="TwilioPhoneNumber" Type=Phone Prompt="e.g. {PHONE}"
      [1.F.1.3] Container Style="margin-top-m" CustomStyle="text-align: center;"
        [1.F.1.3.1] BlockInstance 'ButtonLoading' Source=ButtonLoading IsLoading="IsConfirmPhoneNumberLoading" ShowLabelOnLoading="True"
          [Placeholder 'Button'] Button 'ConfirmPhoneNumber' Enabled="TwilioPhoneNumber <> \"\"" Style="btn" Width="(fill parent)" OnClick→ConfirmPhoneNumberOnClick (Fade)
            [1.F.1.3.1.B.1] Container Style="osui-btn-loading__spinner-animation"
            [1.F.1.3.1.B.2] Text Text="Confirm phone number"
```