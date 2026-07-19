"""Rolling recipe reconciliation (WALL-006) — the "evolving recipes" layer.

`plan_from_spec` computes every step's params STATICALLY from the spec, up front, with no knowledge
of what earlier steps actually authored. That is the root cause of a whole class of live-build
defects (WALL-003/004/005/007): a step assumes a world the previous steps did not build —
a `conditional` targets a widget a reduced create-form never authored; a list's detail target may
not actually declare an `Id` input; a create form's entity may have gained a mandatory attribute.

This module closes that loop. Right before a step is fired, the driver reads the LIVE ODC model
(`context_entities` / `context_screens` / `context_actions`), wraps it in a `LiveModel`, and calls
`reconcile_params(recipe, params, live, spec)`. Each reconciler PATCHES the params that depend on
BUILD STATE — so the rendered prompt reflects reality, not just the spec.

Design invariants:
  * PURE + testable — `reconcile_params` takes a `LiveModel` snapshot (no MCP), returns
    `(patched_params, notes)`. Unit-tested against fixture live models, exactly like recipes.
  * SAFE — an unknown recipe, absent live data, or any error is a NO-OP (returns params unchanged
    with a note). Reconciliation only ever ADDS certainty; it never breaks a step that would have
    worked. So enabling it can only help.
  * SHARED logic — reconcilers reuse the same schema helpers the planner uses (prompt_recipes),
    so Layer-1 (spec) and Layer-2 (live) agree.
"""
from __future__ import annotations

from typing import Any

# ── LiveModel: a defensive snapshot of the live ODC model ────────────────────────
_ITEM_KEYS = ("items", "data", "entities", "screens", "actions", "results", "value")


