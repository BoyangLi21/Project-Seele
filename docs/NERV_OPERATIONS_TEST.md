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
6. From the command seats, walk through all three north exits into the widened
   glass observation gallery, then enter the west briefing/MAGI room and east
   medical/launch-support room. Also inspect the lower southern pressure
   vestibule. Every visible doorway must have a solid, lit floor and an
   enclosed destination; none may open onto the cavern cliff.

7. `/seele geofront audit` must report `operations={valid=true ...
   consoles=3/3 transit=3/3 connectedRoutes=true}`.

## Automated evidence

Run `tools\start_test.bat visual geofront`. The fail-closed client writes 13
PNG files. Besides the cavern, landscape, pyramid, Dogma, LCL and lift views,
the evidence set contains `geofront_nerv_operations.png`,
`geofront_nerv_support_gallery.png`, `geofront_nerv_briefing_room.png`,
`geofront_nerv_medical_support.png` and
`geofront_nerv_pressure_vestibule.png`. The batch is rejected if a command
landmark is missing, the observation glass is absent, or any existing
GeoFront landmark fails its server/client audit.

## Deliberate limitations

The current slice includes Operations, internal transit, MAGI maintenance,
briefing, medical/launch support, Central/Terminal Dogma and physical cockpit
video panels. Power-cable gameplay, full maintenance bays, final authored
decoration and licensed release assets remain later milestones.

## Imported module safety upgrade

When the local command-module asset is installed, all exposed map edges are
converted into usable interior space:

- the north opening is a sealed observation gallery;
- the west branch is a briefing and MAGI-liaison room;
- the east branch is a medical and launch-support room;
- the lower opening ends in an illuminated pressure vestibule;
- high maintenance openings are sealed observation windows, never exits.

Walk through every door visible from the command seats. No route may end over
the GeoFront cliff, expose an unsealed exterior edge, or contain a one-block
choke point. The audit must include `videoWall=true safeAnnex=true`.

## Real EVA pilot-view wall (multiplayer)

This check requires two clients on the same LAN or dedicated server; a single
player cannot simultaneously occupy an EVA cockpit and stand in Operations.

1. Client A boards Unit-00, Unit-01, or Unit-02 and remains in first person.
2. Client B runs `/seele geofront operations` and faces the three-panel wall.
3. Within about one second, only the matching 00/01/02 panel must leave its
   branded standby raster and show Client A's final cockpit frame, including
   the Project SEELE cockpit HUD.
4. Client A turns, aims, changes stance and changes weapon. Client B must see
   those exact first-person changes at roughly four frames per second; the feed
   must not switch to an external entity camera or another EVA variant.
   The strategic text panel must also show the same `POWER UMBILICAL/INTERNAL` and battery ticks as Client A's cockpit HUD.
5. Client A dismounts or disconnects. The last frame must disappear within three
   seconds rather than remaining as a false live image.
6. Repeat with all three pilots at once. Unit-00, Unit-01 and Unit-02 must stay
   isolated on the left, centre and right panels.

Uploads are accepted only from the authenticated first passenger of the claimed
EVA. The server relays them only to players inside the bounded Operations,
gallery and support-room volume; pilots waiting at the launch beds do not
receive their own upload. Frames use a fixed 160x90 PNG envelope and per-pilot
rate limiting. This remains command telemetry, not general screen sharing.
