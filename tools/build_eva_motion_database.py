#!/usr/bin/env python3
"""Retarget a CC0 humanoid library into Project SEELE's runtime motion DB.

The output stores normalized quaternions instead of Bedrock Euler curves.  It
is consumed by the render-rate EVA motion engine, which blends/inertializes
poses independently from Minecraft's 20 Hz simulation clock.

Run with Blender and the active local EVA geometry as the target contract::

    blender --background --python tools/build_eva_motion_database.py -- \
        --source library.glb --target-geo eva_unit01.geo.json \
        --output eva_humanoid_v2.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector


SAMPLE_RATE = 30.0
MODEL_UNITS_PER_SOURCE_METRE = 112.0

CLIPS = {
    "idle": ("Idle_Loop_Armature", True, "idle"),
    "walk": ("Walk_Loop_Armature", True, "locomotion"),
    "formal_walk": ("Walk_Formal_Loop_Armature", True, "locomotion"),
    "jog": ("Jog_Fwd_Loop_Armature", True, "locomotion"),
    "sprint": ("Sprint_Loop_Armature", True, "locomotion"),
    "crouch_idle": ("Crouch_Idle_Loop_Armature", True, "crouch"),
    "crouch_walk": ("Crouch_Fwd_Loop_Armature", True, "crouch"),
    "jump_start": ("Jump_Start_Armature", False, "airborne"),
    "jump_loop": ("Jump_Loop_Armature", True, "airborne"),
    "jump_land": ("Jump_Land_Armature", False, "airborne"),
    "punch_jab": ("Punch_Jab_Armature", False, "combat"),
    "punch_cross": ("Punch_Cross_Armature", False, "combat"),
    "knife_idle": ("Sword_Idle_Armature", True, "combat"),
    "knife_attack": ("Sword_Attack_Armature", False, "combat"),
    "rifle_idle": ("Pistol_Idle_Loop_Armature", True, "combat"),
    "rifle_shoot": ("Pistol_Shoot_Armature", False, "combat"),
}

CLIPS_SECONDARY = {
    "punch_hook": ("Melee_Hook_Armature", False, "combat"),
    "punch_hook_recovery": ("Melee_Hook_Rec_Armature", False, "combat"),
    "knife_regular_a": ("Sword_Regular_A_Armature", False, "combat"),
    "knife_regular_b": ("Sword_Regular_B_Armature", False, "combat"),
    "knife_regular_c": ("Sword_Regular_C_Armature", False, "combat"),
    "knife_combo": ("Sword_Regular_Combo_Armature", False, "combat"),
    "knife_heavy_combo": ("Sword_Heavy_Combo_Armature", False, "combat"),
    "knife_dash": ("Sword_Dash_Armature", False, "combat"),
    "shield_dash": ("Shield_Dash_Armature", False, "combat"),
    "ninja_jump_start": ("NinjaJump_Start_Armature", False, "airborne"),
    "ninja_jump_loop": ("NinjaJump_Idle_Loop_Armature", True, "airborne"),
    "ninja_jump_land": ("NinjaJump_Land_Armature", False, "airborne"),
    "slide_start": ("Slide_Start_Armature", False, "locomotion"),
    "slide_loop": ("Slide_Loop_Armature", True, "locomotion"),
    "slide_exit": ("Slide_Exit_Armature", False, "locomotion"),
}

# Each target entry consumes a consecutive source chain.  Chain collapsing is
# intentional: the current EVA mesh has two torso joints and no clavicle bone,
# while the CC0 humanoid has four spine/neck segments and clavicles.
CHAINS = {
    "torso_lower": ("pelvis", "spine_01"),
    "torso_upper": ("spine_02", "spine_03"),
    "head": ("neck_01", "Head"),
    "arm_l": ("clavicle_l", "upperarm_l"),
    "forearm_l": ("lowerarm_l",),
    "hand_l": ("hand_l",),
    "arm_r": ("clavicle_r", "upperarm_r"),
    "forearm_r": ("lowerarm_r",),
    "hand_r": ("hand_r",),
    "leg_l": ("thigh_l",),
    "shin_l": ("calf_l",),
    "foot_l": ("foot_l", "ball_l"),
    "leg_r": ("thigh_r",),
    "shin_r": ("calf_r",),
    "foot_r": ("foot_r", "ball_r"),
}

for side in ("l", "r"):
    for source, target in (
        ("index", "index"),
        ("middle", "middle"),
        ("ring", "ring"),
        ("pinky", "little"),
        ("thumb", "thumb"),
    ):
        CHAINS[f"finger_{target}_{side}"] = (f"{source}_01_{side}",)
        CHAINS[f"finger_{target}_tip_{side}"] = (f"{source}_02_{side}",)
        CHAINS[f"finger_{target}_distal_{side}"] = (f"{source}_03_{side}",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--source-secondary", type=Path)
    parser.add_argument("--target-geo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--preview-output", type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.actions, bpy.data.armatures, bpy.data.meshes):
        for datablock in tuple(datablocks):
            datablocks.remove(datablock)


def import_source(path: Path) -> bpy.types.Object:
    suffix = path.suffix.lower()
    if suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=False)
    else:
        raise SystemExit(f"unsupported source type: {path}")
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise SystemExit(f"expected one armature, found {len(armatures)}")
    return armatures[0]


def group_local_rotation(
    armature: bpy.types.Object, chain: tuple[str, ...]
) -> tuple[Matrix, Matrix]:
    first = armature.pose.bones[chain[0]]
    last = armature.pose.bones[chain[-1]]
    parent_pose = first.parent.matrix if first.parent else Matrix.Identity(4)
    parent_rest = (
        first.parent.bone.matrix_local if first.parent else Matrix.Identity(4)
    )
    pose_local = parent_pose.inverted_safe() @ last.matrix
    return pose_local.to_3x3().normalized(), parent_rest


def group_delta(
    armature: bpy.types.Object,
    chain: tuple[str, ...],
    reference_local: Matrix,
) -> Quaternion:
    pose_local, parent_rest = group_local_rotation(armature, chain)
    delta_parent = pose_local @ reference_local.inverted_safe()

    # Express the parent-local delta in armature axes, then change coordinates
    # from Blender (X right, Y back, Z up) to Bedrock (X right, Y up, Z back).
    parent_basis = parent_rest.to_3x3().normalized()
    delta_armature = parent_basis @ delta_parent @ parent_basis.inverted_safe()
    basis = Matrix(((1.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0),
                    (0.0, -1.0, 0.0)))
    target = basis @ delta_armature @ basis.inverted_safe()
    quat = target.to_quaternion()
    quat.normalize()
    return quat


def target_vector(vector: Vector) -> Vector:
    return Vector((vector.x, vector.z, -vector.y))


def load_target_pivots(path: Path) -> dict[str, Vector]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    geometries = payload.get("minecraft:geometry", [])
    if not geometries:
        raise SystemExit(f"target geo has no geometry: {path}")
    pivots = {}
    for bone in geometries[0].get("bones", []):
        if "pivot" in bone:
            pivots[bone["name"]] = Vector(tuple(float(v) for v in bone["pivot"]))
    return pivots


def source_limb_goal(
    armature: bpy.types.Object,
    parent_name: str,
    start_name: str,
    middle_name: str,
    end_name: str,
) -> tuple[Vector, float, Vector]:
    start = armature.pose.bones[start_name].matrix.translation
    middle = armature.pose.bones[middle_name].matrix.translation
    end = armature.pose.bones[end_name].matrix.translation
    parent_pose = armature.pose.bones[parent_name].matrix.to_3x3().normalized()
    parent_rest = (
        armature.data.bones[parent_name].matrix_local.to_3x3().normalized()
    )
    # Remove the animated parent rotation while retaining armature/world axes.
    # Transforming points into the Blender bone's local coordinates would also
    # import its arbitrary roll, turning an idle downward leg into a sideways
    # vector before the Bedrock basis conversion.
    remove_parent_animation = (
        parent_pose @ parent_rest.inverted_safe()
    ).inverted_safe()
    source_upper = (
        armature.data.bones[middle_name].head_local
        - armature.data.bones[start_name].head_local
    ).length
    source_lower = (
        armature.data.bones[end_name].head_local
        - armature.data.bones[middle_name].head_local
    ).length
    reach_vector = remove_parent_animation @ (end - start)
    reach_length = reach_vector.length
    if reach_length < 1.0e-7:
        return Vector((0.0, -1.0, 0.0)), 0.05, Vector((0.0, 0.0, -1.0))
    direction_source = reach_vector.normalized()
    pole_source = remove_parent_animation @ (middle - start)
    pole_source -= direction_source * pole_source.dot(direction_source)
    if pole_source.length < 1.0e-6:
        pole_source = Vector((0.0, 1.0, 0.0))
    return (
        target_vector(direction_source).normalized(),
        clamp(reach_length / (source_upper + source_lower), 0.05, 0.995),
        target_vector(pole_source).normalized(),
    )


def solve_target_limb(
    start: Vector,
    middle: Vector,
    end: Vector,
    direction: Vector,
    reach_fraction: float,
    pole: Vector,
) -> tuple[Quaternion, Quaternion]:
    upper_rest = middle - start
    lower_rest = end - middle
    upper_length = upper_rest.length
    lower_length = lower_rest.length
    distance = clamp(
        reach_fraction * (upper_length + lower_length),
        abs(upper_length - lower_length) + 1.0e-4,
        upper_length + lower_length - 1.0e-4,
    )
    direction = direction.normalized()
    along = (
        upper_length * upper_length
        - lower_length * lower_length
        + distance * distance
    ) / (2.0 * distance)
    bend = math.sqrt(max(0.0, upper_length * upper_length - along * along))
    pole = pole - direction * pole.dot(direction)
    if pole.length < 1.0e-6:
        pole = Vector((0.0, 0.0, -1.0))
        pole -= direction * pole.dot(direction)
    pole.normalize()
    wanted_middle = start + direction * along + pole * bend
    wanted_end = start + direction * distance

    wanted_upper = wanted_middle - start
    first = upper_rest.rotation_difference(wanted_upper)
    wanted_lower_parent = wanted_end - wanted_middle
    wanted_lower_local = first.conjugated() @ wanted_lower_parent
    second = lower_rest.rotation_difference(wanted_lower_local)
    first.normalize()
    second.normalize()
    return first, second


def relative_limb_goal(
    current: tuple[Vector, float, Vector],
    reference: tuple[Vector, float, Vector],
    target_start: Vector,
    target_end: Vector,
    component_scale: Vector,
) -> tuple[Vector, float, Vector]:
    current_direction, current_reach, current_pole = current
    reference_direction, reference_reach, _reference_pole = reference
    target_rest_direction = (target_end - target_start).normalized()
    normalized_delta = (current_direction * current_reach
                        - reference_direction * reference_reach)
    normalized_delta.x *= component_scale.x
    normalized_delta.y *= component_scale.y
    normalized_delta.z *= component_scale.z
    goal = target_rest_direction * 0.995 + normalized_delta
    return goal.normalized(), clamp(goal.length, 0.08, 0.995), current_pole


def limb_component_scales(action_name: str) -> tuple[Vector, Vector]:
    """Return (arm, leg) XYZ motion-amplitude profiles in target axes."""
    arm = Vector((0.88, 0.95, 0.92))
    leg = Vector((0.12, 0.96, 0.76))
    if "Crouch_Idle" in action_name:
        leg = Vector((0.10, 0.92, 0.30))
    elif "Crouch_Fwd" in action_name:
        leg = Vector((0.11, 0.95, 0.58))
    elif "Jump" in action_name or "Land" in action_name:
        leg = Vector((0.11, 0.98, 0.68))
    elif "Sprint" in action_name or "Jog" in action_name:
        leg = Vector((0.10, 0.98, 0.82))
    elif "Sword" in action_name or "Melee" in action_name:
        leg = Vector((0.12, 0.96, 0.62))
    elif "Slide" in action_name:
        leg = Vector((0.10, 0.92, 0.55))
    return arm, leg


def target_ankle_position(
    rotations: dict[str, Quaternion],
    pivots: dict[str, Vector],
    side: str,
) -> Vector:
    torso_pivot = pivots["torso_lower"]
    hip = pivots[f"leg_{side}"]
    knee_rest = pivots[f"shin_{side}"]
    ankle_rest = pivots[f"foot_{side}"]
    hip_rotation = rotations[f"leg_{side}"]
    knee_rotation = rotations[f"shin_{side}"]
    upper = hip_rotation @ (knee_rest - hip)
    knee = hip + upper
    lower = (hip_rotation @ knee_rotation) @ (ankle_rest - knee_rest)
    ankle = knee + lower
    return torso_pivot + rotations["torso_lower"] @ (ankle - torso_pivot)


def rounded_quaternion(quat: Quaternion) -> list[float]:
    # WXYZ is explicit in the schema. Runtime continuity uses hemisphere
    # correction, so the exporter keeps no Euler wrapping discontinuities.
    return [round(float(quat.w), 7), round(float(quat.x), 7),
            round(float(quat.y), 7), round(float(quat.z), 7)]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def project_to_eva_joint(name: str, quat: Quaternion) -> Quaternion:
    """Project human motion onto the mechanical limits of the EVA rig.

    The source skeleton has arbitrary bone roll. A mathematically exact
    transfer therefore puts large twist and side-bend components onto target
    knees/elbows whose rigid mesh is a hinge. Long EVA limbs amplify a small
    human roll into the familiar broken/outer-splayed pose. This anatomical
    projection keeps real timing while enforcing the target joint contract.
    """
    euler = quat.to_euler("XYZ")
    degrees = [math.degrees(float(value)) for value in euler]
    if name.startswith("shin_"):
        degrees = [clamp(degrees[0], -8.0, 128.0), 0.0, 0.0]
    elif name.startswith("foot_"):
        degrees = [clamp(degrees[0], -58.0, 58.0),
                   clamp(degrees[1], -6.0, 6.0),
                   clamp(degrees[2], -8.0, 8.0)]
    elif name.startswith("leg_"):
        degrees = [clamp(degrees[0], -76.0, 68.0),
                   clamp(degrees[1], -8.0, 8.0),
                   clamp(degrees[2], -7.0, 7.0)]
    elif name.startswith("forearm_"):
        degrees = [clamp(degrees[0], -138.0, 38.0), 0.0, 0.0]
    elif name == "torso_lower":
        degrees = [clamp(degrees[0], -25.0, 25.0),
                   clamp(degrees[1], -10.0, 10.0),
                   clamp(degrees[2], -8.0, 8.0)]
    elif name == "torso_upper":
        degrees = [clamp(degrees[0], -36.0, 36.0),
                   clamp(degrees[1], -18.0, 18.0),
                   clamp(degrees[2], -12.0, 12.0)]
    elif name == "head":
        degrees = [clamp(degrees[0], -35.0, 35.0),
                   clamp(degrees[1], -30.0, 30.0),
                   clamp(degrees[2], -15.0, 15.0)]
    else:
        return quat
    projected = Euler(tuple(math.radians(value) for value in degrees),
                      "XYZ").to_quaternion()
    projected.normalize()
    return projected


def project_foot_for_contact(raw_foot: Quaternion,
                             parent_global: Quaternion,
                             planted: bool) -> Quaternion:
    raw_global = parent_global @ raw_foot
    if planted:
        desired_global = Quaternion((1.0, 0.0, 0.0, 0.0))
    else:
        euler = raw_global.to_euler("XYZ")
        # A human can point the toe down deeply during swing; the EVA foot is
        # several blocks long, so the same plantar-flexion sweeps through the
        # floor near toe-off. Preserve toe-up clearance and cap toe-down.
        pitch = clamp(math.degrees(float(euler.x)), 0.0, 12.0)
        desired_global = Euler((math.radians(pitch), 0.0, 0.0),
                               "XYZ").to_quaternion()
    result = parent_global.conjugated() @ desired_global
    result.normalize()
    return result


def authored_to_runtime_quaternion(quat: Quaternion) -> Quaternion:
    euler = quat.to_euler("XYZ")
    result = Euler((-euler.x, -euler.y, euler.z), "XYZ").to_quaternion()
    result.normalize()
    return result


def runtime_to_authored_quaternion(quat: Quaternion) -> Quaternion:
    return authored_to_runtime_quaternion(quat)


def authored_to_runtime_vector(vector: Vector) -> Vector:
    return Vector((-vector.x, vector.y, vector.z))


def runtime_target_pivots(pivots: dict[str, Vector]) -> dict[str, Vector]:
    return {
        name: authored_to_runtime_vector(pivot)
        for name, pivot in pivots.items()
    }


def common_reachable_contact_plane(
    pivots: dict[str, Vector], torso_rotation: Quaternion
) -> float:
    torso_pivot = pivots["torso_lower"]
    plane = max(pivots["foot_l"].y, pivots["foot_r"].y)
    for side in ("l", "r"):
        hip = pivots[f"leg_{side}"]
        knee = pivots[f"shin_{side}"]
        ankle = pivots[f"foot_{side}"]
        total = (knee - hip).length + (ankle - knee).length
        world_hip = torso_pivot + torso_rotation @ (hip - torso_pivot)
        plane = max(plane, world_hip.y - total * 0.99999)
    return plane


def pin_leg_endpoint(
    direction: Vector,
    reach: float,
    pivots: dict[str, Vector],
    torso_rotation: Quaternion,
    side: str,
    planted: bool,
    contact_plane: float,
) -> tuple[Vector, float]:
    hip = pivots[f"leg_{side}"]
    knee = pivots[f"shin_{side}"]
    ankle = pivots[f"foot_{side}"]
    total = (knee - hip).length + (ankle - knee).length
    local_goal = hip + direction * reach * total
    torso_pivot = pivots["torso_lower"]
    world_hip = torso_pivot + torso_rotation @ (hip - torso_pivot)
    world_goal = torso_pivot + torso_rotation @ (local_goal - torso_pivot)
    minimum_height = contact_plane if planted else contact_plane + 0.8
    if planted:
        world_goal.y = minimum_height
    elif world_goal.y < minimum_height:
        world_goal.y = minimum_height
    vertical = world_goal.y - world_hip.y
    horizontal = Vector((world_goal.x - world_hip.x, 0.0,
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


def close_loop(frames: list[dict]) -> None:
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
    for frame_index, frame in enumerate(frames):
        amount = frame_index / last_index
        frame["root_m"][1] = round(
            float(frame["root_m"][1]) - root_delta * amount, 7
        )
    frames[-1]["foot_contact"] = list(frames[0]["foot_contact"])


def sample_action(
    scene: bpy.types.Scene,
    armature: bpy.types.Object,
    action: bpy.types.Action,
    loop: bool,
    reference_rotations: dict[str, Matrix],
    reference_pelvis: Vector,
    reference_limb_goals: dict[str, tuple[Vector, float, Vector]],
    target_pivots: dict[str, Vector],
) -> dict:
    source_fps = scene.render.fps / scene.render.fps_base
    start, end = (float(value) for value in action.frame_range)
    duration = max(1.0 / source_fps, (end - start) / source_fps)
    if loop:
        frame_count = max(2, int(round(duration * SAMPLE_RATE)))
        times = [index / SAMPLE_RATE for index in range(frame_count)]
    else:
        frame_count = max(2, int(round(duration * SAMPLE_RATE)) + 1)
        times = [min(duration, index / SAMPLE_RATE) for index in range(frame_count)]

    armature.animation_data_create()
    armature.animation_data.action = action
    arm_scale, leg_scale = limb_component_scales(action.name)
    frames = []
    contact_samples = []
    previous_toes: list[Vector] | None = None
    for seconds in times:
        source_frame = start + seconds * source_fps
        whole = math.floor(source_frame)
        scene.frame_set(int(whole), subframe=source_frame - whole)
        bpy.context.view_layer.update()
        toes = [target_vector(
            armature.pose.bones[f"ball_{side}"].matrix.translation
        ) for side in ("l", "r")]
        speeds = ([0.0, 0.0] if previous_toes is None else [
            (point - old).length * SAMPLE_RATE
            for point, old in zip(toes, previous_toes)
        ])
        contact_samples.append([
            point.y <= 0.08 and speed <= 0.50
            for point, speed in zip(toes, speeds)
        ])
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
    previous: dict[str, Quaternion] = {}
    for sample_index, seconds in enumerate(times):
        source_frame = start + seconds * source_fps
        whole = math.floor(source_frame)
        scene.frame_set(int(whole), subframe=source_frame - whole)
        bpy.context.view_layer.update()

        left_foot = target_vector(
            armature.pose.bones["ball_l"].matrix.translation
        )
        right_foot = target_vector(
            armature.pose.bones["ball_r"].matrix.translation
        )
        contacts = list(contact_samples[sample_index])

        authored_rotations = {}
        runtime_rotations = {}
        for target_name, chain in CHAINS.items():
            authored = group_delta(
                armature, chain, reference_rotations[target_name]
            )
            authored = project_to_eva_joint(target_name, authored)
            authored_rotations[target_name] = authored
            runtime_rotations[target_name] = authored_to_runtime_quaternion(
                authored
            )
        contact_plane = common_reachable_contact_plane(
            target_pivots, runtime_rotations["torso_lower"]
        )

        for side in ("l", "r"):
            arm_goal = source_limb_goal(
                armature, "spine_03", f"upperarm_{side}",
                f"lowerarm_{side}", f"hand_{side}"
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
                arm_goal,
                reference_arm,
                target_pivots[f"arm_{side}"],
                target_pivots[f"hand_{side}"],
                arm_scale,
            )
            arm_first, arm_second = solve_target_limb(
                target_pivots[f"arm_{side}"],
                target_pivots[f"forearm_{side}"],
                target_pivots[f"hand_{side}"],
                arm_direction, arm_reach, arm_pole,
            )
            runtime_rotations[f"arm_{side}"] = arm_first
            runtime_rotations[f"forearm_{side}"] = arm_second
            authored_rotations[f"arm_{side}"] = \
                runtime_to_authored_quaternion(arm_first)
            authored_rotations[f"forearm_{side}"] = \
                runtime_to_authored_quaternion(arm_second)

            leg_goal = source_limb_goal(
                armature, "pelvis", f"thigh_{side}",
                f"calf_{side}", f"foot_{side}"
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
                leg_goal,
                reference_leg,
                target_pivots[f"leg_{side}"],
                target_pivots[f"foot_{side}"],
                leg_scale,
            )
            leg_direction, leg_reach = pin_leg_endpoint(
                leg_direction, leg_reach, target_pivots,
                runtime_rotations["torso_lower"], side,
                contacts[0 if side == "l" else 1], contact_plane,
            )
            leg_first, leg_second = solve_target_limb(
                target_pivots[f"leg_{side}"],
                target_pivots[f"shin_{side}"],
                target_pivots[f"foot_{side}"],
                leg_direction, leg_reach, leg_pole,
            )
            runtime_rotations[f"leg_{side}"] = leg_first
            runtime_rotations[f"shin_{side}"] = leg_second
            authored_rotations[f"leg_{side}"] = \
                runtime_to_authored_quaternion(leg_first)
            authored_rotations[f"shin_{side}"] = \
                runtime_to_authored_quaternion(leg_second)
            foot_parent = (runtime_rotations["torso_lower"]
                           @ runtime_rotations[f"leg_{side}"]
                           @ runtime_rotations[f"shin_{side}"])
            runtime_foot = project_foot_for_contact(
                runtime_rotations[f"foot_{side}"], foot_parent,
                contacts[0 if side == "l" else 1],
            )
            runtime_rotations[f"foot_{side}"] = runtime_foot
            authored_rotations[f"foot_{side}"] = \
                runtime_to_authored_quaternion(runtime_foot)

        rotations = []
        for target_name in CHAINS:
            quat = authored_rotations[target_name]
            old = previous.get(target_name)
            if old is not None and old.dot(quat) < 0.0:
                quat = Quaternion((-quat.w, -quat.x, -quat.y, -quat.z))
            previous[target_name] = quat.copy()
            rotations.append(rounded_quaternion(quat))

        pelvis_delta = (
            armature.pose.bones["pelvis"].matrix.translation
            - reference_pelvis
        )
        root = target_vector(pelvis_delta)
        baseline = max(target_pivots["foot_l"].y,
                       target_pivots["foot_r"].y)
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
        frames.append(
            {
                "root_m": [round(float(value), 7) for value in root],
                "rotation_wxyz": rotations,
                "foot_contact": contacts,
                "foot_height_m": [round(float(left_foot.y), 6),
                                  round(float(right_foot.y), 6)],
            }
        )
    armature.animation_data.action = None
    if loop:
        close_loop(frames)
    result = {
        "duration_seconds": round(duration, 6),
        "loop": loop,
        "frames": frames,
    }
    if loop:
        result["closed_endpoint"] = True
    return result


def export_library(
    source: Path,
    clip_definitions: dict[str, tuple[str, bool, str]],
    neutral_action_name: str,
    target_pivots: dict[str, Vector],
) -> dict[str, dict]:
    reset_scene()
    armature = import_source(source)
    scene = bpy.context.scene
    missing_bones = sorted(
        {bone for chain in CHAINS.values() for bone in chain}
        - set(armature.pose.bones.keys())
    )
    if missing_bones:
        raise SystemExit("missing source bones: " + ", ".join(missing_bones))

    def resolve_action(name: str) -> bpy.types.Action | None:
        action = bpy.data.actions.get(name)
        if action is None and name.endswith("_Armature"):
            action = bpy.data.actions.get(name[:-len("_Armature")])
        return action

    reference_action = resolve_action(neutral_action_name)
    if reference_action is None:
        raise SystemExit(f"missing neutral reference action: {neutral_action_name}")
    armature.animation_data_create()
    armature.animation_data.action = reference_action
    scene.frame_set(int(reference_action.frame_range[0]))
    bpy.context.view_layer.update()
    reference_rotations = {
        target: group_local_rotation(armature, chain)[0].copy()
        for target, chain in CHAINS.items()
    }
    reference_pelvis = armature.pose.bones["pelvis"].matrix.translation.copy()
    reference_limb_goals = {}
    for side in ("l", "r"):
        reference_limb_goals[f"arm_{side}"] = source_limb_goal(
            armature, "spine_03", f"upperarm_{side}",
            f"lowerarm_{side}", f"hand_{side}"
        )
        reference_limb_goals[f"leg_{side}"] = source_limb_goal(
            armature, "pelvis", f"thigh_{side}",
            f"calf_{side}", f"foot_{side}"
        )
    armature.animation_data.action = None

    output = {}
    for semantic_name, (action_name, loop, role) in clip_definitions.items():
        action = resolve_action(action_name)
        if action is None:
            raise SystemExit(f"missing action: {action_name}")
        clip = sample_action(
            scene,
            armature,
            action,
            loop,
            reference_rotations,
            reference_pelvis,
            reference_limb_goals,
            target_pivots,
        )
        clip["source_action"] = action_name
        clip["role"] = role
        output[semantic_name] = clip
    return output


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    if not source.is_file():
        raise SystemExit(f"motion source not found: {source}")
    # The imported EVA body mesh is authored in its standing silhouette, not
    # a humanoid T-pose. Calibrate every library against its own idle first
    # frame so zero rotation means the EVA's authored rest shape.
    target_geo = args.target_geo.resolve()
    if not target_geo.is_file():
        raise SystemExit(f"target geo not found: {target_geo}")
    # Solve limbs in the actual Gecko runtime space (reflected X), then
    # convert the result back to authored Bedrock rotations for storage.
    target_pivots = runtime_target_pivots(load_target_pivots(target_geo))
    needed_pivots = {
        f"{part}_{side}"
        for side in ("l", "r")
        for part in ("arm", "forearm", "hand", "leg", "shin", "foot")
    }
    missing_pivots = sorted(needed_pivots - set(target_pivots))
    if missing_pivots:
        raise SystemExit("missing target pivots: " + ", ".join(missing_pivots))
    output_clips = export_library(
        source, CLIPS, "Idle_Loop_Armature", target_pivots
    )
    sources = [
        {
            "name": "Quaternius Universal Animation Library Standard",
            "url": "https://quaternius.com/packs/universalanimationlibrary.html",
            "license": "CC0-1.0",
        }
    ]
    if args.source_secondary is not None:
        secondary = args.source_secondary.resolve()
        if not secondary.is_file():
            raise SystemExit(f"secondary motion source not found: {secondary}")
        output_clips.update(export_library(
            secondary, CLIPS_SECONDARY, "Idle_No_Loop_Armature",
            target_pivots,
        ))
        sources.append(
            {
                "name": "Quaternius Universal Animation Library 2 Standard",
                "url": "https://quaternius.itch.io/universal-animation-library-2",
                "license": "CC0-1.0",
            }
        )

    document = {
        "schema": 2,
        "coordinate_system": "bedrock_x_right_y_up_z_back",
        "quaternion_order": "wxyz",
        "sample_rate": SAMPLE_RATE,
        "sources": sources,
        "bones": list(CHAINS),
        "clips": output_clips,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    if args.preview_output is not None:
        preview = {"format_version": "1.8.0", "animations": {}}
        bones = document["bones"]
        for clip_name, clip in output_clips.items():
            animation = {
                "loop": bool(clip["loop"]),
                "animation_length": clip["duration_seconds"],
                "bones": {},
            }
            for bone_index, bone_name in enumerate(bones):
                rotations = {}
                for frame_index, frame in enumerate(clip["frames"]):
                    q = frame["rotation_wxyz"][bone_index]
                    euler = Quaternion((q[0], q[1], q[2], q[3])).to_euler("XYZ")
                    rotations[str(round(frame_index / SAMPLE_RATE, 6))] = [
                        round(math.degrees(float(euler.x)), 5),
                        round(math.degrees(float(euler.y)), 5),
                        round(math.degrees(float(euler.z)), 5),
                    ]
                animation["bones"][bone_name] = {"rotation": rotations}
            animation["bones"]["root"] = {
                "position": {
                    str(round(frame_index / SAMPLE_RATE, 6)): [
                        round(float(frame["root_m"][0])
                              * MODEL_UNITS_PER_SOURCE_METRE, 5),
                        round(float(frame["root_m"][1])
                              * MODEL_UNITS_PER_SOURCE_METRE, 5),
                        round(float(frame["root_m"][2])
                              * MODEL_UNITS_PER_SOURCE_METRE, 5),
                    ]
                    for frame_index, frame in enumerate(clip["frames"])
                }
            }
            preview["animations"][f"animation.eva_motion_v2.{clip_name}"] = animation
        args.preview_output.parent.mkdir(parents=True, exist_ok=True)
        args.preview_output.write_text(
            json.dumps(preview, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"EVA motion DB: clips={len(output_clips)} bones={len(CHAINS)} "
        f"bytes={args.output.stat().st_size} output={args.output}"
    )


if __name__ == "__main__":
    main()
