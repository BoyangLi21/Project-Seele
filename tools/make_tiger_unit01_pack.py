#!/usr/bin/env python3
"""Build a LOCAL-ONLY rigged Unit-01 mesh pack from Tigerar1's OBJ source.

The downloaded mesh is CC BY-SA fan art and is never written into Git-tracked
resources. This tool keeps the original triangles/UVs, assigns them to the
Project SEELE bone contract, and writes only to the ignored run resource pack.
"""

import copy
import heapq
import io
import json
import math
import sys
import zipfile
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    REPO / "external-assets/incoming/evangelion-unit-01.zip")
OUT = REPO / "run/resourcepacks/eva_real_model/assets/projectseele"
BASE_GEO = REPO / "src/main/resources/assets/projectseele/geo/eva_unit01.geo.json"
BASE_ANIMATION = REPO / "src/main/resources/assets/projectseele/animations/eva_unit01.animation.json"
BASE_TEXTURE = REPO / "src/main/resources/assets/projectseele/textures/entity/eva_unit01.png"
MODEL_HEIGHT = 192.0
ATLAS_WIDTH = 1024
ATLAS_HEIGHT = 512
# Triangles below this neutral OBJ height belong to the rigid foot shell.
# The old 15-part rig welded them to the shin, making a planted one-knee pose
# mathematically impossible: correcting the knee also tipped the entire foot.
FOOT_CUT_Y = 0.35

# Joint centres measured on the downloaded neutral-pose mesh. Keeping these in
# source OBJ space makes the rig reproducible if MODEL_HEIGHT changes.
SOURCE_PIVOTS = {
    "root": (0.0, 0.0, 0.0),
    "torso_lower": (0.0, 2.08, 0.0),
    "torso_upper": (0.0, 2.86, 0.0),
    "head": (0.0, 3.60, 0.02),
    "pylon_l": (0.44, 3.64, 0.0), "pylon_r": (-0.44, 3.64, 0.0),
    "arm_l": (0.44, 3.54, 0.0), "arm_r": (-0.44, 3.54, 0.0),
    "forearm_l": (0.54, 2.80, -0.03), "forearm_r": (-0.54, 2.80, -0.03),
    "hand_l": (0.56, 2.13, -0.02), "hand_r": (-0.56, 2.13, -0.02),
    # The femur shells extend from y=1.52 to y=2.72.  Their former y=2.06
    # pivot sat near the middle of the thigh, so raising a knee swung every
    # triangle above that point backwards through the waist.  The hip socket
    # is at the top of the shell, just below the pelvis armour.
    "leg_l": (0.25, 2.62, 0.0), "leg_r": (-0.25, 2.62, 0.0),
    "shin_l": (0.35, 1.37, -0.02), "shin_r": (-0.35, 1.37, -0.02),
    "foot_l": (0.35, 0.42, -0.02), "foot_r": (-0.35, 0.42, -0.02),
}
BODY_MESH_BONES = frozenset(SOURCE_PIVOTS) - {"root"}
FINGER_ORDER = ("thumb", "index", "middle", "ring", "little")
# The Tiger OBJ welds each finger root into the continuous arm shell but keeps
# a small distal armour cap as a detached component.  Cut the continuous shell
# at the knuckle line so the imported hand can actually close around a weapon;
# treating only the detached caps as fingers makes the caps orbit an otherwise
# permanently open hand.
FINGER_KNUCKLE_Y = 2.105
# Below this source-space height the four welded finger shafts are four
# genuinely disconnected islands.  Above it the triangulated knuckle webbing
# joins neighbouring digits and must stay on the rigid palm; assigning that
# webbing by a Z centroid is what made the old animated fingers explode.
FINGER_SHAFT_CEILING_Y = 2.04


def read_source():
    with zipfile.ZipFile(SOURCE) as outer:
        nested_name = next(name for name in outer.namelist() if name.lower().endswith("unit01.zip"))
        texture_name = next(name for name in outer.namelist()
                            if name.lower().endswith("e01_201.png") and name.startswith("textures/"))
        texture = outer.read(texture_name)
        with zipfile.ZipFile(io.BytesIO(outer.read(nested_name))) as nested:
            obj_name = next(name for name in nested.namelist() if name.lower().endswith(".obj"))
            return nested.read(obj_name).decode("utf-8", errors="ignore"), texture


def parse_obj(text):
    positions = []
    texcoords = []
    normals = []
    triangles = []
    for raw in text.splitlines():
        fields = raw.split()
        if not fields:
            continue
        if fields[0] == "v":
            positions.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "vt":
            texcoords.append(tuple(float(value) for value in fields[1:3]))
        elif fields[0] == "vn":
            normals.append(tuple(float(value) for value in fields[1:4]))
        elif fields[0] == "f":
            refs = []
            for field in fields[1:]:
                values = field.split("/")
                refs.append((int(values[0]) - 1,
                             int(values[1]) - 1 if len(values) > 1 and values[1] else -1,
                             int(values[2]) - 1 if len(values) > 2 and values[2] else -1))
            for index in range(1, len(refs) - 1):
                triangles.append((refs[0], refs[index], refs[index + 1]))
    return positions, texcoords, normals, triangles


def connected_components(positions, triangles):
    # UV seams duplicate position indices. Weld only for component discovery;
    # the exported render mesh retains every original UV vertex.
    welded = {}
    position_key = []
    for position in positions:
        key = tuple(round(value, 6) for value in position)
        position_key.append(welded.setdefault(key, len(welded)))
    by_position = {}
    for face_index, triangle in enumerate(triangles):
        for ref in triangle:
            by_position.setdefault(position_key[ref[0]], []).append(face_index)
    adjacency = [set() for _ in triangles]
    for face_indices in by_position.values():
        for face_index in face_indices:
            adjacency[face_index].update(face_indices)
    components = []
    seen = set()
    for start in range(len(triangles)):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        component = []
        while stack:
            face_index = stack.pop()
            component.append(face_index)
            for neighbour in adjacency[face_index]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        components.append(component)
    return components


def restricted_connected_components(face_indices, positions, triangles):
    """Connected components for a selected subset of OBJ faces.

    The source hand is one continuous shell.  Cutting it below the knuckle
    webbing reveals one island per finger, but the regular component helper
    cannot express that virtual cut because it traverses every face in the
    OBJ.  Keep UV-seam welding identical to ``connected_components`` so this
    classifier remains deterministic across all three Tiger EVA variants.
    """
    selected = set(face_indices)
    welded = {}
    position_key = []
    for position in positions:
        key = tuple(round(value, 6) for value in position)
        position_key.append(welded.setdefault(key, len(welded)))
    by_position = {}
    for face_index in selected:
        for ref in triangles[face_index]:
            by_position.setdefault(position_key[ref[0]], []).append(face_index)
    adjacency = {face_index: set() for face_index in selected}
    for faces in by_position.values():
        for face_index in faces:
            adjacency[face_index].update(faces)
    components = []
    while selected:
        start = selected.pop()
        stack = [start]
        component = [start]
        while stack:
            current = stack.pop()
            for neighbour in adjacency[current]:
                if neighbour in selected:
                    selected.remove(neighbour)
                    stack.append(neighbour)
                    component.append(neighbour)
        components.append(component)
    return components


def partition_connected_faces(face_indices, seed_faces, lane_z,
                              positions, triangles):
    """Geodesically partition one welded hand island between finger seeds."""
    selected = set(face_indices)
    welded = {}
    position_key = []
    for position in positions:
        key = tuple(round(value, 6) for value in position)
        position_key.append(welded.setdefault(key, len(welded)))
    by_position = {}
    for face_index in selected:
        for ref in triangles[face_index]:
            by_position.setdefault(position_key[ref[0]], []).append(face_index)
    adjacency = {face_index: set() for face_index in selected}
    for faces in by_position.values():
        for face_index in faces:
            adjacency[face_index].update(faces)
    centroid_z = {
        face_index: sum(positions[ref[0]][2]
                        for ref in triangles[face_index]) / 3.0
        for face_index in selected}
    frontier = []
    label_order = {label: order for order, label in enumerate(seed_faces)}
    for label, seeds in seed_faces.items():
        for face_index in seeds:
            heapq.heappush(frontier, (
                0, abs(centroid_z[face_index] - lane_z[label]),
                label_order[label], face_index, label))
    labels = {}
    while frontier:
        distance, _, order, face_index, label = heapq.heappop(frontier)
        if face_index in labels:
            continue
        labels[face_index] = label
        for neighbour in adjacency[face_index]:
            if neighbour not in labels:
                heapq.heappush(frontier, (
                    distance + 1,
                    abs(centroid_z[neighbour] - lane_z[label]),
                    order, neighbour, label))
    if len(labels) != len(selected):
        raise RuntimeError(
            f"finger geodesic partition missed {len(selected) - len(labels)} faces")
    return labels


def component_bounds(component, positions, triangles):
    points = [positions[ref[0]] for face_index in component for ref in triangles[face_index]]
    return ([min(point[axis] for point in points) for axis in range(3)],
            [max(point[axis] for point in points) for axis in range(3)])


