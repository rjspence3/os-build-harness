# Golden reference build — RivianReviewer4 (proven "what worked")

The **16 rendered Mentor prompts** here are the exact sequence that built `RivianReviewer4`
end-to-end, **16/16 steps landed, 0 failed** — a data-complete, on-design Rivian Supplier &
Parts Onboarding app with working write-paths. Mined from the 6 live builds as the definitive
best (Reviewer3 = data-complete; Reviewer4 = + create/edit write-paths).

- App: RivianReviewer4 (app_key 988774de-b1e2-4c9e-8758-cc0e434bf14d)
- URL: https://robertjspencedemos-dev.outsystems.app/RivianReviewer4
- Spec that produced it: golden.app_spec.json (from gen_reviewer_spec.py)
- Verified live: sidebar+theme+styled data on every screen; case-detail stepper+reviews+timeline
  populated; create-supplier form persists a row.

This is the regression baseline: the recipe set + these prompts reproduce a full working app.
The remaining polish (fonts via @font-face, workflow buttons) is staged in gen_reviewer_spec.py
for the next clean build once the Mentor session cap releases.
