# EVA weighted inner proxy Phase D

Status: **after-recursion weighted proxy operational behind a userdev flag;
Tiger remains the live body**.

Phase D connects the reusable Phase-C skinning runtime to Gecko's completed
model-space bone palette. It uses only a procedural Project SEELE proxy and
does not modify an animation, pose bone, Tiger triangle or gameplay state.

## Procedural Unit-01 proxy

`tools/build_eva_weighted_inner_proxy.py` derives model-space joint locations
from the 70-bone canonical rig using:

```text
x = -pivotX / 16
y =  pivotY / 16
z =  pivotZ / 16
```

It builds 15 capped eight-sided joint tubes covering:

- root, lower torso, upper torso and neck;
- both clavicle/shoulder, upper-arm/elbow and forearm/wrist chains;
- both pelvis/hip, thigh/knee and shin/ankle chains.

Each tube has parent, 50/50 and child rings. The result contains 18 palette
bones, 390 vertices, 720 triangles and 120 genuinely dual-weighted vertices.
Its bind envelope is approximately `x=±1.896`, `y=0.012..10.268` and
`z=±1.1` model blocks.

This is not yet a production inner body: the 15 tubes are individually closed
and overlap at junctions rather than sharing a welded, manifold skin surface.
It proves palette placement and deformation without pretending to solve final
topology or aesthetics.

## After-recursion renderer

`EvaWeightedInnerProxy` is loaded during resource reload but renders only when
the JVM property `projectseele.skinnedProxyPreview=true` is present. The
renderer:

1. enables Gecko matrix tracking only for the 18 proxy palette bones;
2. waits until `super.renderRecursively` has completed the root and all
   descendants;
3. samples the final Phase-B model matrices;
4. runs Phase-C weighted positions and inverse-transpose normals;
5. submits a translucent cyan research overlay without hiding or replacing
   the Tiger body.

It never calls a bone rotation/position setter. The default property state is
off, and the contract explicitly fixes `replacesTigerBody=false`,
`writesPoseBones=false` and `productionReady=false`.

## Runtime evidence

The Phase-D smoke capture reports:

```text
palette=18
segments=15
vertices=390
triangles=720
blended_vertices=120
rendered_frames=1
idle_bind_delta=1.4305115e-6
replaces_tiger=false
```

Phase C and Phase D retain identical final position, rotation and scale values
for all 70 canonical bones. Their maximum model/local matrix deltas are
`1.0e-6` and `5.0e-6`, respectively.

## Validation

```powershell
py -3 tools\build_eva_weighted_inner_proxy.py
py -3 tools\validate_eva_phase_d_weighted_proxy.py
py -3 tools\validate_eva_phase_c_skinning.py
.\gradlew.bat build
.\gradlew.bat runClient -PstrictHighDetail=true `
  -PquickPlayWorld=SEELE_EVA_MOTION_LAB `
  -PposeCaptureSmoke=true -PskinnedProxyPreview=true
py -3 tools\validate_eva_pose_capture.py
```

No human action review is required for Phase D because the overlay is an
engineering proxy, not an animation or candidate production body. Promotion
still requires a welded weighted inner mesh, rigid armor-shell masks,
evaluated seam gates across the six foundation actions and human acceptance of
the resulting silhouette.
