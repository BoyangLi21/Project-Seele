#!/usr/bin/env python3
"""Align EVA physical palms with their forearms in the neutral bind pose."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


def text(values) -> str:
    return " ".join(f"{float(value):.9g}" for value in values)


def quaternion_from_x_axis(direction: np.ndarray) -> np.ndarray:
    direction = direction / np.linalg.norm(direction)
    source = np.asarray((1.0, 0.0, 0.0), dtype=np.float64)
    dot = float(np.clip(np.dot(source, direction), -1.0, 1.0))
    if dot > 1.0 - 1.0e-10:
        return np.asarray((1.0, 0.0, 0.0, 0.0), dtype=np.float64)
    if dot < -1.0 + 1.0e-10:
        return np.asarray((0.0, 0.0, 1.0, 0.0), dtype=np.float64)
    axis = np.cross(source, direction)
    quaternion = np.concatenate((
        [math.sqrt((1.0 + dot) * 0.5)],
        axis / math.sqrt(2.0 * (1.0 + dot)),
    ))
    return quaternion / np.linalg.norm(quaternion)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    tree = ET.parse(args.input)
    root = tree.getroot()
    rows = {}
    for side in ("l", "r"):
        wrist = root.find(f".//body[@name='wrist_link_{side}']")
        if wrist is None:
            raise RuntimeError(f"missing wrist_link_{side}")
        vector = np.asarray(
            [float(value) for value in wrist.attrib["pos"].split()],
            dtype=np.float64,
        )
        direction = vector / np.linalg.norm(vector)
        quaternion = quaternion_from_x_axis(direction)
        hand = wrist.find(f"body[@name='hand_{side}']")
        if hand is None:
            raise RuntimeError(f"missing hand_{side}")
        palm = hand.find(f"geom[@name='palm_{side}']")
        knuckle = hand.find(f"geom[@name='knuckle_{side}']")
        grip = hand.find(f"site[@name='palm_grip_{side}']")
        if palm is None or knuckle is None or grip is None:
            raise RuntimeError(f"incomplete hand geometry for {side}")
        palm.attrib["pos"] = text(direction * 0.12)
        palm.attrib["quat"] = text(quaternion)
        palm.attrib["size"] = "0.18 0.105 0.075"
        knuckle.attrib["pos"] = text(direction * 0.27)
        knuckle.attrib["quat"] = text(quaternion)
        knuckle.attrib["size"] = "0.09 0.10 0.07"
        grip.attrib["pos"] = text(direction * 0.15)
        rows[side] = {
            "forearm_direction": direction.tolist(),
            "hand_geometry_quaternion_wxyz": quaternion.tolist(),
            "palm_center": (direction * 0.12).tolist(),
            "knuckle_center": (direction * 0.27).tolist(),
        }
    custom = root.find("custom")
    if custom is None:
        custom = ET.SubElement(root, "custom")
    marker = custom.find("text[@name='visual_hand_bind']")
    if marker is None:
        marker = ET.SubElement(custom, "text", {"name": "visual_hand_bind"})
    marker.attrib["data"] = "palm and knuckle long axis follows neutral forearm"
    ET.indent(tree, space="  ")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    report = {
        "schema": 1,
        "input": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "sides": rows,
        "change": (
            "neutral palm/knuckle +X axis rotated onto evaluated forearm "
            "direction; wrist joint limits unchanged"
        ),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
