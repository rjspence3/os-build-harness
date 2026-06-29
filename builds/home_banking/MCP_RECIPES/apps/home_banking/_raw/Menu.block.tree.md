```
=== Block: Menu ===
Public: False
Flow: Common
Inputs: ActiveItem:Integer (default=-1), ActiveSubItem:Integer (default=-1)
Events: (none)
StyleSheet: (none)

--- WIDGETS ---
[1] AdvancedHtml 'nav'
  [1.1] Container 'Container'
    [1.1.1] If (unnamed)
      [TRUE BRANCH]
      [FALSE BRANCH]
        [1.1.1.F.1] BlockInstance 'ApplicationTitle' SourceBlock="ApplicationTitle"
  [1.2] Container 'PageLinks'
    [1.2.1] Link 'Link'
      [1.2.1.1] Text 'Text'
    [1.2.2] Link 'Link'
      [1.2.2.1] Text 'Text'
    [1.2.3] Link 'Link'
      [1.2.3.1] Text 'Text'
    [1.2.4] Link 'Link'
      [1.2.4.1] Text 'Text'
    [1.2.5] Link 'Link'
      [1.2.5.1] Text 'Text'
  [1.3] Container 'LoginInfo'
    [1.3.1] BlockInstance 'UserInfo' SourceBlock="UserInfo"
```
