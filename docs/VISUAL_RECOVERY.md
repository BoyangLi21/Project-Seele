# Visual Foundation Recovery

## Scope freeze

Until Unit-01 passes this document's gate, do not add Angels, EVA variants,
story stages, maps, launch systems, Mass Production EVA content, or Third
Impact effects. Archived prototype work remains reachable from
`archive/agent-sprawl-2026-07-12`; active recovery work lives on
`recovery/visual-foundation`.

## Pose ownership

- GeckoLib animation data is the sole authority for body and joint rotation.
- Java may select animation state and provide continuous inputs such as aim
  pitch, but must not author a complete weapon or stance pose in a renderer.
- First person renders the normal world-space EVA body from a face-level
  camera socket. Only the enclosing head shell is hidden; arms are never
  detached, translated into screen space, or rendered as a second model.
- Every model family requires an explicit bone contract. Runtime bone-name
  guessing is not an accepted production pipeline.

## Visual Lab

Development commands:

```text
/seele visual setup
/seele visual spawn unit01
/seele visual pose idle
/seele visual pose walk_contact
/seele visual pose crouch
/seele visual pose prone
/seele visual pose knife_windup
/seele visual pose knife_contact
/seele visual pose knife_recovery
/seele visual pose lance_windup
/seele visual pose lance_contact
/seele visual pose lance_recovery
/seele visual pose cannon
/seele visual capture all
```

Unattended local capture:

```text
tools\start_test.bat visual unit01
tools\start_test.bat visual unit00
tools\start_test.bat visual unit02
tools\start_test.bat visual mass
tools\start_test.bat visual impact
```

The first three targets run the full thirteen-view pose matrix. `mass` runs
five synchronized states (`idle`, `move`, held `attack`, `revive`, `ritual`),
each from seven fixed exterior views (there is no fabricated first-person
camera for an unpiloted production body). The client closes only after the
last requested state. `impact` captures the complete Tree tableau. The
equivalent Gradle properties are
`-PvisualCapture=true -PvisualCaptureUnit=<target>`.

For a fast subset iteration, also pass
`-PvisualCapturePose=<pose>` or a comma-separated pose list. PNG files are written locally to
`run/screenshots/projectseele_visual/<yyyyMMdd-HHmmss>/`; they are intentionally ignored by Git
because the active Tigerar1 model is a third-party CC BY-SA evaluation asset
and the captures are local review evidence rather than distributable project
art.

After one asset/contract preflight, `tools/start_test.bat visual all` runs the
Unit-01, Unit-00, Unit-02, Mass Production and complete Third-Impact capture
targets in order. Each unattended client closes before the next starts, and
the suite stops at the first failed Gradle/client run. After every client,
`validate_visual_capture_run.py` also requires exactly one new batch, 156 PNGs
for a piloted Unit, 35 for Mass Production or 3 for Impact, the correct filename
prefix, the shutdown marker and no Visual-invalid log signature. A client that
exits with code zero but produced incomplete evidence therefore fails closed.
The desktop shim accepts the same `visual all` arguments.

Each pose produces front, offset-profile, back, front and both-profile close-ups,
clean/cockpit first-person,
plus yaw-left, yaw-right, pitch-up, and pitch-down first-person images. The
orientation matrix must preserve the camera-to-body connection: turning the
Unit must not orbit, mirror, or independently rotate either arm. A run is
invalid if a camera misses the Unit, a fixture occludes it, or an expected
weapon is absent.

Every filename now includes the complete render source observed by the client,
for example `eva_unit01-triangle-mesh-4226-p17-<crc>-g<hash>-a<hash>-t<hash>-s<hash>`.
The suffixes identify geometry, animation, texture and source pack; all four
resources must exist and come from that same pack. Part count plus content CRC
distinguishes the old 15-part cache from the reviewed 17-part mesh; cannon poses
append their own `positron-triangle-mesh-14391-p1-<crc>` tag. Missing, mixed or
wrong-contract resources invalidate the batch. All poses from one client run share the same
timestamped batch directory. Evidence must cite both the batch directory and
the tagged filename; this prevents screenshots from separate models or runs
from being mistaken for one sequence. If the source tag changes between poses,
the client logs `VISUAL BATCH INVALID` and the entire batch is rejected.

