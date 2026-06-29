# Auth Wiring Capture — Home Banking Portal (original)

App: `Home Banking Portal`, app_key `fa7ab595-f8cd-4140-8826-2acc484727b6`.
Captured 2026-06-11 via `mentor_start` + `applyModelApiCode` typed walks (CAPTURE_PLAYBOOK
rules: read-only reflection walks, `.ToArray()`, no `getScreen`, `mentor_cancel` after
`tool_end`). All node dumps below are verbatim stdout from the sandbox (Translation /
TextResource / ParsedExpression rows filtered in the action dumps to cut i18n noise;
node order is collection order, NOT connector order).

---

## 1. Exception handling wiring

### eSpace-level properties (reflection scan for `*Exception*` / `*Handler*`)

```
GlobalErrorHandler : IExceptionHandler = OnException (NRFlows.FlowExceptionHandlingFlow:B4kRGvrnOEmQonA8ir4Pyg.#FlowExceptionHandler)
PreviousGlobalErrorHandlerValue : PreviousValue = null
UseThemeErrorHandler : Boolean = False
SystemExceptions : ISSCollection`1 = ReadOnlySSCollectionAdapter[AbstractSystemException]
UserExceptions : ISSCollection`1 = ReadOnlySSCollectionAdapter[UserException]
RoleExceptions : ISSCollection`1 = ESpace:lbV6+s34QEGIJirMSEcntg[...].RoleExceptions
GlobalEventHandlers : ISSCollection`1 = ReadOnlySSCollectionAdapter[GlobalEventHandler]
```

### Per-flow `FlowExceptionHandler`

```
Flow: Common (WebFlow)    prop FlowExceptionHandler = FlowExceptionHandlingFlow Name=OnException
Flow: Layouts (WebFlow)   prop FlowExceptionHandler = null
Flow: Blocks (WebFlow)    prop FlowExceptionHandler = null
Flow: Chatbot (WebFlow)   prop FlowExceptionHandler = null
Flow: MainFlow (WebFlow)  prop FlowExceptionHandler = null
Flow: PDF (WebFlow)       prop FlowExceptionHandler = null
Flow: Emails (WebFlow)    prop FlowExceptionHandler = null
```

→ ONE handler, defined on the `Common` UI flow, and promoted to eSpace-level
`GlobalErrorHandler`. No per-flow handlers anywhere else. `UseThemeErrorHandler=False`.

### All exception-ish model objects (23 total)

```
[SystemException] All Exceptions                  under: HomeBankingPortal >
[UserRaisableSystemException] Invalid Login       under: HomeBankingPortal >
[SystemException] Communication Exception         under: HomeBankingPortal >
[SystemException] Security Exception              under: HomeBankingPortal >
[UserRaisableSystemException] Not Registered      under: HomeBankingPortal >
[SystemException] User Exception                  under: HomeBankingPortal >
[SystemException] Database Exception              under: HomeBankingPortal >
[UserRaisableSystemException] Abort Activity Change Exception  under: HomeBankingPortal >
[RoleException] Not HomeBankingPortal             under: HomeBankingPortal >
[ErrorHandler] AllExceptions                      under: HomeBankingPortal > InitClientVars >
[ErrorHandler] AllExceptions                      under: HomeBankingPortal > SendSMS >
[FlowExceptionHandlingFlow] OnException           under: HomeBankingPortal > Common >
[ErrorHandler] AllExceptions                      under: HomeBankingPortal > Common > OnException >
[ErrorHandler] CommunicationException             under: HomeBankingPortal > Common > OnException >
[ErrorHandler] SecurityException                  under: HomeBankingPortal > Common > OnException >
[ErrorHandler] DatabaseException                  under: HomeBankingPortal > Common > OnException >
[ErrorHandler] AllExceptions                      under: HomeBankingPortal > Common > Login > Wakeup >
[ErrorHandler] AllExceptions                      under: HomeBankingPortal > Common > Login > GetInitialData >
[ErrorHandler] AllExceptions                      under: HomeBankingPortal > Common > Login > Wakeup_Twilio >
[ErrorHandler] AllExceptions                      under: HomeBankingPortal > Common > Login > LoginOnClick >
[ErrorHandler] AllExceptions                      under: HomeBankingPortal > Common > Login > ConfirmEmailOnClick >
[ErrorHandler] AllExceptions                      under: HomeBankingPortal > MainFlow > PersonalLoan > ValidateFile >
[ErrorHandler] AllExceptions                      under: HomeBankingPortal > MainFlow > Transfer > ConfirmPhoneNumberOnClick >
```

