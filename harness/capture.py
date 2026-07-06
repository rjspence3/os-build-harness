"""harness-capture — the runtime (rendered-DOM) verification channel.

The judge (`harness-verify --phase live`) routes componentPresent / binding /
navigates assertions to the **capture** channel: they can only be proven against
the *rendered* app, not the offline spec. This module IS that channel's data
source. Given an app_spec + the live app's base URL (+ an optional login), it
drives a headless browser over every screen, resolves each spec'd component in
the live DOM, confirms each nav edge, and emits a screen-walk snapshot in the
exact shape `harness-verify.load_screens_snapshot` ingests:

    {"screens": [{"id": ..., "components": [{"id","type","boundTo"}],
                  "navigation": [{"fromComponent","event","toScreen"}]}]}

So the loop is: `harness-capture spec.json --base-url URL --out d/` →
`harness-verify spec.json --phase live --screens d/runtime_screens.json`.
With `--assert` it also runs the capture-channel assertions inline and exits
nonzero on any fail — a self-contained runtime gate for CI. MCP-free; works
against any deployed app.

RESOLUTION CONTRACT (general across builds):
  1. `[data-spec-id="<componentId>"]` on the rendered element — the strong,
     build-agnostic contract. Builders SHOULD emit it; then resolution is exact.
  2. Fallback per component type (table/list->table+rows, button/link->label text,
     navigation->link href to route, ...) so it also works on apps that predate the
     contract. Heuristic matches are marked in the snapshot (`matchedBy`) so weak
     resolutions are visible, never silent.

Honest semantics: a component is emitted (-> componentPresent pass) only when the
DOM resolves it. `boundTo` is emitted (-> binding pass) only when the component is
present AND, for a data component, actually renders >=1 row — runtime proof the
aggregate is wired and returning data. A nav edge is emitted (-> navigates pass)
only when the fromComponent links to / clicks through to the toScreen route.
Never a silent pass.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Component types that carry data (binding == present AND renders rows).
_DATA_TYPES = {"Table", "List", "Card", "Board", "Chart"}


def _lazy_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except Exception:
        print(
            "harness-capture needs Playwright. Install it in the harness venv:\n"
            "  pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
        raise SystemExit(3)


# ── login (config-driven, general) ──────────────────────────────────────────
def _apply_login(page, base_url: str, login: dict) -> dict:
    """Apply an app login before the screen sweep. Config shapes:
      {"type": "none"}                                             (default)
      {"type": "localstorage", "items": {"k": "v", ...}, "route": "/"}
      {"type": "quickbutton", "match": "Rob Spence", "route": "/Login"}
      {"type": "form", "route": "/Login", "user": "...", "password": "...",
       "userSel"?: css, "passSel"?: css, "submitText"?: "Log in"}
    Returns a small status dict. Best-effort + tolerant; a failed login still
    lets the sweep run (screens that require auth will just resolve as absent)."""
    ltype = (login or {}).get("type", "none")
    if ltype == "none":
        return {"type": "none"}
    route = login.get("route", "/Login")
    page.goto(base_url.rstrip("/") + "/" + route.lstrip("/"), wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1500)
    try:
        page.evaluate("() => { localStorage.clear(); }")
    except Exception:
        pass
    if ltype == "localstorage":
        items = login.get("items", {})
        page.evaluate(
            "(items) => { for (const k in items) localStorage.setItem(k, items[k]); }",
            items,
        )
        return {"type": "localstorage", "set": list(items)}
    if ltype == "quickbutton":
        needle = re.escape(login.get("match", ""))
        clicked = page.evaluate(
            """(pat) => { const re = new RegExp(pat, 'i');
                 const b = [...document.querySelectorAll('button,a,.btn')].find(x => re.test(x.innerText||''));
                 if (b) { b.click(); return (b.innerText||'').trim(); } return null; }""",
            needle,
        )
        page.wait_for_timeout(3500)
        return {"type": "quickbutton", "clicked": clicked}
    if ltype == "form":
        page.evaluate(
            """(cfg) => {
                 const ins = [...document.querySelectorAll('input')];
                 const u = cfg.userSel ? document.querySelector(cfg.userSel)
                        : (ins.find(i=>/email|user|name|login/i.test((i.placeholder||'')+(i.name||'')+(i.id||''))) || ins[0]);
                 const p = cfg.passSel ? document.querySelector(cfg.passSel)
                        : (ins.find(i=>i.type==='password') || ins[1]);
                 const set=(el,v)=>{const d=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value');
                        el.focus(); d.set.call(el,v); el.dispatchEvent(new Event('input',{bubbles:true}));
                        el.dispatchEvent(new Event('change',{bubbles:true})); el.blur();};
                 if(u) set(u, cfg.user||''); if(p) set(p, cfg.password||''); }""",
            login,
        )
        page.wait_for_timeout(500)
        submit = re.escape(login.get("submitText", "Log in"))
        page.evaluate(
            """(pat) => { const re = new RegExp('^\\\\s*'+pat+'\\\\s*$','i');
                 const b = [...document.querySelectorAll('button,a,.btn')].find(x => re.test((x.innerText||'').trim()));
                 if (b) b.click(); }""",
            submit,
        )
        page.wait_for_timeout(3500)
        return {"type": "form", "user": login.get("user")}
    return {"type": ltype, "warning": "unknown login type — treated as none"}


def _login_from_auth(spec: dict) -> dict:
    """Derive a headless login config from the spec's `auth` block, so the behavioral
    gate can authenticate with NO hand-fed --login-config (closes seam 6). For app-local
    auth it uses a quick-login button matching an (admin) test user's label at the login
    screen route. Falls back to {type:none}."""
    auth = spec.get("auth") or {}
    if auth.get("provider") == "app-local":
        users = auth.get("testUsers") or []
        chosen = next((u for u in users if u.get("isAdmin")), users[0] if users else None)
        if chosen and chosen.get("label"):
            login_screen = auth.get("loginScreen", "Login")
            route = next((s.get("route", "/" + login_screen) for s in spec.get("screens", [])
                          if s["id"] == login_screen), "/" + login_screen)
            return {"type": "quickbutton", "match": chosen["label"], "route": route}
    return {"type": "none"}


# ── DOM resolution (contract-first, heuristic-fallback) ─────────────────────
_RESOLVE_JS = r"""
(comp) => {
  const id = comp.id, type = comp.type || '', label = (comp.label || '').trim();
  const esc = (window.CSS && CSS.escape) ? CSS.escape(id) : id;
  const byContract = document.querySelector('[data-spec-id="' + esc + '"]');
  const rowCount = (el) => el ? el.querySelectorAll('table tbody tr, li, [class*="row"], [class*="card"], [data-row-id]').length : 0;
  if (byContract) {
    return {present:true, matchedBy:'data-spec-id', rows: rowCount(byContract),
            entity: byContract.getAttribute('data-entity') || null};
  }
  const DATA = ['Table','List','Card','Board','Chart'];
  const norm = (s)=> (s||'').replace(/\s+/g,' ').trim().toLowerCase();
  if (DATA.includes(type)) {
    // Exclude the persistent NAV container precisely (not any "sidebar" substring —
    // the DATA area is often `sidebar-content`, which must NOT be excluded).
    const inNav = (el) => !!el.closest('nav, aside, [role="navigation"], [class*="sidebar-nav"], [class*="side-nav"], [class*="navbar"]');
    const cands = [...document.querySelectorAll('table, [class*="table"], [class*="card-list"], [class*="board"], [class*="list"], ul, ol')];
    // prefer a non-nav data element that actually renders rows; else any non-nav one.
    const el = cands.find(x => !inNav(x) && rowCount(x) > 0) || cands.find(x => !inNav(x));
    if (el) return {present:true, matchedBy:'heuristic:data', rows: rowCount(el),
                    entity: el.getAttribute('data-entity') || null};
    return {present:false, matchedBy:'heuristic:data', rows:0, entity:null};
  }
  if (['Button','Link','Navigation'].includes(type) && label) {
    const want = norm(label);
    const el = [...document.querySelectorAll('button,a,.btn,[role="button"]')]
       .find(x => norm(x.innerText||x.getAttribute('aria-label')||'').includes(want));
    if (el) return {present:true, matchedBy:'heuristic:label', rows:0,
                    href: el.getAttribute('href')||null, entity:null};
    return {present:false, matchedBy:'heuristic:label', rows:0, entity:null};
  }
  const hintMap = {Form:'form', Input:'input', Dropdown:'select,[class*="dropdown"]',
    Checkbox:'input[type=checkbox]', DatePicker:'[class*="date"],input[type=date]',
    Image:'img', Sidebar:'[class*="sidebar"],aside', Container:'[class*="container"]',
    Label:'label,[class*="label"]'};
  const sel = hintMap[type];
  if (sel) { const el = document.querySelector(sel);
    return {present: !!el, matchedBy:'heuristic:type', rows:0, entity: el?(el.getAttribute('data-entity')||null):null}; }
  return {present:false, matchedBy:'unresolved', rows:0, entity:null};
}
"""


def _confirm_nav_href(from_res: dict, to_route: str) -> bool:
    """href mode: the fromComponent's href targets the toScreen route."""
    route_tail = to_route.strip("/").lower()
    href = (from_res or {}).get("href")
    return bool(route_tail and href and route_tail in href.lower())


