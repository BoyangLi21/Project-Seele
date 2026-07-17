# NERV operations-centre test

This first interior slice is original procedural Minecraft architecture. It
does not reproduce or redistribute an official map, anime frame, texture, or
audio asset.

## Manual route

1. Start `Project SEELE 测试.bat`, enter a creative world, and run
   `/seele geofront setup`.
2. Run `/seele geofront operations`. The player arrives inside the upper
   tactical hall facing the multi-panel status wall.
3. Confirm the central illuminated tactical table, two operator rows, command
   lecterns, side galleries and ceiling-light grid are all visible without
   walls cutting through the room.
4. Take the three-wide quartz stair down to the lower concourse. The southern
   orange route reaches the pressure entrance and exterior command bridge.
5. Follow the lower route north. The distribution gallery must connect to
   three enclosed corridors: orange Unit-00, purple Unit-01 and red Unit-02.
   Each corridor ends in the matching lift approach without a blocked floor or
   one-block-high choke point.
6. `/seele geofront audit` must report `operations={valid=true ...
   consoles=3/3 transit=3/3 connectedRoutes=true}`.

## Automated evidence

Run `tools\start_test.bat visual geofront`. The fail-closed client writes five
PNG files, including `geofront_nerv_operations.png`. The batch is rejected if
the tactical beacon, centre display, access stair, any transit roof/floor
signature, or any existing GeoFront landmark is missing.

## Deliberate limitations

This is the operations and internal-transit slice, not the complete NERV HQ.
MAGI chambers, medical/containment wings, power-cable gameplay, maintenance
bays, Terminal Dogma and final authored decoration remain later milestones.
