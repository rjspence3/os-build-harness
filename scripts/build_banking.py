#!/usr/bin/env python3
"""Build the Home Banking suite from manifests + recipe library.

Phase A (current): --dry-run mode only. Renders every recipe prompt that WOULD
be sent to Mentor MCP, writes them to disk under data/banking_runner_out/, and
prints a summary table. No actual MCP calls.

Phase B (TODO): wires the MCP client + state DB + orchestrator. End state:
`python scripts/build_banking.py --app core` actually drives Mentor.

Phase C (TODO): end-to-end run against fresh apps.

Usage:
    python scripts/build_banking.py --app core --dry-run
    python scripts/build_banking.py --app core --dry-run --out /tmp/run
    python scripts/build_banking.py --list-apps
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Allow `python scripts/build_banking.py` to find the harness package
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from harness.banking_runner.manifest import (  # noqa: E402
    HomeBankingManifest,
    load_home_banking,
)
from harness.banking_runner.recipe import (  # noqa: E402
    DEFAULT_RECIPES_DIR,
    collect_fk_targets,
    load_preamble,
    render_action_stub,
    render_default_screen,
    render_fk_resolution_block,
    render_role,
    render_server_entity,
    render_static_entity,
    render_theme,
    render_verify_probe,
    topologically_order_server_entities,
)
from harness.banking_runner.block_renderer import (  # noqa: E402
    parse_block_tree_file,
    render_block,
)
from harness.banking_runner.chrome_wrap import (  # noqa: E402
    extract_chrome_wrap_manifest,
    render_chrome_wrap,
)
from harness.banking_runner.library_keys import (  # noqa: E402
    LibraryKeysIndex,
    derive_required_imports,
    format_instructions_block,
)
from harness.banking_runner.screen_renderer import (  # noqa: E402
    render_screen_dechromed,
    render_screen_dechromed_parts,
)
from harness.banking_runner.tree_parser import (  # noqa: E402
    parse_coverage,
    parse_tree_file,
)

# scripts/ isn't a package; add to path so we can import batch_recipes.merge
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from batch_recipes import merge as merge_recipes  # noqa: E402

# R8 screen captures (raw widget trees) for Home Banking
SCREEN_CAPTURES_DIR = REPO_ROOT / "builds" / "home_banking" / "MCP_RECIPES" / "apps" / "home_banking" / "_raw"

# Captures below this parse coverage are in a dialect the parser can't fully
# read (narrative Dialect C). Rendering would author an incomplete screen.
SCREEN_MIN_COVERAGE = 0.9

# Per-app theme CSS source for Recipe 10. Theme CSS was extracted from the
# original `Home Banking Portal` (assetKey fa7ab595…) via `context_themes`
# 2026-06-02 — 36KB of brand colors, layout, dark-mode, component overrides.
# Caveat: the CSS references resources at `/HomeBankingPortal/img/…` and
# `/HomeBankingPortal/Sora-*.ttf` which exist on the original app's filesystem
# but NOT on our sandbox. Phase B v1 ships theme styles only; images + fonts
# fall back to defaults until Phase C (resource copy) lands.
APP_THEME_CSS: dict[str, Path] = {
    "portal":     REPO_ROOT / "builds" / "home_banking" / "theme" / "portal.css",
    # "backoffice": REPO_ROOT / "builds" / "home_banking" / "theme" / "backoffice.css",  # not yet extracted
}

# Theme name to author per app. Matches the original Home Banking apps'
# convention (theme name == app name without "Sandbox" suffix) so the screens
# and chrome-wrap that reference styles by class don't drift.
APP_THEME_NAME: dict[str, str] = {
    "portal":     "HomeBankingPortal",
    "backoffice": "HomeBankingBackoffice",
}

# Per-app block whitelist for Phase C — names matching `<name>.block.tree.md`
# captures under SCREEN_CAPTURES_DIR. Originals live in `AgentsCommonResources`
# (a ReactiveLibrary referenced by both consumer apps), but Phase C v1 authors
# them locally on each sandbox so chrome_wrap can resolve `name="X"` lookups
# without an extra library-create + reference round-trip. v2 cleanup: move
# these to a shared library matching the original architecture.
APP_BLOCK_WHITELIST: dict[str, list[str]] = {
    "portal": [
        # Local + chrome blocks captured 2026-06-09 from original fa7ab595…
        # Render order matters: layout blocks FIRST so screens that wrap
        # in them resolve at chrome-wrap time.
        "HBIcon", "Menu", "MenuIcon", "ConfirmationPDF",
        "ApplicationTitle", "HeaderActions", "UserInfo",
        # Layout family (wrap every screen)
        "LayoutBase", "LayoutBaseSection", "LayoutBlank",
        "LayoutTopMenu", "LayoutTopMenuLeftSide", "LayoutTopMenuRightSide",
        "LayoutTopMenuLeftSideWithBanner", "LayoutSideMenu", "PopupLayout",
        # Domain content
        "AccountCard", "AccountAccordian", "LoanAccordian",
        "StackedCarousel", "ItemCard", "DocumentItem",
        "FormInfoField", "ValidationError", "DisplayHTML",
        "TaskBox", "NotificationsBalloon",
        # AI chat (low priority — included in scope for completeness)
        "Chat", "ChatInput", "ChatMessage",
    ],
    "backoffice": ["HBIcon"],  # Phase 2 — Backoffice block capture pending (task #81)
}

# Per-app default-screen target for Recipe 11 (sets eSpace.DefaultScreen).
# Manifest doesn't yet carry a default_screen hint per consumer app. For Portal
# the natural default would be Dashboard, but that screen isn't captured yet
# (Phase A.5 work) — fall back to Transfer (a real customer-facing landing).
# Backoffice will follow the same pattern when its screens dispatch.
APP_DEFAULT_SCREEN: dict[str, str] = {
    "portal":     "Transfer",
    "backoffice": "Dashboard",  # placeholder — re-verify when Backoffice runs
}

# Per-app context for screen authoring: (full_app_name, flow_name, role_name).
# Role names come from Core's owned roles (HomeBankingPortal, HomeBankingBackoffice),
# both public + referenced from consumer apps via Manage Dependencies. The
# original `render_all_screens.py` used `HomeBankingPortalCustomer` /
# `HomeBankingBackofficeEmployee` which don't actually exist in either the
# rebuild or the original Home Banking Portal/Backoffice (those apps own zero
# roles — they gate on Core's public roles). Verified live 2026-06-01 via
# context_roles against the originals.
SCREEN_PREFIX_CONTEXT: dict[str, tuple[str, str, str]] = {
    "portal":     ("HomeBankingPortal",     "MainFlow", "HomeBankingPortal"),
    "backoffice": ("HomeBankingBackoffice", "MainFlow", "HomeBankingBackoffice"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--app", choices=["core", "portal", "backoffice", "all"], default="core",
                        help="Which app's recipes to drive (default: core)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Render prompts to disk; do not call MCP")
    parser.add_argument("--run", action="store_true",
                        help="Actually drive Mentor MCP — requires --app-key and authenticated mcp-remote")
    parser.add_argument("--app-key", type=str, default=None,
                        help="OutSystems asset_key for the target app (required with --run; resolved after Portal-create otherwise)")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "builds" / "home_banking" / "banking_runner_out",
                        help="Output directory for rendered prompts")
    parser.add_argument("--state-db", type=Path, default=REPO_ROOT / "builds" / "home_banking" / "runner_state.db",
                        help="SQLite state DB path")
    parser.add_argument("--list-apps", action="store_true",
                        help="List the apps available in the manifest and exit")
    parser.add_argument("--status", action="store_true",
                        help="Show current state DB counts and exit")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Merge ~N recipes per Mentor session into a batched prompt "
                             "(default: 10; 0 disables batching). Cuts Mentor session-cap pressure ~Nx.")
    parser.add_argument("--no-defer", action="store_true",
                        help="Do NOT move placeholder-containing recipes to _deferred/; "
                             "leave them in the main dispatch set (they will fail their batch).")
    args = parser.parse_args()

    manifest = load_home_banking()

    if args.list_apps:
        return _list_apps(manifest)

    if args.status:
        return _show_status(args.state_db, args.app)

    if not (args.dry_run or args.run):
        print("ERROR: specify --dry-run (render prompts) or --run (drive Mentor)", file=sys.stderr)
        return 2

    if args.run:
        return _run_mode(manifest, args)

    args.out.mkdir(parents=True, exist_ok=True)

    bs = args.batch_size
    nd = args.no_defer
    if args.app == "core":
        return _render_core(manifest, args.out, batch_size=bs, no_defer=nd)
    elif args.app == "portal":
        return _render_consumer(manifest, args.out, app_name="portal",
                                batch_size=bs, no_defer=nd)
    elif args.app == "backoffice":
        return _render_consumer(manifest, args.out, app_name="backoffice",
                                batch_size=bs, no_defer=nd)
    elif args.app == "all":
        # Render Core first, then Portal + Backoffice
        rc1 = _render_core(manifest, args.out, batch_size=bs, no_defer=nd)
        rc2 = _render_consumer(manifest, args.out, app_name="portal",
                               batch_size=bs, no_defer=nd)
        rc3 = _render_consumer(manifest, args.out, app_name="backoffice",
                               batch_size=bs, no_defer=nd)
        return rc1 or rc2 or rc3
    return 0


def _show_status(state_db: Path, app: str) -> int:
    """Show recipe-call counts grouped by status for the given app."""
    from harness.banking_runner.state import StateDB
    if not state_db.exists():
        print(f"No state DB yet at {state_db}")
        return 0
    db = StateDB(state_db)
    apps_to_show = [app] if app != "all" else ["core", "portal", "backoffice"]
    for a in apps_to_show:
        counts = db.counts(a)
        if not counts:
            print(f"[{a}] no recipe calls recorded")
            continue
        total = sum(counts.values())
        print(f"[{a}] {total} total calls: {counts}")
    db.close()
    return 0


def _run_mode(manifest: HomeBankingManifest, args) -> int:
    """Drive the actual rebuild via MCP. Requires Phase A prompts rendered first."""
    import asyncio
    from harness.banking_runner.mcp_client import MentorMCP
    from harness.banking_runner.orchestrator import AppConfig, Orchestrator
    from harness.banking_runner.state import StateDB

    if args.app == "all":
        print("ERROR: --run --app all is not yet implemented; pick a single app for now.", file=sys.stderr)
        return 2

    # Ensure prompts are rendered first
    app_out_dir = args.out / args.app
    if not app_out_dir.exists():
        print(f"  → Rendering prompts first to {app_out_dir}...")
        if args.app == "core":
            _render_core(manifest, args.out,
                         batch_size=args.batch_size, no_defer=args.no_defer)
        else:
            _render_consumer(manifest, args.out, app_name=args.app,
                             batch_size=args.batch_size, no_defer=args.no_defer)

    # Populate state DB from rendered prompts
    db = StateDB(args.state_db)
    queued = _enqueue_from_disk(db, args.app, app_out_dir)
    print(f"  → {queued} recipe calls queued in state DB")

    # Build the app config
    display_map = {
        "core": "HomeBankingCore",
        "portal": "HomeBankingPortal",
        "backoffice": "HomeBankingBackoffice",
    }
    config = AppConfig(
        name=args.app,
        display_name=display_map[args.app],
        app_key=args.app_key,
        consumer_modules=[] if args.app == "core" else ["HomeBankingCore"],
        require_studio_warmup=args.app_key is None,  # only if we just Portal-created
    )

    async def run():
        async with MentorMCP() as mcp:
            orch = Orchestrator(db, mcp, args.out)
            results = await orch.build_app(config)
            print(f"\n=== Build complete for {config.display_name} ===")
            for r in results:
                print(f"  {r.name}: succeeded={r.succeeded}, failed={r.failed}, halted={r.halted_at}")
            return 0 if all(r.failed == 0 for r in results) else 1

    try:
        return asyncio.run(run())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    finally:
        db.close()


def _enqueue_from_disk(db, app: str, app_out_dir: Path) -> int:
    """Walk app_out_dir for *.prompt.txt files and upsert each into state DB."""
    count = 0
    for prompt_path in sorted(app_out_dir.glob("*.prompt.txt")):
        # Filename format: <phase>_<index>_<TargetName>.prompt.txt
        # e.g. 01_server_10_HBCustomer.prompt.txt, 04_serveraction_001_AgentsResponseCreate.prompt.txt
        stem = prompt_path.stem.replace(".prompt", "")
        parts = stem.split("_", 3)
        if len(parts) < 3:
            continue
        # phase is the first two underscore-joined parts (e.g. "01_server", "04_serveraction")
        phase = f"{parts[0]}_{parts[1]}"
        # target_name is whatever follows the index
        target_name = parts[3] if len(parts) >= 4 else parts[2]
        db.upsert_pending(app=app, phase=phase, target_name=target_name, prompt_path=str(prompt_path))
        count += 1
    return count


def _list_apps(manifest: HomeBankingManifest) -> int:
    print(f"Manifest: {manifest.manifest_dir}")
    print(f"Entities: {manifest.entities.total_count} "
          f"(static={len(manifest.entities.static_entities)}, "
          f"server={len(manifest.entities.server_entities)})")
    print(f"Roles: {len(manifest.roles.roles)}")
    print(f"Action apps: {[s.app for s in manifest.actions.apps]}")
    for sec in manifest.actions.apps:
        print(f"  {sec.app}: server={len(sec.server_actions)}, "
              f"client={len(sec.client_actions)}, "
              f"service={len(sec.service_actions)}")
    print(f"Screen apps: {[s.app for s in manifest.screens.apps]}")
    return 0


def _render_core(
    manifest: HomeBankingManifest,
    out_dir: Path,
    batch_size: int = 10,
    no_defer: bool = False,
) -> int:
    """Render every recipe for the HomeBankingCore build.

    Post-render pipeline (R12 lessons baked in):
      * placeholder gate (_gate_placeholders) — moves recipes that contain
        `/* unsupported */` markers to _deferred/ so they don't break batches.
      * batching (_batch_outputs) — groups by phase prefix, merges `batch_size`
        recipes per Mentor session into batches/ to cut per-tenant cap pressure.
    Set batch_size=0 to disable batching; pass no_defer=True to leave
    placeholder-affected recipes in the main dispatch set."""
    static_names = {e.name for e in manifest.entities.static_entities}
    server_names = {e.name for e in manifest.entities.server_entities}
    core_dir = out_dir / "core"
    core_dir.mkdir(parents=True, exist_ok=True)

    rendered = 0
    errors = 0

    print(f"\n[core] Rendering recipes to {core_dir}...")

    # Phase 1: static entities (Recipe 02)
    for i, ent in enumerate(manifest.entities.static_entities, start=1):
        try:
            prompt = render_static_entity(ent)
            path = core_dir / f"02_static_{i:02d}_{ent.name}.prompt.txt"
            path.write_text(prompt)
            rendered += 1
        except Exception as exc:
            print(f"  ✗ static {ent.name}: {exc}")
            errors += 1

    # Phase 2: server entities (Recipe 01) — TOPOLOGICALLY ordered by FK deps.
    # Manifest order is not guaranteed to be topological (R12 lesson: CustomerGoal
    # at manifest position 2 depended on HBAccount at position 8 → naive
    # numeric-order dispatch would have NPE'd at .Named("HBAccount").IdentifierType
    # because HBAccount wasn't published yet). topologically_order_server_entities
    # does Kahn's algorithm over the FK DAG.
    server_entities_ordered = topologically_order_server_entities(
        manifest.entities.server_entities
    )
    for i, ent in enumerate(server_entities_ordered, start=1):
        try:
            prompt = render_server_entity(ent, server_names, static_names)
            path = core_dir / f"01_server_{i:02d}_{ent.name}.prompt.txt"
            path.write_text(prompt)
            rendered += 1
        except Exception as exc:
            print(f"  ✗ server {ent.name}: {exc}")
            errors += 1

    # Phase 3: roles (Recipe 03)
    for i, role in enumerate(manifest.roles.roles, start=1):
        try:
            prompt = render_role(role)
            path = core_dir / f"03_role_{i:02d}_{role.name}.prompt.txt"
            path.write_text(prompt)
            rendered += 1
        except Exception as exc:
            print(f"  ✗ role {role.name}: {exc}")
            errors += 1

    # Phase 4: actions (Recipe 04 — stub) for the 'core' section
    core_actions = next((s for s in manifest.actions.apps if s.app == "core"), None)
    if core_actions:
        for kind, actions in (
            ("server", core_actions.server_actions),
            ("service", core_actions.service_actions),
        ):
            for i, action in enumerate(actions, start=1):
                try:
                    prompt = render_action_stub(action, server_names, static_names)
                    path = core_dir / f"04_{kind}action_{i:03d}_{action.name}.prompt.txt"
                    path.write_text(prompt)
                    rendered += 1
                except Exception as exc:
                    print(f"  ✗ {kind} action {action.name}: {exc}")
                    errors += 1

    # Phase 5: theme (TODO — needs Recipe 10 renderer)
    # Phase 6: default screen (TODO — needs Recipe 11 renderer + a screen target)
    # Phase 7: publish + verify (TODO — needs Recipe 99 renderer)

    print(f"\n[core] Done: {rendered} prompts rendered, {errors} errors")
    print(f"  → output: {core_dir}")
    _print_summary(core_dir)

    # Post-render: placeholder gate, then batching.
    deferred = _gate_placeholders(core_dir, no_defer=no_defer)
    if deferred:
        print(f"  → {deferred} placeholder-affected recipes moved to _deferred/")
    batches_written = _batch_outputs(core_dir, batch_size=batch_size)
    if batches_written:
        print(f"  → {batches_written} batched prompts written to batches/ "
              f"(batch_size={batch_size})")

    return 0 if errors == 0 else 1


def _render_consumer(
    manifest: HomeBankingManifest,
    out_dir: Path,
    app_name: str,
    batch_size: int = 10,
    no_defer: bool = False,
) -> int:
    """Render Portal/Backoffice recipes. Consumer apps reuse Core entities via
    Manage Dependencies (Studio gate); they bring their own actions + screens."""
    consumer_dir = out_dir / app_name
    consumer_dir.mkdir(parents=True, exist_ok=True)

    rendered = 0
    errors = 0

    print(f"\n[{app_name}] Rendering recipes to {consumer_dir}...")

    # Consumer apps have actions (mostly Client + Server) — render as stubs.
    # For consumers, the local entity sets are EMPTY (they reference Core via
    # Manage Dependencies). FK resolution will route to "referenced" lookups
    # for any entity not in the local sets.
    app_actions = next((s for s in manifest.actions.apps if s.app == app_name), None)
    if app_actions:
        for kind, actions in (
            ("server", app_actions.server_actions),
            ("client", app_actions.client_actions),
            ("service", app_actions.service_actions),
        ):
            for i, action in enumerate(actions, start=1):
                try:
                    prompt = render_action_stub(action, set(), set())
                    path = consumer_dir / f"04_{kind}action_{i:03d}_{action.name}.prompt.txt"
                    path.write_text(prompt)
                    rendered += 1
                except Exception as exc:
                    print(f"  ✗ {kind} action {action.name}: {exc}")
                    errors += 1

    # Phase 5: dechromed screens (CHROME-A: structure-only, no chrome-wrap yet)
    # Reads R8 captures from SCREEN_CAPTURES_DIR, gates on parse coverage,
    # renders each as a dechromed screen recipe (placeholders where custom
    # blocks will later substitute via chrome-wrap in CHROME-C).
    screens_added, screens_skipped = _render_dechromed_screens_for_app(
        app_name=app_name, out_dir=consumer_dir
    )
    if screens_added or screens_skipped:
        print(f"  [{app_name}] {screens_added} dechromed screens rendered"
              + (f", {screens_skipped} skipped (low-coverage capture)" if screens_skipped else ""))
        rendered += screens_added

    # Phase 5.4: custom blocks (Recipe 22) — authors HBIcon, Menu, Header etc.
    # locally in the consumer app. The dechromed screen recipes left named
    # Container placeholders (_chrome_HBIcon_<path>); chrome_wrap will later
    # swap them for real BlockInstance widgets referencing these authored
    # blocks. Blocks must exist before chrome_wrap runs (publish boundary —
    # the marker lookup-by-name only resolves across publish per chrome_wrap.py
    # caveat).
    blocks_added, blocks_skipped = _render_blocks_for_app(
        app_name=app_name, out_dir=consumer_dir
    )
    if blocks_added or blocks_skipped:
        print(f"  [{app_name}] {blocks_added} custom blocks rendered"
              + (f", {blocks_skipped} skipped" if blocks_skipped else ""))
        rendered += blocks_added

    # Phase 5.5: theme (Recipe 10) — replaces the app's theme stylesheet with
    # the extracted Home Banking CSS. ODC quirk per [[odc_mcp_mobile_prefixed_api]]:
    # the recipe uses `eSpace.MobileThemes` (NOT `eSpace.Themes`) — even for
    # WebApplication assets, because the new ODC Web stack is built atop the
    # Mobile-prefixed surface. The CSS payload is ~36KB which fits in a single
    # Mentor turn comfortably.
    theme_css_path = APP_THEME_CSS.get(app_name)
    theme_name = APP_THEME_NAME.get(app_name)
    if theme_css_path and theme_name and theme_css_path.exists():
        try:
            # Sanitize the CSS — ODC's OML validator scans `url(/AppPath/…)`
            # refs and rejects unresolved resources at publish (OS-APPS-40028
            # — Phase B v1 learning, see _sanitize_theme_css_for_publish docs).
            # Phase C (resource copy via eSpace.CreateResource) restores the
            # references when fonts/images are ported over.
            raw_css = theme_css_path.read_text()
            sanitized_css = _sanitize_theme_css_for_publish(raw_css)
            sanitized_path = consumer_dir / "_theme_sanitized.css"
            sanitized_path.write_text(sanitized_css)
            stripped_count = raw_css.count("url(") - sanitized_css.count("url(")
            # Filename must have ≥3 underscore tokens so the batcher's phase
            # extraction (`parts[0]_parts[1]`) yields "10_theme", not the whole
            # filename. Include the theme name as the third token.
            prompt = render_theme(
                theme_name=theme_name,
                css_path=sanitized_path,
                is_default=True,
            )
            path = consumer_dir / f"10_theme_01_{theme_name}.prompt.txt"
            path.write_text(prompt)
            rendered += 1
            print(f"  [{app_name}] theme rendered → {theme_name} "
                  f"({sanitized_path.stat().st_size} bytes; "
                  f"sanitized {stripped_count} local url() refs from {theme_css_path.name})")
        except Exception as exc:
            print(f"  ✗ theme: {exc}")
            errors += 1

    # Phase 6: default screen (Recipe 11) — sets eSpace.DefaultScreen to the
    # configured target. Manifest doesn't yet carry a default_screen hint per
    # app; use APP_DEFAULT_SCREEN as a v1 stub.
    default_screen_name = APP_DEFAULT_SCREEN.get(app_name)
    if default_screen_name:
        try:
            prompt = render_default_screen(default_screen_name, flow_name="MainFlow")
            path = consumer_dir / f"11_default_screen_{default_screen_name}.prompt.txt"
            path.write_text(prompt)
            rendered += 1
            print(f"  [{app_name}] default screen → {default_screen_name}")
        except Exception as exc:
            print(f"  ✗ default screen: {exc}")
            errors += 1

    # Phase 7: verify probe (Recipe 99) — read-only validation that the
    # published model matches the manifest's expected shape. For consumer
    # apps, entity count is 0 (Core ref provides entities). Action count is
    # the dispatchable manifest count (placeholder-deferred recipes excluded).
    app_actions_section = next((s for s in manifest.actions.apps if s.app == app_name), None)
    expected_actions = 0
    if app_actions_section:
        expected_actions = (
            len(app_actions_section.server_actions or [])
            + len(app_actions_section.client_actions or [])
            + len(app_actions_section.service_actions or [])
        )
    try:
        prompt = render_verify_probe(
            expected_entities=0,                       # consumers own zero
            expected_screens=screens_added,
            expected_actions=expected_actions,
            expected_default_screen=default_screen_name,
        )
        path = consumer_dir / "99_verify_probe.prompt.txt"
        path.write_text(prompt)
        rendered += 1
        print(f"  [{app_name}] verify probe rendered "
              f"(expects screens={screens_added}, actions={expected_actions})")
    except Exception as exc:
        print(f"  ✗ verify probe: {exc}")
        errors += 1

    print(f"\n[{app_name}] Done: {rendered} prompts rendered, {errors} errors")
    print(f"  → output: {consumer_dir}")

    # Post-render: placeholder gate, then batching.
    deferred = _gate_placeholders(consumer_dir, no_defer=no_defer)
    if deferred:
        print(f"  → {deferred} placeholder-affected recipes moved to _deferred/")
    batches_written = _batch_outputs(consumer_dir, batch_size=batch_size)
    if batches_written:
        print(f"  → {batches_written} batched prompts written to batches/ "
              f"(batch_size={batch_size})")

    return 0 if errors == 0 else 1


def collect_fk_targets_from_action(action) -> list[str]:
    """Extract unique FK target entity names from action parameters."""
    targets: list[str] = []
    for p in action.parameters:
        if p.data_type.endswith(" Identifier"):
            t = p.data_type[: -len(" Identifier")]
            if t not in targets:
                targets.append(t)
    return targets


def _print_summary(out_dir: Path) -> None:
    """Print a one-line-per-recipe-type summary."""
    counts: dict[str, int] = {}
    for p in sorted(out_dir.glob("*.prompt.txt")):
        prefix = "_".join(p.stem.split("_")[:2])
        counts[prefix] = counts.get(prefix, 0) + 1
    for prefix, n in sorted(counts.items()):
        print(f"    {prefix}: {n}")


def _render_blocks_for_app(
    app_name: str,
    out_dir: Path,
) -> tuple[int, int]:
    """Render custom-block recipes (Recipe 22) from `.block.tree.md` captures
    into out_dir. Filename prefix `06_block_NN_<Name>.prompt.txt` slots into
    the per-phase batcher's 1:1 override (blocks are wide widget trees, same
    constraint as screens — they don't fit Mentor's per-applyModelApiCode
    window batched).

    Only blocks listed in APP_BLOCK_WHITELIST[app_name] are rendered, so a
    consumer app gets only the blocks it actually chrome-wraps to (HBIcon,
    Menu, Header in Phase C; chatbot blocks later).

    Returns (rendered_count, skipped_count).

    Phase C v1: HBIcon only — minimal probe to validate Recipe 22 dispatch
    on a new app. Then Menu + Header. Then chrome_wrap to swap dechromed
    Container placeholders for real BlockInstance widgets."""
    block_names = APP_BLOCK_WHITELIST.get(app_name, [])
    if not block_names:
        return (0, 0)

    rendered_count = 0
    skipped_count = 0
    preamble = load_preamble(DEFAULT_RECIPES_DIR).strip()
    # Same import set as screen recipes — block authoring uses the same
    # ServiceStudio.Plugin.NRWidgets / Mobile.Widgets surface.
    imports_lines = "\n".join(f"  - {i}" for i in [
        "System.Linq",
        "OutSystems.Model",
        "OutSystems.Model.Data",
        "OutSystems.Model.Logic",
        "OutSystems.Model.UI.Mobile",
        "OutSystems.Model.UI.Mobile.Widgets",
        "ServiceStudio.Plugin.NRWidgets",
    ])

    for idx, block_name in enumerate(block_names, start=1):
        capture_path = SCREEN_CAPTURES_DIR / f"{block_name}.block.tree.md"
        if not capture_path.exists():
            print(f"  ✗ [{app_name}] block {block_name}: no capture at {capture_path.relative_to(REPO_ROOT)}")
            skipped_count += 1
            continue

        try:
            ast = parse_block_tree_file(capture_path)
            body = render_block(ast)
            prompt = (
                preamble
                + "\n\n```csharp\n"
                + body.strip()
                + "\n```\n\n"
                + "Required imports for the `imports` array on the applyModelApiCode call:\n"
                + imports_lines
                + "\n"
            )
            out_path = out_dir / f"06_block_{idx:02d}_{block_name}.prompt.txt"
            out_path.write_text(prompt)
            rendered_count += 1
        except Exception as exc:
            print(f"  ✗ [{app_name}] block {block_name}: render error: {exc}")
            skipped_count += 1

    return (rendered_count, skipped_count)


def _render_dechromed_screens_for_app(
    app_name: str,
    out_dir: Path,
) -> tuple[int, int]:
    """Render dechromed screen recipes from R8 captures into out_dir.

    Walks SCREEN_CAPTURES_DIR for `<app_name>-*.tree.md`, gates on
    parse coverage, renders each via `render_screen_dechromed`, and writes
    `05_screen_NN_<ScreenName>.prompt.txt` files. The 05_ prefix slots
    cleanly into the post-render batcher's by-phase grouping.

    Coverage gate (SCREEN_MIN_COVERAGE=0.9): captures below this threshold
    are in a dialect the parser can't fully read (narrative Dialect-C);
    rendering them would author an incomplete screen. They're skipped with
    a pointer to R8_CAPTURE_PROMPT.md.

    Phase B (theme) and Phase C (custom blocks + chrome-wrap) are NOT
    rendered here — they're a separate phase requiring CSS extraction and
    block tree captures that don't exist yet.

    Returns (rendered_count, skipped_low_coverage_count)."""
    context = SCREEN_PREFIX_CONTEXT.get(app_name)
    if context is None:
        return (0, 0)
    full_app_name, flow_name, role_name = context

    if not SCREEN_CAPTURES_DIR.exists():
        return (0, 0)

    rendered_count = 0
    skipped_count = 0
    preamble = load_preamble(DEFAULT_RECIPES_DIR).strip()
    imports_lines = "\n".join(f"  - {i}" for i in [
        "System.Linq",
        "OutSystems.Model",
        "OutSystems.Model.Data",
        "OutSystems.Model.Logic",
        "OutSystems.Model.Logic.Nodes",
        "OutSystems.Model.UI.Mobile",
        "OutSystems.Model.UI.Mobile.Widgets",
        "OutSystems.Model.Enumerations",
        "ServiceStudio.Plugin.NRWidgets",
    ])

    captures = sorted(SCREEN_CAPTURES_DIR.glob(f"{app_name}-*.tree.md"))
    for idx, capture in enumerate(captures, start=1):
        cov = parse_coverage(capture.read_text())
        if cov["coverage"] < SCREEN_MIN_COVERAGE:
            print(f"  ✗ [{app_name}] SKIP screen {capture.name} (coverage "
                  f"{cov['coverage']:.2f} < {SCREEN_MIN_COVERAGE}) — "
                  f"re-capture via R8_CAPTURE_PROMPT.md")
            skipped_count += 1
            continue

        ast = parse_tree_file(capture)
        # v3 (2026-06-09): screens named Login or InvalidPermissions render
        # anonymous-accessible — clears Mentor's auto-applied role gate +
        # sets AnonymousAccess=true. Without this, the app has a lockout
        # pattern that produces _error.html for any unauthenticated visitor.
        anonymous_screens = {"Login", "InvalidPermissions"}
        is_anonymous = ast.name in anonymous_screens
        # v16 (2026-06-11): large screens split into part files — part 1 is the
        # skeleton with named sect_N shells, parts 2+ fill them. Single-part
        # screens are byte-identical to the legacy render.
        bodies = render_screen_dechromed_parts(
            ast,
            role_name=None if is_anonymous else role_name,
            flow_name=flow_name,
            anonymous=is_anonymous,
        )
        body = bodies[0]
        prompt = (
            preamble
            + "\n\n```csharp\n"
            + body.strip()
            + "\n```\n\n"
            + f"Required imports for the `imports` array on the applyModelApiCode call:\n"
            + imports_lines
            + "\n"
        )

        # Strip the `<app>-` prefix and `.tree` suffix for a clean screen name.
        screen_name = capture.stem.removeprefix(f"{app_name}-").removesuffix(".tree")
        if len(bodies) == 1:
            out_path = out_dir / f"05_screen_{idx:02d}_{screen_name}.prompt.txt"
            out_path.write_text(prompt)
        else:
            # v16 split: write part files. Part 1 carries the skeleton (and the
            # full preamble); parts 2+ carry the section fills. Dispatch order
            # matters — part 1 MUST publish-or-apply before parts 2+ in the
            # same session (lookup-by-name resolves in-session).
            for pi, pbody in enumerate(bodies, 1):
                pprompt = (
                    preamble
                    + "\n\n```csharp\n"
                    + pbody.strip()
                    + "\n```\n\n"
                    + f"Required imports for the `imports` array on the applyModelApiCode call:\n"
                    + imports_lines
                    + "\n"
                )
                out_path = out_dir / f"05_screen_{idx:02d}_{screen_name}_part{pi}.prompt.txt"
                out_path.write_text(pprompt)
            print(f"  [{app_name}] screen {screen_name}: split into {len(bodies)} parts")
        rendered_count += 1

        # Phase C step 2 — chrome_wrap recipe alongside dechromed. Replaces
        # the named Container placeholders (`_chrome_<SourceBlock>_<path>`)
        # that the dechromed render left behind with real `BlockInstance`
        # widgets pointing to the published custom blocks (HBIcon, Menu,
        # Header). Per chrome_wrap.py caveat: marker lookup-by-name resolves
        # ACROSS a publish boundary — dechromed screens must publish before
        # chrome_wrap runs. The blocks must also exist; chrome_wrap with
        # missing block refs falls back to FirstOrDefault null (see
        # chrome_wrap renderer's resilience pattern). 1:1 batched per
        # _PHASE_BATCH_SIZE_OVERRIDES["07_chrome"].
        try:
            cw_manifest = extract_chrome_wrap_manifest(ast, flow_name=flow_name)
            if cw_manifest.entries:
                cw_body = render_chrome_wrap(cw_manifest)
                # v7 bake (2026-06-08): emit IMPORT PREREQUISITES section listing
                # library blocks this batch references. Mentor calls
                # `addReferenceToElements` MCP tool before applyModelApiCode so
                # the wrap-site lookup chain (IMobileBlockSignature in
                # eSpace.References) can resolve them. addReferenceToElements is
                # idempotent — re-imports are no-ops. Names in library_keys YAML's
                # `missing` list (primitives like Button/Icon) are dropped.
                referenced_blocks = [e.source_block for e in cw_manifest.entries]
                resolved_imports, unresolved_names = derive_required_imports(
                    referenced_blocks
                )
                import_instructions = format_instructions_block(resolved_imports)
                cw_prompt = (
                    preamble
                    + "\n\n"
                    + import_instructions
                    + "```csharp\n"
                    + cw_body.strip()
                    + "\n```\n\n"
                    + f"Required imports for the `imports` array on the applyModelApiCode call:\n"
                    + imports_lines
                    + "\n"
                )
                cw_path = out_dir / f"07_chrome_{idx:02d}_{screen_name}.prompt.txt"
                cw_path.write_text(cw_prompt)
                rendered_count += 1
                if unresolved_names:
                    print(
                        f"  ⚠ [{app_name}] chrome_wrap {screen_name}: "
                        f"{len(unresolved_names)} unresolved block name(s) "
                        f"(may resolve via local MobileFlows): {unresolved_names}"
                    )
        except Exception as exc:
            print(f"  ✗ [{app_name}] chrome_wrap for {screen_name}: {exc}")

    return (rendered_count, skipped_count)


# Regex matching CSS `url(...)` declarations whose path starts with `/`
# (an absolute local path on the *original* source app). The path may be
# surrounded by single or double quotes. Examples that match:
#   url(/HomeBankingPortal/Sora-Regular.ttf)
#   url('/HomeBankingPortal/img/Logo.svg')
#   url("/HomeBankingPortal/CardChecking.svg")
# Examples that do NOT match (preserved):
#   url(http://cdn.example.com/font.woff)
#   url("data:image/svg+xml,…")
#   url(./relative/path.svg)
_LOCAL_URL_REF_RE = re.compile(
    r"""url\(\s*['"]?/[^)'"]*['"]?\s*\)""",
    re.IGNORECASE,
)


def _sanitize_theme_css_for_publish(css: str) -> str:
    """Replace local-resource CSS URLs with `url('')` so the OML binary
    validator doesn't reject the theme at publish-time with OS-APPS-40028
    ("Input binary does not contain a valid OML — Unknown Object" against
    a `/Style Sheet` path).

    The original Home Banking theme references resources at the *source* app's
    filesystem (`/HomeBankingPortal/Sora-*.ttf`, `/HomeBankingPortal/img/*.svg`).
    Those don't exist as authored resources on the rebuild's sandbox app, so
    publish fails. Replacing them with empty `url('')` leaves the CSS
    syntactically valid (browsers fall back: missing fonts → sans-serif,
    missing background-images → no image rendered) and bypasses the validator.

    Phase C should revisit by copying the real resources via
    `eSpace.CreateResource` per [[odc_mcp_resource_api]], then restoring the
    paths.

    Verified live 2026-06-02 on Portal Phase B (~36 KB CSS, ~10–15 local URL
    refs in the Home Banking Portal theme)."""
    return _LOCAL_URL_REF_RE.sub("url('')", css)


def _gate_placeholders(out_dir: Path, no_defer: bool) -> int:
    """Scan rendered prompts for `/* unsupported` markers. Such a recipe can't
    compile cleanly and would break its entire batch when dispatched. Default:
    move affected files to {out_dir}/_deferred/ so they're visible but not in
    the main dispatch set. --no-defer keeps them in place (and they will break
    their batch). Returns the count moved.

    This codifies R12's lesson: List-of-record and Structure-typed params are
    unsupported by the current renderer (the modern Model API for those is
    unprobed); they should never reach Mentor in a batch with healthy recipes."""
    deferred_dir = out_dir / "_deferred"
    moved = 0
    for f in sorted(out_dir.glob("*.prompt.txt")):
        if "/* unsupported" not in f.read_text():
            continue
        if no_defer:
            continue
        deferred_dir.mkdir(parents=True, exist_ok=True)
        f.rename(deferred_dir / f.name)
        moved += 1
    return moved


# Per-phase batch_size overrides for phases where the global default doesn't
# fit Mentor's per-applyModelApiCode execution window. Empirically validated
# 2026-06-02 against HomeBankingPortalSandbox: action stubs batch 10:1 fine,
# but screens at 3:1 stalled (probe v4 — Mentor went silent for 5+ min after
# tool_begin). At 1:1 (probe v5) every screen completed in ~90s.
#   * Screen authoring is wide: ~150 widgets + ~25 expressions + FK resolution
#     against cross-app references per screen.
#   * Block authoring is similar wide-shape work (when we get to CHROME-C).
#   * Theme is one large CSS payload (~30KB) — already a "batch of 1" naturally.
# When the global --batch-size is smaller than the override, the smaller wins
# (so e.g. --batch-size 1 doesn't accidentally batch screens to 10).
_PHASE_BATCH_SIZE_OVERRIDES: dict[str, int] = {
    "05_screen": 1,
    "06_block":  1,    # blocks author wide widget trees, same as screens (Phase C)
    "07_chrome": 1,    # chrome_wrap replaces ~10-40 placeholders per screen; 1:1
}


def _batch_outputs(out_dir: Path, batch_size: int) -> int:
    """Group rendered prompts by phase prefix and merge each phase into
    batched prompts. Output is written to {out_dir}/batches/.

    `batch_size` is the global default. Per-phase overrides in
    `_PHASE_BATCH_SIZE_OVERRIDES` cap specific phases at smaller sizes
    (e.g. screens at 1:1) because Mentor's per-applyModelApiCode time window
    can't fit multiple wide-authoring recipes in one turn.

    Returns the number of batch files written.

    This codifies R12's biggest dispatch lever (1 recipe = 1 Mentor session
    = 1 cap slot; batching cuts cap pressure linearly) plus Phase A's lesson
    that batch_size is phase-dependent. Files within a phase are sorted by
    filename, preserving topological ordering established at render time.

    Phase prefix is the first two underscore-tokens of the filename:
    `01_server`, `02_static`, `03_role`, `04_serveraction`, `04_serviceaction`,
    `05_screen`."""
    if batch_size <= 0:
        return 0
    batches_dir = out_dir / "batches"
    by_phase: dict[str, list[Path]] = {}
    for f in sorted(out_dir.glob("*.prompt.txt")):
        parts = f.name.split("_", 2)
        if len(parts) < 2:
            continue
        phase = f"{parts[0]}_{parts[1]}"
        by_phase.setdefault(phase, []).append(f)

    written = 0
    for phase, files in by_phase.items():
        if not files:
            continue
        # Smaller of global default and per-phase override wins.
        phase_size = min(batch_size, _PHASE_BATCH_SIZE_OVERRIDES.get(phase, batch_size))
        batches_dir.mkdir(parents=True, exist_ok=True)
        for n, start in enumerate(range(0, len(files), phase_size), start=1):
            chunk = files[start:start + phase_size]
            merged = merge_recipes(chunk)
            out_path = batches_dir / f"{phase}_batch_{n:02d}.prompt.txt"
            out_path.write_text(merged)
            written += 1
    return written


if __name__ == "__main__":
    sys.exit(main())
