=== Screen: Login ===
Inputs: (none)
Locals: UserEmail:Text, Password:Text, IsExecuting:Boolean (default=False), IsPasswordVisible:Boolean (default=False), IsSuccess:Boolean, ErrorMsg:Text, TimeoutId:Text, ShowDemoAccessPopup:Boolean, IsConfirmEnabled:Boolean, IsEncryptLoading:Boolean, SearchVar:Text, EmailAux:Text
Aggregates: GetUsers (source=User)
--- WIDGETS (hierarchical) ---
[1] BlockInstance (unnamed) SourceBlock="LayoutBlank" EnableAccessibilityFeatures=null ExtendedClass=null
  [1.1] Container (unnamed) PlaceholderName="Content" Style="\"login-cntr\""
    [1.1.1] Container (unnamed) Width="8 col"
      [1.1.1.1] BlockInstance (unnamed) SourceBlock="Columns2" PhoneBehavior="Entities.BreakColumns.All" GutterSize="Entities.GutterSize.None" TabletBehavior="Entities.BreakColumns.All" ExtendedClass=null
        [1.1.1.1.1] Container (unnamed) PlaceholderName="Column1" Style="\"display-flex justify-content-center\""
          [1.1.1.1.1.1] Container (unnamed) Style="\"login-form\""
            [1.1.1.1.1.1.1] Form 'LoginForm'
              [1.1.1.1.1.1.1.1] Container (unnamed) Style="\"login-logo\"" CustomStyle="text-align: center;"
                [1.1.1.1.1.1.1.1.1] Container (unnamed)
                  [1.1.1.1.1.1.1.1.1.1] Image (unnamed) Width="57px" CustomStyle="height: 55px;" Source="Logo"
                [1.1.1.1.1.1.1.1.2] AdvancedHtml (unnamed) Tag="h5"
                  [1.1.1.1.1.1.1.1.2.1] Container (unnamed)
                    [1.1.1.1.1.1.1.1.2.1.1] Expression (unnamed) Value="\"Home Banking\""
              [1.1.1.1.1.1.1.2] Container (unnamed) Style="\"login-inputs margin-top-xl\""
                [1.1.1.1.1.1.1.2.1] Container (unnamed)
                  [1.1.1.1.1.1.1.2.1.1] Input 'Input_Username' Variable="UserEmail" Style="\"form-control\"" CustomStyle="color: #fff;" MaxLength=250
                [1.1.1.1.1.1.1.2.2] Container (unnamed) Style="\"margin-top-base password-input\""
                  [1.1.1.1.1.1.1.2.2.1] BlockInstance (unnamed) SourceBlock="InputWithIcon" AlignIconRight="True" ExtendedClass=null
                    [1.1.1.1.1.1.1.2.2.1.1] Link (unnamed) PlaceholderName="Icon" CustomStyle="height: auto; margin-top: 2px;" OnClick→Destination="OnTogglePasswordVisibility"
                      [1.1.1.1.1.1.1.2.2.1.1.1] If 'PasswordVisibile' Condition="IsPasswordVisible"
                        [1.1.1.1.1.1.1.2.2.1.1.1.T.1] BlockInstance (unnamed) PlaceholderName="TrueBranch" SourceBlock="HBIcon" Classes=null
                          [1.1.1.1.1.1.1.2.2.1.1.1.T.1.1] Text (unnamed) PlaceholderName="IconName" Style="\"font-size-h3 bold text-neutral-6\"" Text="eyehide"
                        [1.1.1.1.1.1.1.2.2.1.1.1.F.1] BlockInstance (unnamed) PlaceholderName="FalseBranch" SourceBlock="HBIcon" Classes=null
                          [1.1.1.1.1.1.1.2.2.1.1.1.F.1.1] Text (unnamed) PlaceholderName="IconName" Style="\"font-size-h3 bold text-neutral-6\"" Text="eyeshow"
                    [1.1.1.1.1.1.1.2.2.1.2] Input 'Input_Password' PlaceholderName="Input" Variable="Password" Style="\"form-control login-password\"" CustomStyle="color: #fff; padding: 0px 16px 0px 16px;" InputType="Password"
              [1.1.1.1.1.1.1.3] Container (unnamed) Style="\"margin-top-xxl\""
                [1.1.1.1.1.1.1.3.1] BlockInstance (unnamed) SourceBlock="AlignCenter" IsHorizontal=null ExtendedClass=null
                  [1.1.1.1.1.1.1.3.1.1] Container (unnamed) PlaceholderName="Content" Width="9 col" CustomStyle="text-align: left;"
                    [1.1.1.1.1.1.1.3.1.1.1] If (unnamed) Condition="not Client.HideBalance"
                      [1.1.1.1.1.1.1.3.1.1.1.T.1] Container (unnamed) PlaceholderName="TrueBranch"
                        [1.1.1.1.1.1.1.3.1.1.1.T.1.1] Text (unnamed) Style="\"font-semi-bold\"" Text="Privacy Mode Off"
                      [1.1.1.1.1.1.1.3.1.1.1.T.2] Container (unnamed) PlaceholderName="TrueBranch"
                        [1.1.1.1.1.1.1.3.1.1.1.T.2.1] Text (unnamed) Text="Your balances will be visible"
                      [1.1.1.1.1.1.1.3.1.1.1.F.1] Container (unnamed) PlaceholderName="FalseBranch"
                        [1.1.1.1.1.1.1.3.1.1.1.F.1.1] Text (unnamed) Style="\"font-semi-bold\"" Text="Privacy Mode On"
                      [1.1.1.1.1.1.1.3.1.1.1.F.2] Container (unnamed) PlaceholderName="FalseBranch"
                        [1.1.1.1.1.1.1.3.1.1.1.F.2.1] Text (unnamed) Text="Your balances will be hidden"
                  [1.1.1.1.1.1.1.3.1.2] Container (unnamed) PlaceholderName="Content" Width="3 col" CustomStyle="text-align: right;"
                    [1.1.1.1.1.1.1.3.1.2.1] Switch 'Switch1' Variable="Client.HideBalance" Style="\"switch \" + If(Client.HideBalance,\"green-toggle\",\"\")"
              [1.1.1.1.1.1.1.4] Container (unnamed) Style="\"login-button margin-top-l\""
                [1.1.1.1.1.1.1.4.1] BlockInstance (unnamed) SourceBlock="ButtonLoading" ExtendedClass="\"full-width\"" IsLoading="IsExecuting" ShowLabelOnLoading=null
                  [1.1.1.1.1.1.1.4.1.1] Button (unnamed) PlaceholderName="Button" Style="\"btn\"" Width="(fill parent)" IsDefault=true OnClick→Destination="LoginOnClick" OnClick.IsSampleUser="False"
                    [1.1.1.1.1.1.1.4.1.1.1] Container (unnamed) Style="\"osui-btn-loading__spinner-animation\""
                    [1.1.1.1.1.1.1.4.1.1.2] Text (unnamed) Text="Login"
              [1.1.1.1.1.1.1.5] Container (unnamed) Style="\"margin-top-xl\"" CustomStyle="text-align: center;"
                [1.1.1.1.1.1.1.5.1] If (unnamed) Condition="Client.HasDemoAccessCookie or (not GetInitialData.IsDemoAccessCookieEnabled and GetInitialData.IsDataFetched)"
                  [1.1.1.1.1.1.1.5.1.T.1] Link (unnamed) PlaceholderName="TrueBranch" OnClick→Destination="LoginOnClick" OnClick.IsSampleUser="True"
                    [1.1.1.1.1.1.1.5.1.T.1.1] Text (unnamed) CustomStyle="color: #fff;" Text="Login as Sample User"
                  [1.1.1.1.1.1.1.5.1.F.1] Link (unnamed) PlaceholderName="FalseBranch" OnClick→Destination="ToggleDemoAccessPopup" OnClick.IsToClose=null
                    [1.1.1.1.1.1.1.5.1.F.1.1] Text (unnamed) Style="\"text-white\"" Text="Access your demo"
        [1.1.1.1.2] BlockInstance (unnamed) PlaceholderName="Column2" SourceBlock="DisplayOnDevice"
          [1.1.1.1.2.1] Container (unnamed) PlaceholderName="OnDesktop" Style="\"image-cntr\""
            [1.1.1.1.2.1.1] Image (unnamed) Width="397px" Style="\"image\"" Source="LoginBgPortal"
    [1.1.2] Popup (unnamed) ShowPopup="ShowDemoAccessPopup" Style="\"popup-dialog demo-access-popup-main\""
      [1.1.2.1] Container (unnamed) CustomStyle="text-align: right;"
        [1.1.2.1.1] Link (unnamed) OnClick→Destination="ToggleDemoAccessPopup" OnClick.IsToClose="True"
          [1.1.2.1.1.1] Icon (unnamed) Icon="times" Style="\"icon text-white\""
      [1.1.2.2] Container (unnamed) CustomStyle="text-align: center;"
        [1.1.2.2.1] Text (unnamed) Style="\"font-size-h3 text-white\"" Text="Access your demo"
      [1.1.2.3] Container (unnamed) Style="\"margin-top-base\""
        [1.1.2.3.1] Container 'IsTableLoadingOrEmpty'
          [1.1.2.3.1.1] Container (unnamed) Style="\"margin-bottom-l search-login\"" CustomStyle="text-align: center;"
            [1.1.2.3.1.1.1] Container (unnamed) Width="6 col"
              [1.1.2.3.1.1.1.1] BlockInstance (unnamed) SourceBlock="Search" ExtendedClass=null
                [1.1.2.3.1.1.1.1.1] Label (unnamed) PlaceholderName="Input" Style="\"wcag-hide-text\"" Width="(fill parent)"
                  [1.1.2.3.1.1.1.1.1.1] Text (unnamed) Text="Search input"
                [1.1.2.3.1.1.1.1.2] Input 'Input_TextVar' PlaceholderName="Input" Variable="SearchVar" Style="\"form-control\"" InputType="Search" MaxLength=50 OnChange→Destination="OnSearch"
          [1.1.2.3.1.2] Container (unnamed) CustomStyle="height: 175px;"
            [1.1.2.3.1.2.1] If 'IsEmpty' Condition="GetUsers.IsDataFetched and GetUsers.List.Empty"
              [1.1.2.3.1.2.1.T.1] Container (unnamed) PlaceholderName="TrueBranch"
                [1.1.2.3.1.2.1.T.1.1] BlockInstance (unnamed) SourceBlock="BlankSlate" FullHeight=null ExtendedClass=null
                  [1.1.2.3.1.2.1.T.1.1.1] Icon (unnamed) PlaceholderName="Icon" Icon="user-times" Style="\"icon \"" CustomStyle="color: #a9a7a7;"
                  [1.1.2.3.1.2.1.T.1.1.2] Text (unnamed) PlaceholderName="Content" CustomStyle="color: #a9a7a7;" Text="No users were found"
              [1.1.2.3.1.2.1.F.1] If 'IsLoading' PlaceholderName="FalseBranch" Condition="not GetUsers.IsDataFetched"
                [1.1.2.3.1.2.1.F.1.T.1] Container (unnamed) PlaceholderName="TrueBranch" Style="\"list-updating \""
                [1.1.2.3.1.2.1.F.1.F.1] List (unnamed) PlaceholderName="FalseBranch" Source="GetUsers.List" Style="\"profile-grid\""
                  [1.1.2.3.1.2.1.F.1.F.1.1] Container (unnamed) Width="auto" Style="\"email-chip \" + If(GetUsers.List.Current.IsSelected,\"selected\",\"\")"
                    [1.1.2.3.1.2.1.F.1.F.1.1.1] Link (unnamed) OnClick→Destination="EmailOnClick" OnClick.Position="GetUsers.List.CurrentRowNumber" OnClick.Email="GetUsers.List.Current.User.Email"
                      [1.1.2.3.1.2.1.F.1.F.1.1.1.1] Expression (unnamed) Value="GetUsers.List.Current.User.Email" Style="\"text-white\""
      [1.1.2.4] Container (unnamed) Style="\"margin-top-base\"" CustomStyle="text-align: center;"
        [1.1.2.4.1] Text (unnamed) Style="\"font-size-xs \"" CustomStyle="color: #e9ecef;" Text="If you don't see your email on the list please contact the tenant administrator"
      [1.1.2.5] Container (unnamed) Style="\"margin-top-base\"" CustomStyle="text-align: center;"
        [1.1.2.5.1] BlockInstance (unnamed) SourceBlock="ButtonLoading" IsLoading="IsEncryptLoading" ShowLabelOnLoading="True" ExtendedClass=null
          [1.1.2.5.1.1] Button (unnamed) PlaceholderName="Button" Enabled="IsConfirmEnabled or (GetUsers.List.Empty and GetUsers.IsDataFetched and SearchVar = \"\")" Style="\"btn demo-access-confirm-btn \" + If(IsConfirmEnabled,\"IsSelected\", \"\")" Width="(fill parent)" OnClick→Destination="ConfirmEmailOnClick"
            [1.1.2.5.1.1.1] Container (unnamed) Style="\"text-white osui-btn-loading__spinner-animation \""
            [1.1.2.5.1.1.2] Expression (unnamed) Value="\"Confirm\"" Style="\"text-white\""
