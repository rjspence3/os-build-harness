# Recipe 01 — Server Entity (PK + typed attributes + FK delete rules)

## Purpose

Create ONE server entity with the canonical OutSystems shape:
- Long Integer auto-number `Id` as primary key (set immediately, before first publish)
- Strongly typed user attributes (Text/Boolean/Integer/Decimal/DateTime)
- Foreign-key attributes typed against existing entities (local static or referenced)
- DeleteRule = Ignore on all FKs (avoids the OS-BLD-40409 deprecated-Protect wall)

This recipe **must run in the same session as entity creation** and **the caller must publish before any subsequent operation on this entity**. Per [[odc_db_upgrade_pk_change_blocked]], you cannot change a published entity's PK after the fact.

## Inputs the caller fills in

| Placeholder | Meaning | Example |
|---|---|---|
| `{{ENTITY_NAME}}` | PascalCase entity name | `LoanRequest` |
| `{{ENTITY_DESCRIPTION}}` | One-sentence description (set on entity.Description) | `Tracks customer loan applications through underwriting` |
| `{{ATTRIBUTES_BLOCK}}` | The lines that call AddText/AddBool/.../AddIdentFk (see below) | (paste a block like the example) |

### Attribute-block syntax

Each line in `{{ATTRIBUTES_BLOCK}}` is one of:

```csharp
AddText(e, "{{name}}", {{length}}, {{mandatory}});
AddBool(e, "{{name}}");
AddInt(e, "{{name}}");
AddDecimal(e, "{{name}}", {{length}}, {{decimals}});
AddDateTime(e, "{{name}}", {{mandatory}});
AddIdentFk(e, "{{name}}", {{identType_expr}}, {{mandatory}});
```

For FK identifier expressions, use one of these resolutions (declared in the
recipe before the attribute block):

```csharp
// User identifier (most common — for SubmittedById, AssignedToId etc.)
var userIdentType = eSpace.References.SelectMany(r => r.Entities)
    .First(e => e.Name == "User").IdentifierType;

// Local static entity (for Status enums, Categories, etc.)
var loanStatus = eSpace.Entities.OfType<OutSystems.Model.Data.IStaticEntity>()
    .Named("LoanRequestStatus");
// then use loanStatus.IdentifierType
```

## Mentor prompt (paste verbatim, with {{}} substituted)

```csharp
eSpace => {
    // ─── FK type resolution (only include the ones the entity actually uses) ───
    var userIdentType = eSpace.References.SelectMany(r => r.Entities)
        .First(e => e.Name == "User").IdentifierType;

    // example: local static entity reference for a status enum FK
    // var loanStatus = eSpace.Entities.OfType<OutSystems.Model.Data.IStaticEntity>().Named("LoanRequestStatus");

    // ─── Per-type attribute helpers ───────────────────────────────────────────
    void AddText(OutSystems.Model.Data.IServerEntity ent, string name, int length, bool mandatory) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.TextType;
        a.Length = length;
        a.IsMandatory = mandatory;
    }
    void AddBool(OutSystems.Model.Data.IServerEntity ent, string name) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.BooleanType;
    }
    void AddInt(OutSystems.Model.Data.IServerEntity ent, string name) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.IntegerType;
    }
    void AddDecimal(OutSystems.Model.Data.IServerEntity ent, string name, int length, int decimals) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.DecimalType;
        a.Length = length;
        a.Decimals = decimals;
    }
    void AddDateTime(OutSystems.Model.Data.IServerEntity ent, string name, bool mandatory) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.DateTimeType;
        a.IsMandatory = mandatory;
    }
    void AddDate(OutSystems.Model.Data.IServerEntity ent, string name, bool mandatory) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.DateType;
        a.IsMandatory = mandatory;
    }
    void AddLongInt(OutSystems.Model.Data.IServerEntity ent, string name, bool mandatory) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.LongIntegerType;
        a.IsMandatory = mandatory;
    }
    void AddCurrency(OutSystems.Model.Data.IServerEntity ent, string name, bool mandatory) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.CurrencyType;
        a.IsMandatory = mandatory;
    }
    void AddBinary(OutSystems.Model.Data.IServerEntity ent, string name) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.BinaryDataType;
    }
    void AddEmail(OutSystems.Model.Data.IServerEntity ent, string name, int length, bool mandatory) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.EmailType;
        a.Length = length;
        a.IsMandatory = mandatory;
    }
    void AddPhone(OutSystems.Model.Data.IServerEntity ent, string name, int length, bool mandatory) {
        var a = ent.CreateAttribute(name);
        a.DataType = eSpace.PhoneNumberType;
        a.Length = length;
        a.IsMandatory = mandatory;
    }
    void AddIdentFk(OutSystems.Model.Data.IServerEntity ent, string name,
                     OutSystems.Model.Types.IIdentifierType identType, bool mandatory) {
        // Null-safe: if the FK target entity wasn't found (missing Manage
        // Dependencies on the consumer app, or hallucinated entity name in
        // manifest), skip the attribute creation with a loud WARN. Without
        // this guard, `a.DataType = null` produces an invalid OML that AVS
        // rejects with the opaque OS-APPS-40028 closure-rule error at
        // publish time, far from the actual cause. Loud-fail-fast is better.
        // Baked Portal Phase Rebake1 2026-06-02 after Employee was absent on
        // greenfield Core (no AppsCommonCore dep yet).
        if (identType == null) {
            // FK target not found at runtime — skip the attr with a warning so
            // the rest of the entity authors clean and AVS doesn't reject the
            // OML for a null DataType. See memory note on Mentor's body-level
            // qualifier allowlist for why this uses bare Console.WriteLine.
            Console.WriteLine($"WARN: skipping FK {name} on entity {ent.Name} — FK target not found (missing Manage Dependencies?). Add the dep + re-run, or fix the manifest.");
            return;
        }
        var a = ent.CreateAttribute(name);
        a.DataType = identType;
        a.IsMandatory = mandatory;
        a.DeleteRule = OutSystems.Model.Enumerations.DeleteRule.Ignore;
    }

    // ─── Create entity + Id PK (must be first attribute, set IdentifierAttribute immediately) ───
    var e = eSpace.CreateServerEntity("{{ENTITY_NAME}}");
    e.Description = "{{ENTITY_DESCRIPTION}}";
    // v2 (2026-06-08): mark Public so cross-app addReferenceToElements can import
    // this entity. Verified live on HomeBankingCoreRebake1 rev 17→19 — entity.Public
    // is the only required flip; same concrete class implements IServerEntity +
    // IStaticEntity so this loop covers both. See [[odc_mcp_entity_public_for_cross_app_ref]].
    e.Public = true;

    var idAttr = e.CreateAttribute("Id");
    idAttr.DataType = eSpace.LongIntegerType;
    idAttr.IsAutoNumber = OutSystems.Model.Enumerations.AutoNumber.Yes;
    idAttr.IsMandatory = true;
    e.IdentifierAttribute = idAttr;

    // ─── User attributes ──────────────────────────────────────────────────────
    {{ATTRIBUTES_BLOCK}}

    // ─── Diagnostic output (single line) ──────────────────────────────────────
    Console.WriteLine($"Recipe 01: {{ENTITY_NAME}} | Created: PK=Id + {e.Attributes.Count() - 1} attrs | Status: OK");
}
```