def discover_finger_rig(positions, triangles):
    """Return two-joint finger faces and reproducible knuckle pivots.

    Tigerar1's three EVA meshes share ten detached finger armour caps, while
    the long proximal fingers are welded into the continuous arm shell.  The
    caps identify each digit's Z lane; faces below the knuckle line in the arm
    shell are then assigned to the nearest lane.  This retains the palm on the
    hand bone. Each digit is subsequently divided into proximal and distal
    parts; one straight rigid bone cannot make a readable weapon grip.
    """
    candidates = {"l": [], "r": []}
    for component in connected_components(positions, triangles):
        minimum, maximum = component_bounds(component, positions, triangles)
        vertex_indices = {ref[0] for face_index in component
                          for ref in triangles[face_index]}
        centre = tuple(sum(positions[index][axis] for index in vertex_indices)
                       / len(vertex_indices) for axis in range(3))
        if (12 <= len(component) <= 32
                and abs(centre[0]) > 0.48
                and minimum[1] >= 1.98 and maximum[1] <= 2.21):
            side = "l" if centre[0] > 0 else "r"
            candidates[side].append((centre[2], component, centre, maximum[1]))
    if any(len(items) != len(FINGER_ORDER) for items in candidates.values()):
        counts = {side: len(items) for side, items in candidates.items()}
        raise RuntimeError(f"expected five detached fingers per hand, found {counts}")

    face_bones = {}
    source_pivots = {}
    digit_lanes = {}
    cap_minimum_y = {}
    for side, items in candidates.items():
        # The highest detached component is the gold wrist/hand ornament, not
        # a thumb.  Keep it rigid on the hand.  The remaining four caps mark
        # index through little-finger lanes.  Tiger's thumb is welded into the
        # continuous shell and gets its own positive-Z lane below.
        ornament = max(items, key=lambda item: item[2][1])
        for face_index in ornament[1]:
            face_bones[face_index] = "hand_" + side
        fingers = [item for item in items if item is not ornament]
        if len(fingers) != 4:
            raise RuntimeError(f"expected four finger caps on {side}, found {len(fingers)}")

        thumb_name = f"finger_thumb_{side}"
        thumb_x = SOURCE_PIVOTS["hand_" + side][0]
        thumb_z = 0.055
        source_pivots[thumb_name] = (thumb_x, FINGER_KNUCKLE_Y + 0.025, thumb_z)
        digit_lanes.setdefault(side, []).append((thumb_z, thumb_name))

        # Four long fingers run from positive toward negative source Z.
        for digit, (_, component, centre, maximum_y) in zip(
                FINGER_ORDER[1:], sorted(fingers, key=lambda item: item[0], reverse=True)):
            name = f"finger_{digit}_{side}"
            # Pivot at the welded knuckle, not inside the detached cap.  X and
            # Z retain the source digit centre so rotation does not orbit the
            # finger across the palm.
            source_pivots[name] = (centre[0], FINGER_KNUCKLE_Y, centre[2])
            digit_lanes.setdefault(side, []).append((centre[2], name))
            cap_minimum_y[name] = min(
                positions[ref[0]][1] for face_index in component
                for ref in triangles[face_index])
            for face_index in component:
                face_bones[face_index] = name

    # Add the welded thumb and four long finger shafts.  The four shafts are
    # real disconnected islands below FINGER_SHAFT_CEILING_Y.  Classifying
    # those islands preserves every triangle of a digit and leaves only the
    # shared knuckle webbing on the palm.  The former per-face Voronoi pass
    # left webbing fragments between both finger bones, so a valid curl looked
    # like spikes and a straight finger still appeared detached.
    for component in connected_components(positions, triangles):
        if len(component) <= 350:
            continue
        minimum, maximum = component_bounds(component, positions, triangles)
        centre_x = (minimum[0] + maximum[0]) * 0.5
        if abs(centre_x) <= 0.30:
            continue
        side = "l" if centre_x > 0 else "r"
        lanes = sorted(digit_lanes[side], key=lambda lane: lane[0])
        thumb_z, thumb_name = next(
            lane for lane in lanes if "thumb" in lane[1])
        next_lane_z = max(lane_z for lane_z, name in lanes if name != thumb_name)
        thumb_boundary_z = (thumb_z + next_lane_z) * 0.5
        for face_index in component:
            points = [positions[ref[0]] for ref in triangles[face_index]]
            if (max(point[1] for point in points) < FINGER_KNUCKLE_Y
                    and min(point[2] for point in points) >= thumb_boundary_z):
                face_bones[face_index] = thumb_name

        shaft_candidates = []
        for face_index in component:
            points = [positions[ref[0]] for ref in triangles[face_index]]
            on_side = (all(point[0] > 0.42 for point in points) if side == "l"
                       else all(point[0] < -0.42 for point in points))
            if (on_side
                    and min(point[1] for point in points) > 1.82
                    and max(point[1] for point in points) < FINGER_SHAFT_CEILING_Y):
                shaft_candidates.append(face_index)
        shaft_components = []
        for shaft in restricted_connected_components(
                shaft_candidates, positions, triangles):
            shaft_minimum, shaft_maximum = component_bounds(
                shaft, positions, triangles)
            if (10 <= len(shaft) <= 20
                    and shaft_minimum[2] > -0.20
                    and shaft_maximum[2] < 0.12):
                shaft_components.append(shaft)
        if len(shaft_components) != 4:
            raise RuntimeError(
                f"expected four welded finger shafts on {side}, "
                f"found {[len(item) for item in shaft_components]}")
        shaft_components.sort(
            key=lambda shaft: sum(
                positions[index][2] for index in {
                    ref[0] for face_index in shaft
                    for ref in triangles[face_index]})
            / len({ref[0] for face_index in shaft
                   for ref in triangles[face_index]}),
            reverse=True)
        web_candidates = []
        for face_index in component:
            points = [positions[ref[0]] for ref in triangles[face_index]]
            on_side = (all(point[0] > 0.42 for point in points) if side == "l"
                       else all(point[0] < -0.42 for point in points))
            if (on_side
                    and min(point[1] for point in points) > 1.82
                    and max(point[1] for point in points) < FINGER_KNUCKLE_Y):
                web_candidates.append(face_index)
        web_components = restricted_connected_components(
            web_candidates, positions, triangles)
        finger_web = max(web_components, key=len)
        if len(finger_web) < 70:
            raise RuntimeError(
                f"welded finger web on {side} is unexpectedly small: "
                f"{len(finger_web)} faces")
        seed_faces = {}
        lane_z = {}
        for digit, shaft in zip(FINGER_ORDER[1:], shaft_components):
            tip_name = f"finger_{digit}_tip_{side}"
            seed_faces[tip_name] = shaft
            lane_z[tip_name] = source_pivots[f"finger_{digit}_{side}"][2]
        partition = partition_connected_faces(
            finger_web, seed_faces, lane_z, positions, triangles)
        for face_index, tip_name in partition.items():
            face_bones[face_index] = tip_name
        for digit in FINGER_ORDER[1:]:
            root_name = f"finger_{digit}_{side}"
            tip_name = f"finger_{digit}_tip_{side}"
            region = [face_index for face_index, label in partition.items()
                      if label == tip_name]
            region_points = [positions[ref[0]] for face_index in region
                             for ref in triangles[face_index]]
            joint_y = cap_minimum_y[root_name] + 0.012
            joint_points = [point for point in region_points
                            if abs(point[1] - joint_y) <= 0.025]
            if not joint_points:
                joint_points = sorted(
                    region_points, key=lambda point: abs(point[1] - joint_y))[:12]
            source_pivots[tip_name] = (
                sum(point[0] for point in joint_points) / len(joint_points),
                joint_y,
                sum(point[2] for point in joint_points) / len(joint_points))

    # The thumb has no detachable shaft that can survive a rigid two-bone
    # split.  Keep its small connected island on one animated root bone and
    # retain an empty child socket for the shared bone contract.
    for side in ("l", "r"):
        root_name = f"finger_thumb_{side}"
        assigned = [face_index for face_index, bone in face_bones.items()
                    if bone == root_name]
        if not assigned:
            raise RuntimeError(
                f"not enough faces to animate {root_name}: {len(assigned)}")
        tip_name = f"finger_thumb_tip_{side}"
        root_pivot = source_pivots[root_name]
        source_pivots[tip_name] = (
            root_pivot[0], FINGER_SHAFT_CEILING_Y, root_pivot[2])

    for side in ("l", "r"):
        for digit in FINGER_ORDER:
            root_name = f"finger_{digit}_{side}"
            tip_name = f"finger_{digit}_tip_{side}"
            root_count = sum(bone == root_name for bone in face_bones.values())
            tip_count = sum(bone == tip_name for bone in face_bones.values())
            if root_count == 0 or (digit != "thumb" and tip_count == 0):
                raise RuntimeError(
                    f"invalid two-joint split for {root_name}: "
                    f"root={root_count}, tip={tip_count}")
    return face_bones, source_pivots


def side_name(x, left, right):
    # Positive OBJ X is the Unit's anatomical left (viewer's right).
    return left if x >= 0 else right


def component_family(component, bounds, positions, triangles):
    minimum, maximum = bounds
    vertex_indices = {ref[0] for face_index in component for ref in triangles[face_index]}
    centre = [sum(positions[index][axis] for index in vertex_indices) / len(vertex_indices)
              for axis in range(3)]
    absolute_x = abs(centre[0])
    if maximum[1] > 4.30 and absolute_x > 0.30:
        return "pylon"
    # The two 451-face components are the continuous upper-arm/forearm/hand
    # shells. Smaller detached wrist and elbow armour lives in the same zone.
    if (len(component) > 350 and absolute_x > 0.30) or (
            absolute_x > 0.42 and minimum[1] > 1.75):
        return "arm_chain"
    # Separate face/helmet shells sit wholly above the collar. The 804-face
    # central body component intentionally remains torso to keep the neck seam
    # from being cut merely because a few points rise into this range.
    if len(component) < 400 and minimum[1] > 3.30 and absolute_x < 0.42:
        return "head"
    if maximum[1] < 1.80:
        return "shin"
    if maximum[1] < 2.82 and minimum[1] > 1.30 and absolute_x > 0.10:
        return "leg"
    if minimum[1] > 3.25 and absolute_x >= 0.36:
        return "arm_chain"
    return "torso"


def assign_bone(centroid, family):
    x, y, _ = centroid
    if family == "pylon":
        return side_name(x, "pylon_l", "pylon_r")
    if family == "head":
        return "head"
    if family == "arm_chain":
        if y < 2.18:
            return side_name(x, "hand_l", "hand_r")
        if y < 2.82:
            return side_name(x, "forearm_l", "forearm_r")
        return side_name(x, "arm_l", "arm_r")
    if family == "shin":
        if y < FOOT_CUT_Y:
            return side_name(x, "foot_l", "foot_r")
        return side_name(x, "shin_l", "shin_r")
    if family == "leg":
        return side_name(x, "leg_l", "leg_r")
    if y < 2.78:
        return "torso_lower"
    return "torso_upper"


def face_normal(points):
    ax, ay, az = (points[1][axis] - points[0][axis] for axis in range(3))
    bx, by, bz = (points[2][axis] - points[0][axis] for axis in range(3))
    nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / length, ny / length, nz / length


def shift_uv(uv, x_offset):
    if isinstance(uv, list):
        return [uv[0] + x_offset, *uv[1:]]
    if isinstance(uv, dict):
        result = copy.deepcopy(uv)
        for face in result.values():
            if isinstance(face.get("uv"), list):
                face["uv"][0] += x_offset
        return result
    return uv


def build_skeleton(scale, minimum_y, finger_pivots=None):
    finger_pivots = finger_pivots or {}
    source_pivots = {**SOURCE_PIVOTS, **finger_pivots}
    data = json.loads(BASE_GEO.read_text(encoding="utf-8"))
    geometry = data["minecraft:geometry"][0]
    geometry["description"]["texture_width"] = ATLAS_WIDTH
    geometry["description"]["texture_height"] = ATLAS_HEIGHT
    ensure_foot_bones(geometry)
    ensure_finger_bones(geometry, finger_pivots)
    old_pivots = {bone["name"]: copy.deepcopy(bone.get("pivot", [0, 0, 0]))
                  for bone in geometry["bones"]}
    for bone in geometry["bones"]:
        if bone["name"] in source_pivots:
            source_pivot = source_pivots[bone["name"]]
            bone["pivot"] = [round(source_pivot[0] * scale, 5),
                             round((source_pivot[1] - minimum_y) * scale, 5),
                             round(-source_pivot[2] * scale, 5)]
        # The reviewed local pack is fail-closed: never reveal the obsolete
        # cube body (or its extra horn) if its triangle mesh cannot load.
        # Attachment bones are retained and shifted into the fallback half of
        # the atlas; the launcher validator prevents starting with no body.
        if bone["name"] in set(source_pivots) - {"root"} or bone["name"] == "horn":
            bone.pop("cubes", None)
        else:
            for cube in bone.get("cubes", []):
                if "uv" in cube:
                    cube["uv"] = shift_uv(cube["uv"], 512)
    pivots = {bone["name"]: bone.get("pivot", [0, 0, 0]) for bone in geometry["bones"]}
    # The Tiger torso pivot is about 27px above the legacy cube rig. Preserve
    # authored local offsets for the entry plug and both hatch leaves instead
    # of leaving them behind at the obsolete absolute coordinates.
    standard_names = set(source_pivots)
    for bone in geometry["bones"]:
        parent = bone.get("parent")
        if (bone["name"] in standard_names
                or bone["name"] in {"knife", "cannon", "lance"}
                or parent not in standard_names):
            continue
        delta = [pivots[parent][axis] - old_pivots[parent][axis] for axis in range(3)]
        bone["pivot"] = [bone.get("pivot", [0, 0, 0])[axis] + delta[axis]
                         for axis in range(3)]
        for cube in bone.get("cubes", []):
            cube["origin"] = [cube["origin"][axis] + delta[axis] for axis in range(3)]
            if "pivot" in cube:
                cube["pivot"] = [cube["pivot"][axis] + delta[axis] for axis in range(3)]
        pivots[bone["name"]] = bone["pivot"]
    # One semantic shoulder-space layer receives the synchronized cannon pitch
    # in Java.  Rotating torso_upper moved the visible head while the rider
    # socket remained fixed, so a modest look angle could put the entire gun
    # behind the first-person camera.  Both arms now preserve their authored
    # two-hand spacing under a shared, view-independent elevation transform.
    arm_index = next(index for index, bone in enumerate(geometry["bones"])
                     if bone["name"] == "arm_l")
    aim_pivot = [0.0, round((pivots["arm_l"][1] + pivots["arm_r"][1]) * 0.5, 5), 0.0]
    geometry["bones"].insert(arm_index, {
        "name": "aim_pitch", "parent": "torso_upper", "pivot": aim_pivot})
    for bone in geometry["bones"]:
        if bone["name"] in {"arm_l", "arm_r"}:
            bone["parent"] = "aim_pitch"
    pivots["aim_pitch"] = aim_pivot
    # N2 is a true hand-carried device, not a HUD-only weapon state.
    if not any(bone["name"] == "n2" for bone in geometry["bones"]):
        geometry["bones"].append({
            "name": "n2", "parent": "hand_r",
            "pivot": copy.deepcopy(pivots["hand_r"])})
    # Keep temporary weapon/socket geometry attached to the new right hand.
    for name in ("knife", "cannon", "lance", "n2"):
        bone = next(item for item in geometry["bones"] if item["name"] == name)
        old_pivot = bone.get("pivot", [0, 0, 0])
        new_pivot = [pivots["hand_r"][0], pivots["hand_r"][1] - 5.0, pivots["hand_r"][2]]
        delta = [new_pivot[axis] - old_pivot[axis] for axis in range(3)]
        bone["pivot"] = new_pivot
        for cube in bone.get("cubes", []):
            cube["origin"] = [cube["origin"][axis] + delta[axis] for axis in range(3)]
            if "pivot" in cube:
                cube["pivot"] = [cube["pivot"][axis] + delta[axis] for axis in range(3)]
        if name == "cannon":
            bone.pop("cubes", None)
        pivots[name] = new_pivot
    return data, pivots


