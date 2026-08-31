#!/usr/bin/env python3
"""Build the bounded Phase-F landing candidate from the frozen baseline."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
ANIMATION = REPO / (
    "src/main/resources/assets/projectseele/animations/"
    "eva_unit01.animation.json")
BASELINE = "a910890b2d16741e72843cfa534a74def6113078"
RESOURCE_PATH = (
    "src/main/resources/assets/projectseele/animations/"
    "eva_unit01.animation.json")
LAND = "animation.eva_unit01.land"
KEEP_BONES = {
    "root", "torso_upper",
    "leg_l", "shin_l", "foot_l",
    "leg_r", "shin_r", "foot_r",
}
CHANNEL_FACTORS = {
    ("root", "position"): 0.55,
    ("torso_upper", "rotation"): 0.70,
    ("leg_l", "rotation"): 0.65,
    ("shin_l", "rotation"): 0.65,
    ("foot_l", "rotation"): 0.65,
    ("leg_r", "rotation"): 0.65,
    ("shin_r", "rotation"): 0.65,
    ("foot_r", "rotation"): 0.65,
}


def baseline_animation() -> dict:
    text = subprocess.check_output(
        ["git", "show", f"{BASELINE}:{RESOURCE_PATH}"],
        cwd=REPO, text=True, encoding="utf-8")
    return json.loads(text)


def damp(keys: dict, factor: float) -> dict:
    ordered = sorted(keys.items(), key=lambda item: float(item[0]))
    first_time = float(ordered[0][0])
    last_time = float(ordered[-1][0])
    first = ordered[0][1]
    last = ordered[-1][1]
    duration = max(1.0e-9, last_time - first_time)
    result = {}
    for key, value in ordered:
        progress = (float(key) - first_time) / duration
        baseline = [first[index] + progress * (last[index] - first[index])
                    for index in range(3)]
        result[key] = [round(baseline[index]
                             + factor * (value[index] - baseline[index]), 5)
                       for index in range(3)]
    return result


def main() -> None:
    source = baseline_animation()
    landing = source["animations"][LAND]
    source_bone_count = len(landing["bones"])
    bones = {}
    for name, bone in landing["bones"].items():
        if name not in KEEP_BONES:
            continue
        output = {}
        for channel, values in bone.items():
            factor = CHANNEL_FACTORS.get((name, channel), 1.0)
            output[channel] = damp(values, factor)
        bones[name] = output
    landing["bones"] = bones
    current = json.loads(ANIMATION.read_text(encoding="utf-8"))
    current["animations"][LAND] = landing
    ANIMATION.write_text(json.dumps(current, ensure_ascii=False, indent=2)
                         + "\n", encoding="utf-8")
    print(json.dumps({
        "animation": LAND,
        "baseline": BASELINE,
        "keptBones": sorted(bones),
        "removedBoneCount": source_bone_count - len(bones),
        "factors": {f"{bone}.{channel}": factor
                    for (bone, channel), factor
                    in CHANNEL_FACTORS.items()},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
