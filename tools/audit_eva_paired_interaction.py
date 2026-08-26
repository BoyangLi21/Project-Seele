#!/usr/bin/env python3
"""Audit a synchronized two-EVA kinematic interaction candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--actor-a", required=True, type=Path)
    parser.add_argument("--actor-b", required=True, type=Path)
    parser.add_argument("--landmark-a", required=True)
    parser.add_argument("--landmark-b", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--contact-distance-H", type=float, default=0.05)
    parser.add_argument("--minimum-approach-H", type=float, default=0.02)
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    height = float(
        data.xpos[model.body("head").id, 2]
        - min(data.xpos[model.body("foot_l").id, 2],
              data.xpos[model.body("foot_r").id, 2])
    )
    actor_a = np.load(args.actor_a)
    actor_b = np.load(args.actor_b)
    if len(actor_a["qpos"]) != len(actor_b["qpos"]):
        raise RuntimeError("paired states do not have matching frame counts")
    frames_a = np.asarray(actor_a["source_frames"], dtype=np.float64)
    frames_b = np.asarray(actor_b["source_frames"], dtype=np.float64)
    if not np.allclose(frames_a, frames_b, atol=1.0e-5):
        raise RuntimeError("paired states do not share source timestamps")
    names_a = [str(value) for value in actor_a["target_landmark_names"]]
    names_b = [str(value) for value in actor_b["target_landmark_names"]]
    if args.landmark_a not in names_a or args.landmark_b not in names_b:
        raise RuntimeError("requested interaction landmark is missing")
    point_a = np.asarray(actor_a["actual_positions"], dtype=np.float64)[
        :, names_a.index(args.landmark_a)
    ]
    point_b = np.asarray(actor_b["actual_positions"], dtype=np.float64)[
        :, names_b.index(args.landmark_b)
    ]
    distance = np.linalg.norm(point_a - point_b, axis=1) / height
    roots_a = np.asarray(actor_a["qpos"], dtype=np.float64)[:, :3]
    roots_b = np.asarray(actor_b["qpos"], dtype=np.float64)[:, :3]
    root_separation = np.linalg.norm(roots_a - roots_b, axis=1) / height
    contact = distance <= args.contact_distance_H
    final_window = max(2, int(round(0.10 / float(actor_a["timestep"][0]))))
    final_window = min(final_window, len(distance))
    initial_window = min(final_window, len(distance))
    initial_median = float(np.median(distance[:initial_window]))
    final_median = float(np.median(distance[-final_window:]))
    approach = initial_median - final_median
    contact_indices = np.flatnonzero(contact)
    failures = []
    if not np.any(contact[-final_window:]):
        failures.append("no_contact_envelope_in_final_window")
    if final_median > args.contact_distance_H:
        failures.append("final_contact_median_over_limit")
    if approach < args.minimum_approach_H:
        failures.append("insufficient_contact_approach")
    if float(np.min(root_separation)) < 0.25:
        failures.append("actor_roots_overlap")
    report = {
        "schema": 1,
        "model": str(args.model.resolve()),
        "actor_a": str(args.actor_a.resolve()),
        "actor_b": str(args.actor_b.resolve()),
        "frames": len(distance),
        "fps": 1.0 / float(actor_a["timestep"][0]),
        "interaction": f"{args.landmark_a}_A_to_{args.landmark_b}_B",
        "contact_distance_limit_H": args.contact_distance_H,
        "distance_H": {
            "minimum": float(np.min(distance)),
            "p05": float(np.percentile(distance, 5.0)),
            "median": float(np.median(distance)),
            "p95": float(np.percentile(distance, 95.0)),
            "initial_window_median": initial_median,
            "final_window_median": final_median,
            "approach": approach,
        },
        "contact_fraction": float(np.mean(contact)),
        "first_contact_source_frame": (
            None if not len(contact_indices)
            else float(frames_a[contact_indices[0]])
        ),
        "root_separation_H": {
            "minimum": float(np.min(root_separation)),
            "median": float(np.median(root_separation)),
            "maximum": float(np.max(root_separation)),
        },
        "failures": failures,
        "passed": not failures,
        "status": (
            "kinematic_pair_contact_gate_not_a_physical_grip_constraint"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "passed": report["passed"],
        "minimum_H": report["distance_H"]["minimum"],
        "final_median_H": final_median,
        "approach_H": approach,
        "failures": failures,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
