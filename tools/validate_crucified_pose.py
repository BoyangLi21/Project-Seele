#!/usr/bin/env python3
"""Validate Unit-01's Tree-of-Life crucifix pose against the real SmOd rig.

This is deliberately a skeleton-space contract, not a gameplay hitbox check.
It samples the canonical Gecko animation, applies it to the generated SmOd
geometry hierarchy and verifies the cross silhouette at every authored arm
keyframe.  The ordinary EVA animations are never involved.
"""

import argparse
import json
from pathlib import Path

import render_unit01_rig_preview as rig


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSETS = ROOT / "run/resourcepacks/eva_real_model/assets/projectseele"
DEFAULT_ANIMATION = (
    ROOT / "src/main/resources/assets/projectseele/animations/eva_unit01.animation.json"
)
DEFAULT_OUTPUT = ROOT / "external-assets/work/crucified-validation/crucified_pose_report.json"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--animation-json", type=Path, default=DEFAULT_ANIMATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def authored_times(animation_json):
    data = json.loads(animation_json.read_text(encoding="utf-8"))
    animation = data["animations"]["animation.eva_unit01.crucified"]
    times = {0.0}
    for name in ("arm_l", "arm_r"):
        channel = animation["bones"][name]["rotation"]
        if isinstance(channel, dict):
            times.update(float(value) for value in channel)
    return sorted(times)


def world_joint(name, pivots, matrices):
    return rig.transform(matrices[name], pivots[name])


def sample_pose(mesh, geo, animation_json, time):
    pivots, parents, base_rotations = rig.load_skeleton(mesh, geo)
    _, sampled_time, rotations, positions = rig.select_animation(
        animation_json, "crucified", time
    )
    matrices = {}
    required = set(mesh["parts"]) | {
        "arm_l", "arm_r", "forearm_l", "forearm_r", "hand_l", "hand_r",
        "leg_l", "leg_r", "shin_l", "shin_r", "foot_l", "foot_r",
    }
    for bone in required:
        rig.bone_matrix(
            bone, pivots, parents, rotations, positions, base_rotations, matrices
        )
    joints = {name: world_joint(name, pivots, matrices) for name in required}

    shoulder_y = (joints["arm_l"][1] + joints["arm_r"][1]) / 2.0
    hand_y = (joints["hand_l"][1] + joints["hand_r"][1]) / 2.0
    left_elbow_error = abs(joints["forearm_l"][1] - shoulder_y)
    right_elbow_error = abs(joints["forearm_r"][1] - shoulder_y)
    hand_plane_error = max(
        abs(joints["hand_l"][1] - shoulder_y),
        abs(joints["hand_r"][1] - shoulder_y),
    )
    hand_span = abs(joints["hand_l"][0] - joints["hand_r"][0])
    hip_gap = abs(joints["leg_l"][0] - joints["leg_r"][0])
    ankle_gap = abs(joints["foot_l"][0] - joints["foot_r"][0])
    ankle_to_hip_ratio = ankle_gap / hip_gap
    foot_level_error = abs(joints["foot_l"][1] - joints["foot_r"][1])

    checks = {
        "hands_share_shoulder_plane": hand_plane_error <= 1.0,
        "elbows_near_arm_plane": max(left_elbow_error, right_elbow_error) <= 2.0,
        "full_cross_arm_span": hand_span >= 155.0,
        "ankles_close_together": ankle_gap <= 6.0,
        "legs_converge_without_crossing": (
            joints["foot_l"][0] > 0.0
            and joints["foot_r"][0] < 0.0
            and ankle_to_hip_ratio <= 0.30
        ),
        "feet_are_level": foot_level_error <= 0.1,
        "left_right_mirror_height": (
            abs(joints["hand_l"][1] - joints["hand_r"][1]) <= 0.1
            and foot_level_error <= 0.1
        ),
    }
    return {
        "requested_time": time,
        "sampled_time": sampled_time,
        "metrics_model_pixels": {
            "shoulder_plane_y": round(shoulder_y, 4),
            "hand_plane_y": round(hand_y, 4),
            "hand_plane_error": round(hand_plane_error, 4),
            "left_elbow_plane_error": round(left_elbow_error, 4),
            "right_elbow_plane_error": round(right_elbow_error, 4),
            "hand_span": round(hand_span, 4),
            "hip_gap": round(hip_gap, 4),
            "ankle_gap": round(ankle_gap, 4),
            "ankle_to_hip_ratio": round(ankle_to_hip_ratio, 4),
            "foot_level_error": round(foot_level_error, 4),
        },
        "joint_world": {
            name: [round(value, 4) for value in joints[name]]
            for name in (
                "arm_l", "forearm_l", "hand_l",
                "arm_r", "forearm_r", "hand_r",
                "leg_l", "shin_l", "foot_l",
                "leg_r", "shin_r", "foot_r",
            )
        },
        "checks": checks,
        "passed": all(checks.values()),
    }


def main():
    args = parse_args()
    mesh_path = args.assets / "mesh/eva_unit01.mesh.json"
    geo_path = args.assets / "geo/eva_unit01.geo.json"
    missing = [path for path in (mesh_path, geo_path, args.animation_json) if not path.is_file()]
    if missing:
        raise SystemExit("missing crucified-pose input: " + ", ".join(map(str, missing)))

    mesh = json.loads(mesh_path.read_text(encoding="utf-8"))
    samples = [
        sample_pose(mesh, geo_path, args.animation_json, time)
        for time in authored_times(args.animation_json)
    ]
    report = {
        "contract": "canonical crucified animation applied to the real SmOd Unit-01 rig",
        "inputs": {
            "mesh": str(mesh_path),
            "geo": str(geo_path),
            "animation": str(args.animation_json),
        },
        "thresholds_model_pixels": {
            "maximum_hand_plane_error": 1.0,
            "maximum_elbow_plane_error": 2.0,
            "minimum_hand_span": 155.0,
            "maximum_ankle_gap": 6.0,
            "maximum_ankle_to_hip_ratio": 0.30,
        },
        "samples": samples,
        "passed": all(sample["passed"] for sample in samples),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    status = "PASS" if report["passed"] else "FAIL"
    print(f"crucified pose: {status} ({len(samples)} authored samples)")
    print(f"report: {args.output}")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
