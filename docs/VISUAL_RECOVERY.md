# Visual Foundation Recovery

## Recovery scope

Visual work is judged by reproducible images, not by compilation, entity
registration, or the presence of animation JSON.  Until the shared Unit-01
body passes idle, crouch, prone, knife, and positron-aim review, newly added
content remains prototype work.

The active recovery branch is `recovery/visual-foundation`.  The pre-recovery
snapshot remains reachable from `archive/agent-sprawl-2026-07-12`.

## One-body camera contract

First and third person now have one source of truth:

- one world `EvaUnit01Entity` body;
- one evaluated Gecko skeleton and animation state;
- one set of weapon sockets;
- one EVA-eye camera looking along the model's authored forward axis, local
  `-Z` (the horn direction);
- camera-cover `head` / `horn` / `neck` roots may be hidden in first person.
  Their descendants may hide with them;
- crouch and prone may additionally clip the exact `torso_lower` and
  `torso_upper` mesh parts that enclose the camera. This is an exact mesh-part
  near-camera filter: it does not hide either torso bone, does not hide their
  children, and therefore leaves pylons, shoulders, arms, hands, pelvis, and
  legs on the same evaluated world skeleton;
- `RenderHandEvent` may cancel the vanilla player hand while mounted. It must
  not render a second EVA arm pass.

The former screen-space `RenderHand` EVA-arm viewmodel is rejected. Its shared
camera-space root, negative Y scale, arm-only subtree render, and detached-arm
area thresholds could produce two visible shapes while the real world arms
were behind the body. That path is not acceptance evidence and has been
removed from the offline matrix.

Java may select an animation and provide continuous state such as look pitch.
It must not author a second full weapon stance that competes with Gecko. Idle,
knife, cannon, crouch, and prone joint poses belong to the canonical animation
data and must be shared by both cameras.

## TV cockpit interpretation

The TV-style Entry Plug is treated as an immersive cockpit layer rather than
as a replacement pair of EVA arms. The pilot sees an EVA-eye panoramic world
image with original Project SEELE HUD, sync, LCL, warning, motion, and sound
cues. Physical control grips may appear as a separate cockpit overlay, but
they must be visually distinct from the EVA's real hands and cannot be used to
claim first/third-person pose parity. See `docs/TV_COCKPIT_REFERENCE.md`.

No official animation frame, texture, UI plate, or audio is shipped. External
references are design references only.

## Runtime Visual Lab

Development commands:

```text
/seele visual setup
/seele visual spawn unit01
/seele visual pose idle
/seele visual pose crouch
/seele visual pose prone
/seele visual pose knife_windup
/seele visual pose knife_contact
/seele visual pose knife_recovery
/seele visual pose cannon
/seele visual camera front
/seele visual camera side
/seele visual camera back
/seele visual capture all
```

Unattended capture targets:

```text
tools\start_test.bat visual unit01
tools\start_test.bat visual unit00
tools\start_test.bat visual unit02
tools\start_test.bat visual mass
tools\start_test.bat visual impact
tools\start_test.bat visual all
```

PNG batches are written under
`run/screenshots/projectseele_visual/<yyyyMMdd-HHmmss>/`. They remain local
because the active high-detail evaluation meshes are third-party assets.
Every accepted runtime statement must identify the batch directory and exact
tagged filename. A new code change without a new image is `BLOCKED`, never an
implicit visual pass.

## Offline recovery suite

Run:

```text
tools\start_test.bat offline
```

After regenerating and structurally validating the private local resource
pack, offline mode runs all of these gates even if an earlier one fails:

1. `validate_third_person_pose.py` — real Unit-00/01/02 meshes; authored local
   `-Z`; idle hands, two-hand cannon, recoil, and knife guard/contact/recovery.
2. `validate_crucified_pose.py` — Unit-01 cross silhouette, horizontal arms,
   joined feet, and authored keyframe sampling.
3. `render_launch_silo_preview.py --strict` — fixed bed, moving carrier,
   insertion and launch clearances.
