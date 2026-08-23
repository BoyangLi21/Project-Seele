#!/usr/bin/env python3
"""Reviewed runtime-animation repairs for Project SEELE EVA-00/01/02.

This module is intentionally a deterministic post-pass.  The source-frame
finger adapter remains owned by eva_finger_axis_repair.py.  It first installs
the reviewed canonical catalogue, then applies the Pro R03 biomechanics layer
for locomotion, low stances, prone weapons and Longinus motion.  Keeping both
layers here prevents a later model-pack regeneration from silently restoring
the superseded animations.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

PATCH_FILE = Path(__file__).with_name("eva_animation_reviewed_overrides.json")
R03_PATCH_FILE = Path(__file__).with_name("eva_animation_r03_replacements.json")
R04_PATCH_FILE = Path(__file__).with_name("eva_animation_r04_replacements.json")

ARM_CHAIN = ("arm_r", "forearm_r", "hand_r",
             "arm_l", "forearm_l", "hand_l")


def _animation(animations: dict[str, Any], suffix: str) -> dict[str, Any]:
    matches = [value for name, value in animations.items()
               if name.endswith("." + suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one animation ending in .{suffix}, got {len(matches)}")
    return matches[0]


def _set_arm_keys(animations: dict[str, Any], suffix: str,
                  keys: dict[str, dict[str, list[float]]]) -> None:
    bones = _animation(animations, suffix).setdefault("bones", {})
    for bone, rotation in keys.items():
        bones.setdefault(bone, {})["rotation"] = copy.deepcopy(rotation)


def _copy_arm_rotation(animations: dict[str, Any], source: str,
                       target: str) -> None:
    source_bones = _animation(animations, source)["bones"]
    target_bones = _animation(animations, target).setdefault("bones", {})
    for bone in ARM_CHAIN:
        target_bones.setdefault(bone, {})["rotation"] = copy.deepcopy(
            source_bones[bone]["rotation"])


def _sample_arm_pose(animations: dict[str, Any], source: str, time: str,
                     target: str) -> None:
    source_bones = _animation(animations, source)["bones"]
    target_bones = _animation(animations, target).setdefault("bones", {})
    for bone in ARM_CHAIN:
        channel = source_bones[bone]["rotation"]
        if isinstance(channel, dict):
            value = channel.get(time)
            if value is None:
                numeric_time = float(time)
                matching_key = next((key for key in channel
                                     if abs(float(key) - numeric_time) < 1.0e-6),
                                    None)
                if matching_key is None:
                    raise RuntimeError(
                        f"{source}.{bone} has no key at {time}")
                value = channel[matching_key]
        else:
            value = channel
        target_bones.setdefault(bone, {})["rotation"] = copy.deepcopy(value)


def _apply_local_r05_arm_repairs(animations: dict[str, Any]) -> None:
    """Keep every arm joint on its authored parent and replace broken poses.

    The reviewed R04 catalogue still translated several hand bones and used
    80-146 degree wrist compensation to hide low elbows.  On the Tiger rig a
    translated child is no longer attached to its parent, so those channels
    are the direct cause of floating/broken joints.  R05 is deliberately
    rotation-only and uses solved shoulder/elbow targets at chest height.
    """
    for animation in animations.values():
        bones = animation.get("bones", {})
        for bone in ARM_CHAIN:
            channel = bones.get(bone)
            if channel is not None:
                channel.pop("position", None)

    neutral_r = [1.331, -13.366, 5.061]
    neutral_rf = [-2.681, 0.769, -11.094]
    neutral_l = [-5.0, 0.0, -5.0]
    neutral_lf = [4.0, 0.0, 0.0]
    zero = [0.0, 0.0, 0.0]

    ready = {
        "arm_r": {"0.0": [-63.388, -11.149, 51.551],
                  "0.6": [-64.1, -11.149, 51.551],
                  "1.2": [-63.388, -11.149, 51.551]},
        "forearm_r": {"0.0": [-90.289, -24.529, 16.368],
                      "0.6": [-90.289, -24.529, 16.368],
                      "1.2": [-90.289, -24.529, 16.368]},
        "hand_r": {"0.0": [0.0, 0.0, -8.0], "0.6": [0.0, 0.0, -8.0],
                   "1.2": [0.0, 0.0, -8.0]},
        "arm_l": {"0.0": [-52.371, -2.955, -36.63],
                  "0.6": [-53.0, -2.955, -36.63],
                  "1.2": [-52.371, -2.955, -36.63]},
        "forearm_l": {"0.0": [-76.219, 34.732, 33.565],
                      "0.6": [-76.219, 34.732, 33.565],
                      "1.2": [-76.219, 34.732, 33.565]},
        "hand_l": {"0.0": zero, "0.6": zero, "1.2": zero},
    }
    _set_arm_keys(animations, "knife_ready", ready)

    knife_times = ("0.0", "0.1942", "0.4439", "0.6658", "0.86")
    knife = {
        "arm_r": dict(zip(knife_times, ([-63.388, -11.149, 51.551],
            [-63.192, 12.171, 50.524], [-51.632, 28.627, 49.095],
            [-49.828, 5.816, 44.193], [-63.388, -11.149, 51.551]))),
        "forearm_r": dict(zip(knife_times, ([-90.289, -24.529, 16.368],
            [-104.299, -22.431, 5.643], [-60.643, -8.086, -72.917],
            [-89.809, -29.181, -2.796], [-90.289, -24.529, 16.368]))),
        "hand_r": dict(zip(knife_times, ([0, 0, -8], [0, 0, -15],
            [0, 0, 8], zero, [0, 0, -8]))),
        "arm_l": dict(zip(knife_times, ([-52.371, -2.955, -36.63],
            [-31.271, -15.984, -39.99], [-76.428, 9.43, -11.937],
            [-61.617, 3.121, -33.401], [-52.371, -2.955, -36.63]))),
        "forearm_l": dict(zip(knife_times, ([-76.219, 34.732, 33.565],
            [-85.756, 39.991, 39.172], [-71.665, 62.94, 30.635],
            [-77.567, 38.664, 34.807], [-76.219, 34.732, 33.565]))),
        "hand_l": dict(zip(knife_times, (zero, zero, zero, zero, zero))),
    }
    _set_arm_keys(animations, "knife", knife)

    knife_left = copy.deepcopy(knife)
    knife_left["arm_r"] = dict(zip(knife_times, (
        [-63.388, -11.149, 51.551], [-81.769, -38.182, -6.168],
        [-3.394, 24.413, 64.402], [-49.828, 5.816, 44.193],
        [-63.388, -11.149, 51.551])))
    knife_left["forearm_r"] = dict(zip(knife_times, (
        [-90.289, -24.529, 16.368], [-2.043, -55.717, -10.079],
        [-97.433, 0.74, 17.4], [-89.809, -29.181, -2.796],
        [-90.289, -24.529, 16.368])))
    _set_arm_keys(animations, "knife_left", knife_left)

    melee_times = ("0.0", "0.16", "0.36", "0.54", "0.76")
    melee = {
        "arm_r": dict(zip(melee_times, (neutral_r,
            [-69.198, 2.578, 36.414], [-24.516, 36.291, 54.619],
            [-32.238, 11.125, 39.59], neutral_r))),
        "forearm_r": dict(zip(melee_times, (neutral_rf,
            [-56.734, -10.6, -64.067], [-62.135, -12.509, -64.047],
            [-68.547, -25.856, -40.484], neutral_rf))),
        "hand_r": dict(zip(melee_times, (zero, [0, 0, 10], [0, 0, 6],
                                           [0, 0, 2], zero))),
        "arm_l": dict(zip(melee_times, (neutral_l,
            [-22.938, -23.215, -41.239], [-81.787, 24.674, -12.285],
            [-68.829, 7.734, -28.72], neutral_l))),
        "forearm_l": dict(zip(melee_times, (neutral_lf,
            [-74.512, 40.655, 59.081], [-42.646, 52.174, 44.288],
            [-63.052, 37.058, 37.686], neutral_lf))),
        "hand_l": dict(zip(melee_times, (zero, zero, zero, zero, zero))),
    }
    _set_arm_keys(animations, "melee", melee)

    melee_left_times = ("0.0", "0.18", "0.38", "0.54", "0.76")
    melee_left = {
        "arm_l": dict(zip(melee_left_times, (neutral_l,
            [-66.422, -4.977, -37.457], [-21.299, -36.785, -56.542],
            [-28.665, -14.769, -39.689], neutral_l))),
        "forearm_l": dict(zip(melee_left_times, (neutral_lf,
            [-57.897, 11.0, 67.976], [-61.914, 12.013, 65.157],
            [-67.114, 26.157, 46.678], neutral_lf))),
        "hand_l": dict(zip(melee_left_times, (zero, [0, 0, -10], [0, 0, -6],
                                                [0, 0, -2], zero))),
        "arm_r": dict(zip(melee_left_times, (neutral_r,
            [-28.244, 24.998, 37.314], [-82.845, -26.762, 14.217],
            [-71.194, -8.734, 25.169], neutral_r))),
        "forearm_r": dict(zip(melee_left_times, (neutral_rf,
            [-72.464, -42.932, -54.828], [-42.859, -50.344, -42.028],
            [-61.614, -42.054, -32.687], neutral_rf))),
        "hand_r": dict(zip(melee_left_times, (zero, zero, zero, zero, zero))),
    }
    _set_arm_keys(animations, "melee_left", melee_left)

    smash_times = ("0.0", "0.26", "0.48", "0.68", "0.9", "1.08")
    smash = {
        "arm_r": dict(zip(smash_times, (neutral_r,
            [-102.604, 14.361, 77.162], [-101.225, 26.798, 87.513],
            [25.007, 41.728, 75.059], [-17.052, 27.21, 43.339], neutral_r))),
        "forearm_r": dict(zip(smash_times, (neutral_rf,
            [-99.06, 4.745, -92.114], [-88.474, 25.269, -89.588],
            [-71.821, -33.735, -63.344], [-74.825, -36.727, -53.167], neutral_rf))),
        "hand_r": dict(zip(smash_times, (zero, [0, 0, 5], [0, 0, 12],
                                           [0, 0, 8], [0, 0, 2], zero))),
        "arm_l": dict(zip(smash_times, (neutral_l,
            [-2.394, -2.28, -47.701], [-29.399, -20.813, -35.082],
            [-84.606, 34.222, -2.112], [-75.153, 11.539, -19.901], neutral_l))),
        "forearm_l": dict(zip(smash_times, (neutral_lf,
            [-92.091, 32.352, 68.244], [-88.765, 46.908, 42.028],
            [-63.311, 75.384, 35.65], [-64.905, 48.321, 40.631], neutral_lf))),
        "hand_l": dict(zip(smash_times, (zero, zero, zero, zero, zero, zero))),
    }
    _set_arm_keys(animations, "smash", smash)

    heavy_times = ("0.0", "0.28", "0.5", "0.7", "0.92", "1.3")
    heavy = {
        "arm_r": dict(zip(heavy_times, ([-63.461, -5.571, 41.367],
            [-85.732, -0.941, 52.111], [-97.857, 20.441, 65.633],
            [10.499, 38.348, 69.059], [-20.154, 17.061, 55.78],
            [-63.576, -4.604, 39.602]))),
        "forearm_r": dict(zip(heavy_times, ([-73.856, -32.994, -16.563],
            [-81.626, -5.808, -28.24], [-69.963, -2.091, -30.916],
            [-91.904, -35.64, -18.516], [-104.839, -31.762, -27.712],
            [-67.617, -31.981, -27.157]))),
        "hand_r": dict(zip(heavy_times, ([0, 0, -8], [0, 0, -15],
            [0, 0, -12], [0, 0, 8], zero, [0, 0, -8]))),
        "arm_l": dict(zip(heavy_times, ([-52.371, -2.955, -36.63],
            [-3.775, -24.237, -49.982], [-39.908, -21.525, -31.193],
            [-86.174, 31.289, -7.231], [-76.942, 12.407, -25.319],
            [-52.371, -2.955, -36.63]))),
        "forearm_l": dict(zip(heavy_times, ([-76.219, 34.732, 33.565],
            [-87.322, 42.623, 53.831], [-82.284, 49.676, 44.1],
            [-48.87, 68.525, 44.052], [-66.419, 45.473, 35.728],
            [-76.219, 34.732, 33.565]))),
        "hand_l": dict(zip(heavy_times, (zero, zero, zero, zero, zero, zero))),
    }
    _set_arm_keys(animations, "knife_heavy", heavy)

    for source, target in (("melee", "crouch_melee"),
                           ("melee_left", "crouch_melee_left"),
                           ("knife", "crouch_knife"),
                           ("knife_heavy", "crouch_knife_heavy"),
                           ("smash", "crouch_smash")):
        _copy_arm_rotation(animations, source, target)

    for source, time, target in (
            ("knife_ready", "0.0", "visual_knife_ready"),
            ("knife", "0.1942", "visual_knife_windup"),
            ("knife", "0.4439", "visual_knife_contact"),
            ("knife", "0.6658", "visual_knife_recovery"),
            ("knife_heavy", "0.7", "visual_knife_heavy_contact"),
            ("knife", "0.4439", "visual_crouch_knife_contact")):
        _sample_arm_pose(animations, source, time, target)


def _apply_local_r06_combat_repairs(animations: dict[str, Any]) -> None:
    """Author human-readable combat arcs on the measured Tiger arm chain.

    R05 removed every detached-child translation, but several inherited Euler
    solutions still routed a forearm through the chest or let the elbow reach
    the target before the hand.  These keys were solved against the runtime
    shoulder/elbow/wrist pivots.  Longinus keeps the reviewed weapon placement:
    both hands stay within one model pixel of the R04 grip points while the
    elbows take the physically plausible outside route.
    """
    zero = [0.0, 0.0, 0.0]
    neutral_r = [1.331, -13.366, 5.061]
    neutral_rf = [-2.681, 0.769, -11.094]
    neutral_l = [-5.0, 0.0, -5.0]
    neutral_lf = [4.0, 0.0, 0.0]

    # Two-hand red-spear guard: the rear/right elbow flares outside the torso;
    # the forward/left forearm crosses in front of, never through, the chest.
    lance_ready_pose = {
        "arm_r": [2.491, -2.753, 57.774],
        "forearm_r": [-77.272, -73.691, -26.101],
        "arm_l": [-53.361, 45.191, 17.754],
        "forearm_l": [22.904, -6.417, 28.123],
    }
    for suffix in ("lance_ready", "lance_carry"):
        bones = _animation(animations, suffix).setdefault("bones", {})
        for bone, rotation in lance_ready_pose.items():
            bones.setdefault(bone, {})["rotation"] = {
                "0.0": rotation,
                "0.6": [rotation[0] + (0.35 if bone.startswith("arm_") else 0.0),
                        rotation[1], rotation[2]],
                "1.2": rotation,
            }

    lance_times = ("0.0", "0.09", "0.12", "0.165", "0.18",
                   "0.34", "0.52", "0.72", "0.96")
    thrust_contact = {
        "arm_r": [34.881, 25.413, 62.809],
        "forearm_r": [-90.055, -58.061, -38.632],
        "arm_l": [-100.563, 62.844, -10.994],
        "forearm_l": [-52.237, 129.018, -14.811],
    }
    windup = {
        "arm_r": [-16.0, -12.0, 63.0],
        "forearm_r": [-73.0, -77.0, -24.0],
        "arm_l": [-61.0, 41.0, 13.0],
        "forearm_l": [16.0, -4.0, 34.0],
    }

    def blend(left: list[float], right: list[float], amount: float) -> list[float]:
        return [round(a + (b - a) * amount, 3)
                for a, b in zip(left, right)]

    lance = {}
    for bone in lance_ready_pose:
        ready_rotation = lance_ready_pose[bone]
        windup_rotation = windup[bone]
        contact_rotation = thrust_contact[bone]
        lance[bone] = dict(zip(lance_times, (
            ready_rotation,
            blend(ready_rotation, windup_rotation, 0.55),
            blend(ready_rotation, windup_rotation, 0.8),
            windup_rotation,
            windup_rotation,
            blend(windup_rotation, contact_rotation, 0.35),
            contact_rotation,
            blend(contact_rotation, ready_rotation, 0.45),
            ready_rotation,
        )))
    _set_arm_keys(animations, "lance_thrust", lance)

    # Alternating claw rakes.  The contact hand leads the elbow by more than
    # twenty model pixels; the opposite arm remains a compact forward guard.
    melee_times = ("0.0", "0.16", "0.36", "0.54", "0.76")
    melee = {
        "arm_r": dict(zip(melee_times, (neutral_r, [-47, -8, 37],
            [1.255, 37.712, 61.958], [-24, 9, 36], neutral_r))),
        "forearm_r": dict(zip(melee_times, (neutral_rf, [-43, -18, -52],
            [-69.145, -29.938, -72.852], [-48, -22, -43], neutral_rf))),
        "hand_r": dict(zip(melee_times, (zero, [0, 0, 12], [0, 0, 8],
                                            [0, 0, 3], zero))),
        "arm_l": dict(zip(melee_times, (neutral_l, [-42, 5, -31],
            [-81.397, 23.239, -16.318], [-57, 8, -27], neutral_l))),
        "forearm_l": dict(zip(melee_times, (neutral_lf, [-53, 29, 36],
            [-42.1, 54.919, 45.55], [-51, 35, 38], neutral_lf))),
        "hand_l": dict(zip(melee_times, (zero, zero, zero, zero, zero))),
    }
    _set_arm_keys(animations, "melee", melee)

    melee_left_times = ("0.0", "0.18", "0.38", "0.54", "0.76")
    melee_left = {
        "arm_l": dict(zip(melee_left_times, (neutral_l, [-47, 8, -37],
            [4.503, -37.25, -63.864], [-24, -9, -36], neutral_l))),
        "forearm_l": dict(zip(melee_left_times, (neutral_lf, [-43, 18, 52],
            [-69.087, 29.262, 73.959], [-48, 22, 43], neutral_lf))),
        "hand_l": dict(zip(melee_left_times, (zero, [0, 0, -12],
                                                 [0, 0, -8], [0, 0, -3], zero))),
        "arm_r": dict(zip(melee_left_times, (neutral_r, [-42, -5, 31],
            [-82.437, -25.359, 18.112], [-57, -8, 27], neutral_r))),
        "forearm_r": dict(zip(melee_left_times, (neutral_rf, [-53, -29, -36],
            [-42.341, -53.077, -43.376], [-51, -35, -38], neutral_rf))),
        "hand_r": dict(zip(melee_left_times, (zero, zero, zero, zero, zero))),
    }
    _set_arm_keys(animations, "melee_left", melee_left)

    # Right-click is a committed two-hand downward rake.  Both hands remain in
    # front of the torso; no frame presents the elbow as the impact point.
    smash_times = ("0.0", "0.26", "0.48", "0.68", "0.9", "1.08")
    smash = {
        "arm_r": dict(zip(smash_times, (neutral_r, [-72, 2, 57],
            [-55, 20, 69], [39.314, 39.355, 72.594],
            [-17, 20, 43], neutral_r))),
        "forearm_r": dict(zip(smash_times, (neutral_rf, [-58, -20, -54],
            [-63, -27, -63], [-75.702, -36.165, -66.007],
            [-52, -24, -46], neutral_rf))),
        "hand_r": dict(zip(smash_times, (zero, [0, 0, 6], [0, 0, 12],
                                            [0, 0, 9], [0, 0, 3], zero))),
        "arm_l": dict(zip(smash_times, (neutral_l, [-67, -8, -51],
            [-72, 18, -32], [-85.537, 48.736, -7.12],
            [-59, 13, -24], neutral_l))),
        "forearm_l": dict(zip(smash_times, (neutral_lf, [-57, 28, 48],
            [-51, 53, 36], [-44.866, 82.49, 18.37],
            [-49, 47, 31], neutral_lf))),
        "hand_l": dict(zip(smash_times, (zero, zero, zero, zero, zero, zero))),
    }
    _set_arm_keys(animations, "smash", smash)

    # Low-stance attacks use the same anatomical upper-body solution on top
    # of their own reviewed root/leg stance.
    for source, target in (("melee", "crouch_melee"),
                           ("melee_left", "crouch_melee_left"),
                           ("smash", "crouch_smash"),
                           ("lance_thrust", "crouch_lance_thrust"),
                           ("lance_thrust", "prone_lance_thrust")):
        _copy_arm_rotation(animations, source, target)
    _copy_arm_rotation(animations, "lance_ready", "prone_lance_ready")

    for source, time, target in (
            ("lance_ready", "0.0", "visual_lance_ready"),
            ("lance_thrust", "0.18", "visual_lance_windup"),
            ("lance_thrust", "0.52", "visual_lance_contact"),
            ("lance_thrust", "0.72", "visual_lance_recovery")):
        _sample_arm_pose(animations, source, time, target)


def semantic_sha256(animations: dict[str, Any]) -> str:
    blob = json.dumps(animations, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def apply_reviewed_animation_repairs(data: dict[str, Any], *, strict_source: bool = False) -> dict[str, Any]:
    patch = json.loads(PATCH_FILE.read_text(encoding="utf-8"))
    animations = data["animations"]
    source_sha = semantic_sha256(animations)
    expected = patch["source_animation_semantic_sha256"]
    if strict_source and source_sha != expected:
        raise RuntimeError(
            f"animation source SHA mismatch: expected {expected}, got {source_sha}")

    for name, replacement in patch["replace_animations"].items():
        animations[name] = copy.deepcopy(replacement)

    target = patch["target_animation_semantic_sha256"]
    actual = semantic_sha256(animations)
    if actual != target:
        raise RuntimeError(f"reviewed animation target SHA mismatch: expected {target}, got {actual}")

    r03 = json.loads(R03_PATCH_FILE.read_text(encoding="utf-8"))
    expected_r03_source = r03["source_animation_semantic_sha256"]
    if actual != expected_r03_source:
        raise RuntimeError(
            f"R03 animation source SHA mismatch: expected {expected_r03_source}, got {actual}")
    for name, replacement in r03["replace_animations"].items():
        animations[name] = copy.deepcopy(replacement)
    r03_target = r03["target_animation_semantic_sha256"]
    actual = semantic_sha256(animations)
    if actual != r03_target:
        raise RuntimeError(
            f"R03 animation target SHA mismatch: expected {r03_target}, got {actual}")

    r04 = json.loads(R04_PATCH_FILE.read_text(encoding="utf-8"))
    expected_r04_source = r04["source_animation_semantic_sha256"]
    if actual != expected_r04_source:
        raise RuntimeError(
            f"R04 animation source SHA mismatch: expected {expected_r04_source}, got {actual}")
    for name, replacement in r04["replace_animations"].items():
        animations[name] = copy.deepcopy(replacement)
    r04_target = r04["target_animation_semantic_sha256"]
    actual = semantic_sha256(animations)
    if actual != r04_target:
        raise RuntimeError(
            f"R04 animation target SHA mismatch: expected {r04_target}, got {actual}")
    # R04 is the reviewed authority for the complete three-unit catalogue.
    # Do not layer the old local R05/R06 Euler guesses on top: doing so
    # reintroduced the broken Longinus elbows and iron-golem melee poses that
    # R04 was built to replace.
    return data