def ensure_foot_bones(geometry):
    """Add the ankle layer to a legacy 15-bone fallback skeleton."""
    bones = geometry["bones"]
    existing = {bone["name"] for bone in bones}
    for name, parent in (("foot_l", "shin_l"), ("foot_r", "shin_r")):
        if name not in existing:
            bones.append({"name": name, "parent": parent})


def ensure_finger_bones(geometry, finger_pivots):
    """Extend the shared rig contract with proximal and distal digit bones."""
    bones = geometry["bones"]
    existing = {bone["name"] for bone in bones}
    # Emit parents before child tips for Gecko and the offline preview.
    ordered = sorted(finger_pivots, key=lambda name: ("_tip_" in name, name))
    for name in ordered:
        if name not in existing:
            parent = (name.replace("_tip_", "_") if "_tip_" in name
                      else "hand_" + name[-1])
            bones.append({"name": name, "parent": parent})
            existing.add(name)


def build_mesh(positions, texcoords, normals, triangles, pivots, scale, minimum_y,
               finger_faces=None):
    finger_faces = finger_faces or {}
    components = connected_components(positions, triangles)
    face_family = {}
    for component in components:
        bounds = component_bounds(component, positions, triangles)
        family = component_family(component, bounds, positions, triangles)
        for face_index in component:
            face_family[face_index] = family
    parts = {}
    counts = {}
    for face_index, triangle in enumerate(triangles):
        source_points = [positions[ref[0]] for ref in triangle]
        centroid = tuple(sum(point[axis] for point in source_points) / 3.0 for axis in range(3))
        bone = finger_faces.get(face_index,
                                assign_bone(centroid, face_family[face_index]))
        pivot = pivots[bone]
        fallback_normal = face_normal(source_points)
        output = parts.setdefault(bone, [])
        for ref in triangle:
            position = positions[ref[0]]
            uv = texcoords[ref[1]] if ref[1] >= 0 else (0.0, 0.0)
            normal = normals[ref[2]] if ref[2] >= 0 else fallback_normal
            output.extend([
                round(position[0] * scale - pivot[0], 5),
                round((position[1] - minimum_y) * scale - pivot[1], 5),
                # Tigerar1's OBJ faces +Z; Project SEELE/Gecko entities face
                # -Z. Reflect Z once during import so cameras and weapons use
                # the same forward convention.
                round(-position[2] * scale - pivot[2], 5),
                round(uv[0] * 0.5, 6), round(1.0 - uv[1], 6),
                round(normal[0], 5), round(normal[1], 5), round(-normal[2], 5),
            ])
        counts[bone] = counts.get(bone, 0) + 1
    return {
        "format_version": 1,
        "source": "Tigerar1 Evangelion Unit-01 (CC BY-SA), local evaluation only",
        "model_height": MODEL_HEIGHT,
        "stride": 8,
        "parts": {bone: {"pivot": pivots[bone], "vertices": values}
                  for bone, values in sorted(parts.items())},
    }, counts


def build_atlas(source_texture):
    atlas = Image.new("RGBA", (ATLAS_WIDTH, ATLAS_HEIGHT), (0, 0, 0, 0))
    atlas.paste(Image.open(io.BytesIO(source_texture)).convert("RGBA"), (0, 0))
    atlas.paste(Image.open(BASE_TEXTURE).convert("RGBA"), (512, 0))
    return atlas


def sample_channel(channel, time):
    if not isinstance(channel, dict):
        return copy.deepcopy(channel)
    keyed = []
    for key, value in channel.items():
        try:
            keyed.append((float(key), value))
        except (TypeError, ValueError):
            pass
    if not keyed:
        return copy.deepcopy(channel)
    keyed.sort(key=lambda item: item[0])
    before = max((item for item in keyed if item[0] <= time),
                 default=keyed[0], key=lambda item: item[0])
    after = min((item for item in keyed if item[0] >= time),
                default=keyed[-1], key=lambda item: item[0])
    left = before[1].get("post", before[1].get("pre")) if isinstance(before[1], dict) else before[1]
    right = after[1].get("pre", after[1].get("post")) if isinstance(after[1], dict) else after[1]
    if before[0] == after[0] or not isinstance(left, list) or not isinstance(right, list):
        return copy.deepcopy(left)
    factor = (time - before[0]) / (after[0] - before[0])
    return [a + (b - a) * factor if isinstance(a, (int, float)) and isinstance(b, (int, float)) else a
            for a, b in zip(left, right)]


def static_pose(animation, time):
    bones = {}
    for bone, channels in animation.get("bones", {}).items():
        sampled = {name: {"0.0": sample_channel(channel, time)}
                   for name, channel in channels.items()}
        if sampled:
            bones[bone] = sampled
    return {"loop": True, "animation_length": 1.0, "bones": bones}


def retime_animation(animation, factor):
    """Scale every numeric Bedrock key time without touching key values."""
    result = copy.deepcopy(animation)
    result["animation_length"] = round(
        float(result.get("animation_length", 0.0)) * factor, 4)
    for channels in result.get("bones", {}).values():
        for channel_name, keyed in list(channels.items()):
            if not isinstance(keyed, dict):
                continue
            remapped = {}
            for key, value in keyed.items():
                try:
                    new_key = str(round(float(key) * factor, 4))
                except (TypeError, ValueError):
                    new_key = key
                remapped[new_key] = value
            channels[channel_name] = remapped
    return result


def _rotation(keys):
    return {"rotation": {time: value for time, value in keys.items()}}


def _position(keys):
    return {"position": {time: value for time, value in keys.items()}}


def _set_hand_curl(bones, side, curl=22, thumb=17, tip_curl=12, thumb_tip=4):
    """Close one anatomically matched hand around a weapon grip.

    The geodesic hand partition keeps each continuous shaft on its distal
    bone, so the second joint can now contribute a real hook instead of
    exposing loose triangle fragments. Runtime close-up comparison proved
    both imported hands close on positive local X. Mirroring the left sign
    opened its fingers and was the source of the flat weapon/punch hand.
    """
    direction = 1
    for digit in FINGER_ORDER:
        angle = thumb if digit == "thumb" else curl
        bones[f"finger_{digit}_{side}"] = _rotation(
            {"0.0": [angle * direction, 0, 0]})
        tip_angle = thumb_tip if digit == "thumb" else tip_curl
        bones[f"finger_{digit}_tip_{side}"] = _rotation(
            {"0.0": [tip_angle * direction, 0, 0]})


def _set_finger_curl(bones, curl=50, thumb=30, tip_curl=34, thumb_tip=14):
    """Close both hands with conservative angles that preserve the mesh."""
    for side in ("l", "r"):
        _set_hand_curl(bones, side, curl, thumb, tip_curl, thumb_tip)


def _set_firearm_grip(bones):
    """Author a support-hand grip plus a distinct right trigger finger."""
    # The imported fingers have two independently weighted joints.  Fifty
    # degrees only touched the outside of the receiver in the real client;
    # the distal segment still read as four straight claws.  This tighter
    # two-joint wrap closes around the grip without reaching the 70/55
    # self-intersection seen in the stress preview.
    _set_hand_curl(bones, "l", curl=60, thumb=34,
                   tip_curl=44, thumb_tip=16)
    _set_hand_curl(bones, "r", curl=60, thumb=34,
                   tip_curl=44, thumb_tip=16)
    # Keep the right index on the trigger instead of folding it into the
    # middle/ring/little-finger fist.
    bones["finger_index_r"] = _rotation({"0.0": [20, 0, 0]})
    bones["finger_index_tip_r"] = _rotation({"0.0": [9, 0, 0]})


def _set_knife_grip(bones):
    """Close a real fist around the reverse-grip hilt."""
    _set_hand_curl(bones, "r", curl=72, thumb=44,
                   tip_curl=54, thumb_tip=22)
    _set_hand_curl(bones, "l", curl=22, thumb=15,
                   tip_curl=14, thumb_tip=6)


def _set_claw_hand(bones, side):
    """Animate a partially closed biological hand through one raking strike."""
    for digit in FINGER_ORDER:
        root_ready = 18 if digit != "thumb" else 14
        root_windup = 36 if digit != "thumb" else 25
        root_contact = 29 if digit != "thumb" else 22
        tip_ready = 9 if digit != "thumb" else 5
        tip_windup = 25 if digit != "thumb" else 11
        tip_contact = 20 if digit != "thumb" else 9
        bones[f"finger_{digit}_{side}"] = _rotation({
            "0.0": [root_ready, 0, 0],
            "0.14": [root_windup, 0, 0],
            "0.34": [root_contact, 0, 0],
            "0.54": [root_ready, 0, 0],
            "0.68": [root_ready, 0, 0],
        })
        bones[f"finger_{digit}_tip_{side}"] = _rotation({
            "0.0": [tip_ready, 0, 0],
            "0.14": [tip_windup, 0, 0],
            "0.34": [tip_contact, 0, 0],
            "0.54": [tip_ready, 0, 0],
            "0.68": [tip_ready, 0, 0],
        })