### OnException handler flow (Common > OnException, FlowExceptionHandlingFlow) — verbatim node dump

```
[WebDestination] Common\InvalidPermissions | Destination=InvalidPermissions
[FeedbackMessage] (unnamed) | Message="There was a problem with the database request. Please contact the administrator"
[ErrorHandler] CommunicationException | Exception=Communication Exception | AbortTransaction=True | LogError=True
[Assign] (unnamed)
[ErrorHandler] SecurityException | Exception=Security Exception | AbortTransaction=True | LogError=False
[If] (unnamed) | Condition=GetUserId() <> NullTextIdentifier()
[Comment] (unnamed)
[End] (unnamed)
[End] (unnamed)
[End] (unnamed)
[ErrorHandler] DatabaseException | Exception=Database Exception | AbortTransaction=True | LogError=True
[ErrorHandler] AllExceptions | Exception=All Exceptions | AbortTransaction=True | LogError=True
[FeedbackMessage] (unnamed) | Message="There was a problem communicating with the server. Please try again or contact your administrator"
[FeedbackMessage] (unnamed) | Message="There was a problem. Please contact the administrator"
[WebDestination] Common\Login | Destination=Login
  [Assignment] (unnamed) | Value=GetBookmarkableURL() | Variable=Client.LastURL
```

Reading (4 typed ErrorHandler entry points in one handler flow):
- **SecurityException** (LogError=False): `If GetUserId() <> NullTextIdentifier()` →
  authenticated-but-unauthorized → redirect `Common\InvalidPermissions`; else (anonymous) →
  `Assign Client.LastURL = GetBookmarkableURL()` → redirect `Common\Login`. This is the
  return-URL capture + login bounce.
- **CommunicationException** (LogError=True): FeedbackMessage "problem communicating with
  the server…" → End (stay on screen).
- **DatabaseException** (LogError=True): FeedbackMessage "problem with the database
  request…" → End.
- **AllExceptions** (LogError=True): FeedbackMessage "There was a problem…" → End.
- All four have AbortTransaction=True. Messages are multi-locale (ar/de/es/ja/ko/pt
  Translation rows present, omitted here).

---

## 2. DoLogin — real body

Two objects named `DoLogin` exist:

### 2a. `[ClientActionFlow] DoLogin` — app-level CLIENT action (under HomeBankingPortal root, not screen-scoped)

Signature: inputs `Username`, `Password`; outputs `Success`, `ErrorMessage`.

Verbatim node dump (collection order):

```
[GenericInputParameter] Username
[GenericInputParameter] Password
[If] (unnamed) | Condition=CheckHomeBankingPortalRole()
[ExecuteAction] CheckAndGrantRole | Action=CheckAndGrantRole
[Start] (unnamed)
[If] (unnamed) | Condition=Login.UserLoginResult.UserLoginFailureReason.TooManyFailedLoginAttempts
[End] (unnamed)
[Assign] (unnamed)
[End] (unnamed)
[End] (unnamed)
[If] (unnamed) | Condition=Login.UserLoginResult.UserLoginFailureReason.InvalidCredentials
[ExecuteClientAction] WithnewRole | Action=Login
[End] (unnamed)
[ExecuteClientAction] Login | Action=Login
[If] (unnamed) | Condition=Login.UserLoginResult.Success
[Assign] (unnamed)
[Assign] (unnamed)
[Assign] (unnamed)
[GenericOutputParameter] Success
[GenericOutputParameter] ErrorMessage
  [Argument] (unnamed) | Value=Login.UserLoginResult.UserId | Parameter=UserId      ← arg of CheckAndGrantRole
  [Assignment] (unnamed) | Value="Invalid credentials." | Variable=ErrorMessage
  [Argument] (unnamed) | Value=Password | Parameter=Password                        ← args of ExecuteClientAction Login
  [Argument] (unnamed) | Value=Username | Parameter=Username
  [Argument] (unnamed) | Value=Password | Parameter=Password                        ← args of ExecuteClientAction WithnewRole (re-Login)
  [Argument] (unnamed) | Value=Username | Parameter=Username
  [Assignment] (unnamed) | Value="Too many failed login attempts. Please try again in " + Login.UserLoginResult.RetryAfterSeconds + " seconds." | Variable=ErrorMessage
  [Assignment] (unnamed) | Value="Login operation failed." | Variable=ErrorMessage
  [Assignment] (unnamed) | Value=True | Variable=Success
```

