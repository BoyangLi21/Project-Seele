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
gradlew runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true
```

For a fast subset iteration, also pass
`-PvisualCapturePose=<pose>` or a comma-separated pose list. PNG files are written locally to
`run/screenshots/projectseele_visual/`; they are intentionally ignored by Git
because the active SmOd model is a local, unlicensed evaluation asset.

Each pose produces front, offset-profile, back, front and both-profile close-ups,
clean/cockpit first-person,
plus yaw-left, yaw-right, pitch-up, and pitch-down first-person images. The
orientation matrix must preserve the camera-to-body connection: turning the
Unit must not orbit, mirror, or independently rotate either arm. A run is
invalid if a camera misses the Unit, a fixture occludes it, or an expected
weapon is absent.

An unattended run closes the development client after the final requested
pose, so a successful screenshot batch cannot leave Gradle hanging behind an
open game window.

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

## 2026-07-12 checkpoint

Local SmOd evaluation evidence (not redistributable):

| Gate | Status | Evidence and reason |
|---|---|---|
| Idle silhouette | PASS | `unit01_front_close_idle.png` and `unit01_side_close_idle.png`: feet are planted and both arms hang beside the torso without Java pose overrides. |
| Walk contact geometry | PASS | `unit01_side_close_walk_contact.png` and `unit01_side_opposite_close_walk_contact.png`: the legs separate into a readable stride and both knees bend on the forward/back axis. |
| Walk motion/skating | BLOCKED | Static PNGs cannot prove foot locking through the full loop; requires a short user-recorded side-view clip. |
| First-person body connection | PASS | `unit01_first_person_clean_idle.png` has no forced floating fists; `unit01_first_person_pitch_down_idle.png` shows the uninterrupted chest, shoulders and both arm roots at the body sides. |
| Orientation stability | PASS | `unit01_first_person_yaw_left_idle.png` and `unit01_first_person_yaw_right_idle.png`: neither arm mirrors or orbits independently from the body. |
| Knife key poses | PASS | `unit01_front_close_knife_windup.png`, `unit01_side_close_knife_contact.png`, and `unit01_side_close_knife_recovery.png` form distinct raise, forward contact and lowered recovery silhouettes; the blade remains parented to `weapon_socket_r`. |
| Knife timing/weight | BLOCKED | Still images establish joint continuity but not perceived timing or impact weight; requires the same user clip. |
| Crouch/prone camera | PASS | `unit01_first_person_clean_crouch.png` and `unit01_first_person_clean_prone.png` clear the chest shell; their `pitch_down` frames show the real shared arms/body instead of a detached viewmodel. |
| Cannon connection | PASS | `unit01_side_close_cannon.png`, `unit01_side_opposite_close_cannon.png`, and `unit01_first_person_pitch_down_cannon.png`: the cannon begins at the right-hand socket and the left arm reaches the support area without tilting the torso sideways. |
| Prone cannon brace | PENDING | Dedicated `prone_cannon` capture now verifies the low two-handed firing state separately from the weight-bearing crawl arms. |
| Longinus thrust | PASS | `unit01_front_close_lance_windup.png`, `unit01_side_close_lance_contact.png`, and `unit01_front_close_lance_recovery.png`: both arms converge on one shaft line through pull-back, thrust, and lowered recovery. Local geometry is EUD-derived and remains non-publishable. |
| Unit-01 face | SOURCE RESTORED | The rejected procedural mask has been removed. Local evaluation uses SmOd's original head and authored proportions unchanged; a production replacement still needs an editable, approved source model. |

The Visual Lab now uses the fixed isolated origin `(4096, 64, 4096)`, captures
both side close-ups, and automatically closes the unattended client after the
last requested pose. Earlier screenshots polluted by clouds or old overhead
platforms are not accepted as evidence.

## Formal asset gate

A production model must include a `.bbmodel` or Blender source, reference
images that are legal to redistribute, `EXPORT.md`, and `bone-contract.json`.
The current SmOd conversion is explicitly an external local prototype: it may
be evaluated on the owner's machine but cannot be published or promoted to a
formal model without permission and an editable source workflow.
