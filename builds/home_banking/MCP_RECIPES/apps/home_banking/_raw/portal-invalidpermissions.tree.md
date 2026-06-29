=== Screen: InvalidPermissions ===
Inputs: (none)
Locals: (none)
Aggregates: (none)
--- WIDGETS (hierarchical) ---
[1] BlockInstance (unnamed) SourceBlock="LayoutTopMenu" ExtendedClass=null EnableAccessibilityFeatures=null HasFixedHeader=null
  [1.1] Container (unnamed) PlaceholderName="Header" Style="\"full-height display-flex align-items-center justify-content-flex-end\""
    [1.1.1] BlockInstance (unnamed) SourceBlock="UserInfo"
  [1.2] BlockInstance (unnamed) PlaceholderName="MainContent" SourceBlock="BlankSlate" ExtendedClass=null FullHeight="True"
    [1.2.1] BlockInstance (unnamed) PlaceholderName="Icon" SourceBlock="HBIcon" Classes=null
      [1.2.1.1] Text (unnamed) PlaceholderName="IconName" Text="lock"
    [1.2.2] Container (unnamed) PlaceholderName="Content"
      [1.2.2.1] Text (unnamed) Style="\"heading6\"" Text="You don't have the necessary permission to see this screen."
    [1.2.3] Container (unnamed) PlaceholderName="Content" Style="\"margin-top-s\""
      [1.2.3.1] Text (unnamed) Text="Please contact your system administrator."
    [1.2.4] If 'NotRegistered' PlaceholderName="Actions" Condition="GetUserId() = NullTextIdentifier()"
      [1.2.4.T.1] Link (unnamed) PlaceholderName="TrueBranch" OnClick→Destination="Login"
        [1.2.4.T.1.1] Text (unnamed) Text="Go to login"
