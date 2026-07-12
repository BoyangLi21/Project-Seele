# Unit-02 external evaluation

- Source: [Tigerar1 Evangelion Unit-02](https://sketchfab.com/3d-models/evangelion-unit-02-a8731145a84f4e63b0fbc51f4f5948da)
- Page licence: CC BY-SA (no version asserted by the model page)
- Local archive: `external-assets/incoming/evangelion-unit-02.zip` (Git-ignored)
- Converter: `tools/make_tiger_eva_variants_pack.py --only unit02`
- Runtime output: local resource-pack files only; the source model and derived art are not MIT assets

The OBJ contains 3,384 source vertices and 3,952 triangles. It shares the
Unit-01 192-pixel, 17-mesh-part contract and can reuse all existing EVA
locomotion, prone, melee, lance and cannon animation names. Separate `foot_l`
and `foot_r` parts are parented to their corresponding shins, while the total
remains exactly 3,952 triangles. Non-mesh attachment bones are not included in
the 17-part count.

This is rigid per-bone partitioning, not weighted skinning. Shoulder, elbow,
wrist, hip, knee and ankle seams must be checked in Visual Lab before release.
The 17-part contract passes offline validation; its final crouch and ankle
silhouette remain blocked on a new in-game capture.
