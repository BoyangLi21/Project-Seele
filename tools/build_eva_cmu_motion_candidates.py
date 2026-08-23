#!/usr/bin/env python3
"""Retarget selected CMU 120 Hz mocap segments into an EVA candidate DB.

The output is intentionally separate from the runtime database.  It is a 3D
review artifact: candidates must pass the exact-matrix Blender lab and motion
quality gates before any clip is promoted to Minecraft.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_eva_motion_database import (
    MODEL_UNITS_PER_SOURCE_METRE,
    SAMPLE_RATE,
    clamp,
    group_delta,
    group_local_rotation,
    load_target_pivots,
    project_foot_for_contact,
    project_to_eva_joint,
    relative_limb_goal,
    rounded_quaternion,
    solve_target_limb,
    source_limb_goal,
    target_ankle_position,
    target_vector,
)


CMU_CHAINS = {
    "torso_lower": ("lowerback", "upperback"),
    "torso_upper": ("thorax", "lowerneck"),
    "head": ("upperneck", "head"),
    "arm_l": ("lclavicle", "lhumerus"),
    "forearm_l": ("lradius",),
    "hand_l": ("lwrist", "lhand"),
    "arm_r": ("rclavicle", "rhumerus"),
    "forearm_r": ("rradius",),
    "hand_r": ("rwrist", "rhand"),
    "leg_l": ("lhipjoint", "lfemur"),
    "shin_l": ("ltibia",),
    "foot_l": ("lfoot", "ltoes"),
    "leg_r": ("rhipjoint", "rfemur"),
    "shin_r": ("rtibia",),
    "foot_r": ("rfoot", "rtoes"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--target-geo", required=True, type=Path)
    parser.add_argument("--base-motion-db", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.actions, bpy.data.armatures, bpy.data.meshes):
        for datablock in tuple(datablocks):
            datablocks.remove(datablock)


def import_bvh(path: Path) -> bpy.types.Object:
    reset_scene()
    bpy.ops.import_anim.bvh(
        filepath=str(path.resolve()), target="ARMATURE",
        global_scale=0.1, frame_start=1, use_fps_scale=False,
        update_scene_fps=True, update_scene_duration=True,
        rotate_mode="NATIVE", axis_forward="-Z", axis_up="Y",
    )
    armatures = [obj for obj in bpy.context.scene.objects
                 if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise SystemExit(f"expected one armature, found {len(armatures)}")
    return armatures[0]


def quantile(values: list[float], amount: float) -> float:
    ordered = sorted(values)
    position = amount * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    alpha = position - low
    return ordered[low] * (1.0 - alpha) + ordered[high] * alpha


def pose_point(armature: bpy.types.Object, name: str) -> Vector:
    return armature.matrix_world @ armature.pose.bones[name].matrix.translation


def source_root_yaw(armature: bpy.types.Object) -> float:
    left = pose_point(armature, "lfemur")
    right = pose_point(armature, "rfemur")
    lateral = right - left
    lateral.z = 0.0
    lateral.normalize()
    forward = Vector((-lateral.y, lateral.x, 0.0))
    return math.atan2(forward.x, -forward.y)


def capture_scale_and_floor(armature: bpy.types.Object) -> tuple[float, float]:
    scene = bpy.context.scene
    scene.frame_set(scene.frame_start)
    bpy.context.view_layer.update()
    points = [pose_point(armature, name) for name in (
        "head", "lfoot", "ltoes", "rfoot", "rtoes"
    )]
    height = max(point.z for point in points) - min(point.z for point in points)
    source_to_meters = 1.75 / max(height, 1.0e-6)
    foot_heights = []
    step = max(1, int(round((scene.render.fps / scene.render.fps_base) / 30.0)))
    for frame in range(scene.frame_start, scene.frame_end + 1, step):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for side in ("l", "r"):
            foot_heights.append(min(
                pose_point(armature, f"{side}foot").z,
                pose_point(armature, f"{side}toes").z,
            ))
    return source_to_meters, quantile(foot_heights, 0.015)


def reference_contract(path: Path) -> tuple[
    dict[str, Matrix], dict[str, tuple[Vector, float, Vector]], float
]:
    armature = import_bvh(path)
    scene = bpy.context.scene
    scene.frame_set(scene.frame_start)
    bpy.context.view_layer.update()
    rotations = {
        target: group_local_rotation(armature, chain)[0].copy()
        for target, chain in CMU_CHAINS.items()
    }
    goals = {}
    for side in ("l", "r"):
        goals[f"arm_{side}"] = source_limb_goal(
            armature, "thorax", f"{side}humerus",
            f"{side}radius", f"{side}wrist"
        )
        goals[f"leg_{side}"] = source_limb_goal(
            armature, "root", f"{side}femur",
            f"{side}tibia", f"{side}foot"
        )
    source_to_meters, _floor = capture_scale_and_floor(armature)
    return rotations, goals, source_to_meters


def find_definition(analysis: dict, kind: str, segment_id: str) -> dict:
    key = ("cycles" if kind == "locomotion"
           else "jumps" if kind == "jump" else "segments")
    for item in analysis[key]:
        if item["id"] == segment_id:
            return item
    raise KeyError(f"missing {segment_id} in {key}")


def limb_scales(kind: str) -> tuple[Vector, Vector]:
    if kind == "locomotion":
        return Vector((0.82, 0.96, 0.88)), Vector((0.11, 0.98, 0.76))
    if kind == "punch":
        return Vector((0.94, 1.0, 0.96)), Vector((0.13, 0.94, 0.64))
    if kind == "jump":
        return Vector((0.90, 1.0, 0.94)), Vector((0.11, 0.98, 0.78))
    if kind == "trajectory":
        return Vector((0.84, 0.98, 0.90)), Vector((0.11, 0.98, 0.78))
    if kind == "prone":
        return Vector((1.0, 1.0, 1.0)), Vector((0.34, 1.0, 0.94))
    if kind == "posture_transition":
        return Vector((0.96, 1.0, 0.98)), Vector((0.24, 1.0, 0.88))
    return Vector((0.96, 1.0, 0.98)), Vector((0.14, 0.94, 0.68))


def authored_to_runtime_quaternion(quat: Quaternion) -> Quaternion:
    """Apply Gecko's Bedrock authored (-X,-Y,+Z) Euler convention."""
    euler = quat.to_euler("XYZ")
    result = Euler((-euler.x, -euler.y, euler.z), "XYZ").to_quaternion()
    result.normalize()
    return result


