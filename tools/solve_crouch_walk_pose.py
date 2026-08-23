#!/usr/bin/env python3
"""Solve grounded compact crouch-walk leg keys through the real EVA rig."""
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

REPO = Path(__file__).resolve().parent.parent
PACK = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
RENDERER = REPO / "tools/render_unit01_rig_preview.py"


def load_renderer():
    spec = importlib.util.spec_from_file_location("eva_rig_preview", RENDERER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    preview = load_renderer()
    mesh_path = PACK / "mesh/eva_unit01.mesh.json"
    geo_path = PACK / "geo/eva_unit01.geo.json"
    animation_path = PACK / "animations/eva_unit01.animation.json"
    mesh = json.loads(mesh_path.read_text(encoding="utf-8"))
    pivots, parents, base_rotations = preview.load_skeleton(mesh, geo_path)

    old = {
        0.0: {"l": (-59.49, 96.12, -44.67), "r": (-34.23, 95.30, -69.15)},
        0.25: {"l": (-53.12, 106.19, -61.08), "r": (-45.02, 101.18, -64.21)},
        0.5: {"l": (-34.23, 95.30, -69.15), "r": (-59.49, 96.12, -44.67)},
        0.75: {"l": (-45.02, 101.18, -64.21), "r": (-53.12, 106.19, -61.08)},
    }
    targets = {
        0.0: {"l": (-10.0, 0.05), "r": (7.0, 0.05)},
        0.25: {"l": (-3.0, 3.0), "r": (1.0, 0.05)},
        0.5: {"l": (7.0, 0.05), "r": (-10.0, 0.05)},
        0.75: {"l": (1.0, 0.05), "r": (-3.0, 3.0)},
    }
    solved = {}
    for time in (0.0, 0.25, 0.5, 0.75):
        _, _, base_pose, positions = preview.select_animation(
            animation_path, "crouch_walk", time)
        solved[str(time)] = {}
        for side in ("l", "r"):
            leg, shin, foot = (f"leg_{side}", f"shin_{side}", f"foot_{side}")
            start = np.asarray(old[time][side], dtype=float)
            target_z, target_min_y = targets[time][side]
            foot_part = mesh["parts"][foot]
            stride = int(mesh["stride"])

            def sample(angles):
                pose = dict(base_pose)
                pose[leg] = (float(angles[0]), 0.0, -3.0 if side == "l" else 3.0)
                pose[shin] = (float(angles[1]), 0.0, 0.0)
                pose[foot] = (float(angles[2]), 0.0, 3.0 if side == "l" else -3.0)
                matrices = {}
                knee = preview.transform(
                    preview.bone_matrix(shin, pivots, parents, pose, positions,
                                        base_rotations, matrices), pivots[shin])
                ankle_matrix = preview.bone_matrix(
                    foot, pivots, parents, pose, positions,
                    base_rotations, matrices)
                ankle = preview.transform(ankle_matrix, pivots[foot])
                verts = []
                values = foot_part["vertices"]
                for start_index in range(0, len(values), stride):
                    absolute = [values[start_index + axis] + foot_part["pivot"][axis]
                                for axis in range(3)]
                    verts.append(preview.transform(
                        ankle_matrix, (-absolute[0], absolute[1], absolute[2])))
                minimum_y = min(point[1] for point in verts)
                front = min((point for point in verts if point[2] <= ankle[2]),
                            key=lambda point: point[1])[1]
                rear = min((point for point in verts if point[2] > ankle[2]),
                           key=lambda point: point[1])[1]
                return np.asarray(knee), np.asarray(ankle), minimum_y, front - rear

            def residual(angles):
                knee, ankle, minimum_y, sole_tilt = sample(angles)
                return np.asarray([
                    (ankle[2] - target_z) * 1.25,
                    (minimum_y - target_min_y) * 2.0,
                    sole_tilt * 0.7,
                    (knee[2] + 30.0) * 0.18,
                    *(0.018 * (angles - start)),
                ])

            result = least_squares(
                residual, start,
                bounds=([-80.0, 65.0, -100.0], [-25.0, 125.0, -20.0]),
                xtol=1e-11, ftol=1e-11, gtol=1e-11, max_nfev=2500)
            knee, ankle, minimum_y, sole_tilt = sample(result.x)
            solved[str(time)][side] = {
                "angles": [round(float(value), 2) for value in result.x],
                "knee_yz": [round(float(knee[1]), 3), round(float(knee[2]), 3)],
                "ankle_yz": [round(float(ankle[1]), 3), round(float(ankle[2]), 3)],
                "min_y": round(float(minimum_y), 3),
                "sole_tilt": round(float(sole_tilt), 3),
                "cost": round(float(result.cost), 5),
            }
    print(json.dumps(solved, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()