# S19 Local Command Asset Audit

This document records facts measured directly from the private local
`nerv_command_left.nbt`. It is a geometry contract, not an interpretation of
the Evangelion setting. The NBT remains private and is not distributed.

## Authority and transform

- Authored template size: `56 x 77 x 129`.
- Facility transform: `CLOCKWISE_180`.
- Placement base relative to the facility centre:
  `(27, -368, 64)`.
- A template block `(x, y, z)` therefore lands at:
  `(27 - x, -368 + y, 64 - z)`.
- Exact transformed envelope:
  `x[-28, 27] y[-368, -292] z[-64, 64]`.
- The north/front screen wall is at negative relative Z. The command tower is
  on the south/rear side.

No post-pass may clear or rebuild this envelope. A post-pass may only:

1. replace an explicitly registered dummy-screen mask in place;
2. bind an interaction entity to an authored chair or button;
3. join an explicitly registered boundary port outside the envelope.

## Authored command hierarchy

Measured chair anchors after transform:

| Role | Block anchor | Ride anchor |
|---|---:|---:|
| Ikari | `(1, -309, 10)` | `(1.5, -308.42, 10.5)` |
| Fuyutsuki | `(4, -312, 1)` | `(4.5, -311.42, 1.5)` |
| Operator left | `(-7, -325, -4)` | `(-6.5, -324.42, -3.5)` |
| Operator centre | `(1, -327, -12)` | `(1.5, -326.42, -11.5)` |
| Operator right | `(9, -325, -4)` | `(9.5, -324.42, -3.5)` |

Ikari is the sole highest central command position. Fuyutsuki is lower and
offset beside him. New geometry must not mirror the two into equal thrones.

## Authored rear route

The two-block door behind Ikari is at:

`(1, -309..-308, 15)`.

The source asset already contains a narrow authored structure behind this
door through approximately `z=27`. A clean rebuild must inspect and preserve
that structure, then terminate it at one registered rear vestibule/lift port.
It must not create a lateral bridge across the command-room sightline.

The retired `buildCommanderLiftGallery()` post-pass occupied:

`x[4,58] y[-340,-305] z[7,15]`.

That volume crossed the authored command tower and produced the erroneous
extra passage visible in human review. It is forbidden in the clean rebuild.

## In-place sloped screen dummies

The source asset contains two distinct stepped/sloped coloured screen fields.
They face the command hierarchy and must be replaced at their current
surfaces, not accompanied by a second video wall.

### Amber upper plane

Primary transformed mask:

- X span: about `[-7, 9]`.
- Connected component: `425` authored blocks.
- Y span: `[-334, -304]`.
- Z span: `[-44, -28]`.
- Least-squares side slope: `dY/dZ = -1.940`.
- Surface inclination: `62.7 degrees` from horizontal.
- A vertical XY display plane therefore needs approximately `XRot=-27.3`
  degrees; using `-62.7` would apply the complementary angle and be wrong.
- Source materials: yellow concrete plus ochre froglight.

### Orange lower plane

Primary transformed mask:

- X span: about `[-7, 9]`.
- Connected component: `756` authored blocks.
- Y span: `[-337, -323]`.
- Z span: `[-64, -26]`.
- Orange glass face span: `x[-6,8]`.
- Least-squares side slope: `dY/dZ = -0.388`.
- Surface inclination: `21.2 degrees` from horizontal.
- A vertical XY display plane therefore needs approximately `XRot=-68.8`
  degrees.
- Source materials: orange stained glass, orange concrete and ochre
  froglight.

The previous generic display panels at constant `z=-58` and pitches around
`-10 degrees` do not conform to either authored plane. The clean presentation
must derive display transforms from these masks or replace the stepped blocks
themselves with emissive translucent screen material.

## Clean-save isolation

`SEELE_FULL_REBUILD` is a broken read-only archive. The clean target is:

`SEELE_CLEAN_REBUILD`.

It is copied from normal-noise `level.dat` metadata only. The following are
not copied:

- `region`, `entities`, `poi`, `dimensions`, `data`;
- `playerdata`, `stats`, `advancements`;
- old datapacks/server config;
- old Project SEELE SavedData, builder receipts and facility entities.

The clean save marker is:

`.projectseele_clean_rebuild.json`.

No legacy full-map builder, rescue director, runtime repair pass or legacy
command alias may write into this save.