def runtime_to_authored_quaternion(quat: Quaternion) -> Quaternion:
    # The sign convention is an involution in the bounded EVA joint domain.
    return authored_to_runtime_quaternion(quat)


def authored_to_runtime_vector(vector: Vector) -> Vector:
    return Vector((-vector.x, vector.y, vector.z))


def runtime_target_pivots(pivots: dict[str, Vector]) -> dict[str, Vector]:
    return {
        name: authored_to_runtime_vector(pivot)
        for name, pivot in pivots.items()
    }


def pin_leg_endpoint(
    direction: Vector,
    reach: float,
    target_pivots: dict[str, Vector],
    torso_rotation: Quaternion,
    side: str,
    planted: bool,
    contact_plane: float,
) -> tuple[Vector, float]:
    """Pin a declared contact in target space before solving the EVA leg."""
    hip = target_pivots[f"leg_{side}"]
    knee = target_pivots[f"shin_{side}"]
    ankle = target_pivots[f"foot_{side}"]
    total = (knee - hip).length + (ankle - knee).length
    local_goal = hip + direction * reach * total
    torso_pivot = target_pivots["torso_lower"]
    world_goal = torso_pivot + torso_rotation @ (local_goal - torso_pivot)
    # A near-ground swing foot must not pass below the rigid EVA sole.  A true
    # contact is pinned exactly; swing keeps a small mechanical clearance.
    minimum_height = contact_plane if planted else contact_plane + 0.8
    if planted:
        world_goal.y = minimum_height
    elif world_goal.y < minimum_height:
        world_goal.y = minimum_height
    world_hip = torso_pivot + torso_rotation @ (hip - torso_pivot)
    # Ground contact is non-negotiable.  If the human step is wider than the
    # long but finite EVA leg can reach at that height, shorten only the
    # horizontal component instead of letting the solver pull the foot up.
    vertical = world_goal.y - world_hip.y
    horizontal = Vector((world_goal.x - world_hip.x,
                         0.0,
                         world_goal.z - world_hip.z))
    reach_cap = 0.99999 if planted else 0.995
    maximum_horizontal = math.sqrt(max(
        0.0, (total * reach_cap) ** 2 - vertical ** 2
    ))
    if horizontal.length > maximum_horizontal:
        if maximum_horizontal > 1.0e-6:
            horizontal.normalize()
            horizontal *= maximum_horizontal
            world_goal.x = world_hip.x + horizontal.x
            world_goal.z = world_hip.z + horizontal.z
        else:
            world_goal.x = world_hip.x
            world_goal.z = world_hip.z
    local_goal = torso_pivot + torso_rotation.conjugated() @ (
        world_goal - torso_pivot
    )
    vector = local_goal - hip
    return vector.normalized(), clamp(vector.length / total, 0.08, reach_cap)


def common_reachable_contact_plane(
    target_pivots: dict[str, Vector], torso_rotation: Quaternion
) -> float:
    """Find one pre-root floor plane reachable by both asymmetric hips."""
    torso_pivot = target_pivots["torso_lower"]
    plane = max(target_pivots["foot_l"].y,
                target_pivots["foot_r"].y)
    for side in ("l", "r"):
        hip = target_pivots[f"leg_{side}"]
        knee = target_pivots[f"shin_{side}"]
        ankle = target_pivots[f"foot_{side}"]
        total = (knee - hip).length + (ankle - knee).length
        world_hip = torso_pivot + torso_rotation @ (hip - torso_pivot)
        plane = max(plane, world_hip.y - total * 0.99999)
    return plane


