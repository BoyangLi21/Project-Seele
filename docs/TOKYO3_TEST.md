# Third New Tokyo City / NERV sortie test

This is an original block-built development district. It does not contain an
official map, anime screenshot, official texture, or redistributed third-party
city asset.

## Manual test

1. Start the desktop launcher: `Project SEELE 测试.bat`.
2. Enter a creative test world and stand on an open surface with at least
   48 blocks of vertical clearance above and 36 below.
3. Run `/seele tokyo3 setup`. The command intentionally writes a
   208 x 208 block development area and can pause the integrated server for a
   few seconds while the shells and roads are placed.
4. The player arrives on the south skyline deck. Run
   `/seele tokyo3 audit`; a valid first slice reports:

   `roads=8/8 towers=13/13 substations=2/2 pylons=6/6 battleBeacon=true sortieLane=true observationDeck=true foundation=true`

5. Run `/seele silo board` to enter the central Unit-01 from its high dorsal
   gantry. The existing synchronization and catapult sequence must finish on
   the city surface.
6. Run `/seele tokyo3 overview` at any time to return to the skyline deck.

## Automated visual evidence

From a terminal in the repository:

`tools\start_test.bat visual tokyo3`

The client builds a fixed district, audits the runtime blocks and local
high-detail Unit-00/01/02 fingerprints, then writes exactly four PNG files:

- `tokyo3_skyline_overview.png`
- `tokyo3_sortie_street.png`
- `tokyo3_power_grid.png`
- `tokyo3_battle_plaza.png`

The unattended client closes only after all four screenshots have been queued.
`tools/validate_visual_capture_run.py` rejects a missing view or any
`VISUAL TOKYO3 INVALID` log marker.

The fast offline layout gate is:

`python tools/render_tokyo3_preview.py --strict`

It writes the plan/isometric review image and JSON report under
`external-assets/work/tokyo3-preview/`.

## Human visual checklist

- The three colour-coded EVA bays remain centred in one unobstructed apron.
- The north/south sortie street is wide enough for a 24-block EVA to turn.
- Thirteen armour towers form a skyline ring rather than filling the launch
  envelope.
- Two orange substations and six connected pylons read as the power
  infrastructure for the positron operation.
- The red Angel plaza remains an open target space.
- The south observation deck frames both the city ring and central NERV apron.
- A continuous 240 x 240 foundation and six-block retaining edge support the
  whole district even in the Visual Lab void world.
- No road crosses a tower footprint and no tower occupies a launch shaft.

## Deliberate limitations

This is the first Phase 4 surface slice, not a claim that Tokyo-3 is finished.
The buildings are static original shells; actual layer-by-layer retraction,
Jigsaw variation, the GeoFront dimension, NERV interior modules, traffic and
licensed campaign maps remain separate work. The current acceptance target is
the connected loop: cage -> entry plug -> catapult -> surface district.
