"""Chrome wrap (Recipe 23) — pairs with dechromed screen renderer (Recipe 07 / T2.2).

API status (live findings 2026-05-28 — block-instance API CORRECTED + pieces
validated; see memory [[odc_mcp_screen_widget_authoring_api]]):
  - block instance: `marker.CreateWidget<OutSystems.Model.UI.Mobile.Widgets.IMobileBlockInstanceWidget>("name")`
    created INSIDE the marker container (validated). The earlier
    `parent.CreateBlockInstance(...)` was CS1061; `marker.Parent` is a
    CustomPlaceholderWidget (cast wall), so we create inside the marker and leave
    it as a transparent wrapper rather than replacing it.
  - source block: set via REFLECTION
    `bi.GetType().GetProperty("SourceWebBlock").SetValue(bi, blockSig)` (validated:
    clears the "Source Block must be set" error). SourceWebBlock is not on the
    static IMobileBlockInstanceWidget interface, so a direct assignment is CS1061.
  - input-parameter bindings: DEFERRED to LOGIC phase.

Portal Phase C VERIFY probe (Transfer screen at rev 13, 2026-06-02):
marker-lookup-by-name ACROSS a publish boundary is NOT the wall the earlier
caveat called out (a same-call create+lookup returns null because the model
isn't refreshed within one applyModelApiCode — true, but separate concern).
The actual wall hitting `wrapped=0/18` was a NAME-MISMATCH: the OutSystems
Model API silently strips a leading underscore from widget Name during
CreateWidget. Renderer authored `_chrome_<sb>_<path>` markers; platform
stored them as `chrome_<sb>_<path>`; chrome_wrap looked up the original-
underscored form and found nothing. strip_marker_name (in screen_renderer.py)
flipped to `chrome_<sb>_<path>` — both sides now agree. See memory
[[odc_mcp_widget_name_strips_leading_underscore]].

Portal Phase C VERIFY re-dispatch (Transfer rev 13 → rev 14, 2026-06-02):
LIVE-VALIDATED end-to-end with the fix in place. wrapped=2/18 with
15-of-18 markers resolved by lookup (3 real marker holes are separate, to
be investigated). The 2 successful wraps (Menu + HBIcon) prove:
(a) marker-lookup-by-name across publish boundary works once names agree;
(b) CreateWidget<IMobileBlockInstanceWidget>("name") on a found marker
    Container creates a valid block instance;
(c) reflection-set SourceWebBlock via `bi.GetType().GetProperty(...)` clears
    the "Source Block must be set" OML validation;
(d) publish persists the chrome_wrap mutations across a separate publish_start
    call (the chrome_wrap recipe ITSELF doesn't publish — caller does).
Remaining gap: 16-of-18 wrap sites failed because the LOCAL blockSig lookup
(`eSpace.MobileFlows.SelectMany(f => f.GetAllDescendantsOfType<IMobileBlock>())`)
finds only locally-authored blocks; Phase C still has 8 distinct blocks to
author via APP_BLOCK_WHITELIST + Recipe 22 dispatches.

Two pieces:
1. `extract_chrome_wrap_manifest(ast)` — walks a parsed ScreenAST and pulls
   out every BlockInstance referencing a CUSTOM (non-OS-UI) block. Each entry
   carries the path, source_block, original widget name, parameter bindings,
   and child widgets (placeholder fillings).

2. `render_chrome_wrap(manifest)` — emits Mentor MCP applyModelApiCode that
   mutates an already-published screen: finds each stripped placeholder
   Container by its stable marker Name (set by T2.2), removes it, creates a
   BlockInstance in the same position with the same parameter bindings.

The chrome wrap runs AFTER T2.2 + Recipe 22 have both landed and published.

Strategy: WIDE NET — collect every BlockInstance that references a name not
in OS_UI_STANDARD_BLOCKS. The strip naming is symmetric: T2.2 names the
placeholder with `strip_marker_name(source_block, path)`, T2.5 looks it up
with the same function. No coordination state needed beyond the original AST.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from harness.banking_runner.screen_renderer import (
    OS_UI_STANDARD_BLOCKS,
    RenderContext,
    strip_marker_name,
)
from harness.banking_runner.tree_parser import ScreenAST, WidgetNode


# v2 (2026-06-08): block names that chrome_wrap should NOT attempt to wrap due
# to known recipe limitations. Each entry has a documented reason. The chrome
# marker for these blocks stays as an empty Container — LOGIC phase or manual
# Studio touch-up is responsible for filling them.
#
# Why these are skipped:
# - InputWithIcon: BlockInstance contains a nested Input widget whose .Variable
#   property is a required reference-typed property. SetArgumentValue with an
#   empty string literal doesn't satisfy AVS validation (Error: Required
#   Property Value on the Input widget). Studio Mentor binds it to a real
#   screen-local Variable expression; our chrome_wrap placeholder pass can't
#   conjure a Variable reference without an aggregate or local var in scope.
#   Live failure: Rebake1 Portal Transfer screen batch 03, 2026-06-08.
SKIP_BLOCKS_WITH_RUNTIME_VARIABLE_BIND = {
    "InputWithIcon",
    # ButtonLoading: placeholder Button child demands a bound On Click event —
    # a screen-action reference the chrome pass can't conjure. Unset On Click is
    # a validation Error → OS-APPS-40028 at publish (zero in-session errors).
    # Live failure: Portal4 WakeUp wrap, bisection 2026-06-11. Bind in LOGIC phase.
    "ButtonLoading",
}


# ─── Manifest ──────────────────────────────────────────────────────────────────

@dataclass
class ChromeWrapEntry:
    path: str                                       # widget path in the original AST, e.g. "1.1.1"
    source_block: str                               # name of the custom block to instantiate
    widget_name: Optional[str]                      # name to give the new BlockInstance (from original)
    parent_path: Optional[str]                      # parent widget path, or None for top-level
    parameters: dict[str, str] = field(default_factory=dict)
    # Note: child widgets / placeholder fillings are NOT yet wired in MVP —
    # see PLAN_GAP CW-A below. The dechromed screen already has them as
    # children of the placeholder Container; the wrap currently discards
    # the placeholder Container (and its children with it) and recreates a
    # fresh BlockInstance.


@dataclass
class ChromeWrapManifest:
    screen_name: str
    flow_name: str = "MainFlow"
    entries: list[ChromeWrapEntry] = field(default_factory=list)


# ─── Manifest extraction ───────────────────────────────────────────────────────

def extract_chrome_wrap_manifest(ast: ScreenAST, flow_name: str = "MainFlow") -> ChromeWrapManifest:
    """Walk the screen AST and pull every BlockInstance that references a
    custom (non-OS-UI) block. Returns the manifest used by `render_chrome_wrap`."""
    manifest = ChromeWrapManifest(screen_name=ast.name, flow_name=flow_name)
    _walk(ast.widgets, manifest)
    return manifest


def _walk(widgets: list[WidgetNode], manifest: ChromeWrapManifest):
    for w in widgets:
        if w.widget_type == "BlockInstance" and w.source_block:
            if w.source_block in SKIP_BLOCKS_WITH_RUNTIME_VARIABLE_BIND:
                # Don't enqueue — chrome marker stays as empty Container.
                continue
            if w.source_block not in OS_UI_STANDARD_BLOCKS:
                manifest.entries.append(ChromeWrapEntry(
                    path=w.path,
                    source_block=w.source_block,
                    widget_name=w.name,
                    parent_path=_parent_path_of(w.path),
                    parameters=dict(w.properties),
                ))
        # Descend regardless of widget type — custom blocks can nest inside
        # other widgets (Container, If, OS UI Layout placeholders, etc.)
        _walk(w.children, manifest)
        _walk(w.true_branch, manifest)
        _walk(w.false_branch, manifest)


def _parent_path_of(path: str) -> Optional[str]:
    if "." not in path:
        return None
    return path.rsplit(".", 1)[0]


# ─── Renderer ──────────────────────────────────────────────────────────────────

def render_chrome_wrap(manifest: ChromeWrapManifest) -> str:
    """Emit the C# body that wraps an already-published screen with custom
    block references. Returns the bare `eSpace => { ... }` lambda."""
    ctx = RenderContext()
    _emit_setup(manifest, ctx)
    for entry in manifest.entries:
        _emit_entry(entry, ctx)
    _emit_diagnostic(manifest, ctx)
    return "eSpace => {\n    " + "\n    ".join(ctx.lines) + "\n}"


def _emit_setup(manifest: ChromeWrapManifest, ctx: RenderContext):
    ctx.emit(f"// ─── Chrome Wrap: {manifest.screen_name} (Recipe 23) ─────────────")
    ctx.emit(f'var flow = eSpace.MobileFlows.FirstOrDefault(f => f.Name == "{manifest.flow_name}");')
    # Self-healing: on-demand create the MobileFlow if missing. Greenfield
    # MCP-`app_create` apps ship without MainFlow (discovered Portal Rebake1
    # 2026-06-02). Mirrors the pattern in block_renderer.py + screen_renderer.py.
    ctx.emit(f'if (flow == null) {{ flow = eSpace.CreateMobileFlow("{manifest.flow_name}"); Console.WriteLine($"Created missing MobileFlow {manifest.flow_name}"); }}')
    ctx.emit(f'var screen = flow.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileScreen>().FirstOrDefault(s => s.Name == "{manifest.screen_name}");')
    ctx.emit(f'if (screen == null) {{ Console.WriteLine($"FAILED: Screen {manifest.screen_name} not found"); return; }}')
    ctx.emit(f'int wrapped = 0, missing = 0;')


def _emit_entry(entry: ChromeWrapEntry, ctx: RenderContext):
    # Validated chrome-wrap API (live, 2026-05-28 — memory
    # [[odc_mcp_screen_widget_authoring_api]]):
    #  - find the marker by Name via GetAllDescendantsOfType<IContainer> (the
    #    dechromed renderer creates markers as NRWidgets.IContainer; .Name reads
    #    back the CreateWidget name arg). NOTE: lookup-by-name needs post-publish
    #    validation in R12 — a same-call create+lookup returns null (model not
    #    refreshed within one applyModelApiCode); the real flow publishes the
    #    dechromed screen first, then wraps in a separate call.
    #  - create the block instance INSIDE the marker via
    #    CreateWidget<...Widgets.IMobileBlockInstanceWidget> (avoids the
    #    marker.Parent → CustomPlaceholderWidget cast wall). The marker stays as
    #    a transparent wrapper.
    #  - set the source block via REFLECTION: GetProperty("SourceWebBlock") +
    #    SetValue. (SourceWebBlock is NOT declared on IMobileBlockInstanceWidget's
    #    static interface, so a direct `bi.SourceWebBlock =` is CS1061 — reflection
    #    sets the concrete-class property and clears the "Source Block must be
    #    set" validation.)
    #  - block input-parameter bindings are DEFERRED to the LOGIC phase.
    marker_nm = strip_marker_name(entry.source_block, entry.path)
    ctx.emit("")
    ctx.emit(f'// Wrap site: {entry.path} → block instance of {entry.source_block} inside marker {marker_nm}')
    ctx.emit(f'{{')
    ctx.emit(f'    var marker = screen.GetAllDescendantsOfType<ServiceStudio.Plugin.NRWidgets.IContainer>()')
    ctx.emit(f'        .FirstOrDefault(c => c.Name == "{marker_nm}");')
    ctx.emit(f'    if (marker == null) {{ Console.WriteLine($"WARN: chrome marker {marker_nm} not found — skipping"); missing++; }}')
    ctx.emit(f'    else {{')
    # Portal Phase C step 2 learning (2026-06-02): `IReference.Blocks` does NOT
    # exist on the Model API (CS1061 — verified live). The cross-app block
    # fallback that this line previously emitted (`eSpace.References.SelectMany
    # (r => r.Blocks)…`) failed compile across all wrap sites. For v1 we drop
    # the cross-app fallback entirely — all custom blocks land locally on the
    # consumer app via `_render_blocks_for_app` before chrome_wrap runs, so
    # the local `eSpace.MobileFlows.SelectMany(…)` lookup is sufficient.
    # When/if v2 supports cross-app block references (e.g. HBIcon hosted in
    # AgentsCommonResources rather than re-authored locally), probe the
    # correct Model API: likely `r.GetAllDescendantsOfType<IMobileBlockSignature>()`
    # or `r.MobileBlocks` — both unprobed at write-time.
    # Lookup priority: LOCAL block first (eSpace.MobileFlows), then CROSS-APP
    # via TWO signature interfaces:
    # 1. IMobileBlockSignature — for Mobile-flow blocks in custom apps
    # 2. IWebBlockSignature — for Web/Reactive-flow blocks in shared libraries
    #    (OutSystemsUI patterns like Tag, Columns3, InputWithIcon; InputMasks
    #    like MaskText, MaskCurrency; etc.)
    # All three interfaces share IModelObject as base; we erase to `object` so
    # `bi.GetType().GetProperty("SourceWebBlock").SetValue(bi, blockSig)` via
    # reflection accepts any. Baked Portal Rebake1 2026-06-03 — earlier two-source
    # lookup was missing every OutSystemsUI pattern reference because they're
    # IWebBlockSignature, not IMobileBlockSignature.
    ctx.emit(f'        object blockSig = (object)eSpace.MobileFlows.SelectMany(f => f.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileBlock>())')
    ctx.emit(f'            .FirstOrDefault(b => b.Name == "{entry.source_block}")')
    ctx.emit(f'            ?? (object)eSpace.References.SelectMany(r => r.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.IMobileBlockSignature>())')
    ctx.emit(f'            .FirstOrDefault(b => b.Name == "{entry.source_block}")')
    ctx.emit(f'            ?? (object)eSpace.References.SelectMany(r => r.GetAllDescendantsOfType<OutSystems.Model.UI.Web.IWebBlockSignature>())')
    ctx.emit(f'            .FirstOrDefault(b => b.Name == "{entry.source_block}");')
    ctx.emit(f'        if (blockSig == null) {{ Console.WriteLine($"WARN: block {entry.source_block} not found — skipping"); missing++; }}')
    ctx.emit(f'        else {{')
    bi_name = entry.widget_name or f"inst_{entry.path.replace('.', '_')}"
    # Idempotency guard (baked Portal Phase C 2026-06-02): if a previous chrome_wrap
    # dispatch already authored a BlockInstance inside this marker (e.g. partial-
    # publish then retry), bail instead of stacking another. Without this guard
    # each retry adds another instance silently; the third or fourth dispatch
    # then hits opaque OML-validator rejections for "duplicate widget" or
    # nested-instance violations. Cheap check, defensive.
    ctx.emit(f'            if (marker.GetAllDescendantsOfType<OutSystems.Model.UI.Mobile.Widgets.IMobileBlockInstanceWidget>().Any()) {{')
    ctx.emit(f'                Console.WriteLine($"SKIP: marker {marker_nm} already wrapped — preserving existing BlockInstance"); wrapped++;')
    ctx.emit(f'            }} else {{')
    ctx.emit(f'                var bi = marker.CreateWidget<OutSystems.Model.UI.Mobile.Widgets.IMobileBlockInstanceWidget>("{bi_name}");')
    # v10 chrome_wrap bake (2026-06-09): use typed SourceBlock setter (Mentor's
    # canonical API per Counter probe) for IMobileBlock + IMobileBlockSignature,
    # fall back to reflection on SourceWebBlock for IWebBlockSignature. The Counter
    # probe captured Mentor's verbatim: `instance.SourceBlock = (IMobileBlockSignature)blockSig`.
    # Reflection on SourceWebBlock works IN-SESSION (Mentor reports wrapped=N/N) but
    # the OML serializer rejects with OS-APPS-40028 at publish time — the binding
    # doesn't survive the binary write. Typed setter writes via the model layer's
    # canonical path, persists through serialization. See V14 in GAPS.md.
    # v13 (2026-06-11, Portal4 bisection): the binding path is TYPE-DEPENDENT.
    # - LOCAL IMobileBlock → reflection SourceWebBlock setter. Proven published
    #   (Rebake1 rev 23, v6). The v10 typed `bi.SourceBlock = localBlock`
    #   assignment of the block OBJECT corrupts the session OML → AVS rejects
    #   with OS-APPS-40028 (bisection: batch_01-alone fresh-session publish
    #   failed under v12; identical wrap set published clean under v6).
    # - REFERENCED IMobileBlockSignature → typed SourceBlock setter. Proven
    #   published (Counter probe rev 28). Mentor's canonical API assigns a
    #   SIGNATURE, never the block object.
    # The IMobileBlock branch MUST come first: local blocks may also satisfy
    # other interface checks.
    ctx.emit(f'                try {{')
    ctx.emit(f'                    if (blockSig is OutSystems.Model.UI.Mobile.IMobileBlock) bi.GetType().GetProperty("SourceWebBlock")?.SetValue(bi, blockSig);  // LOCAL: reflection (proven rev 23)')
    ctx.emit(f'                    else if (blockSig is OutSystems.Model.UI.Mobile.IMobileBlockSignature mobileSig) bi.SourceBlock = mobileSig;  // REF: typed signature (proven rev 28)')
    ctx.emit(f'                    else bi.GetType().GetProperty("SourceWebBlock")?.SetValue(bi, blockSig);  // IWebBlockSignature fallback')
    ctx.emit(f'                }} catch (Exception ex) {{ Console.WriteLine($"WARN: source-bind failed on {entry.source_block}: {{ex.Message}}"); }}')
    # Bake B-revised (Portal Rebake1 2026-06-08): bind EVERY block-instance input
    # parameter (mandatory AND optional) to a type-appropriate placeholder
    # expression literal via `bi.SetArgumentValue(parameter, expression_string)`.
    # AVS rejects publish with OS-APPS-40028 when any mandatory input lacks a
    # bound value; earlier `CreateArgument(ip)` created an arg slot but left
    # the value unset, which AVS still treats as unbound. Method name
    # `SetArgumentValue` discovered by post-Studio-Mentor probe — confirmed live
    # 2026-06-08 against Transfer screen's published BlockInstances (rev 22).
    # Pattern Mentor confirmed in chat: "bind ALL inputs, even optional ones —
    # the safe pattern AVS accepts."
    # Placeholder literals (v6, Studio Mentor verified 2026-06-08):
    #   Boolean → "False"
    #   Integer / Long Integer / Currency / Decimal → "0"
    #   Text (mandatory) → '"X"'  (NON-EMPTY — AVS rejects "" on mandatory Text inputs)
    #   Identifier / Date / Date Time / everything else → '""'  (empty literal acceptable)
    # The Text branch MUST come before the catch-all: Identifier-typed inputs
    # serialize as "<EntityName> Identifier" which contains neither "text" nor any
    # numeric keyword, so they correctly land on the catch-all (empty string).
    # The LOGIC phase later overwrites these with real expressions.
    # v14 param-bind (2026-06-11, Portal4 root-cause): the concrete BlockInstance
    # class has NO SetArgumentValue method — the old reflection lookup returned
    # null and the null-guard SILENTLY SKIPPED every bind (no WARN), leaving
    # mandatory args unbound → one validation Error → OS-APPS-40028 at publish.
    # Canonical API (verified live, Portal4 rev 5 published): walk the typed
    # IArgument descendants of the BlockInstance; arg.SetValue(expression_string)
    # persists via implicit string → ExpressionDefinition conversion. Arguments
    # materialize automatically after SourceWebBlock is set. Bind only when the
    # current Value is empty (don't clobber pre-existing binds on re-runs).
    ctx.emit(f'                try {{')
    ctx.emit(f'                    var argList = bi.GetAllDescendantsOfType<OutSystems.Model.IArgument>().ToArray();')
    ctx.emit(f'                    foreach (var arg in argList) {{')
    ctx.emit(f'                        if (arg.Parameter == null) continue;')
    ctx.emit(f'                        var curVal = arg.Value?.ToString() ?? "";')
    ctx.emit(f'                        if (!string.IsNullOrWhiteSpace(curVal)) continue;  // keep existing binds')
    ctx.emit(f'                        var dtStr = (arg.Parameter.DataType?.ToString() ?? "").ToLower();')
    ctx.emit(f'                        string placeholder;')
    ctx.emit(f'                        if (dtStr.Contains("boolean")) placeholder = "False";')
    ctx.emit(f'                        else if (dtStr.Contains("integer") || dtStr.Contains("currency") || dtStr.Contains("decimal") || dtStr.Contains("long")) placeholder = "0";')
    ctx.emit(f'                        else if (dtStr.Contains("text") || dtStr.Contains("phone") || dtStr.Contains("email")) placeholder = "\\"X\\"";')
    # v15 type-gate (2026-06-11 bisection): the old catch-all bound a Text
    # literal '""' to STRUCTURE-typed params (e.g. ProgressBar.OptionalConfigs:
    # ProgressBarOptionalConfigs) — type-mismatch validation Error →
    # OS-APPS-40028 at publish with zero in-session errors. Identifier/Date/Time
    # accept the empty literal (verified published); everything else (structures,
    # records, lists, objects, binary) is SKIPPED — unbound optional is legal,
    # and no literal satisfies a structure type. LOGIC phase binds real values.
    ctx.emit(f'                        else if (dtStr.Contains("identifier") || dtStr.Contains("date") || dtStr.Contains("time")) placeholder = "\\"\\"";')
    ctx.emit(f'                        else {{ Console.WriteLine($"WARN: skip non-basic param bind {{arg.Parameter.Name}} ({{dtStr}}) on {entry.source_block}"); continue; }}')
    ctx.emit(f'                        arg.SetValue(placeholder);')
    ctx.emit(f'                    }}')
    ctx.emit(f'                }} catch (Exception ex) {{ Console.WriteLine($"WARN: param-bind failed on {entry.source_block}: {{ex.Message}}"); }}')
    # Note: captured binds (e.g. `AccountTypeId = GetAccounts.List.Current.Id`)
    # are tracked here for the LOGIC phase but NOT emitted at chrome-wrap time —
    # those expressions reference unauthored aggregates and would fail validation.
    binds = {k: v for k, v in entry.parameters.items()
             if k not in ("Width", "Style", "CustomStyle", "Visible")}
    if binds:
        ctx.emit(f'                // captured binds (bind in LOGIC phase): {binds}')
    ctx.emit(f'                wrapped++;')
    ctx.emit(f'            }}')  # close idempotency-guard else
    ctx.emit(f'        }}')      # close blockSig != null else
    ctx.emit(f'    }}')          # close marker != null else
    ctx.emit(f'}}')              # close per-wrap-site block


def _emit_diagnostic(manifest: ChromeWrapManifest, ctx: RenderContext):
    expected = len(manifest.entries)
    ctx.emit("")
    ctx.emit(f'Console.WriteLine($"Recipe 23: {manifest.screen_name} | wrapped={{wrapped}}/{expected}, missing={{missing}} | Status: ' +
             f'{{(wrapped == {expected} && missing == 0 ? \\"OK\\" : \\"PARTIAL\\")}}");')
