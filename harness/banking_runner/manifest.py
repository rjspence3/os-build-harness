"""Manifest loaders for the banking-app rebuild.

Reads the four YAML manifests in data/MCP_RECIPES/apps/home_banking/:
  - entities.yaml   (static + server entities)
  - roles.yaml      (3 roles)
  - actions.yaml    (152 action signatures, 5 with bodies)
  - screens.yaml    (16 screens)

Each loader returns a Pydantic-validated dataclass-like model. Missing fields
default reasonably; structural errors raise ManifestError.

The manifests describe the WHOLE suite (Core + Portal + Backoffice etc.) — the
caller picks which app to materialize via the `app` field on each entity/role/etc.

Path resolution: defaults to data/MCP_RECIPES/apps/home_banking/ relative to
the repo root, but caller can override for tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


class ManifestError(Exception):
    """Raised when a manifest YAML is structurally invalid."""


# ─── Entities ─────────────────────────────────────────────────────────────────

@dataclass
class Attribute:
    """One column on an entity (static or server)."""
    name: str
    data_type: str             # "Text", "Long Integer", "<Entity> Identifier", etc.
    length: Optional[int] = None
    decimals: Optional[int] = None
    is_mandatory: bool = False
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Attribute":
        return cls(
            name=d["name"],
            data_type=d["dataType"],
            length=d.get("length"),
            decimals=d.get("decimals"),
            is_mandatory=d.get("isMandatory", False),
            description=d.get("description"),
        )


@dataclass
class StaticEntity:
    name: str
    pk_name: str
    pk_data_type: str          # "Integer" or "Text"
    pk_length: Optional[int]   # for Text PKs only
    attributes: list[Attribute]
    records: list[str]         # record identifier strings
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StaticEntity":
        pk = d.get("pk", {"name": "Id", "dataType": "Integer"})
        return cls(
            name=d["name"],
            pk_name=pk["name"],
            pk_data_type=pk["dataType"],
            pk_length=pk.get("length"),
            attributes=[Attribute.from_dict(a) for a in d.get("attributes", [])],
            records=d.get("records", []),
            description=d.get("description"),
        )


@dataclass
class ServerEntity:
    name: str
    pk_name: str
    pk_data_type: str          # always "Long Integer" canonical
    pk_is_auto_number: bool
    attributes: list[Attribute]
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ServerEntity":
        pk = d.get("pk", {"name": "Id", "dataType": "Long Integer", "isAutoNumber": True})
        return cls(
            name=d["name"],
            pk_name=pk["name"],
            pk_data_type=pk["dataType"],
            pk_is_auto_number=pk.get("isAutoNumber", True),
            attributes=[Attribute.from_dict(a) for a in d.get("attributes", [])],
            description=d.get("description"),
        )


@dataclass
class EntitiesManifest:
    app: str
    app_asset_key: str
    static_entities: list[StaticEntity]
    server_entities: list[ServerEntity]

    @property
    def total_count(self) -> int:
        return len(self.static_entities) + len(self.server_entities)


def load_entities(path: Path) -> EntitiesManifest:
    """Parse entities.yaml. Raises ManifestError on structural problems."""
    data = _load_yaml(path)
    try:
        return EntitiesManifest(
            app=data["app"],
            app_asset_key=data["app_assetKey"],
            static_entities=[StaticEntity.from_dict(e) for e in data.get("static_entities", [])],
            server_entities=[ServerEntity.from_dict(e) for e in data.get("server_entities", [])],
        )
    except KeyError as exc:
        raise ManifestError(f"entities.yaml missing field {exc}") from exc


# ─── Roles ─────────────────────────────────────────────────────────────────────

@dataclass
class Role:
    name: str
    is_public: bool
    description: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Role":
        return cls(
            name=d["name"],
            is_public=d.get("isPublic", False),
            description=(d.get("description") or "").strip(),
        )


@dataclass
class RolesManifest:
    app: str
    app_asset_key: str
    roles: list[Role]


def load_roles(path: Path) -> RolesManifest:
    data = _load_yaml(path)
    try:
        return RolesManifest(
            app=data["app"],
            app_asset_key=data["app_assetKey"],
            roles=[Role.from_dict(r) for r in data.get("roles", [])],
        )
    except KeyError as exc:
        raise ManifestError(f"roles.yaml missing field {exc}") from exc


# ─── Actions ───────────────────────────────────────────────────────────────────

@dataclass
class ActionParameter:
    name: str
    direction: str             # "Input" | "Output"
    data_type: str
    is_mandatory: bool = False
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ActionParameter":
        return cls(
            name=d["name"],
            direction=d["direction"],
            data_type=d["dataType"],
            is_mandatory=d.get("isMandatory", False),
            description=d.get("description"),
        )


@dataclass
class Action:
    name: str
    action_type: str           # "ServerAction" | "ClientAction" | "ServiceAction"
    is_public: bool
    parameters: list[ActionParameter]
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Action":
        return cls(
            name=d["name"],
            action_type=d.get("actionType", "ServerAction"),
            is_public=d.get("isPublic", False),
            parameters=[ActionParameter.from_dict(p) for p in d.get("parameters", [])],
            description=d.get("description"),
        )

    @property
    def inputs(self) -> list[ActionParameter]:
        return [p for p in self.parameters if p.direction == "Input"]

    @property
    def outputs(self) -> list[ActionParameter]:
        return [p for p in self.parameters if p.direction == "Output"]


@dataclass
class ActionsAppSection:
    """One per-app block from actions.yaml (Core / Portal / Backoffice / ...)."""
    app: str
    server_actions: list[Action] = field(default_factory=list)
    client_actions: list[Action] = field(default_factory=list)
    service_actions: list[Action] = field(default_factory=list)


@dataclass
class ActionsManifest:
    apps: list[ActionsAppSection]


_ACTION_APP_KEYS = ("core", "portal", "backoffice", "loan_request", "mobile")


def load_actions(path: Path) -> ActionsManifest:
    """Parse actions.yaml. Top-level keys are app names (core, portal, ...);
    each maps to a dict with server_actions / client_actions / service_actions lists."""
    data = _load_yaml(path)
    apps: list[ActionsAppSection] = []

    for app_name in _ACTION_APP_KEYS:
        section = data.get(app_name)
        if not isinstance(section, dict):
            continue
        sec = ActionsAppSection(app=app_name)
        for a in section.get("server_actions", []) or []:
            sec.server_actions.append(Action.from_dict(a))
        for a in section.get("client_actions", []) or []:
            sec.client_actions.append(Action.from_dict(a))
        for a in section.get("service_actions", []) or []:
            sec.service_actions.append(Action.from_dict(a))
        apps.append(sec)

    return ActionsManifest(apps=apps)


# ─── Screens ───────────────────────────────────────────────────────────────────

@dataclass
class ScreenInputParam:
    name: str
    data_type: str
    required: bool = False

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ScreenInputParam":
        return cls(
            name=d["name"],
            data_type=d["data_type"],
            required=d.get("required", False),
        )


@dataclass
class Screen:
    name: str
    key: str
    title_expression: str
    roles: list[str]
    inputs: list[ScreenInputParam]
    ui_flow: str               # "Common" | "MainFlow" | "PDF"
    pattern_hint: Optional[str] = None   # "dashboard" | "table" | "wizard" | etc.
    priority: Optional[str] = None       # "P0" | "P1" | "P2"
    is_public: bool = False
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any], ui_flow: str) -> "Screen":
        return cls(
            name=d["name"],
            key=d.get("key", ""),
            title_expression=d.get("title_expression", ""),
            roles=d.get("roles", []) or [],
            inputs=[ScreenInputParam.from_dict(i) for i in d.get("inputs", []) or []],
            ui_flow=ui_flow,
            pattern_hint=d.get("pattern_hint"),
            priority=d.get("priority"),
            is_public=d.get("is_public", False),
            description=d.get("description"),
        )


@dataclass
class ScreensAppSection:
    app: str
    app_key: str
    screens: list[Screen]


@dataclass
class ScreensManifest:
    apps: list[ScreensAppSection]


def load_screens(path: Path) -> ScreensManifest:
    data = _load_yaml(path)
    apps: list[ScreensAppSection] = []

    for app_name in ("portal", "backoffice"):  # only these have screens in current manifest
        section = data.get(app_name)
        if not section:
            continue
        screens: list[Screen] = []
        for ui_flow, ui_screens in (section.get("uiflows") or {}).items():
            for s in ui_screens or []:
                # Skip auto-generated entries marked do-not-author
                desc = s.get("description") or ""
                if "do not re-author" in desc.lower():
                    continue
                screens.append(Screen.from_dict(s, ui_flow))
        apps.append(ScreensAppSection(
            app=section.get("app_name", app_name),
            app_key=section.get("app_key", ""),
            screens=screens,
        ))

    return ScreensManifest(apps=apps)


# ─── Bundle loader ─────────────────────────────────────────────────────────────

@dataclass
class HomeBankingManifest:
    """All four manifests loaded together. Use this for the main runner entry."""
    entities: EntitiesManifest
    roles: RolesManifest
    actions: ActionsManifest
    screens: ScreensManifest
    manifest_dir: Path


DEFAULT_MANIFEST_DIR = Path(__file__).resolve().parents[2] / "builds" / "home_banking" / "MCP_RECIPES" / "apps" / "home_banking"


def load_home_banking(manifest_dir: Path = DEFAULT_MANIFEST_DIR) -> HomeBankingManifest:
    """Load all four banking manifests from one directory."""
    if not manifest_dir.is_dir():
        raise ManifestError(f"Manifest directory not found: {manifest_dir}")
    return HomeBankingManifest(
        entities=load_entities(manifest_dir / "entities.yaml"),
        roles=load_roles(manifest_dir / "roles.yaml"),
        actions=load_actions(manifest_dir / "actions.yaml"),
        screens=load_screens(manifest_dir / "screens.yaml"),
        manifest_dir=manifest_dir,
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ManifestError(f"Manifest file not found: {path}")
    with path.open() as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            raise ManifestError(f"YAML parse error in {path}: {exc}") from exc
