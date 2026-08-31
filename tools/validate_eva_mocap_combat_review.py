#!/usr/bin/env python3
"""Fail-closed static validator for the isolated Phase-G combat review DB."""

from __future__ import annotations

import hashlib
import json
import math
import py_compile
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
RESOURCE = REPO / (
    "src/main/resources/assets/projectseele/motion/"
    "eva_mocap_combat_review_v1.json")
MANIFEST = REPO / "tools/eva_mocap_combat_review_manifest.json"
LOCKS = REPO / (
    "src/main/resources/assets/projectseele/eva/"
    "eva_approved_actions.json")
SOURCE_HASHES = {
    "external-assets/incoming/mocap/cmu/subject144/bvh/144_13.bvh":
        "0cc6d4bd771970fa1a07d33b8bf5e42f12e72e4ee9bd61afecd53ac09d07cbe3",
    "external-assets/incoming/mocap/cmu/subject144/bvh/144_20.bvh":
        "d8e4025891f8ffc94ff53839525b0e71cfacd2cbec30a181bd738ec8220cbfce",
    "external-assets/incoming/mocap/cmu/subject02/bvh/02_08.bvh":
        "9eb38f57c2d4aedf00da5a1700f134423ad5f3ee407e3ae1bdb00060569943d8",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError("EVA Phase-G mocap review invalid: " + message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quaternion_step(first, second) -> float:
    first_norm = math.sqrt(sum(float(value) ** 2 for value in first))
    second_norm = math.sqrt(sum(float(value) ** 2 for value in second))
    dot = abs(sum(float(a) * float(b) for a, b in zip(first, second))
              / (first_norm * second_norm))
    return math.degrees(2.0 * math.acos(min(1.0, max(-1.0, dot))))


def main() -> None:
    document = json.loads(RESOURCE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(document["schema"] == 2 and document["preview_only"],
            "resource is not explicitly preview-only")
    require(not document["live_gameplay_replacement"],
            "candidate falsely declares a live replacement")
    require(document["sample_rate"] == 60.0,
            "candidate sample rate differs")
    require(len(document["bones"]) == 50
            and len(set(document["bones"])) == 50,
            "candidate must contain exactly 50 unique controls")
    require(len([name for name in document["bones"]
                 if name.startswith("finger_")]) == 26,
            "candidate visible grip must contain 26 controls")
    expected = {
        "mocap_unarmed_left": (92, "cmu_144_13_1044_1173"),
        "mocap_unarmed_right": (92, "cmu_144_20_504_633"),
        "mocap_knife_light": (84, "cmu_02_08_strike_01"),
        "mocap_knife_heavy": (86, "cmu_02_08_strike_05"),
    }
    require(set(document["clips"]) == set(expected),
            "review clip catalogue differs")
    lower = {
        "root", "torso_lower", "leg_l", "shin_l", "ankle_l", "foot_l",
        "leg_r", "shin_r", "ankle_r", "foot_r",
    }
    indices = {name: index for index, name in enumerate(document["bones"])}
    lower_reference = None
    maximum_step = 0.0
    for name, (frame_count, source_id) in expected.items():
        clip = document["clips"][name]
        frames = clip["frames"]
        require(len(frames) == frame_count
                and clip["source_id"] == source_id,
                f"{name} provenance or frame count differs")
        require(clip["role"] ==
                "isolated_constrained_human_mocap_review_only",
                f"{name} role is not isolated review")
        require(all(frame["root_m"] == [0.0, 0.0, 0.0]
                    and frame["foot_contact"] == [True, True]
                    for frame in frames),
                f"{name} violates locked support/root authority")
        for frame in frames:
            require(len(frame["rotation_wxyz"]) == 50,
                    f"{name} rotation width differs")
            for value in frame["rotation_wxyz"]:
                norm = math.sqrt(sum(float(item) ** 2 for item in value))
                require(abs(norm - 1.0) < 2.0e-5,
                        f"{name} has non-unit quaternion")
        for frame_index in range(1, len(frames)):
            for first, second in zip(
                    frames[frame_index - 1]["rotation_wxyz"],
                    frames[frame_index]["rotation_wxyz"]):
                maximum_step = max(
                    maximum_step, quaternion_step(first, second))
        require(max(quaternion_step(first, last) for first, last in zip(
            frames[0]["rotation_wxyz"],
            frames[-1]["rotation_wxyz"])) < 0.001,
            f"{name} does not return to the exact ready pose")
        support = {
            bone: frames[0]["rotation_wxyz"][indices[bone]]
            for bone in lower
        }
        require(all(max(abs(float(current) - float(reference))
                        for current, reference in zip(
                            frame["rotation_wxyz"][indices[bone]], value))
                    <= 2.0e-7
                    for frame in frames
                    for bone, value in support.items()),
                f"{name} lower-body support is not locked")
        if lower_reference is None:
            lower_reference = support
        else:
            require(support == lower_reference,
                    f"{name} does not share the approved support pose")
        for bone in document["bones"]:
            if not bone.startswith("finger_"):
                continue
            values = [frame["rotation_wxyz"][indices[bone]]
                      for frame in frames]
            require(all(max(abs(float(current) - float(reference))
                            for current, reference in zip(
                                value, values[0])) <= 2.0e-7
                        for value in values),
                    f"{name} writes untracked dynamic finger motion")
    require(maximum_step <= 20.0,
            f"maximum rotation step {maximum_step:.6f} exceeds 20 degrees")

    require(manifest["constraints"]["supportMode"] ==
            "LOCKED_READY_LOWER_BODY",
            "manifest support mode differs")
    locks = json.loads(LOCKS.read_text(encoding="utf-8"))["actions"]
    require({name for name, value in locks.items()
             if value["status"] == "VISUALLY_APPROVED"} == {
                 "idle", "walk", "run", "jump_landing",
             }, "Phase-F human approval set differs")
    require(locks["unarmed_attack"]["humanReviewRequired"]
            and locks["progressive_knife"]["humanReviewRequired"],
            "review candidates escaped their live approval lock")
    java = "\n".join(path.read_text(encoding="utf-8")
                     for path in (REPO / "src/main/java").rglob("*.java"))
    require("eva_mocap_combat_review_v1" not in java
            and not any(name in java for name in expected),
            "isolated candidate is referenced by runtime Java")
    for relative, expected_hash in SOURCE_HASHES.items():
        path = REPO / relative
        if path.is_file():
            require(digest(path) == expected_hash,
                    f"raw source hash differs: {relative}")
    for script in (
            "tools/export_eva_anatomical_action_candidate.py",
            "tools/build_eva_mocap_combat_review.py",
            "tools/build_eva_mocap_combat_review_package.py",
            "tools/render_eva_motion_lab_review.py"):
        py_compile.compile(str(REPO / script), doraise=True)
    print("EVA Phase-G mocap combat review passed: clips=4 bones=50 "
          f"maximumStep={maximum_step:.6f} support=LOCKED_READY_LOWER_BODY "
          "liveGameplayChanged=false automaticVisualApproval=false")


if __name__ == "__main__":
    main()