An unattended run closes the development client after the final requested
pose, so a successful screenshot batch cannot leave Gradle hanging behind an
open game window.

The desktop launcher regenerates the ignored local pack and then runs
`python tools/validate_local_eva_pack.py` before Forge starts. The preflight
requires the reviewed Unit-01, Unit-00, Unit-02, Mass Production and positron
cannon meshes, finite vertex data, parseable Gecko geometry/animations and
non-empty textures. It also requires PNG/Geo atlas sizes to match, preserves
the complete Mass Production wing half, rejects every old body/head/cannon
fallback cube and checks Unit-00's shield contract. Each Tiger EVA body has exactly the
same 17 semantic mesh parts, including `foot_l` under `shin_l` and `foot_r`
under `shin_r`; attachment-only Gecko bones are additional to that count. A
failed preflight stops the launcher. Visual Lab and the normal desktop test
also enable runtime strict mode: a stale/mixed ResourceManager pack is logged
with full SHA-256 evidence and the renderer refuses the obsolete fallback
instead of revealing an old cube body or extra horn.

## Unit-01 acceptance gate

All four groups must pass before expansion resumes:

1. Idle: feet contact the floor; knees, elbows and wrists do not reverse; arms
   rest beside the torso; front/side/back silhouette is readable.
2. Walk contact: one clear load-bearing foot; the other leg advances without
   skating; pelvis and shoulders counter-rotate without mesh inversion.
3. First person: straight-ahead idle does not force floating fists into view;
   looking down reveals a continuous shoulder-arm-hand-body chain at both body
   sides. Every attack changes in the same direction and timing as its
   third-person keyframe; no head shell blocks the camera.
4. Progressive knife: windup, contact and recovery read as one attack; the
   blade stays attached to the right forearm/hand socket; the off hand does not
   point behind the back; no limb or weapon intersects the head or chest.

For every item record `PASS`, `FAIL`, or `BLOCKED` with the screenshot filename
and a concrete reason. “Build successful”, “entity summoned”, and “code exists”
are not visual evidence.

## 2026-07-12 Tigerar1 replacement checkpoint

The PNG files directly under `projectseele_visual/` predate batch directories
and source tags. They mix several SmOd and Tigerar1 runs and are retained only
as legacy diagnostic evidence. In particular, older-looking weapon/action
images do not prove that the current runtime fell back to cubes; only a tagged
`cube-fallback` filename can establish that. The next full-pose
`triangle-mesh-4226` batch is required for formal gate decisions. The local
mesh is CC BY-SA third-party art; its exact release attribution and share-alike
packaging still require a formal asset review.

The table below records useful observations from that legacy set, not a closed
acceptance gate. `FAIL` findings remain actionable; visual `PASS` findings must
be repeated in the next tagged batch before expansion can resume.

