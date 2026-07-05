"""Tests for the v0.2 additive expressiveness constructs (Pillar 3):
app-level `navigation` (shared nav), app-level `auth`, per-screen `access`, and
the product-UI component types Modal/Tabs/Avatar/Badge/CommandPalette.

Confirms: (a) a spec that USES the new constructs correctly passes schema +
cross-ref; (b) each dangling reference is caught as a gating spec-gap; (c) a spec
that does NOT use them is unaffected (backward-compatible).
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.verify import validate_spec


def _gating(spec):
    return [f for f in validate_spec(spec) if f.severity == "spec-gap"]


def _base():
    """A minimal spec exercising navigation + auth + access + new component types."""
    return {
        "specVersion": "0.2",
        "app": {"name": "t", "roles": ["User", "Admin"]},
        "dataModel": {"entities": [
            {"name": "Member", "attributes": [
                {"name": "Id", "dataType": "Identifier", "isIdentifier": True, "mandatory": True},
                {"name": "IsAdmin", "dataType": "Boolean"}]}]},
        "navigation": {"block": "SidebarNav", "style": "sidebar",
                       "items": [{"label": "Home", "toScreen": "home"}], "showOn": "all"},
        "auth": {"provider": "app-local", "userEntity": "Member", "adminAttribute": "IsAdmin",
                 "loginScreen": "login", "sessionKeys": {"userId": "ln_uid", "userName": "ln_name"},
                 "testUsers": [{"role": "Admin", "label": "Rob", "isAdmin": True},
                               {"role": "User", "label": "Kira"}]},
        "screens": [
            {"id": "home", "name": "Home", "route": "/home",
             "components": [{"id": "nav", "type": "Sidebar"}, {"id": "palette", "type": "CommandPalette"},
                            {"id": "who", "type": "Avatar"}],
             "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "nav"}]}},
            {"id": "admin", "name": "Admin", "route": "/admin",
             "access": {"adminOnly": True, "redirectTo": "home"},
             "components": [{"id": "tbl", "type": "Table", "boundTo": "Member"},
                            {"id": "tabs", "type": "Tabs"}, {"id": "dlg", "type": "Modal"}],
             "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "tbl"}]}},
            {"id": "login", "name": "Login", "route": "/login",
             "components": [{"id": "form", "type": "Form"}],
             "acceptance": {"assertions": [{"kind": "componentPresent", "componentId": "form"}]}},
        ],
    }


def test_base_spec_with_all_new_constructs_is_clean():
    assert _gating(_base()) == []


def test_new_component_types_are_schema_valid():
    # each new product-UI type must pass schema validation (no "not one of enum")
    for t in ("Modal", "Tabs", "Avatar", "Badge", "CommandPalette"):
        spec = _base()
        spec["screens"][0]["components"].append({"id": f"c_{t}", "type": t})
        assert _gating(spec) == [], f"{t} should be a valid component type"


def test_nav_item_dangling_screen_is_gap():
    spec = _base()
    spec["navigation"]["items"].append({"label": "Ghost", "toScreen": "nope"})
    gaps = _gating(spec)
    assert any("navigation item targets unknown screen" in g.summary for g in gaps)


def test_nav_showon_dangling_screen_is_gap():
    spec = _base()
    spec["navigation"]["showOn"] = ["home", "ghost"]
    assert any("navigation showOn references unknown screen" in g.summary for g in _gating(spec))


def test_auth_user_entity_unknown_is_gap():
    spec = _base()
    spec["auth"]["userEntity"] = "Nobody"
    assert any("auth.userEntity unknown" in g.summary for g in _gating(spec))


def test_auth_admin_attribute_not_on_entity_is_gap():
    spec = _base()
    spec["auth"]["adminAttribute"] = "NotAnAttr"
    assert any("auth.adminAttribute not on userEntity" in g.summary for g in _gating(spec))


def test_auth_login_screen_unknown_is_gap():
    spec = _base()
    spec["auth"]["loginScreen"] = "ghostlogin"
    assert any("auth.loginScreen targets unknown screen" in g.summary for g in _gating(spec))


def test_access_requires_unknown_role_is_gap():
    spec = _base()
    spec["screens"][1]["access"] = {"requiresRole": "Wizard"}
    assert any("access.requiresRole not in app.roles" in g.summary for g in _gating(spec))


def test_access_redirect_unknown_screen_is_gap():
    spec = _base()
    spec["screens"][1]["access"] = {"adminOnly": True, "redirectTo": "ghost"}
    assert any("access.redirectTo targets unknown screen" in g.summary for g in _gating(spec))


def test_access_admin_only_without_admin_attribute_is_gap():
    spec = _base()
    del spec["auth"]["adminAttribute"]                       # now nothing to gate on
    spec["screens"][1]["access"] = {"adminOnly": True}
    assert any("access.adminOnly needs auth.adminAttribute" in g.summary for g in _gating(spec))


def test_spec_without_new_constructs_is_unaffected():
    spec = _base()
    del spec["navigation"]
    del spec["auth"]
    for s in spec["screens"]:
        s.pop("access", None)
    assert _gating(spec) == []
