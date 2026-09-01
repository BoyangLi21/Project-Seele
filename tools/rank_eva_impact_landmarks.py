#!/usr/bin/env python3
"""Rank captured full-body strikes by EVA impact-chain evidence.

This is a source-screening gate, not visual approval.  It rewards a fast
dominant arm, pelvis/thorax angular drive, a planted support and a measurable
post-peak speed drop.  It does not add camera shake or alter the source pose.
"""

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
    lengths = np.linalg.norm(planar, axis=1)
    planar /= np.maximum(lengths[:, None], 1.0e-9)
    forward = np.column_stack((planar[:, 1], -planar[:, 0]))
    return np.unwrap(np.arctan2(forward[:, 1], forward[:, 0]))


def audit(path: Path) -> dict:
    data = np.load(path)
    names = [str(value) for value in data["landmark_names"]]
    index = {name: offset for offset, name in enumerate(names)}
    positions = np.asarray(data["positions_H"], dtype=np.float64)
    fps = float(data["fps"][0])
    contacts = np.asarray(data["foot_contact"], dtype=bool)
    frames = np.asarray(data["frames"], dtype=np.float64)

    wrists = {
        side: positions[:, index[f"wrist_{side}"]]
        for side in ("l", "r")
    }
    speeds = {
        side: np.linalg.norm(derivative(value, fps), axis=1)
        for side, value in wrists.items()
    }
    pelvis_yaw = np.unwrap(np.asarray(data["root_yaw_rad"], dtype=np.float64))
    shoulder_left = (
        positions[:, index["shoulder_l"]]
        - positions[:, index["shoulder_r"]]
    )
    thorax_yaw = yaw_from_left(shoulder_left)
    pelvis_yaw_speed = derivative(pelvis_yaw, fps)
    thorax_yaw_speed = derivative(thorax_yaw, fps)
    root_speed = np.linalg.norm(
        derivative(positions[:, index["pelvis"]], fps), axis=1)

    follow = max(2, int(round(fps * 0.18)))
    margin = max(follow + 1, int(round(fps * 0.12)))
    candidates = []
    for frame_index in range(margin, len(frames) - margin):
        for side in ("l", "r"):
            speed = float(speeds[side][frame_index])
            if speed < float(np.percentile(speeds[side], 65.0)):
                continue
            post_min = float(np.min(
                speeds[side][frame_index + 1:frame_index + follow + 1]
            ))
            braking = max(0.0, min(1.0, 1.0 - post_min / max(speed, 1.0e-9)))
            other = "r" if side == "l" else "l"
            dominance = speed / max(float(speeds[other][frame_index]), 1.0e-6)
            angular_drive = (
                abs(float(pelvis_yaw_speed[frame_index]))
                + abs(float(thorax_yaw_speed[frame_index]))
            )
            support = bool(np.any(contacts[
                max(0, frame_index - 2):frame_index + 3
            ]))
            score = (
                speed
                * (0.35 + braking)
                * (0.5 + min(1.0, angular_drive / math.radians(360.0)))
                * (1.0 if support else 0.72)
                * min(1.4, max(0.75, dominance))
            )
            candidates.append((score, frame_index, side, braking,
                               post_min, dominance, angular_drive, support))
    if not candidates:
        raise RuntimeError(f"no impact candidate in {path}")
    event_separation = max(1, int(round(fps * 0.28)))
    selected_events = []
    for candidate in sorted(candidates, reverse=True):
        if any(abs(candidate[1] - existing[1]) < event_separation
               for existing in selected_events):
            continue
        selected_events.append(candidate)
        if len(selected_events) >= 6:
            break
    selected_events.sort(key=lambda value: value[1])
    (raw_score, peak, side, braking, post_min, dominance,
     angular_drive, support) = max(candidates)
    other = "r" if side == "l" else "l"
    path_delta = wrists[side][min(len(frames) - 1, peak + follow)] \
        - wrists[side][max(0, peak - follow)]
    pelvis_yaw_range = math.degrees(float(
        np.max(pelvis_yaw) - np.min(pelvis_yaw)))
    excessive_turn = pelvis_yaw_range > 120.0
    score = raw_score * (0.35 if excessive_turn else 1.0)
    impact_events = [{
        "sample": int(event[1]),
        "sourceFrame": round(float(frames[event[1]]), 5),
        "seconds": round(float(event[1] / fps), 5),
        "primarySide": event[2],
        "rawImpactScore": round(float(event[0]), 6),
        "wristSpeedHPerSecond": round(float(
            speeds[event[2]][event[1]]), 6),
        "postImpactSpeedDropFraction": round(float(event[3]), 6),
        "combinedAngularDriveDegreesPerSecond": round(math.degrees(
            float(event[6])), 5),
        "supportPresent": bool(event[7]),
    } for event in selected_events]
    report = {
        "source": str(path.resolve()),
        "samples": len(frames),
        "fps": fps,
        "durationSeconds": round((len(frames) - 1) / fps, 5),
        "primarySide": side,
        "impactSample": int(peak),
        "impactSourceFrame": round(float(frames[peak]), 5),
        "impactScore": round(float(score), 6),
        "rawImpactScoreBeforeStyleRejects": round(float(raw_score), 6),
        "ordinaryAttackEligible": not excessive_turn,
        "styleRejects": (["pelvis_yaw_range_over_120_degrees"]
                         if excessive_turn else []),
        "impactEventCount": len(impact_events),
        "impactEvents": impact_events,
        "primaryWristSpeedHPerSecond": round(float(speeds[side][peak]), 6),
        "otherWristSpeedHPerSecond": round(float(speeds[other][peak]), 6),
        "dominanceRatio": round(float(dominance), 6),
        "postImpactMinimumSpeedHPerSecond": round(post_min, 6),
        "postImpactSpeedDropFraction": round(float(braking), 6),
        "pelvisAngularSpeedDegreesPerSecond": round(math.degrees(
            abs(float(pelvis_yaw_speed[peak]))), 5),
        "thoraxAngularSpeedDegreesPerSecond": round(math.degrees(
            abs(float(thorax_yaw_speed[peak]))), 5),
        "combinedAngularDriveDegreesPerSecond": round(math.degrees(
            float(angular_drive)), 5),
        "supportPresentAtImpact": support,
        "rootTravelH": round(float(np.max(np.linalg.norm(
            positions[:, index["pelvis"]] - positions[0, index["pelvis"]],
            axis=1))), 6),
        "maximumRootSpeedHPerSecond": round(float(np.max(root_speed)), 6),
        "pelvisYawRangeDegrees": round(pelvis_yaw_range, 5),
        "thoraxYawRangeDegrees": round(math.degrees(float(
            np.max(thorax_yaw) - np.min(thorax_yaw))), 5),
        "strikePathForwardLeftUpH": [
            round(float(value), 6) for value in path_delta
        ],
    }
    return report


def main() -> None:
    args = parse_args()
    candidates = [audit(path.resolve()) for path in args.inputs]
    candidates.sort(key=lambda value: value["impactScore"], reverse=True)
    output = {
        "schema": 1,
        "authority": "captured_landmark_impact_chain_screening",
        "result": "SOURCE_RANKING_ONLY_NOT_VISUALLY_APPROVED",
        "criteria": [
            "dominant arm speed",
            "post-peak braking",
            "pelvis and thorax angular drive",
            "support present at impact",
            "whole-body root commitment",
        ],
        "candidates": candidates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(
        output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "winner": candidates[0]["source"],
        "impactScore": candidates[0]["impactScore"],
        "candidates": len(candidates),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
