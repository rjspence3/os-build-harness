# WALLS — 01_support_triage live build

## WALL-001 [mcp-wall] — RESOLVED
SupportCore publish fails persistently with OS-DPL-50203 (database migration script generation).

RESOLUTION (2026-07-11): after applying the corrected data model (Text length 255/2000, AuditEvent.At →
DateTime, Changed-Attributes update behavior) via a fresh delete-and-recreate turn AND a ~20-min cooldown,
SupportCore published clean on the FIRST attempt — deployed at revision 4, all 5 entities Public with the
corrected types/lengths verified live via context_entities. Cannot fully isolate cause (model change +
cooldown both applied); most likely the earlier failures were a transient migration-generator window, since
the model was valid before too. If OS-DPL-50203 recurs on another app: retry after a cooldown first, then
rebuild-fresh. Original detail retained below.

- context: SupportCore (app 92f0ad79-2031-4949-bb0b-2047b65ffc2f), first publish of the data model
  (Customer, PolicyDoc, Ticket, ResolutionAction, AuditEvent — all Public, Id identifiers, 3 FKs).
  Mentor authoring succeeded, model validation returned 0 errors. Publish `failed{OS-DPL-50203}` after
  3 server-side retries; a second bounded-recovery publish also failed{OS-DPL-50203} after 3 retries (6 total).
- tried: one bounded-recovery re-publish (same result). Not thrashing further per the no-blind-republish rule.
- needs: investigation. OS-DPL-50203 is deployment-side (DB migration script gen), NOT a validation error —
  minutes earlier RivianScreenProbe + KnowledgeAgent (entities + FKs) published fine on the same tenant/env,
  so the tenant was healthy just before. Leading hypotheses (most→least likely):
    1) TRANSIENT migration-generator infra. The tenant was healthy minutes earlier and the model is clean;
       6 attempts inside a ~3-min window can all fall in one bad window. Retry in a few hours, model unchanged
       — cheapest first move, no code change.
    2) rebuild FRESH under a new name (B1 wedge-rebuild) to rule out per-app OML/deploy-state corruption from
       the failed attempts.
  A reserved-word column (e.g. `AuditEvent.At`) is UNLIKELY the cause: ODC mangles physical column/table names
  (observed `suppl_nvfjvqme3i3tndy6rrn52r71`), so a source attribute named `At` should not reach the DB as a
  reserved token. Only worth probing if (1) and (2) both fail.
- STATUS: open. The offline suite is unaffected (specs + app_specs verified). This blocks only the LIVE build
  of #1 SupportCore; all other apps depend on it, so the #1 live build is paused here.
