~/Development/kyleAccounts/scripts/os_element_reflect/Program.cs(66,61): warning CS8619: Nullability of reference types in value of type 'Type?[]' doesn't match target type 'Type[]'. [~/Development/kyleAccounts/scripts/os_element_reflect/os_element_reflect.csproj]
# OS Element Authoring Reference

Reflection-derived from the installed ODC Studio .NET assemblies via
`System.Reflection.MetadataLoadContext` (metadata-only — the Studio internals are
never executed). Authoritative + version-stable; bypasses the Mentor introspection
guardrail (odc_mcp_mentor_wont_run_arbitrary_read_code). Regenerate:
`dotnet run --project scripts/os_element_reflect > data/MCP_RECIPES/OS_ELEMENT_REFERENCE.md`

Source assemblies (with a target type):
- OutSystems.Model 13.0.0.0 — 11 target types
- OutSystems.Model.Plugin.NRWidgets 13.0.0.0 — 8 target types
- OutSystems.Model.V1 13.0.0.0 — 43 target types
- OutSystems.ServiceStudio.PluginAPI 13.0.0.0 — 11 target types

## IContainer
_ServiceStudio.Plugin.NRWidgets.IContainer_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IWidget, IWidgetSignature, IMobileWidget, IMobileWidgetSignature, IContainerSignature

