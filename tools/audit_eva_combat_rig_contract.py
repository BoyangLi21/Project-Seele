"""Audit the current Blender EVA against the physical visual-rig contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--contract", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--rig", default="EVA_ANATOMICAL_ARMATURE")
parser.add_argument("--mesh", default="EVA_ANATOMICAL_RIGID_MESH")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

contract = json.loads(args.contract.read_text(encoding="utf-8"))
rig = bpy.data.objects[args.rig]
mesh = bpy.data.objects[args.mesh]
bone_names = {bone.name for bone in rig.data.bones}
group_names = {group.name for group in mesh.vertex_groups}
missing_bones = sorted(set(contract["required_visual_bones"]) - bone_names)
unweighted_required = sorted(
    name for name in contract["required_visual_bones"]
    if name in bone_names and name not in group_names
    and name not in {"world_root"}
)
missing_interfaces = [
    pair for pair in contract["required_flexible_interfaces"]
    if pair[0] not in bone_names or pair[1] not in bone_names
]

payload = {
    "schema": 1,
    "blend": bpy.data.filepath,
    "contract": str(args.contract.resolve()),
    "bone_count": len(bone_names),
    "mesh_group_count": len(group_names),
    "missing_required_bones": missing_bones,
    "required_bones_without_direct_mesh_group": unweighted_required,
    "interfaces_blocked_by_missing_bones": missing_interfaces,
    "production_ready": not missing_bones and not missing_interfaces,
    "verdict": "PASS" if not missing_bones and not missing_interfaces else "FAIL",
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(payload, ensure_ascii=False))