Required imports (paste into the recipe call's `imports` array):

```
System.Linq
OutSystems.Model
OutSystems.Model.Data
OutSystems.Model.Enumerations
OutSystems.Model.Types
```

## Expected stdout

```
Recipe 01: LoanRequest | Created: PK=Id + 29 attrs | Status: OK
```

## Common failures + paste-ready fixes

### ✗ `Identifier of existing Entity 'X' cannot be changed` at publish (OS-RDBS-GEN-40003)

Cause: the entity already exists at a prior revision without a PK. You're trying to add one.
Fix: this recipe is for FIRST-publish entities only. For an existing PK-less entity, you must delete + recreate. See [[odc_db_upgrade_pk_change_blocked]] for the recovery sequence.

### ✗ `Using the feature ModelFeature_DeleteRuleOnReferences` at publish (OS-BLD-40409)

Cause: One of your FK attributes still has `DeleteRule = Protect` (the deprecated default). The recipe sets Ignore via `AddIdentFk`, so this only happens if you bypassed the helper.
Fix: For every FK attribute on the entity, set `attr.DeleteRule = OutSystems.Model.Enumerations.DeleteRule.Ignore`. Then republish.

### ✗ `Object reference not set to an instance of an object` at runtime

Cause: A type lookup failed before any attribute was added. Most common: looking up the `User` entity in `eSpace.Entities` instead of `eSpace.References` — User lives in (System) module.
Fix: Use the `eSpace.References.SelectMany(r => r.Entities).First(e => e.Name == "User").IdentifierType` pattern shown at the top of the recipe.

## Example: HBCustomer entity from Home Banking Core

```csharp
// {{ENTITY_NAME}}       = "HBCustomer"
// {{ENTITY_DESCRIPTION}} = "Banking customer master record"
// {{ATTRIBUTES_BLOCK}}:

AddText(e, "FirstName", 100, true);
AddText(e, "LastName", 100, true);
AddText(e, "Email", 200, true);
AddText(e, "PhoneNumber", 50, false);
AddDateTime(e, "DateOfBirth", false);
AddText(e, "Address", 500, false);
AddText(e, "City", 100, false);
AddText(e, "State", 50, false);
AddText(e, "PostalCode", 20, false);
AddText(e, "SSNLast4", 4, false);
AddDateTime(e, "OnboardedAt", false);
AddBool(e, "IsActive");
AddBool(e, "MarketingOptIn");
AddIdentFk(e, "BranchId", branchEntity.IdentifierType, false);
// ... 22 attrs total
```

## Memory refs

- [[odc_mcp_entity_auto_actions_incomplete]] — explains why PK must be set explicitly
- [[odc_db_upgrade_pk_change_blocked]] — explains why PK must be set on first publish
- [[odc_mcp_record_literal_via_typed_local]] — relevant when this entity is used as a record type in a Server Action

## Related recipes

- [02_entity_static](./02_entity_static.md) — for the static enum entities this one's FKs point to
- [04_action_crud](./04_action_crud.md) — to create CRUD actions against this entity
- [07_screen_table](./07_screen_table.md) — to render a list of this entity's rows
- [99_publish_verify](./99_publish_verify.md) — to lock the entity into a revision after this recipe runs
