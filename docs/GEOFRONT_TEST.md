# GeoFront development-sector test

This clean-room development dimension uses only original procedural geometry
and vanilla Minecraft blocks. It contains no official EVA map, screenshot,
texture, audio, or redistributed third-party structure.

## Manual test

1. Start `Project SEELE 测试.bat` and enter a creative world.
2. Run `/seele geofront setup`. The first build places a bounded cavern shell,
   floor, lake, pyramid and infrastructure and may pause for several seconds.
   Minecraft may show its standard experimental-world confirmation the first
   time an existing save discovers the custom dimension; choose **Proceed**.
3. The player arrives on the south observation deck. Run
   `/seele geofront audit`; a valid sector reports:

   `floor=true wall=true lclLake=true nervPyramid=true artificialSun=true lifts=3/3 commandBridge=true observation=true`

4. Walk across the illuminated command bridge toward the central NERV
   pyramid. The orange glass lake is a visual stand-in until the dedicated LCL
   fluid lands in Phase 5.
5. `/seele geofront surface` returns to the exact dimension and coordinates
   saved before entry. `/seele geofront enter` revisits an already-built sector.

## Linked Tokyo-3 sortie

1. On an open surface, run `/seele tokyo3 setup` to build and audit the three
   surface bays.
2. Run `/seele geofront link` beside that complex. Unit-00, Unit-01 and Unit-02
   are transferred to their matching underground terminals; their exact
   surface beds remain the persisted destinations. The command places the
   player on Unit-01's rear high gantry.
3. Aim at the dorsal entry-plug socket and right-click, or use
   `/seele silo board`. The airframe remains frozen through synchronization,
   rises on the real 11 x 11 carrier, crosses dimensions at the top of the
   GeoFront shaft, and remounts the same pilot at the Tokyo-3 surface bay.
4. `/seele geofront sortie_audit` before launch reports exactly three linked
   variants, three valid surface destinations and three accessible gantries.
   `/seele tokyo3 audit` continues to locate and audit the registered surface
   district after its EVAs have deployed underground.

## Automated visual test

Run `tools\start_test.bat visual geofront` (or pass `visual geofront` to the
desktop launcher). The dedicated client rebuilds the sector, performs both
server and client landmark audits, captures four fixed PNG views, verifies the
new batch, and closes itself. A passing run names `cavern_overview`,
`nerv_pyramid`, `lcl_lake`, and `lift_terminals`.

Run `tools\start_test.bat visual geofront_sortie` for the connected flow. It
must capture exactly four state-gated frames: `three_units_ready`,
`entry_plug_locked`, `ascent_mid`, and `tokyo3_surface_arrival`. The ascent
frame is accepted only after the client-observed EVA has risen at least ten
blocks, and the arrival frame requires the same piloted EVA in the Overworld.

## Current scope

This is the first bounded GeoFront slice: cavern, artificial sun, lake,
headquarters silhouette and three working EVA lift terminals. The audited
GeoFront-to-Tokyo-3 catapult route is complete for this slice. Full NERV
interiors, final shaft art, Terminal Dogma, LCL fluid and the final ~400-block
cavern remain later work and are not claimed complete here.