def repair_tiger_runtime_animations(data):
    """Retarget authored poses to the imported Tiger rig's Gecko axes.

    The converter and offline preview deliberately reproduce GeckoLib 4's
    Bedrock pivot reflection, X/Y rotation signs, animated-X translation sign,
    and the local triangle layer's emitted-X reflection.  Pose signs here
    therefore match the actual runtime path instead of the raw OBJ coordinate
    system.  Keep this retarget local to the imported mesh; the fallback cube
    rig keeps its own animation catalogue.
    """
    animations = data["animations"]
    prefix = "animation.eva_unit01."

    idle = animations[prefix + "idle"]["bones"]
    idle["arm_l"] = _rotation({"0.0": [-5, 0, -5], "1.6": [-6, 0, -6],
                                "3.2": [-5, 0, -5]})
    idle["arm_r"] = _rotation({"0.0": [-5, 0, 5], "1.6": [-6, 0, 6],
                                "3.2": [-5, 0, 5]})
    idle["forearm_l"] = _rotation({"0.0": [4, 0, 0], "1.6": [5, 0, 0],
                                    "3.2": [4, 0, 0]})
    idle["forearm_r"] = copy.deepcopy(idle["forearm_l"])

    def claw_strike(side):
        """A shoulder-led human rake, not an iron-golem straight punch."""
        other = "l" if side == "r" else "r"
        sign = 1 if side == "r" else -1
        bones = {
            "root": _position({
                "0.0": [0, 0, 0], "0.14": [0, 0.35, 0.6],
                "0.34": [0, 0.8, -1.2], "0.54": [0, 0.25, -0.4],
                "0.68": [0, 0, 0]}),
            "torso_lower": _rotation({
                "0.0": [0, 0, 0], "0.14": [1, 9 * sign, 0],
                "0.34": [5, -14 * sign, 0], "0.54": [2, -5 * sign, 0],
                "0.68": [0, 0, 0]}),
            "torso_upper": _rotation({
                "0.0": [0, 0, 0], "0.14": [-3, 21 * sign, 0],
                "0.34": [7, -29 * sign, -3 * sign],
                "0.54": [3, -10 * sign, 0], "0.68": [0, 0, 0]}),
            f"arm_{side}": _rotation({
                "0.0": [-5, 0, 5 * sign],
                "0.14": [22, -14 * sign, 27 * sign],
                "0.34": [-108, -18 * sign, 18 * sign],
                "0.54": [-48, -7 * sign, 12 * sign],
                "0.68": [-5, 0, 5 * sign]}),
            f"forearm_{side}": _rotation({
                "0.0": [4, 0, 0], "0.14": [-72, 0, -12 * sign],
                "0.34": [-18, 0, 7 * sign],
                "0.54": [-46, 0, 3 * sign], "0.68": [4, 0, 0]}),
            f"hand_{side}": _rotation({
                "0.0": [0, 0, 0], "0.14": [0, 0, -14 * sign],
                "0.34": [0, 0, 12 * sign], "0.54": [0, 0, 4 * sign],
                "0.68": [0, 0, 0]}),
            # The free hand guards the face and ribs instead of dangling like
            # the unused arm of a Minecraft mob attack.
            f"arm_{other}": _rotation({
                "0.0": [-5, 0, -5 * sign], "0.14": [-28, 8 * sign, -18 * sign],
                "0.34": [-36, 12 * sign, -20 * sign],
                "0.54": [-20, 5 * sign, -12 * sign],
                "0.68": [-5, 0, -5 * sign]}),
            f"forearm_{other}": _rotation({
                "0.0": [4, 0, 0], "0.14": [-68, 5 * sign, 16 * sign],
                "0.34": [-76, 8 * sign, 20 * sign],
                "0.54": [-42, 3 * sign, 10 * sign],
                "0.68": [4, 0, 0]}),
        }
        _set_claw_hand(bones, side)
        _set_hand_curl(bones, other, curl=24, thumb=16,
                       tip_curl=15, thumb_tip=6)
        return {"animation_length": 0.68, "bones": bones}

    animations[prefix + "melee"] = claw_strike("r")
    animations[prefix + "melee_left"] = claw_strike("l")

    walk = animations[prefix + "walk"]["bones"]
    # Keep the gait inside a human range. The imported source used a very
    # large vertical bob and near-straight pendulum arms; at EVA scale that
    # read as skating between two extreme keyframes rather than transferring
    # weight through a planted foot.
    walk["root"] = _position({
        "0.0": [0, 0.52, 0], "0.25": [0, 0.87, 0],
        "0.5": [0, 0.52, 0], "0.75": [0, 0.87, 0],
        "1.0": [0, 0.52, 0]})
    walk["leg_l"] = _rotation({
        "0.0": [-23, 0, -1], "0.25": [-8, 0, -1],
        "0.5": [23, 0, -1], "0.75": [10, 0, -1],
        "1.0": [-23, 0, -1]})
    walk["leg_r"] = _rotation({
        "0.0": [23, 0, 1], "0.25": [10, 0, 1],
        "0.5": [-23, 0, 1], "0.75": [-8, 0, 1],
        "1.0": [23, 0, 1]})
    walk["shin_l"] = _rotation({
        "0.0": [7, 0, 0], "0.25": [27, 0, 0], "0.5": [4, 0, 0],
        "0.75": [11, 0, 0], "1.0": [7, 0, 0]})
    walk["shin_r"] = _rotation({
        "0.0": [4, 0, 0], "0.25": [11, 0, 0], "0.5": [7, 0, 0],
        "0.75": [27, 0, 0], "1.0": [4, 0, 0]})
    walk["foot_l"] = _rotation({
        "0.0": [-7, 0, 1], "0.25": [-17, 0, 1],
        "0.5": [7, 0, 1], "0.75": [2, 0, 1],
        "1.0": [-7, 0, 1]})
    walk["foot_r"] = _rotation({
        "0.0": [7, 0, -1], "0.25": [2, 0, -1],
        "0.5": [-7, 0, -1], "0.75": [-17, 0, -1],
        "1.0": [7, 0, -1]})
    walk["arm_l"] = _rotation({
        "0.0": [14, 0, -4], "0.5": [-11, 0, -4], "1.0": [14, 0, -4]})
    walk["arm_r"] = _rotation({
        "0.0": [-11, 0, 4], "0.5": [14, 0, 4], "1.0": [-11, 0, 4]})
    # EVA is a biological humanoid, not a pair of rigid pendulums.  Flex the
    # elbows through the gait so neither straight arm disappears behind the
    # pilot camera at foot contact; the opposite phasing preserves a readable
    # human walk in third person and shows both real arms when looking down.
    walk["forearm_l"] = _rotation({
        "0.0": [-33, 0, 0], "0.5": [-24, 0, 0], "1.0": [-33, 0, 0]})
    walk["forearm_r"] = _rotation({
        "0.0": [-24, 0, 0], "0.5": [-33, 0, 0], "1.0": [-24, 0, 0]})
    walk["torso_lower"] = _rotation({
        "0.0": [3, 1.5, 0], "0.5": [3, -1.5, 0], "1.0": [3, 1.5, 0]})
    walk["torso_upper"] = _rotation({
        "0.0": [2, 2.5, 0], "0.5": [2, -2.5, 0], "1.0": [2, 2.5, 0]})

    run = animations[prefix + "run"]["bones"]
    run["leg_l"] = _rotation({
        "0.0": [-32, 0, -2], "0.155": [4, 0, -2],
        "0.31": [32, 0, -2], "0.465": [-4, 0, -2],
        "0.62": [-32, 0, -2]})
    run["leg_r"] = _rotation({
        "0.0": [32, 0, 2], "0.155": [-4, 0, 2],
        "0.31": [-32, 0, 2], "0.465": [4, 0, 2],
        "0.62": [32, 0, 2]})
    run["shin_l"] = _rotation({
        "0.0": [18, 0, 0], "0.155": [44, 0, 0],
        "0.31": [6, 0, 0], "0.465": [12, 0, 0],
        "0.62": [18, 0, 0]})
    run["shin_r"] = _rotation({
        "0.0": [6, 0, 0], "0.155": [12, 0, 0],
        "0.31": [18, 0, 0], "0.465": [44, 0, 0],
        "0.62": [6, 0, 0]})
    run["foot_l"] = _rotation({
        "0.0": [-10, 0, 2], "0.155": [-25, 0, 2],
        "0.31": [12, 0, 2], "0.465": [4, 0, 2],
        "0.62": [-10, 0, 2]})
    run["foot_r"] = _rotation({
        "0.0": [12, 0, -2], "0.155": [4, 0, -2],
        "0.31": [-10, 0, -2], "0.465": [-25, 0, -2],
        "0.62": [12, 0, -2]})
    run["arm_l"] = _rotation({
        "0.0": [28, 0, -7], "0.31": [-28, 0, -7], "0.62": [28, 0, -7]})
    run["arm_r"] = _rotation({
        "0.0": [-28, 0, 7], "0.31": [28, 0, 7], "0.62": [-28, 0, 7]})
    run["forearm_l"] = _rotation({
        "0.0": [-64, 0, 0], "0.31": [-50, 0, 0], "0.62": [-64, 0, 0]})
    run["forearm_r"] = _rotation({
        "0.0": [-50, 0, 0], "0.31": [-64, 0, 0], "0.62": [-50, 0, 0]})
    run["root"] = _position({
        "0.0": [0, 0.52, 0], "0.155": [0, 1.0, 0],
        "0.31": [0, 0.52, 0], "0.465": [0, 1.0, 0],
        "0.62": [0, 0.52, 0]})
    run["torso_lower"] = _rotation({
        "0.0": [8, 2, 0], "0.31": [8, -2, 0], "0.62": [8, 2, 0]})
    run["torso_upper"] = _rotation({
        "0.0": [5, 4, 0], "0.31": [5, -4, 0], "0.62": [5, 4, 0]})

    # Take-off is a one-shot strike layer fired on the exact server jump
    # impulse.  The base airborne animation must not loop back through a deep
    # crouch while the entity is already tens of blocks above the ground.
    takeoff = {"animation_length": 0.38, "bones": {
        "root": _position({
            "0.0": [0, 0, 0], "0.08": [0, -2.0, 0],
            "0.22": [0, 1.0, 0], "0.38": [0, 0, 0]}),
        "torso_lower": _rotation({
            "0.0": [8, 0, 0], "0.08": [16, 0, 0],
            "0.22": [-5, 0, 0], "0.38": [1, 0, 0]}),
        "torso_upper": _rotation({
            "0.0": [4, 0, 0], "0.08": [10, 0, 0],
            "0.22": [-8, 0, 0], "0.38": [-2, 0, 0]}),
        "arm_l": _rotation({
            "0.0": [-18, 0, -8], "0.08": [-10, 0, -13],
            "0.22": [-108, 0, -11], "0.38": [-72, 0, -14]}),
        "forearm_l": _rotation({
            "0.0": [-28, 0, 0], "0.08": [-52, 0, 0],
            "0.22": [-16, 0, 0], "0.38": [-30, 0, 0]}),
        "arm_r": _rotation({
            "0.0": [-18, 0, 8], "0.08": [-10, 0, 13],
            "0.22": [-108, 0, 11], "0.38": [-72, 0, 14]}),
        "forearm_r": _rotation({
            "0.0": [-28, 0, 0], "0.08": [-52, 0, 0],
            "0.22": [-16, 0, 0], "0.38": [-30, 0, 0]}),
        "leg_l": _rotation({
            "0.0": [-34, 0, -3], "0.08": [-48, 0, -3],
            "0.22": [-4, 0, -3], "0.38": [-14, 0, -4]}),
        "shin_l": _rotation({
            "0.0": [58, 0, 0], "0.08": [74, 0, 0],
            "0.22": [8, 0, 0], "0.38": [28, 0, 0]}),
        "foot_l": _rotation({
            "0.0": [-28, 0, 3], "0.08": [-38, 0, 3],
            "0.22": [-4, 0, 3], "0.38": [-14, 0, 3]}),
        "leg_r": _rotation({
            "0.0": [-34, 0, 3], "0.08": [-48, 0, 3],
            "0.22": [-4, 0, 3], "0.38": [-7, 0, 4]}),
        "shin_r": _rotation({
            "0.0": [58, 0, 0], "0.08": [74, 0, 0],
            "0.22": [8, 0, 0], "0.38": [17, 0, 0]}),
        "foot_r": _rotation({
            "0.0": [-28, 0, -3], "0.08": [-38, 0, -3],
            "0.22": [-4, 0, -3], "0.38": [-9, 0, -3]}),
    }}
    animations[prefix + "takeoff"] = takeoff

    # Airborne hold: a long, slightly asymmetric biological silhouette with
    # hands ahead of the shoulder plane and no repeated squat.
    jump = animations[prefix + "jump"]
    jump["loop"] = True
    jump["animation_length"] = 1.2
    jump["bones"].update({
        "torso_lower": _rotation({"0.0": [1, 0, 0], "1.2": [1, 0, 0]}),
        "torso_upper": _rotation({"0.0": [-2, 0, 0], "1.2": [-2, 0, 0]}),
        "arm_l": _rotation({"0.0": [-60, 0, -14], "1.2": [-58, 0, -15]}),
        "forearm_l": _rotation({"0.0": [-30, 0, 0], "1.2": [-32, 0, 0]}),
        "arm_r": _rotation({"0.0": [-60, 0, 14], "1.2": [-62, 0, 15]}),
        "forearm_r": _rotation({"0.0": [-30, 0, 0], "1.2": [-28, 0, 0]}),
        "leg_l": _rotation({"0.0": [-14, 0, -4], "1.2": [-16, 0, -4]}),
        "shin_l": _rotation({"0.0": [28, 0, 0], "1.2": [31, 0, 0]}),
        "foot_l": _rotation({"0.0": [-14, 0, 3], "1.2": [-15, 0, 3]}),
        "leg_r": _rotation({"0.0": [-7, 0, 4], "1.2": [-6, 0, 4]}),
        "shin_r": _rotation({"0.0": [17, 0, 0], "1.2": [15, 0, 0]}),
        "foot_r": _rotation({"0.0": [-9, 0, -3], "1.2": [-8, 0, -3]}),
    })
    animations[prefix + "fall"]["bones"].update({
        "torso_lower": _rotation({"0.0": [-3, 0, 0]}),
        "torso_upper": _rotation({"0.0": [-5, 0, 0]}),
        # Landing preparation keeps the hands ahead of the face and chest.
        # A 42-degree lateral spread put both hands at x=+/-60 model pixels,
        # completely outside the pilot's horizontal FOV.  Forward flex plus
        # a smaller elbow-out angle reads as a human bracing posture in third
        # person while the attached real arms remain in opposite peripheral
        # regions of the first-person view.
        "arm_l": _rotation({"0.0": [-42, 0, -22]}),
        "forearm_l": _rotation({"0.0": [-32, 0, 0]}),
        "arm_r": _rotation({"0.0": [-42, 0, 22]}),
        "forearm_r": _rotation({"0.0": [-32, 0, 0]}),
        "leg_l": _rotation({"0.0": [-8, 0, -4]}),
        "shin_l": _rotation({"0.0": [18, 0, 0]}),
        "foot_l": _rotation({"0.0": [-10, 0, 4]}),
        "leg_r": _rotation({"0.0": [8, 0, 4]}),
        "shin_r": _rotation({"0.0": [18, 0, 0]}),
        "foot_r": _rotation({"0.0": [-26, 0, -4]}),
    })

    crouch_bones = {
        "root": _position({"0.0": [0, -39.15, 0]}),
        "torso_lower": _rotation({"0.0": [0, 0, 0]}),
        "torso_upper": _rotation({"0.0": [5, 0, 0], "0.8": [3, 0, 0],
                                   "1.6": [5, 0, 0]}),
        # Human single-knee support: a forward thigh, vertical shin and level
        # planted sole. The real Tiger mesh solver measures the front foot at
        # +0.8 px and the rear support at -0.02 px. The former -88/+48/+40
        # chain angled the shin farther forward and left that foot 22.8 px in
        # the air even though the rear knee was grounded.
        "leg_l": _rotation({"0.0": [-75, 0, -3]}),
        "shin_l": _rotation({"0.0": [75, 0, 0]}),
        "foot_l": _rotation({"0.0": [0, 0, 0]}),
        "leg_r": _rotation({"0.0": [5.13, 0, 3]}),
        "shin_r": _rotation({"0.0": [80.71, 0, 0]}),
        "foot_r": _rotation({"0.0": [-85.84, 0, 0]}),
        # Relaxed guard rather than two locked zombie arms. Elbows stay bent
        # and low enough to remain in the shared first-person periphery.
        "arm_l": _rotation({"0.0": [-18, 0, -7]}),
        "forearm_l": _rotation({"0.0": [-80, 0, 0]}),
        "arm_r": _rotation({"0.0": [-18, 0, 7]}),
        "forearm_r": _rotation({"0.0": [-80, 0, 0]}),
    }
    animations[prefix + "crouch"] = {
        "loop": True, "animation_length": 1.6, "bones": crouch_bones}
    # Moving while crouched is a two-foot low gait, not the static single-knee
    # pose translated across the floor. Both knees remain loaded while the
    # lead and trail feet exchange roles at half-cycle.
    crouch_walk = {"loop": True, "animation_length": 1.0, "bones": {}}
    crouch_walk["bones"]["root"] = _position({
        # Keep the moving pelvis within 5-7 px of the static kneel.  The old
        # -10/-13 curve raised the EVA almost thirty pixels the instant W was
        # pressed, which looked like standing up between every crouched step.
        "0.0": [0, -32, 0], "0.25": [0, -34, 0],
        "0.5": [0, -32, 0], "0.75": [0, -34, 0],
        "1.0": [0, -32, 0]})
    crouch_walk["bones"]["torso_lower"] = _rotation({
        "0.0": [8, 2, 0], "0.25": [8, 0, 0],
        "0.5": [8, -2, 0], "0.75": [8, 0, 0],
        "1.0": [8, 2, 0]})
    crouch_walk["bones"]["torso_upper"] = _rotation({
        "0.0": [-2, 3, 0], "0.25": [-3, 0, 0],
        "0.5": [-2, -3, 0], "0.75": [-3, 0, 0],
        "1.0": [-2, 3, 0]})
    crouch_walk["bones"]["leg_l"] = _rotation({
        "0.0": [-59.49, 0, -3], "0.25": [-53.12, 0, -3],
        "0.5": [-34.23, 0, -3], "0.75": [-45.02, 0, -3],
        "1.0": [-59.49, 0, -3]})
    crouch_walk["bones"]["shin_l"] = _rotation({
        "0.0": [96.12, 0, 0], "0.25": [106.19, 0, 0],
        "0.5": [95.3, 0, 0], "0.75": [101.18, 0, 0],
        "1.0": [96.12, 0, 0]})
    crouch_walk["bones"]["foot_l"] = _rotation({
        "0.0": [-44.67, 0, 3], "0.25": [-61.08, 0, 3],
        "0.5": [-69.15, 0, 3], "0.75": [-64.21, 0, 3],
        "1.0": [-44.67, 0, 3]})
    crouch_walk["bones"]["leg_r"] = _rotation({
        "0.0": [-34.23, 0, 3], "0.25": [-45.02, 0, 3],
        "0.5": [-59.49, 0, 3], "0.75": [-53.12, 0, 3],
        "1.0": [-34.23, 0, 3]})
    crouch_walk["bones"]["shin_r"] = _rotation({
        "0.0": [95.3, 0, 0], "0.25": [101.18, 0, 0],
        "0.5": [96.12, 0, 0], "0.75": [106.19, 0, 0],
        "1.0": [95.3, 0, 0]})
    crouch_walk["bones"]["foot_r"] = _rotation({
        "0.0": [-69.15, 0, -3], "0.25": [-64.21, 0, -3],
        "0.5": [-44.67, 0, -3], "0.75": [-61.08, 0, -3],
        "1.0": [-69.15, 0, -3]})
    crouch_walk["bones"]["arm_l"] = _rotation({
        "0.0": [-21, 0, -7], "0.5": [-15, 0, -7], "1.0": [-21, 0, -7]})
    crouch_walk["bones"]["forearm_l"] = _rotation({
        "0.0": [-84, 0, 0], "0.5": [-76, 0, 0], "1.0": [-84, 0, 0]})
    crouch_walk["bones"]["arm_r"] = _rotation({
        "0.0": [-15, 0, 7], "0.5": [-21, 0, 7], "1.0": [-15, 0, 7]})
    crouch_walk["bones"]["forearm_r"] = _rotation({
        "0.0": [-76, 0, 0], "0.5": [-84, 0, 0], "1.0": [-76, 0, 0]})
    animations[prefix + "crouch_walk"] = crouch_walk

    prone_bones = {
        # Belly-down rifle-prone silhouette. Gecko negates authored X, so +90
        # becomes the runtime sternum-down quarter turn. The old -46.4 root
        # left the abdomen suspended on both knees like a dog crawl; -70 puts
        # chest, pelvis and boots on one low human contact envelope.
        "root": _position({"0.0": [0, -70, 0]}),
        "torso_lower": _rotation({"0.0": [90, 0, 0]}),
        "torso_upper": _rotation({"0.0": [-8, 0, 0]}),
        "head": _rotation({"0.0": [-72, 0, 0]}),
        "leg_l": _rotation({"0.0": [0, 0, -4]}),
        "shin_l": _rotation({"0.0": [0, 0, 0]}),
        "foot_l": _rotation({"0.0": [0, 0, 4]}),
        "leg_r": _rotation({"0.0": [0, 0, 4]}),
        "shin_r": _rotation({"0.0": [0, 0, 0]}),
        "foot_r": _rotation({"0.0": [0, 0, -4]}),
        # Keep each elbow under its own shoulder. Large opposing local-Z
        # angles made the world-space forearms cross directly in front of the
        # head socket even though the third-person silhouette looked usable.
        "arm_l": _rotation({"0.0": [-158, 0, -5]}),
        "forearm_l": _rotation({"0.0": [-25, 0, 2]}),
        "hand_l": _rotation({"0.0": [0, 0, 0]}),
        "arm_r": _rotation({"0.0": [-158, 0, 5]}),
        "forearm_r": _rotation({"0.0": [-25, 0, -2]}),
        "hand_r": _rotation({"0.0": [0, 0, 0]}),
    }
    animations[prefix + "prone"] = {
        "loop": True, "animation_length": 2.4, "bones": prone_bones}
    crawl = copy.deepcopy(animations[prefix + "prone"])
    crawl["animation_length"] = 1.4
    crawl["bones"]["root"] = _position({
        # Active low crawl rides a few pixels above the passive prone contact
        # envelope. This leaves room for the drawn knee and pulling forearm
        # without turning the pose into either swimming or ground clipping.
        "0.0": [-0.25, -61.6, 0], "0.35": [0, -61.5, 0],
        "0.7": [0.25, -61.6, 0], "1.05": [0, -61.5, 0],
        "1.4": [-0.25, -61.6, 0]})
    crawl["bones"]["torso_lower"] = _rotation({
        "0.0": [90, 1.2, 0], "0.7": [90, -1.2, 0], "1.4": [90, 1.2, 0]})
    crawl["bones"]["torso_upper"] = _rotation({
        "0.0": [-8, -1.5, 0], "0.7": [-8, 1.5, 0], "1.4": [-8, -1.5, 0]})
    crawl["bones"]["leg_l"] = _rotation({
        # Human low-crawl gait: one knee draws outward while the opposite leg
        # stays long, then the pair trades roles at half-cycle. Small local-X
        # flex plus local-Z abduction keeps the thigh parallel to the ground;
        # the former +/-5-only motion was visually indistinguishable from a
        # static prone pose.
        "0.0": [-10, 0, -18], "0.35": [-5, 0, -11],
        "0.7": [0, 0, -4], "1.05": [-5, 0, -11],
        "1.4": [-10, 0, -18]})
    crawl["bones"]["leg_r"] = _rotation({
        "0.0": [0, 0, 4], "0.35": [-5, 0, 11],
        "0.7": [-10, 0, 18], "1.05": [-5, 0, 11],
        "1.4": [0, 0, 4]})
    crawl["bones"]["shin_l"] = _rotation({
        "0.0": [10, 0, 0], "0.35": [5, 0, 0],
        "0.7": [0, 0, 0], "1.05": [5, 0, 0],
        "1.4": [10, 0, 0]})
    crawl["bones"]["shin_r"] = _rotation({
        "0.0": [0, 0, 0], "0.35": [5, 0, 0],
        "0.7": [10, 0, 0], "1.05": [5, 0, 0],
        "1.4": [0, 0, 0]})
    crawl["bones"]["arm_l"] = _rotation({
        "0.0": [-160, 0, -5], "0.35": [-152, 0, -5],
        "0.7": [-145, 0, -5], "1.05": [-152, 0, -5],
        "1.4": [-160, 0, -5]})
    crawl["bones"]["arm_r"] = _rotation({
        "0.0": [-145, 0, 5], "0.35": [-152, 0, 5],
        "0.7": [-160, 0, 5], "1.05": [-152, 0, 5],
        "1.4": [-145, 0, 5]})
    crawl["bones"]["forearm_l"] = _rotation({
        "0.0": [-22, 0, 2], "0.35": [-38, 0, 2],
        "0.7": [-55, 0, 2], "1.05": [-38, 0, 2],
        "1.4": [-22, 0, 2]})
    crawl["bones"]["forearm_r"] = _rotation({
        "0.0": [-55, 0, -2], "0.35": [-38, 0, -2],
        "0.7": [-22, 0, -2], "1.05": [-38, 0, -2],
        "1.4": [-55, 0, -2]})
    animations[prefix + "crawl"] = crawl

    animations[prefix + "aim"] = {
        "loop": True, "animation_length": 1.2, "bones": {
            # Stabilise the shoulder line while the locomotion controller
            # continues to animate pelvis and legs underneath it.
            "torso_upper": _rotation({
                "0.0": [0, 0, 0], "0.6": [0, 0, 0],
                "1.2": [0, 0, 0]}),
            # Shoulder the receiver instead of locking both elbows.  The
            # right/trigger hand stays close to the face while the left hand
            # reaches the fore-end, so the same world skeleton has a readable
            # first-person silhouette and a credible third-person firing line.
            # Open the trigger elbow and keep it outside the rib armour.  The
            # former -52/-81 chain folded the joint into an acute hook under
            # both guns; this solved shoulder/forearm pair keeps the wrist on
            # the receiver while reading as a human right-shoulder stance.
            "arm_r": _rotation({"0.0": [-62, -10, 12], "0.6": [-63, -10, 12],
                                  "1.2": [-62, -10, 12]}),
            "forearm_r": _rotation({"0.0": [-68, -8, -8]}),
            "hand_r": _rotation({"0.0": [0, 0, 0]}),
            # Solve the support wrist into the receiver volume at roughly
            # (0.5,160,-58.6).  The lower target used before finger flexion
            # left a visibly closed fist hanging beneath the fore-end.
            "arm_l": _rotation({"0.0": [-97.41, 26.22, -1.84],
                                  "0.6": [-98.2, 26.22, -1.84],
                                  "1.2": [-97.41, 26.22, -1.84]}),
            "forearm_l": _rotation({"0.0": [2.83, -8.18, -6.28]}),
            "hand_l": _rotation({"0.0": [0, 0, 0]}),
            # The receiver is parented to the bent trigger wrist.  Cancel the
            # wrist's upward pitch so the bore remains on the chassis forward
            # axis rather than pointing over the EVA's head.
            # Numerically solved against the actual Pallet Rifle muzzle cap:
            # the bore is parallel to model -Z instead of 18 degrees left.
            # Solved from the installed Kantrophe mesh after the elbow
            # correction: far-cap vector [0.053, -0.059, -91.272].
            "cannon": _rotation({"0.0": [40.24, -8.41, 20.45]}),
        }}
    _set_firearm_grip(animations[prefix + "aim"]["bones"])
    # The TV Pallet Rifle uses the same semantic socket but its authored
    # barrel axis differs by about two degrees.  Give it an independent
    # attachment correction instead of compromising both weapon muzzles.
    rifle_aim = copy.deepcopy(animations[prefix + "aim"])
    rifle_aim["bones"]["cannon"] = _rotation({
        "0.0": [38.32, -8.41, 20.30]})
    animations[prefix + "rifle_aim"] = rifle_aim
    animations[prefix + "prone_aim"] = {
        "loop": True, "animation_length": 1.2, "bones": {
            # A separate elbows-braced firing pose.  Reusing the standing aim
            # layer on the torso's prone quarter-turn sent the cannon straight
            # through the ground.  Both hands now meet around the receiver and
            # the cannon socket cancels the remaining wrist elevation.
            "arm_r": _rotation({"0.0": [-158, 0, 14]}),
            "forearm_r": _rotation({"0.0": [-25, 0, -8]}),
            "hand_r": _rotation({"0.0": [0, 0, 0]}),
            "arm_l": _rotation({"0.0": [-158, 0, -14]}),
            "forearm_l": _rotation({"0.0": [-25, 0, 8]}),
            "hand_l": _rotation({"0.0": [0, 0, 0]}),
            # Match the prone pilot's twelve-degree downward sightline.  The
            # previous one-degree socket left the barrel high above the
            # crosshair in the shared world-body first-person view even
            # though its third-person silhouette looked almost horizontal.
            # Prone rotates the parent chain by a quarter turn and therefore
            # needs its own solved muzzle correction.
            "cannon": _rotation({"0.0": [9.89, -3.95, 21.28]}),
        }}
    _set_firearm_grip(animations[prefix + "prone_aim"]["bones"])

    n2_ready_bones = {
        # Right hand carries the bomb by its protected handle; the left hand
        # braces the arming panel close to the sternum.
        "torso_upper": _rotation({
            "0.0": [2, 2, 0], "0.7": [3, 2, 0], "1.4": [2, 2, 0]}),
        "arm_r": _rotation({
            "0.0": [-37.97, -19.21, 8.86],
            "0.7": [-38.7, -19.21, 8.86],
            "1.4": [-37.97, -19.21, 8.86]}),
        "forearm_r": _rotation({"0.0": [-77.49, -8.98, 1.15]}),
        "hand_r": _rotation({"0.0": [0, 0, 4]}),
        "arm_l": _rotation({
            "0.0": [-57.16, 22.15, -10.54],
            "0.7": [-57.9, 22.15, -10.54],
            "1.4": [-57.16, 22.15, -10.54]}),
        "forearm_l": _rotation({"0.0": [-47.12, 5.58, 3.22]}),
        "hand_l": _rotation({"0.0": [0, 0, -3]}),
        "n2": _rotation({"0.0": [0, 0, 0]}),
    }
    _set_hand_curl(n2_ready_bones, "r", curl=42, thumb=28,
                   tip_curl=26, thumb_tip=12)
    _set_hand_curl(n2_ready_bones, "l", curl=36, thumb=25,
                   tip_curl=22, thumb_tip=10)
    animations[prefix + "n2_ready"] = {
        "loop": True, "animation_length": 1.4, "bones": n2_ready_bones}

    knife_ready_bones = {
        # Reverse grip: the weapon hand is folded beside the right ribs with
        # the blade running down the forearm. The left hand remains a forward
        # guard instead of mirroring the weapon arm like a zombie pose.
        "torso_upper": _rotation({
            "0.0": [1, 3, 0], "0.6": [2, 4, 0], "1.2": [1, 3, 0]}),
        "arm_r": _rotation({
            "0.0": [-16.55, -14.63, 20.32],
            "0.6": [-17.25, -14.63, 20.32],
            "1.2": [-16.55, -14.63, 20.32]}),
        "forearm_r": _rotation({"0.0": [-107.73, -23.77, -5.93]}),
        "hand_r": _rotation({"0.0": [0, 0, -8]}),
        "arm_l": _rotation({
            "0.0": [-30.35, -1.91, -24.76],
            "0.6": [-31.0, -1.91, -24.76],
            "1.2": [-30.35, -1.91, -24.76]}),
        "forearm_l": _rotation({"0.0": [-74.23, 29.94, 30.51]}),
        "hand_l": _rotation({"0.0": [0, 0, 0]}),
        "knife": _rotation({"0.0": [90, 0, 12]}),
    }
    animations[prefix + "knife_ready"] = {
        "loop": True, "animation_length": 1.2, "bones": knife_ready_bones}
    _set_knife_grip(knife_ready_bones)

    # One anatomically readable reverse-grip slash. The knife always remains
    # in the right hand; alternating a left-hand clip while the attachment
    # stayed on hand_r was the source of the crossed-arm attack.
    knife_attack = copy.deepcopy(animations[prefix + "knife_ready"])
    knife_attack.pop("loop", None)
    knife_attack["animation_length"] = 0.62
    bones = knife_attack["bones"]
    bones["root"] = _position({
        "0.0": [0, 0, 0], "0.14": [0, 0.55, 1],
        "0.32": [0, 1.35, -2], "0.48": [0, 0.8, -1],
        "0.62": [0, 0, 0]})
    bones["torso_lower"] = _rotation({
        "0.0": [0, 0, 0], "0.14": [2, 8, 0],
        "0.32": [7, -12, 0], "0.48": [3, -4, 0],
        "0.62": [0, 0, 0]})
    bones["torso_upper"] = _rotation({
        "0.0": [1, 3, 0], "0.14": [-2, 13, 0],
        "0.32": [8, -16, 0], "0.48": [4, -5, 0],
        "0.62": [1, 3, 0]})
    bones["arm_r"] = _rotation({
        "0.0": [-16.55, -14.63, 20.32],
        "0.14": [-30.55, -16.21, 14.84],
        "0.32": [-44.34, 7.49, 23.88],
        "0.48": [-30.97, -1.22, 24.14],
        "0.62": [-16.55, -14.63, 20.32]})
    bones["forearm_r"] = _rotation({
        "0.0": [-107.73, -23.77, -5.93],
        "0.14": [-123.81, -27.42, -10.57],
        "0.32": [-64.85, -13.23, 7.26],
        "0.48": [-92.23, -27.49, -3.96],
        "0.62": [-107.73, -23.77, -5.93]})
    bones["hand_r"] = _rotation({
        "0.0": [0, 0, -8], "0.14": [0, 0, -12],
        "0.32": [0, 0, 5], "0.48": [0, 0, -2],
        "0.62": [0, 0, -8]})
    bones["arm_l"] = _rotation({
        "0.0": [-30.35, -1.91, -24.76],
        "0.14": [-14.82, -10.12, -31.91],
        "0.32": [-45.82, 18.67, -8.28],
        "0.48": [-35.67, 5.52, -15.84],
        "0.62": [-30.35, -1.91, -24.76]})
    bones["forearm_l"] = _rotation({
        "0.0": [-74.23, 29.94, 30.51],
        "0.14": [-84.44, 32.72, 35.96],
        "0.32": [-74.28, 34.51, 30.87],
        "0.48": [-76.73, 29.12, 30.96],
        "0.62": [-74.23, 29.94, 30.51]})
    bones["knife"] = _rotation({"0.0": [90, 0, 12]})
    _set_knife_grip(bones)
    knife_attack = retime_animation(knife_attack, 0.86 / 0.62)
    animations[prefix + "knife"] = knife_attack
    animations[prefix + "knife_left"] = copy.deepcopy(knife_attack)

    # RMB uses a deliberate single-hand power slash.  It retains the reverse
    # grip and the free-hand guard; only the right arm owns the blade.  This
    # replaces the generic two-handed smash that made the knife jump between
    # both palms.
    knife_heavy = retime_animation(knife_attack, 1.10 / 0.86)
    knife_heavy["bones"]["root"] = _position({
        "0.0": [0, 0, 0], "0.25": [0, 0.7, 1.3],
        "0.57": [0, 1.7, -4.0], "0.86": [0, 0.7, -1.4],
        "1.1": [0, 0, 0]})
    knife_heavy["bones"]["torso_lower"] = _rotation({
        "0.0": [0, 0, 0], "0.25": [3, 12, 0],
        "0.57": [10, -19, 0], "0.86": [4, -6, 0],
        "1.1": [0, 0, 0]})
    knife_heavy["bones"]["torso_upper"] = _rotation({
        "0.0": [1, 3, 0], "0.25": [-4, 18, 0],
        "0.57": [11, -24, 0], "0.86": [5, -7, 0],
        "1.1": [1, 3, 0]})
    animations[prefix + "knife_heavy"] = knife_heavy

    lance_ready = {
        # A braced, staggered human spear stance. The right hand owns the
        # socket but stays at the rear grip beside the ribs; the left hand is
        # the forward guide. This keeps two distinct points on the haft instead
        # of crossing both wrists around the attachment pivot. The lowered root keeps both feet on
        # the floor after the corrected hip pivot moved the femur origin up.
        "root": _position({"0.0": [0, -2.62, 0], "0.6": [0, -2.87, 0],
                             "1.2": [0, -2.62, 0]}),
        "torso_lower": _rotation({"0.0": [2, 0, 0]}),
        "torso_upper": _rotation({"0.0": [3, -6, 0], "0.6": [3, -6, 0],
                                    "1.2": [3, -6, 0]}),
        "leg_l": _rotation({"0.0": [-22, 0, -2]}),
        "shin_l": _rotation({"0.0": [20, 0, 0]}),
        "foot_l": _rotation({"0.0": [2, 0, 2]}),
        "leg_r": _rotation({"0.0": [22, 0, 2]}),
        "shin_r": _rotation({"0.0": [-2, 0, 0]}),
        "foot_r": _rotation({"0.0": [-20, 0, -2]}),
        "arm_r": _rotation({"0.0": [-24, -12, 18], "0.6": [-25, -12, 18],
                              "1.2": [-24, -12, 18]}),
        "forearm_r": _rotation({"0.0": [-120.71, -35.05, -12.69]}),
        "arm_l": _rotation({"0.0": [-73.62, 10.95, -20.07],
                              "0.6": [-74.3, 10.95, -20.07],
                              "1.2": [-73.62, 10.95, -20.07]}),
        "forearm_l": _rotation({"0.0": [-29.97, 15.13, 41.82]}),
        "hand_r": _rotation({"0.0": [0, 0, 5]}),
        "hand_l": _rotation({"0.0": [0, 0, -4]}),
        # Three degrees converges the shaft toward the target centre without
        # the old upper-left aim error.
        "lance": {
            "rotation": {"0.0": [22.45, 0.05, 61.56]},
            # Move the haft to the EVA's anatomical right without changing the
            # reviewed two-hand orientation.  This is a socket correction, not
            # another arm-axis guess.
            "position": {"0.0": [-1.75, 0, 0]},
        },
    }
    lance_ready["arm_r"] = _rotation({
        "0.0": [-17.27, -13.33, 22.44],
        "0.6": [-17.9, -13.33, 22.44],
        "1.2": [-17.27, -13.33, 22.44]})
    animations[prefix + "lance_ready"] = {
        "loop": True, "animation_length": 1.2, "bones": lance_ready}
    _set_finger_curl(animations[prefix + "lance_ready"]["bones"])
    # Moving with Longinus keeps the two-hand grip but must not overwrite the
    # base controller's pelvis and legs. The former full-body ready layer was
    # why an EVA slid across the ground with frozen or distorted strides.
    lance_carry = copy.deepcopy(animations[prefix + "lance_ready"])
    for bone in ("root", "torso_lower", "leg_l", "leg_r",
                 "shin_l", "shin_r", "foot_l", "foot_r"):
        lance_carry["bones"].pop(bone, None)
    animations[prefix + "lance_carry"] = lance_carry
    lance_thrust = copy.deepcopy(animations[prefix + "lance_ready"])
    lance_thrust.pop("loop", None)
    lance_thrust["animation_length"] = 0.72
    lance_thrust["bones"]["torso_lower"] = _rotation({
        "0.0": [2, 0, 0], "0.2": [-1, 0, 0], "0.42": [8, 0, 0],
        "0.6": [4, 0, 0], "0.72": [2, 0, 0]})
    lance_thrust["bones"]["torso_upper"] = _rotation({
        "0.0": [3, -6, 0], "0.2": [-2, 4, 0], "0.42": [10, -10, 0],
        "0.6": [6, -4, 0], "0.72": [3, -6, 0]})
    lance_thrust["bones"]["arm_r"] = _rotation({
        "0.0": [-17.27, -13.33, 22.44],
        "0.2": [-15.29, -15.49, 22.69],
        "0.42": [-39.99, -9.79, 16.20],
        "0.6": [-30.69, -12.57, 19.50],
        "0.72": [-17.27, -13.33, 22.44]})
    lance_thrust["bones"]["forearm_r"] = _rotation({
        "0.0": [-120.71, -35.05, -12.69],
        "0.2": [-118.23, -37.12, -10.34],
        "0.42": [-114.81, -24.73, -14.43],
        "0.6": [-113.70, -29.41, -12.05],
        "0.72": [-120.71, -35.05, -12.69]})
    lance_thrust["bones"]["arm_l"] = _rotation({
        "0.0": [-73.62, 10.95, -20.07],
        "0.2": [-60.52, 4.34, -27.84],
        "0.42": [-99.03, 19.43, -16.47],
        "0.6": [-82.89, 6.61, -21.50],
        "0.72": [-73.62, 10.95, -20.07]})
    lance_thrust["bones"]["forearm_l"] = _rotation({
        "0.0": [-29.97, 15.13, 41.82],
        "0.2": [-37.19, 25.31, 56.35],
        "0.42": [-11.96, 15.96, 13.48],
        "0.6": [-25.26, 24.11, 33.27],
        "0.72": [-29.97, 15.13, 41.82]})
    lance_thrust["bones"]["hand_r"] = _rotation({
        "0.0": [0, 0, 5], "0.2": [0, 0, 8],
        "0.42": [0, 0, 1], "0.6": [0, 0, 3],
        "0.72": [0, 0, 5]})
    lance_thrust["bones"]["hand_l"] = _rotation({
        "0.0": [0, 0, -4], "0.2": [0, 0, -7],
        "0.42": [0, 0, 0], "0.6": [0, 0, -2],
        "0.72": [0, 0, -4]})
    lance_thrust["bones"]["root"] = _position({
        "0.0": [0, -2.62, 0], "0.2": [0, -1.63, 0],
        "0.42": [0, -6.68, 0], "0.6": [0, -4.45, 0],
        "0.72": [0, -2.62, 0]})
    for bone, values in {
        "leg_l": ([-22, 0, -2], [-15, 0, -2], [-40, 0, -2], [-31, 0, -2]),
        "shin_l": ([20, 0, 0], [12, 0, 0], [45, 0, 0], [33, 0, 0]),
        "foot_l": ([2, 0, 2], [2, 0, 2], [-5, 0, 2], [-2, 0, 2]),
        "leg_r": ([22, 0, 2], [17, 0, 2], [35, 0, 2], [29, 0, 2]),
        "shin_r": ([-2, 0, 0], [-2, 0, 0], [-5, 0, 0], [-4, 0, 0]),
        "foot_r": ([-20, 0, -2], [-15, 0, -2], [-30, 0, -2], [-25, 0, -2]),
    }.items():
        ready, windup, contact, recovery = values
        lance_thrust["bones"][bone] = _rotation({
            "0.0": ready, "0.2": windup, "0.42": contact,
            "0.6": recovery, "0.72": ready})
    lance_thrust["bones"]["lance"] = _rotation({
        "0.0": [22.45, 0.05, 61.56],
        "0.2": [29.55, 6.36, 55.95],
        "0.42": [27.43, -0.55, 61.89],
        "0.6": [27.96, 1.13, 59.75],
        "0.72": [22.45, 0.05, 61.56]})
    lance_thrust["bones"]["lance"]["position"] = {
        "0.0": [-1.75, 0, 0],
        "0.2": [-1.0, 0, 0],
        "0.42": [-1.75, 0, 0],
        "0.6": [-1.75, 0, 0],
        "0.72": [-1.75, 0, 0],
    }
    animations[prefix + "lance_thrust"] = lance_thrust
    _set_finger_curl(animations[prefix + "lance_thrust"]["bones"])

    # The strike controller has higher priority than the locomotion controller.
    # Every low attack therefore carries the complete prone support envelope;
    # otherwise an attack clip evaluates an upright root for one half-second
    # and visibly stands the EVA up while it is still crawling.
    def prone_punch(side):
        bones = copy.deepcopy(prone_bones)
        other = "l" if side == "r" else "r"
        sign = 1 if side == "r" else -1
        bones[f"arm_{side}"] = _rotation({
            "0.0": [-158, 0, 14 * sign], "0.14": [-137, 0, 28 * sign],
            "0.30": [-174, 0, 7 * sign], "0.46": [-164, 0, 11 * sign],
            "0.58": [-158, 0, 14 * sign]})
        bones[f"forearm_{side}"] = _rotation({
            "0.0": [-25, 0, -8 * sign], "0.14": [-58, 0, -15 * sign],
            "0.30": [-5, 0, -3 * sign], "0.46": [-16, 0, -6 * sign],
            "0.58": [-25, 0, -8 * sign]})
        # The bracing arm stays planted under the shoulder.
        bones[f"arm_{other}"] = copy.deepcopy(prone_bones[f"arm_{other}"])
        bones[f"forearm_{other}"] = copy.deepcopy(prone_bones[f"forearm_{other}"])
        _set_hand_curl(bones, side, curl=35, thumb=23,
                       tip_curl=24, thumb_tip=10)
        _set_hand_curl(bones, other, curl=18, thumb=12,
                       tip_curl=10, thumb_tip=4)
        return {"animation_length": 0.58, "bones": bones}

    animations[prefix + "prone_melee"] = prone_punch("r")
    animations[prefix + "prone_melee_left"] = prone_punch("l")

    prone_knife = {"animation_length": 0.64,
                   "bones": copy.deepcopy(prone_bones)}
    bones = prone_knife["bones"]
    bones["arm_r"] = _rotation({
        "0.0": [-158.88, 0.08, 13.72],
        "0.16": [-158.14, 17.41, -12.85],
        "0.34": [-175, 3, 6],
        "0.50": [-158.42, 6.84, 9.27],
        "0.64": [-158.88, 0.08, 13.72]})
    bones["forearm_r"] = _rotation({
        "0.0": [-25.04, 0.14, -7.70],
        "0.16": [-42.51, -18.37, -61.16],
        "0.34": [-7, 0, -2],
        "0.50": [-30.29, 0.43, -17.25],
        "0.64": [-25.04, 0.14, -7.70]})
    bones["hand_r"] = _rotation({
        "0.0": [0, 0, -8], "0.16": [0, 0, -12],
        "0.34": [0, 0, 3], "0.50": [0, 0, -3],
        "0.64": [0, 0, -8]})
    # Reverse grip follows the prone forearm back toward the ribs instead of
    # pointing through the ground. Every key was solved against a +Z blade
    # axis and a non-negative elbow/forearm clearance contract.
    bones["knife"] = _rotation({
        "0.0": [144.70, 114.12, -5.15],
        "0.16": [126.56, 123.59, 16.49],
        "0.34": [134.14, 108.80, -41.87],
        "0.50": [127.05, 112.78, -23.75],
        "0.64": [144.70, 114.12, -5.15]})
    _set_knife_grip(bones)
    animations[prefix + "prone_knife"] = prone_knife
    animations[prefix + "prone_knife_heavy"] = retime_animation(
        prone_knife, 1.10 / 0.64)

    prone_lance = {"animation_length": 0.72,
                   "bones": copy.deepcopy(prone_bones)}
    bones = prone_lance["bones"]
    bones["arm_r"] = _rotation({
        "0.0": [-155.75, 17.81, -2.86],
        "0.20": [-153.43, 26.69, -6.61],
        "0.42": [-167.41, 23.57, 18.38],
        "0.60": [-162.87, 25.54, -0.34],
        "0.72": [-155.75, 17.81, -2.86]})
    bones["forearm_r"] = _rotation({
        "0.0": [-41.26, -22.98, -41.25],
        "0.20": [-57.82, -28.84, -51.28],
        "0.42": [-4.83, -24.22, -2.48],
        "0.60": [-34.43, -32.19, -26.48],
        "0.72": [-41.26, -22.98, -41.25]})
    bones["arm_l"] = _rotation({
        "0.0": [-174.46, 2.20, -24.61],
        "0.20": [-168.88, 0.31, -24.03],
        "0.42": [-173.03, -2.54, -23.17],
        "0.60": [-173.88, -2.13, -24.71],
        "0.72": [-174.46, 2.20, -24.61]})
    bones["forearm_l"] = _rotation({
        "0.0": [2.66, -4.98, -6.22],
        "0.20": [-12.75, -1.64, 3.13],
        "0.42": [2.60, -10.96, -6.22],
        "0.60": [2.53, -11.93, -6.36],
        "0.72": [2.66, -4.98, -6.22]})
    bones["lance"] = _rotation({
        "0.0": [27.31, 8.28, 49.92],
        "0.20": [34.15, 0.61, 61.01],
        "0.42": [14.62, 29.02, 21.61],
        "0.60": [34.63, 14.83, 40.60],
        "0.72": [27.31, 8.28, 49.92]})
    bones["lance"]["position"] = {
        key: [-1.75, 0, 0] for key in ("0.0", "0.20", "0.42", "0.60", "0.72")}
    _set_finger_curl(bones, curl=48, thumb=30,
                     tip_curl=30, thumb_tip=14)
    animations[prefix + "prone_lance_thrust"] = prone_lance

    prone_smash = {"animation_length": 0.72,
                   "bones": copy.deepcopy(prone_bones)}
    bones = prone_smash["bones"]
    for side, sign in (("l", -1), ("r", 1)):
        bones[f"arm_{side}"] = _rotation({
            "0.0": [-158, 0, 14 * sign], "0.18": [-135, 0, 24 * sign],
            "0.40": [-176, 0, 8 * sign], "0.58": [-165, 0, 11 * sign],
            "0.72": [-158, 0, 14 * sign]})
        bones[f"forearm_{side}"] = _rotation({
            "0.0": [-25, 0, -8 * sign], "0.18": [-62, 0, -14 * sign],
            "0.40": [-4, 0, -2 * sign], "0.58": [-14, 0, -5 * sign],
            "0.72": [-25, 0, -8 * sign]})
    _set_finger_curl(bones, curl=50, thumb=30,
                     tip_curl=34, thumb_tip=14)
    animations[prefix + "prone_smash"] = prone_smash

    cannon_fire = animations[prefix + "cannon_fire"]["bones"]
    # Cannon recoil is an upper-body overlay. Keeping the source root, pelvis
    # and legs here made a prone shot stand up even though the aim pose itself
    # was correct.
    for bone in ("root", "torso_lower", "torso_upper", "head",
                 "leg_l", "leg_r", "shin_l", "shin_r", "foot_l", "foot_r"):
        cannon_fire.pop(bone, None)
    cannon_fire["arm_r"] = _rotation({
        "0.0": [-62, -10, 12], "0.06": [-58, -10, 14],
        "0.2": [-65, -10, 10], "0.55": [-62, -10, 12]})
    cannon_fire["forearm_r"] = _rotation({"0.0": [-68, -8, -8]})
    cannon_fire["hand_r"] = _rotation({"0.0": [0, 0, 0]})
    cannon_fire["arm_l"] = _rotation({
        "0.0": [-97.41, 26.22, -1.84], "0.06": [-93.5, 26.2, 0],
        "0.2": [-100.0, 26.5, -3.0], "0.55": [-97.41, 26.22, -1.84]})
    cannon_fire["forearm_l"] = _rotation({"0.0": [2.83, -8.18, -6.28]})
    cannon_fire["hand_l"] = _rotation({"0.0": [0, 0, 0]})
    cannon_fire["cannon"] = _rotation({"0.0": [40.24, -8.41, 20.45]})
    _set_firearm_grip(cannon_fire)

    # Triggered attacks run on the highest-priority controller.  Crouch clips
    # therefore animate only the upper body: the base controller remains the
    # sole owner of root, pelvis and legs and cannot be popped upright by an
    # attack.  The same layers work over both the static kneel and low gait.
    lower_body = {
        "root", "torso_lower", "leg_l", "leg_r",
        "shin_l", "shin_r", "foot_l", "foot_r",
    }

    def upper_body_clip(source):
        clip = copy.deepcopy(source)
        clip.pop("loop", None)
        for bone in lower_body:
            clip["bones"].pop(bone, None)
        return clip

    animations[prefix + "crouch_melee"] = upper_body_clip(
        animations[prefix + "melee"])
    animations[prefix + "crouch_melee_left"] = upper_body_clip(
        animations[prefix + "melee_left"])
    animations[prefix + "crouch_knife"] = upper_body_clip(
        animations[prefix + "knife"])
    animations[prefix + "crouch_knife_heavy"] = upper_body_clip(
        animations[prefix + "knife_heavy"])
    animations[prefix + "crouch_lance_thrust"] = upper_body_clip(
        animations[prefix + "lance_thrust"])
    animations[prefix + "crouch_smash"] = upper_body_clip(
        animations[prefix + "smash"])

    # Crawling still needs a visible weapon between attacks.  These readiness
    # clips sample the reviewed low attack at rest, then discard every lower
    # body channel so crawl legs continue to advance underneath the grip.
    animations[prefix + "prone_knife_ready"] = upper_body_clip(
        static_pose(animations[prefix + "prone_knife"], 0.0))
    animations[prefix + "prone_knife_ready"]["loop"] = True
    animations[prefix + "prone_lance_ready"] = upper_body_clip(
        static_pose(animations[prefix + "prone_lance_thrust"], 0.0))
    animations[prefix + "prone_lance_ready"]["loop"] = True

    prone_cannon_fire = upper_body_clip(
        static_pose(animations[prefix + "prone_aim"], 0.0))
    prone_cannon_fire["animation_length"] = 0.55
    prone_cannon_fire["bones"]["arm_r"] = _rotation({
        "0.0": [-158, 0, 14], "0.06": [-154, 0, 16],
        "0.2": [-161, 0, 12], "0.55": [-158, 0, 14]})
    prone_cannon_fire["bones"]["arm_l"] = _rotation({
        "0.0": [-158, 0, -14], "0.06": [-154, 0, -16],
        "0.2": [-161, 0, -12], "0.55": [-158, 0, -14]})
    prone_cannon_fire["bones"]["cannon"] = _rotation({
        "0.0": [9.89, -3.95, 21.28]})
    _set_firearm_grip(prone_cannon_fire["bones"])
    animations[prefix + "prone_cannon_fire"] = prone_cannon_fire

    # The pallet rifle is automatic, so its recoil is shorter and lighter
    # than the Yashima cannon discharge while still visibly reacting on every
    # accepted server shot. Both clips are upper-body overlays and preserve
    # the user-approved crouch/prone lower-body silhouettes.
    rifle_fire = upper_body_clip(
        static_pose(animations[prefix + "rifle_aim"], 0.0))
    rifle_fire["animation_length"] = 0.18
    rifle_fire["bones"]["arm_r"] = _rotation({
        "0.0": [-62, -10, 12], "0.04": [-58.5, -10, 14],
        "0.11": [-64, -10, 10], "0.18": [-62, -10, 12]})
    rifle_fire["bones"]["arm_l"] = _rotation({
        "0.0": [-97.41, 26.22, -1.84], "0.04": [-94, 26.2, 0],
        "0.11": [-99, 26.4, -2.7], "0.18": [-97.41, 26.22, -1.84]})
    _set_firearm_grip(rifle_fire["bones"])
    animations[prefix + "rifle_fire"] = rifle_fire

    prone_rifle_fire = upper_body_clip(
        static_pose(animations[prefix + "prone_aim"], 0.0))
    prone_rifle_fire["animation_length"] = 0.18
    prone_rifle_fire["bones"]["arm_r"] = _rotation({
        "0.0": [-158, 0, 14], "0.04": [-154.5, 0, 16],
        "0.11": [-160, 0, 12], "0.18": [-158, 0, 14]})
    prone_rifle_fire["bones"]["arm_l"] = _rotation({
        "0.0": [-158, 0, -14], "0.04": [-154.5, 0, -16],
        "0.11": [-160, 0, -12], "0.18": [-158, 0, -14]})
    _set_firearm_grip(prone_rifle_fire["bones"])
    animations[prefix + "prone_rifle_fire"] = prone_rifle_fire

    # Bare-hand melee owns animated claw fingers; do not overwrite those
    # channels with the old static iron-golem fist.
    for attack_name in ("smash", "stomp"):
        if prefix + attack_name in animations:
            _set_finger_curl(animations[prefix + attack_name]["bones"],
                             curl=62, thumb=36,
                             tip_curl=46, thumb_tip=17)

    crucified = animations[prefix + "crucified"]["bones"]
    crucified["arm_l"] = _rotation({
        "0.0": [0, 0, -85.25], "1.5": [0, 0, -85], "3.0": [0, 0, -85.25]})
    crucified["arm_r"] = _rotation({
        "0.0": [0, 0, 85.25], "1.5": [0, 0, 85], "3.0": [0, 0, 85.25]})
    # Pull both legs toward the centreline without swapping them.  The old
    # signs spread the ankles more than twice the hip width, which read as a
    # relaxed star pose instead of the restrained Tree-of-Life crucifix.
    # Nine degrees closes the ankles to less than half a model pixel while
    # retaining each foot on its anatomical side. Twelve degrees crossed the
    # entire lower legs into a visible X beneath the Tree-of-Life cross pose.
    crucified["leg_l"] = _rotation({"0.0": [0, 0, 9]})
    crucified["leg_r"] = _rotation({"0.0": [0, 0, -9]})
    crucified["foot_l"] = _rotation({"0.0": [0, 0, -9]})
    crucified["foot_r"] = _rotation({"0.0": [0, 0, 9]})

    activation = animations[prefix + "activation"]["bones"]
    activation["arm_l"] = _rotation({"0.0": [-8, 0, -5]})
    activation["arm_r"] = _rotation({"0.0": [-8, 0, 5]})
    return data


