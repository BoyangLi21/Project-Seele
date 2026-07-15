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
    # Keep temporary weapon/socket geometry attached to the new right hand.
    for name in ("knife", "cannon", "lance"):
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


def _rotation(keys):
    return {"rotation": {time: value for time, value in keys.items()}}


def _position(keys):
    return {"position": {time: value for time, value in keys.items()}}


def _set_finger_curl(bones, curl=60, thumb=39, tip_curl=40, thumb_tip=0):
    """Close both anatomically matched hands around a weapon grip.

    The geodesic hand partition keeps each continuous shaft on its distal
    bone, so the second joint can now contribute a real hook instead of
    exposing loose triangle fragments.  OBJ X is mirrored between hands, but
    their local flexion axis is not: the same positive X rotation closes both.
    """
    for side in ("l", "r"):
        for digit in FINGER_ORDER:
            angle = thumb if digit == "thumb" else curl
            bones[f"finger_{digit}_{side}"] = _rotation(
                {"0.0": [angle, 0, 0]})
            tip_angle = thumb_tip if digit == "thumb" else tip_curl
            bones[f"finger_{digit}_tip_{side}"] = _rotation(
                {"0.0": [tip_angle, 0, 0]})


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

    walk = animations[prefix + "walk"]["bones"]
    for keyframe in walk["arm_l"]["rotation"].values():
        keyframe[2] = -abs(keyframe[2])
    for keyframe in walk["arm_r"]["rotation"].values():
        keyframe[2] = abs(keyframe[2])
    # EVA is a biological humanoid, not a pair of rigid pendulums.  Flex the
    # elbows through the gait so neither straight arm disappears behind the
    # pilot camera at foot contact; the opposite phasing preserves a readable
    # human walk in third person and shows both real arms when looking down.
    walk["forearm_l"] = _rotation({
        "0.0": [-55, 0, 0], "0.5": [-42, 0, 0], "1.0": [-55, 0, 0]})
    walk["forearm_r"] = _rotation({
        "0.0": [-42, 0, 0], "0.5": [-55, 0, 0], "1.0": [-42, 0, 0]})
    # Raising the anatomical hip pivot fixes the thigh/waist inversion but
    # also lengthens the effective planted leg. Preserve the authored bob and
    # lower its whole curve so one sole meets the floor at each contact frame.
    for keyframe in walk.get("root", {}).get("position", {}).values():
        if isinstance(keyframe, list) and len(keyframe) >= 2:
            keyframe[1] -= 3.6

    run = animations[prefix + "run"]["bones"]
    for keyframe in run["arm_l"]["rotation"].values():
        keyframe[0] = max(-32, min(32, keyframe[0]))
        keyframe[2] = -abs(keyframe[2])
        keyframe[2] = max(keyframe[2], -6)
    for keyframe in run["arm_r"]["rotation"].values():
        keyframe[0] = max(-32, min(32, keyframe[0]))
        keyframe[2] = abs(keyframe[2])
        keyframe[2] = min(keyframe[2], 6)
    run["forearm_l"] = _rotation({
        "0.0": [-72, 0, 0], "0.31": [-56, 0, 0], "0.62": [-72, 0, 0]})
    run["forearm_r"] = _rotation({
        "0.0": [-56, 0, 0], "0.31": [-72, 0, 0], "0.62": [-56, 0, 0]})
    run["root"] = _position({
        "0.0": [0, -8.7, 0], "0.31": [0, -8.7, 0],
        "0.62": [0, -8.7, 0]})

    animations[prefix + "jump"]["bones"].update({
        "arm_l": _rotation({"0.0": [-24, 0, -20]}),
        "forearm_l": _rotation({"0.0": [8, 0, 0]}),
        "arm_r": _rotation({"0.0": [-24, 0, 20]}),
        "forearm_r": _rotation({"0.0": [8, 0, 0]}),
    })
    animations[prefix + "fall"]["bones"].update({
        "arm_l": _rotation({"0.0": [-8, 0, -34]}),
        "arm_r": _rotation({"0.0": [-8, 0, 34]}),
    })

    crouch_bones = {
        "root": _position({"0.0": [0, -39.15, 0]}),
        "torso_lower": _rotation({"0.0": [0, 0, 0]}),
        "torso_upper": _rotation({"0.0": [5, 0, 0], "0.8": [3, 0, 0],
                                   "1.6": [5, 0, 0]}),
        # Human single-knee support: left thigh reaches the planted front knee,
        # then the shin folds diagonally back to a level sole. The previous
        # same-sign hip/knee pair added to 74 degrees and turned the front leg
        # into a near-horizontal split.
        "leg_l": _rotation({"0.0": [-88, 0, -3]}),
        "shin_l": _rotation({"0.0": [48, 0, 0]}),
        "foot_l": _rotation({"0.0": [40, 0, 0]}),
        "leg_r": _rotation({"0.0": [5.13, 0, 3]}),
        "shin_r": _rotation({"0.0": [80.71, 0, 0]}),
        "foot_r": _rotation({"0.0": [-85.84, 0, 0]}),
        # Relaxed guard rather than two locked zombie arms. Elbows stay bent
        # and low enough to remain in the shared first-person periphery.
        "arm_l": _rotation({"0.0": [-22, 0, -7]}),
        "forearm_l": _rotation({"0.0": [-58, 0, 0]}),
        "arm_r": _rotation({"0.0": [-22, 0, 7]}),
        "forearm_r": _rotation({"0.0": [-58, 0, 0]}),
    }
    animations[prefix + "crouch"] = {
        "loop": True, "animation_length": 1.6, "bones": crouch_bones}
    crouch_walk = copy.deepcopy(animations[prefix + "crouch"])
    crouch_walk["animation_length"] = 1.15
    crouch_walk["bones"]["root"] = _position({
        "0.0": [0, -39.15, 0], "0.28": [0, -38.55, 0],
        "0.57": [0, -38.25, 0], "0.86": [0, -38.55, 0],
        "1.15": [0, -39.15, 0]})
    crouch_walk["bones"]["torso_lower"] = _rotation({
        "0.0": [0, 2, 0], "0.57": [0, -2, 0], "1.15": [0, 2, 0]})
    crouch_walk["bones"]["leg_l"] = _rotation({
        "0.0": [-88, 0, -3], "0.57": [-84, 0, -3], "1.15": [-88, 0, -3]})
    crouch_walk["bones"]["shin_l"] = _rotation({
        "0.0": [48, 0, 0], "0.57": [45, 0, 0], "1.15": [48, 0, 0]})
    crouch_walk["bones"]["foot_l"] = _rotation({
        "0.0": [40, 0, 0], "0.57": [39, 0, 0], "1.15": [40, 0, 0]})
    crouch_walk["bones"]["leg_r"] = _rotation({
        "0.0": [5.13, 0, 3], "0.57": [7.5, 0, 3], "1.15": [5.13, 0, 3]})
    crouch_walk["bones"]["shin_r"] = _rotation({
        "0.0": [80.71, 0, 0], "0.57": [77.5, 0, 0], "1.15": [80.71, 0, 0]})
    crouch_walk["bones"]["foot_r"] = _rotation({
        "0.0": [-85.84, 0, 0], "0.57": [-83, 0, 0], "1.15": [-85.84, 0, 0]})
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
        "arm_l": _rotation({"0.0": [-158, 0, -14]}),
        "forearm_l": _rotation({"0.0": [-25, 0, 8]}),
        "hand_l": _rotation({"0.0": [0, 0, 0]}),
        "arm_r": _rotation({"0.0": [-158, 0, 14]}),
        "forearm_r": _rotation({"0.0": [-25, 0, -8]}),
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
        "0.0": [-0.25, -62.0, 0], "0.35": [0, -61.5, 0],
        "0.7": [0.25, -62.0, 0], "1.05": [0, -61.5, 0],
        "1.4": [-0.25, -62.0, 0]})
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
        "0.0": [-160, 0, -14], "0.35": [-152, 0, -23],
        "0.7": [-145, 0, -35], "1.05": [-152, 0, -23],
        "1.4": [-160, 0, -14]})
    crawl["bones"]["arm_r"] = _rotation({
        "0.0": [-145, 0, 35], "0.35": [-152, 0, 23],
        "0.7": [-160, 0, 14], "1.05": [-152, 0, 23],
        "1.4": [-145, 0, 35]})
    crawl["bones"]["forearm_l"] = _rotation({
        "0.0": [-22, 0, 8], "0.35": [-38, 0, 16],
        "0.7": [-55, 0, 25], "1.05": [-38, 0, 16],
        "1.4": [-22, 0, 8]})
    crawl["bones"]["forearm_r"] = _rotation({
        "0.0": [-55, 0, -25], "0.35": [-38, 0, -16],
        "0.7": [-22, 0, -8], "1.05": [-38, 0, -16],
        "1.4": [-55, 0, -25]})
    animations[prefix + "crawl"] = crawl

    animations[prefix + "aim"] = {
        "loop": True, "animation_length": 1.2, "bones": {
            # Shoulder the receiver instead of locking both elbows.  The
            # right/trigger hand stays close to the face while the left hand
            # reaches the fore-end, so the same world skeleton has a readable
            # first-person silhouette and a credible third-person firing line.
            "arm_r": _rotation({"0.0": [-52, -18, 5], "0.6": [-53, -18, 5],
                                  "1.2": [-52, -18, 5]}),
            "forearm_r": _rotation({"0.0": [-81, 0, 0]}),
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
            "cannon": _rotation({"0.0": [45, 0, 0]}),
        }}
    _set_finger_curl(animations[prefix + "aim"]["bones"])
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
            "cannon": _rotation({"0.0": [18, 0, 0]}),
        }}
    _set_finger_curl(animations[prefix + "prone_aim"]["bones"])

    animations[prefix + "knife_ready"]["bones"].update({
        "arm_r": _rotation({"0.0": [-55, -8, 12], "0.6": [-56, -8, 12],
                              "1.2": [-55, -8, 12]}),
        "forearm_r": _rotation({"0.0": [-45, 0, 0]}),
        "arm_l": _rotation({"0.0": [-55, 8, -12], "0.6": [-56, 8, -12],
                              "1.2": [-55, 8, -12]}),
        "forearm_l": _rotation({"0.0": [-45, 0, 0]}),
        "hand_r": _rotation({"0.0": [0, 0, 0]}),
        "hand_l": _rotation({"0.0": [0, 0, 0]}),
        # Blade down beside the forearm: a reverse grip, not the former
        # forward sabre grip.  Keep this channel in every attack keyframe so
        # Gecko cannot briefly restore the old cube orientation.
        "knife": _rotation({"0.0": [90, 0, 15]}),
    })
    _set_finger_curl(animations[prefix + "knife_ready"]["bones"])
    for name in ("knife", "knife_left"):
        bones = animations[prefix + name]["bones"]
        # Preserve the authored forward/back lunge but keep a planted sole.
        # Most of the source clip's vertical lift is removed; the recovery key
        # needs a 1.4-pixel compensation because the rotating ankle shell would
        # otherwise cut visibly through the floor.
        bones["root"] = _position({
            "0.0": [0, 0, 0], "0.12": [0, 0, 1],
            "0.28": [0, 0, -3], "0.42": [0, 1.4, -1],
            "0.6": [0, 0, 0]})
        bones["arm_r"]["rotation"] = {
            "0.0": [-55, -8, 12], "0.12": [-30, -12, 24],
            "0.28": [-96, -5, 6], "0.42": [-72, -6, 10],
            "0.6": [-55, -8, 12]}
        bones["forearm_r"]["rotation"] = {
            "0.0": [-45, 0, 0], "0.12": [-78, 0, 0],
            "0.28": [-8, 0, 0], "0.42": [-26, 0, 0],
            "0.6": [-45, 0, 0]}
        bones["arm_l"]["rotation"] = {
            "0.0": [-55, 8, -12], "0.12": [-48, 8, -14],
            "0.28": [-62, 3, -10], "0.42": [-58, 5, -11],
            "0.6": [-55, 8, -12]}
        bones["forearm_l"]["rotation"] = {
            "0.0": [-45, 0, 0], "0.12": [-50, 0, 0],
            "0.28": [-34, 0, 0], "0.42": [-40, 0, 0],
            "0.6": [-45, 0, 0]}
        bones["hand_r"] = _rotation({"0.0": [0, 0, 0]})
        bones["hand_l"] = _rotation({"0.0": [0, 0, 0]})
        bones["knife"] = _rotation({"0.0": [90, 0, 15]})
        _set_finger_curl(bones)

    lance_ready = {
        # A braced, staggered human spear stance.  The right/front hand owns
        # the weapon socket while the left/rear hand is solved against a point
        # 25 px farther back on the haft.  The lowered root keeps both feet on
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
        "arm_r": _rotation({"0.0": [-50, -8, 5], "0.6": [-51, -8, 5],
                              "1.2": [-50, -8, 5]}),
        "forearm_r": _rotation({"0.0": [-45, 0, 0]}),
        "arm_l": _rotation({"0.0": [-77.0, 40.62, -27.31],
                              "0.6": [-77.5, 40.62, -27.31],
                              "1.2": [-77.0, 40.62, -27.31]}),
        "forearm_l": _rotation({"0.0": [-28.58, 14.93, 44.54]}),
        "hand_r": _rotation({"0.0": [0, 0, 0]}),
        "hand_l": _rotation({"0.0": [0, 0, 0]}),
        # Three degrees converges the shaft toward the target centre without
        # the old upper-left aim error.
        "lance": _rotation({"0.0": [-5, 0, 3]}),
    }
    animations[prefix + "lance_ready"] = {
        "loop": True, "animation_length": 1.2, "bones": lance_ready}
    _set_finger_curl(animations[prefix + "lance_ready"]["bones"])
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
        "0.0": [-50, -8, 5], "0.2": [-45, -8, 5],
        "0.42": [-64, -8, 5], "0.6": [-56, -8, 5],
        "0.72": [-50, -8, 5]})
    lance_thrust["bones"]["forearm_r"] = _rotation({
        "0.0": [-45, 0, 0], "0.2": [-55, 0, 0],
        "0.42": [-26, 0, 0], "0.6": [-38, 0, 0],
        "0.72": [-45, 0, 0]})
    lance_thrust["bones"]["arm_l"] = _rotation({
        "0.0": [-77.0, 40.62, -27.31], "0.2": [-70, 45, -30],
        "0.42": [-75.74, 33.59, -20.6], "0.6": [-76, 37, -24],
        "0.72": [-77.0, 40.62, -27.31]})
    lance_thrust["bones"]["forearm_l"] = _rotation({
        "0.0": [-28.58, 14.93, 44.54], "0.2": [-35, 17, 50],
        "0.42": [-26.83, 12.94, 45.89], "0.6": [-27, 12, 40],
        "0.72": [-28.58, 14.93, 44.54]})
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
        "0.0": [-5, 0, 3], "0.2": [2, 0, 3],
        "0.42": [-18, 0, 3], "0.6": [-10, 0, 3],
        "0.72": [-5, 0, 3]})
    animations[prefix + "lance_thrust"] = lance_thrust
    _set_finger_curl(animations[prefix + "lance_thrust"]["bones"])

    cannon_fire = animations[prefix + "cannon_fire"]["bones"]
    cannon_fire["arm_r"] = _rotation({
        "0.0": [-52, -18, 5], "0.06": [-48, -18, 7],
        "0.2": [-55, -18, 4], "0.55": [-52, -18, 5]})
    cannon_fire["forearm_r"] = _rotation({"0.0": [-81, 0, 0]})
    cannon_fire["hand_r"] = _rotation({"0.0": [0, 0, 0]})
    cannon_fire["arm_l"] = _rotation({
        "0.0": [-97.41, 26.22, -1.84], "0.06": [-93.5, 26.2, 0],
        "0.2": [-100.0, 26.5, -3.0], "0.55": [-97.41, 26.22, -1.84]})
    cannon_fire["forearm_l"] = _rotation({"0.0": [2.83, -8.18, -6.28]})
    cannon_fire["hand_l"] = _rotation({"0.0": [0, 0, 0]})
    cannon_fire["cannon"] = _rotation({"0.0": [45, 0, 0]})
    _set_finger_curl(cannon_fire)

    for attack_name in ("melee", "melee_left", "smash", "stomp"):
        if prefix + attack_name in animations:
            _set_finger_curl(animations[prefix + attack_name]["bones"],
                             curl=55, thumb=36)

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
    animations["animation.eva_unit01.visual_idle"] = static_pose(
        animations["animation.eva_unit01.idle"], 0.0)
    animations["animation.eva_unit01.visual_walk_contact"] = static_pose(
        animations["animation.eva_unit01.walk"], 0.0)
    animations["animation.eva_unit01.visual_run_contact"] = static_pose(
        animations["animation.eva_unit01.run"], 0.0)
    animations["animation.eva_unit01.visual_jump"] = static_pose(
        animations["animation.eva_unit01.jump"], 0.0)
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
        animations["animation.eva_unit01.knife"], 0.12)
    animations["animation.eva_unit01.visual_knife_contact"] = static_pose(
        animations["animation.eva_unit01.knife"], 0.28)
    animations["animation.eva_unit01.visual_knife_recovery"] = static_pose(
        animations["animation.eva_unit01.knife"], 0.50)
    animations["animation.eva_unit01.visual_lance_windup"] = static_pose(
        animations["animation.eva_unit01.lance_thrust"], 0.20)
    animations["animation.eva_unit01.visual_lance_contact"] = static_pose(
        animations["animation.eva_unit01.lance_thrust"], 0.42)
    animations["animation.eva_unit01.visual_lance_recovery"] = static_pose(
        animations["animation.eva_unit01.lance_thrust"], 0.70)
    animations["animation.eva_unit01.visual_cannon"] = static_pose(
        animations["animation.eva_unit01.aim"], 0.0)
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