Reconstructed control flow:

```
Start
 → ExecuteClientAction Login           (SYSTEM client action "Login", args Username/Password)
 → If Login.UserLoginResult.Success
     true:  If CheckHomeBankingPortalRole()
              true:  Assign Success=True → End
              false: ExecuteAction CheckAndGrantRole(UserId=Login.UserLoginResult.UserId)   [server round-trip]
                     → ExecuteClientAction "WithnewRole" (SYSTEM Login again, same Username/Password — refreshes the session with the newly granted role)
                     → Assign Success=True → End
     false: If ...UserLoginFailureReason.InvalidCredentials
              true:  Assign ErrorMessage="Invalid credentials." → End
              false: If ...UserLoginFailureReason.TooManyFailedLoginAttempts
                       true:  Assign ErrorMessage="Too many failed login attempts. Please try again in " + RetryAfterSeconds + " seconds." → End
                       false: Assign ErrorMessage="Login operation failed." → End
```

The system action called is the built-in **client action `Login(Username, Password)`**
whose result is read via `Login.UserLoginResult.{Success, UserId,
UserLoginFailureReason.InvalidCredentials, UserLoginFailureReason.TooManyFailedLoginAttempts,
RetryAfterSeconds}`. (NOT server-side User_Login; ODC system client Login.)

### 2b. Supporting server-side: `CheckAndGrantRole` + `GrantHBPortalRole`

```
--- [UserAction] CheckAndGrantRole  under: HomeBankingPortal >
[GenericInputParameter] UserId
[Start] (unnamed)
[End] (unnamed)
[ExecuteAction] GrantHBPortalRole | Action=GrantHBPortalRole
  [Argument] (unnamed) | Value=UserId | Parameter=UserId
```

= local Server Action, body is just `Start → GrantHBPortalRole(UserId) → End`. Despite the
name, there is no check inside — the check (`CheckHomeBankingPortalRole()`) happens in
DoLogin before the call.

```
--- [ReferenceServiceAPIMethod] GrantHBPortalRole  under: HomeBankingPortal > HomeBankingCore >
[ReferenceSerializableInputParameter] UserId
```

= `GrantHBPortalRole(UserId)` is a **referenced Service Action consumed from
HomeBankingCore** (the role grant itself lives in the Core app, where the role is owned).

Role surface in this eSpace:

```
[ReferenceRole] HomeBankingPortal                      (role referenced from HomeBankingCore)
[CheckRole] CheckHomeBankingPortalRole                 (server-side check function)
[CheckRoleClientSide] CheckHomeBankingPortalRole       (client-side check function)
[RoleException] Not HomeBankingPortal                  (role exception)
```

---

## 3. Login screen — submit wiring

### Buttons on the Login screen (DefaultCustomEvent walk; widgets unnamed, identified by handler)

```
Button #1: OnClick EventHandler
  Destination (ClientScreenActionFlow) = ConfirmEmailOnClick
  Validation = None
  Transition = Fade

Button #2: OnClick EventHandler
  Destination (ClientScreenActionFlow) = LoginOnClick
  Validation = ValidateAndContinue
  Transition = Inherited
```

(Note: widget `OnClick` is NOT a direct property on Button — it lives at
`Button.DefaultCustomEvent` (type `NRWebWidgetEvents.EventHandler`) with
`Destination`/`NavigationTarget` pointing at the screen action. The earlier
`GetProperty("OnClick")` probe returned null for all widgets.)

