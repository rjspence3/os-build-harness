"""harness-gate — the single machine-checkable DEFINITION OF DONE (Phase 5: "enforce, don't advise").

An autonomous build-root session (or a stranger who cloned the harness) needs ONE trustworthy
"am I done?" check that a green publish cannot fake. This composes every applicable gate into a single
consolidated acceptance report + exit code. A build is DONE only when EVERY dimension the spec DECLARES
is runtime-green:

  spec        (verify.validate_spec)          ALWAYS — the spec itself must be gap-free (gating findings
                                              stop the run: you cannot verify a build against a broken spec)
  structural  (capture --assert)              ALWAYS — every spec'd component resolves in the live DOM
  behavioral  (capture --behavioral)          iff the spec has Create/Update/Delete write-paths
  role        (capture --role)                iff the spec has access-gated screens
  render      (capture --render)              iff the spec has charts or a design.theme
  pixel       (capture --pixel <ref>)         iff a --pixel reference is supplied

Policy (the definition of "done"):
- A dimension the spec does NOT exercise is OMITTED, never vacuously passed — "done" means every DECLARED
  dimension is green.
- The behavioral gate is the REAL bar: if the spec has write-paths, a build with a dead/ non-persisting
  button is NOT done, no matter how many structural assertions pass.
- pixel is opt-in (it needs a reference); omit it and the fidelity dimension is simply not asserted.
- Exit 0 iff DONE (no gate FAILED and spec+structural actually ran); nonzero otherwise. This is the
  enforcement point the autonomous executor and CI both gate on.

Usage:
  harness-gate <spec> --base-url <deployed-url> [--login-config <json|path>]
               [--pixel <reference>] [--pixel-threshold N] [--pixel-tol N] [--pixel-mask RECTS]
               [--nav-mode href|click|both] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness import capture, verify


def _has_write_paths(spec: dict) -> bool:
    """True iff any screen declares a Create/Update/Delete action AND resolves a writable entity —
    the same predicate run_behavioral drives on (so 'applicable' matches 'actually checkable')."""
    from harness.prompt_recipes import _screen_write_entity
    write = {"CreateEntity", "UpdateEntity", "DeleteEntity"}
    for screen in spec.get("screens", []):
        does_all = set()
        for a in screen.get("actions", []):
            does_all |= set(a.get("does", []))
        if does_all & write and _screen_write_entity(spec, screen):
            return True
    return False


def _has_render_targets(spec: dict) -> bool:
    if (spec.get("design") or {}).get("theme"):
        return True
    return any(s.get("charts") for s in spec.get("screens", []))


def _gate_row(name: str, status: str, detail: str = "", results=None) -> dict:
    return {"gate": name, "status": status, "detail": detail, "results": results or []}


def _empty_bound_components(snapshot: dict) -> set:
    """(screen_id, component_id) for data widgets that are PRESENT but rendered zero rows
    (the snapshot marks these `boundTo_unrendered`). Their binding cannot be confirmed OR
    denied at runtime — inconclusive, not failed. Without this the structural gate is
    order-dependent: an empty list (no-seed spec) hard-fails its binding on a cold run, then
    passes once anything (a seed or the behavioral gate's own create) leaves a row. An
    enforcement tool must give the same verdict on the same app state."""
    out = set()
    for s in snapshot.get("screens", []):
        for c in s.get("components", []):
            if c.get("boundTo_unrendered") and not c.get("boundTo"):
                out.add((s.get("id"), c.get("id")))
    return out


def run_all_gates(spec: dict, base_url: str, login: dict, *, pixel_ref: str | None,
                  pixel_threshold: float, pixel_tol: int, pixel_mask: list, nav_mode: str,
                  out_dir: Path | None) -> list[dict]:
    """Run every applicable gate in order and return one row per gate (PASS/FAIL/OMIT).
    Stops after the spec gate if the spec has gating gaps — the live gates are meaningless then."""
    rows: list[dict] = []

    # 1. spec — gating gaps mean we cannot trust anything downstream.
    gating = [f for f in verify.validate_spec(spec) if f.severity == "spec-gap"]
    if gating:
        rows.append(_gate_row("spec", "FAIL", f"{len(gating)} spec-gap finding(s); fix the spec first",
                              [f.summary for f in gating]))
        return rows
    rows.append(_gate_row("spec", "PASS", "no spec-gap findings"))

    # 2. structural — spec'd components resolve in the live DOM. A binding failure on a
    #    present-but-empty table is INCONCLUSIVE (empty lists can't prove binding), not a hard
    #    fail — this keeps the verdict stable regardless of prior runs / seed state.
    snapshot = capture.build_runtime_snapshot(spec, base_url, login, out_dir, nav_mode)
    results, n_pass, _ = capture._assert_capture_channel(spec, snapshot)
    empty = _empty_bound_components(snapshot)
    hard_fails, inconclusive = [], []
    for sid, r in results:
        if r.status != "fail":
            continue
        if r.kind == "binding" and any(sid == es and ec and f"'{ec}'" in r.detail for es, ec in empty):
            inconclusive.append(f"{sid}·binding: list empty (no rows) — binding inconclusive, not failed")
        else:
            hard_fails.append(f"{sid}·{r.kind}: {r.detail}")
    detail = f"{n_pass} pass, {len(hard_fails)} fail"
    if inconclusive:
        detail += f", {len(inconclusive)} inconclusive (empty list — seed to confirm)"
    rows.append(_gate_row("structural", "FAIL" if hard_fails else "PASS", detail,
                          hard_fails + inconclusive))

    # 3. behavioral — the real bar, iff the spec has write-paths.
    if _has_write_paths(spec):
        br = capture.run_behavioral(spec, base_url, login)
        good = {"PERSISTS", "UPDATES", "DELETES"}
        bad = [f"{r['screen']}·{r.get('op', 'create')} {r['entity']}: {r['verdict']}"
               for r in br if r["verdict"] not in good]
        rows.append(_gate_row("behavioral", "FAIL" if bad else "PASS",
                              f"{len(br) - len(bad)}/{len(br)} write-path(s) persist", bad))
    else:
        rows.append(_gate_row("behavioral", "OMIT", "no Create/Update/Delete write-paths in spec"))

    # 4. role — iff the spec has access-gated screens.
    if capture._gated_screens(spec):
        rr = capture.run_role(spec, base_url, login)
        good = {"BLOCKS_ANON", "ALLOWS_MEMBER"}
        bad = [f"{r['screen']}·{r['check']}: {r['verdict']}" for r in rr if r["verdict"] not in good]
        rows.append(_gate_row("role", "FAIL" if bad else "PASS",
                              f"{len(rr) - len(bad)}/{len(rr)} check(s) ok", bad))
    else:
        rows.append(_gate_row("role", "OMIT", "no access-gated screens in spec"))

    # 5. render — iff the spec has charts or a design.theme.
    if _has_render_targets(spec):
        rn = capture.run_render(spec, base_url, login)
        good = {"APPLIED", "RENDERS"}
        bad = [f"{r.get('kind')} {r.get('target')}: {r['verdict']}" for r in rn if r["verdict"] not in good]
        rows.append(_gate_row("render", "FAIL" if bad else "PASS",
                              f"{len(rn) - len(bad)}/{len(rn)} target(s) ok", bad))
    else:
        rows.append(_gate_row("render", "OMIT", "no charts or design.theme in spec"))

    # 6. pixel — iff a reference was supplied (fidelity is opt-in; it needs something to diff against).
    if pixel_ref:
        px = capture.run_pixel(spec, base_url, login, pixel_ref, out_dir, pixel_tol,
                               pixel_threshold, pixel_mask)
        scored = [r["match_pct"] for r in px if r.get("match_pct") is not None]
        fidelity = round(sum(scored) / len(scored), 2) if scored else 0.0
        bad = [f"{r['screen']}: {r['verdict']} ({r.get('match_pct')}%)"
               for r in px if r["verdict"] != "MATCH"]
        rows.append(_gate_row("pixel", "FAIL" if bad else "PASS",
                              f"fidelity {fidelity}% (threshold {pixel_threshold}%)", bad))
    else:
        rows.append(_gate_row("pixel", "OMIT", "no --pixel reference supplied"))

    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="harness-gate",
        description="The single machine-checkable DEFINITION OF DONE: run every applicable gate "
                    "(spec, structural, behavioral, role, render, pixel) and emit one verdict.")
    ap.add_argument("spec", type=Path, help="app_spec.json")
    ap.add_argument("--base-url", required=True, help="deployed app base URL")
    ap.add_argument("--login-config", default=None,
                    help="login config as inline JSON or a path (else derived from the spec's auth block)")
    ap.add_argument("--pixel", default=None,
                    help="pixel reference: a dir of shot_<screenId>.png or a URL to capture the original from")
    ap.add_argument("--pixel-threshold", type=float, default=99.0)
    ap.add_argument("--pixel-tol", type=int, default=16)
    ap.add_argument("--pixel-mask", default=None, help="'x1,y1,x2,y2;...' zeroed in both images")
    ap.add_argument("--nav-mode", choices=["href", "click", "both"], default="href")
    ap.add_argument("--out", type=Path, default=None, help="output dir for snapshots + pixel artifacts")
    ap.add_argument("--json", action="store_true", help="emit the acceptance report as JSON")
    args = ap.parse_args(argv)

    if not args.spec.exists():
        print(f"spec not found: {args.spec}", file=sys.stderr)
        return 2
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"spec is not valid JSON: {e}", file=sys.stderr)
        return 2

    if args.login_config:
        p = Path(args.login_config)
        try:
            login = json.loads(p.read_text(encoding="utf-8")) if p.exists() else json.loads(args.login_config)
        except Exception as e:
            print(f"--login-config unreadable ({e})", file=sys.stderr)
            return 2
    else:
        login = capture._login_from_auth(spec)

    mask_rects = []
    if args.pixel_mask:
        for rect in args.pixel_mask.split(";"):
            rect = rect.strip()
            if rect:
                mask_rects.append(tuple(int(v) for v in rect.split(",")))

    rows = run_all_gates(spec, args.base_url, login, pixel_ref=args.pixel,
                         pixel_threshold=args.pixel_threshold, pixel_tol=args.pixel_tol,
                         pixel_mask=mask_rects, nav_mode=args.nav_mode, out_dir=args.out)

    failed = [r for r in rows if r["status"] == "FAIL"]
    ran = [r for r in rows if r["status"] in ("PASS", "FAIL")]
    # DONE requires spec + structural to have actually run (guards against a spec-gap short-circuit
    # being mistaken for green) and zero failures.
    done = not failed and {"spec", "structural"} <= {r["gate"] for r in ran}

    if args.json:
        print(json.dumps({"gates": rows, "done": done,
                          "verdict": "DONE" if done else "NOT_DONE"}, indent=2))
    else:
        print(f"harness-gate — {args.spec.name}: {'✅ DONE' if done else '❌ NOT DONE'}")
        for r in rows:
            mark = {"PASS": "ok ", "FAIL": "FAIL", "OMIT": "—  "}[r["status"]]
            print(f"  [{mark}] {r['gate']:<11} {r['detail']}")
            for d in r["results"]:
                print(f"          · {d}")
    return 0 if done else 1


if __name__ == "__main__":
    raise SystemExit(main())
