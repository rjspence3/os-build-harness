# IMPORT INSTRUCTIONS — Employee producer reference (WALL-001)

**Why:** The original Home Banking Core keys `HBAccount.AssignedToEmpId` and `LoanRequest.AssignedToEmpId`
to an external **Employee** entity. The clone app `harnessbuild_hbcore` does not yet reference the producer
that owns it, so the renderer WARN-skipped both FKs. This is the D9 "missing external dependency" fall-out
pattern — the harness can re-author the FKs via MCP, but a human must add the producer reference because
the right `Employee` must be pinned among look-alikes. **It has been pinned (see below) — no guesswork left.**

## Pinned producer (verified 2026-06-17)
- **Consumer app:** `harnessbuild_hbcore` — key `bf7ed15f-1819-4a65-a6f6-4b5d8528bfd4` (env Development)
- **Producer app:** `AppsCommonCore` — key `4ba075ee-bb56-43a2-adc2-a81271fa5ee2`
- **Element to import:** the **`Employee`** entity — key `86dabd64-5219-49da-8965-8535260ab309` (public)
- Provenance: the original Core (`695efc5b`) `HBAccount.AssignedToEmpId.foreignKey` →
  `producerAssetKey = 4ba075ee… (AppsCommonCore)`, `entityKey = 86dabd64… (Employee)`,
  `globalKey = 7nWgS1a7okOtwqgScfpe4g*NhdArZzjwU235L3l5_35vQ`. The globalKey's producer-half decodes
  exactly to `4ba075ee… (AppsCommonCore)` via `library_keys.compute_global_key`, confirming the producer.
  (The element-half decodes to `ad401736-e39c-4dc1-b7e4-bde5e7fdf9bd`, Employee's identifier attribute —
  importing the entity brings it.)

## Steps (ODC Studio — Manage Dependencies)
1. Open **ODC Studio** and open the app **`harnessbuild_hbcore`** (Development).
2. Open **Manage Dependencies** (the dependencies / "Add public elements" dialog).
3. In the producer list, select **`AppsCommonCore`** (`4ba075ee-bb56-43a2-adc2-a81271fa5ee2`).
4. Under its **Entities**, check **`Employee`**. (Only Employee is required; check `EmployeePicture` too only
   if you want it for later avatar fidelity — not needed for WALL-001.)
5. Click **Apply** / **OK** to stage the dependency.
6. **Publish** `harnessbuild_hbcore` so the reference materializes.

## After you confirm the import is published
Tell the driver session "Employee imported". It will then, via one Mentor turn + publish:
- add `AssignedToEmpId` → `Employee.IdentifierType` (DeleteRule = Ignore, **IsMandatory = false** — matches the
  original) on **`HBAccount`** and on **`LoanRequest`**, then verify both FKs are present.

This dependency does **not** block the visual phases — the driver proceeds with blocks/theme/screens while this
is pending, and re-adds the two FKs once you confirm.