Button #1 = the demo-access popup confirm (email-chip picker → `ConfirmEmailOnClick`,
which per validation warnings calls server `SetCookie`). Button #2 = the real login
submit → `LoginOnClick` with client-side validation enabled.

### `LoginOnClick` screen action flow (ClientScreenActionFlow on Login screen) — verbatim node dump

Input: `IsSampleUser` (Boolean). Screen has data actions `Wakeup`, `Wakeup_Twilio`,
`GetInitialData` (fetch-gating) and local vars `UserEmail`, `Password`, `IsExecuting`,
`IsSuccess`, `ErrorMsg`.

```
[GenericInputParameter] IsSampleUser
[ErrorHandler] AllExceptions | Exception=All Exceptions | AbortTransaction=True | LogError=True
[Assign] (unnamed)
[If] (unnamed) | Condition=Wakeup.IsDataFetched and Wakeup_Twilio.IsDataFetched and GetInitialData.IsDataFetched
[Assign] (unnamed)
[ExecuteClientAction] SetDefaultLocale | Action=SetDefaultLocale
[Assign] (unnamed)
[JavascriptNode] Wait
[End] (unnamed)
[If] (unnamed) | Condition=Wakeup.HasError or Wakeup_Twilio.HasError or GetInitialData.HasError
[ExecuteClientAction] DoLogin_SampleUser | Action=DoLogin
[Assign] (unnamed)
[If] (unnamed) | Condition=IsSuccess
[Assign] (unnamed)
[Assign] (unnamed)
[FeedbackMessage] (unnamed) | Message=AllExceptions.ExceptionMessage
[If] (unnamed) | Condition=IsSampleUser
[End] (unnamed)
[ExecuteClientAction] DoLogin | Action=DoLogin
[FeedbackMessage] (unnamed) | Message="An error has occurred while loading the app." + NewLine() + "Please refresh the page and try again."
[FeedbackMessage] (unnamed) | Message=ErrorMsg
[Assign] (unnamed)
[WebDestination] MainFlow\Dashboard | Destination=Dashboard
[Assign] (unnamed)
[ExecuteClientAction] FeedbackMessageClose | Action=FeedbackMessageClose
[End] (unnamed)
[Assign] (unnamed)
[Start] (unnamed)
  [Assignment] (unnamed) | Value=False | Variable=IsExecuting
  [Assignment] (unnamed) | Value=DoLogin_SampleUser.Success | Variable=IsSuccess
  [Assignment] (unnamed) | Value=DoLogin_SampleUser.ErrorMessage | Variable=ErrorMsg
  [Assignment] (unnamed) | Value=True | Variable=IsExecuting
  [JSOutputParameter] TimeoutId
  [Argument] (unnamed) | Value=GetInitialData.UserPassword | Parameter=Password     ← args of DoLogin_SampleUser
  [Argument] (unnamed) | Value=GetInitialData.Username | Parameter=Username
  [Assignment] (unnamed) | Value=GetInitialData.SessionId | Variable=Client.ChatSessionId
  [Assignment] (unnamed) | Value=Wait.TimeoutId | Variable=TimeoutId
  [Assignment] (unnamed) | Value="" | Variable=Password
  [Argument] (unnamed) | Value=Password | Parameter=Password                        ← args of DoLogin (manual path)
  [Argument] (unnamed) | Value=UserEmail | Parameter=Username
  [Assignment] (unnamed) | Value=DoLogin.Success | Variable=IsSuccess
  [Assignment] (unnamed) | Value=DoLogin.ErrorMessage | Variable=ErrorMsg
  [Assignment] (unnamed) | Value=False | Variable=IsExecuting
  [Assignment] (unnamed) | Value="" | Variable=Password
```

Reconstructed control flow:

