#!/usr/bin/env python3
"""Merge isolated EVA combo databases into one human-selection resource."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    documents = [json.loads(path.read_text(encoding="utf-8"))
                 for path in args.inputs]
    first = documents[0]
    fields = ("coordinate_system", "quaternion_order", "sample_rate", "bones")
    for document in documents[1:]:
        if any(document[field] != first[field] for field in fields):
            raise RuntimeError("combo selection databases use different rigs")
    clips = {}
    contracts = {}
    sources = []
    for path, document in zip(args.inputs, documents):
        overlap = set(clips) & set(document["clips"])
        if overlap:
            raise RuntimeError("duplicate clips: " + ", ".join(sorted(overlap)))
        clips.update(document["clips"])
        contracts.update({name: document.get("combo_contract", {})
                          for name in document["clips"]})
        for source in document.get("sources", []):
            if source not in sources:
                sources.append(source)
    output = {
        "schema": 2,
        "coordinate_system": first["coordinate_system"],
        "quaternion_order": first["quaternion_order"],
        "sample_rate": first["sample_rate"],
        "preview_only": True,
        "live_gameplay_replacement": False,
        "human_review": {
            "status": "FOUR_GROUP_SELECTION_REQUIRES_HUMAN_REVIEW",
            "selected": None,
        },
        "authority": "four_native_combat_combo_human_selection_only",
        "root_authority": first["root_authority"],
        "sources": sources,
        "bones": first["bones"],
        "selection_contract": {
            "groups": list(clips),
            "chooseExactlyOneOrRejectAll": True,
            "liveGameplayChanged": False,
            "comboContracts": contracts,
        },
        "clips": clips,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    print(json.dumps({
        "clips": len(clips),
        "frames": {name: len(clip["frames"])
                   for name, clip in clips.items()},
        "output": str(args.output.resolve()),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