def close_loop(frames: list[dict]) -> None:
    """Distribute residual cycle drift continuously over a locomotion loop."""
    if len(frames) < 3:
        return
    last_index = len(frames) - 1
    identity = Quaternion((1.0, 0.0, 0.0, 0.0))
    for bone_index in range(len(frames[0]["rotation_wxyz"])):
        first = Quaternion(tuple(frames[0]["rotation_wxyz"][bone_index]))
        last = Quaternion(tuple(frames[-1]["rotation_wxyz"][bone_index]))
        correction = last.conjugated() @ first
        correction.normalize()
        for frame_index, frame in enumerate(frames):
            amount = frame_index / last_index
            partial = identity.slerp(correction, amount)
            current = Quaternion(tuple(frame["rotation_wxyz"][bone_index]))
            closed = current @ partial
            closed.normalize()
            frame["rotation_wxyz"][bone_index] = rounded_quaternion(closed)
    root_delta = (float(frames[-1]["root_m"][1])
                  - float(frames[0]["root_m"][1]))
    yaw_delta = (float(frames[-1].get("root_yaw_radians", 0.0))
                 - float(frames[0].get("root_yaw_radians", 0.0)))
    for frame_index, frame in enumerate(frames):
        amount = frame_index / last_index
        frame["root_m"][1] = round(
            float(frame["root_m"][1]) - root_delta * amount, 7
        )
        if "root_yaw_radians" in frame:
            frame["root_yaw_radians"] = round(
                float(frame["root_yaw_radians"]) - yaw_delta * amount, 7
            )
    frames[-1]["foot_contact"] = list(frames[0]["foot_contact"])
    if "hand_contact" in frames[0]:
        frames[-1]["hand_contact"] = list(frames[0]["hand_contact"])


def lock_contact_feet(
    frames: list[dict],
    bone_order: list[str],
    pivots: dict[str, Vector],
    root_travel: Vector,
) -> None:
    """Bake contact locks with shared pelvis correction and target-space IK."""
    if len(frames) < 2:
        return
    bone_indices = {name: index for index, name in enumerate(bone_order)}
    cached_rotations = [{
        name: authored_to_runtime_quaternion(Quaternion(tuple(
            frame["rotation_wxyz"][index]
        )))
        for name, index in bone_indices.items()
    } for frame in frames]
    root_rotations = [Quaternion((
        math.cos(float(frame.get("root_yaw_radians", 0.0)) * 0.5),
        0.0,
        math.sin(float(frame.get("root_yaw_radians", 0.0)) * 0.5),
        0.0,
    )) for frame in frames]
    virtual_roots = [
        authored_to_runtime_vector(root_travel)
        * (MODEL_UNITS_PER_SOURCE_METRE
           * index / max(1, len(frames) - 1))
        for index in range(len(frames))
    ]
    cached_roots = [
        authored_to_runtime_vector(Vector(tuple(
            float(value) for value in frame["root_m"]
        ))) * MODEL_UNITS_PER_SOURCE_METRE + virtual_roots[index]
        for index, frame in enumerate(frames)
    ]

    targets: list[list[Vector | None]] = [
        [None, None] for _ in frames
    ]
    ground_y = max(pivots["foot_l"].y, pivots["foot_r"].y) \
        + 0.018 * MODEL_UNITS_PER_SOURCE_METRE
    for side_index, side in enumerate(("l", "r")):
        runs = []
        opened = None
        for index, frame in enumerate(frames):
            active = bool(frame["foot_contact"][side_index])
            if active and opened is None:
                opened = index
            elif not active and opened is not None:
                runs.append((opened, index - 1))
                opened = None
        if opened is not None:
            runs.append((opened, len(frames) - 1))
        for first, last in runs:
            positions = [
                root_rotations[index] @ target_ankle_position(
                    cached_rotations[index], pivots, side
                )
                + cached_roots[index]
                for index in range(first, last + 1)
            ]
            lock = sum(positions, Vector((0.0, 0.0, 0.0))) / len(positions)
            lock.y = ground_y
            for index in range(first, last + 1):
                targets[index][side_index] = lock.copy()

    def write_root(index: int) -> None:
        local_runtime = (cached_roots[index] - virtual_roots[index]) \
            / MODEL_UNITS_PER_SOURCE_METRE
        authored = authored_to_runtime_vector(local_runtime)
        frames[index]["root_m"] = [
            round(float(value), 7) for value in authored
        ]

    def solve_side(index: int, side_index: int, side: str) -> None:
        target = targets[index][side_index]
        if target is None:
            return
        rotations = cached_rotations[index]
        target_world = root_rotations[index].conjugated() @ (
            target - cached_roots[index]
        )
        torso_pivot = pivots["torso_lower"]
        torso = rotations["torso_lower"]
        target_local = torso_pivot + torso.conjugated() @ (
            target_world - torso_pivot
        )
        hip = pivots[f"leg_{side}"]
        knee = pivots[f"shin_{side}"]
        ankle = pivots[f"foot_{side}"]
        vector = target_local - hip
        total = (knee - hip).length + (ankle - knee).length
        reach = clamp(vector.length / total, 0.08, 0.99999)
        direction = vector.normalized()
        current_knee = hip + rotations[f"leg_{side}"] @ (knee - hip)
        pole = current_knee - hip
        pole -= direction * pole.dot(direction)
        if pole.length < 1.0e-6:
            pole = Vector((0.0, 0.0, -1.0))
        pole.normalize()
        thigh, shin = solve_target_limb(
            hip, knee, ankle, direction, reach, pole
        )
        rotations[f"leg_{side}"] = thigh
        rotations[f"shin_{side}"] = shin
        parent = rotations["torso_lower"] @ thigh @ shin
        rotations[f"foot_{side}"] = project_foot_for_contact(
            rotations[f"foot_{side}"], parent, True
        )
        for bone_name in (f"leg_{side}", f"shin_{side}", f"foot_{side}"):
            frames[index]["rotation_wxyz"][bone_indices[bone_name]] = \
                rounded_quaternion(runtime_to_authored_quaternion(
                    rotations[bone_name]
                ))

    # A few Gauss-Seidel-style passes share incompatible two-foot error with
    # the pelvis/root instead of stretching either rigid leg beyond reach.
    for _iteration in range(6):
        for index in range(len(frames)):
            active = [(side_index, side, targets[index][side_index])
                      for side_index, side in enumerate(("l", "r"))
                      if targets[index][side_index] is not None]
            if not active:
                continue
            errors = []
            for side_index, side, target in active:
                actual = (root_rotations[index] @ target_ankle_position(
                    cached_rotations[index], pivots, side
                ) + cached_roots[index])
                errors.append(target - actual)
            correction = sum(errors, Vector((0.0, 0.0, 0.0))) / len(errors)
            cached_roots[index] += correction * 0.72
            write_root(index)
            for side_index, side, _target in active:
                solve_side(index, side_index, side)

    # Re-establish quaternion hemisphere continuity after the IK bake.
    for bone_index in range(len(bone_order)):
        previous = None
        for frame in frames:
            quat = Quaternion(tuple(frame["rotation_wxyz"][bone_index]))
            if previous is not None and previous.dot(quat) < 0.0:
                quat = Quaternion((-quat.w, -quat.x, -quat.y, -quat.z))
                frame["rotation_wxyz"][bone_index] = rounded_quaternion(quat)
            previous = quat


