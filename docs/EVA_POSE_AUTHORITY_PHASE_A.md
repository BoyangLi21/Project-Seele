# EVA Pose Authority Phase A

Status: **observation infrastructure only; no animation or bone is modified by
the Phase-A PoseGraph**.

Phase A freezes the current pre-mocap gameplay baseline and makes the actual
game renderer observable before any new candidate pose is generated.

## Contracts

- `assets/projectseele/eva/eva_rig_schema.json` is the normalized Unit-01
  70-bone canonical schema. Unit-00's `shield` is recorded as a variant-only
  extra. After filtering that explicit extra, all three variants have the same
  canonical bone order and parent map.
- `assets/projectseele/eva/eva_pose_authority_contract.json` partitions every
  canonical bone into one mask and defines the intended owner priority. The
  current `EvaPoseGraph` is strictly `OBSERVE_ONLY_NO_BONE_WRITES`.
- `assets/projectseele/eva/eva_approved_actions.json` hash-locks eight baseline
  action families. Every entry is
  `FROZEN_BASELINE_NOT_VISUALLY_APPROVED`; automatic approval is forbidden.
  Baseline hashes are calculated from the immutable `a910890b` rollback
  snapshot, not from the current animation file. Any drift is regenerated as
  `CANDIDATE_HASH_CHANGED` and makes the Phase-A gate fail pending human review.

The contracts are rebuilt deterministically with:

```powershell
py -3 tools\build_eva_phase_a_contracts.py
py -3 tools\validate_eva_phase_a_contract.py
```

## Final runtime matrix recording

The recorder samples `GeoBone` only after the real Gecko recursive render has
evaluated controllers and after Project SEELE's MotionEngine/aim layers have
run. Each JSONL frame contains:

- active resource-pack mesh/geo/animation/texture hashes;
- entity world transform, velocity, AABB, weapon and stance;
- camera position, yaw, pitch, FOV and view type;
- action token plus contract-derived active layers, resolved owner and
  overlapping owner candidates (the observer does not claim byte-level Gecko
  write provenance);
- final local/model/world matrices for every rendered bone;
- hand/weapon matrices plus the gameplay aim and muzzle socket;
- explicit `UNOBSERVED_PHASE_A` contact fields where no final contact authority
  exists yet.

The companion `.owners.json` file compacts every bone owner and action token
into frame ranges.

Only a normally controlled Motion Lab EVA can start an official recording:

```mcfunction
/seele motionlab reset
/seele motionlab enter unit01
/seele motionlab record start baseline_idle
/seele motionlab record status
/seele motionlab record stop
```

Files are written locally under `run/pose-captures/`. Recording refuses every
legacy Motion Lab demo/physics preview. Motion Lab does not set action, stance
or sprint state for the recorder; the player must use the same inputs as normal
gameplay.

Validate the newest closed recording (or pass an explicit JSONL path) with:

```powershell
py -3 tools\validate_eva_pose_capture.py
py -3 tools\validate_eva_pose_capture.py run\pose-captures\eva_pose_....jsonl
```

An automatic one-frame technical smoke capture is available only in userdev:

```powershell
.\gradlew.bat runClient -PstrictHighDetail=true `
  -PquickPlayWorld=SEELE_EVA_MOTION_LAB -PposeCaptureSmoke=true
```

## Interpretation boundary

The contract's result vocabulary contains only `FAIL` and
`ELIGIBLE_FOR_HUMAN_REVIEW`. Contract, matrix, hash or owner consistency never
means `VISUALLY_APPROVED`. Contact fields beyond vanilla `onGround` are
deliberately marked unobserved until a single gameplay contact authority
exists.
