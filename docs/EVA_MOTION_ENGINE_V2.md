# EVA Motion Engine V2

## Objective

Minecraft remains the world, networking and collision host. It is not the
visual-animation authority for an Evangelion. The V2 renderer evaluates the
EVA skeleton at render rate from public-domain motion capture, then adds
distance-synchronized gait blending, inertialization, contact-aware leg IK and
weapon constraints. A 20 TPS pose enum is never sent as a sequence of visible
body steps.

## Current vertical slice

- Source: two Quaternius CC0 libraries plus CMU Graphics Lab 120 Hz motion
  capture. The runtime contains 34 clips/45 mapped bones at 30 samples/second;
  walk, jog and sprint are promoted from same-performer CMU captures.
- Offline retarget: `tools/build_eva_motion_database.py`; limb transfer is
  endpoint-based, proportion-aware two-bone IK rather than direct human Euler
  angle copying.
- Runtime database: `assets/projectseele/motion/eva_humanoid_v2.json`.
- Runtime evaluator: `EvaMotionEngineV2`.
- Selection: idle / walk / jog / sprint / crouch / takeoff / airborne.
- Continuous blend: adjacent gaits share normalized phase and blend with
  quaternion slerp.
- Cadence: phase advances from actual render-side distance travelled and each
  clip's fitted post-retarget stride, not entity age or a guessed constant.
- Transition response: half-life inertialization runs at render rate.
- Grounding: contacts are labelled from 3D toe velocity plus height and a
  majority filter. Offline locking shares incompatible two-foot error with the
  pelvis, then resolves both rigid legs with target-space IK. Reviewed planted
  foot speed is 0.02--0.05 m/s for the promoted walk/jog/sprint clips.
- Rollout guard: V2 currently replaces the body only for entities tagged
  `seele_motion_lab`. R28 and server gameplay keep their reviewed fallback
  until the test-lab pass is accepted.

## 3D authority and gates

- `EVA_CMU_MOTION_LAB_ARMATURE.blend` is the editable Blender armature/NLA
  workspace.
- `EVA_CMU_MOTION_LAB_EXACT.blend` is the visual authority: every one of the
  18,132 body vertices is transformed by the same recursively accumulated
  Gecko matrices used at runtime. Sword candidates include the actual
  progressive-knife attachment, not a screenshot or proxy stick figure.
- The exact candidate set currently contains 38 clips: three cyclic gaits,
  one full jump, four punches, eleven sword attacks, fifteen start/stop/veer/
  90-degree trajectory captures, crawl/lay-down/get-up, and the neutral
  reference. The skeleton database passes 0/38; the hash-bound full exact lab
  plus the dedicated low-posture review are the mesh authorities. The promoted runtime core (including the
  three phase-aware jump clips) passes 0/11 skeleton and exact-mesh failures.
- The important coordinate contract is explicit: IK is solved in Gecko's
  reflected runtime space, then converted back into authored Bedrock
  rotations. Solving against raw JSON pivots was the root cause of previously
  mirrored/folded limbs and elevated planted feet.
- Minecraft is an integration target only. Motion is authored, edited and
  rejected in Blender first; no game launch is part of the animation-quality
  loop.

## Architecture target

1. **Motion database** — add eight-direction locomotion, stop/pivot/start clips,
   prone transitions and EVA-scale landings. Raw source assets remain outside
   Git; distributable data must be CC0/compatible or original.
2. **Motion matching** — nearest-neighbour selection over desired trajectory,
   facing, velocity, gait phase and contact state. Preserve semantic tags for
   weapon/stance restrictions.
3. **Inertialization** — retain angular velocity across clip changes and decay
   pose offsets instead of cross-fading through an averaged rubber pose.
4. **Constraint stack** — pelvis height compensation, two-foot ground probes,
   leg IK, hand sockets, two-hand weapon IK, elbow/knee pole vectors, look/aim
   constraints and collision-aware prone placement.
5. **Rendering** — migrate the rigid per-part local mesh to a true skinned mesh
   with bone-index/weight attributes and GPU skinning. The CPU submits one pose
   palette; it does not rebuild or upload the EVA body per frame.
6. **Networking** — server sends gameplay state and sparse corrections only.
   Each client predicts the trajectory and renders a continuous local pose;
   remote EVAs use timestamped transform splines rather than packet-to-packet
   stepping.
7. **Validation** — the disposable `SEELE_EVA_MOTION_LAB` remains the only
   rollout target until foot slide, knee direction, joint separation, contact
   timing, muzzle sockets and first/third-person consistency pass a human
   visual review.