def fit_loop_root_travel(
    frames: list[dict], bone_order: list[str], pivots: dict[str, Vector],
    fallback: Vector,
) -> Vector:
    """Least-surprise stride fitted to the retargeted planted-foot velocity."""
    if len(frames) < 3:
        return fallback
    indices = {name: index for index, name in enumerate(bone_order)}
    rotations = []
    root_rotations = []
    roots = []
    for frame in frames:
        rotations.append({
            name: authored_to_runtime_quaternion(Quaternion(tuple(
                frame["rotation_wxyz"][index]
            )))
            for name, index in indices.items()
        })
        yaw = float(frame.get("root_yaw_radians", 0.0))
        root_rotations.append(Quaternion((math.cos(yaw * 0.5), 0.0,
                                            math.sin(yaw * 0.5), 0.0)))
        roots.append(authored_to_runtime_vector(Vector(tuple(
            float(value) for value in frame["root_m"]
        ))) * MODEL_UNITS_PER_SOURCE_METRE)
    x_candidates = []
    z_candidates = []
    cycle_scale = (len(frames) - 1) / MODEL_UNITS_PER_SOURCE_METRE
    for side_index, side in enumerate(("l", "r")):
        for index in range(1, len(frames)):
            if (not frames[index - 1]["foot_contact"][side_index]
                    or not frames[index]["foot_contact"][side_index]):
                continue
            previous = (root_rotations[index - 1] @ target_ankle_position(
                rotations[index - 1], pivots, side
            ) + roots[index - 1])
            current = (root_rotations[index] @ target_ankle_position(
                rotations[index], pivots, side
            ) + roots[index])
            delta = current - previous
            x_candidates.append(-delta.x * cycle_scale)
            z_candidates.append(-delta.z * cycle_scale)
    if len(x_candidates) < 2:
        return fallback
    runtime = Vector((statistics.median(x_candidates), 0.0,
                      statistics.median(z_candidates)))
    authored = authored_to_runtime_vector(runtime)
    magnitude = math.hypot(authored.x, authored.z)
    return authored if 0.35 <= magnitude <= 4.5 else fallback


def target_hand_position(rotations: dict[str, Quaternion],
                         pivots: dict[str, Vector], side: str) -> Vector:
    shoulder = pivots[f"arm_{side}"]
    elbow_rest = pivots[f"forearm_{side}"]
    wrist_rest = pivots[f"hand_{side}"]
    arm = rotations[f"arm_{side}"]
    forearm = rotations[f"forearm_{side}"]
    elbow = shoulder + arm @ (elbow_rest - shoulder)
    wrist = elbow + (arm @ forearm) @ (wrist_rest - elbow_rest)
    upper_pivot = pivots["torso_upper"]
    wrist = upper_pivot + rotations["torso_upper"] @ (wrist - upper_pivot)
    lower_pivot = pivots["torso_lower"]
    return lower_pivot + rotations["torso_lower"] @ (wrist - lower_pivot)


