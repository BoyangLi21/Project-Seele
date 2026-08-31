# EVA manifold inner body Phase E

Status: **single-component weighted inner surface and rigid Tiger masks pass;
production body replacement remains disabled**.

Phase E replaces the overlapping Phase-D engineering tubes with a single
procedural closed surface. It also records every current Tiger part as a
single-owner rigid shell. No Tiger triangle, animation or gameplay pose is
changed.

## Manifold generation

`tools/build_eva_manifold_inner_body.py` uses no new installed dependency. It
builds a voxel union from the canonical torso, arm, leg, head, hand and foot
capsules, fills enclosed voids, removes diagonal voxel saddles, extracts a
shared-vertex cubical boundary and applies three deterministic Laplacian
smoothing passes.

The resulting project-owned body is:

```text
palette_bones=23
primitives=20
vertices=3278
triangles=6552
components=1
non_manifold_edges=0
euler_characteristic=2
signed_volume=42.2488413
influences: 2=257, 3=45, 4=2976
```

Every edge has exactly two incident triangles, all vertices belong to one
component, the orientation has positive volume and the topology is sphere-like
(`V-E+F=2`). Weights are derived from capsule proximity, limited to four
canonical bones and normalized after deterministic rounding.

## Rigid Tiger shell masks

`eva_unit01_rigid_shell_masks.json` is an aggregate contract over the active
local Tiger mesh; it does not copy any third-party triangle data into Git.

- all 43 body parts retain exactly one owner bone;
- all 6,044 triangles are accounted for;
- finger parts are marked `RIGID_DIGIT_SHELL`;
- all other parts are marked `RIGID_ARMOR_SHELL`;
- the source semantic SHA-256 must match the currently installed local mesh.

The weighted manifold is therefore an independent inner layer while the
existing outer parts remain rigid shells.

## Runtime isolation

`EvaManifoldInnerBody` loads the body and mask contracts during resource
reload. Rendering requires the explicit userdev property
`projectseele.manifoldInnerPreview=true`; the default remains off. It samples
the final Phase-B palette after root recursion, writes no bones and submits a
green translucent engineering overlay without hiding Tiger.

The Phase-E smoke capture reports:

```text
rendered_frames=1
idle_bind_delta=2.861023e-6
replaces_tiger=false
```

Phase D and Phase E retain identical final position, rotation and scale values
for all 70 canonical bones. Maximum model/local matrix differences are
`1.7e-6` and `7.63e-6`.

## Validation

```powershell
py -3 tools\build_eva_manifold_inner_body.py
py -3 tools\validate_eva_phase_e_manifold.py
py -3 tools\validate_eva_phase_d_weighted_proxy.py
.\gradlew.bat build
.\gradlew.bat runClient -PstrictHighDetail=true `
  -PquickPlayWorld=SEELE_EVA_MOTION_LAB `
  -PposeCaptureSmoke=true -PmanifoldInnerPreview=true
py -3 tools\validate_eva_pose_capture.py
```

This is still not visually approved production skin. Phase E proves bind
space, topology, weights and rigid-shell accounting only. The next stage must
evaluate the manifold and armor clearance over idle, walk, run, jump/landing,
one unarmed attack and one Progressive Knife attack, including triangle
inversion, self-intersection and visible seam/clearance gates before any live
body switch is considered.
