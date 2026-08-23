#!/usr/bin/env python3
"""Apply the deterministic reviewed EVA animation patch chain to JSON files."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from eva_animation_geometry_repairs import apply_reviewed_animation_repairs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", action="append", required=True, type=Path)
    parser.add_argument("--sync-variant", action="append", default=[], type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    repaired = apply_reviewed_animation_repairs(data, strict_source=False)
    payload = json.dumps(repaired, ensure_ascii=False, indent=2) + "\n"
    for output in args.output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    for variant_path in args.sync_variant:
        variant = json.loads(variant_path.read_text(encoding="utf-8"))
        target = variant.setdefault("animations", {})
        for name, animation in repaired["animations"].items():
            target[name] = copy.deepcopy(animation)
        variant_path.write_text(
            json.dumps(variant, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"Applied EVA animation patch chain to {len(args.output)} outputs; "
        f"synced {len(args.sync_variant)} variants"
    )


if __name__ == "__main__":
    main()
