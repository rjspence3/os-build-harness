```
=== Block: UserInfo ===
Public: False
Flow: Common
Inputs: (none)
Events: (none)
StyleSheet: (none)

--- WIDGETS ---
[1] Container (unnamed) Style="full-height display-flex align-items-center" Width="(fill parent)"
  [1.1] If (unnamed) Condition="not(IsPhone() or IsTablet())"
  [1.2] Container 'UserLogInOut' Style="user-info" Width="(fill parent)"
    [1.2.1] WebBlockInstance (unnamed)
    [1.2.2] Container (unnamed) Width="(fill parent)"
      [1.2.2.1] If 'UserIsLogged' Condition="GetUserId() <> NullTextIdentifier()"
        [TRUE BRANCH — logged in]
        [1.2.2.1.T.1] Container (unnamed) Style="user-info" Width="(fill parent)"
          [1.2.2.1.T.1.1] Container (unnamed) Style="margin-right-base white-space-nowrap" Width="(fill parent)"
            [1.2.2.1.T.1.1.1] Text Value="Welcome, "
            [1.2.2.1.T.1.1.2] Expression Style="font-semi-bold"
          [1.2.2.1.T.1.2] Image Style="avatar avatar-small border-radius-rounded user-img"
          [1.2.2.1.T.1.3] Container (unnamed) Style="margin-left-s" Width="(fill parent)"
          [1.2.2.1.T.1.4] WebBlockInstance (unnamed) BlockSource="HBIcon"
            PLACEHOLDER 'IconName'
              [1.2.2.1.T.1.4.1] Text Style="heading6" Value="logout"
          [1.2.2.1.T.1.5] Link (unnamed)
        [FALSE BRANCH — not logged in]
        [1.2.2.1.F.1] Link (unnamed) Width="(fill parent)"
          [1.2.2.1.F.1.1] Text Style="margin-left-s" Value="Login"
          [1.2.2.1.F.1.2] WebBlockInstance (unnamed) BlockSource="HBIcon"
            PLACEHOLDER 'IconName'
              [1.2.2.1.F.1.2.1] Text Style="heading6" Value="login"
```

<!--
Provenance: probed via mcp__outsystems__mentor_start (app=fa7ab595-f8cd-4140-8826-2acc484727b6).
Capture run: 2026-06-09. Method: applyModelApiCode flat-walk + depth reconstruction.
Total widgets: 35.

Flat → hierarchy reconstruction is BEST-EFFORT — the IfBranch sequence in the flat
output is hard to disambiguate. Two HBIcon webblock instances confirmed with literal
"logout" and "login" text values inside their IconName placeholders. Avatar image
class confirmed. "Welcome, " prefix Text + Expression for name confirmed.
-->