def snapshot_screen(page, base_url: str, screen: dict, all_screens: list,
                    out_dir: Path | None, nav_mode: str) -> dict:
    """Navigate to the screen's route, resolve its spec components + nav edges in
    the live DOM, screenshot, and return a screen-walk entry."""
    sid = screen["id"]
    route = screen.get("route", "/" + sid)
    url = base_url.rstrip("/") + "/" + route.lstrip("/")
    landed = {"id": sid, "route": route, "components": [], "navigation": []}
    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2200)
    except Exception as e:
        landed["error"] = repr(e)
        return landed
    landed["finalUrl"] = page.url
    landed["redirected"] = route.strip("/").lower() not in page.url.lower()

    resolved_by_id: dict = {}
    for comp in screen.get("components", []):
        res = page.evaluate(_RESOLVE_JS, comp)
        resolved_by_id[comp["id"]] = res
        if not res.get("present"):
            continue
        entry = {"id": comp["id"], "type": comp.get("type"), "matchedBy": res.get("matchedBy")}
        bound = comp.get("boundTo")
        if bound:
            is_data = comp.get("type") in _DATA_TYPES
            if (not is_data) or res.get("rows", 0) > 0:
                entry["boundTo"] = bound
            else:
                entry["boundTo_unrendered"] = bound  # present but empty — not a binding pass
        landed["components"].append(entry)

    route_of = {s["id"]: s.get("route", "/" + s["id"]) for s in all_screens}
    for edge in screen.get("navigation", []):
        fc = edge.get("fromComponent")
        to = edge["toScreen"]
        to_route = route_of.get(to, "/" + to)
        confirmed = _confirm_nav_href(resolved_by_id.get(fc, {}), to_route)
        if not confirmed and nav_mode in ("click", "both"):
            confirmed = _confirm_nav_click(page, url, fc, to_route)
        if confirmed:
            landed["navigation"].append({"fromComponent": fc, "event": edge.get("event"), "toScreen": to})

    if out_dir is not None:
        try:
            page.screenshot(path=str(out_dir / f"shot_{sid}.png"), full_page=True)
        except Exception:
            pass
    return landed


