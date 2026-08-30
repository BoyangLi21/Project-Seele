#!/usr/bin/env python3
"""Combine compatible single-clip EVA motion-review databases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--runtime-visual", action="store_true")
    args = parser.parse_args()
    documents = [json.loads(path.read_text(encoding="utf-8"))
                 for path in args.input]
    first = documents[0]
    clips = {}
    sources = []
    for path, document in zip(args.input, documents):
        for key in ("schema", "coordinate_system", "quaternion_order",
                    "bones", "authority"):
            if document.get(key) != first.get(key):
                raise RuntimeError(f"incompatible {key} in {path}")
        overlap = set(clips) & set(document["clips"])
        if overlap:
            raise RuntimeError(f"duplicate clips: {sorted(overlap)}")
        clips.update(document["clips"])
        for source in document.get("sources", []):
            if source not in sources:
                sources.append(source)
    output = dict(first)
    output["clips"] = clips
    output["sources"] = sources
    if args.runtime_visual:
        output["preview_only"] = False
        output["authority"] = (
            "client_visual_mocap_server_combat_remains_authoritative"
        )
        for clip in clips.values():
            clip["role"] = "ordinary_attack_runtime_visual"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        output, ensure_ascii=False, separators=(",", ":")
    ) + "\n", encoding="utf-8")
    report = {
        "schema": 1,
        "inputs": [str(path.resolve()) for path in args.input],
        "output": str(args.output.resolve()),
        "clips": sorted(clips),
        "bones": len(first["bones"]),
        "frames": sum(len(clip["frames"]) for clip in clips.values()),
        "status": (
            "runtime_visual_database_server_combat_remains_authoritative"
            if args.runtime_visual
            else "combined_review_database_not_gameplay_authority"
        ),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