def build_animations():
    data = json.loads(BASE_ANIMATION.read_text(encoding="utf-8"))
    repair_tiger_runtime_animations(data)
    animations = data["animations"]

    def composed_pose(base_name, base_time, overlay_name, overlay_time):
        """Freeze the same base/upper-body composition Gecko evaluates live."""
        pose = static_pose(animations[base_name], base_time)
        overlay = static_pose(animations[overlay_name], overlay_time)
        pose["bones"].update(overlay["bones"])
        return pose

    animations["animation.eva_unit01.visual_idle"] = static_pose(
        animations["animation.eva_unit01.idle"], 0.0)
    animations["animation.eva_unit01.visual_walk_contact"] = static_pose(
        animations["animation.eva_unit01.walk"], 0.0)
    animations["animation.eva_unit01.visual_run_contact"] = static_pose(
        animations["animation.eva_unit01.run"], 0.0)
    animations["animation.eva_unit01.visual_jump"] = static_pose(
        animations["animation.eva_unit01.takeoff"], 0.22)
    animations["animation.eva_unit01.visual_fall"] = static_pose(
        animations["animation.eva_unit01.fall"], 0.0)
    animations["animation.eva_unit01.visual_crouch_walk"] = static_pose(
        animations["animation.eva_unit01.crouch_walk"], 0.0)
    animations["animation.eva_unit01.visual_crawl"] = static_pose(
        animations["animation.eva_unit01.crawl"], 0.0)
    animations["animation.eva_unit01.visual_knife_ready"] = static_pose(
        animations["animation.eva_unit01.knife_ready"], 0.0)
    animations["animation.eva_unit01.visual_lance_ready"] = static_pose(
        animations["animation.eva_unit01.lance_ready"], 0.0)
    animations["animation.eva_unit01.visual_knife_windup"] = static_pose(
        animations["animation.eva_unit01.knife"], 0.20)
    animations["animation.eva_unit01.visual_knife_contact"] = static_pose(
        animations["animation.eva_unit01.knife"], 0.45)
    animations["animation.eva_unit01.visual_knife_recovery"] = static_pose(
        animations["animation.eva_unit01.knife"], 0.70)
    animations["animation.eva_unit01.visual_knife_heavy_contact"] = static_pose(
        animations["animation.eva_unit01.knife_heavy"], 0.57)
    animations["animation.eva_unit01.visual_lance_windup"] = static_pose(
        animations["animation.eva_unit01.lance_thrust"], 0.20)
    animations["animation.eva_unit01.visual_lance_contact"] = static_pose(
        animations["animation.eva_unit01.lance_thrust"], 0.42)
    animations["animation.eva_unit01.visual_lance_recovery"] = static_pose(
        animations["animation.eva_unit01.lance_thrust"], 0.70)
    animations["animation.eva_unit01.visual_cannon"] = static_pose(
        animations["animation.eva_unit01.aim"], 0.0)
    animations["animation.eva_unit01.visual_rifle"] = static_pose(
        animations["animation.eva_unit01.rifle_aim"], 0.0)
    animations["animation.eva_unit01.visual_crouch_knife_contact"] = composed_pose(
        "animation.eva_unit01.crouch", 0.0,
        "animation.eva_unit01.crouch_knife", 0.45)
    animations["animation.eva_unit01.visual_prone_knife_contact"] = static_pose(
        animations["animation.eva_unit01.prone_knife"], 0.34)
    animations["animation.eva_unit01.visual_crouch_lance_contact"] = composed_pose(
        "animation.eva_unit01.crouch", 0.0,
        "animation.eva_unit01.crouch_lance_thrust", 0.42)
    animations["animation.eva_unit01.visual_prone_lance_contact"] = static_pose(
        animations["animation.eva_unit01.prone_lance_thrust"], 0.42)
    animations["animation.eva_unit01.visual_n2_ready"] = static_pose(
        animations["animation.eva_unit01.n2_ready"], 0.0)
    animations["animation.eva_unit01.visual_rifle_walk_contact"] = composed_pose(
        "animation.eva_unit01.walk", 0.0,
        "animation.eva_unit01.rifle_aim", 0.0)
    animations["animation.eva_unit01.visual_crouch_rifle_contact"] = composed_pose(
        "animation.eva_unit01.crouch_walk", 0.0,
        "animation.eva_unit01.rifle_aim", 0.0)
    animations["animation.eva_unit01.visual_prone_rifle"] = composed_pose(
        "animation.eva_unit01.prone", 0.0,
        "animation.eva_unit01.prone_aim", 0.0)
    return data