4. `render_tree_of_life_preview.py --layout current --strict` — current real
   EVA envelopes, label collisions, clipping, pure-red composition, and
   front-facing tableau geometry.
5. `render_eva_validation_matrix.py` — Unit-00/01/02 exterior and unified
   pilot-eye standing, crouch, prone, knife, aim, and prone-aim evidence plus
   the five Mass Production states.

The matrix uses `render_unified_eva_view_audit.py`, which fails if the signed
stance socket, allowed hidden roots, exact low-stance camera-clip parts, or
unified-camera constants drift. The
base perspective renderer places the camera at the stance-specific head socket
and always looks along local `-Z`; it no longer rewards a backwards arm pose.
Each Unit/pose row must produce its complete PNG
set and metrics JSON. At least one of the `forward` and `pitch_down` views must
show both attached arm regions on opposite sides. Knife and cannon rows must
also contain their real attachment geometry. Missing files, missing bones,
wrong camera direction, hidden arm/pylon roots, any unapproved exact mesh
filter, ground penetration, or a blank arm/weapon result fail closed.

Outputs are timestamped under:

```text
external-assets/work/eva-offline-validation/<yyyyMMdd-HHmmss>/
```

The manifest records exact SHA-256 evidence and the architecture contract.
An offline `PASS` means the static inputs and declared geometric checks passed;
it does not mean Minecraft rendered the same pixels, animation timing feels
natural, the camera does not clip during motion, or a human accepted the pose.

Normal `tools\start_test.bat` does not run these static image gates. It retains
resource-pack and structural preflight, then starts Forge. This keeps an
intentional offline visual failure from blocking ordinary manual testing.

## Human acceptance gate

For Unit-01, then Unit-00 and Unit-02, review the same animation in exterior
front/side/back and pilot-eye views:

1. Idle: the side view proves hands are beside or slightly in front of the
   torso, never behind the back; feet contact the floor; elbows and knees do
   not reverse.
2. Crouch: one planted foot and one grounded knee are readable; the camera
   still sees the same attached arms when looking down.
3. Prone: hands and knees form an all-fours crawl base, not a swimming pose;
   arms are not folded behind the spine; the pilot camera is not blank.
4. Knife: windup, contact, and recovery form one forward attack; the blade
   stays on the right hand; the guard hand does not point behind the body.
5. Positron cannon: both hands support the weapon; the left hand does not drift
   upper-left; the barrel points forward at chest/shoulder height. Prone aim
   must have a distinct brace rather than reusing a standing silhouette.
6. Camera parity: a turn or attack changes the one world skeleton once. The
   pilot-eye view must not mirror, independently rotate, translate, or animate
   a second pair of arms.

Record `PASS`, `FAIL`, or `BLOCKED` for every row with a concrete visual reason.
`build successful`, `no exception`, and `entity summoned` are not visual
evidence.

## Current evidence status (2026-07-13)

The architecture changed after the last Minecraft batch. Therefore there is
currently no runtime `PASS` for unified first-person arms, crouch/prone
visibility, knife parity, or cannon parity. These rows remain `BLOCKED` until a
new tagged Visual Lab batch is captured and reviewed by the user.

The older `external-assets/work/eva-offline-validation/20260713-091205/` batch
belongs to the rejected arm-only `RenderHand` experiment. Its numeric arm-area,
centre-overlap, and negative-scale results are retained only as diagnostic
history and must not be cited as evidence for the current architecture.

The crucified-pose, launch-silo, and Tree-of-Life reports are static offline
contracts. Their latest results may be reported as offline geometry/composition
results only; the complete in-game Third Impact tableau and launch sequence
remain separately `BLOCKED` pending new runtime images or video.

The latest unified matrix is
`external-assets/work/eva-offline-validation/20260713-112438/`. Its static
standing, crouch, prone, knife, standing-aim, and prone-aim rows pass for
Unit-00, Unit-01, and Unit-02. The repaired prone-aim layer now keeps both arm
regions readable around the same attached cannon instead of dropping the left
support arm. This is an offline geometry/visibility result only: every row
still requires a new tagged Minecraft batch for runtime and human review.