def lock_contact_hands(frames: list[dict], bone_order: list[str],
                       pivots: dict[str, Vector], root_travel: Vector,
                       move_root: bool = True) -> None:
    """Lock supporting hands without moving the already foot-locked pelvis."""
    if len(frames) < 2 or not any("hand_contact" in frame for frame in frames):
        return
    indices = {name: index for index, name in enumerate(bone_order)}
    rotations = [{
        name: authored_to_runtime_quaternion(Quaternion(tuple(
            frame["rotation_wxyz"][index]
        )))
        for name, index in indices.items()
    } for frame in frames]
    root_rotations = [Quaternion((
        math.cos(float(frame.get("root_yaw_radians", 0.0)) * 0.5), 0.0,
        math.sin(float(frame.get("root_yaw_radians", 0.0)) * 0.5), 0.0,
    )) for frame in frames]
    roots = []
    virtual_roots = []
    for frame_index, frame in enumerate(frames):
        root = authored_to_runtime_vector(Vector(tuple(
            float(value) for value in frame["root_m"]
        ))) * MODEL_UNITS_PER_SOURCE_METRE
        phase = frame_index / max(1, len(frames) - 1)
        virtual = authored_to_runtime_vector(root_travel) \
            * (MODEL_UNITS_PER_SOURCE_METRE * phase)
        root += virtual
        virtual_roots.append(virtual)
        roots.append(root)

    targets: list[list[Vector | None]] = [[None, None] for _ in frames]
    for side_index, side in enumerate(("l", "r")):
        opened = None
        runs = []
        for frame_index, frame in enumerate(frames):
            active = bool(frame.get("hand_contact", (False, False))[side_index])
            if active and opened is None:
                opened = frame_index
            elif not active and opened is not None:
                runs.append((opened, frame_index - 1))
                opened = None
        if opened is not None:
            runs.append((opened, len(frames) - 1))
        for first, last in runs:
            positions = [
                root_rotations[index] @ target_hand_position(
                    rotations[index], pivots, side
                ) + roots[index]
                for index in range(first, last + 1)
            ]
            lock = sum(positions, Vector((0.0, 0.0, 0.0))) / len(positions)
            lock.y = sorted(point.y for point in positions)[len(positions) // 2]
            for index in range(first, last + 1):
                targets[index][side_index] = lock.copy()

    def write_root(frame_index: int) -> None:
        local_runtime = (roots[frame_index] - virtual_roots[frame_index]) \
            / MODEL_UNITS_PER_SOURCE_METRE
        authored = authored_to_runtime_vector(local_runtime)
        frames[frame_index]["root_m"] = [
            round(float(value), 7) for value in authored
        ]

    for _iteration in range(8 if move_root else 1):
      for frame_index, frame_targets in enumerate(targets):
        active_targets = [target for target in frame_targets
                          if target is not None]
        if move_root and active_targets:
            errors = []
            for side_index, side in enumerate(("l", "r")):
                target = frame_targets[side_index]
                if target is None:
                    continue
                actual = (root_rotations[frame_index] @ target_hand_position(
                    rotations[frame_index], pivots, side
                ) + roots[frame_index])
                errors.append(target - actual)
            roots[frame_index] += (
                sum(errors, Vector((0.0, 0.0, 0.0))) / len(errors)
            ) * 0.90
            write_root(frame_index)
        for side_index, side in enumerate(("l", "r")):
            target = frame_targets[side_index]
            if target is None:
                continue
            pose = rotations[frame_index]
            body_target = root_rotations[frame_index].conjugated() @ (
                target - roots[frame_index]
            )
            lower_pivot = pivots["torso_lower"]
            body_target = lower_pivot + pose["torso_lower"].conjugated() @ (
                body_target - lower_pivot
            )
            upper_pivot = pivots["torso_upper"]
            local_target = upper_pivot + pose["torso_upper"].conjugated() @ (
                body_target - upper_pivot
            )
            shoulder = pivots[f"arm_{side}"]
            elbow = pivots[f"forearm_{side}"]
            wrist = pivots[f"hand_{side}"]
            vector = local_target - shoulder
            total = (elbow - shoulder).length + (wrist - elbow).length
            direction = vector.normalized()
            reach = clamp(vector.length / total, 0.08, 0.9995)
            current_elbow = shoulder + pose[f"arm_{side}"] @ (elbow - shoulder)
            pole = current_elbow - shoulder
            pole -= direction * pole.dot(direction)
            if pole.length < 1.0e-6:
                pole = Vector((0.0, 0.0, -1.0))
            pole.normalize()
            arm, forearm = solve_target_limb(
                shoulder, elbow, wrist, direction, reach, pole
            )
            pose[f"arm_{side}"] = arm
            pose[f"forearm_{side}"] = forearm
            for bone_name in (f"arm_{side}", f"forearm_{side}"):
                frames[frame_index]["rotation_wxyz"][indices[bone_name]] = \
                    rounded_quaternion(runtime_to_authored_quaternion(
                        pose[bone_name]
                    ))
    for bone_index in range(len(bone_order)):
        previous = None
        for frame in frames:
            quat = Quaternion(tuple(frame["rotation_wxyz"][bone_index]))
            if previous is not None and previous.dot(quat) < 0.0:
                quat = Quaternion((-quat.w, -quat.x, -quat.y, -quat.z))
                frame["rotation_wxyz"][bone_index] = rounded_quaternion(quat)
            previous = quat


def prune_unstable_hand_contacts(frames: list[dict], bone_order: list[str],
                                 pivots: dict[str, Vector],
                                 root_travel: Vector,
                                 maximum_speed: float = 0.35) -> int:
    """Remove automatic contact labels contradicted by target hand velocity."""
    indices = {name: index for index, name in enumerate(bone_order)}
    positions = {"l": [], "r": []}
    for frame_index, frame in enumerate(frames):
        rotations = {
            name: authored_to_runtime_quaternion(Quaternion(tuple(
                frame["rotation_wxyz"][index]
            )))
            for name, index in indices.items()
        }
        yaw = float(frame.get("root_yaw_radians", 0.0))
        yaw_rotation = Quaternion((math.cos(yaw * 0.5), 0.0,
                                   math.sin(yaw * 0.5), 0.0))
        root = authored_to_runtime_vector(Vector(tuple(
            float(value) for value in frame["root_m"]
        ))) * MODEL_UNITS_PER_SOURCE_METRE
        phase = frame_index / max(1, len(frames) - 1)
        root += authored_to_runtime_vector(root_travel) \
            * (MODEL_UNITS_PER_SOURCE_METRE * phase)
        for side in ("l", "r"):
            positions[side].append(
                yaw_rotation @ target_hand_position(rotations, pivots, side)
                + root
            )
    removed = 0
    for side_index, side in enumerate(("l", "r")):
        for frame_index in range(1, len(frames)):
            previous = frames[frame_index - 1].get(
                "hand_contact", (False, False)
            )[side_index]
            current = frames[frame_index].get(
                "hand_contact", (False, False)
            )[side_index]
            if not previous or not current:
                continue
            speed = ((positions[side][frame_index]
                      - positions[side][frame_index - 1]).length
                     / MODEL_UNITS_PER_SOURCE_METRE * SAMPLE_RATE)
            if speed > maximum_speed:
                frames[frame_index]["hand_contact"][side_index] = False
                removed += 1
    return removed


def sample_segment(
    armature: bpy.types.Object,
    definition: dict,
    kind: str,
    reference_rotations: dict[str, Matrix],
    reference_limb_goals: dict[str, tuple[Vector, float, Vector]],
    target_pivots: dict[str, Vector],
    bone_order: list[str],
    fallback_rotations: list[list[float]],
    source_to_meters: float,
    floor: float,
) -> dict:
    scene = bpy.context.scene
    source_fps = scene.render.fps / scene.render.fps_base
    start = float(definition["start_frame"])
    end = float(definition["end_frame"])
    duration = max(1.0 / source_fps, (end - start) / source_fps)
    loop = kind == "locomotion"
    count = max(2, int(round(duration * SAMPLE_RATE)) + (0 if loop else 1))
    times = [index / SAMPLE_RATE for index in range(count)]
    scene.frame_set(int(start))
    bpy.context.view_layer.update()
    start_root = pose_point(armature, "root")
    arm_scale, leg_scale = limb_scales(kind)
    fallback_authored = {
        name: Quaternion(tuple(fallback_rotations[index]))
        for index, name in enumerate(bone_order)
    }
    contact_samples = []
    hand_contact_samples = []
    yaw_samples = []
    previous_toes: list[Vector] | None = None
    previous_hands: list[Vector] | None = None
    for seconds in times:
        source_frame = min(end, start + seconds * source_fps)
        whole = math.floor(source_frame)
        scene.frame_set(int(whole), subframe=source_frame - whole)
        bpy.context.view_layer.update()
        toes = [
            target_vector(pose_point(armature, f"{side}toes"))
            * source_to_meters
            for side in ("l", "r")
        ]
        heights = [min(
            pose_point(armature, f"{side}foot").z,
            pose_point(armature, f"{side}toes").z,
        ) for side in ("l", "r")]
        speeds = ([0.0, 0.0] if previous_toes is None else [
            (point - old).length * SAMPLE_RATE
            for point, old in zip(toes, previous_toes)
        ])
        contact_samples.append([
            height <= floor + 0.08 / source_to_meters and speed <= 0.50
            for height, speed in zip(heights, speeds)
        ])
        hands = [
            target_vector(pose_point(armature, f"{side}hand"))
            * source_to_meters
            for side in ("l", "r")
        ]
        hand_speeds = ([0.0, 0.0] if previous_hands is None else [
            (point - old).length * SAMPLE_RATE
            for point, old in zip(hands, previous_hands)
        ])
        hand_contact_samples.append([
            (kind in {"prone", "posture_transition"}
             and point.y <= floor * source_to_meters + 0.13
             and speed <= 0.50)
            for point, speed in zip(hands, hand_speeds)
        ])
        previous_hands = [point.copy() for point in hands]
        yaw = source_root_yaw(armature)
        if yaw_samples:
            while yaw - yaw_samples[-1] > math.pi:
                yaw -= math.tau
            while yaw - yaw_samples[-1] < -math.pi:
                yaw += math.tau
        yaw_samples.append(yaw)
        previous_toes = [point.copy() for point in toes]
    if len(contact_samples) >= 3:
        filtered = []
        for index in range(len(contact_samples)):
            left = max(0, index - 1)
            right = min(len(contact_samples), index + 2)
            filtered.append([
                sum(contact_samples[item][side]
                    for item in range(left, right)) * 2 >= right - left
                for side in (0, 1)
            ])
        contact_samples = filtered
        filtered_hands = []
        for index in range(len(hand_contact_samples)):
            left = max(0, index - 1)
            right = min(len(hand_contact_samples), index + 2)
            filtered_hands.append([
                sum(hand_contact_samples[item][side]
                    for item in range(left, right)) * 2 >= right - left
                for side in (0, 1)
            ])
        hand_contact_samples = filtered_hands
    previous: dict[str, Quaternion] = {}
    frames = []
    for sample_index, seconds in enumerate(times):
        source_frame = min(end, start + seconds * source_fps)
        whole = math.floor(source_frame)
        scene.frame_set(int(whole), subframe=source_frame - whole)
        bpy.context.view_layer.update()
        feet = [min(
            pose_point(armature, f"{side}foot").z,
            pose_point(armature, f"{side}toes").z,
        ) for side in ("l", "r")]
        contacts = list(contact_samples[sample_index])
        hand_contacts = list(hand_contact_samples[sample_index])

        authored_rotations = dict(fallback_authored)
        runtime_rotations = {
            name: authored_to_runtime_quaternion(quat)
            for name, quat in fallback_authored.items()
        }
        for target_name, chain in CMU_CHAINS.items():
            authored = project_to_eva_joint(
                target_name,
                group_delta(armature, chain, reference_rotations[target_name]),
            )
            authored_rotations[target_name] = authored
            runtime_rotations[target_name] = authored_to_runtime_quaternion(
                authored
            )
        contact_plane = common_reachable_contact_plane(
            target_pivots, runtime_rotations["torso_lower"]
        )
        for side in ("l", "r"):
            arm_goal = source_limb_goal(
                armature, "thorax", f"{side}humerus",
                f"{side}radius", f"{side}wrist"
            )
            arm_goal = (
                authored_to_runtime_vector(arm_goal[0]), arm_goal[1],
                authored_to_runtime_vector(arm_goal[2]),
            )
            reference_arm = reference_limb_goals[f"arm_{side}"]
            reference_arm = (
                authored_to_runtime_vector(reference_arm[0]), reference_arm[1],
                authored_to_runtime_vector(reference_arm[2]),
            )
            arm_direction, arm_reach, arm_pole = relative_limb_goal(
                arm_goal, reference_arm,
                target_pivots[f"arm_{side}"],
                target_pivots[f"hand_{side}"], arm_scale,
            )
            upper, lower = solve_target_limb(
                target_pivots[f"arm_{side}"],
                target_pivots[f"forearm_{side}"],
                target_pivots[f"hand_{side}"],
                arm_direction, arm_reach, arm_pole,
            )
            runtime_rotations[f"arm_{side}"] = upper
            runtime_rotations[f"forearm_{side}"] = lower
            authored_rotations[f"arm_{side}"] = \
                runtime_to_authored_quaternion(upper)
            authored_rotations[f"forearm_{side}"] = \
                runtime_to_authored_quaternion(lower)

            leg_goal = source_limb_goal(
                armature, "root", f"{side}femur",
                f"{side}tibia", f"{side}foot"
            )
            leg_goal = (
                authored_to_runtime_vector(leg_goal[0]), leg_goal[1],
                authored_to_runtime_vector(leg_goal[2]),
            )
            reference_leg = reference_limb_goals[f"leg_{side}"]
            reference_leg = (
                authored_to_runtime_vector(reference_leg[0]), reference_leg[1],
                authored_to_runtime_vector(reference_leg[2]),
            )
            leg_direction, leg_reach, leg_pole = relative_limb_goal(
                leg_goal, reference_leg,
                target_pivots[f"leg_{side}"],
                target_pivots[f"foot_{side}"], leg_scale,
            )
            leg_direction, leg_reach = pin_leg_endpoint(
                leg_direction, leg_reach, target_pivots,
                runtime_rotations["torso_lower"], side,
                contacts[0 if side == "l" else 1],
                contact_plane,
            )
            thigh, shin = solve_target_limb(
                target_pivots[f"leg_{side}"],
                target_pivots[f"shin_{side}"],
                target_pivots[f"foot_{side}"],
                leg_direction, leg_reach, leg_pole,
            )
            # The analytic two-bone solve already operates on the EVA's own
            # rest vectors and preserves the requested ankle endpoint.  An
            # Euler projection here moves that endpoint after IK, producing
            # the high planted foot seen in earlier labs.  Keep the exact
            # quaternion solution; target-space pole/reach limits above are
            # the mechanical constraint authority.
            runtime_rotations[f"leg_{side}"] = thigh
            runtime_rotations[f"shin_{side}"] = shin
            authored_rotations[f"leg_{side}"] = \
                runtime_to_authored_quaternion(thigh)
            authored_rotations[f"shin_{side}"] = \
                runtime_to_authored_quaternion(shin)
            parent = (runtime_rotations["torso_lower"]
                      @ runtime_rotations[f"leg_{side}"]
                      @ runtime_rotations[f"shin_{side}"])
            runtime_foot = project_foot_for_contact(
                runtime_rotations[f"foot_{side}"], parent,
                contacts[0 if side == "l" else 1],
            )
            runtime_rotations[f"foot_{side}"] = runtime_foot
            authored_rotations[f"foot_{side}"] = \
                runtime_to_authored_quaternion(runtime_foot)

        ordered = []
        for name in bone_order:
            quat = authored_rotations[name]
            old = previous.get(name)
            if old is not None and old.dot(quat) < 0.0:
                quat = Quaternion((-quat.w, -quat.x, -quat.y, -quat.z))
            previous[name] = quat.copy()
            ordered.append(rounded_quaternion(quat))

        source_root = pose_point(armature, "root") - start_root
        root = target_vector(source_root) * source_to_meters
        if loop:
            root.x = 0.0
            root.z = 0.0
        baseline = max(target_pivots["foot_l"].y,
                       target_pivots["foot_r"].y)
        # Root-height authority is derived from the target chain for every
        # frame, including aerial transitions.  That prevents a long rigid
        # swing foot from cutting the floor between contact samples.
        correction = {
            side: (baseline - target_ankle_position(
                runtime_rotations, target_pivots, side
            ).y) / MODEL_UNITS_PER_SOURCE_METRE
            for side in ("l", "r")
        }
        if any(contacts):
            root.y = max(
                correction[side]
                for side, planted in zip(("l", "r"), contacts)
                if planted
            ) + 0.018
        else:
            root.y = max(root.y, *correction.values()) + 0.018
        frames.append({
            "root_m": [round(float(value), 7) for value in root],
            "root_yaw_radians": round(
                float(-(yaw_samples[sample_index] - yaw_samples[0])), 7
            ),
            "rotation_wxyz": ordered,
            "foot_contact": contacts,
            "hand_contact": hand_contacts,
            "foot_height_m": [
                round((height - floor) * source_to_meters, 6)
                for height in feet
            ],
        })
    source_root_travel = Vector((0.0, 0.0, 0.0))
    root_travel = Vector((0.0, 0.0, 0.0))
    if loop:
        scene.frame_set(int(end))
        bpy.context.view_layer.update()
        source_root_travel = target_vector(
            pose_point(armature, "root") - start_root
        ) * source_to_meters
        close_loop(frames)
        root_travel = fit_loop_root_travel(
            frames, bone_order, target_pivots, source_root_travel
        )
    lock_contact_feet(frames, bone_order, target_pivots, root_travel)
    lock_contact_hands(frames, bone_order, target_pivots, root_travel,
                       move_root=True)
    lock_contact_feet(frames, bone_order, target_pivots, root_travel)
    lock_contact_hands(frames, bone_order, target_pivots, root_travel,
                       move_root=False)
    if prune_unstable_hand_contacts(
            frames, bone_order, target_pivots, root_travel) > 0:
        lock_contact_hands(frames, bone_order, target_pivots, root_travel,
                           move_root=False)
    output = {
        "duration_seconds": round(duration, 6),
        "loop": loop,
        "role": ("candidate_locomotion" if loop
                 else "candidate_airborne" if kind == "jump"
                 else "candidate_trajectory" if kind == "trajectory"
                 else "candidate_prone" if kind == "prone"
                 else "candidate_posture_transition"
                 if kind == "posture_transition"
                 else "candidate_combat"),
        "source_frame_range": [int(start), int(end)],
        "frames": frames,
    }
    if loop:
        output["closed_endpoint"] = True
        output["root_travel_m"] = [
            round(float(root_travel.x), 7),
            round(float(root_travel.y), 7),
            round(float(root_travel.z), 7),
        ]
        output["source_root_travel_m"] = [
            round(float(source_root_travel.x), 7),
            round(float(source_root_travel.y), 7),
            round(float(source_root_travel.z), 7),
        ]
        output["retargeted_stride_meters"] = round(
            math.hypot(root_travel.x, root_travel.z), 7
        )
    for key in ("stride_meters", "speed_mps", "peak_frame", "peak_energy"):
        if key in definition:
            output[key] = definition[key]
    if kind == "jump":
        output["phase_frame_indices"] = {
            label: max(0, min(len(frames) - 1, int(round(
                (float(definition[f"{label}_frame"]) - start)
                / source_fps * SAMPLE_RATE
            ))))
            for label in ("takeoff", "apex", "landing")
        }
    return output


def main() -> None:
    args = parse_args()
    root = Path.cwd()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    base = json.loads(args.base_motion_db.read_text(encoding="utf-8"))
    bone_order = list(base["bones"])
    target_pivots = runtime_target_pivots(load_target_pivots(args.target_geo))
    reference_cache = {}
    # Carry one already-reviewed neutral frame sequence so the exact 3D lab
    # has a stable dimensional/ground reference.  It is not a CMU candidate.
    output = {"idle": base["clips"]["idle"]}
    provenance = []
    for capture in manifest["captures"]:
        source = (root / capture["source"]).resolve()
        analysis_path = (root / capture["analysis"]).resolve()
        if not source.is_file() or not analysis_path.is_file():
            raise SystemExit(f"missing capture input: {source} / {analysis_path}")
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        neutral_path = (root / capture.get(
            "neutral_source", manifest["neutral_source"]
        )).resolve()
        cache_key = str(neutral_path)
        if cache_key not in reference_cache:
            reference_cache[cache_key] = reference_contract(neutral_path)
        (reference_rotations, reference_limb_goals,
         reference_source_to_meters) = reference_cache[cache_key]
        armature = import_bvh(source)
        _capture_scale, floor = capture_scale_and_floor(armature)
        source_to_meters = reference_source_to_meters
        kind = capture["kind"]
        fallback_clip = (
            "knife_idle" if kind == "sword"
            else "punch_jab" if kind == "punch" else "idle"
        )
        fallback = base["clips"][fallback_clip]["frames"][0]["rotation_wxyz"]
        for semantic_name, segment_id in capture["clips"].items():
            definition = find_definition(analysis, kind, segment_id)
            clip = sample_segment(
                armature, definition, kind,
                reference_rotations, reference_limb_goals,
                target_pivots, bone_order, fallback,
                source_to_meters, floor,
            )
            clip["source_capture"] = source.name
            clip["source_segment"] = segment_id
            output[semantic_name] = clip
        provenance.append({
            "file": source.name,
            "kind": kind,
            "source_to_meters": round(source_to_meters, 8),
            "floor_source_units": round(floor, 8),
        })
    document = {
        "schema": 2,
        "coordinate_system": "bedrock_x_right_y_up_z_back",
        "quaternion_order": "wxyz",
        "sample_rate": SAMPLE_RATE,
        "sources": [{
            "name": "Carnegie Mellon University Graphics Lab Motion Capture Database",
            "url": "https://mocap.cs.cmu.edu/",
            "license": "CMU database terms: free use; acknowledge source",
        }],
        "bones": bone_order,
        "captures": provenance,
        "clips": output,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA CMU candidate DB: clips={len(output)} bones={len(bone_order)} "
        f"bytes={args.output.stat().st_size} output={args.output}"
    )


if __name__ == "__main__":
    main()
