#!/usr/bin/env python3
"""Validate a closed Phase-A capture of final Gecko render matrices."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CONTRACT_DIR = REPO / "src/main/resources/assets/projectseele/eva"
RIG = CONTRACT_DIR / "eva_rig_schema.json"
AUTHORITY = CONTRACT_DIR / "eva_pose_authority_contract.json"
ACTIONS = CONTRACT_DIR / "eva_approved_actions.json"
CAPTURE_DIR = REPO / "run/pose-captures"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("EVA pose capture invalid: " + message)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite_vector(value: object, length: int) -> bool:
    return (isinstance(value, list) and len(value) == length
            and all(isinstance(item, (int, float))
                    and math.isfinite(item) for item in value))


def latest_capture() -> Path:
    candidates = list(CAPTURE_DIR.glob("*.jsonl"))
    require(bool(candidates), f"no JSONL capture exists under {CAPTURE_DIR}")
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "capture", nargs="?", type=Path,
        help="capture JSONL; defaults to the newest run/pose-captures file",
    )
    return parser.parse_args()


def validate_ranges(ranges: object, frame_count: int,
                    label: str) -> None:
    require(isinstance(ranges, list) and ranges,
            f"{label} has no timeline ranges")
    expected_start = 0
    for index, item in enumerate(ranges):
        require(isinstance(item, dict),
                f"{label} range {index} is not an object")
        start = item.get("startFrame")
        end = item.get("endFrame")
        require(start == expected_start,
                f"{label} timeline has a gap before frame {expected_start}")
        require(isinstance(end, int) and end >= start,
                f"{label} range {index} has an invalid end")
        require(isinstance(item.get("value"), str) and item["value"],
                f"{label} range {index} has no value")
        expected_start = end + 1
    require(expected_start == frame_count,
            f"{label} timeline ends at frame {expected_start - 1}, "
            f"expected {frame_count - 1}")


def main() -> None:
    args = parse_args()
    capture = (args.capture if args.capture is not None
               else latest_capture()).resolve()
    require(capture.is_file(), f"capture does not exist: {capture}")
    try:
        records = [json.loads(line) for line in
                   capture.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
    except (OSError, json.JSONDecodeError) as exception:
        raise SystemExit(
            f"EVA pose capture invalid: cannot parse {capture}: {exception}"
        ) from exception
    require(len(records) >= 3, "capture is not closed with header/frame/footer")
    header, *middle, footer = records
    require(header.get("type") == "header", "first record is not a header")
    require(footer.get("type") == "footer", "last record is not a footer")
    require(all(record.get("type") == "frame" for record in middle),
            "capture contains a non-frame body record")
    require(header.get("schema") == 1, "unsupported capture schema")
    require(header.get("captureContract") ==
            "FINAL_POST_CONTROLLER_GECKO_MATRICES",
            "capture is not from the final Gecko render path")
    require(header.get("poseGraphMode") == "OBSERVE_ONLY_NO_BONE_WRITES",
            "Phase-A capture used an enforcing pose graph")
    require(header.get("automaticVisualApproval") is False,
            "capture falsely permits automatic visual approval")
    require(header.get("resultVocabulary") ==
            ["FAIL", "ELIGIBLE_FOR_HUMAN_REVIEW"],
            "capture result vocabulary drifted")

    rig = read_json(RIG)
    authority = read_json(AUTHORITY)
    actions = read_json(ACTIONS)
    bones = [bone["name"] for bone in rig["bones"]]
    bone_set = set(bones)
    require(header.get("rigVersion") == rig["rigVersion"],
            "capture rig version differs from live contract")
    require(header.get("poseGraphVersion") ==
            authority["poseGraphVersion"],
            "capture PoseGraph version differs from live contract")
    for field, path in (
            ("rigContractSha256", RIG),
            ("authorityContractSha256", AUTHORITY),
            ("approvedActionsSha256", ACTIONS)):
        require(header.get(field) == raw_sha256(path),
                f"{field} differs from live resource")
    require(actions["rigVersion"] == rig["rigVersion"],
            "live action and rig contracts disagree")

    frame_count = len(middle)
    require(frame_count > 0, "capture contains no rendered frame")
    require(footer.get("frames") == frame_count,
            "footer frame count differs from JSONL body")
    require(isinstance(header.get("maxFrames"), int)
            and frame_count <= header["maxFrames"],
            "capture exceeds its declared frame limit")
    for expected_index, frame in enumerate(middle):
        require(frame.get("frame") == expected_index,
                f"frame index {frame.get('frame')} is not {expected_index}")
        entity = frame.get("entity", {})
        pose = frame.get("poseGraph", {})
        require(entity.get("motionPreview") == 0
                and entity.get("visualPose") == 0,
                f"frame {expected_index} used preview/demo authority")
        require(pose.get("eligibleForHumanReview") is True,
                f"frame {expected_index} is not eligible for human review")
        owners = pose.get("owners")
        require(isinstance(owners, dict) and set(owners) == bone_set,
                f"frame {expected_index} owner map differs from canonical rig")
        require(isinstance(pose.get("ownerConflicts"), dict),
                f"frame {expected_index} has no owner-conflict map")
        missing = frame.get("missingCanonicalBones")
        require(missing == [],
                f"frame {expected_index} misses canonical bones: {missing}")
        captured = frame.get("bones")
        require(isinstance(captured, dict)
                and bone_set.issubset(captured),
                f"frame {expected_index} does not contain every canonical bone")
        for name in bones:
            bone = captured[name]
            require(bone.get("owner") == owners[name],
                    f"frame {expected_index} owner differs for {name}")
            for matrix_name in ("localMatrix", "modelMatrix", "worldMatrix"):
                require(finite_vector(bone.get(matrix_name), 16),
                        f"frame {expected_index} {name}.{matrix_name} "
                        "is not a finite 4x4 matrix")
            for vector_name in ("finalPosition", "finalRotationRadians",
                                "finalScale"):
                require(finite_vector(bone.get(vector_name), 3),
                        f"frame {expected_index} {name}.{vector_name} "
                        "is not a finite vec3")
        resources = frame.get("resources", {})
        require(resources.get("valid") is True,
                f"frame {expected_index} visual fingerprint is invalid")
        require(finite_vector(frame.get("camera", {}).get("position"), 3),
                f"frame {expected_index} camera position is invalid")

    owners_path = capture.with_suffix(".owners.json")
    require(owners_path.is_file(), "owner timeline sidecar is missing")
    timeline = read_json(owners_path)
    require(timeline.get("schema") == 1, "unsupported owner timeline schema")
    require(timeline.get("frames") == frame_count,
            "owner timeline frame count differs")
    bone_timeline = timeline.get("boneOwnerTimeline")
    require(isinstance(bone_timeline, dict)
            and set(bone_timeline) == bone_set,
            "owner timeline differs from canonical rig")
    for name in bones:
        validate_ranges(bone_timeline[name], frame_count,
                        f"owner timeline for {name}")
    validate_ranges(timeline.get("actionTimeline"), frame_count,
                    "action timeline")

    print("EVA final-pose capture passed: "
          f"file={capture.name} frames={frame_count} bones={len(bones)} "
          "missing=0 matrices=local/model/world result=ELIGIBLE_FOR_HUMAN_REVIEW")


if __name__ == "__main__":
    main()
