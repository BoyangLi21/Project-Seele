# Kantrophe positron rifle staging pipeline

- Source: [Kantrophe Positron Rifle - Neon Genesis Evangelion](https://sketchfab.com/3d-models/positron-rifle-neon-genesis-evangelion-523e4d5b344543aa97b21e885f9dc064)
- Page licence: CC Attribution (no version asserted by the model page)
- Page complexity: 29.4k vertices / 56.6k triangles
- Local archive: `external-assets/incoming/positron-rifle-neon-genesis-evangelion.zip` (Git-ignored)

The download contains a Blender 3.04 source file and 4K PBR textures, but no
OBJ, FBX or glTF. A portable Blender 3.6 copy was downloaded from a mirror
selected by the official Blender download page into ignored
`external-assets/tools/`; it is not installed system-wide. The portable 3.6.0
ZIP matched the release manifest SHA256
`AFAC432BE3D302A47AC213971D02840E6ED5251B7D9C1D3DC4A81E7F35B0DBB0`.

Staged workflow:

1. Run `tools/export_positron_rifle_blender.py` with Blender in background
   mode. Its default 0.36 decimation reduced the source from 56,614 to 20,381
   triangles and the exporter did not save changes to the source `.blend`.
2. Run `tools/make_kantrophe_positron_pack.py`. It normalizes the longest axis
   to a 128-pixel weapon length, builds a `cannon` mesh part, downsamples the
   4K material families to a 2048x2048 atlas and preserves a separate
   emissive atlas for a future glow render pass.
3. The authored ground cradles/tripods are a distinct 5,990-triangle support
   material and are excluded by default. The staged handheld body contains
   14,391 triangles. In the neutral `cannon` socket the muzzle points local
   `-Y` and the authored top points local `-Z`; the approximately 92-degree aim
   bend maps them to world forward `-Z` and world up `+Y`. The provisional grip
   origin intersects the lower receiver. The model is an elaborate fan redesign
   rather than a frame-exact copy of the television prop.
4. Test the double-hand socket in Visual Lab after each grip/pose revision.

The Blender export, generated OBJ, atlases and mesh JSON stay under ignored
`external-assets/work/`. They are external CC art, not MIT project assets.
