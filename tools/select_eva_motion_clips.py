#!/usr/bin/env python3
"""Create a compact review database from selected motion clip names."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--clip", action="append", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    document = json.loads(args.input.read_text(encoding="utf-8"))
    missing = sorted(set(args.clip) - set(document["clips"]))
    if missing:
        raise SystemExit("missing clips: " + ", ".join(missing))
    output = copy.deepcopy(document)
    output["clips"] = {
        name: copy.deepcopy(document["clips"][name]) for name in args.clip
    }
    output["review_selection"] = list(args.clip)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"EVA motion selection: clips={len(args.clip)} output={args.output}")


if __name__ == "__main__":
    main()
