#!/usr/bin/env python3
"""Promote only the animation keys changed by direct gameplay review."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from make_tiger_unit01_pack import _json_value_span


REVIEW_ANIMATIONS = {
    f"animation.eva_unit01.{suffix}"
    for suffix in (
        "aim", "rifle_aim", "n2_ready",
        "knife_ready", "knife", "knife_heavy",
        "crouch_knife", "crouch_knife_heavy",
        "prone_knife", "prone_knife_heavy", "prone_knife_ready",
        "visual_knife_ready", "visual_knife_windup",
        "visual_knife_contact", "visual_knife_recovery",
        "visual_knife_heavy_contact", "visual_crouch_knife_contact",
        "visual_rifle", "visual_rifle_walk_contact",
        "visual_crouch_rifle_contact",
    )
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", action="append", required=True)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    repo = Path(__file__).resolve().parent.parent
    for relative in args.target:
        text = subprocess.check_output(
            ["git", "show", f"HEAD:{Path(relative).as_posix()}"],
            cwd=repo, text=True, encoding="utf-8",
        )
        baseline = json.loads(text)
        unexpected = sorted(
            name for name in source["animations"]
            if source["animations"][name] != baseline["animations"][name]
            and name not in REVIEW_ANIMATIONS
        )
        if unexpected:
            raise SystemExit(
                "candidate changes animations outside review scope: "
                + ", ".join(unexpected))
        replacements = []
        for name in REVIEW_ANIMATIONS:
            start, end = _json_value_span(text, name)
            value = json.dumps(
                source["animations"][name], ensure_ascii=False, indent=2)
            lines = value.splitlines()
            indented = lines[0] + "\n" + "\n".join(
                "    " + line for line in lines[1:])
            replacements.append((start, end, indented))
        for start, end, value in sorted(replacements, reverse=True):
            text = text[:start] + value + text[end:]
        (repo / relative).write_text(text, encoding="utf-8", newline="")
    print(f"promoted {len(REVIEW_ANIMATIONS)} review animations "
          f"to {len(args.target)} catalogues")


if __name__ == "__main__":
    main()
