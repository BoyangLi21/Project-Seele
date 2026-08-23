import bpy
import json
import sys


path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=path, use_anim=True)

report = {"objects": [], "actions": []}
for obj in bpy.context.scene.objects:
    entry = {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
    }
    if obj.type == "MESH":
        entry.update({
            "vertices": len(obj.data.vertices),
            "polygons": len(obj.data.polygons),
            "materials": [slot.material.name if slot.material else None
                          for slot in obj.material_slots],
            "vertex_groups": [group.name for group in obj.vertex_groups],
            "dimensions": list(obj.dimensions),
        })
    elif obj.type == "ARMATURE":
        entry["bones"] = [bone.name for bone in obj.data.bones]
    report["objects"].append(entry)

for action in bpy.data.actions:
    report["actions"].append({
        "name": action.name,
        "frame_range": list(action.frame_range),
        "slots": [slot.name for slot in action.slots],
    })

print("ULTRAMAN_REPORT=" + json.dumps(report, ensure_ascii=False))