def main():
    if not SOURCE.exists():
        sys.exit(f"Unit-01 source not found: {SOURCE}")
    obj_text, texture = read_source()
    positions, texcoords, normals, triangles = parse_obj(obj_text)
    finger_faces, finger_pivots = discover_finger_rig(positions, triangles)
    minimum_y = min(position[1] for position in positions)
    height = max(position[1] for position in positions) - minimum_y
    scale = MODEL_HEIGHT / height
    skeleton, pivots = build_skeleton(scale, minimum_y, finger_pivots)
    mesh, counts = build_mesh(positions, texcoords, normals, triangles, pivots, scale,
                              minimum_y, finger_faces)

    geo_dir = OUT / "geo"
    animation_dir = OUT / "animations"
    texture_dir = OUT / "textures/entity"
    mesh_dir = OUT / "mesh"
    for directory in (geo_dir, animation_dir, texture_dir, mesh_dir):
        directory.mkdir(parents=True, exist_ok=True)
    (geo_dir / "eva_unit01.geo.json").write_text(
        json.dumps(skeleton, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (animation_dir / "eva_unit01.animation.json").write_text(
        json.dumps(build_animations(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (mesh_dir / "eva_unit01.mesh.json").write_text(
        json.dumps(mesh, separators=(",", ":")), encoding="utf-8")
    build_atlas(texture).save(texture_dir / "eva_unit01.png")
    pack_root = OUT.parent.parent
    (pack_root / "pack.mcmeta").write_text(json.dumps({
        "pack": {
            "pack_format": 15,
            "description": "Project SEELE local external model evaluation - not for redistribution",
        }
    }, indent=2) + "\n", encoding="utf-8")
    source_note = pack_root / "_SOURCE.txt"
    existing_note = source_note.read_text(encoding="utf-8") if source_note.exists() else ""
    source_title = "Tigerar1 Evangelion Unit-01 (Sketchfab, CC BY-SA).\n"
    source_url = ("https://sketchfab.com/3d-models/"
                  "evangelion-unit-01-9fddeb0a7143436598c805dab2f147bf\n")
    if source_url not in existing_note:
        addition = "" if "Tigerar1 Evangelion Unit-01" in existing_note else source_title
        addition += source_url
        if "Converted from the user-downloaded OBJ" not in existing_note:
            addition += "Converted from the user-downloaded OBJ for LOCAL TESTING ONLY.\n"
        source_note.write_text(existing_note + addition, encoding="utf-8")
    print(f"Tigerar1 Unit-01: {len(positions)} vertices / {len(triangles)} triangles")
    print("bone faces: " + ", ".join(f"{bone}={count}" for bone, count in sorted(counts.items())))
    print(f"local mesh pack written -> {OUT}")


if __name__ == "__main__":
    main()
