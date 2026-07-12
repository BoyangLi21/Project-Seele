# Third Impact visual contract

This sequence is an explicitly staged visual prototype. Code presence is not
acceptance: every model or renderer change must still pass the views below.

## Reference boundary

- The film tableau uses nine Mass-Production Evangelions as the outer
  Sephirot, with Unit-01 at Tiferet, and presents the Tree in an inverted
  orientation.
- The reconstructed glyph uses the factual Golden Dawn graph: ten Sephirot,
  22 paths and the Hebrew letters Aleph through Tav. It does not ship or trace
  an Evangelion frame, official artwork, or a third-party diagram.
- Name and graph cross-checks:
  - https://en.wikipedia.org/wiki/The_End_of_Evangelion#Religion,_philosophy_and_psychology
  - https://evangelion.fandom.com/wiki/Tree_of_Life
  - https://commons.wikimedia.org/wiki/File:Tree_of_Life_(Sephiroth).svg

## Current composition

- Inverted layout: Keter is the low point and Malkuth the high point.
- Node field: 68 blocks wide by 140.8 blocks high (before rings and heading),
  reduced from 84 by 179.2.
- Pure-red double paths and concentric Sephira rings.
- Ten numbered Latin transliterations, ten Hebrew names, 22 Hebrew path
  letters, and a compact `SYSTEMA SEPHIROTHICVM X DIVINORVM NOMINVM / OTZ
  CHIIM` heading.
- All nine production units and all nearby EVA variants receive one complete
  front-facing yaw (body, head, previous-frame rotations and pitch).
- Every deployed production unit receives the synchronized `VISUAL_RITUAL`
  state. Ritual rendering no longer infers intent from `NoAI + NoGravity`, so
  an inert Visual-Lab subject can still display idle, move, attack or revive.
- Unit-01's crucified flag has priority over Visual Lab, weapon, aim and
  movement animations. Entering the tableau clears held weapons and forces the
  dedicated arms-out animation.

## Manual acceptance pass

1. Run `/seele visual setup`, followed by `/seele visual impact`. The second
   command immediately stages the tree, parks all nine vessels and moves the
   player to the deterministic full-front camera.
2. For the normal story timeline, instead give the player
   `/give @s projectseele:seele_scenario`, aim at Unit-01 and use it once. Wait
   15 seconds for the tree phase.
3. Capture the complete front, a 30-degree side view, and a close Tiferet view.
4. Reject the pass if any of these occurs:
   - Unit-01's arms are not horizontally outstretched;
   - an old aim/weapon animation replaces either arm;
   - a production EVA shows its back while another shows its front;
   - Keter appears at the top rather than the inverted low point;
   - labels are mirrored, boxes, hidden by depth, or unreadable at the normal
     scenario viewing distance;
   - the tree is clipped out of a normal-FOV front capture.
5. Use the scenario item on Unit-01 a second time to verify clean release and
   slow-falling recovery.

## Current automated evidence

Run the dedicated batch with:

```text
gradlew runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=impact
```

The desktop equivalent is `tools/start_test.bat visual impact`. The client
checks nine living vessels, all nine front-facing yaws, nine synchronized
ritual states, a crucified Unit-01, and both local triangle meshes before
writing three separately settled views:
`impact_front.png`, `impact_oblique.png`, and `impact_tiferet_close.png`. The
first proves the full glyph fits; the oblique view exposes depth/mirroring;
the close view makes the Unit-01 cross silhouette and label backing reviewable.

Both the normal story timeline and `/seele visual impact` also emit a
server-side `Third Impact tableau audit` line. Its structural gate requires
exactly nine distinct occupied outer nodes, nine front-facing vessels and,
when present, a crucified front-facing Unit-01 centred at Tiferet. A
`valid=true` audit proves state and placement only; it is not visual approval.

The active 4,226-triangle Unit-01 mesh also has a direct offline pose sheet at
`external-assets/work/unit01-crucified-final/`: front and back show the full
horizontal cross silhouette, while the side view confirms both arms remain in
one plane rather than folding behind the torso. This passes the animation pose
offline; the complete in-game tableau remains separately blocked below.

The latest real image is
`run/screenshots/projectseele_visual/20260713-012435/impact_front.png` and is a
visual `FAIL`: the complete red graph renders and occupies about 72% of the
frame, but its lines obscure the EVA silhouettes and the labels are not
readable at the captured resolution. The subsequent narrower/back-shifted
graph, larger backed labels and full-bright bodies have compiled but remain
`BLOCKED` pending a new screenshot. Log-only facts (`massCount=9`,
`massFacingFront=9`, `crucifiedUnit01=true`) do not override that decision.

## Offline composition preview

`tools/render_tree_of_life_preview.py` provides a fast framing loop without
starting Minecraft. It parses the ten nodes and 22 paths from
`TreeOfLifeLayout.java`, parses all Latin/Hebrew labels and their current
scales from `ClientFxManager.java`, and parses the front-capture distance and
vertical target from `VisualCaptureManager.java`. It then projects the current
layout to a 1280x720 image, with nine front-facing vessel probes and a rigid
cross-shaped Unit-01 probe at Tiferet:

```text
python tools/render_tree_of_life_preview.py --layout current --strict
```

The ignored output directory is
`external-assets/work/tree-of-life-preview/`. It contains
`tree_of_life_front.png`, a machine-readable JSON report and a short text
report. `--fov-degrees` overrides the default 70-degree vertical-FOV
assumption; Minecraft's player FOV is an option rather than a Java source
constant. `--strict` returns a failing exit code for clipping, sub-8-pixel
labels, any label/subject collision, missing path-letter backing or an
oversized frame.

`--layout candidate` is retained as a regression reconstruction of the adopted
candidate:

```text
python tools/render_tree_of_life_preview.py --layout candidate --strict
```

The candidate has now been adopted in Java. `ClientFxManager` owns the ten
`LABEL_X_OFFSETS`, 22 `PATH_LABEL_OFFSETS`, outward/alternating bilingual node
labels, leader lines, enlarged scales and `0xA0000000` backing for every label.
`VisualCaptureManager` uses the adopted 38-block top margin. The JSON report
records these parsed values under `adopted_java_layout`; it is no longer a list
of unapplied suggestions. The `current` and `candidate` PNGs must be
pixel-identical.

The adopted current source passes the offline strict gate: all 46 labels are
on-screen, the minimum measured glyph height is 12.67 pixels, no label bounding
boxes collide, no label intersects any of the ten ritual-body probes, and all
22 path letters use the canonical Golden Dawn edge mapping. Text, rings and
paths are pure red with no label backdrop or shadow. The complete layout
occupies about 37.1% of the frame width and 77.3% of its height. This is an offline composition pass only;
it cannot prove real mesh pose, Minecraft depth behaviour, exact vanilla-font
rasterisation or animation state. The latest real in-game image remains the
older `FAIL`, so the adopted layout is `BLOCKED` pending a fresh capture rather
than visually accepted.
