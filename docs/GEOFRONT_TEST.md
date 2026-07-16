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

## Automated visual test

Run `tools\start_test.bat visual geofront` (or pass `visual geofront` to the
desktop launcher). The dedicated client rebuilds the sector, performs both
server and client landmark audits, captures four fixed PNG views, verifies the
new batch, and closes itself. A passing run names `cavern_overview`,
`nerv_pyramid`, `lcl_lake`, and `lift_terminals`.

## Current scope

This is the first bounded GeoFront slice: cavern, artificial sun, lake,
headquarters silhouette and three future EVA lift terminals. Cross-dimension
catapult travel, full NERV interiors, Terminal Dogma, LCL fluid and the final
~400-block cavern remain later work and are not claimed complete here.