| Gate | Status | Evidence and reason |
|---|---|---|
| Mesh load and orientation | PASS | The historical pre-ankle-split `latest.log` records 15 mesh parts / 4,226 triangles. `unit01_front_close_idle.png` shows the face and chest while `unit01_back_idle.png` shows the authored back, so the previous front/back reversal is fixed. The current 17-part contract is covered separately by offline validation and still needs a new tagged game capture. |
| Idle silhouette | PASS | `unit01_front_close_idle.png`, `unit01_side_close_idle.png`, and `unit01_side_opposite_close_idle.png`: both feet contact the floor, elbows and knees face plausible directions, and both arms rest beside the torso. |
| Walk contact geometry | FAIL | `unit01_front_close_walk_contact.png` and `unit01_side_close_walk_contact.png` separate the legs, but the arms and shoulders remain almost identical to idle and the static frame does not clearly communicate a load-bearing step or body counter-rotation. |
| Walk motion/skating | BLOCKED | Static PNGs cannot prove foot locking or weight transfer through the loop; requires a short fixed side-view clip after the contact pose is improved. |
| First-person idle connection | FAIL | `unit01_first_person_clean_idle.png` is correctly unobstructed, but `unit01_first_person_pitch_down_idle.png` shows chest/shoulder armour without either forearm or hand. It does not yet demonstrate the required continuous shoulder-arm-hand chain at both body sides. |
| First-person crouch/prone connection | FAIL | `unit01_first_person_pitch_down_crouch.png` and `unit01_first_person_pitch_down_prone.png` show both hands clustered near the screen centre. They are shared world-body arms, but they do not read as human first-person arms at the left and right body sides. |
| First-person orientation stability | BLOCKED | `unit01_first_person_yaw_left_idle.png` and `unit01_first_person_yaw_right_idle.png` contain no arms, so these captures verify camera direction only; they cannot prove that either arm stays attached and does not mirror/orbit. |
| Crouch geometry | FAIL | `unit01_front_close_crouch.png` initially reads as lowered, but `unit01_side_opposite_close_crouch.png` exposes crossed, forward-folded legs and no convincing planted foot / single-knee support. It is not yet a valid kneel. |
| Prone geometry | PASS | `unit01_front_close_prone.png` and `unit01_side_close_prone.png` show a recognisable hands-and-knees crawl pose rather than a flat swimming pose. Crawl gait and hand/foot locking remain untested. |
| Knife contact geometry | FAIL | `unit01_front_close_knife_contact.png` and `unit01_side_close_knife_contact.png` show the current Tigerar1 contact frame, but the feet stay in the idle base, the torso leans sideways, and the off hand opens away from the weapon. The placeholder rectangular blade also does not read as a finished progressive knife. |
| Knife sequence and timing | BLOCKED | Only the replacement model's contact pose has a current capture. Windup/recovery must be recaptured with Tigerar1 before continuity, socket stability, timing, or impact weight can be judged. |
| Cannon connection | BLOCKED | Existing `cannon` captures predate the Tigerar1 replacement and cannot validate its hand sockets, two-hand support pose, or prone brace. |
| Longinus thrust | BLOCKED | Existing `lance_*` captures predate the Tigerar1 replacement. The full three-pose sequence must be recaptured; EUD-derived local geometry also remains outside the publishable asset set. |
| Unit-01 authored face source | PASS | The known Tigerar1 idle capture `unit01_face_close_idle.png` preserves the source head, horn, jaw, chest, and pylon proportions without a procedural mask. This passes source selection only; the in-game face still needs a tagged batch capture. |
| Rigid-joint production gate | FAIL | The current OBJ conversion is partitioned rigidly into 17 body mesh parts, including independent feet. Static neutral poses do not expose every seam; elbows, wrists, ankles and waist still require stress-pose review plus joint liners or weighted skinning before this can be called production-ready. |

The Visual Lab now uses the fixed isolated origin `(4096, 64, 4096)`, captures
both side close-ups, writes an independently tagged directory for every client
run, and automatically closes the unattended client after the last requested
pose. Direct-root legacy screenshots and earlier frames polluted by clouds or
old overhead platforms are not accepted as final gate evidence.

## Tagged runtime evidence through 2026-07-13

These decisions supersede the untagged legacy observations above. A later
code change without a new PNG is recorded as `BLOCKED`, not silently promoted
to a visual pass.