**Properties** (name | type | get/set):
- `Align` | Align | get/set
- `Animate` | Boolean | get/set
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Content` | IContent | get
- `CustomStyle` | String | get/set
- `Definition` | IWidgetDefinitionSignature | get
- `Descriptor` | IContainerDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Events` | ISequence<IEvent> | get
- `ExtendedProperties` | ISequence<IExtendedProperty> | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `MarginLeft` | String | get/set
- `MarginTop` | String | get/set
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Style` | IExpression | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `Visible` | IExpression | get
- `VisibleWasExpression` | Boolean | get/set
- `WasDeleted` | Boolean | get
- `Widgets` | IEnumerable<IMobileWidget> | get
- `Width` | String | get/set

**Members** (setters/creators ranked first — signature → returns):
- `SetStyle(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `SetVisible(ExpressionDefinition value)` → Void
- `CreateEvent()` → IEvent
- `CreateExtendedProperty()` → IExtendedProperty
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CreateWidget(IWidgetDefinitionSignature widgetDefinition, String name, IKey key)` → IMobileWidget
- `CreateWidget<T>(String name, IKey key)` → T
- `CreateWidget(Type widgetType, String name, IKey key)` → IMobileWidget
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Delete(Boolean preserveChildren)` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IExpression
_ServiceStudio.Plugin.NRWidgets.IExpression_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IWidget, IWidgetSignature, IMobileWidget, IMobileWidgetSignature, IExpressionSignature

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `CustomStyle` | String | get/set
- `Definition` | IWidgetDefinitionSignature | get
- `Descriptor` | IExpressionDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Events` | ISequence<IEvent> | get
- `Example` | String | get/set
- `ExtendedProperties` | ISequence<IExtendedProperty> | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `MarginLeft` | String | get/set
- `MarginTop` | String | get/set
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Style` | IExpression | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `Value` | IExpression | get
- `WasDeleted` | Boolean | get
- `Width` | String | get/set

**Members** (setters/creators ranked first — signature → returns):
- `SetStyle(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `SetValue(ExpressionDefinition value)` → Void
- `CreateEvent()` → IEvent
- `CreateExtendedProperty()` → IExtendedProperty
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Delete(Boolean preserveChildren)` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## ITextWidget
_ServiceStudio.Model.Interfaces.ITextWidget_  
Inherits: IWidgetWithEditableText, IVersionedObject, IModelObject, IObjectSignature, ICustomCommandTarget, IDraggableType, IDraggableObject, IDropTarget, IPasteTarget, ICommandTarget, IImportTarget, IXmlSerializable, IObjectWithIdentifier, ISSSerializable, ITrackableObject, IObject, IContentObject, IWidget, IHtmlElement, IHtmlElementWidget

**Properties** (name | type | get/set):
- `AsAbstractObject` | AbstractObject | get
- `AsAbstractWidget` | AbstractWidget | get
- `ChildCollectionsPreviewGeneration` | Int64 | get
- `Children` | IEnumerable<IModelObject> | get
- `ChildrenPreviewGeneration` | Int64 | get
- `CollectionDescriptor` | IChildCollection | get
- `Collections` | IEnumerable<CollectionMetadata> | get
- `CssClasses` | String[] | get
- `Descriptor` | IClassDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HtmlTag` | String | get
- `Id` | IObjectIdentifier | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `New` | Boolean | get/set
- `Object` | AbstractObject | get
- `ObjectKey` | IKey | get
- `Owner` | IWidgetOwner | get
- `OwnerESpace` | ESpace | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `SelfPreviewGeneration` | Int64 | get
- `TagName` | String | get
- `Text` | String | get/set
- `TextPropertyDescriptor` | PropertyDescriptor | get
- `TransactionsManager` | ITransactionsManager | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetPropertyValue(String propertyName, Object value)` → Void
- `BehavesAs<T>()` → Boolean
- `Delete()` → Void
- `ForceValidate()` → Void
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetCssPropertiesFromWidgetProperties(CssPropertyDictionary dictionary)` → Void
- `GetESpace()` → IESpace
- `GetInheritedCssPropertiesFromWidgetProperties(CssPropertyDictionary dictionary)` → Void
- `GetInterface()` → Type
- `GetOwnerEspace()` → IEspace
- `GetParent()` → IModelObject
- `GetPropertyValue(String propertyName)` → Object
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `IncreasePreviewGeneration(ContentObjectChangeType changeType)` → Void
- `InnerIncreasePreviewGeneration(ContentObjectChangeType changeType)` → Boolean
- `IsInside<T>()` → Boolean
- `IsInsideObjectWithDescriptor<T>()` → Boolean
- `IsOrIsInside<T>()` → Boolean
- `IsOrIsInsideObjectWithDescriptor<T>()` → Boolean
- `IsValidForToolbar()` → Boolean
- `LoadChildren(IXmlDeserializer loader)` → Void
- `LoadPropertyAttributes(IObjectAttributeReader loader)` → Void
- `LoadPropertyElements(IObjectAttributeReader loader)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void
- `SaveChildren(IXmlSerializer saver)` → Void
- `SavePropertyAttributes(IXmlSerializer saver)` → Void
- `SavePropertyElements(IXmlSerializer saver)` → Void
- `Serialize(IBinarySerializer writer)` → Void

## IButton
_ServiceStudio.Plugin.NRWidgets.IButton_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IWidget, IWidgetSignature, IMobileWidget, IMobileWidgetSignature, IButtonSignature

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `ConfirmationMessage` | IExpression | get
- `Content` | IContent | get
- `CustomStyle` | String | get/set
- `Definition` | IWidgetDefinitionSignature | get
- `Descriptor` | IButtonDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Enabled` | IExpression | get
- `Events` | ISequence<IEvent> | get
- `ExtendedProperties` | ISequence<IExtendedProperty> | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IndexInParent` | Int32 | get
- `IsDefault` | Boolean | get/set
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `MarginLeft` | String | get/set
- `MarginTop` | String | get/set
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `OnClick` | IBuiltinEvent | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Style` | IExpression | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `Visible` | IExpression | get
- `WasDeleted` | Boolean | get
- `Widgets` | IEnumerable<IMobileWidget> | get
- `Width` | String | get/set

**Members** (setters/creators ranked first — signature → returns):
- `SetConfirmationMessage(ExpressionDefinition value)` → Void
- `SetEnabled(Boolean value)` → Void
- `SetEnabled(ExpressionDefinition value)` → Void
- `SetStyle(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `SetVisible(ExpressionDefinition value)` → Void
- `CreateEvent()` → IEvent
- `CreateExtendedProperty()` → IExtendedProperty
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CreateWidget(IWidgetDefinitionSignature widgetDefinition, String name, IKey key)` → IMobileWidget
- `CreateWidget<T>(String name, IKey key)` → T
- `CreateWidget(Type widgetType, String name, IKey key)` → IMobileWidget
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Delete(Boolean preserveChildren)` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IImage
_ServiceStudio.Plugin.NRWidgets.IImage_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IWidget, IWidgetSignature, IMobileWidget, IMobileWidgetSignature, IImageSignature

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `CustomStyle` | String | get/set
- `DefaultImage` | IImageSignature | get/set
- `Definition` | IWidgetDefinitionSignature | get
- `Descriptor` | IImageDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Events` | ISequence<IEvent> | get
- `ExtendedProperties` | ISequence<IExtendedProperty> | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `Image` | IImageSignature | get/set
- `ImageContent` | IExpression | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `MarginLeft` | String | get/set
- `MarginTop` | String | get/set
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Style` | IExpression | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `Type` | Type | get/set
- `Url` | IExpression | get
- `WasDeleted` | Boolean | get
- `Width` | String | get/set

**Members** (setters/creators ranked first — signature → returns):
- `SetImageContent(ExpressionDefinition value)` → Void
- `SetStyle(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `SetUrl(ExpressionDefinition value)` → Void
- `CreateEvent()` → IEvent
- `CreateExtendedProperty()` → IExtendedProperty
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Delete(Boolean preserveChildren)` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IInput
_ServiceStudio.Plugin.NRWidgets.IInput_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IWidget, IWidgetSignature, IMobileWidget, IMobileWidgetSignature, IInputSignature

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `CustomStyle` | String | get/set
- `Definition` | IWidgetDefinitionSignature | get
- `Descriptor` | IInputDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Enabled` | IExpression | get
- `Events` | ISequence<IEvent> | get
- `ExtendedProperties` | ISequence<IExtendedProperty> | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IndexInParent` | Int32 | get
- `InputType` | InputType | get/set
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `Mandatory` | IExpression | get
- `MarginLeft` | String | get/set
- `MarginTop` | String | get/set
- `MaxLength` | Nullable<Int32> | get/set
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `OnChange` | IBuiltinEvent | get
- `Parent` | IModelObject | get
- `Prompt` | IExpression | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Style` | IExpression | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `Variable` | IExpression | get
- `WasDeleted` | Boolean | get
- `Width` | String | get/set

**Members** (setters/creators ranked first — signature → returns):
- `SetEnabled(Boolean value)` → Void
- `SetEnabled(ExpressionDefinition value)` → Void
- `SetMandatory(Boolean value)` → Void
- `SetMandatory(ExpressionDefinition value)` → Void
- `SetPrompt(ExpressionDefinition value)` → Void
- `SetStyle(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `SetVariable(ExpressionDefinition value)` → Void
- `CreateEvent()` → IEvent
- `CreateExtendedProperty()` → IExtendedProperty
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Delete(Boolean preserveChildren)` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IInputWidget
_OutSystems.Model.UI.Web.Widgets.IInputWidget_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IWidget, IWidgetSignature, IWebWidget, IWebWidgetSignature, IInputWidgetSignature

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `CustomStyle` | String | get/set
- `Descriptor` | IInputWidgetDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `EffectiveMarginLeft` | EffectiveMarginLeftType | get/set
- `EffectiveWidth` | EffectiveWidthType | get/set
- `Enabled` | IExpression | get
- `ExtendedProperties` | ISequence<IExtendedProperty> | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `Mandatory` | IExpression | get
- `MarginLeft` | String | get/set
- `MarginTop` | String | get/set
- `MaxLength` | Nullable<Int32> | get/set
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `NullValue` | IExpression | get
- `ObjectKey` | IKey | get
- `OnChange` | IOnChange | get
- `Parent` | IModelObject | get
- `Prompt` | IExpression | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `StyleClasses` | String | get/set
- `TextLines` | Nullable<Int32> | get/set
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `Type` | InputType | get/set
- `ValidationParent` | IObject | get/set
- `Variable` | IExpression | get
- `Visible` | IExpression | get
- `WasDeleted` | Boolean | get
- `Width` | String | get/set

**Members** (setters/creators ranked first — signature → returns):
- `SetEnabled(ExpressionDefinition value)` → Void
- `SetMandatory(ExpressionDefinition value)` → Void
- `SetNullValue(ExpressionDefinition value)` → Void
- `SetPrompt(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `SetVariable(ExpressionDefinition value)` → Void
- `SetVisible(ExpressionDefinition value)` → Void
- `CreateExtendedProperty()` → IExtendedProperty
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Delete(Boolean preserveChildren)` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IList
_ServiceStudio.Plugin.NRWidgets.IList_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IWidget, IWidgetSignature, IMobileWidget, IMobileWidgetSignature, IListSignature

**Properties** (name | type | get/set):
- `AnimateItems` | Boolean | get/set
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `CustomStyle` | String | get/set
- `Definition` | IWidgetDefinitionSignature | get
- `Descriptor` | IListDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Events` | ISequence<IEvent> | get
- `ExpandedInWebEditor` | Boolean | get/set
- `ExtendedProperties` | ISequence<IExtendedProperty> | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `ListItem` | IContent | get
- `MarginLeft` | String | get/set
- `MarginTop` | String | get/set
- `Metadata` | ISequence<IMetadata> | get
- `Mode` | Mode | get/set
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `OnScrollEnding` | IBuiltinEvent | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Source` | IExpression | get
- `Style` | IExpression | get
- `Tag` | String | get/set
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `WasDeleted` | Boolean | get
- `Widgets` | IEnumerable<IMobileWidget> | get
- `Width` | String | get/set

**Members** (setters/creators ranked first — signature → returns):
- `SetSource(ExpressionDefinition value)` → Void
- `SetStyle(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateEvent()` → IEvent
- `CreateExtendedProperty()` → IExtendedProperty
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CreateWidget(IWidgetDefinitionSignature widgetDefinition, String name, IKey key)` → IMobileWidget
- `CreateWidget<T>(String name, IKey key)` → T
- `CreateWidget(Type widgetType, String name, IKey key)` → IMobileWidget
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Delete(Boolean preserveChildren)` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## ILink
_ServiceStudio.Plugin.NRWidgets.ILink_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IWidget, IWidgetSignature, IMobileWidget, IMobileWidgetSignature, ILinkSignature

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `ConfirmationMessage` | IExpression | get
- `Content` | IContent | get
- `CustomStyle` | String | get/set
- `Definition` | IWidgetDefinitionSignature | get
- `Descriptor` | ILinkDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Enabled` | IExpression | get
- `Events` | ISequence<IEvent> | get
- `ExtendedProperties` | ISequence<IExtendedProperty> | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `MarginLeft` | String | get/set
- `MarginTop` | String | get/set
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `OnClick` | IBuiltinEvent | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Style` | IExpression | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `Visible` | IExpression | get
- `WasDeleted` | Boolean | get
- `Widgets` | IEnumerable<IMobileWidget> | get
- `Width` | String | get/set

**Members** (setters/creators ranked first — signature → returns):
- `SetConfirmationMessage(ExpressionDefinition value)` → Void
- `SetEnabled(Boolean value)` → Void
- `SetEnabled(ExpressionDefinition value)` → Void
- `SetStyle(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `SetVisible(ExpressionDefinition value)` → Void
- `CreateEvent()` → IEvent
- `CreateExtendedProperty()` → IExtendedProperty
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CreateWidget(IWidgetDefinitionSignature widgetDefinition, String name, IKey key)` → IMobileWidget
- `CreateWidget<T>(String name, IKey key)` → T
- `CreateWidget(Type widgetType, String name, IKey key)` → IMobileWidget
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Delete(Boolean preserveChildren)` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IIcon
_ServiceStudio.Plugin.NRWidgets.IIcon_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IWidget, IWidgetSignature, IMobileWidget, IMobileWidgetSignature, IIconSignature

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `CustomStyle` | String | get/set
- `Definition` | IWidgetDefinitionSignature | get
- `Descriptor` | IIconDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Events` | ISequence<IEvent> | get
- `ExtendedProperties` | ISequence<IExtendedProperty> | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `Icon` | String | get/set
- `IconSize` | IconSize | get/set
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `MarginLeft` | String | get/set
- `MarginTop` | String | get/set
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Style` | IExpression | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `Visible` | IExpression | get
- `WasDeleted` | Boolean | get
- `Weight` | String | get/set

**Members** (setters/creators ranked first — signature → returns):
- `SetStyle(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `SetVisible(ExpressionDefinition value)` → Void
- `CreateEvent()` → IEvent
- `CreateExtendedProperty()` → IExtendedProperty
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Delete(Boolean preserveChildren)` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IPlaceholderWidget
_ServiceStudio.PluginAPI.Model.UI.IPlaceholderWidget_  
Inherits: IObjectWithWidgets, IVersionedObject, IModelObject, IObjectSignature, ICustomCommandTarget, IDraggableType, IWidgetSignature, IModelObjectWithName, IReferenceableObject, IWidget, IWidgetWithChildren

**Properties** (name | type | get/set):
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `CustomStyle` | String | get
- `Descriptor` | IClassDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Owner` | IContentNode | get
- `OwnerESpace` | IEspace | get
- `Parent` | ICustomWidget | get
- `PlaceholderDescriptor` | Placeholder | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `WasDeleted` | Boolean | get
- `Widgets` | IEnumerable<IWidget> | get

**Members** (setters/creators ranked first — signature → returns):
- `SetPropertyValue(String propertyName, Object value)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateWidget<WidgetType>()` → WidgetType
- `CreateWidget(CustomObjectDescriptor customObjectDescriptor)` → ICustomWidget
- `BehavesAs<T>()` → Boolean
- `CanMoveAfter()` → Boolean
- `CanMoveBefore()` → Boolean
- `CanMoveToIndex(Int32 index)` → Boolean
- `ChangeParent(IObjectWithWidgets newParent)` → Void
- `Delete()` → Void
- `FindParentWidgetOfType<T>()` → ICustomWidget
- `ForceValidate()` → Void
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetChildAtIndex(Int32 index)` → IWidget
- `GetESpace()` → IESpace
- `GetIndexInParent()` → Int32
- `GetInterface()` → Type
- `GetOwnerEspace()` → IEspace
- `GetParent()` → IModelObject
- `GetPropertyValue(String propertyName)` → Object
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `IsInside<T>()` → Boolean
- `IsInsideObjectWithDescriptor<T>()` → Boolean
- `IsOrIsInside<T>()` → Boolean
- `IsOrIsInsideObjectWithDescriptor<T>()` → Boolean
- `MoveAfter()` → Void
- `MoveBefore()` → Void
- `MoveToIndex(Int32 index)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IMobileBlockInstanceWidget
_OutSystems.Model.UI.Mobile.Widgets.IMobileBlockInstanceWidget_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IWidget, IWidgetSignature, IMobileWidget, IMobileWidgetSignature, IMobileBlockInstanceWidgetSignature

**Properties** (name | type | get/set):
- `Arguments` | IEnumerable<IArgument> | get
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `CustomStyle` | String | get/set
- `Definition` | IWidgetDefinitionSignature | get
- `Descriptor` | IMobileBlockInstanceWidgetDescriptor | get
- `DesignMode` | DesignMode | get/set
- `Digest` | String | get
- `DisplayName` | String | get
- `EventHandlers` | IEnumerable<IEventHandler> | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `PlaceholdersContent` | ISequence<IPlaceholderContentWidget> | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `SourceBlock` | IMobileBlockSignature | get/set
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Delete(Boolean preserveChildren)` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IWidget
_ServiceStudio.PluginAPI.Model.UI.IWidget_  
Inherits: IWidgetSignature, IVersionedObject, IModelObject, IObjectSignature, IModelObjectWithName, ICustomCommandTarget, IDraggableType, IReferenceableObject

**Properties** (name | type | get/set):
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `CustomStyle` | String | get
- `Descriptor` | IWidgetSignatureDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Owner` | IContentNode | get
- `OwnerESpace` | IEspace | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetPropertyValue(String propertyName, Object value)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `BehavesAs<T>()` → Boolean
- `CanMoveAfter()` → Boolean
- `CanMoveBefore()` → Boolean
- `CanMoveToIndex(Int32 index)` → Boolean
- `ChangeParent(IObjectWithWidgets newParent)` → Void
- `Delete()` → Void
- `FindParentWidgetOfType<T>()` → ICustomWidget
- `ForceValidate()` → Void
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetIndexInParent()` → Int32
- `GetInterface()` → Type
- `GetOwnerEspace()` → IEspace
- `GetParent()` → IModelObject
- `GetPropertyValue(String propertyName)` → Object
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `IsInside<T>()` → Boolean
- `IsInsideObjectWithDescriptor<T>()` → Boolean
- `IsOrIsInside<T>()` → Boolean
- `IsOrIsInsideObjectWithDescriptor<T>()` → Boolean
- `MoveAfter()` → Void
- `MoveBefore()` → Void
- `MoveToIndex(Int32 index)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IStartNode
_OutSystems.Model.Processes.Nodes.IStartNode_  
Inherits: IProcessNodeSignature, IVersionedObject, IModelObject, IObjectSignature, IFlowNodeSignature, IObject, IFlowNode, IProcessNode

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Connectors` | IEnumerable<IConnector> | get
- `CreatedBy` | String | get
- `Descriptor` | IStartNodeDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HorizontalPosition` | Int32 | get/set
- `IncomingConnectors` | IEnumerable<IConnector> | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsDisabled` | Boolean | get/set
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `LastMergedBy` | String | get
- `LastMergedDate` | DateTime | get
- `LastModifiedBy` | String | get
- `LastModifiedDate` | DateTime | get
- `Metadata` | ISequence<IMetadata> | get
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Targets` | ICollection<IProcessNode> | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `VerticalPosition` | Int32 | get/set
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IEndNode
_OutSystems.Model.Processes.Nodes.IEndNode_  
Inherits: IProcessNodeSignature, IVersionedObject, IModelObject, IObjectSignature, IFlowNodeSignature, IObject, IFlowNode, IProcessNode

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Connectors` | IEnumerable<IConnector> | get
- `CreatedBy` | String | get
- `Descriptor` | IEndNodeDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HorizontalPosition` | Int32 | get/set
- `IncomingConnectors` | IEnumerable<IConnector> | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsDisabled` | Boolean | get/set
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `LastMergedBy` | String | get
- `LastMergedDate` | DateTime | get
- `LastModifiedBy` | String | get
- `LastModifiedDate` | DateTime | get
- `Metadata` | ISequence<IMetadata> | get
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TerminateProcess` | Boolean | get/set
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `VerticalPosition` | Int32 | get/set
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IAssignNode
_OutSystems.Model.Logic.Nodes.IAssignNode_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IFlowNodeSignature, IFlowNode, IActionNode

**Properties** (name | type | get/set):
- `Assignments` | ISequence<IAssignment> | get
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Connectors` | IEnumerable<IConnector> | get
- `Descriptor` | IAssignNodeDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HorizontalPosition` | Int32 | get/set
- `IncomingConnectors` | IEnumerable<IConnector> | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsDisabled` | Boolean | get/set
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `Label` | String | get/set
- `Metadata` | ISequence<IMetadata> | get
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Target` | IActionNode | get/set
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `VerticalPosition` | Int32 | get/set
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateAssignment()` → IAssignment
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IIfNode
_OutSystems.Model.Logic.Nodes.IIfNode_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IFlowNodeSignature, IFlowNode, IActionNode

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Condition` | IExpression | get
- `Connectors` | IEnumerable<IConnector> | get
- `Descriptor` | IIfNodeDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `FalseTarget` | IActionNode | get/set
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HorizontalPosition` | Int32 | get/set
- `IncomingConnectors` | IEnumerable<IConnector> | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsDisabled` | Boolean | get/set
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `Label` | String | get/set
- `Metadata` | ISequence<IMetadata> | get
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `TrueTarget` | IActionNode | get/set
- `VerticalPosition` | Int32 | get/set
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetCondition(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void
- `SwapConnectors()` → Void

## IForEachNode
_OutSystems.Model.Logic.Nodes.IForEachNode_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IFlowNodeSignature, IFlowNode, IActionNode

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Connectors` | IEnumerable<IConnector> | get
- `CycleTarget` | IActionNode | get/set
- `Descriptor` | IForEachNodeDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HorizontalPosition` | Int32 | get/set
- `IncomingConnectors` | IEnumerable<IConnector> | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsDisabled` | Boolean | get/set
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `Label` | String | get/set
- `MaximumIterations` | IExpression | get
- `Metadata` | ISequence<IMetadata> | get
- `NodesWithinCycle` | IEnumerable<IActionNode> | get
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `RecordList` | IExpression | get
- `Referrers` | IEnumerable<IModelObject> | get
- `StartIndex` | IExpression | get
- `Target` | IActionNode | get/set
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `VerticalPosition` | Int32 | get/set
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetMaximumIterations(ExpressionDefinition value)` → Void
- `SetRecordList(ExpressionDefinition value)` → Void
- `SetStartIndex(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void
- `SwapConnectors()` → Void

## ISwitchNode
_OutSystems.Model.Logic.Nodes.ISwitchNode_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IFlowNodeSignature, IFlowNode, IActionNode

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Conditions` | ISequence<ISwitchCondition> | get
- `Connectors` | IEnumerable<IConnector> | get
- `Descriptor` | ISwitchNodeDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HorizontalPosition` | Int32 | get/set
- `IncomingConnectors` | IEnumerable<IConnector> | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsDisabled` | Boolean | get/set
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `Label` | String | get/set
- `Metadata` | ISequence<IMetadata> | get
- `ObjectKey` | IKey | get
- `OtherwiseTarget` | IActionNode | get/set
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `VerticalPosition` | Int32 | get/set
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateCondition()` → ISwitchCondition
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IExecuteActionNode

_Not found under that name._ Near: 

## IExecuteClientActionNode
_OutSystems.Model.Logic.Nodes.IExecuteClientActionNode_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IFlowNodeSignature, IFlowNode, IActionNode

**Properties** (name | type | get/set):
- `Action` | IActionSignature | get/set
- `Arguments` | IEnumerable<IArgument> | get
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Connectors` | IEnumerable<IConnector> | get
- `Descriptor` | IExecuteClientActionNodeDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HorizontalPosition` | Int32 | get/set
- `IncomingConnectors` | IEnumerable<IConnector> | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsDisabled` | Boolean | get/set
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Target` | IActionNode | get/set
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `VerticalPosition` | Int32 | get/set
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IAggregateNode
_OutSystems.Model.Logic.Nodes.IAggregateNode_  
Inherits: IFlowNodeSignature, IVersionedObject, IModelObject, IObjectSignature, IFlowNode, IObject, IActionNode, IAggregate

**Properties** (name | type | get/set):
- `AsDatabaseAggregate` | IDatabaseAggregate | get
- `AsFullAggregate` | IFullAggregate | get
- `CacheInMinutes` | Nullable<Int32> | get/set
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Connectors` | IEnumerable<IConnector> | get
- `Description` | String | get/set
- `Descriptor` | IAggregateNodeDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HorizontalPosition` | Int32 | get/set
- `ImplicitParameters` | ISequence<IImplicitParameter> | get
- `IncomingConnectors` | IEnumerable<IConnector> | get
- `IndexInParent` | Int32 | get
- `IsClientSide` | Boolean | get
- `IsDetached` | Boolean | get
- `IsDisabled` | Boolean | get/set
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `MaxRecords` | IExpression | get
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `StartIndex` | IExpression | get
- `Target` | IActionNode | get/set
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `Timeout` | Nullable<Int32> | get/set
- `TransactionsManager` | ITransactionsManager | get
- `Type` | ITypeSignature | get
- `VerticalPosition` | Int32 | get/set
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetMaxRecords(ExpressionDefinition value)` → Void
- `SetStartIndex(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IJSONDeserializeNode
_OutSystems.Model.Logic.Nodes.IJSONDeserializeNode_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IFlowNodeSignature, IFlowNode, IActionNode

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Connectors` | IEnumerable<IConnector> | get
- `DataType` | ITypeSignature | get/set
- `DateFormat` | JSONDateFormat | get/set
- `Description` | String | get/set
- `Descriptor` | IJSONDeserializeNodeDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HorizontalPosition` | Int32 | get/set
- `IncomingConnectors` | IEnumerable<IConnector> | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsDisabled` | Boolean | get/set
- `IsValid` | Boolean | get
- `JSONString` | IExpression | get
- `Key` | IKey | get
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Target` | IActionNode | get/set
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `VerticalPosition` | Int32 | get/set
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetJSONString(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IRefreshDataNode
_OutSystems.Model.Logic.Nodes.IRefreshDataNode_  
Inherits: IObject, IVersionedObject, IModelObject, IObjectSignature, IFlowNodeSignature, IFlowNode, IActionNode

**Properties** (name | type | get/set):
- `Arguments` | IEnumerable<IArgument> | get
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Connectors` | IEnumerable<IConnector> | get
- `DataSource` | IObject | get/set
- `Descriptor` | IRefreshDataNodeDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HorizontalPosition` | Int32 | get/set
- `IncomingConnectors` | IEnumerable<IConnector> | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsDisabled` | Boolean | get/set
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `MaxRecords` | IExpression | get
- `Metadata` | ISequence<IMetadata> | get
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `StartIndex` | IExpression | get
- `Target` | IActionNode | get/set
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `VerticalPosition` | Int32 | get/set
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetMaxRecords(ExpressionDefinition value)` → Void
- `SetStartIndex(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## INode
_ServiceStudio.Model.Interfaces.INode_  
Inherits: IVersionedObject, IModelObject, IObjectSignature, ICustomCommandTarget, IDraggableType, IDraggableObject, IDropTarget, IPasteTarget, ICommandTarget, IImportTarget, IXmlSerializable, IObjectWithIdentifier, ISSSerializable, ITrackableObject, IObject

**Properties** (name | type | get/set):
- `AsAbstractNode` | AbstractNode | get
- `AsAbstractObject` | AbstractObject | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Collections` | IEnumerable<CollectionMetadata> | get
- `Descriptor` | IClassDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `Id` | IObjectIdentifier | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `New` | Boolean | get/set
- `Object` | AbstractObject | get
- `ObjectKey` | IKey | get
- `OwnerESpace` | ESpace | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TagName` | String | get
- `TransactionsManager` | ITransactionsManager | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetPropertyValue(String propertyName, Object value)` → Void
- `Delete()` → Void
- `ForceValidate()` → Void
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetInterface()` → Type
- `GetOwnerEspace()` → IEspace
- `GetParent()` → IModelObject
- `GetPropertyValue(String propertyName)` → Object
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `IsInside<T>()` → Boolean
- `IsInsideObjectWithDescriptor<T>()` → Boolean
- `IsOrIsInside<T>()` → Boolean
- `IsOrIsInsideObjectWithDescriptor<T>()` → Boolean
- `IsValidForToolbar()` → Boolean
- `LoadChildren(IXmlDeserializer loader)` → Void
- `LoadPropertyAttributes(IObjectAttributeReader loader)` → Void
- `LoadPropertyElements(IObjectAttributeReader loader)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void
- `SaveChildren(IXmlSerializer saver)` → Void
- `SavePropertyAttributes(IXmlSerializer saver)` → Void
- `SavePropertyElements(IXmlSerializer saver)` → Void
- `Serialize(IBinarySerializer writer)` → Void

## IMobileScreen
_OutSystems.Model.UI.Mobile.IMobileScreen_  
Inherits: IShareableESpaceObject`2, IObjectSignature, IVersionedObject, IModelObject, IObject, IShareable, IShareableESpaceObject, IMobileScreenSignature, IMobileFlowNodeSignature, IFlowNodeSignature, IUIFlowNodeSignature, IScreenSignature, IMobileFlowNode, IFlowNode, IUIFlowNode, IScreen

**Properties** (name | type | get/set):
- `AnonymousAccess` | Boolean | get/set
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Connectors` | IEnumerable<IConnector> | get
- `CreatedBy` | String | get
- `CreatedByTool` | CreatedByTool | get
- `CustomURL` | Boolean | get/set
- `DataActions` | IEnumerable<IDataAction> | get
- `Description` | String | get
- `Descriptor` | IMobileScreenDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HorizontalPosition` | Int32 | get/set
- `Icon` | Byte[] | get
- `IncomingConnectors` | IEnumerable<IConnector> | get
- `IndexInParent` | Int32 | get
- `InputParameters` | IEnumerable<IInputParameterSignature> | get
- `IsDetached` | Boolean | get
- `IsDisabled` | Boolean | get/set
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `LastMergedBy` | String | get
- `LastMergedDate` | DateTime | get
- `LastModifiedBy` | String | get
- `LastModifiedByTool` | CreatedByTool | get
- `LastModifiedDate` | DateTime | get
- `LocalVariables` | ISequence<ILocalVariable> | get
- `Metadata` | ISequence<IMetadata> | get
- `ModifiedByTools` | CreatedByTool | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `OnDestroy` | IUILifeCycleEvent | get
- `OnInitialize` | IUILifeCycleEvent | get
- `OnReady` | IUILifeCycleEvent | get
- `OnRender` | IUILifeCycleEvent | get
- `OnSyncComplete` | IOnSyncCompleteEvent | get
- `OnSyncError` | IOnSyncErrorEvent | get
- `OnSyncStart` | IOnSyncStartEvent | get
- `PageName` | String | get/set
- `Parent` | IModelObject | get
- `Public` | Boolean | get/set
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `RequiredScripts` | ICollection<IScriptSignature> | get
- `Roles` | ICollection<IRoleSignature> | get
- `ScreenActions` | IEnumerable<IScreenAction> | get
- `ScreenAggregates` | IEnumerable<IScreenAggregate> | get
- `StyleSheet` | String | get/set
- `Targets` | ICollection<IUIFlowNode> | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `Title` | IExpression | get
- `TransactionsManager` | ITransactionsManager | get
- `URLStructure` | URLStructure | get/set
- `VerticalPosition` | Int32 | get/set
- `WasDeleted` | Boolean | get
- `Widgets` | ISequence<IMobileWidget> | get

**Members** (setters/creators ranked first — signature → returns):
- `SetTitle(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateDataAction(String name, IKey key)` → IDataAction
- `CreateInputParameter(String name, IKey key)` → IInputParameter
- `CreateLocalVariable(String name, IKey key)` → ILocalVariable
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOnSyncComplete()` → IOnSyncCompleteEvent
- `CreateOnSyncError()` → IOnSyncErrorEvent
- `CreateOnSyncStart()` → IOnSyncStartEvent
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateScreenAction(String name, IKey key)` → IScreenAction
- `CreateScreenAggregate(Boolean isClientSide, String name, IKey key)` → IScreenAggregate
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CreateWidget(IWidgetDefinitionSignature widgetDefinition, String name, IKey key)` → IMobileWidget
- `CreateWidget<T>(String name, IKey key)` → T
- `CreateWidget(Type type, String name, IKey key)` → IWidget
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceEntity(IEntitySignature oldEntity, IEntitySignature newEntity, Dictionary<IEntityAttributeSignature,IEntityAttributeSignature> attributesMapping)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IScreenAggregate
_OutSystems.Model.UI.Mobile.IScreenAggregate_  
Inherits: IVersionedObject, IModelObject, IObjectSignature, IObject, IAggregate

**Properties** (name | type | get/set):
- `AsDatabaseAggregate` | IDatabaseAggregate | get
- `AsFullAggregate` | IFullAggregate | get
- `CacheInMinutes` | Nullable<Int32> | get/set
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Description` | String | get/set
- `Descriptor` | IScreenAggregateDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Fetch` | DataSourceFetch | get/set
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `ImplicitParameters` | ISequence<IImplicitParameter> | get
- `IndexInParent` | Int32 | get
- `IsClientSide` | Boolean | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `MaxRecords` | IExpression | get
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `OnAfterFetch` | IUILifeCycleEvent | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `StartIndex` | IExpression | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `Timeout` | Nullable<Int32> | get/set
- `TransactionsManager` | ITransactionsManager | get
- `Type` | ITypeSignature | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetMaxRecords(ExpressionDefinition value)` → Void
- `SetStartIndex(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## ILocalVariable
_ServiceStudio.PluginAPI.Model.ILocalVariable_  
Inherits: IDraggableModelObject`1, IVersionedObject, IModelObject, IObjectSignature, ICustomCommandTarget, IDraggableType

**Properties** (name | type | get/set):
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Descriptor` | IClassDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TransactionsManager` | ITransactionsManager | get
- `Type` | TypeKind | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetPropertyValue(String propertyName, Object value)` → Void
- `Delete()` → Void
- `ForceValidate()` → Void
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetInterface()` → Type
- `GetOwnerEspace()` → IEspace
- `GetParent()` → IModelObject
- `GetPropertyValue(String propertyName)` → Object
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `IsInside<T>()` → Boolean
- `IsInsideObjectWithDescriptor<T>()` → Boolean
- `IsOrIsInside<T>()` → Boolean
- `IsOrIsInsideObjectWithDescriptor<T>()` → Boolean
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IInputParameter
_ServiceStudio.PluginAPI.Model.IInputParameter_  
Inherits: IDraggableModelObject`1, IVersionedObject, IModelObject, IObjectSignature, ICustomCommandTarget, IDraggableType

**Properties** (name | type | get/set):
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Descriptor` | IClassDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TransactionsManager` | ITransactionsManager | get
- `Type` | TypeKind | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetPropertyValue(String propertyName, Object value)` → Void
- `Delete()` → Void
- `ForceValidate()` → Void
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetInterface()` → Type
- `GetOwnerEspace()` → IEspace
- `GetParent()` → IModelObject
- `GetPropertyValue(String propertyName)` → Object
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `IsInside<T>()` → Boolean
- `IsInsideObjectWithDescriptor<T>()` → Boolean
- `IsOrIsInside<T>()` → Boolean
- `IsOrIsInsideObjectWithDescriptor<T>()` → Boolean
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IOutputParameter
_OutSystems.Model.IOutputParameter_  
Inherits: IOutputParameterSignature, IVersionedObject, IModelObject, IObjectSignature, IObject

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `DataType` | ITypeSignature | get/set
- `DefaultValue` | IExpression | get
- `Description` | String | get/set
- `Descriptor` | IOutputParameterDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IndexInParent` | Int32 | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TransactionsManager` | ITransactionsManager | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetDefaultValue(ExpressionDefinition value)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IClientScreenAction

_Not found under that name._ Near: ConversionFromFlows_ActivityToNRFlows_ClientScreenActionFlow, ConversionFromFlows_CustomActionFlowToNRFlows_ClientScreenActionFlow, ConversionFromFlows_DecisionToNRFlows_ClientScreenActionFlow, ConversionFromFlows_EmailPreparationToNRFlows_ClientScreenActionFlow, ConversionFromFlows_OnCloseToNRFlows_ClientScreenActionFlow

## IClientAction
_ServiceStudio.Model.Interfaces.IClientAction_  
Inherits: IVersionedObject, IModelObject, IObjectSignature, ICustomCommandTarget, IDraggableType, IDraggableObject, IDropTarget, IPasteTarget, ICommandTarget, IImportTarget, IXmlSerializable, IObjectWithIdentifier, ISSSerializable, ITrackableObject, IObject, ICallable, IAction

**Properties** (name | type | get/set):
- `AsAbstractObject` | AbstractObject | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Collections` | IEnumerable<CollectionMetadata> | get
- `Descriptor` | IClassDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `Id` | IObjectIdentifier | get
- `InputParameters` | IEnumerable<AbstractInputParameter> | get
- `IsDetached` | Boolean | get
- `IsFunction` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `LocalVariables` | ISSSequence<LocalVariable> | get
- `New` | Boolean | get/set
- `Object` | AbstractObject | get
- `ObjectKey` | IKey | get
- `OutputParameters` | IEnumerable<AbstractOutputParameter> | get
- `OwnerESpace` | ESpace | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TagName` | String | get
- `TransactionsManager` | ITransactionsManager | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetPropertyValue(String propertyName, Object value)` → Void
- `Delete()` → Void
- `ForceValidate()` → Void
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetInterface()` → Type
- `GetOwnerEspace()` → IEspace
- `GetParent()` → IModelObject
- `GetPropertyValue(String propertyName)` → Object
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `IsInside<T>()` → Boolean
- `IsInsideObjectWithDescriptor<T>()` → Boolean
- `IsOrIsInside<T>()` → Boolean
- `IsOrIsInsideObjectWithDescriptor<T>()` → Boolean
- `IsValidForToolbar()` → Boolean
- `LoadChildren(IXmlDeserializer loader)` → Void
- `LoadPropertyAttributes(IObjectAttributeReader loader)` → Void
- `LoadPropertyElements(IObjectAttributeReader loader)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void
- `SaveChildren(IXmlSerializer saver)` → Void
- `SavePropertyAttributes(IXmlSerializer saver)` → Void
- `SavePropertyElements(IXmlSerializer saver)` → Void
- `Serialize(IBinarySerializer writer)` → Void

## IServerAction
_OutSystems.Model.Logic.IServerAction_  
Inherits: IShareable, IVersionedObject, IModelObject, IShareableESpaceObject, IObjectSignature, IObject, IShareableESpaceObject`2, IServerActionSignature, IFlowSignature, IActionSignature, IFlow, IAction

**Properties** (name | type | get/set):
- `CacheInMinutes` | Nullable<Int32> | get/set
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `CreatedBy` | String | get/set
- `CreatedByTool` | CreatedByTool | get
- `Description` | String | get/set
- `Descriptor` | IServerActionDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Folder` | IFolder | get/set
- `Function` | Boolean | get/set
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `Icon` | Byte[] | get/set
- `IndexInParent` | Int32 | get
- `InputParameters` | IEnumerable<IInputParameterSignature> | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `LastMergedBy` | String | get
- `LastMergedDate` | DateTime | get
- `LastModifiedBy` | String | get/set
- `LastModifiedByTool` | CreatedByTool | get
- `LastModifiedDate` | DateTime | get/set
- `LocalVariables` | ISequence<ILocalVariable> | get
- `Metadata` | ISequence<IMetadata> | get
- `ModifiedByTools` | CreatedByTool | get
- `Name` | String | get/set
- `Nodes` | IEnumerable<IActionNode> | get
- `ObjectKey` | IKey | get
- `OutputParameters` | IEnumerable<IOutputParameterSignature> | get
- `Parent` | IModelObject | get
- `Public` | Boolean | get/set
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateInputParameter(String name, IKey key)` → IInputParameter
- `CreateLocalVariable(String name, IKey key)` → ILocalVariable
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateNode<T>(String name, IKey key)` → T
- `CreateNode(Type type, String name, IKey key)` → IActionNode
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateOutputParameter(String name, IKey key)` → IOutputParameter
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IServiceAction
_OutSystems.Model.Logic.IServiceAction_  
Inherits: IShareable, IVersionedObject, IModelObject, IShareableESpaceObject, IObjectSignature, IObject, IShareableESpaceObject`2, IServiceActionSignature, IFlowSignature, IActionSignature, IFlow, IAction

**Properties** (name | type | get/set):
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `CreatedBy` | String | get/set
- `CreatedByTool` | CreatedByTool | get
- `Description` | String | get/set
- `Descriptor` | IServiceActionDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Folder` | IFolder | get/set
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `Icon` | Byte[] | get/set
- `IndexInParent` | Int32 | get
- `InputParameters` | IEnumerable<IInputParameterSignature> | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `LastMergedBy` | String | get
- `LastMergedDate` | DateTime | get
- `LastModifiedBy` | String | get/set
- `LastModifiedByTool` | CreatedByTool | get
- `LastModifiedDate` | DateTime | get/set
- `LocalVariables` | ISequence<ILocalVariable> | get
- `Metadata` | ISequence<IMetadata> | get
- `ModifiedByTools` | CreatedByTool | get
- `Name` | String | get/set
- `Nodes` | IEnumerable<IActionNode> | get
- `ObjectKey` | IKey | get
- `OutputParameters` | IEnumerable<IOutputParameterSignature> | get
- `Parent` | IModelObject | get
- `Public` | Boolean | get/set
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `TransactionsManager` | ITransactionsManager | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateInputParameter(String name, IKey key)` → IInputParameter
- `CreateLocalVariable(String name, IKey key)` → ILocalVariable
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateNode<T>(String name, IKey key)` → T
- `CreateNode(Type type, String name, IKey key)` → IActionNode
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateOutputParameter(String name, IKey key)` → IOutputParameter
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IEntity
_OutSystems.Model.Extensions.IEntity_  
Inherits: IType, IVersionedObject, IModelObject, IExtensionObject, IRecordType, IShareable, IShareableExtensionObject, IShareableExtensionObject`2

**Properties** (name | type | get/set):
- `Attributes` | ISequence<IEntityAttribute> | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `ConvertDefaultValueToFromNullInDatabase` | Boolean | get/set
- `Description` | String | get/set
- `Descriptor` | IEntityDescriptor | get
- `DisplayName` | String | get
- `ExposeAsReadOnly` | Boolean | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `HideCreateEntity` | Boolean | get
- `HideCreateOrUpdateAllEntity` | Boolean | get
- `HideCreateOrUpdateEntity` | Boolean | get
- `HideDeleteAllEntity` | Boolean | get
- `HideDeleteEntity` | Boolean | get
- `HideGetEntity` | Boolean | get
- `HideGetEntityForUpdate` | Boolean | get
- `HideUpdateEntity` | Boolean | get
- `IdentifierAttribute` | IEntityAttribute | get/set
- `IdentifierType` | IIdentifierType | get
- `IsDetached` | Boolean | get
- `IsStaticEntity` | Boolean | get
- `Key` | IKey | get
- `LogicalDatabase` | String | get/set
- `Metadata` | IEnumerable<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `Referrers` | IEnumerable<IModelObject> | get
- `SourceCodeExcluded` | Boolean | get
- `TableOrViewDefaultName` | String | get/set
- `TransactionsManager` | ITransactionsManager | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `CreateAttribute(String name, IKey key)` → IEntityAttribute
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `Delete()` → Void
- `GetExtension()` → IExtension
- `GetInterface()` → Type

## IStructure
_OutSystems.Model.ExternalLibraries.IStructure_  
Inherits: IExtensionObject, IVersionedObject, IModelObject, IType, IExternalLibraryObject, IShareable, IShareableExternalLibraryObject, IShareableExternalLibraryObject`2

**Properties** (name | type | get/set):
- `Attributes` | ISequence<IStructureAttribute> | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Description` | String | get/set
- `Descriptor` | IStructureDescriptor | get
- `DisplayName` | String | get
- `ExternalLibrary` | IExternalLibrary | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `IsDetached` | Boolean | get
- `Key` | IKey | get
- `Metadata` | IEnumerable<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `Referrers` | IEnumerable<IModelObject> | get
- `TransactionsManager` | ITransactionsManager | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `Delete()` → Void
- `GetExtension()` → IExtension
- `GetInterface()` → Type

## IMobileTheme
_OutSystems.Model.UI.Mobile.IMobileTheme_  
Inherits: IShareableESpaceObject`2, IObjectSignature, IVersionedObject, IModelObject, IObject, IShareable, IShareableESpaceObject, IMobileThemeSignature, IThemeSignature, ITheme

**Properties** (name | type | get/set):
- `BaseTheme` | IMobileThemeSignature | get/set
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `ColumnWidth` | Int32 | get
- `Columns` | Int32 | get
- `CreatedBy` | String | get
- `Description` | String | get
- `Descriptor` | IMobileThemeDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `FirstThemeWithGrid` | IMobileThemeSignature | get
- `Folder` | IFolderSignature | get
- `Footer` | IMobileBlockSignature | get/set
- `GeneratedStyleSheet` | String | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `GridType` | GridType | get
- `GutterWidth` | Int32 | get
- `GutterWidthPercentage` | Int32 | get
- `Header` | IMobileBlockSignature | get/set
- `IconLibrary` | String | get/set
- `IndexInParent` | Int32 | get
- `InvisibleStyleSheet` | String | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Key` | IKey | get
- `LastMergedBy` | String | get
- `LastMergedDate` | DateTime | get
- `LastModifiedBy` | String | get
- `LastModifiedDate` | DateTime | get
- `Layout` | IMobileBlockSignature | get/set
- `MaxWidth` | Nullable<Int32> | get
- `Menu` | IMobileBlockSignature | get/set
- `Metadata` | ISequence<IMetadata> | get
- `MinWidth` | Nullable<Int32> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `Public` | Boolean | get/set
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `StyleSheet` | String | get
- `StyleSheetExpression` | ITextWithReferencedElements | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `ThemeValues` | IEnumerable<IThemeValuesSignature> | get
- `TotalWidth` | Int32 | get
- `TransactionsManager` | ITransactionsManager | get
- `UserStyleSheet` | String | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `AddOrUpdateThemeValues(Dictionary<ThemeProperty,String> properties)` → Void
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `IsBasedOnModelPlugin()` → ValueTuple<Boolean,String,String,Version>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

## IDatabaseAggregate
_OutSystems.Model.Logic.Aggregates.Database.IDatabaseAggregate_  
Inherits: IVersionedObject, IModelObject, IObjectSignature, IObject, IAggregate

**Properties** (name | type | get/set):
- `AggregatedAttributes` | IEnumerable<IAggregatedAttribute> | get
- `AsDatabaseAggregate` | IDatabaseAggregate | get
- `AsFullAggregate` | IFullAggregate | get
- `CacheInMinutes` | Nullable<Int32> | get/set
- `CalculatedAttributes` | IEnumerable<ICalculatedAttribute> | get
- `CalculatedAttributesInGroupBy` | IEnumerable<ICalculatedAttribute> | get
- `CanMoveAfter` | Boolean | get
- `CanMoveBefore` | Boolean | get
- `Children` | IEnumerable<IModelObject> | get
- `CollectionDescriptor` | IChildCollection | get
- `Description` | String | get/set
- `Descriptor` | IClassDescriptor | get
- `Digest` | String | get
- `DisplayName` | String | get
- `Filters` | ISequence<IFilter> | get
- `FiltersInGroupBy` | ISequence<IFilter> | get
- `Generation` | Int64 | get
- `GlobalKey` | IGlobalKey | get
- `GroupByAttributes` | IEnumerable<IGroupByAttribute> | get
- `ImplicitParameters` | ISequence<IImplicitParameter> | get
- `IndexInParent` | Int32 | get
- `IsClientSide` | Boolean | get
- `IsDetached` | Boolean | get
- `IsValid` | Boolean | get
- `Joins` | ISequence<IJoin> | get
- `Key` | IKey | get
- `MasterSource` | IAliasedSource | get
- `MaxRecords` | IExpression | get
- `Metadata` | ISequence<IMetadata> | get
- `Name` | String | get/set
- `ObjectKey` | IKey | get
- `Parent` | IModelObject | get
- `ReadableIdentifier` | String | get
- `Referrers` | IEnumerable<IModelObject> | get
- `Sorts` | ISequence<ISort> | get
- `SortsInGroupBy` | ISequence<ISort> | get
- `Sources` | IEnumerable<IAliasedSource> | get
- `StartIndex` | IExpression | get
- `TextResources` | IEnumerable<ITextResource> | get
- `TextResourcesIds` | IEnumerable<String> | get
- `Timeout` | Nullable<Int32> | get/set
- `TransactionsManager` | ITransactionsManager | get
- `Type` | ITypeSignature | get
- `WasDeleted` | Boolean | get

**Members** (setters/creators ranked first — signature → returns):
- `SetMaxRecords(ExpressionDefinition value)` → Void
- `SetStartIndex(ExpressionDefinition value)` → Void
- `SetTranslationBehavior(String id, TranslationBehavior behavior)` → Void
- `CreateAggregatedAttribute(String name, IKey key)` → IAggregatedAttribute
- `CreateCalculatedAttribute(String name, IKey key)` → ICalculatedAttribute
- `CreateCalculatedAttributeInGroupBy(String name, IKey key)` → ICalculatedAttribute
- `CreateFilter(String condition, IKey key)` → IFilter
- `CreateFilterInGroupBy(String condition, IKey key)` → IFilter
- `CreateGroupByAttribute(String name, IKey key)` → IGroupByAttribute
- `CreateJoin(IKey key)` → IJoin
- `CreateMetadata<T>(String name, String managedBy, IKey key)` → T
- `CreateOrUpdateTranslation(Culture culture, String id, String value)` → Void
- `CreateSibling<T>(String name, IKey key)` → T
- `CreateSibling(Type type, String name, IKey key)` → IModelObject
- `CreateSort(IKey key)` → ISort
- `CreateSortInGroupBy(IKey key)` → ISort
- `CreateSource(IDataSource dataSource, String name, IKey key)` → IAliasedSource
- `CanMoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Boolean
- `CanMoveToNewRelativeIndex(Int32 newRelativeIndex)` → Boolean
- `Copy(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Copy(IObjectSignature obj)` → IObjectSignature
- `Delete()` → Void
- `Duplicate(IEnumerable<IObjectSignature> objects)` → IEnumerable<IObjectSignature>
- `Duplicate(IObjectSignature obj)` → IObjectSignature
- `GetAllDescendantsOfType<T>()` → IEnumerable<T>
- `GetESpace()` → IESpace
- `GetEnvironment(IExpressionProperty property)` → IEnvironment
- `GetInterface()` → Type
- `GetValidationMessages(Boolean includeMessagesFromDescendants)` → IEnumerable<IValidationMessage>
- `MoveAfter()` → Void
- `MoveAfterSibling(IObject sibling)` → Void
- `MoveBefore()` → Void
- `MoveBeforeSibling(IObject sibling)` → Void
- `MoveToEnd()` → Void
- `MoveToNewAbsoluteIndex(Int32 newAbsoluteIndex)` → Void
- `MoveToNewRelativeIndex(Int32 newRelativeIndex)` → Void
- `ReplaceReferences(IObjectSignature previousObject, IObjectSignature newObject)` → Void

