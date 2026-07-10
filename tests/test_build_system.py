"""Unit tests for the cross-app system executor (harness.build_system) — general (retail fixture,
not Rivian). Drives build_system against a FakeSystemMCP that always authors/publishes OK, and asserts
the orchestration: modular gate, topo order (producer-before-consumer), deterministic <prefix><Logical>
naming, and producerApp reference rewriting to the prefixed producer name."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from harness import build_system
from harness.mcp_client import MentorRunResult


class FakeSystemMCP:
    """Minimal always-succeeds client for the system executor: every author + publish lands, every
    read confirms. Records the ORDER apps were created and the specs' producerApp refs at build time."""
    def __init__(self):
        self._n = 0
        self.created: list[str] = []            # app names in creation order
        self.built_refs: dict[str, list] = {}   # app_key -> producerApp names seen when building it
        self._key_to_name: dict[str, str] = {}
        self._cur_app_key = None

    # -- app lifecycle --
    async def app_list(self, search=None):
        return {"results": []}                  # nothing pre-exists → always create (clean run)

    async def app_create(self, name, kind="CrossDevice"):
        self._n += 1
        key = f"key-{self._n}-{name}"
        self.created.append(name)
        self._key_to_name[key] = name
        return {"key": key}

    async def env_list(self):
        return {"results": [{"key": "env-dev", "purpose": "Development"}]}

    async def env_app(self, key, env_key):
        return {"url": f"https://app/{self._key_to_name.get(key, 'x')}"}

    # -- mentor turn --
    async def mentor_start(self, app_key=None, prompt="", *, session_id=None, session_token=None, fresh_context=False):
        self._cur_app_key = app_key or self._cur_app_key
        self._n += 1
        return f"run-{self._n}"

    async def mentor_poll(self, run_id, timeout_seconds=400, **kw):
        return MentorRunResult(run_id=run_id, status="succeeded", stdout="ok", compile_errors=[],
                               summary="", session_id="sid", session_token="tok", raw_events=[])

    async def mentor_cancel(self, run_id):
        pass

    async def publish_start(self, session_id, session_token, env_key=""):
        self._n += 1
        return f"pub-{self._n}"

    async def publish_wait(self, pub_id, timeout_seconds=600):
        return {"state": "succeeded", "revision": 1}

    # -- reads (verify) all confirm present --
    async def context_entities(self, app_key, **kw):
        return {"items": []}       # empty → 'cannot verify' → treated as landed (never a false defect)

    async def context_screens(self, app_key, **kw):
        return {"items": []}


def _retail():
    fx = Path(__file__).parent / "fixtures"
    system = json.loads((fx / "system_retail.json").read_text())
    domain = json.loads((fx / "domain_retail.json").read_text())
    return system, domain


def test_build_system_drives_topo_order_with_deterministic_names(tmp_path):
    system, domain = _retail()
    mcp = FakeSystemMCP()
    result = asyncio.run(build_system.build_system(
        system, domain, prefix="Shop", mcp=mcp,
        state_dir=tmp_path, prompts_dir=tmp_path / "p"))
    assert result.modular and result.ok
    # every built app is named <prefix><Logical>
    assert all(a.name.startswith("Shop") for a in result.apps)
    # producers (core layer) are created BEFORE the consumers that depend on them
    names = mcp.created
    cores = [n for n in names if "Core" in n]
    enduser = [a.name for a in result.apps if a.layer == "enduser"]
    for eu in enduser:
        for c in cores:
            # a consumer references its core → the core must have been created earlier
            if c in names and eu in names:
                assert names.index(c) < names.index(eu)


def test_build_system_rewrites_producer_refs_to_prefixed_name():
    # a consumer's appReferences.producerApp is rewritten to <prefix><producer> so the reference
    # resolves to the app this run actually builds (closes the manual-threading gap B4).
    spec = {"appReferences": [{"producerApp": "OrderingCore", "elements": [{"name": "Order", "kind": "Entity"}]}]}
    out = build_system._rewrite_producer_refs(json.loads(json.dumps(spec)), "Shop")
    assert out["appReferences"][0]["producerApp"] == "ShopOrderingCore"
    # an already-prefixed name is left alone (idempotent)
    spec2 = {"appReferences": [{"producerApp": "ShopOrderingCore", "elements": []}]}
    out2 = build_system._rewrite_producer_refs(json.loads(json.dumps(spec2)), "Shop")
    assert out2["appReferences"][0]["producerApp"] == "ShopOrderingCore"


def test_build_system_rejects_a_monolith(tmp_path):
    mono = json.loads((Path(__file__).parent / "fixtures" / "system_monolith.json").read_text())
    result = asyncio.run(build_system.build_system(mono, None, prefix="X", mcp=FakeSystemMCP(),
                                                   state_dir=tmp_path, prompts_dir=tmp_path / "p"))
    assert result.modular is False and not result.ok
