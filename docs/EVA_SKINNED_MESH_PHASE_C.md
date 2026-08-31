# EVA weighted-mesh runtime Phase C

Status: **weighted-mesh format and deterministic runtime reference active;
current Tiger body remains the unchanged rigid mesh**.

Phase C removes the data-format blocker identified after Pose Authority Phase
B. It does not claim that a production Hybrid Rig exists, and it does not
connect any weighted asset to `EvaUnit01Renderer`.

## Format contract

`assets/projectseele/eva/eva_skinned_mesh_contract.json` defines
`projectseele:skinned_mesh_v1`:

- bind positions and normals are in reflected Gecko model space, in blocks;
- matrices are 16 column-major JOML floats;
- each vertex stores position, UV, normal, four palette indices and four
  weights in a 16-value packed stride;
- weights are finite, non-negative and sum to one within `1e-5`;
- the deformation formula is
  `currentModel * inverseBind * bindPosition` per influence, followed by a
  weighted sum;
- normals use the inverse-transpose of each skin matrix and are normalized
  after blending.

The project-owned `skinning_probe_v1.json` is a two-bone, six-vertex ribbon.
Its middle ring has true 50/50 dual-bone weights. A 90-degree child-joint test
has explicit expected positions, so row/column order, inverse-bind direction
and weight application cannot silently mirror one another while still passing.

## Runtime reference

`EvaSkinnedMeshRuntime` loads the contract and probe during resource reload. It
fails closed on:

- duplicate or out-of-range palette entries;
- malformed matrices, vertices or triangles;
- invalid weights or a probe without blended vertices;
- bind-pose round-trip error, posed-position error or normalized-normal error
  above `1e-5`;
- any contract that enables a live skinned body or claims a production asset.

The accepted runtime probe is:

```text
palette=2
vertices=6
triangles=4
blended_vertices=2
bind_error=0
pose_error=0
normal_error=5.96e-8
live_body=false
```

The final-pose recorder embeds the contract/probe SHA-256 values and the
`skinnedLiveBodyEnabled=false` isolation flag in every capture header.

The Phase-B and Phase-C idle captures retain identical final position,
rotation and scale values for all 70 bones. Their maximum model-matrix delta is
`2.0e-6`; Gecko's camera/render-offset-bearing `localSpaceMatrix` differs by
`9.0e-6`, below its separate cross-launch limit of `2.0e-5`.

## Validation

```powershell
py -3 tools\validate_eva_phase_c_skinning.py
py -3 tools\validate_eva_phase_b_contract.py
.\gradlew.bat build
.\gradlew.bat runClient -PstrictHighDetail=true `
  -PquickPlayWorld=SEELE_EVA_MOTION_LAB -PposeCaptureSmoke=true
py -3 tools\validate_eva_pose_capture.py
```

## Promotion boundary

The live body remains `LocalTriangleMeshLayer` format v1 with stride 8 and one
rigid owning bone per part. Phase C performs no aesthetic change and therefore
needs no human animation review.

A later phase must still provide a Unit-01 weighted inner body, rigid armor
shell assignments and an after-recursion palette renderer. Phase D now proves
that hook with an isolated procedural joint proxy
(`docs/EVA_WEIGHTED_PROXY_PHASE_D.md`), but its overlapping tubes are not a
welded production body. It may set
`skinnedBodyEnabled=true` only after evaluated shoulder, wrist, hip and ankle
seam growth is at most `0.005 H`, all six foundation action slices pass runtime
capture, and a human accepts the resulting silhouette and deformation.