def _items(payload: Any) -> list:
    """Pull the element list out of a context_* payload across ODC response shapes."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in _ITEM_KEYS:
            v = payload.get(k)
            if isinstance(v, list):
                return v
    return []


def _name(el: dict) -> str | None:
    for k in ("name", "Name", "id", "logicalName", "label"):
        v = el.get(k)
        if isinstance(v, str) and v:
            return v
    return None


class LiveModel:
    """Read-only view of the live model: which entities/screens/actions exist and, where the
    payloads carry the detail, each entity's attributes and each screen's components + input
    parameters. Every accessor returns None when the element is UNKNOWN to this snapshot (so a
    reconciler can distinguish "absent from the model" from "present but empty")."""

    def __init__(self, entities: list | None = None, screens: list | None = None,
                 actions: list | None = None):
        self._entities = {n.lower(): el for el in (entities or []) if (n := _name(el))}
        self._screens = {n.lower(): el for el in (screens or []) if (n := _name(el))}
        self._actions = {n.lower() for el in (actions or []) if (n := _name(el))}

    @classmethod
    def from_payloads(cls, entities=None, screens=None, actions=None) -> "LiveModel":
        return cls(_items(entities), _items(screens), _items(actions))

    # entities ---------------------------------------------------------------------
    def has_entity(self, name: str) -> bool:
        return name.lower() in self._entities

    def entity_attrs(self, name: str) -> list | None:
        el = self._entities.get(name.lower())
        if el is None:
            return None
        for k in ("attributes", "Attributes", "attrs"):
            v = el.get(k)
            if isinstance(v, list):
                return v
        return []

    # screens ----------------------------------------------------------------------
    def has_screen(self, name: str) -> bool:
        return name.lower() in self._screens

    def screen_component_ids(self, name: str) -> set | None:
        """The set of data-spec-id / component ids present on the live screen, or None if the screen
        is unknown to the snapshot. Reads the widget tree defensively (context payloads vary)."""
        el = self._screens.get(name.lower())
        if el is None:
            return None
        ids: set = set()

        def walk(node):
            if isinstance(node, dict):
                for k in ("dataSpecId", "data_spec_id", "specId", "componentId", "id", "name"):
                    v = node.get(k)
                    if isinstance(v, str) and v:
                        ids.add(v)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        for k in ("components", "widgets", "tree", "layout", "children"):
            if k in el:
                walk(el[k])
        return ids

    def screen_input_params(self, name: str) -> list | None:
        el = self._screens.get(name.lower())
        if el is None:
            return None
        for k in ("inputParameters", "inputs", "parameters", "InputParameters"):
            v = el.get(k)
            if isinstance(v, list):
                return v
        return []

    def screen_takes_id(self, name: str) -> bool | None:
        """True/False when known: does the live screen declare an `Id`-like input parameter?
        None when the screen is unknown to the snapshot."""
        ips = self.screen_input_params(name)
        if ips is None:
            return None
        for ip in ips:
            nm = (_name(ip) or "").lower()
            if nm == "id" or nm.endswith("id"):
                return True
        return False

    # actions ----------------------------------------------------------------------
    def has_action(self, name: str) -> bool:
        return name.lower() in self._actions


# ── spec helpers used by reconcilers (kept import-light) ─────────────────────────
def _spec_screen(spec: dict, screen_id: str) -> dict:
    for s in spec.get("screens", []) or []:
        if s.get("id") == screen_id or s.get("name") == screen_id:
            return s
    return {}


def _spec_write_entity(spec: dict, screen: dict) -> str | None:
    for c in screen.get("components", []) or []:
        if c.get("boundTo"):
            return c["boundTo"].split(".")[0]
    for ip in screen.get("inputParameters", []) or []:
        if ip.get("references"):
            return ip["references"]
    return None


# ── reconcilers (recipe name -> fn(params, live, spec) -> (params, notes)) ────────
def _reconcile_conditional(params: dict, live: LiveModel, spec: dict):
    """WALL-003: a conditional targets a widget (and reads a control) that a reduced create-form may
    never have authored. If the live screen is missing the target component or the control the
    `visible_when` reads, emit `ensure_widgets` (create-if-absent, bound to the form record) so the
    recipe self-heals instead of setting Visible on a phantom."""
    notes: list = []
    screen_id = params.get("screen")
    comp = params.get("component_id")
    expr = params.get("visible_when") or ""
    live_ids = live.screen_component_ids(screen_id) if screen_id else None
    if live_ids is None:
        return params, [f"conditional: screen '{screen_id}' not in live model — no reconcile"]

    spec_screen = _spec_screen(spec, screen_id)
    by_id = {c.get("id"): c for c in spec_screen.get("components", []) or []}
    entity = _spec_write_entity(spec, spec_screen)
    record = f"New{entity}" if entity else None

    # candidate widgets the conditional depends on: the target + any spec component whose id appears
    # in the visible_when expression (e.g. "MOCRequired = True" reads the MOCRequired control).
    needed = {comp}
    for cid in by_id:
        if cid and cid != comp and cid in expr:
            needed.add(cid)

    ensure = []
    for cid in sorted(x for x in needed if x):
        if cid in (live_ids or set()):
            continue  # already authored — nothing to heal
        c = by_id.get(cid)
        if not c:
            continue
        attr = (c.get("boundTo") or "").split(".")[-1] or cid
        ensure.append({"id": cid, "attr": attr, "type": c.get("type", "Input")})

    if ensure and record:
        params = {**params, "ensure_widgets": ensure, "record": record}
        notes.append(f"conditional: self-heal {[w['id'] for w in ensure]} absent on live '{screen_id}' "
                     f"-> ensure_widgets bound to {record}")
    elif ensure and not record:
        notes.append(f"conditional: {[w['id'] for w in ensure]} absent but no form record resolvable "
                     f"on '{screen_id}' — cannot self-heal")
    return params, notes


def _reconcile_list_screen(params: dict, live: LiveModel, spec: dict):
    """WALL-003: (a) resolve a placeholder column set from the live/spec entity attributes; (b) tell
    the recipe whether the detail target actually declares an Id input, so it does not pass an Id to
    a screen that takes none."""
    notes: list = []
    out = dict(params)

    # (a) resolve unresolved placeholder columns from the entity's attributes.
    cols = params.get("columns")
    entity = params.get("entity")
    placeholder = cols in (None, [], ["(entity display fields)"]) or (
        isinstance(cols, list) and any(isinstance(c, str) and c.startswith("(") for c in cols))
    if placeholder and entity:
        attrs = live.entity_attrs(entity)
        names = None
        if attrs:
            names = [(_name(a)) for a in attrs
                     if not (a.get("isIdentifier") or a.get("references"))]
            names = [n for n in names if n]
        if not names:  # fall back to the spec's declared attributes
            for e in spec.get("dataModel", {}).get("entities", []) or []:
                if e.get("name") == entity:
                    names = [a["name"] for a in e.get("attributes", [])
                             if not (a.get("isIdentifier") or a.get("references"))]
        if names:
            out["columns"] = [{"field": n, "kind": "text"} for n in names[:3]]
            notes.append(f"list-screen: resolved placeholder columns for {entity} -> "
                         f"{[c['field'] for c in out['columns']]}")

    # (b) detail-screen Id awareness.
    detail = params.get("detail_screen")
    if detail:
        takes = live.screen_takes_id(detail)
        if takes is None:  # not in live snapshot — fall back to the spec
            ds = _spec_screen(spec, detail)
            ips = ds.get("inputParameters", []) or []
            takes = any((ip.get("name", "").lower() == "id" or ip.get("references")) for ip in ips)
        out["detail_takes_id"] = bool(takes)
        if not takes:
            notes.append(f"list-screen: detail '{detail}' declares no Id input — nav will pass no arg")
    return out, notes


def _reconcile_create_form(params: dict, live: LiveModel, spec: dict):
    """Refresh mandatory_defaults from the LIVE entity attributes when available (the entity may have
    gained a mandatory attribute since planning). Static-FK initial records still resolve from the
    spec (design-time). No-op when the live entity is unknown or carries no attribute detail."""
    entity = params.get("entity")
    attrs = live.entity_attrs(entity) if entity else None
    if not attrs:
        return params, []
    from harness import prompt_recipes as pr
    # Build a mini-spec so the shared helper resolves static initial records + type defaults, but
    # over the LIVE attribute list (authoritative for what mandatory columns currently exist).
    static_entities = [e for e in spec.get("dataModel", {}).get("entities", []) or [] if e.get("isStatic")]
    mini = {"dataModel": {"entities": static_entities + [{"name": entity, "attributes": attrs}]}}
    fresh = pr._mandatory_defaults(mini, entity, params.get("fields", []),
                                   params.get("context_fk"), params.get("creator_attr"))
    if fresh and fresh != params.get("mandatory_defaults"):
        return {**params, "mandatory_defaults": fresh}, [
            f"create-form: refreshed mandatory_defaults from live '{entity}' -> "
            f"{[d['field'] for d in fresh]}"]
    return params, []


_RECONCILERS = {
    "conditional": _reconcile_conditional,
    "list-screen": _reconcile_list_screen,
    "create-form": _reconcile_create_form,
}


def reconcile_params(recipe: str, params: dict, live: LiveModel | None, spec: dict | None = None):
    """Patch a step's params against the live model right before rendering. Returns
    `(patched_params, notes)`. A missing reconciler, absent live model, or any error is a safe no-op."""
    fn = _RECONCILERS.get(recipe)
    if fn is None or live is None:
        return params, []
    try:
        return fn(dict(params or {}), live, spec or {})
    except Exception as exc:  # never let reconciliation break a step
        return params, [f"reconcile skipped ({recipe}): {exc!r}"]