The next implementation step is a compact feature database (root velocity,
facing, future trajectory, hip/feet positions and contact state), periodic
nearest-neighbour selection, and velocity-preserving inertialization based on
the MIT `orangeduck/Motion-Matching` reference. It will first run inside the
Blender/standalone motion lab; the Forge renderer is the final adapter.

That standalone slice now exists: `build_eva_motion_matching_database.py`
produces 1,154 searchable poses from 19 locomotion/trajectory clips with 26
normalised pose, velocity, contact and future-trajectory features.
`query_eva_motion_matching.py` verifies idle/straight/left/right/stop queries;
`simulate_eva_motion_matching.py` drives an eight-second idle -> start -> run ->
90-degree turn -> stop trajectory with semantic range masks and transition
costs. It remains an offline artifact until the 3D transition sequence itself
passes visual direction review.

`compose_eva_motion_matching_demo.py` now materialises that decision stream as
one 240-frame clip, applies velocity-preserving cubic quaternion exponential-
map inertialization, integrates a continuous curved root path, then re-runs
shared-pelvis contact locking. The
resulting `EVA_MOTION_MATCHING_DEMO_EXACT.blend` passes both its database audit
and the 18,132-vertex exact-mesh audit (0/2 failures). It is the first review
surface for the new controller; Minecraft is still not used for authoring.

Combat uses the same gate. `rank_eva_combat_candidates.py` measures actual
left/right hand and progressive-knife-tip paths, peak speed, root travel and
recovery error. `EVA_COMBAT_SHORTLIST_EXACT.blend` contains only the current
top three punches and top three knife actions plus neutral, with the real
knife mesh and a 0/7 hash-bound exact audit. Ranking is a shortlist, not
automatic artistic approval.

`compose_eva_combat_combo.py` chains each three-action shortlist with the same
velocity-preserving inertialization, continuous root placement and offline
two-foot lock. `EVA_COMBAT_COMBO_EXACT.blend` contains a 67-frame punch combo
and a 100-frame real-knife combo; its database and exact-mesh audits are both
green (0/3). These remain Blender review assets rather than live attack input.

The jump path is likewise phase-aware rather than a looping Minecraft jump:
`extract_eva_jump_controller.py` splits the audited 120 Hz capture into a
0.30 s takeoff, 0.60 s ballistic segment (apex at 0.5) and 0.37 s landing.
V2 samples rising and falling halves independently from airborne state, while
still remaining behind the `seele_motion_lab` rollout guard.

Low posture now has a separate four-contact review. CMU crawl, lay-down and
floor-recovery are retargeted against a standing neutral from the same subject.
Velocity/height labels drive feet and supporting hands; shared-root leg IK and
shoulder/elbow IK then lock those contacts. Crawl hand speed fell from roughly
4.5 m/s to 0.00/0.31 m/s, with lay-down and get-up also below 0.35 m/s.
`EVA_POSTURE_REVIEW_EXACT.blend` displays cyan/magenta hand-contact markers and
passes its database and exact-mesh audits (0/4).

Two-hand weapons have their own exact surface gate. The current Gecko rifle,
prone-rifle and Longinus layers are converted by
`build_eva_weapon_pose_database.py` with animated weapon-bone translations.
`audit_eva_weapon_pose_exact.py` measures real hand-mesh to weapon-mesh
distance and muzzle/fork direction, rather than wrist-pivot proxies. The rifle
was already in contact (right/left 0.02/0.05 Blender units); the lance support
hand was 0.19--0.80 away. `solve_eva_weapon_hand_contacts.py` uses the exact
closest surface delta and two-bone shoulder/elbow IK to reduce Longinus to
0.04--0.06 while preserving its 1.00 forward-axis cosine. The solved weapon
lab passes body and weapon audits. `export_eva_weapon_contact_patch.py`
compresses the curves to a maximum 0.35-degree quaternion error and installs
them as hash-chained R07 replacements after R04. EVA-00/01/02 now share the
same semantic animation hash; rebuilding the actual runtime resource and its
weapon/body labs passes 0/8 weapon and 0/9 exact-mesh failures.

## Non-goals

- No official Evangelion animation or footage is extracted.
- Epic Fight and similar mods may inform architecture or be optional runtime
  integrations; their protected assets are not copied.
- High quality does not mean more hand-written Euler keyframes. New work must
  improve motion data, constraints, prediction or the renderer itself.