```
Start → Assign IsExecuting=True
 → If (Wakeup.IsDataFetched and Wakeup_Twilio.IsDataFetched and GetInitialData.IsDataFetched)
     false: JavascriptNode "Wait" (timeout JS, TimeoutId out) → Assign TimeoutId → End (retry-style wait for data actions)
     true:  If (Wakeup.HasError or Wakeup_Twilio.HasError or GetInitialData.HasError)
              true:  FeedbackMessage "An error has occurred while loading the app…" → Assign IsExecuting=False → End
              false: If IsSampleUser
                       true:  ExecuteClientAction DoLogin_SampleUser = DoLogin(Username=GetInitialData.Username, Password=GetInitialData.UserPassword)
                              → Assign IsSuccess=DoLogin_SampleUser.Success, ErrorMsg=DoLogin_SampleUser.ErrorMessage
                       false: ExecuteClientAction DoLogin(Username=UserEmail, Password=Password)
                              → Assign IsSuccess=DoLogin.Success, ErrorMsg=DoLogin.ErrorMessage
                     → If IsSuccess
                         true:  Assign Client.ChatSessionId=GetInitialData.SessionId, Password="" → ExecuteClientAction SetDefaultLocale
                                → FeedbackMessageClose → WebDestination MainFlow\Dashboard
                         false: FeedbackMessage ErrorMsg → Assign IsExecuting=False, Password="" → End
ErrorHandler AllExceptions (AbortTransaction=True, LogError=True): FeedbackMessage AllExceptions.ExceptionMessage
```

Also on the screen: `ConfirmEmailOnClick` (demo-user picker; sets a cookie server-side —
flagged by platform validation as anonymous-exposed Server Action `SetCookie`, same for
`GetInitialData/Get_Settings`). `GetInitialData` returns `Username` + `UserPassword` +
`SessionId` for the selected sample user — i.e. demo credentials come from the server.

---

## How the original authenticates end-users

1. Login screen (Common flow, anonymous) has two buttons: demo-picker confirm →
   `ConfirmEmailOnClick` (server `SetCookie`), and submit → `LoginOnClick(IsSampleUser)`
   with ValidateAndContinue.
2. `LoginOnClick` waits for 3 screen data actions (`Wakeup`, `Wakeup_Twilio`,
   `GetInitialData`), then calls app-level client action `DoLogin` — sample-user creds
   come from `GetInitialData.Username/UserPassword`, manual creds from `UserEmail`/`Password`.
3. `DoLogin` calls the ODC **system client action `Login(Username, Password)`** and reads
   `Login.UserLoginResult.*` (Success / InvalidCredentials / TooManyFailedLoginAttempts /
   RetryAfterSeconds).
4. On success, if `CheckHomeBankingPortalRole()` is false it calls server action
   `CheckAndGrantRole(Login.UserLoginResult.UserId)` → Core Service Action
   `GrantHBPortalRole(UserId)` (role owned by HomeBankingCore), then calls system `Login`
   AGAIN ("WithnewRole") to refresh the session with the new role.
5. On success, `LoginOnClick` stores `Client.ChatSessionId`, clears `Password`, and
   navigates to `MainFlow\Dashboard`; on failure it shows `ErrorMsg` as FeedbackMessage.
6. Unauthorized access elsewhere is funneled by the eSpace `GlobalErrorHandler`
   (`Common > OnException`): SecurityException → logged-in users go to
   `InvalidPermissions`, anonymous users get `Client.LastURL = GetBookmarkableURL()` then
   redirect to `Login` (return-URL bounce). Communication/Database/All exceptions show a
   FeedbackMessage and stay put. Only the Common flow defines a handler; it is global.

<!--
Provenance: 6 mentor_start turns (warm session 6a590dae-745d-48d4-b610-5ee0fa176669) on
app fa7ab595-f8cd-4140-8826-2acc484727b6, 2026-06-11. All applyModelApiCode walks
read-only. Walls hit: (a) IMobileWidgetSignature has no .Name / .OnClick — Name via
reflection, click wiring via Button.DefaultCustomEvent (NRWebWidgetEvents.EventHandler)
.Destination; (b) node dumps are collection-order, connector edges not exposed via the
reflected properties probed — control flow reconstructed from conditions + argument
adjacency; (c) one transient NullReferenceException on an unguarded reflection ToString —
Mentor auto-retried with guarded code same turn.
-->
