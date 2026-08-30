#!/usr/bin/env python3
"""Promote screened lance channels without rewriting unrelated EVA motion."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


PATCH_ANIMATIONS = (
    "animation.eva_unit01.crouch_lance_thrust",
    "animation.eva_unit01.lance_carry",
    "animation.eva_unit01.lance_ready",
    "animation.eva_unit01.lance_thrust",
)
RESOURCE_ANIMATIONS = PATCH_ANIMATIONS + (
    "animation.eva_unit01.visual_crouch_lance_contact",
    "animation.eva_unit01.visual_lance_contact",
    "animation.eva_unit01.visual_lance_ready",
    "animation.eva_unit01.visual_lance_recovery",
    "animation.eva_unit01.visual_lance_windup",
)


def value_span(text: str, key: str) -> tuple[int, int]:
    marker = json.dumps(key) + ": "
    start = text.index(marker) + len(marker)
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1
    raise RuntimeError(f"unterminated object: {key}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch", required=True, type=Path)
    parser.add_argument("--candidate-patch", required=True, type=Path)
    parser.add_argument("--source-animation", type=Path)
    parser.add_argument("--animation", action="append", default=[])
    args = parser.parse_args()
    current = json.loads(args.patch.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate_patch.read_text(encoding="utf-8"))
    for name in PATCH_ANIMATIONS:
        current["replace_animations"][name] = \
            candidate["replace_animations"][name]
    candidate_sources = {
        name: value for name, value in candidate["sources"].items()
        if name.startswith("lance_thrust_v")
    }
    if len(candidate_sources) != 1:
        raise SystemExit(
            f"expected one versioned lance source, got {list(candidate_sources)}"
        )
    for name in list(current["sources"]):
        if name.startswith("lance_thrust_v"):
            del current["sources"][name]
    current["sources"].update(candidate_sources)
    args.patch.write_text(
        json.dumps(current, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if args.animation and args.source_animation is None:
        parser.error("--animation requires --source-animation")
    if not args.animation:
        print("promoted lance patch channels")
        return
    repo = Path(__file__).resolve().parent.parent
    source = json.loads(args.source_animation.read_text(encoding="utf-8"))
    for relative in args.animation:
        text = subprocess.check_output(
            ["git", "show", f"HEAD:{Path(relative).as_posix()}"],
            cwd=repo, text=True, encoding="utf-8",
        )
        replacements = []
        for name in RESOURCE_ANIMATIONS:
            start, end = value_span(text, name)
            value = json.dumps(
                source["animations"][name], ensure_ascii=False, indent=2
            )
            lines = value.splitlines()
            indented = lines[0] + "\n" + "\n".join(
                "    " + line for line in lines[1:]
            )
            replacements.append((start, end, indented))
        for start, end, value in sorted(replacements, reverse=True):
            text = text[:start] + value + text[end:]
        (repo / relative).write_text(text, encoding="utf-8", newline="")
    print(f"promoted lance resource channels to {len(args.animation)} catalogues")


if __name__ == "__main__":
    main()
