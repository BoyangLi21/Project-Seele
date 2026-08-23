"""Clean-room EVA hand bind-frame recovery for the Tiger OBJ generators.

All topology work happens in source OBJ/model space. The returned adapter
rotation is a Bedrock/Gecko JSON rotation which becomes the requested runtime
basis after Gecko's (-X,+Y,+Z) pivot reflection and X/Y rotation sign rules.
"""
from __future__ import annotations

import math
from collections import defaultdict

A_SOURCE_TO_RUNTIME = ((-1.0, 0.0, 0.0),
                       (0.0, 1.0, 0.0),
                       (0.0, 0.0, -1.0))


def _add(a, b): return tuple(a[i] + b[i] for i in range(3))
def _sub(a, b): return tuple(a[i] - b[i] for i in range(3))
def _mul(a, s): return tuple(a[i] * s for i in range(3))
def _dot(a, b): return sum(a[i] * b[i] for i in range(3))
def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _length(v): return math.sqrt(_dot(v, v))
def _normalise(v):
    length = _length(v)
    if length <= 1.0e-12:
        raise RuntimeError("zero-length hand frame vector")
    return _mul(v, 1.0 / length)


def _matrix_vector(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[column]
                     for column in range(3)) for row in range(3))


def _det3(matrix):
    return _dot(matrix[0], _cross(matrix[1], matrix[2]))


def _transpose_columns(columns):
    return tuple(tuple(columns[column][row] for column in range(3))
                 for row in range(3))


def _smallest_eigenvector_symmetric3(covariance):
    """Jacobi diagonalisation; avoids adding NumPy to the asset generator."""
    a = [list(row) for row in covariance]
    v = [[1.0 if row == column else 0.0 for column in range(3)]
         for row in range(3)]
    for _ in range(32):
        p, q = max(((0, 1), (0, 2), (1, 2)),
                   key=lambda pair: abs(a[pair[0]][pair[1]]))
        if abs(a[p][q]) < 1.0e-14:
            break
        angle = 0.5 * math.atan2(2.0 * a[p][q], a[q][q] - a[p][p])
        c, s = math.cos(angle), math.sin(angle)
        for k in range(3):
            apk, aqk = a[p][k], a[q][k]
            a[p][k] = c * apk - s * aqk
            a[q][k] = s * apk + c * aqk
        for k in range(3):
            akp, akq = a[k][p], a[k][q]
            a[k][p] = c * akp - s * akq
            a[k][q] = s * akp + c * akq
        for k in range(3):
            vkp, vkq = v[k][p], v[k][q]
            v[k][p] = c * vkp - s * vkq
            v[k][q] = s * vkp + c * vkq
    index = min(range(3), key=lambda item: a[item][item])
    return _normalise(tuple(v[row][index] for row in range(3)))


def _welded_position_keys(positions):
    return [tuple(round(value, 6) for value in position)
            for position in positions]


def _welded_edge_faces(positions, triangles):
    keys = _welded_position_keys(positions)
    coordinates = {key: key for key in keys}
    edge_faces = defaultdict(list)
    for face_index, triangle in enumerate(triangles):
        ids = [keys[ref[0]] for ref in triangle]
        for start, end in ((ids[0], ids[1]), (ids[1], ids[2]),
                           (ids[2], ids[0])):
            if start != end:
                edge_faces[tuple(sorted((start, end)))].append(face_index)
    return edge_faces, coordinates


def _palm_plane(positions, triangles, owners, side):
    vertices = {ref[0]
                for face_index, owner in owners.items()
                if owner == f"hand_{side}"
                for ref in triangles[face_index]}
    # UV seams duplicate OBJ position indices. Weight each welded location
    # once or the fitted normal drifts toward high-UV-density armour panels.
    unique = {tuple(round(value, 6) for value in positions[index])
              for index in vertices}
    points = [point for point in unique if 1.92 < point[1] < 2.22]
    if len(points) < 12:
        raise RuntimeError(f"not enough distal palm points on {side}: {len(points)}")
    center = tuple(sum(point[axis] for point in points) / len(points)
                   for axis in range(3))
    covariance = [[0.0] * 3 for _ in range(3)]
    for point in points:
        delta = _sub(point, center)
        for row in range(3):
            for column in range(3):
                covariance[row][column] += delta[row] * delta[column]
    normal = _smallest_eigenvector_symmetric3(covariance)
    toward_body = (-1.0, 0.0, 0.0) if side == "l" else (1.0, 0.0, 0.0)
    if _dot(normal, toward_body) < 0.0:
        normal = _mul(normal, -1.0)
    return center, normal


