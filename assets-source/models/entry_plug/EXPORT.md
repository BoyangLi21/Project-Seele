# Entry Plug local export

The runtime Entry Plug is generated only into the ignored
`run/resourcepacks/eva_real_model/` pack.

## Sources

- Crymsin, `Entry Plug (Evangelion)`, Thingiverse item 2501188, CC BY. The
  downloaded `EntryPlugSolidv3.obj` supplies the pressure-capsule exterior.
- DONW999, `Neo Genesis Evangelion Entry Plug Pilot Seat - The Soul Throne`,
  Thingiverse item 4961673, CC BY. The downloaded archive unexpectedly contains
  only `Stand.stl`; its bundled render images are used as proportion references
  for a clean-room Project SEELE seat and two induction levers.

Neither archive nor the converted mesh is committed or redistributed.

## Rebuild

Run:

```text
python tools/make_entry_plug_model.py
```

The wrapper locates Blender, cuts a physical hatch opening, decimates the five
exterior material groups separately, adds the cockpit, and emits:

- `mesh/entry_plug.mesh.json`
- `textures/entity/entry_plug.png`

The reviewed contract is 8 x 8 x 50 model pixels, 11,654 triangles and three
runtime parts. The EVA itself was enlarged to its final two-times world scale,
but the pressure capsule deliberately was not enlarged one-for-one. At the
final 3.2 render scale the independent physical carrier is approximately
1.6 x 10 blocks; its 2 x 10 block interaction volume follows that shell and
the hatch can be used from up to 14 blocks away. The capsule is hidden after
insertion; the EVA body does not render a second dorsal copy.

All exported geometry uses a single canonical frame: the insertion tip is the
origin, +Z runs outward along the capsule, -Z is the insertion direction, +Y
is the hatch/top side and +X is right. Runtime kinematics must not add a
second pivot or axis-correction rotation.