| Gate | Status | Tagged evidence and decision |
|---|---|---|
| Model continuity across actions | BLOCKED (legacy tag insufficient) | Batch `20260712-235539` kept the old `triangle-mesh-4226` filename, but that tag could not distinguish the former 15-part cache from the current 17-part mesh and did not identify the cannon. Tags now include triangle count, part count and CRC; cannon poses also carry a separate positron tag. A new batch is required. |
| Unit-01 source face and idle body | PASS | `20260713-002420/unit01_triangle-mesh-4226_face_close_idle.png` and `front_close_idle.png` show the authored Tiger head/face and complete body with no procedural mask or second horn shell. |
| Walk contact | PASS (static) | `20260713-001545/unit01_triangle-mesh-4226_side_close_walk_contact.png` shows a separated load-bearing/advancing leg pair. Foot locking and skating through the complete loop still require video. |
| First-person body connection | FAIL (old runtime), PASS (offline projection), BLOCKED (new runtime) | The rejected `20260713-002420` batch has an empty forward prone view. The adopted all-fours pose, `10.2` forward socket, pylon cover and prone-only exact torso-mesh filter now retain both real upper-arm/forearm/hand chains on opposite sides without an independent animation. A new tagged game batch must confirm near clipping. |
| Crouch / one-knee support | PASS (offline), FAIL (last runtime), BLOCKED (new runtime) | `20260713-001545/...front_close_crouch.png` remains the rejected old pose. The replacement `external-assets/work/crouch-foot170-review/...sheet.png` reads as right-foot support plus grounded left knee and rear toe: right foot `Y=+0.2245`, left shin/knee armour `+0.9923`, rear toe `+0.6578`. Its 65-sample crouch-walk loop remains above ground at `+0.2245…+0.6867`. A new tagged game batch is still required. |
| Prone / crawl base | PASS (offline), BLOCKED (runtime) | The canonical four-support pose has minimum `Y=+0.714px`; sampled crawl contacts remain above the bind ground (`+0.336px` minimum in the reviewed Unit-01 cycle) while arms and opposite legs alternate. Unit-00/02 use the same canonical JSON. Its game render and collision feel still need a new batch. |
| Longinus two-hand thrust | PASS (offline current art), BLOCKED (runtime) | `external-assets/work/eva-offline-validation/20260713-074159/` renders the final EUD 40-cube spear together with all three Tiger bodies and the corrected shared entry-plug offset. Ready/windup/contact/recovery keep the hand pivots `16.74..17.91px` apart and the complete weapon/body bounds stay above ground. A tagged Minecraft sequence is still required. |
| Positron mesh axis/socket | PASS | `20260713-010636/...side_close_cannon.png` shows the 14,391-triangle cannon horizontal at the right-hand socket; it no longer stands vertically, floats above the head or wraps around a leg. |
| Positron two-hand support | PASS (offline third-person), BLOCKED (runtime/first-person) | The current matrix renders the 14,391-triangle cannon through the same skeleton: standing hands are `11.04px` apart and prone hands `13.15px` apart; both third-person poses clear the floor. The forward first-person aim still hides one arm behind the receiver, so it is deliberately not promoted to runtime acceptance. |
| Unit-00 body and shield | PASS (offline), BLOCKED (runtime) | The complete canonical action catalogue prevents old-axis action fallback. The new full-height shield is rendered from its real Gecko cubes and a dedicated two-arm brace overlays the one-knee pose; `20260713-053906/unit00/third_person/shield_brace/` clears the ground with hands `16.45px` apart. |
| Unit-02 body | PASS (offline), BLOCKED (runtime) | The converter copies the complete canonical catalogue, strips obsolete horn cubes and passes the same walk/crouch/prone/cannon/Longinus ground matrix as Unit-01. The old game screenshot predates these fixes. |
| Mass Production five-state matrix/ritual | PASS (offline), FAIL (old tableau), BLOCKED (runtime) | `20260713-074159` uses the actual `visual_attack` state, renders the replica lance for idle/move/attack, hides it for revive/ritual as the runtime does, and catches attachment penetration. The first pass exposed `-26px` idle/move spear penetration; the adopted ready pose now records `0px` idle and `-0.384px` moving contact. All five state sheets remain distinct. The older runtime tableau is still rejected pending a new tagged game capture. |

The rejected `012435` tableau was followed by narrower paths, an eight-block
tree back-plane offset, larger pure-red labels without backdrop or shadow, full-bright ritual
bodies and a 240-block Visual Lab cleanup volume. Those changes are deliberately
marked pending until a new `impact_front.png` exists.

## Offline pose lab

`tools/render_unit01_rig_preview.py` loads the same ignored triangle mesh,
texture, Gecko skeleton and animation JSON used at runtime. It also converts
selected Gecko cube attachments (`--geo-cube-bone`) so shields, Longinus,
replica lances and insertion hardware cannot pass while invisible or below
ground. Rotated Blockbench cubes are included, so the faceted entry plug and
its end caps are no longer silently omitted. It samples a real
animation time through the parent hierarchy, writes front/side/back contact
sheets, overlays joint links and emits per-bone ground/contact metrics. Preview
overrides make candidate angles reviewable without changing the animation file.
`--camera-forward`, `--camera-eye-height` and `--camera-right` provide a
three-axis first-person socket scan; a candidate is adopted only after reading
the PNG, not merely because a polygon counter says both arms exist.

