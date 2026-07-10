"""harness-build-system — the CROSS-APP executor: drive a whole modular topology to built + gated,
in topo order, producer-before-consumer, with NO hand execution.

`run_system` PLANS (topo order + per-app steps); this EXECUTES that plan across apps. It closes the
orchestration hole that made a modular build a pile of ad-hoc shell scripts:

- **Deterministic naming** — every app is `<prefix><LogicalName>` (e.g. Rivian + OnboardingCore =
  RivianOnboardingCore). A consumer's `appReferences[].producerApp` is rewritten to `<prefix><producer>`
  so cross-app references resolve BY CONSTRUCTION — no manual `--core` threading (closes gap B4).
- **Producer-before-consumer** — topo_order guarantees a producer is built + published (SpecDriver
  publishes per step) before any consumer that references it is built.
- **Reuses SpecDriver per app** — so each app inherits session-reuse, cap-cascade, the B1 compile-wedge
  halt-fast (→ this executor rebuilds that app FRESH under a new suffix rather than grinding), the B3
  transient-401 ride-out, and publish-failure diagnostics.
- **Seed trigger** — after a data-owning app builds, its deployed Home is loaded to fire the OnReady seed.
- **Resumable** — per-app StateDB; a completed app is skipped on re-run.

    harness-build-system <system.json> --prefix Rivian [--domain domain.json] [--tenant host]
    harness-build-system <domain.json> --domain-only --prefix Rivian   # decompose first
"""
from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from harness import architecture, decompose, expand
from harness.run_system import topo_order, _apps, _producers, _kind_of

# Map the topology's app KIND to run_build/app_create kinds.
_KIND_TO_CREATE = {
    "WebApplication": "CrossDevice", "Mobile": "Mobile", "MobileApplication": "Mobile",
    "AIAgent": "AIAgent", "BusinessProcess": "BusinessProcess", "Library": "ReactiveLibrary",
}


@dataclass
class AppResult:
    name: str
    logical: str
    layer: str
    ok: bool = False
    app_key: Optional[str] = None
    halted_at: Optional[str] = None
    succeeded: int = 0
    failed: int = 0
    total: int = 0
    note: str = ""


