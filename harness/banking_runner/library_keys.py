"""Library element keys for the `addReferenceToElements` MCP tool.

Loads `data/MCP_RECIPES/apps/home_banking/library_element_keys.yaml` and
maps block names to (elementKey, producerKey) pairs. chrome_wrap uses this
to emit an "IMPORT PREREQUISITES" section in its recipe prompts — Mentor
calls `addReferenceToElements` for any library block that may not yet be
imported into the consumer app, then runs the C# code.

The `addReferenceToElements` MCP tool is idempotent in this run: calling it
for already-imported elements is a no-op (verified live 2026-06-08 against
Rebake1 Counter import probe).

Discovered via context_search 2026-06-08 — see the YAML's header comment
for provenance.
"""

from __future__ import annotations

import base64
import uuid as _uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


def compute_global_key(producer_key: str, element_key: str) -> str:
    """Construct an OutSystems globalKey from producer + element UUIDs.

    globalKey = base64url(UUID.bytes_le(producerKey)) + "*" + base64url(UUID.bytes_le(elementKey))

    Verified against live data 2026-06-10: OutSystemsUI Counter's globalKey
    `Kn_hixxDWEm4lMd7mIpycQ*jGWcpKjbIEWYM4W62bEUKQ` round-trips exactly from
    assetKey 8be17f2a-431c-4958-b894-c77b988a7271 + elementKey
    a49c658c-dba8-4520-9833-85bad9b11429 (.NET GUID little-endian byte order,
    urlsafe base64, padding stripped). Source: MCP retest B2-rerun extract +
    Counter probe stub. Makes AddDependency emission fully deterministic —
    no getWebBlock round-trip needed.
    """
    def _b64(u: str) -> str:
        return base64.urlsafe_b64encode(_uuid.UUID(u).bytes_le).decode().rstrip("=")
    return f"{_b64(producer_key)}*{_b64(element_key)}"


_DEFAULT_YAML_PATH = (
    Path(__file__).resolve().parents[2]
    / "builds" / "home_banking" / "MCP_RECIPES" / "apps" / "home_banking"
    / "library_element_keys.yaml"
)


@dataclass(frozen=True)
class ElementRef:
    block_name: str
    library: str
    element_key: str
    producer_key: str


class LibraryKeysIndex:
    """Block-name → ElementRef lookup over the library_element_keys.yaml file."""

    def __init__(self, yaml_path: Optional[Path] = None):
        self._yaml_path = yaml_path or _DEFAULT_YAML_PATH
        self._by_block: dict[str, ElementRef] = {}
        self._missing_names: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self._yaml_path.exists():
            raise FileNotFoundError(
                f"library_element_keys.yaml not found at {self._yaml_path}. "
                f"Run the discovery probe to regenerate it."
            )
        data = yaml.safe_load(self._yaml_path.read_text()) or {}
        libraries = data.get("libraries", {}) or {}
        for lib_name, lib_entry in libraries.items():
            producer_key = (lib_entry or {}).get("producerKey")
            if not producer_key:
                continue
            # `blocks` and `actions` are both {name: elementKey} pairs imported
            # via the same addReferenceToElements path; load both into one
            # name→ref map. (V20: producer actions were previously uncollected.)
            blocks = {**((lib_entry or {}).get("blocks", {}) or {}),
                      **((lib_entry or {}).get("actions", {}) or {})}
            for block_name, element_key in blocks.items():
                if not element_key:
                    continue
                ref = ElementRef(
                    block_name=block_name,
                    library=lib_name,
                    element_key=str(element_key),
                    producer_key=str(producer_key),
                )
                if block_name in self._by_block:
                    # First-library-wins; later libraries' same-named blocks are
                    # ignored. The YAML should not contain collisions; this is
                    # defensive.
                    continue
                self._by_block[block_name] = ref
        for missing in data.get("missing", []) or []:
            name = (missing or {}).get("name")
            if name:
                self._missing_names.add(name)

    def lookup(self, block_name: str) -> Optional[ElementRef]:
        return self._by_block.get(block_name)

    def is_known_missing(self, block_name: str) -> bool:
        """True if the block is in the YAML's `missing` list — meaning it
        doesn't exist as an importable block (primitive widget, or genuinely
        not in this tenant). chrome_wrap should NOT emit an import-pre-step
        for these names."""
        return block_name in self._missing_names


def derive_required_imports(
    block_names: list[str],
    index: Optional[LibraryKeysIndex] = None,
) -> tuple[list[ElementRef], list[str]]:
    """Map a list of block names to (resolved ElementRefs, unresolved names).

    Unresolved names are those that are NOT in the YAML and NOT in the YAML's
    `missing` list — i.e. true unknowns. chrome_wrap can warn for these and
    proceed; the wrap-site lookup may still find them via local MobileFlows
    if they're authored locally.

    Names that ARE in the `missing` list (primitives like Button/Icon) are
    silently dropped — they don't need imports.
    """
    idx = index or LibraryKeysIndex()
    resolved: list[ElementRef] = []
    unresolved: list[str] = []
    seen: set[str] = set()
    for name in block_names:
        if name in seen:
            continue
        seen.add(name)
        ref = idx.lookup(name)
        if ref:
            resolved.append(ref)
        elif idx.is_known_missing(name):
            continue
        else:
            unresolved.append(name)
    return resolved, unresolved


