# EVA Pose Authority Phase B

Status: **post-Gecko single commit authority active; no animation resource or
gameplay action changed**.

Phase B promotes the Phase-A observer into the only orchestrator allowed to
write EVA bones after Gecko has evaluated its controllers. The migration keeps
the exact previous MotionEngine, weapon-pitch and pilot-head formulas, but they
now execute in one declared order through `EvaPoseGraph.commit`.

## Authority boundary

The runtime order is:

1. `GECKO_COMPOSITE` evaluates the existing `base`, `arms` and `strike`
   controllers. Phase B deliberately treats their current internal blend as
   one upstream source; it does not pretend to have byte-level per-controller
   bone provenance.
2. `MOTION_ENGINE_PREVIEW` may replace the exact bones returned by
   `EvaMotionEngineV2`, but only for quarantined Motion Lab previews. Official
   captures continue to reject this authority.
3. `POSE_GRAPH_WEAPON_AIM` writes only `aim_pitch`, including the absolute zero
   reset for non-firearm loadouts.
4. `POSE_GRAPH_PILOT_AIM` writes only `head` when a pilot exists.

Every canonical bone therefore has one final rotation, position and scale
owner. Possible overlap inside the upstream Gecko controller stack is recorded
separately as `upstreamOverlapCandidates`; it is not mislabeled as a
final-owner conflict.

## Migration guarantees

- The eight frozen animation families remain anchored to commit `a910890b`.
- `EvaUnit01Renderer` contains no rotation, position or scale write and does
  not invoke MotionEngine directly.
- The only Java call to `EvaMotionEngineV2.apply` is inside
  `EvaPoseGraph.commit`.
- MotionEngine reports separate rotation-bone and position-bone write sets
  instead of a coarse Boolean; the recorder stores all three channel-owner
  maps and timelines.
- The final-matrix recorder requires an enforced commit serial and an empty
  final-owner conflict map for every accepted frame.
- Phase B is anchored to migration baseline `cee87f5`; changing action JSON is
  neither required nor permitted by this consolidation.

Rebuild and validate the current contracts with:

```powershell
py -3 tools\build_eva_phase_b_contracts.py
py -3 tools\validate_eva_phase_b_contract.py
```

The named entry point delegates to the original deterministic contract builder
and emits the current Phase-B version `eva_pose_graph_enforced_r02`.

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
is generic and should be reused for later authority-only migrations.

## What Phase B does not solve

The Gecko `base`/`arms`/`strike` stack is still one upstream composite. A later
phase may replace it with explicit mask-aware pose nodes, but only after a
matrix-equivalent adapter exists. The current stride-8 local mesh format also
remains single-bone rigid geometry; it cannot express the canonical weighted
inner body required by a Hybrid Rig. That renderer/asset migration is the next
structural step and must remain isolated until its evaluated-mesh seam gates
pass.

Phase B needs no aesthetic approval because it introduces no candidate motion.
Passing matrices means only that the authority migration is technically
eligible; it still cannot approve the appearance of any existing action.
