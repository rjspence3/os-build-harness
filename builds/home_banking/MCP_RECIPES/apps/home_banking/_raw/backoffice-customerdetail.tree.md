```
=== Screen: CustomerDetail ===
Inputs: CustomerId:HBCustomer Identifier (mandatory)
Locals: ShowSSN:Boolean (default=False)
Aggregates: GetAccountsByCustomerId, GetCustomerById, GetCustomerPictureByCustomerId, GetRequestStatuses, GetPortfolioItems (DataAction)
--- WIDGETS (hierarchical) ---
[1] BlockInstance 'LayoutSideMenuBannerActionsInstance' SourceBlock="LayoutSideMenuBannerActions"
  [1.1] PLACEHOLDER 'Navigation'
    [1.1.1] BlockInstance 'MenuInstance' SourceBlock="Menu" ActiveItem="1"
  [1.2] PLACEHOLDER 'Header'
    [1.2.1] BlockInstance 'HeaderInstance' SourceBlock="Header" HasAIChat="False"
  [1.3] PLACEHOLDER 'Breadcrumbs'
    [1.3.1] BlockInstance 'BreadcrumbsInstance' SourceBlock="Breadcrumbs"
      [1.3.1.1] PLACEHOLDER 'Content'
        [1.3.1.1.1] BlockInstance 'BreadcrumbsItemInstance' SourceBlock="BreadcrumbsItem"
          [1.3.1.1.1.1] PLACEHOLDER 'Title'
            [1.3.1.1.1.1.1] Link Text="Customers" OnClick=Customers (screen)
              [1.3.1.1.1.1.1.1] Text "Customers"
          [1.3.1.1.1.2] PLACEHOLDER 'Icon'
            [1.3.1.1.1.2.1] Icon Icon="angle-right" Style="\"icon\""
        [1.3.1.1.2] BlockInstance 'BreadcrumbsItemInstance2' SourceBlock="BreadcrumbsItem"
          [1.3.1.1.2.1] PLACEHOLDER 'Title'
            [1.3.1.1.2.1.1] Text "Customer Details"
  [1.4] PLACEHOLDER 'Title'
    [1.4.1] BlockInstance 'AlignCenterInstance' SourceBlock="AlignCenter" IsHorizontal=(null)
      [1.4.1.1] PLACEHOLDER 'Content'
        [1.4.1.1.1] Container Style="\"margin-right-base\""
          [1.4.1.1.1.1] If Condition="GetCustomerPictureByCustomerId.IsDataFetched" DesignMode=ShowTrueOrPreview
            [TRUE]
              [1.4.1.1.1.1.T.1] Image Type=Binary Source="GetCustomerPictureByCustomerId.List.Current.CustomerPicture.PictureBinary" Style="\"img-circle\"" Width="44px"
            [FALSE]
              [1.4.1.1.1.1.F.1] Container CustomStyle="text-align: center;"
                [1.4.1.1.1.1.F.1.1] BlockInstance 'AnimateInstance' SourceBlock="Animate" AnimationType="Entities.AnimationType.Spinner"
                  [1.4.1.1.1.1.F.1.1.1] PLACEHOLDER 'Content'
                    [1.4.1.1.1.1.F.1.1.1.1] Icon Icon="spinner" IconSize=Twotimes Style="\"icon\""
        [1.4.1.1.2] Container Width="(fill parent)"
          [1.4.1.1.2.1] BlockInstance 'AlignCenterInstance2' SourceBlock="AlignCenter" IsHorizontal=(null)
            [1.4.1.1.2.1.1] PLACEHOLDER 'Content'
              [1.4.1.1.2.1.1.1] Expression Value="GetCustomerById.List.Current.HBCustomer.Name" Style="\"heading6 margin-right-m\""
              [1.4.1.1.2.1.1.2] If 'Loading' Condition="not GetCustomerById.IsDataFetched" DesignMode=ShowFalse
                [FALSE]
                  [1.4.1.1.2.1.1.2.F.1] If Condition="GetCustomerById.List.Current.HBCustomer.IsPremium" DesignMode=ShowTrueOrPreview
                    [TRUE]
                      [1.4.1.1.2.1.1.2.F.1.T.1] BlockInstance 'TagInstance' SourceBlock="Tag" Size="Entities.Size.Small" ExtendedClass="\"background-tag-is-premium\""
                        [1.4.1.1.2.1.1.2.F.1.T.1.1] PLACEHOLDER 'Tag'
                          [1.4.1.1.2.1.1.2.F.1.T.1.1.1] BlockInstance 'HBIconInstance' SourceBlock="HBIcon" Classes="\"margin-right-xs\""
                            [1.4.1.1.2.1.1.2.F.1.T.1.1.1.1] PLACEHOLDER 'IconName'
                              [1.4.1.1.2.1.1.2.F.1.T.1.1.1.1.1] Text "star"
                          [1.4.1.1.2.1.1.2.F.1.T.1.1.2] Text "Premium"
                    [FALSE]
                      [1.4.1.1.2.1.1.2.F.1.F.1] BlockInstance 'TagInstance2' SourceBlock="Tag" Size="Entities.Size.Small" ExtendedClass="\"background-tag-not-premium\"" Color="Entities.Color.Blue"
                        [1.4.1.1.2.1.1.2.F.1.F.1.1] PLACEHOLDER 'Tag'
                          [1.4.1.1.2.1.1.2.F.1.F.1.1.1] BlockInstance 'HBIconInstance2' SourceBlock="HBIcon" Classes="\"margin-right-xs\""
                            [1.4.1.1.2.1.1.2.F.1.F.1.1.1.1] PLACEHOLDER 'IconName'
                              [1.4.1.1.2.1.1.2.F.1.F.1.1.1.1.1] Text "medal"
                          [1.4.1.1.2.1.1.2.F.1.F.1.1.2] Text "Standard"
          [1.4.1.1.2.2] BlockInstance 'CreditRatingInstance' SourceBlock="CreditRating" CreditScore="GetCustomerById.List.Current.HBCustomer.CreditScore"
  [1.5] PLACEHOLDER 'Details'
    [1.5.1] Container Style="\"margin-right-l\""
      [1.5.1.1] Label Text="Card ID"
      [1.5.1.2] Expression Value="GetCustomerById.List.Current.HBCustomer.CardID" Style="\"font-semi-bold\""
    [1.5.2] Container Style="\"margin-right-l\""
      [1.5.2.1] Label Text="SSN"
      [1.5.2.2] BlockInstance 'AlignCenterInstance3' SourceBlock="AlignCenter" IsHorizontal=(null)
        [1.5.2.2.1] PLACEHOLDER 'Content'
          [1.5.2.2.1.1] Expression Value="If(ShowSSN, HBCustomer.SSN, \"***-**-\"+Substr(SSN,Length(SSN)-4,4))" Style="\"font-semi-bold\"" CustomStyle="min-width: 95px;" Example="***-**-1234"
          [1.5.2.2.1.2] Link Style="\"margin-left-xs\"" OnClick=ToggleHideSSNOnClick
            [1.5.2.2.1.2.1] If Condition="ShowSSN" DesignMode=ShowTrueOrPreview
              [TRUE]
                [1.5.2.2.1.2.1.T.1] BlockInstance 'HBIconInstance3' SourceBlock="HBIcon"
                  [1.5.2.2.1.2.1.T.1.1] PLACEHOLDER 'IconName'
                    [1.5.2.2.1.2.1.T.1.1.1] Text "eyehide"
              [FALSE]
                [1.5.2.2.1.2.1.F.1] BlockInstance 'HBIconInstance4' SourceBlock="HBIcon"
                  [1.5.2.2.1.2.1.F.1.1] PLACEHOLDER 'IconName'
                    [1.5.2.2.1.2.1.F.1.1.1] Text "eyeshow"
    [1.5.3] Container Style="\"margin-right-l\""
      [1.5.3.1] Label Text="Birth Date"
      [1.5.3.2] Expression Value="FormatDateLocale(HBCustomer.BirthDate, Client.LocaleId)" Style="\"font-semi-bold\""
    [1.5.4] Container Style="\"margin-right-l\""
      [1.5.4.1] Label Text="Phone"
      [1.5.4.2] Expression Value="GetCustomerById.List.Current.HBCustomer.Mobile" Style="\"font-semi-bold\""
    [1.5.5] Container Style="\"margin-right-l\""
      [1.5.5.1] Label Text="Email"
      [1.5.5.2] Link OnClick=RedirectToURL(URL="mailto:"+HBCustomer.Email)
        [1.5.5.2.1] Expression Value="GetCustomerById.List.Current.HBCustomer.Email" Style="\"font-semi-bold\""
    [1.5.6] Container
      [1.5.6.1] Label Text="Address"
      [1.5.6.2] Expression Value="GetCustomerById.List.Current.HBCustomer.Address" Style="\"font-semi-bold\""
  [1.6] PLACEHOLDER 'Actions'
    [1.6.1] Container Style="\"customer-actions\""
      [1.6.1.1] Button Text="Edit" Style="\"btn\"" OnClick=NotImplemented
      [1.6.1.2] Button Text="Complaint Ticket" Style="\"btn\"" OnClick=NotImplemented
      [1.6.1.3] Button Text="New Simulation" Style="\"btn\"" OnClick=NotImplemented
      [1.6.1.4] Button Text="New Account" Style="\"btn\"" OnClick=NotImplemented
      [1.6.1.5] Button Text="Product Request" Style="\"btn\"" OnClick=NotImplemented
      [1.6.1.6] Button Text="Deposit" Style="\"btn btn-primary\"" OnClick=NotImplemented
      [1.6.1.7] Button Text="Transfer" Style="\"btn btn-primary\"" OnClick=NotImplemented
      [1.6.1.8] Button Text="Withdrawal" Style="\"btn btn-primary\"" OnClick=NotImplemented
  [1.7] PLACEHOLDER 'MainContent'
    [1.7.1] BlockInstance 'TabsInstance' SourceBlock="Tabs" OptionalConfigs="{ JustifyHeaders: True }"
      [1.7.1.1] PLACEHOLDER 'Header'
        [1.7.1.1.1] BlockInstance 'TabsHeaderItemInstance' SourceBlock="TabsHeaderItem"
          [1.7.1.1.1.1] PLACEHOLDER 'Title'
            [1.7.1.1.1.1.1] Text "Financial Information"
        [1.7.1.1.2] BlockInstance 'TabsHeaderItemInstance2' SourceBlock="TabsHeaderItem"
          [1.7.1.1.2.1] PLACEHOLDER 'Title'
            [1.7.1.1.2.1.1] Text "Accounts"
        [1.7.1.1.3] BlockInstance 'TabsHeaderItemInstance3' SourceBlock="TabsHeaderItem"
          [1.7.1.1.3.1] PLACEHOLDER 'Title'
            [1.7.1.1.3.1.1] Text "Customer Portfolio"
      [1.7.1.2] PLACEHOLDER 'Content'
        [1.7.1.2.1] BlockInstance 'TabsContentItemInstance' SourceBlock="TabsContentItem"  [TAB: Financial Information]
          [1.7.1.2.1.1] PLACEHOLDER 'Content'
            [1.7.1.2.1.1.1] Container Style="\"margin-top-xl\""
              [1.7.1.2.1.1.1.1] If 'IsDataFetchedFinancial' Condition="GetCustomerById.IsDataFetched" DesignMode=ShowAll
                [TRUE]
                  [1.7.1.2.1.1.1.1.T.1] If 'NoCustomerInfo' Condition="GetCustomerById.List.Empty" DesignMode=ShowAll
                    [TRUE]
                      [1.7.1.2.1.1.1.1.T.1.T.1] BlockInstance 'BlankSlateInstance' SourceBlock="BlankSlate" FullHeight="False"
                        [1.7.1.2.1.1.1.1.T.1.T.1.1] PLACEHOLDER 'Icon'
                          [1.7.1.2.1.1.1.1.T.1.T.1.1.1] BlockInstance 'HBIconInstance5' SourceBlock="HBIcon"
                            [1.7.1.2.1.1.1.1.T.1.T.1.1.1.1] PLACEHOLDER 'IconName'
                              [1.7.1.2.1.1.1.1.T.1.T.1.1.1.1.1] Text "columnchart"
                        [1.7.1.2.1.1.1.1.T.1.T.1.2] PLACEHOLDER 'Content'
                          [1.7.1.2.1.1.1.1.T.1.T.1.2.1] Text "Financial information not available"
                    [FALSE]
                      [1.7.1.2.1.1.1.1.T.1.F.1] Container Style="\"card\""
                        [1.7.1.2.1.1.1.1.T.1.F.1.1] Container Width="(fill parent)"
                          [1.7.1.2.1.1.1.1.T.1.F.1.1.1] BlockInstance 'Columns5Instance' SourceBlock="Columns5" PhoneBehavior="Entities.BreakColumns.All"
                            [1.7.1.2.1.1.1.1.T.1.F.1.1.1.1] PLACEHOLDER 'Column1'
                              [1.7.1.2.1.1.1.1.T.1.F.1.1.1.1.1] Container
                                [1.7.1.2.1.1.1.1.T.1.F.1.1.1.1.1.1] Label Text="Client Since"
                                [1.7.1.2.1.1.1.1.T.1.F.1.1.1.1.1.2] Expression Value="FormatDateLocale(HBCustomer.ClientSince, Client.LocaleId)" Style="\"font-semi-bold\""
                            [1.7.1.2.1.1.1.1.T.1.F.1.1.1.2] PLACEHOLDER 'Column2'
                              [1.7.1.2.1.1.1.1.T.1.F.1.1.1.2.1] Container
                                [1.7.1.2.1.1.1.1.T.1.F.1.1.1.2.1.1] Label Text="Branch"
                                [1.7.1.2.1.1.1.1.T.1.F.1.1.1.2.1.2] Expression Value="GetCustomerById.List.Current.HBBranch.Name" Style="\"font-semi-bold\""
                            [1.7.1.2.1.1.1.1.T.1.F.1.1.1.3] PLACEHOLDER 'Column3'
                              [1.7.1.2.1.1.1.1.T.1.F.1.1.1.3.1] Container
                                [1.7.1.2.1.1.1.1.T.1.F.1.1.1.3.1.1] Label Text="Employment Status"
                                [1.7.1.2.1.1.1.1.T.1.F.1.1.1.3.1.2] Expression Value="GetCustomerById.List.Current.HBCustomer.EmploymentStatus" Style="\"font-semi-bold\""
                            [1.7.1.2.1.1.1.1.T.1.F.1.1.1.4] PLACEHOLDER 'Column4'
                              [1.7.1.2.1.1.1.1.T.1.F.1.1.1.4.1] Container
                                [1.7.1.2.1.1.1.1.T.1.F.1.1.1.4.1.1] Label Text="Employer Name"
                                [1.7.1.2.1.1.1.1.T.1.F.1.1.1.4.1.2] Expression Value="GetCustomerById.List.Current.HBCustomer.EmployerName" Style="\"font-semi-bold\""
                            [1.7.1.2.1.1.1.1.T.1.F.1.1.1.5] PLACEHOLDER 'Column5'
                              [1.7.1.2.1.1.1.1.T.1.F.1.1.1.5.1] Container
                                [1.7.1.2.1.1.1.1.T.1.F.1.1.1.5.1.1] Label Text="Position"
                                [1.7.1.2.1.1.1.1.T.1.F.1.1.1.5.1.2] Expression Value="GetCustomerById.List.Current.HBCustomer.Position" Style="\"font-semi-bold\""
                        [1.7.1.2.1.1.1.1.T.1.F.1.2] Container Style="If(IsPhone(), \"margin-top-base\", \"margin-top-l\")"
                          [1.7.1.2.1.1.1.1.T.1.F.1.2.1] BlockInstance 'Columns5Instance2' SourceBlock="Columns5" PhoneBehavior="Entities.BreakColumns.All"
                            [1.7.1.2.1.1.1.1.T.1.F.1.2.1.1] PLACEHOLDER 'Column1'
                              [1.7.1.2.1.1.1.1.T.1.F.1.2.1.1.1] Container
                                [1.7.1.2.1.1.1.1.T.1.F.1.2.1.1.1.1] Label Text="Employment Start Date"
                                [1.7.1.2.1.1.1.1.T.1.F.1.2.1.1.1.2] Expression Value="FormatDateLocale(HBCustomer.EmploymentStartDate, Client.LocaleId)" Style="\"font-semi-bold\""
                            [1.7.1.2.1.1.1.1.T.1.F.1.2.1.2] PLACEHOLDER 'Column2'
                              [1.7.1.2.1.1.1.1.T.1.F.1.2.1.2.1] Container
                                [1.7.1.2.1.1.1.1.T.1.F.1.2.1.2.1.1] Label Text="Annual Income"
                                [1.7.1.2.1.1.1.1.T.1.F.1.2.1.2.1.2] Expression Value="FormatCurrencyCustom(HBCustomer.AnnualIncome,2)" Style="\"font-semi-bold\""
                            [1.7.1.2.1.1.1.1.T.1.F.1.2.1.3] PLACEHOLDER 'Column3'
                              [1.7.1.2.1.1.1.1.T.1.F.1.2.1.3.1] Container
                                [1.7.1.2.1.1.1.1.T.1.F.1.2.1.3.1.1] Label Text="Other Source of Income"
                                [1.7.1.2.1.1.1.1.T.1.F.1.2.1.3.1.2] Expression Value="GetCustomerById.List.Current.HBCustomer.OtherSourceofIncome" Style="\"font-semi-bold\""
                            [1.7.1.2.1.1.1.1.T.1.F.1.2.1.4] PLACEHOLDER 'Column4'
                              [1.7.1.2.1.1.1.1.T.1.F.1.2.1.4.1] Container
                                [1.7.1.2.1.1.1.1.T.1.F.1.2.1.4.1.1] Label Text="Home Ownership"
                                [1.7.1.2.1.1.1.1.T.1.F.1.2.1.4.1.2] Expression Value="GetCustomerById.List.Current.HBCustomer.HomeOwnership" Style="\"font-semi-bold\""
                            [1.7.1.2.1.1.1.1.T.1.F.1.2.1.5] PLACEHOLDER 'Column5'
                              [1.7.1.2.1.1.1.1.T.1.F.1.2.1.5.1] Container
                                [1.7.1.2.1.1.1.1.T.1.F.1.2.1.5.1.1] Label Text="Credit Category"
                                [1.7.1.2.1.1.1.1.T.1.F.1.2.1.5.1.2] BlockInstance 'CreditCategoriesInstance' SourceBlock="CreditCategories" CreditScore="GetCustomerById.List.Current.HBCustomer.CreditScore"
                [FALSE]
                  [1.7.1.2.1.1.1.1.F.1] Container Style="\"list-updating\""
        [1.7.1.2.2] BlockInstance 'TabsContentItemInstance2' SourceBlock="TabsContentItem"  [TAB: Accounts]
          [1.7.1.2.2.1] PLACEHOLDER 'Content'
            [1.7.1.2.2.1.1] Container Style="\"margin-top-xl\""
              [1.7.1.2.2.1.1.1] If 'IsDataFetchedAccounts' Condition="GetAccountsByCustomerId.IsDataFetched" DesignMode=ShowAll
                [TRUE]
                  [1.7.1.2.2.1.1.1.T.1] If 'NoAccounts' Condition="GetAccountsByCustomerId.List.Empty" DesignMode=ShowAll
                    [TRUE]
                      [1.7.1.2.2.1.1.1.T.1.T.1] BlockInstance 'BlankSlateInstance2' SourceBlock="BlankSlate" FullHeight="False"
                        [1.7.1.2.2.1.1.1.T.1.T.1.1] PLACEHOLDER 'Icon'
                          [1.7.1.2.2.1.1.1.T.1.T.1.1.1] BlockInstance 'HBIconInstance6' SourceBlock="HBIcon"
                            [1.7.1.2.2.1.1.1.T.1.T.1.1.1.1] PLACEHOLDER 'IconName'
                              [1.7.1.2.2.1.1.1.T.1.T.1.1.1.1.1] Text "cards"
                        [1.7.1.2.2.1.1.1.T.1.T.1.2] PLACEHOLDER 'Content'
                          [1.7.1.2.2.1.1.1.T.1.T.1.2.1] Text "Accounts not available"
                    [FALSE]
                      [1.7.1.2.2.1.1.1.T.1.F.1] BlockInstance 'CarouselInstance' SourceBlock="Carousel" OptionalConfigs="{ AutoPlay: False, Loop: False, ItemsGap: \"20px\" }" ItemsPerSlide="{ Desktop: 3, Tablet: 2, Phone: 1 }" Navigation="Entities.CarouselNavigation.Dots"
                        [1.7.1.2.2.1.1.1.T.1.F.1.1] PLACEHOLDER 'CarouselItems'
                          [1.7.1.2.2.1.1.1.T.1.F.1.1.1] List Source="GetAccountsByCustomerId.List" Style="\"list list-group\""
                            [1.7.1.2.2.1.1.1.T.1.F.1.1.1.1] Container
                              [1.7.1.2.2.1.1.1.T.1.F.1.1.1.1.1] BlockInstance 'AccountCardInstance' SourceBlock="AccountCard" Balance="GetAccountsByCustomerId.List.Current.AccountBalance" AccountTypeId="...ProductTypeId" EmployeeId="...AssignedToEmpId" AccountNumber4Digit="Substr(...AccountNumber,-4,4)" AccountName="...Name" IsPersonal="...IsPersonal" Location="Substr(...Address,...)" Date="...CreatedOn"
                [FALSE]
                  [1.7.1.2.2.1.1.1.F.1] Container Style="\"list-updating\""
        [1.7.1.2.3] BlockInstance 'TabsContentItemInstance3' SourceBlock="TabsContentItem"  [TAB: Customer Portfolio]
          [1.7.1.2.3.1] PLACEHOLDER 'Content'
            [1.7.1.2.3.1.1] Container Style="\"margin-top-xl\""
              [1.7.1.2.3.1.1.1] If 'IsDataFetchedPortFolio' Condition="GetPortfolioItems.IsDataFetched" DesignMode=ShowAll
                [TRUE]
                  [1.7.1.2.3.1.1.1.T.1] If 'NoRecords' Condition="GetPortfolioItems.PortfolioItemList.Empty" DesignMode=ShowAll
                    [TRUE]
                      [1.7.1.2.3.1.1.1.T.1.T.1] BlockInstance 'BlankSlateInstance3' SourceBlock="BlankSlate" FullHeight="False"
                        [1.7.1.2.3.1.1.1.T.1.T.1.1] PLACEHOLDER 'Icon'
                          [1.7.1.2.3.1.1.1.T.1.T.1.1.1] BlockInstance 'HBIconInstance7' SourceBlock="HBIcon"
                            [1.7.1.2.3.1.1.1.T.1.T.1.1.1.1] PLACEHOLDER 'IconName'
                              [1.7.1.2.3.1.1.1.T.1.T.1.1.1.1.1] Text "dashboard"
                        [1.7.1.2.3.1.1.1.T.1.T.1.2] PLACEHOLDER 'Content'
                          [1.7.1.2.3.1.1.1.T.1.T.1.2.1] Text "Portfolio data not available"
                    [FALSE]
                      [1.7.1.2.3.1.1.1.T.1.F.1] BlockInstance 'GalleryInstance' SourceBlock="Gallery" RowItemsPhone="1" RowItemsTablet="2" RowItemsDesktop="4" ItemsGap="Entities.Space.Medium"
                        [1.7.1.2.3.1.1.1.T.1.F.1.1] PLACEHOLDER 'Content'
                          [1.7.1.2.3.1.1.1.T.1.F.1.1.1] List Source="GetPortfolioItems.PortfolioItemList" Style="\"list list-group\""
                            [1.7.1.2.3.1.1.1.T.1.F.1.1.1.1] BlockInstance 'PortfolioItemCardInstance' SourceBlock="PortfolioItemCard" PortfolioItemTypeId="...Current.ProductType" Title="...Current.Title" Amount="...Current.Amount" StartDate="HBCustomer.EmploymentStartDate" EndDate="...Current.EndDate"
                [FALSE]
                  [{IP_ADDRESS}.1.1.F.1] Container Style="\"list-updating\""
```