def _confirm_nav_click(page, screen_url: str, from_id: str, to_route: str) -> bool:
    """click mode: click the fromComponent, observe the URL land on to_route, go back."""
    route_tail = to_route.strip("/").lower()
    if not route_tail:
        return False
    try:
        clicked = page.evaluate(
            """(cid) => { const el = document.querySelector('[data-spec-id="'+cid+'"]'); if(el){el.click(); return true;} return false; }""",
            from_id,
        )
        if not clicked:
            return False
        page.wait_for_timeout(2000)
        landed = route_tail in page.url.lower()
        page.goto(screen_url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(1200)
        return landed
    except Exception:
        return False


def build_runtime_snapshot(spec: dict, base_url: str, login: dict, out_dir: Path | None,
                           nav_mode: str) -> dict:
    sync_playwright = _lazy_playwright()
    screens_out = []
    console_errors: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page = ctx.new_page()
        cur = {"s": "login"}
        page.on("console", lambda m: console_errors.setdefault(cur["s"], []).append(m.text)
                if m.type == "error" else None)
        login_status = _apply_login(page, base_url, login)
        for screen in spec["screens"]:
            cur["s"] = screen["id"]
            screens_out.append(snapshot_screen(page, base_url, screen, spec["screens"], out_dir, nav_mode))
        browser.close()
    return {
        "base_url": base_url,
        "login": login_status,
        "screens": screens_out,
        "consoleErrors": {k: v[:8] for k, v in console_errors.items() if v},
    }


# ── inline assertion gate (reuses verify.py semantics — single source of truth) ─
def _assert_capture_channel(spec: dict, snapshot: dict):
    """Run the capture-channel assertions (componentPresent/binding/navigates)
    against the runtime snapshot, reusing verify.py's evaluators. Returns
    (results, n_pass, n_fail)."""
    from harness.verify import (load_screens_snapshot, _eval_component_present,
                                _eval_binding, _eval_navigates)

    walk = load_screens_snapshot(snapshot)
    evald = {"componentPresent": _eval_component_present, "binding": _eval_binding, "navigates": _eval_navigates}
    results, n_pass, n_fail = [], 0, 0
    for screen in spec["screens"]:
        for a in screen.get("acceptance", {}).get("assertions", []):
            fn = evald.get(a["kind"])
            if not fn:
                continue  # entityExists/attribute/integrationExists — not this channel
            r = fn(a, screen, walk)
            results.append((screen["id"], r))
            if r.status == "pass":
                n_pass += 1
            elif r.status == "fail":
                n_fail += 1
    return results, n_pass, n_fail


# ── behavioral verification (Phase 6 — the definition of "working", not "present") ──
# Drives each spec'd create action against the live app and asserts a row PERSISTS on
# reload. This is the gate structural checks cannot provide (componentPresent is true for
# a dead button). Spec-driven off actions/does + the create-form recipe's data-spec-id.
def _route_of(spec: dict, screen_id: str) -> str:
    for s in spec.get("screens", []):
        if s["id"] == screen_id:
            return s.get("route", "/" + screen_id)
    return "/" + screen_id


def _parent_context_nav(spec: dict, form_screen: dict):
    """(parent_route, click_label) to reach a child create screen that requires a parent-context
    input param: the parent list has a component whose onClick navigates to this screen passing
    the param, so opening a parent record supplies a real parent id. None if no such nav exists
    (iteration-3 seam 3c)."""
    fid = form_screen["id"]
    for s in spec.get("screens", []):
        for nav in s.get("navigation", []) or []:
            if nav.get("toScreen") == fid and nav.get("params"):
                label, fc = None, nav.get("fromComponent")
                for c in s.get("components", []):
                    if c.get("id") == fc:
                        label = c.get("label")
                        break
                return (_route_of(spec, s["id"]), label)
    return None


_COUNT_JS = r"""(entity) => {
  const inNav=(el)=>!!el.closest('nav,aside,[role=navigation],[class*="sidebar-nav"],[class*="navbar"]');
  // EXACT with the contract (data-entity on the list container); heuristic otherwise.
  const host=[...document.querySelectorAll('[data-entity="'+entity+'"]')].find(x=>!inNav(x));
  const scope=host||document.querySelector('.sidebar-content, main, [class*="content"]')||document;
  let rows=[...scope.querySelectorAll('[data-row-id]')].filter(x=>!inNav(x));
  if(!rows.length) rows=[...scope.querySelectorAll('table tbody tr')].filter(x=>!inNav(x));
  if(!rows.length) rows=[...scope.querySelectorAll('li')].filter(x=>!inNav(x) && (x.innerText||'').trim().length>2);
  if(!rows.length){ // repeated-sibling heuristic for div/anchor-based lists (largest same-shape group >=2)
    const groups={};
    [...scope.querySelectorAll('a,div')].filter(x=>!inNav(x) && (x.innerText||'').trim().length>3).forEach(x=>{
      const p=x.parentElement; const k=(p?(p.className||p.tagName):'')+'|'+x.tagName+'|'+(x.className||'');
      (groups[k]=groups[k]||[]).push(x);});
    const big=Object.values(groups).filter(g=>g.length>=2).sort((a,b)=>b.length-a.length)[0];
    rows=big||[];
  }
  return rows.length;
}"""

_FILL_JS = r"""(fields) => {
  let n=0;
  const bad=(el)=>!!el.closest('nav,aside,[role=navigation],[class*="sidebar-nav"],[class*="search"]')
     || ['hidden','search','checkbox','radio','file'].includes(el.type) || el.disabled || el.readOnly || el.offsetParent===null;
  const set=(el,v)=>{const proto=el.tagName==='TEXTAREA'?window.HTMLTextAreaElement:window.HTMLInputElement;
    const d=Object.getOwnPropertyDescriptor(proto.prototype,'value'); el.focus(); d.set.call(el,v);
    el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); el.blur();};
  // 1. contract ids from the create-form recipe
  for(const f of fields){let el=document.querySelector('[data-spec-id="'+f.toLowerCase()+'input"]');
    if(el&&el.tagName!=='INPUT'&&el.tagName!=='TEXTAREA') el=el.querySelector('input,textarea');
    if(el&&!bad(el)){set(el,'QA '+f+' '+Math.floor(performance.now())); n++;}}
  // 2. fallback: ANY visible, editable, non-nav text input/textarea on the page (modal or form)
  if(n===0){[...document.querySelectorAll('input,textarea')]
     .filter(el=>!bad(el) && (el.tagName==='TEXTAREA' || ['text','email','url',''].includes(el.type)))
     .forEach((el,i)=>{set(el,'QA test '+i); n++;});}
  // 3. native dropdowns (partial handling for FK pickers): pick the last real option
  [...document.querySelectorAll('select')]
    .filter(el=>el.offsetParent!==null && !el.disabled && !el.closest('nav,aside,[class*="sidebar-nav"]'))
    .forEach(el=>{ if(el.options.length>1){ el.selectedIndex=el.options.length-1;
       el.dispatchEvent(new Event('change',{bubbles:true})); n++; } });
  return n;
}"""


def _drive_create(page, base_url: str, spec: dict, form_screen: dict, entity: str) -> dict:
    """Count rows on the list screen → click the "New <entity>" entry point (handles a
    modal on the list OR a nav to a form screen, uniformly) → fill the editable inputs →
    save → reload the list → assert the count grew. Verdict names exactly what happened."""
    from harness.prompt_recipes import _form_fields, _list_screen_for_entity
    r = {"entity": entity, "screen": form_screen["id"]}
    base = base_url.rstrip("/")
    try:
        list_screen = _list_screen_for_entity(spec, entity)
        if not list_screen:
            r["verdict"] = "NO_LIST_SCREEN (cannot measure persistence)"
            return r
        # A create screen that requires a parent-context input param (e.g. tasks needs ListId)
        # is only reachable faithfully by navigating from the parent list, which supplies a real
        # parent id — so the create gets a valid mandatory FK on save (seam 3c).
        needs_ctx = any(ip.get("references") for ip in form_screen.get("inputParameters", []))
        ctx_nav = _parent_context_nav(spec, form_screen) if needs_ctx else None
        if ctx_nav:
            parent_route, click_label = ctx_nav
            page.goto(base + "/" + parent_route.lstrip("/"), wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(2500)
            opened_parent = page.evaluate(
                r"""(label)=>{const re=label?new RegExp('^\\s*'+label+'\\s*$','i'):/^\s*(open|view|details?)\s*$/i;
                  const b=[...document.querySelectorAll('button,a,.btn,[role=button]')]
                     .find(x=>re.test((x.innerText||'').trim()) && !x.closest('nav,aside,[class*="sidebar-nav"]'));
                  if(b){b.click(); return true;} return false;}""", click_label)
            r["parentOpened"] = opened_parent
            if not opened_parent:
                r["verdict"] = ("NO_PARENT_CONTEXT (no parent-list entry point to supply "
                                + form_screen["id"] + "'s required context)")
                return r
            page.wait_for_timeout(2800)
            list_url = page.url  # the contextualized child URL (carries the real parent id)
        else:
            list_url = base + "/" + _route_of(spec, list_screen).lstrip("/")
        page.goto(list_url, wait_until="networkidle", timeout=45000); page.wait_for_timeout(2500)
        before = page.evaluate(_COUNT_JS, entity); r["before"] = before
        # the create entry point on the list screen: "New <entity>" / "+ New" / "Create"
        opened = page.evaluate(
            r"""(entity)=>{const re=new RegExp('(new|create|add)\\s*('+entity+')?|^\\s*\\+\\s*new','i');
              const b=[...document.querySelectorAll('button,a,.btn,[role=button]')]
                 .find(x=>re.test((x.innerText||'').trim()) && !x.closest('nav,aside,[class*="sidebar-nav"]'));
              if(b){b.click(); return (b.innerText||'').trim();} return null;}""", entity)
        r["openedVia"] = opened
        if not opened:
            r["verdict"] = "NO_CREATE_ENTRY (no New/Create/Add button on the list)"; return r
        page.wait_for_timeout(2600)
        filled = page.evaluate(_FILL_JS, _form_fields(spec, entity)); r["inputsFilled"] = filled
        if filled == 0:
            r["verdict"] = "FORM_NOT_FOUND ('New' opened no editable form — dead button / read-only)"; return r
        page.wait_for_timeout(400)
        saved = page.evaluate(
            r"""(entity)=>{let b=document.querySelector('[data-spec-id="save'+entity.toLowerCase()+'btn"]');
              if(!b) b=[...document.querySelectorAll('button,a,.btn,[role=button]')]
                 .find(x=>/^\s*(save|create|add|submit|done)\b/i.test((x.innerText||'').trim()));
              if(b){b.click(); return (b.innerText||'save').trim();} return null;}""", entity)
        r["saveClicked"] = saved
        if not saved:
            r["verdict"] = "SAVE_NOT_FOUND (form present but no save/create button)"; return r
        page.wait_for_timeout(3200)
        page.goto(list_url, wait_until="networkidle", timeout=45000); page.wait_for_timeout(2800)
        after = page.evaluate(_COUNT_JS, entity); r["after"] = after
        r["verdict"] = "PERSISTS" if (after is not None and before is not None and after > before) \
            else "NO_PERSIST (submitted, list row count did not grow after reload)"
    except Exception as e:
        r["verdict"] = "ERROR " + repr(e)[:90]
    return r


def _goto_entity_list(page, base: str, spec: dict, form_screen: dict, entity: str):
    """Navigate to the entity's list, contextualized via the parent nav when the screen needs a
    parent input param (seam 3c). Returns (list_url, None) or (None, error_verdict)."""
    from harness.prompt_recipes import _list_screen_for_entity
    list_screen = _list_screen_for_entity(spec, entity)
    if not list_screen:
        return None, "NO_LIST_SCREEN (cannot measure)"
    needs_ctx = any(ip.get("references") for ip in form_screen.get("inputParameters", []))
    ctx_nav = _parent_context_nav(spec, form_screen) if needs_ctx else None
    if ctx_nav:
        parent_route, click_label = ctx_nav
        page.goto(base + "/" + parent_route.lstrip("/"), wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2500)
        opened = page.evaluate(
            r"""(label)=>{const re=label?new RegExp('^\\s*'+label+'\\s*$','i'):/^\s*(open|view|details?)\s*$/i;
              const b=[...document.querySelectorAll('button,a,.btn,[role=button]')]
                 .find(x=>re.test((x.innerText||'').trim()) && !x.closest('nav,aside,[class*="sidebar-nav"]'));
              if(b){b.click(); return true;} return false;}""", click_label)
        if not opened:
            return None, "NO_PARENT_CONTEXT (no parent-list entry point)"
        page.wait_for_timeout(2800)
        list_url = page.url
    else:
        list_url = base + "/" + _route_of(spec, list_screen).lstrip("/")
    page.goto(list_url, wait_until="networkidle", timeout=45000); page.wait_for_timeout(2500)
    return list_url, None


_CLICK_ROWACTION_JS = r"""([specId, textRe]) => {
  const inNav=(el)=>!!el.closest('nav,aside,[class*="sidebar-nav"]');
  let b=[...document.querySelectorAll('[data-spec-id="'+specId+'"]')].find(x=>!inNav(x));
  if(!b){ const re=new RegExp(textRe,'i');
    b=[...document.querySelectorAll('button,a,.btn,[role=button]')]
       .find(x=>re.test((x.innerText||'').trim()) && !inNav(x)); }
  if(b){ b.click(); return true; } return false;
}"""

_SET_FIELD_JS = r"""([fields, val]) => {
  const bad=(el)=>el.disabled||el.readOnly||el.offsetParent===null||el.closest('nav,aside,[class*="sidebar-nav"]');
  const set=(el,v)=>{const d=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value');
    el.focus(); d.set.call(el,v); el.dispatchEvent(new Event('input',{bubbles:true}));
    el.dispatchEvent(new Event('change',{bubbles:true})); el.blur();};
  for(const f of fields){ let el=document.querySelector('[data-spec-id="'+f.toLowerCase()+'input"]');
    if(el&&el.tagName!=='INPUT'&&el.tagName!=='TEXTAREA') el=el.querySelector('input,textarea');
    if(el&&!bad(el)){ set(el,val); return true; } }
  return false;
}"""


def _drive_delete(page, base_url: str, spec: dict, form_screen: dict, entity: str) -> dict:
    """Per-row Delete: count → click a row's Delete → reload → assert the count dropped."""
    r = {"entity": entity, "screen": form_screen["id"], "op": "delete"}
    base = base_url.rstrip("/")
    try:
        list_url, err = _goto_entity_list(page, base, spec, form_screen, entity)
        if err:
            r["verdict"] = err; return r
        before = page.evaluate(_COUNT_JS, entity); r["before"] = before
        if not before:
            r["verdict"] = "NO_ROWS (nothing to delete)"; return r
        clicked = page.evaluate(_CLICK_ROWACTION_JS, ["delete" + entity.lower() + "btn", r"^\s*delete\s*$"])
        if not clicked:
            r["verdict"] = "NO_DELETE_ENTRY (no Delete control on rows)"; return r
        page.wait_for_timeout(3200)
        page.goto(list_url, wait_until="networkidle", timeout=45000); page.wait_for_timeout(2800)
        after = page.evaluate(_COUNT_JS, entity); r["after"] = after
        r["verdict"] = "DELETES" if (after is not None and before is not None and after < before) \
            else "NO_DELETE (row count did not drop after reload)"
    except Exception as e:
        r["verdict"] = "ERROR " + repr(e)[:90]
    return r


def _drive_update(page, base_url: str, spec: dict, form_screen: dict, entity: str) -> dict:
    """Per-row Update: open a row's Edit (prefills the form) → set the first text field to a unique
    marker → save → reload → assert the marker appears in the list."""
    from harness.prompt_recipes import _form_fields
    r = {"entity": entity, "screen": form_screen["id"], "op": "update"}
    base = base_url.rstrip("/")
    try:
        list_url, err = _goto_entity_list(page, base, spec, form_screen, entity)
        if err:
            r["verdict"] = err; return r
        if not page.evaluate(_COUNT_JS, entity):
            r["verdict"] = "NO_ROWS (nothing to edit)"; return r
        opened = page.evaluate(_CLICK_ROWACTION_JS, ["edit" + entity.lower() + "btn", r"^\s*edit\s*$"])
        if not opened:
            r["verdict"] = "NO_EDIT_ENTRY (no Edit control on rows)"; return r
        page.wait_for_timeout(1800)
        marker = "QAEDIT" + str(int(page.evaluate("()=>Math.floor(performance.now())")))
        setok = page.evaluate(_SET_FIELD_JS, [_form_fields(spec, entity), marker])
        if not setok:
            r["verdict"] = "EDIT_FORM_NOT_FOUND (Edit opened no editable field)"; return r
        page.wait_for_timeout(300)
        saved = page.evaluate(
            r"""(entity)=>{let b=document.querySelector('[data-spec-id="save'+entity.toLowerCase()+'btn"]');
              if(!b) b=[...document.querySelectorAll('button,a,.btn,[role=button]')]
                 .find(x=>/^\s*(save|update|submit|done)\b/i.test((x.innerText||'').trim()));
              if(b){b.click(); return true;} return false;}""", entity)
        if not saved:
            r["verdict"] = "SAVE_NOT_FOUND (edit form present but no save button)"; return r
        page.wait_for_timeout(3200)
        page.goto(list_url, wait_until="networkidle", timeout=45000); page.wait_for_timeout(2800)
        present = page.evaluate("(m)=>document.body.innerText.includes(m)", marker)
        r["marker"] = marker
        r["verdict"] = "UPDATES" if present else "NO_UPDATE (edited value not present after reload)"
    except Exception as e:
        r["verdict"] = "ERROR " + repr(e)[:90]
    return r


def run_behavioral(spec: dict, base_url: str, login: dict) -> list[dict]:
    """For every spec'd Create/Update/Delete action, drive it and assert the change persists.
    Order per screen: create (adds a row) → update (edits one) → delete (removes one)."""
    from harness.prompt_recipes import _screen_write_entity
    sync_playwright = _lazy_playwright()
    results, seen = [], set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
        _apply_login(page, base_url, login)
        for screen in spec.get("screens", []):
            does_all = set()
            for a in screen.get("actions", []):
                does_all |= set(a.get("does", []))
            entity = _screen_write_entity(spec, screen)
            if not entity:
                continue
            for kind, driver in (("CreateEntity", _drive_create),
                                 ("UpdateEntity", _drive_update),
                                 ("DeleteEntity", _drive_delete)):
                key = (screen["id"], entity, kind)
                if kind in does_all and key not in seen:
                    seen.add(key)
                    results.append(driver(page, base_url, spec, screen, entity))
        browser.close()
    return results


_CHART_JS = r"""(chartId) => {
  const inNav=(el)=>!!el.closest('nav,aside,[role=navigation],[class*="sidebar-nav"]');
  const byId = chartId && (document.querySelector('[data-spec-id="'+chartId.toLowerCase()+'"]')
             || document.querySelector('[id*="'+chartId+'"]'));
  const scope = byId || document.querySelector('main, [class*="content"]') || document;
  const gfx = [...scope.querySelectorAll('svg, canvas')].filter(x=>!inNav(x)
              && (x.getBoundingClientRect().width>40) && (x.getBoundingClientRect().height>40));
  return gfx.length;    // a rendered chart is a non-trivial svg/canvas in the content area
}"""


def run_render(spec: dict, base_url: str, login: dict) -> list[dict]:
    """Phase 2 render checks: a spec'd chart actually RENDERS (a non-trivial svg/canvas), and the
    spec'd theme is APPLIED (its palette tokens live in the loaded stylesheet). Verdicts, exit nonzero
    on any fail — so a chart that authored in-model but doesn't paint, or an inert theme, FAILS."""
    sync_playwright = _lazy_playwright()
    results = []
    base = base_url.rstrip("/")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
        _apply_login(page, base_url, login)
        theme = (spec.get("design") or {}).get("theme")
        if theme:
            first = spec.get("screens", [{}])[0]
            page.goto(base + "/" + _route_of(spec, first.get("id", "")).lstrip("/"),
                      wait_until="networkidle", timeout=45000); page.wait_for_timeout(2500)
            palette = theme.get("palette") or {}
            applied = page.evaluate(
                r"""(keys)=>{const cs=getComputedStyle(document.documentElement);
                  return keys.some(k=>cs.getPropertyValue('--'+k).trim().length>0);}""",
                list(palette.keys()) or ["primary"])
            results.append({"kind": "theme", "target": "design.theme",
                            "verdict": "APPLIED" if applied else "NOT_APPLIED (palette tokens absent from live stylesheet)"})
        for s in spec.get("screens", []):
            for ch in s.get("charts", []) or []:
                page.goto(base + "/" + _route_of(spec, s["id"]).lstrip("/"),
                          wait_until="networkidle", timeout=45000); page.wait_for_timeout(3500)
                n = page.evaluate(_CHART_JS, ch.get("id", ""))
                results.append({"kind": "chart", "screen": s["id"], "target": ch.get("id"),
                                "verdict": "RENDERS" if n else "NO_CHART (no non-trivial svg/canvas in content)"})
        browser.close()
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="harness-capture",
        description="Runtime (rendered-DOM) verification channel: drive the live app, emit a "
                    "screen-walk snapshot for harness-verify --phase live, optionally gate.")
    ap.add_argument("spec", type=Path, help="app_spec.json")
    ap.add_argument("--base-url", required=True, help="deployed app base URL")
    ap.add_argument("--login-config", default=None,
                    help="login config as inline JSON or a path to a .json file (see module docstring)")
    ap.add_argument("--out", type=Path, default=None, help="output dir for snapshot + screenshots")
    ap.add_argument("--nav-mode", choices=["href", "click", "both"], default="href",
                    help="how to confirm nav edges (default href; click drives real navigation)")
    ap.add_argument("--assert", dest="do_assert", action="store_true",
                    help="also run capture-channel assertions inline and exit nonzero on any fail")
    ap.add_argument("--behavioral", action="store_true",
                    help="Phase 6 WORKING gate: drive each spec'd create action and assert a row persists")
    ap.add_argument("--render", action="store_true",
                    help="Phase 2 render gate: assert each spec'd chart RENDERS and design.theme is APPLIED at runtime")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON to stdout")
    args = ap.parse_args(argv)

    if not args.spec.exists():
        print(f"spec not found: {args.spec}", file=sys.stderr)
        return 1
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"spec is not valid JSON: {e}", file=sys.stderr)
        return 1

    if args.login_config:
        raw = args.login_config
        p = Path(raw)
        try:
            login = json.loads(p.read_text(encoding="utf-8")) if p.exists() else json.loads(raw)
        except Exception as e:
            print(f"--login-config unreadable ({e})", file=sys.stderr)
            return 1
    else:
        login = _login_from_auth(spec)   # seam 6: authenticate from the spec's auth block

    if args.behavioral:
        results = run_behavioral(spec, args.base_url, login)
        good = {"PERSISTS", "UPDATES", "DELETES"}
        n_ok = sum(1 for r in results if r["verdict"] in good)
        n_fail = len(results) - n_ok
        if args.json:
            print(json.dumps({"behavioral": results, "pass": n_ok, "fail": n_fail}, indent=2))
        else:
            print(f"behavioral gate — {len(results)} write-path(s): {n_ok} ok, {n_fail} fail")
            for r in results:
                mark = "ok " if r["verdict"] in good else "FAIL"
                delta = f" ({r.get('before')}->{r.get('after')})" if "after" in r else ""
                print(f"  [{mark}] {r['screen']} · {r.get('op', 'create')} {r['entity']} — {r['verdict']}{delta}")
            if not results:
                print("  (no Create/Update/Delete actions in spec — nothing to behaviorally verify)")
        return 1 if n_fail else 0

    if args.render:
        results = run_render(spec, args.base_url, login)
        good = {"APPLIED", "RENDERS"}
        n_ok = sum(1 for r in results if r["verdict"] in good)
        n_fail = len(results) - n_ok
        if args.json:
            print(json.dumps({"render": results, "pass": n_ok, "fail": n_fail}, indent=2))
        else:
            print(f"render gate — {len(results)} check(s): {n_ok} ok, {n_fail} fail")
            for r in results:
                mark = "ok " if r["verdict"] in good else "FAIL"
                where = r.get("screen", "") and f"{r['screen']}·"
                print(f"  [{mark}] {r['kind']} {where}{r.get('target')} — {r['verdict']}")
            if not results:
                print("  (no charts or design.theme in spec — nothing to render-verify)")
        return 1 if n_fail else 0

    out_dir = args.out
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    snapshot = build_runtime_snapshot(spec, args.base_url, login, out_dir, args.nav_mode)

    snap_path = None
    if out_dir is not None:
        snap_path = out_dir / "runtime_screens.json"
        snap_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    exit_code = 0
    assert_summary = None
    if args.do_assert:
        results, n_pass, n_fail = _assert_capture_channel(spec, snapshot)
        assert_summary = {"pass": n_pass, "fail": n_fail,
                          "results": [{"screen": s, **r.__dict__} for s, r in results]}
        exit_code = 1 if n_fail else 0

    if args.json:
        print(json.dumps({"snapshot": snapshot, "snapshot_path": str(snap_path) if snap_path else None,
                          "assert": assert_summary}, indent=2))
    else:
        n_screens = len(snapshot["screens"])
        n_comp = sum(len(s["components"]) for s in snapshot["screens"])
        n_nav = sum(len(s["navigation"]) for s in snapshot["screens"])
        print(f"harness-capture — {n_screens} screen(s): {n_comp} component(s) resolved, "
              f"{n_nav} nav edge(s) confirmed in the live DOM.")
        if snap_path:
            print(f"snapshot -> {snap_path}\n  feed to: harness-verify {args.spec} --phase live --screens {snap_path}")
        ce = snapshot.get("consoleErrors")
        if ce:
            print(f"console errors on: {', '.join(ce)}")
        if assert_summary:
            print(f"\ncapture-channel assertions: {assert_summary['pass']} pass, {assert_summary['fail']} fail")
            for row in assert_summary["results"]:
                if row["status"] != "pass":
                    print(f"  [{row['status']}] {row['screen']} · {row['kind']} — {row['detail']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
