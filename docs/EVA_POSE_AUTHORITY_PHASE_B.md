# EVA Pose Authority Phase B

Status: **post-Gecko single commit authority active; r03 admits one
human-selected live-test MotionEngine action**.

Phase B promotes the Phase-A observer into the only orchestrator allowed to
write EVA bones after Gecko has evaluated its controllers. Preview/live motion,
weapon pitch and pilot head now execute through `EvaPoseGraph.commit`, with
conditional ownership when a live full-body action already owns aim or head.

## Authority boundary

The runtime order is:

1. `GECKO_COMPOSITE` evaluates the existing `base`, `arms` and `strike`
   controllers. Phase B deliberately treats their current internal blend as
   one upstream source; it does not pretend to have byte-level per-controller
   bone provenance.
2. `MOTION_ENGINE_PREVIEW` may replace the exact bones returned by
   `EvaMotionEngineV2`, but only for quarantined Motion Lab previews. Official
   captures continue to reject this owner.
3. `MOTION_ENGINE_LIVE_ACTION` may own only an explicitly human-selected live
   action mask. r03 currently admits the selected standing-fists Group C
   ordinary attack; it does not admit Phase U kicks or research previews.
4. `POSE_GRAPH_WEAPON_AIM` writes `aim_pitch` only when the active motion owner
   has not already written it.
5. `POSE_GRAPH_PILOT_AIM` writes `head` only when a pilot exists and the active
   motion owner has not already written it.

Every canonical bone therefore has one final rotation, position and scale
owner. Possible overlap inside the upstream Gecko controller stack is recorded
separately as `upstreamOverlapCandidates`; it is not mislabeled as a
final-owner conflict.

## Migration guarantees

- Gecko fallback families remain anchored to commit `a910890b`; the selected
  ordinary attack is locked separately by its live motion-resource hash.
- `EvaUnit01Renderer` contains no rotation, position or scale write and does
  not invoke MotionEngine directly.
- The only Java call to `EvaMotionEngineV2.apply` is inside
  `EvaPoseGraph.commit`.
- MotionEngine reports separate rotation-bone and position-bone write sets plus
  the actual preview/live owner; the recorder stores all three channel-owner
  maps and timelines.
- The final-matrix recorder requires an enforced commit serial and an empty
  final-owner conflict map for every accepted frame.
- Phase B remains anchored to migration baseline `cee87f5`; later action
  promotion must carry an independent human receipt and resource hash.

Rebuild and validate the current contracts with:

```powershell
py -3 tools\build_eva_phase_b_contracts.py
py -3 tools\validate_eva_phase_b_contract.py
```

The named entry point delegates to the original deterministic contract builder
and emits the current Phase-B version `eva_pose_graph_enforced_r03`.

Run a one-frame final-matrix smoke capture with:

```powershell
.\gradlew.bat runClient -PstrictHighDetail=true `
  -PquickPlayWorld=SEELE_EVA_MOTION_LAB -PposeCaptureSmoke=true
py -3 tools\validate_eva_pose_capture.py
```

The Phase-A `004012` and final Phase-B `012027` idle captures were also checked
with `tools/audit_eva_pose_capture_equivalence.py`: all 70 final position,
rotation and scale vectors were identical; maximum local/model matrix deltas
were `8.0e-6` and `1.90e-6`, both below the `1.0e-5` migration limit. The tool
is generic and should be reused for later authority-only migrations; it now
keeps `modelMatrix` at `1.0e-5` and gives Gecko's camera-bearing
`localSpaceMatrix` a separate `2.0e-5` cross-launch limit.

## What Phase B does not solve

The Gecko `base`/`arms`/`strike` stack is still one upstream composite. A later
phase may replace it with explicit mask-aware pose nodes, but only after a
matrix-equivalent adapter exists. The current stride-8 local mesh format also
remains single-bone rigid geometry; it cannot express the canonical weighted
inner body required by a Hybrid Rig. Phase C now defines and validates the
weighted format (`docs/EVA_SKINNED_MESH_PHASE_C.md`), while the production
renderer/asset migration remains isolated until its evaluated-mesh seam gates
pass.

The authority migration itself needs no aesthetic approval. Individual live
actions still require a project-owner receipt and semantic hash; Phase U kicks
remain review-only even when their matrices pass.
