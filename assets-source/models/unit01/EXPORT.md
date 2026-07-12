# Unit-01 asset state

The active local evaluation model is generated from Tigerar1's downloaded
CC BY-SA Unit-01 OBJ by `tools/make_tiger_unit01_pack.py`. If that generator is
not run, the preceding local SmOd pack may remain selected; if the Tiger mesh
itself fails to parse after generation, the repository's cube geometry is the
runtime safety fallback. Downloaded archives, extracted files, generated
triangle meshes and the local resource pack are Git-ignored and must not be
committed.

This folder does not contain the third-party OBJ or texture. The converter
preserves all 4,226 triangles and their UVs in an ignored mesh resource. It
partitions the armour into exactly 17 standard mesh parts, including separate
`foot_l` and `foot_r` shells parented to `shin_l` and `shin_r`; non-mesh
weapon, entry-plug and hatch attachment bones are additional Gecko bones and
are not included in that part count. No triangles are added or removed by the
ankle split. The current partition is a rigid prototype; elbows, wrists,
ankles and waist still need joint-liner or weighted-skinning review before
production approval.

The converter output and parent relationships pass the offline local-pack
validator. The split only makes independent ankle posing possible: it does not
by itself establish that the crouch is a convincing one-knee pose. That remains
blocked on a new Visual Lab game capture.

The Tigerar1 head is used unchanged; no procedural mask is added. The local
Longinus bone still uses EUD 1.1.0's CC BY-NC 4.0 model/texture when that
ignored jar is present. Each asset retains its own licence and attribution;
none is relicensed as MIT with the Project SEELE code.

Local regeneration:

```text
python tools/make_smod_model_pack.py
python tools/make_tiger_unit01_pack.py
```

Expected output is `run/resourcepacks/eva_real_model/`.