def _digit_seam(edge_faces, coordinates, owners, side, digit):
    hand = f"hand_{side}"
    digit_family = {f"finger_{digit}_{side}",
                    f"finger_{digit}_tip_{side}"}
    edges = []
    for edge, adjacent in edge_faces.items():
        if len(adjacent) != 2:
            continue
        owner_a, owner_b = owners[adjacent[0]], owners[adjacent[1]]
        if ((owner_a in digit_family and owner_b == hand)
                or (owner_b in digit_family and owner_a == hand)):
            edges.append(edge)
    if not edges:
        raise RuntimeError(f"no welded digit/palm seam for {side} {digit}")
    weighted = [0.0, 0.0, 0.0]
    total_length = 0.0
    for start_key, end_key in edges:
        start, end = coordinates[start_key], coordinates[end_key]
        length = _length(_sub(end, start))
        if length <= 1.0e-12:
            continue
        midpoint = _mul(_add(start, end), 0.5)
        for axis in range(3):
            weighted[axis] += midpoint[axis] * length
        total_length += length
    if total_length <= 1.0e-12:
        raise RuntimeError(f"zero-length digit/palm seam for {side} {digit}")
    return tuple(value / total_length for value in weighted), total_length


def _thumb_target(positions, triangles, face_bones, side, seam_center):
    name = f"finger_thumb_{side}"
    vertices = {ref[0]
                for face_index, owner in face_bones.items()
                if owner == name
                for ref in triangles[face_index]}
    points = [positions[index] for index in vertices]
    if not points:
        raise RuntimeError(f"no source thumb vertices for {name}")
    ordered = sorted(points, key=lambda point: _length(_sub(point, seam_center)))
    distances = [_length(_sub(point, seam_center)) for point in ordered]
    q_index = (len(distances) - 1) * 0.65
    lower = int(math.floor(q_index))
    upper = min(len(distances) - 1, lower + 1)
    fraction = q_index - lower
    threshold = distances[lower] * (1.0 - fraction) + distances[upper] * fraction
    far = [point for point, distance in zip(ordered, distances)
           if distance >= threshold]
    return tuple(sum(point[axis] for point in far) / len(far)
                 for axis in range(3))


def _runtime_matrix_to_geo_rotation(matrix):
    # Runtime matrix is Rz(z) * Ry(y) * Rx(x). Gecko loads JSON rotation
    # [jx,jy,jz] as runtime [-jx,-jy,+jz].
    sy = max(-1.0, min(1.0, -matrix[2][0]))
    y = math.asin(sy)
    cy = math.cos(y)
    if abs(cy) > 1.0e-8:
        x = math.atan2(matrix[2][1], matrix[2][2])
        z = math.atan2(matrix[1][0], matrix[0][0])
    else:
        x = 0.0
        z = math.atan2(-matrix[0][1], matrix[1][1])
    return [-math.degrees(x), -math.degrees(y), math.degrees(z)]


def recover_finger_frames(positions, triangles, face_bones, owners,
                          source_pivots, finger_order, root_embed):
    """Return source-space MCPs and one static runtime axis frame per digit."""
    edge_faces, coordinates = _welded_edge_faces(positions, triangles)
    frames = {}
    roots = {}
    palm_planes = {}
    for side in ("l", "r"):
        palm_center, palm_normal_source = _palm_plane(
            positions, triangles, owners, side)
        palm_normal_runtime = _normalise(
            _matrix_vector(A_SOURCE_TO_RUNTIME, palm_normal_source))
        palm_planes[side] = {
            "center_source": palm_center,
            "normal_source": palm_normal_source,
            "normal_runtime": palm_normal_runtime,
        }
        for digit in finger_order:
            root_name = f"finger_{digit}_{side}"
            seam_center, seam_length = _digit_seam(
                edge_faces, coordinates, owners, side, digit)
            if digit == "thumb":
                target = _thumb_target(
                    positions, triangles, face_bones, side, seam_center)
            else:
                target = source_pivots[f"finger_{digit}_tip_{side}"]
            tangent_source = _normalise(_sub(target, seam_center))
            tangent_runtime = _normalise(
                _matrix_vector(A_SOURCE_TO_RUNTIME, tangent_source))
            palm_flex_runtime = _normalise(_sub(
                palm_normal_runtime,
                _mul(tangent_runtime,
                     _dot(palm_normal_runtime, tangent_runtime))))
            hinge_runtime = _normalise(
                _cross(tangent_runtime, palm_flex_runtime))
            # Canonical clean finger: local -Y points distally, +X points
            # toward palm, +Z is the positive anatomical flexion hinge.
            runtime_matrix = _transpose_columns((
                palm_flex_runtime,
                _mul(tangent_runtime, -1.0),
                hinge_runtime,
            ))
            determinant = _det3(runtime_matrix)
            if determinant < 0.999:
                raise RuntimeError(
                    f"left-handed finger frame {root_name}: det={determinant}")
            roots[root_name] = _sub(
                seam_center, _mul(tangent_source, root_embed))
            frames[root_name] = {
                "mcp_source": roots[root_name],
                "root_embed": root_embed,
                "side": side,
                "digit": digit,
                "seam_center_source": seam_center,
                "seam_length_source": seam_length,
                "bind_tangent_source": tangent_source,
                "bind_tangent_runtime": tangent_runtime,
                "palm_flex_runtime": palm_flex_runtime,
                "hinge_runtime": hinge_runtime,
                "runtime_matrix": runtime_matrix,
                "geo_rotation": _runtime_matrix_to_geo_rotation(runtime_matrix),
            }
    return roots, frames, palm_planes


