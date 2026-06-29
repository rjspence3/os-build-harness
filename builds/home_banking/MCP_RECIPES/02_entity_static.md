# Recipe 02 — Static Entity (enum w/ records)

## Purpose

Create ONE static entity with the canonical OutSystems shape:
- Primary key: usually `Id` Text(50) but Integer or other PKs supported
- Standard attribute set: `Label` (Text), often `Order` (Int) and `Is_Active` (Bool)
- Pre-loaded records (the enum values)

Static entities are the OutSystems equivalent of database-backed enums. They appear in
Studio as a special icon, can be referenced via `Entities.<Name>.<RecordIdentifier>` in
expressions, and are commonly used for status fields, categories, lookup tables, and
display-order tables.

This recipe creates the entity + records in ONE Mentor turn. The records become available
to other recipes (like FK attribute creation) immediately within the same session.

## Inputs the caller fills in

| Placeholder | Meaning | Example |
|---|---|---|
| `{{ENTITY_NAME}}` | PascalCase entity name | `LoanRequestStatus` |
| `{{PK_NAME}}` | Primary key attribute name (usually `Id`) | `Id` |
| `{{PK_DATATYPE}}` | `eSpace.TextType` (Id text-50) or `eSpace.IntegerType` | `eSpace.TextType` |
| `{{PK_LENGTH}}` | If Text PK, length (usually 50). Omit for Integer. | `50` |
| `{{EXTRA_ATTRS_BLOCK}}` | C# lines that AddText/AddBool/.../AddInt the other attributes | (see example) |
| `{{RECORDS_BLOCK}}` | C# lines that create each record with its column values | (see example) |

### Extra attributes — common patterns

```csharp
AddText(e, "Label", 50, true);              // every static needs a Label
AddInt(e, "Order");                          // for display ordering
AddBool(e, "Is_Active");                     // for soft-deletion semantics
AddText(e, "Color", 20, false);              // for status chips
AddText(e, "IconName", 50, false);           // for FA / Lucide refs
AddBool(e, "HideOnApprove");                 // domain-specific extras
```

### Records — the enum values

For each enum value, create one record + set its attribute values. The Identifier becomes
the value users reference in expressions (e.g. `Entities.LoanRequestStatus.Submitted`).

```csharp
{
    var r = e.CreateRecord("Submitted");
    SetRecordAttr(e, r, "Label", "\"Submitted\"");
    SetRecordAttr(e, r, "Order", "1");
    SetRecordAttr(e, r, "Is_Active", "True");
}
```

## Mentor prompt (paste verbatim, with {{}} substituted)

```csharp
eSpace => {
    // ─── Per-type attribute helpers (same as recipe 01) ───
    void AddText(OutSystems.Model.Data.IStaticEntity ent, string name, int length, bool mandatory) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.TextType;
        a.Length = length;
        a.IsMandatory = mandatory;
    }
    void AddBool(OutSystems.Model.Data.IStaticEntity ent, string name) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.BooleanType;
    }
    void AddInt(OutSystems.Model.Data.IStaticEntity ent, string name) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.IntegerType;
    }

    // Record-attribute setter (handles literal expression strings)
    void SetRecordAttr(OutSystems.Model.Data.IStaticEntity ent,
                       OutSystems.Model.Data.IRecord rec,
                       string attrName, string valueExpr) {
        var attr = ent.Attributes.First(a => a.Name == attrName);
        rec.SetAttributeValue(attr, valueExpr);
    }

    // ─── Create static entity + PK ───────────────────────────────────────────
    var e = eSpace.CreateStaticEntity("{{ENTITY_NAME}}");
    // v2 (2026-06-08): mark Public so cross-app addReferenceToElements imports it.
    // Same concrete class implements IServerEntity + IStaticEntity, so this
    // matches the entity_server recipe's pattern.
    e.Public = true;

    var pkAttr = e.CreateAttribute("{{PK_NAME}}");
    pkAttr.DataType = {{PK_DATATYPE}};
    pkAttr.Length = {{PK_LENGTH}};
    pkAttr.IsMandatory = true;
    e.IdentifierAttribute = pkAttr;

    // ─── Extra attributes (Label, Order, Is_Active, domain extras) ──────────
    {{EXTRA_ATTRS_BLOCK}}

    // ─── Records (enum values) ──────────────────────────────────────────────
    {{RECORDS_BLOCK}}

    Console.WriteLine($"Recipe 02: {{ENTITY_NAME}} | Created: PK={pkAttr.Name} + {e.Attributes.Count() - 1} attrs + {e.Records.Count()} records | Status: OK");
}
```

Required imports:

```
System.Linq
OutSystems.Model
OutSystems.Model.Data
```

## Expected stdout

```
Recipe 02: LoanRequestStatus | Created: PK=Id + 3 attrs + 10 records | Status: OK
```

## Common failures + paste-ready fixes

### ✗ `Object with name 'Submitted' already exists in the records collection`

Cause: re-running the recipe against an existing entity. CreateRecord doesn't overwrite.
Fix: this recipe is for FIRST creation. For modification, use a separate recipe that deletes + recreates the records, or sets attribute values on existing records via `e.Records.First(r => r.Identifier == "Submitted")`.

### ✗ `Invalid Length` validation warning

Cause: Text PK without Length set, or Length > 50.
Fix: ODC static-entity Text PKs are conventionally Length=50. Other Text attributes can go higher (up to 2000). Set explicitly.

## Example: LoanRequestStatus from Home Banking Core

From the catalog: `LoanRequestStatus (static, 10 attrs, 10 records)`.

```csharp
// {{ENTITY_NAME}}      = "LoanRequestStatus"
// {{PK_NAME}}          = "Id"
// {{PK_DATATYPE}}      = eSpace.TextType
// {{PK_LENGTH}}        = 50

// {{EXTRA_ATTRS_BLOCK}}:
AddText(e, "Label", 50, true);
AddInt(e, "Order");
AddBool(e, "Is_Active");
AddText(e, "Color", 20, false);
AddText(e, "IconName", 50, false);
AddText(e, "Description", 500, false);
AddBool(e, "AllowTransitionFromHere");
AddInt(e, "SLA_Hours");
AddBool(e, "IsFinalState");

// {{RECORDS_BLOCK}}:
{ var r = e.CreateRecord("Submitted");
  SetRecordAttr(e, r, "Label", "\"Submitted\"");
  SetRecordAttr(e, r, "Order", "1");
  SetRecordAttr(e, r, "Is_Active", "True");
  SetRecordAttr(e, r, "IsFinalState", "False"); }
{ var r = e.CreateRecord("Underwriting");
  SetRecordAttr(e, r, "Label", "\"Underwriting\"");
  SetRecordAttr(e, r, "Order", "2");
  /* ... */ }
// ... 10 records total
```

## Memory refs

- [[odc_native_sample_data_pattern]] — for cases where seed records are loaded separately from entity creation
- [[odc_mcp_record_literal_via_typed_local]] — relevant when you need to reference these record identifiers in Server Actions

## Related recipes

- [01_entity_server](./01_entity_server.md) — when a server entity's FK points to this static entity
- [99_publish_verify](./99_publish_verify.md) — to verify records made it through publish