The same tool now has a perspective first-person gate. For example, run these
three commands against the active local pack (replace `<base>` with
`run/resourcepacks/eva_real_model/assets/projectseele`):

```text
python tools/render_unit01_rig_preview.py <base>/mesh/eva_unit01.mesh.json <base>/textures/entity/eva_unit01.png external-assets/work/unit01-first-person-preview --geo <base>/geo/eva_unit01.geo.json --animation-json <base>/animations/eva_unit01.animation.json --animation idle --first-person-stance standing
python tools/render_unit01_rig_preview.py <base>/mesh/eva_unit01.mesh.json <base>/textures/entity/eva_unit01.png external-assets/work/unit01-first-person-preview --geo <base>/geo/eva_unit01.geo.json --animation-json <base>/animations/eva_unit01.animation.json --animation crouch --first-person-stance crouch
python tools/render_unit01_rig_preview.py <base>/mesh/eva_unit01.mesh.json <base>/textures/entity/eva_unit01.png external-assets/work/unit01-first-person-preview --geo <base>/geo/eva_unit01.geo.json --animation-json <base>/animations/eva_unit01.animation.json --animation prone --first-person-stance prone
```

This is not an independently animated viewmodel. It applies the renderer's
`2.5` scale, Unit-01's actual standing/crouch/prone eye heights
(`24.8/15.75/10.8` blocks), actual forward sockets (`5.0/4.0/10.2` blocks), the
Visual Lab's `12/70` degree forward/pitch-down samples and the same shared bone
matrices as third person. The enclosing head and two leaf pylons are hidden in
all pilot views. In prone only, the exact upper/lower torso mesh parts are
omitted without hiding their bones or descendants; this clears the centre while
both upper-arm/forearm/hand chains remain driven by the real world skeleton at
opposite body sides. Each run writes two 1280x720 PNGs, a contact sheet and
machine-readable arm bounds. This makes camera/pose failures reviewable before
a Minecraft launch; it does not replace the tagged in-game capture gate.

Camera-only candidates can be tested without touching Java by adding
`--camera-eye-height <blocks>` and `--camera-forward <blocks>`. The override is
recorded in both the PNG filename and metrics JSON, so it cannot be confused
with the runtime socket. A bounded search over the adopted crouch/prone poses
produced the following forward-view results (triangle counts are
upper-arm/forearm/hand for one side; the opposite side is symmetric):

| Pose / socket (eye, forward) | Visible arm triangles | Torso triangles in viewport | Offline reading |
|---|---:|---:|---|
| Crouch former runtime `17.5, 5.5` | `0 / 11 / 135` | `0` | FAIL: only fingertips and a forearm sliver touch the bottom edge. |
| Crouch current runtime/default `15.75, 4.0` | `3 / 88 / 230` | `0` | BEST: both forearm/hand chains run continuously from the body-side edge into the lower half; the camera remains about 1.2 blocks in front of the posed torso AABB. |
| Crouch alternative `15.75, 4.5` | `0 / 76 / 230` | `0` | Clear lower-corner hands, but the upper-arm link is entirely outside the viewport. |
| Prone former runtime `10.8, 9.0` | `0 / 0 / 0` | `26` | FAIL: the old flat pose left both arm chains behind the camera. |
| Prone diagnostic `6.0, 3.0` | `85 / 124 / 216` | `0` | Geometry is continuous and unobstructed, but the camera sits below the torso; arms descend from the top of frame. This is not a believable pilot/head socket. |
| Prone clearance test `10.8, 12.0` | `0 / 0 / 0` | `0` | Moving ahead of the torso clears it, but also leaves the entire arm chain behind the camera. |

That search proved the old prone failure was a pose constraint, not something
another random camera offset could solve. The four-support candidate below is
now the canonical `prone` pose for Unit-01/00/02, and `crawl` interpolates a
diagonal arm/opposite-leg gait around it:

