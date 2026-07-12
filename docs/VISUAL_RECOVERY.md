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
- First person uses the same evaluated arm bone trees as third person. Its
  camera-space scale and separation are projection settings, not a second
  animation system.
- Every model family requires an explicit bone contract. Runtime bone-name
  guessing is not an accepted production pipeline.

## Visual Lab

Development commands:

```text
/seele visual setup
/seele visual spawn unit01
/seele visual pose idle
/seele visual pose walk_contact
/seele visual pose knife_windup
/seele visual pose knife_contact
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

Each pose produces front, offset-profile, back, clean first-person, and cockpit
first-person images. A run is invalid if a camera misses the Unit, a fixture
occludes it, or the expected arms/weapon are absent.

## Unit-01 acceptance gate

All four groups must pass before expansion resumes:

1. Idle: feet contact the floor; knees, elbows and wrists do not reverse; arms
   rest beside the torso; front/side/back silhouette is readable.
2. Walk contact: one clear load-bearing foot; the other leg advances without
   skating; pelvis and shoulders counter-rotate without mesh inversion.
3. First person: two real Unit-01 arms appear at the lower body sides; they do
   not cross at idle; every attack changes in the same direction and timing as
   its third-person keyframe; no head, torso or pelvis blocks the camera.
4. Progressive knife: windup, contact and recovery read as one attack; the
   blade stays attached to the right forearm/hand socket; the off hand does not
   point behind the back; no limb or weapon intersects the head or chest.

For every item record `PASS`, `FAIL`, or `BLOCKED` with the screenshot filename
and a concrete reason. “Build successful”, “entity summoned”, and “code exists”
are not visual evidence.

## Formal asset gate

A production model must include a `.bbmodel` or Blender source, reference
images that are legal to redistribute, `EXPORT.md`, and `bone-contract.json`.
The current SmOd conversion is explicitly an external local prototype: it may
be evaluated on the owner's machine but cannot be published or promoted to a
formal model without permission and an editable source workflow.
