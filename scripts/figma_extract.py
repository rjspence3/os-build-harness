#!/usr/bin/env python3
"""Figma → structured design extractor (Tier 2 of the "MCP replicates a Figma design" test).

Given a Figma file URL/key + a personal access token, pulls the node tree and PNG renders of
the top-level frames (= screens), and emits:
  - figma_design.json  — per-frame structured node list (type, name, bbox, fills→hex, text +
    font style, cornerRadius) + a global tokens summary (palette + fonts). The MCP-driver
    authors ODC from THIS (exact structure), not just from a screenshot.
  - <frame-slug>.png    — the rendered frame = the pixel target for scripts/pixel_diff.py.

No external deps (urllib). The token is NEVER printed/committed; read from --token, env
FIGMA_TOKEN, or a token file (default ~/.figma_token), so it stays out of chat + git.

Usage:
  FIGMA_TOKEN=figd_xxx python scripts/figma_extract.py <figma-url-or-key> \
      --out builds/quote-forge/spec/design/figma
  # or:  --token-file ~/.figma_token   (a gitignored file holding just the PAT)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

API = "https://api.figma.com/v1"


def file_key(url_or_key: str) -> str:
    m = re.search(r"figma\.com/(?:file|design)/([A-Za-z0-9]+)", url_or_key)
    return m.group(1) if m else url_or_key.strip()


def _get(url: str, token: str) -> bytes:
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def _hex(color: dict) -> str:
    return "#%02x%02x%02x" % tuple(round(color.get(c, 0) * 255) for c in "rgb")


def _solid_fills(node: dict) -> list[str]:
    out = []
    for f in node.get("fills", []) or []:
        if f.get("type") == "SOLID" and f.get("visible", True):
            out.append(_hex(f["color"]))
    return out


def flatten(node: dict, acc: list, palette: dict, fonts: dict) -> None:
    """Walk a frame subtree → a flat list of meaningful nodes + accumulate tokens."""
    t = node.get("type")
    bbox = node.get("absoluteBoundingBox") or {}
    fills = _solid_fills(node)
    for h in fills:
        palette[h] = palette.get(h, 0) + 1
    entry = {
        "type": t,
        "name": node.get("name"),
        "bbox": {k: round(bbox[k]) for k in ("x", "y", "width", "height") if k in bbox},
        "fills": fills,
    }
    if node.get("cornerRadius") is not None:
        entry["cornerRadius"] = node["cornerRadius"]
    if t == "TEXT":
        entry["text"] = node.get("characters", "")
        st = node.get("style", {}) or {}
        entry["font"] = {k: st.get(k) for k in ("fontFamily", "fontWeight", "fontSize", "textAlignHorizontal") if k in st}
        fam = st.get("fontFamily")
        if fam:
            fonts[fam] = fonts.get(fam, 0) + 1
    if t in ("TEXT", "RECTANGLE", "FRAME", "GROUP", "INSTANCE", "COMPONENT", "VECTOR", "ELLIPSE", "LINE"):
        acc.append(entry)
    for ch in node.get("children", []) or []:
        flatten(ch, acc, palette, fonts)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "frame").lower()).strip("-") or "frame"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url", help="Figma file URL or key")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--token", default=None)
    ap.add_argument("--token-file", type=Path, default=Path.home() / ".figma_token")
    ap.add_argument("--scale", default="2")
    args = ap.parse_args(argv)

    token = args.token or os.environ.get("FIGMA_TOKEN")
    if not token and args.token_file.exists():
        token = args.token_file.read_text(encoding="utf-8").strip()
    if not token:
        print("No Figma token. Set FIGMA_TOKEN, pass --token, or put the PAT in ~/.figma_token.",
              file=sys.stderr)
        return 2

    key = file_key(args.url)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"file key: {key}")

    doc = json.loads(_get(f"{API}/files/{key}", token))
    # top-level frames across all canvases
    frames = []
    for canvas in doc["document"].get("children", []):
        for n in canvas.get("children", []):
            if n.get("type") in ("FRAME", "COMPONENT") and n.get("absoluteBoundingBox"):
                frames.append(n)
    print(f"frames found: {len(frames)} -> {[f.get('name') for f in frames]}")

    palette: dict = {}
    fonts: dict = {}
    out_frames = []
    for fr in frames:
        nodes: list = []
        flatten(fr, nodes, palette, fonts)
        out_frames.append({"id": fr["id"], "name": fr.get("name"), "slug": slug(fr.get("name")),
                           "size": {k: round(fr["absoluteBoundingBox"][k]) for k in ("width", "height")},
                           "nodes": nodes})

    design = {
        "file_key": key, "name": doc.get("name"),
        "tokens": {
            "palette": sorted(palette, key=palette.get, reverse=True),
            "fonts": sorted(fonts, key=fonts.get, reverse=True),
        },
        "frames": out_frames,
    }
    (args.out / "figma_design.json").write_text(json.dumps(design, indent=2), encoding="utf-8")
    print(f"wrote figma_design.json ({len(out_frames)} frames, {len(palette)} colors, fonts={design['tokens']['fonts']})")

    # render each frame to PNG (the pixel targets)
    ids = ",".join(f["id"] for f in frames)
    imgs = json.loads(_get(f"{API}/images/{key}?ids={ids}&format=png&scale={args.scale}", token)).get("images", {})
    for fr in out_frames:
        url = imgs.get(fr["id"])
        if not url:
            print(f"  (no render for {fr['name']})"); continue
        png = urllib.request.urlopen(url, timeout=120).read()
        (args.out / f"{fr['slug']}.png").write_bytes(png)
        print(f"  {fr['slug']}.png ({len(png)//1024} KB)")
    print(f"\ndone → {args.out}/  (figma_design.json + frame PNGs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
