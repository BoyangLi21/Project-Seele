#!/usr/bin/env python3
"""Solve articulated EVA finger contacts in the exact Gecko matrix path.

This is a pose-authoring utility, not a pass/fail test.  It keeps the wrist,
weapon and camera transforms fixed, then numerically fits each three-phalange
digit to explicit contact points on a weapon grip.  Its compact JSON output is
copied into ``make_tiger_unit01_pack.py`` after visual inspection.
"""

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares


REPO = Path(__file__).resolve().parent.parent
PACK = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
MESH = PACK / "mesh/eva_unit01.mesh.json"
GEO = PACK / "geo/eva_unit01.geo.json"
ANIMATION = PACK / "animations/eva_unit01.animation.json"
KNIFE_MESH = PACK / "mesh/progressive_knife.mesh.json"
RENDERER = REPO / "tools/render_unit01_rig_preview.py"

# Contacts are expressed in the preview's world/model-pixel frame.  The four
# long fingers enter from the palm's +X side, touch the near hilt face, then
# hook around its camera-facing quadrant.  The thumb opposes them from -Z.
KNIFE_CONTACTS = {
    "thumb": ((10.45, 139.30, -26.98), (10.20, 138.95, -28.90)),
    "index": ((12.30, 138.00, -28.50), (10.00, 137.80, -26.50)),
    "middle": ((11.50, 135.80, -28.68), (9.03, 135.49, -26.55)),
    "ring": ((11.00, 133.50, -27.98), (8.30, 133.30, -26.56)),
    "little": ((10.60, 131.80, -26.79), (8.10, 131.60, -26.03)),
}


def load_renderer():
    spec = importlib.util.spec_from_file_location("eva_rig_preview", RENDERER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--animation", default="knife_ready")
    parser.add_argument("--hand", choices=("l", "r"), default="r")
    args = parser.parse_args()

    preview = load_renderer()
    mesh = json.loads(MESH.read_text(encoding="utf-8"))
    pivots, parents, base_rotations = preview.load_skeleton(mesh, GEO)
    _, _, base_pose, positions = preview.select_animation(
        ANIMATION, args.animation, 0.0)

    attachment = json.loads(KNIFE_MESH.read_text(encoding="utf-8"))
    attachment_vertices = []
    attachment_matrices = {}
    for bone, part in attachment["parts"].items():
        matrix = preview.bone_matrix(
            bone, pivots, parents, base_pose, positions,
            base_rotations, attachment_matrices)
        values = part["vertices"]
        stride = int(attachment["stride"])
        for start_index in range(0, len(values), stride):
            absolute = [values[start_index + axis] + part["pivot"][axis]
                        for axis in range(3)]
            attachment_vertices.append(preview.transform(
                matrix, (-absolute[0], absolute[1], absolute[2])))

    solved = {}
    diagnostics = {}
    for digit, (root_target, distal_target) in KNIFE_CONTACTS.items():
        root = f"finger_{digit}_{args.hand}"
        tip = f"finger_{digit}_tip_{args.hand}"
        distal = f"finger_{digit}_distal_{args.hand}"
        root_length = abs(pivots[tip][1] - pivots[root][1])
        tip_length = abs(pivots[distal][1] - pivots[tip][1])
        distal_part = mesh["parts"][distal]
        distal_ys = []
        values = distal_part["vertices"]
        for start in range(0, len(values), int(mesh["stride"])):
            distal_ys.append(values[start + 1]
                             + distal_part["pivot"][1])
        distal_length = pivots[distal][1] - min(distal_ys)

        # Preserve the approved two-contact curve while introducing a third
        # joint: the PIP/DIP boundary begins on the straight segment between
        # the former root and fingertip targets.  Later weapon profiles may
        # move this contact around a cylindrical grip for an independent hook.
        blend = tip_length / (tip_length + distal_length)
        tip_target = tuple(
            root_target[axis]
            + (distal_target[axis] - root_target[axis]) * blend
            for axis in range(3))

        start = np.array((*base_pose.get(root, (0.0, 0.0, 0.0)),
                          *base_pose.get(tip, (0.0, 0.0, 0.0)),
                          *base_pose.get(distal, (0.0, 0.0, 0.0))), dtype=float)

        def endpoints(angles):
            rotations = dict(base_pose)
            rotations[root] = tuple(angles[:3])
            rotations[tip] = tuple(angles[3:6])
            rotations[distal] = tuple(angles[6:])
            matrices = {}
            root_matrix = preview.bone_matrix(
                root, pivots, parents, rotations, positions,
                base_rotations, matrices)
            tip_matrix = preview.bone_matrix(
                tip, pivots, parents, rotations, positions,
                base_rotations, matrices)
            distal_matrix = preview.bone_matrix(
                distal, pivots, parents, rotations, positions,
                base_rotations, matrices)
            root_end = preview.transform(
                root_matrix,
                (pivots[root][0], pivots[root][1] - root_length,
                 pivots[root][2]))
            tip_end = preview.transform(
                tip_matrix,
                (pivots[tip][0], pivots[tip][1] - tip_length,
                 pivots[tip][2]))
            distal_end = preview.transform(
                distal_matrix,
                (pivots[distal][0], pivots[distal][1] - distal_length,
                 pivots[distal][2]))
            return (np.array(root_end), np.array(tip_end),
                    np.array(distal_end))

        neutral_matrices = {}
        root_joint = preview.transform(
            preview.bone_matrix(root, pivots, parents, base_pose, positions,
                                base_rotations, neutral_matrices),
            pivots[root])

        def residual(angles):
            root_end, tip_end, distal_end = endpoints(angles)
            contact = np.concatenate((
                root_end - np.asarray(root_target),
                tip_end - np.asarray(tip_target),
                distal_end - np.asarray(distal_target)))
            # Select the nearest continuous branch when several Euler triples
            # can reach the same two contacts.
            regularization = (angles - start) * 0.0025
            return np.concatenate((contact, regularization))

        result = least_squares(
            residual, start, bounds=(-170.0, 170.0),
            xtol=1.0e-12, ftol=1.0e-12, gtol=1.0e-12,
            max_nfev=4000)
        root_end, tip_end, distal_end = endpoints(result.x)
        solved[digit] = {
            "root": [round(value, 2) for value in result.x[:3]],
            "tip": [round(value, 2) for value in result.x[3:6]],
            "distal": [round(value, 2) for value in result.x[6:]],
        }
        diagnostics[digit] = {
            "joint": [round(float(value), 3) for value in root_joint],
            "lengths": [round(root_length, 3), round(tip_length, 3),
                        round(distal_length, 3)],
            "root_error": round(float(np.linalg.norm(
                root_end - np.asarray(root_target))), 4),
            "tip_error": round(float(np.linalg.norm(
                tip_end - np.asarray(tip_target))), 4),
            "distal_error": round(float(np.linalg.norm(
                distal_end - np.asarray(distal_target))), 4),
        }

        slice_points = [point for point in attachment_vertices
                        if abs(point[1] - root_joint[1]) <= 0.65]
        if slice_points:
            diagnostics[digit]["grip_slice_xz"] = [
                round(min(point[0] for point in slice_points), 3),
                round(max(point[0] for point in slice_points), 3),
                round(min(point[2] for point in slice_points), 3),
                round(max(point[2] for point in slice_points), 3),
            ]

    print(json.dumps({"pose": solved, "errors": diagnostics},
                     separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
