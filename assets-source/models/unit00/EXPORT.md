# Unit-00 external evaluation

- Source: [Tigerar1 Evangelion Unit-00](https://sketchfab.com/3d-models/evangelion-unit-00-abe48f0c88914d66b7a5c916704767b3)
- Page licence: CC BY-SA (no version asserted by the model page)
- Local archive: `external-assets/incoming/evangelion-unit-00.zip` (Git-ignored)
- Converter: `tools/make_tiger_eva_variants_pack.py --only unit00`
- Runtime output: local resource-pack files only; the source model and derived art are not MIT assets

The OBJ contains 3,120 source vertices and 3,692 triangles. The converter
normalizes it to the same 192-pixel, 17-mesh-part contract as Unit-01. Separate
`foot_l` and `foot_r` parts are parented to their corresponding shins, while
the total remains exactly 3,692 triangles. Non-mesh attachment bones are not
included in the 17-part count. The Project SEELE cube body remains a per-bone
failure fallback. The functional shield is a separate Project SEELE
attachment; it is not part of the downloaded Tigerar1 body. Its current
full-height two-cube plate and dedicated two-arm brace are verified together by
the offline cube-attachment renderer; release art still needs an original
editable shield source and an in-game capture.

This is rigid per-bone partitioning, not weighted skinning. Shoulder, elbow,
wrist, hip, knee and ankle seams must be checked in Visual Lab before release.
The 17-part contract passes offline validation; its final crouch and ankle
silhouette remain blocked on a new in-game capture.