def format_instructions_block(refs: list[ElementRef]) -> str:
    """Emit the `IMPORT PREREQUISITES` instructions block for a chrome_wrap
    recipe prompt. Mentor reads this and:
      1. Cache-warms via `context_search` per producer library (workaround for B2)
      2. Calls `addReferenceToElements` with the elementKey/producerKey pairs
      3. Verifies the import landed via `app_refs` (workaround for B2 silent no-op)
      4. Calls `applyModelApiCode` with the C# code below

    v9 bake (2026-06-09): added cache-warming and verification steps.
    Background: bug B2 (data/bug_reports/B2.md) — `addReferenceToElements`
    silently no-ops (returns `result: null`) when element UUIDs aren't in
    Mentor's resolution cache. The workaround is to context_search the
    producer library first to populate the cache, then verify via app_refs
    that the producer landed.
    """
    if not refs:
        return ""
    # Group refs by library so we emit one context_search per producer.
    producers: dict[str, list[ElementRef]] = {}
    for ref in refs:
        producers.setdefault(ref.library, []).append(ref)

    lines: list[str] = []
    lines.append("IMPORT PREREQUISITES:")
    lines.append("")
    lines.append(
        "Before running the C# code below, complete these THREE STEPS in order. "
        "This works around a known silent-no-op in `addReferenceToElements` when "
        "element UUIDs are not cache-warmed (see bug B2)."
    )
    lines.append("")
    # ── Step 1: cache-warm via context_search per producer ──
    lines.append("STEP 1 — Cache-warm each producer library by calling `context_search`:")
    lines.append("")
    for library_name in producers:
        lines.append(f"  context_search({{")
        lines.append(f'    query: "*",')
        lines.append(f'    objects: ["Blocks"],')
        lines.append(f'    app: "{library_name}",')
        lines.append(f"    limit: 100,")
        lines.append(f'    search_type: "full-text"')
        lines.append(f"  }})")
        lines.append("")
    # ── Step 2: addReferenceToElements ──
    lines.append("STEP 2 — Call `addReferenceToElements` with this exact payload:")
    lines.append("")
    lines.append("```json")
    lines.append("{")
    lines.append('  "elements": [')
    for i, ref in enumerate(refs):
        suffix = "," if i < len(refs) - 1 else ""
        lines.append(
            f'    {{"elementKey": "{ref.element_key}", '
            f'"producerKey": "{ref.producer_key}"}}{suffix}'
            f"  // {ref.library}::{ref.block_name}"
        )
    lines.append("  ]")
    lines.append("}")
    lines.append("```")
    lines.append("")
    # ── Step 3: AddDependency(ParseGlobalKey) — the load-bearing second half ──
    # v12 (2026-06-10): globalKeys are COMPUTED here (see compute_global_key) so
    # the AddDependency lines are literal — no getWebBlock round-trip, zero
    # Mentor judgment. Per the MCP retest B2-rerun: `addReferenceToElements` returning
    # null is EXPECTED (stages the import); the reference only materializes
    # after these AddDependency calls run via applyModelApiCode.
    # NOTE: deliberately NOT a ```csharp fence — scripts/batch_recipes.py's
    # parse_recipe() splits on the FIRST ```csharp fence to find the recipe
    # body; a fenced block here hijacks the parse and discards the real
    # recipe (verified live on the v12 first render). Indented code reads
    # fine for Mentor and is invisible to the batcher.
    lines.append(
        "STEP 3 — Run ONE applyModelApiCode call containing EXACTLY these lines "
        "(this materializes the staged imports — addReferenceToElements alone "
        "returns null without this step):"
    )
    lines.append("")
    lines.append("    eSpace => {")
    for ref in refs:
        gk = compute_global_key(ref.producer_key, ref.element_key)
        lines.append(
            f'        eSpace.AddDependency(Services.ModelServices.ParseGlobalKey("{gk}"));'
            f"  // {ref.library}::{ref.block_name}"
        )
    lines.append('        Console.WriteLine("AddDependency batch complete");')
    lines.append("    }")
    lines.append("")
    # ── Step 4: verify via app_refs ──
    lines.append(
        "STEP 4 — Verify each producer landed by calling `app_refs` on this app. "
        "The response's `references[]` array MUST contain each of these producer "
        f"names: {', '.join(sorted(producers.keys()))}. If any are missing, "
        "repeat Step 3 for the missing producers."
    )
    lines.append("")
    lines.append(
        "STEP 5 — After verification passes, call `applyModelApiCode` with the "
        "C# code below."
    )
    lines.append("")
    return "\n".join(lines)
