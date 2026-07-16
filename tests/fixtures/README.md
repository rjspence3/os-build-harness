# Test Fixtures

## basf_trimmed_spec.md

A trimmed slice of the BASF Wyandotte Maintenance Requests specification
(`BASF-Modernized-Spec.md`), hand-curated for deterministic unit and integration
testing of `harness/spec_ingest.py`.

The trim preserves:
- H1 title + `**Application**:` line
- `#### Entities` / `##### MaintenanceRequest` (~10 attrs covering the full type
  variety the mapper tests need: Auto Number, FK patterns, User Id, Text (2000),
  Text (unlimited), Date, Date Time, Boolean, Text (N)) + `##### Building`
- `#### Static Entities` / `##### RequestStatus` (Record|Label|Order, 6 rows)
  + `##### RequestType` (Record|Label only)
- `### Roles` / `#### Role Definitions` (bold names) + `#### Permissions Matrix`
- `#### MaintenanceRequestCreate` with Data Table (8 rows spanning Dropdown,
  DatePicker, Read-only badge, Text, Radio, User picker) + Actions table
- Short SAP + Excel-batch prose (for integration extraction)
- `**Transition rules:**` table (for workflow-note extraction)

**Not** a faithful reproduction of the full spec — sections are dropped or
abbreviated to keep the fixture small and test-deterministic. Do not use this
file to understand the real application requirements.

Provenance: trimmed from `BASF-Modernized-Spec.md` (internal, not checked in).