```text
root position       = [0, -46, 20]
torso_lower rotation= [110, 0, 0]
torso_upper rotation= [-50, 0, 0]
head rotation       = [-40, 0, 0]
arm_l / arm_r       = [-112, 0, -12] / [-112, 0, 12]
forearm_l / r       = [0, 0, 0] / [0, 0, 0]
leg_l / leg_r       = [-89, 0, -4] / [-75, 0, 4]
shin_l / shin_r     = unchanged [126, 0, 0] / [95, 0, 0]
```

The leg changes compensate for the lower-torso redistribution and preserve the
rear contacts. The extra root `Z=20` pixels (3.125 blocks) brings the grounded
hands ahead of the head; the prone collision envelope remains a separate
runtime gate.

Offline measurements: overall minimum `Y=0.714` pixels; both hand shells remain
on the ground; hand pivot `Z=125.5` is about `45.9` pixels ahead of the head;
all upper-arm/forearm/hand parts intersect the forward viewport (`229/124/230`
triangles per side); the left chain occupies `X=-1.753..-0.406`, with the right
side symmetric. The side silhouette is four-point support rather than the old
flat swimming shape. The forward frame still includes the upper body along the
bottom centre, but the camera is above rather than inside the torso and both
continuous arm chains occupy the lower sides. Review sheets are:

- `external-assets/work/prone-dog-crawl-candidate-d/unit01_rig_prone_override_0.000_sheet.png`
- `external-assets/work/prone-dog-crawl-candidate-d/first-person/unit01_rig_prone_override_first_person_prone_0.000_sheet.png`

`--hide-bone <exact-part>` exposed the distinction between hiding a bone
subtree and omitting only one mesh shell. The renderer now hides the two pylon
leaf bones as subtrees, then filters only `torso_lower` / `torso_upper` mesh
parts in prone; their bones and both arm descendants remain active. At the
adopted `10.8,10.2` socket the forward projection contains all
upper-arm/forearm/hand regions on both sides. Runtime screenshots are still
required to judge near clipping and perceived connection.

The lab first exposed why the pre-split crouch could not be repaired by another
root offset: its right shin penetrated the bind ground by `19.1841` pixels, but
lifting the root by that amount raised the intended kneeling joint to about
`29.9` pixels. At that checkpoint every ankle correction rotated the entire
welded shin/foot shell.

The converter now closes that topology blocker for Unit-01, Unit-00 and
Unit-02. It splits `foot_l` and `foot_r` from the lower-leg source geometry,
parents them to `shin_l` and `shin_r`, and emits exactly 17 standard body mesh
parts. Current ignored pack output remains 4,226 / 3,692 / 3,952 triangles
respectively, so the split adds or drops no triangles. The offline validator
now enforces the exact part count, both foot parts and both parent
relationships.

The replacement animation now passes the offline silhouette and ground gate:
the right foot is planted at `Y=+0.2245`, the left knee/shin armour contacts at
`+0.9923`, and the rear toe remains at `+0.6578`. The 65-point crouch-walk
cycle stays above ground throughout (`+0.2245…+0.6867`) while shifting weight
over the supporting side. This is still not a runtime visual pass; the final
sheet is under `external-assets/work/crouch-foot170-review/`, and a new tagged
Visual Lab batch must confirm scale, interpolation and first-person framing.

The adopted four-point baseline is root position `[0,-46,20]`, lower/upper
torso `110/-50`, head `-40`, arms `-112` with mirrored 12-degree spread,
straight forearms, and asymmetric folded legs. Its static minimum is
`+0.714px`; the reviewed Unit-01 crawl keyframes remain at or above
`+0.336px`. These are offline geometric facts, not a substitute for the next
in-game first-person batch.

`tools\start_test.bat offline` renders this contract for Unit-01, Unit-00,
Unit-02 and all five Mass Production states into one timestamped directory and
writes a SHA-256 manifest. It intentionally exits before Forge; the tagged
Minecraft matrix remains the final runtime gate.

## Formal asset gate

A production model must include a `.bbmodel` or Blender source, reference
images that are legal to redistribute, `EXPORT.md`, and `bone-contract.json`.
The current Tigerar1 OBJ conversion is explicitly an external local prototype:
it may be evaluated on the owner's machine, but it cannot pass the formal gate
without a rigged editable source workflow and a verified CC BY-SA attribution /
share-alike release plan. SmOd remains a separate local fallback and is not
accepted as production art.