@dataclass
class SystemResult:
    modular: bool
    order: list[str] = field(default_factory=list)
    apps: list[AppResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.modular and all(a.ok for a in self.apps)


def _tenant_name(prefix: str, logical: str) -> str:
    return f"{prefix}{logical}"


def _rewrite_producer_refs(spec: dict, prefix: str) -> dict:
    """Point every appReferences[].producerApp at its DETERMINISTIC tenant name (<prefix><logical>),
    so the consumer references the producer this run actually builds — no manual threading."""
    for ref in spec.get("appReferences", []) or []:
        producer_logical = ref.get("producerApp", "")
        # already-prefixed names pass through; bare logical names get the prefix.
        if producer_logical and not producer_logical.startswith(prefix):
            ref["producerApp"] = _tenant_name(prefix, producer_logical)
    return spec


async def _resolve_or_create_by_name(mcp, name: str, kind: str) -> Optional[str]:
    """The tenant app_key for `name`: resolve it if it already exists (idempotent / resume), else create."""
    from harness.run_build import resolve_or_create_app, _rows
    try:
        listing = await mcp.app_list(search=name) if hasattr(mcp, "app_list") else None
    except Exception:
        listing = None
    if listing:
        for app in _rows(listing):
            if (app.get("name") or app.get("assetName")) == name:
                return app.get("assetKey") or app.get("key")
    return await resolve_or_create_app(mcp, app_key=None, create=True, name=name, kind=kind)


async def _trigger_seed(mcp, app_key: str, env_key: str) -> None:
    """Fire a data-owner's OnReady seed by loading its deployed Home (best-effort, browser-free HTTP)."""
    getter = getattr(mcp, "env_app", None)
    if getter is None:
        return
    try:
        info = await getter(app_key, env_key)
        url = (info or {}).get("url")
    except Exception:
        return
    if not url:
        return
    try:
        import urllib.request
        for _ in range(2):
            urllib.request.urlopen(url.rstrip("/") + "/Home", timeout=30).read()
    except Exception:
        pass


async def build_system(system: dict, domain: Optional[dict], *, prefix: str, tenant: Optional[str] = None,
                       env_key: Optional[str] = None, state_dir: Optional[Path] = None,
                       prompts_dir: Optional[Path] = None, mcp=None,
                       per_call_timeout: int = 700, max_wedge_rebuilds: int = 1) -> SystemResult:
    """Execute a modular topology to built apps, topo order, producer-before-consumer. Pass `mcp` to
    inject a client (tests); else opens a live MentorMCP. Libraries are skipped (recipe path)."""
    rows = architecture.check_system(system)
    if not architecture.verdict(rows):
        return SystemResult(modular=False)

    exp = expand.expand_system(system, domain)
    specs, libraries = exp["specs"], set(exp["libraries"])
    by_name = {a["name"]: a for a in _apps(system)}
    order = topo_order(system)
    result = SystemResult(modular=True, order=order)

    state_dir = Path(state_dir) if state_dir else Path(".")
    prompts_dir = Path(prompts_dir) if prompts_dir else Path("./_system_prompts")

    async def _run_with(client):
        from harness.run_build import SpecDriver, resolve_env_key
        from harness.build_state import StateDB
        ek = env_key if env_key is not None else await resolve_env_key(client, None)
        for logical in order:
            app = by_name[logical]
            if logical in libraries:
                result.apps.append(AppResult(name=_tenant_name(prefix, logical), logical=logical,
                                             layer=app.get("layer", ""), ok=True, note="library (recipe path — skipped)"))
                continue
            spec = specs.get(logical)
            if not spec:
                result.apps.append(AppResult(name=_tenant_name(prefix, logical), logical=logical,
                                             layer=app.get("layer", ""), note="no spec emitted"))
                continue
            spec = _rewrite_producer_refs(json.loads(json.dumps(spec)), prefix)
            create_kind = _KIND_TO_CREATE.get(_kind_of(app), "CrossDevice")
            owns_seed = any(e.get("sampleData") for e in (spec.get("dataModel", {}) or {}).get("entities", []))

            base_name = _tenant_name(prefix, logical)
            ares = AppResult(name=base_name, logical=logical, layer=app.get("layer", ""))
            wedge_attempt = 0
            while True:
                name = base_name if wedge_attempt == 0 else f"{base_name}V{wedge_attempt+1}"
                print(f"\n########## {name} ({create_kind}) — layer={app.get('layer')} ##########")
                app_key = await _resolve_or_create_by_name(client, name, create_kind)
                if not app_key:
                    ares.note = "could not resolve/create app"
                    break
                ares.app_key, ares.name = app_key, name
                slug = name.lower()
                db = StateDB(state_dir / f"{slug}.state.json")
                driver = SpecDriver(client, prompts_dir / slug, per_call_timeout=per_call_timeout,
                                    db=db, env_key=ek)
                report = await driver.build(spec, app_key, app_name=name)
                db.close()
                ares.succeeded, ares.failed, ares.total = report.succeeded, report.failed, report.total
                ares.halted_at = report.halted_at
                if report.ok:
                    ares.ok = True
                    if owns_seed:
                        await _trigger_seed(client, app_key, ek)
                    break
                # B1: a COMPILE-WEDGED app can't be salvaged in place — rebuild FRESH under a new name.
                if report.halted_at and "COMPILE-WEDGED" in " ".join(
                        s.outcome for s in report.steps if s.outcome) and wedge_attempt < max_wedge_rebuilds:
                    wedge_attempt += 1
                    print(f"    ↻ {name} compile-wedged — rebuilding FRESH as {base_name}V{wedge_attempt+1}")
                    continue
                ares.note = f"halted at {report.halted_at}"
                break

            result.apps.append(ares)
            if not ares.ok:
                print(f"    ✗ {ares.name} did not complete ({ares.note}); stopping (consumers depend on it).")
                break
        return result

    if mcp is not None:
        return await _run_with(mcp)
    from harness.mcp_client import MentorMCP
    mcp_kwargs = {"tenant": tenant} if tenant else {}
    async with MentorMCP(**mcp_kwargs) as client:
        return await _run_with(client)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="harness-build-system",
                                 description="Execute a modular topology to built apps — topo order, no hand execution.")
    ap.add_argument("spec", type=Path, help="system_spec.json (or a domain spec with --domain-only)")
    ap.add_argument("--prefix", required=True, help="tenant app-name prefix (e.g. Rivian); every app is <prefix><Logical>")
    ap.add_argument("--domain", type=Path, default=None, help="domain spec (for entity attributes during expand)")
    ap.add_argument("--domain-only", action="store_true", help="the positional spec IS a domain spec — decompose it first")
    ap.add_argument("--tenant", default=None, help="ODC tenant hostname override")
    ap.add_argument("--env-key", default=None, help="ODC environment key (default: auto-resolve Dev)")
    ap.add_argument("--state-dir", type=Path, default=None, help="dir for per-app StateDBs (resumable)")
    ap.add_argument("--prompts-dir", type=Path, default=None, help="dir for rendered prompts")
    ap.add_argument("--plan-only", action="store_true", help="print the topo order + per-app step counts and exit")
    args = ap.parse_args(argv)

    raw = json.loads(args.spec.read_text())
    domain = json.loads(args.domain.read_text()) if args.domain else (raw if args.domain_only else None)
    system = decompose.decompose(raw)["system"] if args.domain_only else raw

    if args.plan_only:
        from harness.run_system import plan_system
        plan = plan_system(system, domain)
        print(f"modular={plan['modular']}  order={' -> '.join(plan['order'])}")
        for ph in plan["phases"]:
            print(f"  {ph['app']:<24} {ph['kind']:<16} {ph['stepCount']} steps  (after {ph['dependsOn'] or '—'})")
        return 0

    result = asyncio.run(build_system(system, domain, prefix=args.prefix, tenant=args.tenant,
                                      env_key=args.env_key, state_dir=args.state_dir, prompts_dir=args.prompts_dir))
    print(f"\nSystem build {'OK' if result.ok else 'INCOMPLETE'} — modular={result.modular}")
    for a in result.apps:
        mark = "✓" if a.ok else "✗"
        print(f"  {mark} {a.name:<26} {a.succeeded}/{a.total} steps"
              + (f"  — {a.note}" if a.note else "") + (f"  (halt: {a.halted_at})" if a.halted_at and not a.ok else ""))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
