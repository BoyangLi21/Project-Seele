#!/usr/bin/env python3
"""Rank captured kick events by foot impact, support and non-spin evidence."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--events-per-source", type=int, default=8)
    return parser.parse_args()


def derivative(values: np.ndarray, fps: float) -> np.ndarray:
    output = np.zeros_like(values, dtype=np.float64)
    if len(values) > 1:
        output[0] = (values[1] - values[0]) * fps
        output[-1] = (values[-1] - values[-2]) * fps
    if len(values) > 2:
        output[1:-1] = (values[2:] - values[:-2]) * (fps * 0.5)
    return output


def yaw_from_left(left: np.ndarray) -> np.ndarray:
    planar = left[:, :2].copy()
    planar /= np.maximum(np.linalg.norm(planar, axis=1)[:, None], 1.0e-9)
    forward = np.column_stack((planar[:, 1], -planar[:, 0]))
    return np.unwrap(np.arctan2(forward[:, 1], forward[:, 0]))


def angle_degrees(first: np.ndarray, second: np.ndarray) -> float:
    denominator = float(np.linalg.norm(first) * np.linalg.norm(second))
    if denominator < 1.0e-9:
        return 0.0
    cosine = float(np.clip(np.dot(first, second) / denominator, -1.0, 1.0))
    return math.degrees(math.acos(cosine))


def audit(path: Path, events_per_source: int) -> dict:
    data = np.load(path)
    names = [str(value) for value in data["landmark_names"]]
    index = {name: offset for offset, name in enumerate(names)}
    positions = np.asarray(data["positions_H"], dtype=np.float64)
    contacts = np.asarray(data["foot_contact"], dtype=bool)
    frames = np.asarray(data["frames"], dtype=np.float64)
    fps = float(data["fps"][0])
    pelvis_yaw = np.unwrap(np.asarray(data["root_yaw_rad"], dtype=np.float64))
    shoulder_left = (
        positions[:, index["shoulder_l"]]
        - positions[:, index["shoulder_r"]]
    )
    thorax_yaw = yaw_from_left(shoulder_left)
    pelvis_yaw_speed = derivative(pelvis_yaw, fps)
    thorax_yaw_speed = derivative(thorax_yaw, fps)

    toes = {side: positions[:, index[f"toe_{side}"]] for side in ("l", "r")}
    ankles = {
        side: positions[:, index[f"ankle_{side}"]] for side in ("l", "r")
    }
    speeds = {
        side: np.linalg.norm(derivative(toes[side], fps), axis=1)
        for side in ("l", "r")
    }
    follow = max(2, int(round(fps * 0.16)))
    path_radius = max(2, int(round(fps * 0.12)))
    yaw_radius = max(3, int(round(fps * 0.55)))
    margin = max(follow + 2, yaw_radius)
    candidates = []
    for sample in range(margin, len(frames) - margin):
        for side_index, side in enumerate(("l", "r")):
            speed = float(speeds[side][sample])
            if speed < float(np.percentile(speeds[side], 68.0)):
                continue
            if speed < speeds[side][sample - 1] or speed < speeds[side][sample + 1]:
                continue
            other = "r" if side == "l" else "l"
            other_index = 1 - side_index
            post_min = float(np.min(speeds[side][sample + 1:sample + follow + 1]))
            braking = float(np.clip(1.0 - post_min / max(speed, 1.0e-9), 0.0, 1.0))
            support = bool(np.any(contacts[
                sample - 2:sample + 3, other_index
            ]))
            foot_height = float(toes[side][sample, 2]
                                - toes[other][sample, 2])
            knee = positions[sample, index[f"knee_{side}"]]
            hip = positions[sample, index[f"hip_{side}"]]
            ankle = ankles[side][sample]
            knee_extension = angle_degrees(hip - knee, ankle - knee)
            knee_extension = float(np.clip(knee_extension, 0.0, 180.0))
            left = sample - path_radius
            right = sample + path_radius
            path_delta = toes[side][right] - toes[side][left]
            horizontal_path = float(np.linalg.norm(path_delta[:2]))
            yaw_slice = pelvis_yaw[sample - yaw_radius:sample + yaw_radius + 1]
            yaw_range = math.degrees(float(np.max(yaw_slice) - np.min(yaw_slice)))
            angular_drive = (
                abs(float(pelvis_yaw_speed[sample]))
                + abs(float(thorax_yaw_speed[sample]))
            )
            spin_reject = yaw_range > 105.0
            low_foot_reject = foot_height < 0.08
            score = (
                speed
                * (0.45 + braking)
                * (0.65 + min(1.0, max(0.0, foot_height) / 0.45))
                * (0.65 + min(1.0, knee_extension / 150.0))
                * (1.0 if support else 0.42)
                * (1.0 if horizontal_path >= 0.08 else 0.55)
                * (0.22 if spin_reject else 1.0)
                * (0.35 if low_foot_reject else 1.0)
            )
            candidates.append({
                "score": score,
                "sample": sample,
                "sourceFrame": float(frames[sample]),
                "side": side,
                "footSpeedHPerSecond": speed,
                "postImpactSpeedDropFraction": braking,
                "supportPresent": support,
                "strikingFootHeightAboveSupportH": foot_height,
                "kneeExtensionDegrees": knee_extension,
                "horizontalPathH": horizontal_path,
                "pathForwardLeftUpH": path_delta.tolist(),
                "pelvisYawRangeDegrees": yaw_range,
                "combinedAngularDriveDegreesPerSecond": math.degrees(
                    angular_drive
                ),
                "styleRejects": [
                    reason for reason, rejected in (
                        ("pelvis_yaw_range_over_105_degrees", spin_reject),
                        ("striking_foot_below_0.08_body_height", low_foot_reject),
                        ("no_support_foot_at_impact", not support),
                    ) if rejected
                ],
            })

    separation = max(1, int(round(fps * 0.55)))
    selected = []
    for event in sorted(candidates, key=lambda item: item["score"], reverse=True):
        if any(abs(event["sample"] - kept["sample"]) < separation
               for kept in selected):
            continue
        selected.append(event)
        if len(selected) >= events_per_source:
            break
    for event in selected:
        event["score"] = round(float(event["score"]), 6)
        event["sourceFrame"] = round(float(event["sourceFrame"]), 5)
        event["seconds"] = round(float(event["sample"] / fps), 5)
        for key in (
            "footSpeedHPerSecond", "postImpactSpeedDropFraction",
            "strikingFootHeightAboveSupportH", "kneeExtensionDegrees",
            "horizontalPathH", "pelvisYawRangeDegrees",
            "combinedAngularDriveDegreesPerSecond",
        ):
            event[key] = round(float(event[key]), 6)
        event["pathForwardLeftUpH"] = [
            round(float(value), 6) for value in event["pathForwardLeftUpH"]
        ]
    selected.sort(key=lambda item: item["score"], reverse=True)
    return {
        "source": str(path.resolve()),
        "samples": len(frames),
        "fps": fps,
        "durationSeconds": round((len(frames) - 1) / fps, 5),
        "events": selected,
    }


def main() -> None:
    args = parse_args()
    sources = [audit(path.resolve(), args.events_per_source)
               for path in args.inputs]
    output = {
        "schema": 1,
        "authority": "captured_kick_landmark_source_screening",
        "result": "SOURCE_RANKING_ONLY_NOT_VISUALLY_APPROVED",
        "automaticVisualApproval": False,
        "criteria": [
            "striking-foot speed and braking",
            "other-foot support at impact",
            "foot elevation and knee extension",
            "horizontal strike path",
            "pelvis yaw spin rejection",
        ],
        "sources": sources,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "sources": len(sources),
        "best": [
            {"source": source["source"], "event": source["events"][0]}
            for source in sources if source["events"]
        ],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
