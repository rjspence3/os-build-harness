```
=== Screen: ManageSettings ===
Inputs: (none)
Locals: IsBootstrapStarted:Boolean (default=False)
Aggregates: GetDataSettings (source=DataSettings), GetRegions (source=Region, sort=Region.Region)
--- WIDGETS (hierarchical) ---
[1] BlockInstance 'LayoutSideMenu' SourceBlock="LayoutSideMenu"
    [1.1] Placeholder 'Navigation'
        [1.1.1] BlockInstance 'Menu' SourceBlock="Menu" ActiveItem=null ActiveSubItem=null
    [1.2] Placeholder 'Header'
        [1.2.1] BlockInstance 'Header' SourceBlock="Header" NotificationCount=null HasAIChat="False"
    [1.3] Placeholder 'Title'
        [1.3.1] Text (unnamed) Text="Manage Settings"
    [1.4] Placeholder 'MainContent'
        [1.4.1] Container (unnamed) Style="margin-bottom-xxl" Width="(fill parent)" Visible="True"
            [1.4.1.1] BlockInstance 'AlignCenter' SourceBlock="AlignCenter" IsHorizontal=null
                [1.4.1.1.1] Placeholder 'Content'
                    [1.4.1.1.1.1] Container (unnamed) Width="2 col" Visible="True"
                        [1.4.1.1.1.1.1] Text (unnamed) Text="Default Region" CustomStyle="font-weight: bold;"
                    [1.4.1.1.1.2] Container (unnamed) Width="10 col" Visible="True"
                        [1.4.1.1.1.2.1] Dropdown 'Dropdown1' Style="dropdown" Width="6 col" List="GetRegions.List" Labels="Region.Region" Values="Region.Region" Variable="GetDataSettings.List.Current.DataSettings.CurrentRegionName" Mandatory="False" Enabled="True"
                        [1.4.1.1.1.2.2] Container (unnamed) Style="margin-top-s" Width="(fill parent)" Visible="True"
                            [1.4.1.1.1.2.2.1] Text (unnamed) Text="(Region/Country that changes addresses for customers and bank headquarters)"
        [1.4.2] Container (unnamed) Width="(fill parent)" Visible="True"
            [1.4.2.1] Button (unnamed) Style="btn btn-primary" Enabled="not IsBootstrapStarted" Visible="True" OnClick=SaveSettingsOnClick
                [1.4.2.1.1] Text (unnamed) Text="Save Settings & Bootstrap Data"
            [1.4.2.2] Container (unnamed) Style="text-yellow margin-top-m" Width="(fill parent)" Visible="IsBootstrapStarted" Animate=true
                [1.4.2.2.1] BlockInstance 'HBIcon' SourceBlock="HBIcon"
                    [1.4.2.2.1.1] Placeholder 'IconName'
                        [1.4.2.2.1.1.1] Text (unnamed) Text="warning" Style="heading3" CustomStyle="font-weight: bold;"
                [1.4.2.2.2] Container (unnamed) Width="11 col" Visible="True"
                    [1.4.2.2.2.1] Text (unnamed) Text="The data bootstrap has just started!\nPlease follow the results in the ODC Portal, under the timer details in the "
                    [1.4.2.2.2.2] Text (unnamed) Text="Home Banking Core" CustomStyle="font-weight: bold;"
                    [1.4.2.2.2.3] Text (unnamed) Text=" app, and don't forget to check the logs as well to see if any errors occurred."
```