# Mass Production EVA external evaluation

- Source: [Tigerar1 Mass Production Evangelion](https://sketchfab.com/3d-models/mass-production-evangelion-a483209197814af99fc536b396813698)
- Page licence: CC BY-SA (no version asserted by the model page)
- Local archive: `external-assets/incoming/mass-production-evangelion.zip` (Git-ignored)
- Converter: `tools/make_tiger_eva_variants_pack.py --only mass`
- Runtime output: local resource-pack files only; the source model and derived art are not MIT assets

The source contains 5,341 triangles: 3,392 for the airframe, 1,509 for the
authored wings and 440 for a separate double-bladed weapon. The converter
imports the 4,901 airframe/wing triangles and deliberately excludes the weapon,
which is laid flat at world origin in the neutral OBJ and would otherwise be
glued under the entity. Functional weapon rendering remains a separate socket.

The runtime contract uses 16 bones: the standard EVA torso/limbs plus
`wing_l` and `wing_r`. It supplies the exact animation names consumed by
`MassProductionEvaEntity`: `idle_1`, `move`, `attack`, `visual_attack`,
`revive` and `ritual`. EUD's local replica-lance cubes are grafted after the
Tiger body; the offline cube renderer caught their original 26-pixel ground
penetration, and the adopted idle/move ready pose now keeps the weapon level.
Revive and ritual intentionally hide that cube attachment. The ritual
pose places both arms in a cross while retaining the authored open-wing
silhouette. The source exports chest, neck and both arms as one connected
shell, so the converter uses documented spatial joint cuts; this is still a
rigid prototype and needs in-game seam inspection.
