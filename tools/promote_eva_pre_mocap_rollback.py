#!/usr/bin/env python3
"""Extract and promote the user-selected pre-mocap gameplay animations."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
from pathlib import Path

from make_tiger_unit01_pack import write_animation_catalogue


SOURCE_COMMIT = "a910890b2d16741e72843cfa534a74def6113078"
ROLLBACK_ANIMATIONS = {
    f"animation.eva_unit01.{suffix}"
    for suffix in (
        "melee", "melee_left", "smash",
        "crouch_melee", "crouch_melee_left", "crouch_smash",
        "prone_melee", "prone_melee_left", "prone_smash",
        "knife_ready", "knife", "knife_left", "knife_heavy",
        "crouch_knife", "crouch_knife_heavy",
        "prone_knife", "prone_knife_heavy", "prone_knife_ready",
        "crouch", "crouch_walk", "prone", "crawl",
        "prone_aim", "prone_rifle_aim",
        "prone_cannon_fire", "prone_rifle_fire",
        "visual_crouch_walk", "visual_crawl",
        "visual_knife_ready", "visual_knife_windup",
        "visual_knife_contact", "visual_knife_recovery",
        "visual_knife_heavy_contact", "visual_crouch_knife_contact",
        "visual_prone_knife_contact", "visual_crouch_rifle_contact",
        "visual_prone_rifle",
    )
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch", required=True, type=Path)
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("--write-patch", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent
    if args.write_patch:
        relative = Path(
            "src/main/resources/assets/projectseele/animations/"
            "eva_unit01.animation.json")
        text = subprocess.check_output(
            ["git", "show", f"{SOURCE_COMMIT}:{relative.as_posix()}"],
            cwd=repo, text=True, encoding="utf-8",
        )
        source = json.loads(text)
        payload = {
            "schema": 1,
            "source_commit": SOURCE_COMMIT,
            "status": "user_requested_pre_real_human_motion_rollback",
            "replace_animations": {
                name: source["animations"][name]
                for name in sorted(ROLLBACK_ANIMATIONS)
            },
        }
        args.patch.write_text(json.dumps(
            payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    patch = json.loads(args.patch.read_text(encoding="utf-8"))
    if (patch.get("source_commit") != SOURCE_COMMIT
            or set(patch.get("replace_animations", {}))
            != ROLLBACK_ANIMATIONS):
        raise SystemExit("rollback patch provenance or animation scope drifted")
    for relative in args.target:
        path = repo / relative
        catalogue = json.loads(path.read_text(encoding="utf-8"))
        for name, replacement in patch["replace_animations"].items():
            catalogue["animations"][name] = copy.deepcopy(replacement)
        write_animation_catalogue(path, catalogue)
    print(f"pre-mocap rollback: animations={len(ROLLBACK_ANIMATIONS)} "
          f"targets={len(args.target)}")


if __name__ == "__main__":
    main()