def install_axis_adapters(geometry, pivots, frames, lengths, scale):
    """Add one unanimated adapter per digit and keep legacy joint names."""
    bones = geometry["bones"]
    by_name = {bone["name"]: bone for bone in bones}
    insertions = []
    for root_name, frame in frames.items():
        side, digit = frame["side"], frame["digit"]
        tip_name = f"finger_{digit}_tip_{side}"
        distal_name = f"finger_{digit}_distal_{side}"
        axis_name = f"finger_{digit}_axis_{side}"
        root = list(pivots[root_name])
        l1, l2, _ = lengths[digit]
        tip = [root[0], root[1] - l1 * scale, root[2]]
        distal = [tip[0], tip[1] - l2 * scale, tip[2]]
        pivots[axis_name] = root
        pivots[root_name] = root
        pivots[tip_name] = tip
        pivots[distal_name] = distal
        by_name[root_name]["parent"] = axis_name
        by_name[root_name]["pivot"] = [round(value, 5) for value in root]
        by_name[tip_name]["pivot"] = [round(value, 5) for value in tip]
        by_name[distal_name]["pivot"] = [round(value, 5) for value in distal]
        axis_bone = {
            "name": axis_name,
            "parent": f"hand_{side}",
            "pivot": [round(value, 5) for value in root],
            "rotation": [round(value, 8) for value in frame["geo_rotation"]],
        }
        insertions.append((bones.index(by_name[root_name]), axis_bone))
    for index, axis_bone in sorted(insertions, reverse=True):
        bones.insert(index, axis_bone)
    return pivots


def validate_axis_frames(frames, tolerance_degrees=1.0):
    """Fail closed on bind mapping, mirror parity and flexion half-space."""
    cosine_gate = math.cos(math.radians(tolerance_degrees))
    by_digit = defaultdict(dict)
    for root_name, frame in frames.items():
        matrix = frame["runtime_matrix"]
        columns = [tuple(matrix[row][column] for row in range(3))
                   for column in range(3)]
        if _det3(matrix) < 0.999:
            raise RuntimeError(f"invalid adapter handedness for {root_name}")
        for column in columns:
            if abs(_length(column) - 1.0) > 1.0e-5:
                raise RuntimeError(f"non-unit adapter axis for {root_name}")
        if max(abs(_dot(columns[a], columns[b]))
               for a in range(3) for b in range(a + 1, 3)) > 1.0e-5:
            raise RuntimeError(f"non-orthogonal adapter axes for {root_name}")
        mapped_tangent = _mul(columns[1], -1.0)  # local -Y
        if _dot(mapped_tangent, frame["bind_tangent_runtime"]) < cosine_gate:
            raise RuntimeError(f"adapter loses bind tangent for {root_name}")
        if _dot(columns[0], frame["palm_flex_runtime"]) < cosine_gate:
            raise RuntimeError(f"adapter loses palm flex axis for {root_name}")
        if _dot(columns[2], frame["hinge_runtime"]) < cosine_gate:
            raise RuntimeError(f"adapter loses hinge for {root_name}")
        recovered_seam = _add(
            frame["mcp_source"],
            _mul(frame["bind_tangent_source"], frame["root_embed"]))
        if _length(_sub(recovered_seam, frame["seam_center_source"])) > 1.0e-6:
            raise RuntimeError(f"MCP is not embedded from seam for {root_name}")
        # Positive local Z must move local -Y toward local +X.
        theta = math.radians(5.0)
        curled_local = (math.sin(theta), -math.cos(theta), 0.0)
        curled_runtime = _matrix_vector(matrix, curled_local)
        base_runtime = _matrix_vector(matrix, (0.0, -1.0, 0.0))
        inward_gain = _dot(_sub(curled_runtime, base_runtime),
                           frame["palm_flex_runtime"])
        if inward_gain <= 0.01 * math.sin(theta):
            raise RuntimeError(f"positive curl leaves palm half-space for {root_name}")
        by_digit[frame["digit"]][frame["side"]] = frame

    mirror_x = ((-1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 1.0))
    for digit, pair in by_digit.items():
        if set(pair) != {"l", "r"}:
            raise RuntimeError(f"missing mirrored frame for {digit}")
        left, right = pair["l"], pair["r"]
        checks = (
            (right["bind_tangent_runtime"],
             _matrix_vector(mirror_x, left["bind_tangent_runtime"]),
             "tangent"),
            (right["palm_flex_runtime"],
             _matrix_vector(mirror_x, left["palm_flex_runtime"]),
             "flex"),
            # Cross products are pseudovectors under a reflection.
            (right["hinge_runtime"],
             _mul(_matrix_vector(mirror_x, left["hinge_runtime"]), -1.0),
             "hinge"),
        )
        for actual, expected, label in checks:
            if _length(_sub(actual, expected)) > 0.02:
                raise RuntimeError(
                    f"left/right {label} mirror mismatch for {digit}")



