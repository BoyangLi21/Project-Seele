#!/usr/bin/env python3
"""Catalog third-party humanoid motion clips without shipping their assets.

The private development instance may inspect reference mods, but Project SEELE
keeps GeckoLib as the only runtime skeleton authority.  This tool records clip
timing and bone coverage only; it never copies animation matrices into tracked
resources and never adds the reference mod to a release pack.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path


TARGETS = {
    "fist_auto1": "melee",
    "fist_auto2": "melee_left",
    "fist_auto3": "smash",
    "dagger_auto1": "knife_left",
    "dagger_auto2": "knife",
    "dagger_auto3": "knife_heavy",
    "spear_twohand_auto1": "lance_thrust",
    "spear_twohand_auto2": "lance_thrust follow-through",
    "mob_spear_twohand1": "lance_ready/contact reference",
    "mob_spear_twohand2": "lance recovery reference",
    "mob_spear_twohand3": "lance heavy reference",
    "walk": "walk",
    "run": "run",
    "run_spear": "lance_carry locomotion",
    "jump": "jump",
    "bow_aim_lying": "prone_aim reference",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Catalog selected Epic Fight motion clips for offline retargeting"
    )
    parser.add_argument("jar", type=Path, help="Epic Fight reference JAR")
    parser.add_argument("output", type=Path, help="JSON catalog to write")
    return parser.parse_args()


def clip_name(path: str) -> str:
    return Path(path).stem


def summarize(path: str, payload: dict) -> dict:
    tracks = payload.get("animation", [])
    duration = 0.0
    keyframes = 0
    bones: list[str] = []
    for track in tracks:
        name = str(track.get("name", ""))
        if name:
            bones.append(name)
        times = track.get("time", [])
        if times:
            duration = max(duration, max(float(value) for value in times))
            keyframes += len(times)
    name = clip_name(path)
    return {
        "source_path": path,
        "source_clip": name,
        "seele_reference_target": TARGETS[name],
        "duration_seconds": round(duration, 4),
        "track_count": len(tracks),
        "keyframe_count": keyframes,
        "bones": sorted(set(bones)),
    }


def main() -> None:
    args = parse_args()
    if not args.jar.is_file():
        raise SystemExit(f"reference JAR not found: {args.jar}")

    selected: dict[str, str] = {}
    with zipfile.ZipFile(args.jar) as archive:
        for path in archive.namelist():
            if not re.fullmatch(
                r"assets/epicfight/animmodels/animations/biped/(?:[^/]+/)*[^/]+\.json",
                path,
            ):
                continue
            name = clip_name(path)
            if name not in TARGETS:
                continue
            # Epic Fight also ships combat/data sidecars with the same basename.
            # Prefer the actual transform clip over those metadata payloads.
            current = selected.get(name)
            if current is None or ("/data/" in current and "/data/" not in path):
                selected[name] = path

        missing = sorted(set(TARGETS) - set(selected))
        clips = [
            summarize(path, json.loads(archive.read(path)))
            for _, path in sorted(selected.items())
        ]

    document = {
        "schema": 1,
        "policy": {
            "runtime_authority": "GeckoLib / Project SEELE only",
            "reference_assets_copied": False,
            "reference_mod_shipped": False,
            "usage": "timing and biomechanics reference before manual retargeting",
        },
        "source": {
            "jar_name": args.jar.name,
            "jar_size": args.jar.stat().st_size,
        },
        "missing_requested_clips": missing,
        "clips": clips,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"cataloged {len(clips)} clips; missing={len(missing)}; output={args.output}"
    )


if __name__ == "__main__":
    main()
