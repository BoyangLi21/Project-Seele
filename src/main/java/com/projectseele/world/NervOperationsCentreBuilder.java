package com.projectseele.world;

import java.util.Locale;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockState;

/** Original block-built NERV command interior inside the GeoFront pyramid. */
public final class NervOperationsCentreBuilder
{
    public static final int OPERATIONS_FLOOR_Y = 7;
    public static final int OPERATIONS_ENTRY_Z = 18;
    public static final int DISPLAY_Z = -20;

    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;
    private static final int[] TRANSIT_X = {-28, 0, 28};

    private NervOperationsCentreBuilder() {}

    public static void build(ServerLevel level, BlockPos origin)
    {
        boolean localCommand =
                LocalMapAssetLoader.placeCommandModule(level, origin);
        buildLowerConcourse(level, origin);
        if (!localCommand)
        {
            buildOperationsHall(level, origin);
        }
        buildCommandSupportAnnex(level, origin, localCommand);
        buildVideoWall(level, origin, localCommand);
        buildAccessStairs(level, origin);
        buildLiftTransit(level, origin);
        NervOperationsConsole.install(level, origin);
        NervCommandTelemetry.install(level, origin);
    }

    /**
     * Paints the final, physical interchange after MAGI and Terminal Dogma
     * have opened their own doors. Keeping this pass last prevents either
     * deep-facility builder from hiding the route identity again.
     */
    public static void linkFacilities(ServerLevel level, BlockPos origin)
    {
        BlockState magi = Blocks.PURPLE_CONCRETE.defaultBlockState();
        BlockState terminal = Blocks.RED_CONCRETE.defaultBlockState();

        // West operations-floor route: command centre -> MAGI descent.
        for (int x = -34; x <= -23; x++)
        {
            set(level, origin.offset(x, OPERATIONS_FLOOR_Y, 12), magi);
        }

        // East lower-concourse route: central interchange -> Central Dogma.
        for (int x = 0; x <= 34; x++)
        {
            set(level, origin.offset(x, 1, -23), terminal);
        }

        // A compact three-colour route diagram is set into the existing wall,
        // so it cannot become another freestanding structure inside the shell.
        for (int y = 3; y <= 5; y++)
        {
            for (int x = -30; x <= -12; x++)
            {
                BlockState pixel = x <= -25
                        ? Blocks.PURPLE_STAINED_GLASS.defaultBlockState()
                        : x >= -18
                        ? Blocks.RED_STAINED_GLASS.defaultBlockState()
                        : Blocks.ORANGE_STAINED_GLASS.defaultBlockState();
                set(level, origin.offset(x, y, -17), pixel);
            }
        }
        set(level, origin.offset(-27, 4, -17),
                Blocks.SEA_LANTERN.defaultBlockState());
        set(level, origin.offset(-21, 4, -17),
                Blocks.SEA_LANTERN.defaultBlockState());
        set(level, origin.offset(-15, 4, -17),
                Blocks.SEA_LANTERN.defaultBlockState());
    }

    /**
     * Repairs only the command-room access network used at runtime. This is
     * deliberately bounded: camera shortcuts must never rebuild the 512-block
     * GeoFront sphere merely because an audit chunk was unloaded.
     */
    public static OperationsAudit repairRuntimeAccess(ServerLevel level,
                                                       BlockPos origin)
    {
        repairConnectedLowerRoutes(level, origin);
        linkFacilities(level, origin);
        NervOperationsConsole.install(level, origin);
        boolean localCommand =
                LocalMapAssetLoader.commandMarkersPresent(level, origin);
        buildCommandSupportAnnex(level, origin, localCommand);
        buildVideoWall(level, origin, localCommand);
        NervCommandTelemetry.install(level, origin);
        return inspect(level, origin);
    }

    public static OperationsAudit inspect(ServerLevel level, BlockPos origin)
    {
        boolean localCommand =
                LocalMapAssetLoader.commandMarkersPresent(level, origin);
        boolean entrance = localCommand
                || level.getBlockState(origin.offset(0, 7, 34))
                .is(Blocks.ORANGE_CONCRETE);
        boolean tacticalTable = localCommand
                || level.getBlockState(origin.offset(0, 8, 0))
                .is(Blocks.BEACON);
        boolean display = localCommand
                || level.getBlockState(origin.offset(0, 11, DISPLAY_Z))
                .is(Blocks.RED_STAINED_GLASS);
        boolean stairs = level.getBlockState(origin.offset(-13, 2, 22))
                .is(Blocks.SMOOTH_QUARTZ_STAIRS);
        int consoles = localCommand ? 3 : 0;
        if (!localCommand)
        {
            for (int x : new int[] {-10, 0, 10})
            {
                if (level.getBlockState(origin.offset(x, 9, 6))
                        .is(Blocks.COMPARATOR))
                {
                    consoles++;
                }
            }
        }
        int transitLinks = 0;
        for (int x : TRANSIT_X)
        {
            if (!level.getBlockState(origin.offset(x, 1, -50)).isAir()
                    && level.getBlockState(origin.offset(x, 6, -50))
                    .is(Blocks.IRON_BLOCK))
            {
                transitLinks++;
            }
        }
        boolean connectedRoutes = hasConnectedLowerRoutes(level, origin);
        boolean facilityLinks =
                level.getBlockState(origin.offset(-30, OPERATIONS_FLOOR_Y, 12))
                        .is(Blocks.PURPLE_CONCRETE)
                        && level.getBlockState(origin.offset(24, 1, -23))
                        .is(Blocks.RED_CONCRETE)
                        && level.getBlockState(origin.offset(-21, 4, -17))
                        .is(Blocks.SEA_LANTERN);
        int telemetryScreens = NervCommandTelemetry.countScreens(level, origin);
        BlockPos videoAnchor = localCommand
                ? origin.offset(0, 17, 58)
                : origin.offset(0, 7, DISPLAY_Z + 1);
        boolean videoWall = level.getBlockState(videoAnchor.offset(0, 4, -1))
                .is(Blocks.BLACK_CONCRETE)
                && level.getBlockState(videoAnchor.offset(-18, 4, -1))
                .is(Blocks.POLISHED_DEEPSLATE);
        boolean safeAnnex = !localCommand
                || level.getBlockState(origin.offset(1, -5, 95))
                .is(Blocks.POLISHED_DEEPSLATE)
                && level.getBlockState(origin.offset(0, -2, 98))
                .is(Blocks.GRAY_STAINED_GLASS)
                && level.getBlockState(origin.offset(-43, 0, 71))
                .is(Blocks.RED_STAINED_GLASS)
                && level.getBlockState(origin.offset(39, -4, 82))
                .is(Blocks.SMOOTH_QUARTZ_SLAB)
                && level.getBlockState(origin.offset(-18, -4, 94)).isAir()
                && level.getBlockState(origin.offset(0, -4, 94)).isAir()
                && level.getBlockState(origin.offset(18, -4, 94)).isAir()
                && level.getBlockState(origin.offset(-18, -5, 94))
                .is(Blocks.ORANGE_CONCRETE)
                && level.getBlockState(origin.offset(18, -5, 94))
                .is(Blocks.RED_CONCRETE)
                && level.getBlockState(origin.offset(-1, -20, -33)).isAir()
                && level.getBlockState(origin.offset(-1, -21, -34))
                .is(Blocks.POLISHED_BLACKSTONE)
                && level.getBlockState(origin.offset(-1, -18, -42))
                .is(Blocks.ORANGE_STAINED_GLASS)
                && hasSafeAnnexRoutes(level, origin);
        NervOperationsConsole.ConsoleAudit commandConsole =
                NervOperationsConsole.inspect(level, origin);
        boolean valid = entrance && tacticalTable && display && stairs
                && consoles == 3 && transitLinks == 3 && connectedRoutes
                && facilityLinks && videoWall && safeAnnex
                && telemetryScreens == NervCommandTelemetry.SCREEN_COUNT
                && commandConsole.valid();
        return new OperationsAudit(valid, entrance, tacticalTable, display,
                stairs, consoles, transitLinks, connectedRoutes, facilityLinks,
                videoWall, safeAnnex, telemetryScreens, commandConsole);
    }

    private static void buildLowerConcourse(ServerLevel level, BlockPos origin)
    {
        BlockState floor = Blocks.POLISHED_BLACKSTONE.defaultBlockState();
        BlockState wall = Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState();
        BlockState accent = Blocks.ORANGE_CONCRETE.defaultBlockState();

        // The southern command bridge enters the pyramid at this nine-block
        // pressure gate and continues through the lower public concourse.
        for (int z = 18; z <= 36; z++)
        {
            for (int x = -5; x <= 5; x++)
            {
                set(level, origin.offset(x, 1, z),
                        x == 0 && z % 4 < 2 ? accent : floor);
                for (int y = 2; y <= 6; y++)
                {
                    set(level, origin.offset(x, y, z), Blocks.AIR.defaultBlockState());
                }
            }
            for (int y = 2; y <= 6; y++)
            {
                set(level, origin.offset(-6, y, z), wall);
                set(level, origin.offset(6, y, z), wall);
            }
            set(level, origin.offset(0, 6, z),
                    z % 5 == 0 ? Blocks.SEA_LANTERN.defaultBlockState()
                            : Blocks.IRON_BLOCK.defaultBlockState());
        }
        for (int x = -6; x <= 6; x++)
        {
            set(level, origin.offset(x, 7, 34),
                    Math.abs(x) <= 2 ? accent : Blocks.IRON_BLOCK.defaultBlockState());
        }

        // A wide lower gallery distributes staff between the three EVA lift
        // corridors without forcing them through the command hall above.
        for (int x = -32; x <= 32; x++)
        {
            for (int z = -28; z <= -18; z++)
            {
                set(level, origin.offset(x, 1, z),
                        z == -23 && Math.floorMod(x, 6) < 3
                                ? accent : floor);
                for (int y = 2; y <= 5; y++)
                {
                    set(level, origin.offset(x, y, z), Blocks.AIR.defaultBlockState());
                }
                set(level, origin.offset(x, 6, z),
                        x % 8 == 0 ? Blocks.SEA_LANTERN.defaultBlockState()
                                : Blocks.IRON_BLOCK.defaultBlockState());
            }
        }
        for (int x = -32; x <= 32; x++)
        {
            for (int y = 2; y <= 5; y++)
            {
                set(level, origin.offset(x, y, -29), wall);
                set(level, origin.offset(x, y, -17), wall);
            }
        }

        // Join the southern entrance and northern distribution gallery.
        for (int z = -18; z <= 18; z++)
        {
            for (int x = -5; x <= 5; x++)
            {
                set(level, origin.offset(x, 1, z),
                        x == 0 && z % 6 < 3 ? accent : floor);
                for (int y = 2; y <= 6; y++)
                {
                    set(level, origin.offset(x, y, z), Blocks.AIR.defaultBlockState());
                }
            }
        }
    }

    private static void buildOperationsHall(ServerLevel level, BlockPos origin)
    {
        BlockState floor = Blocks.SMOOTH_STONE.defaultBlockState();
        BlockState wall = Blocks.BLACK_CONCRETE.defaultBlockState();

        for (int x = -23; x <= 23; x++)
        {
            for (int z = -21; z <= 21; z++)
            {
                set(level, origin.offset(x, OPERATIONS_FLOOR_Y, z),
                        Math.floorMod(x + z, 9) == 0
                                ? Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState() : floor);
                for (int y = 8; y <= 13; y++)
                {
                    set(level, origin.offset(x, y, z), Blocks.AIR.defaultBlockState());
                }
                set(level, origin.offset(x, 14, z),
                        x % 8 == 0 && z % 8 == 0
                                ? Blocks.SEA_LANTERN.defaultBlockState()
                                : Blocks.GRAY_CONCRETE.defaultBlockState());
            }
        }
        for (int y = 8; y <= 13; y++)
        {
            for (int x = -23; x <= 23; x++)
            {
                set(level, origin.offset(x, y, -21), wall);
                set(level, origin.offset(x, y, 21), wall);
            }
            for (int z = -21; z <= 21; z++)
            {
                set(level, origin.offset(-23, y, z), wall);
                set(level, origin.offset(23, y, z), wall);
            }
        }

        buildTacticalDisplay(level, origin);
        buildConsoleTerraces(level, origin);
        buildSideGalleries(level, origin);
    }

    private static void buildTacticalDisplay(ServerLevel level, BlockPos origin)
    {
        for (int x = -18; x <= 18; x++)
        {
            for (int y = 9; y <= 13; y++)
            {
                BlockState pixel;
                if (y == 9 || y == 13)
                {
                    pixel = Blocks.BLACK_CONCRETE.defaultBlockState();
                }
                else if (Math.abs(x) <= 1)
                {
                    pixel = Blocks.RED_STAINED_GLASS.defaultBlockState();
                }
                else if (Math.abs(x) % 6 == 0)
                {
                    pixel = Blocks.BLACK_CONCRETE.defaultBlockState();
                }
                else if (Math.floorMod(x + y, 5) == 0)
                {
                    pixel = Blocks.LIME_STAINED_GLASS.defaultBlockState();
                }
                else
                {
                    pixel = x < 0 ? Blocks.CYAN_STAINED_GLASS.defaultBlockState()
                            : Blocks.BLUE_STAINED_GLASS.defaultBlockState();
                }
                set(level, origin.offset(x, y, DISPLAY_Z), pixel);
            }
        }

        // Central tactical table: the beacon is an unambiguous runtime
        // signature and the glass map reads from every command tier.
        for (int x = -4; x <= 4; x++)
        {
            for (int z = -3; z <= 3; z++)
            {
                set(level, origin.offset(x, 8, z),
                        Math.abs(x) == 4 || Math.abs(z) == 3
                                ? Blocks.POLISHED_BLACKSTONE.defaultBlockState()
                                : Blocks.ORANGE_STAINED_GLASS.defaultBlockState());
            }
        }
        set(level, origin.offset(0, 8, 0), Blocks.BEACON.defaultBlockState());
        set(level, origin.offset(0, 9, 0), Blocks.RED_STAINED_GLASS.defaultBlockState());
    }

    private static void buildConsoleTerraces(ServerLevel level, BlockPos origin)
    {
        BlockState chair = Blocks.POLISHED_BLACKSTONE_BRICK_STAIRS.defaultBlockState()
                .setValue(StairBlock.FACING, Direction.NORTH);
        for (int z : new int[] {6, 11})
        {
            for (int x = -15; x <= 15; x += 5)
            {
                set(level, origin.offset(x, 8, z),
                        Blocks.POLISHED_BLACKSTONE.defaultBlockState());
                set(level, origin.offset(x, 9, z), Blocks.COMPARATOR.defaultBlockState());
                set(level, origin.offset(x, 8, z + 2), chair);
                if (Math.abs(x) % 10 == 0)
                {
                    set(level, origin.offset(x, 10, z),
                            Blocks.LIME_STAINED_GLASS.defaultBlockState());
                }
            }
        }
        for (int x = -18; x <= 18; x++)
        {
            set(level, origin.offset(x, 8, 16),
                    Math.abs(x) <= 3 ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                            : Blocks.POLISHED_DEEPSLATE.defaultBlockState());
        }
        for (int x : new int[] {-8, 8})
        {
            set(level, origin.offset(x, 9, 16), Blocks.LECTERN.defaultBlockState());
        }
    }

    private static void buildSideGalleries(ServerLevel level, BlockPos origin)
    {
        for (int z = -16; z <= 16; z++)
        {
            for (int x : new int[] {-21, 21})
            {
                set(level, origin.offset(x, 11, z),
                        z % 5 == 0 ? Blocks.SEA_LANTERN.defaultBlockState()
                                : Blocks.IRON_BLOCK.defaultBlockState());
                set(level, origin.offset(x > 0 ? x - 1 : x + 1, 12, z),
                        Blocks.IRON_BARS.defaultBlockState());
            }
        }
    }


    /**
     * Finishes the downloaded command module's open boundary as inhabited,
     * pressure-safe NERV space. The source build ends at several naked map
     * edges; those edges must never read as doors onto the GeoFront cliff.
     */
    private static void buildCommandSupportAnnex(ServerLevel level,
                                                  BlockPos origin,
                                                  boolean localCommand)
    {
        if (!localCommand)
        {
            return;
        }

        BlockState floor = Blocks.POLISHED_DEEPSLATE.defaultBlockState();
        BlockState wall = Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState();
        BlockState ceiling = Blocks.GRAY_CONCRETE.defaultBlockState();

        // The large north opening becomes an enclosed observation gallery.
        // At this height the sloping pyramid's north face is z=98..99, so z=98
        // is the deepest pressure wall that stays completely inside the shell.
        buildSafeRoom(level, origin, -30, 30, -5, 4, 94, 98,
                floor, wall, ceiling, true);
        for (int x = -28; x <= 28; x++)
        {
            for (int y = -4; y <= 2; y++)
            {
                set(level, origin.offset(x, y, 98),
                        y >= -3 && y <= 1
                                ? Blocks.GRAY_STAINED_GLASS.defaultBlockState()
                                : wall);
            }
        }
        openGalleryDoorway(level, origin, -18,
                Blocks.ORANGE_CONCRETE.defaultBlockState());
        openGalleryDoorway(level, origin, 0,
                Blocks.PURPLE_CONCRETE.defaultBlockState());
        openGalleryDoorway(level, origin, 18,
                Blocks.RED_CONCRETE.defaultBlockState());
        // A continuous illuminated route makes the three exits read as one
        // inhabited NERV circulation space rather than unrelated holes in the
        // downloaded module. Keep all three interior rows obstacle-free.
        for (int x = -29; x <= 29; x++)
        {
            set(level, origin.offset(x, -5, 96),
                    Math.floorMod(x, 8) == 0
                            ? Blocks.SEA_LANTERN.defaultBlockState()
                            : Blocks.GRAY_CONCRETE.defaultBlockState());
        }
        for (int[] route : new int[][] {
                {-18, 1}, {0, 2}, {18, 3}
        })
        {
            BlockState accent = route[1] == 1
                    ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                    : route[1] == 2
                            ? Blocks.PURPLE_CONCRETE.defaultBlockState()
                            : Blocks.RED_CONCRETE.defaultBlockState();
            for (int z = 94; z <= 97; z++)
            {
                set(level, origin.offset(route[0], -5, z), accent);
            }
        }
        decorateSupportGallery(level, origin);


        // Two real support rooms branch from the gallery without protruding
        // through the sloping pyramid: west is briefing/MAGI liaison, east is
        // medical and launch-control support.
        buildSafeRoom(level, origin, -56, -30, -5, 4, 70, 96,
                floor, wall, ceiling, false);
        buildSafeRoom(level, origin, 30, 56, -5, 4, 70, 96,
                floor, wall, ceiling, false);
        openDoorway(level, origin, -30, -4, 94, Direction.WEST);
        openDoorway(level, origin, 30, -4, 94, Direction.EAST);
        furnishBriefingRoom(level, origin);
        furnishMedicalSupport(level, origin);

        // The lower southern asset opening now terminates in an illuminated
        // pressure vestibule rather than empty cavern air.
        buildSafeRoom(level, origin, -5, 5, -21, -14, -42, -33,
                Blocks.POLISHED_BLACKSTONE.defaultBlockState(), wall,
                Blocks.IRON_BLOCK.defaultBlockState(), false);
        for (int x = -2; x <= 2; x++)
        {
            for (int y = -20; y <= -16; y++)
            {
                set(level, origin.offset(x, y, -42),
                        Blocks.ORANGE_STAINED_GLASS.defaultBlockState());
            }
        }
        openPressureVestibuleDoorway(level, origin);

        // Two high maintenance apertures are observation windows, not exits.
        for (int x : new int[] {-26, -25, 21, 22})
        {
            set(level, origin.offset(x, 39, 95),
                    Blocks.IRON_BLOCK.defaultBlockState());
            for (int y = 40; y <= 42; y++)
            {
                set(level, origin.offset(x, y, 95),
                        Blocks.RED_STAINED_GLASS.defaultBlockState());
            }
        }
    }

    private static void buildSafeRoom(ServerLevel level, BlockPos origin,
                                      int minimumX, int maximumX,
                                      int floorY, int ceilingY,
                                      int minimumZ, int maximumZ,
                                      BlockState floor, BlockState wall,
                                      BlockState ceiling,
                                      boolean glassNorth)
    {
        for (int x = minimumX; x <= maximumX; x++)
        {
            for (int z = minimumZ; z <= maximumZ; z++)
            {
                set(level, origin.offset(x, floorY, z), floor);
                set(level, origin.offset(x, ceilingY, z),
                        Math.floorMod(x + z, 7) == 0
                                ? Blocks.SEA_LANTERN.defaultBlockState()
                                : ceiling);
                for (int y = floorY + 1; y < ceilingY; y++)
                {
                    boolean boundary = x == minimumX || x == maximumX
                            || z == minimumZ || z == maximumZ;
                    BlockState state = boundary
                            ? glassNorth && z == maximumZ
                                    ? Blocks.GRAY_STAINED_GLASS.defaultBlockState()
                                    : wall
                            : Blocks.AIR.defaultBlockState();
                    set(level, origin.offset(x, y, z), state);
                }
            }
        }
    }

    private static void openGalleryDoorway(ServerLevel level,
                                            BlockPos origin, int centreX,
                                            BlockState accent)
    {
        // The imported module is clipped at relative z=95. A two-block
        // pressure threshold replaces each exposed exit with a real doorway
        // into the sealed support gallery.
        for (int z = 94; z <= 95; z++)
        {
            for (int x = centreX - 2; x <= centreX + 2; x++)
            {
                for (int y = -4; y <= 1; y++)
                {
                    set(level, origin.offset(x, y, z),
                            Blocks.AIR.defaultBlockState());
                }
            }
        }
        for (int y = -4; y <= 2; y++)
        {
            set(level, origin.offset(centreX - 3, y, 94), accent);
            set(level, origin.offset(centreX + 3, y, 94), accent);
        }
        for (int x = centreX - 2; x <= centreX + 2; x++)
        {
            set(level, origin.offset(x, 2, 94),
                    x == centreX
                            ? Blocks.SEA_LANTERN.defaultBlockState()
                            : accent);
        }
    }

    private static void decorateSupportGallery(ServerLevel level,
                                               BlockPos origin)
    {
        // Recessed information bays break up the imported module's blank
        // clipped wall without consuming any of the three walkable rows.
        // Their colours repeat the physical route stripes under each door.
        int[][] panels = {
                {-28, -23, 0}, {-13, -6, 1},
                {6, 13, 2}, {23, 28, 3}
        };
        for (int[] panel : panels)
        {
            BlockState accent = switch (panel[2])
            {
                case 0 -> Blocks.ORANGE_STAINED_GLASS.defaultBlockState();
                case 1 -> Blocks.PURPLE_STAINED_GLASS.defaultBlockState();
                case 2 -> Blocks.RED_STAINED_GLASS.defaultBlockState();
                default -> Blocks.CYAN_STAINED_GLASS.defaultBlockState();
            };
            int centre = (panel[0] + panel[1]) / 2;
            for (int x = panel[0]; x <= panel[1]; x++)
            {
                for (int y = -3; y <= 1; y++)
                {
                    boolean frame = x == panel[0] || x == panel[1]
                            || y == -3 || y == 1;
                    set(level, origin.offset(x, y, 94),
                            frame
                                    ? Blocks.POLISHED_DEEPSLATE
                                            .defaultBlockState()
                                    : Blocks.BLACK_CONCRETE
                                            .defaultBlockState());
                }
            }
            for (int x = panel[0] + 1; x < panel[1]; x += 2)
            {
                set(level, origin.offset(x, -1, 94), accent);
            }
            set(level, origin.offset(centre, 0, 94),
                    Blocks.SEA_LANTERN.defaultBlockState());
        }

        // Full-block mullions make the north face read as a pressure-rated
        // observation window rather than a missing chunk exposing raw rock.
        // They remain in the boundary plane at z=98, outside the aisle.
        for (int x = -28; x <= 28; x += 8)
        {
            for (int y = -3; y <= 1; y++)
            {
                set(level, origin.offset(x, y, 98),
                        Blocks.POLISHED_DEEPSLATE.defaultBlockState());
            }
            set(level, origin.offset(x, -1, 98),
                    Blocks.IRON_BLOCK.defaultBlockState());
        }
    }

    private static void openPressureVestibuleDoorway(ServerLevel level,
                                                      BlockPos origin)
    {
        // The downloaded module has one genuine three-block service exit on
        // its south boundary. Continue that floor into the sealed vestibule
        // instead of replacing the doorway with a wall or leaving a drop.
        for (int x = -2; x <= 0; x++)
        {
            for (int y = -20; y <= -17; y++)
            {
                set(level, origin.offset(x, y, -33),
                        Blocks.AIR.defaultBlockState());
            }
        }
        for (int y = -21; y <= -16; y++)
        {
            set(level, origin.offset(-3, y, -33),
                    Blocks.ORANGE_CONCRETE.defaultBlockState());
            set(level, origin.offset(1, y, -33),
                    Blocks.ORANGE_CONCRETE.defaultBlockState());
        }
        for (int x = -2; x <= 0; x++)
        {
            set(level, origin.offset(x, -16, -33),
                    x == -1 ? Blocks.SEA_LANTERN.defaultBlockState()
                            : Blocks.ORANGE_CONCRETE.defaultBlockState());
        }
    }



    private static void openDoorway(ServerLevel level, BlockPos origin,
                                    int wallX, int feetY, int centreZ,
                                    Direction direction)
    {
        int inward = direction == Direction.WEST ? -1 : 1;
        for (int x = wallX; x != wallX + inward * 4; x += inward)
        {
            for (int z = centreZ - 1; z <= centreZ + 1; z++)
            {
                for (int y = feetY; y <= feetY + 3; y++)
                {
                    set(level, origin.offset(x, y, z),
                            Blocks.AIR.defaultBlockState());
                }
            }
        }
    }

    private static void furnishBriefingRoom(ServerLevel level, BlockPos origin)
    {
        // Remove the old floor-level slab prototype before installing a
        // readable human-scale table and unobstructed circulation aisle.
        for (int x = -51; x <= -35; x++)
        {
            for (int z = 78; z <= 87; z++)
            {
                set(level, origin.offset(x, -4, z),
                        Blocks.AIR.defaultBlockState());
                set(level, origin.offset(x, -3, z),
                        Blocks.AIR.defaultBlockState());
            }
        }

        for (int x = -48; x <= -38; x++)
        {
            for (int z = 80; z <= 84; z++)
            {
                boolean cutCorner = Math.abs(x + 43) == 5
                        && Math.abs(z - 82) == 2;
                if (!cutCorner)
                {
                    set(level, origin.offset(x, -3, z),
                            Blocks.SMOOTH_QUARTZ_SLAB.defaultBlockState());
                }
            }
        }
        for (int x : new int[] {-47, -39})
        {
            for (int z : new int[] {81, 83})
            {
                set(level, origin.offset(x, -4, z),
                        Blocks.POLISHED_BLACKSTONE_WALL.defaultBlockState());
            }
        }
        set(level, origin.offset(-43, -4, 82),
                Blocks.SEA_LANTERN.defaultBlockState());
        set(level, origin.offset(-43, -3, 82),
                Blocks.CYAN_STAINED_GLASS.defaultBlockState());

        BlockState northChair = Blocks.POLISHED_BLACKSTONE_BRICK_STAIRS
                .defaultBlockState().setValue(StairBlock.FACING,
                        Direction.SOUTH);
        BlockState southChair = Blocks.POLISHED_BLACKSTONE_BRICK_STAIRS
                .defaultBlockState().setValue(StairBlock.FACING,
                        Direction.NORTH);
        for (int x : new int[] {-47, -43, -39})
        {
            set(level, origin.offset(x, -4, 78), northChair);
            set(level, origin.offset(x, -4, 86), southChair);
        }
        set(level, origin.offset(-50, -4, 82),
                Blocks.POLISHED_BLACKSTONE_BRICK_STAIRS.defaultBlockState()
                        .setValue(StairBlock.FACING, Direction.EAST));
        set(level, origin.offset(-36, -4, 82),
                Blocks.POLISHED_BLACKSTONE_BRICK_STAIRS.defaultBlockState()
                        .setValue(StairBlock.FACING, Direction.WEST));

        // A recessed tactical wall sits behind the table, fully inside the
        // room shell. It reads as a screen instead of a freestanding billboard.
        for (int x = -50; x <= -36; x++)
        {
            for (int y = -3; y <= 1; y++)
            {
                boolean frame = x == -50 || x == -36 || y == -3 || y == 1;
                set(level, origin.offset(x, y, 71), frame
                        ? Blocks.PURPLE_CONCRETE.defaultBlockState()
                        : Blocks.BLACK_CONCRETE.defaultBlockState());
            }
        }
        for (int x = -48; x <= -38; x++)
        {
            set(level, origin.offset(x, -1, 71),
                    Math.floorMod(x, 3) == 0
                            ? Blocks.SEA_LANTERN.defaultBlockState()
                            : Blocks.ORANGE_STAINED_GLASS.defaultBlockState());
        }
        set(level, origin.offset(-46, 0, 71),
                Blocks.CYAN_STAINED_GLASS.defaultBlockState());
        set(level, origin.offset(-43, 0, 71),
                Blocks.RED_STAINED_GLASS.defaultBlockState());
        set(level, origin.offset(-40, 0, 71),
                Blocks.CYAN_STAINED_GLASS.defaultBlockState());

        for (int x = -55; x <= -30; x++)
        {
            set(level, origin.offset(x, -5, 94),
                    Blocks.PURPLE_CONCRETE.defaultBlockState());
        }
        for (int z = 72; z <= 94; z++)
        {
            set(level, origin.offset(-56, 0, z),
                    Math.floorMod(z, 6) == 0
                            ? Blocks.PURPLE_STAINED_GLASS.defaultBlockState()
                            : Blocks.BLACK_CONCRETE.defaultBlockState());
        }
    }

    private static void furnishMedicalSupport(ServerLevel level,
                                               BlockPos origin)
    {
        // Clear the former wool benches so each treatment pod has a bed,
        // head monitor, visitor seat and a full-width aisle to the gallery.
        for (int x = 35; x <= 46; x++)
        {
            for (int z = 73; z <= 91; z++)
            {
                set(level, origin.offset(x, -4, z),
                        Blocks.AIR.defaultBlockState());
                set(level, origin.offset(x, -3, z),
                        Blocks.AIR.defaultBlockState());
            }
        }

        for (int centreZ : new int[] {75, 82, 89})
        {
            for (int x = 36; x <= 43; x++)
            {
                for (int z = centreZ; z <= centreZ + 1; z++)
                {
                    BlockState bed = x == 36
                            ? Blocks.IRON_BLOCK.defaultBlockState()
                            : Blocks.SMOOTH_QUARTZ_SLAB.defaultBlockState();
                    set(level, origin.offset(x, -4, z), bed);
                }
            }
            set(level, origin.offset(36, -3, centreZ),
                    Blocks.SEA_LANTERN.defaultBlockState());
            set(level, origin.offset(36, -3, centreZ + 1),
                    Blocks.CYAN_STAINED_GLASS.defaultBlockState());
            set(level, origin.offset(45, -4, centreZ),
                    Blocks.QUARTZ_STAIRS.defaultBlockState()
                            .setValue(StairBlock.FACING, Direction.WEST));
            set(level, origin.offset(45, -4, centreZ + 1),
                    Blocks.QUARTZ_STAIRS.defaultBlockState()
                            .setValue(StairBlock.FACING, Direction.WEST));
        }

        for (int x = 34; x <= 52; x++)
        {
            for (int y = -3; y <= 1; y++)
            {
                boolean frame = x == 34 || x == 52 || y == -3 || y == 1;
                set(level, origin.offset(x, y, 71), frame
                        ? Blocks.CYAN_CONCRETE.defaultBlockState()
                        : Blocks.BLACK_CONCRETE.defaultBlockState());
            }
        }
        for (int x = 36; x <= 50; x++)
        {
            set(level, origin.offset(x, -1, 71),
                    Math.floorMod(x, 4) == 0
                            ? Blocks.REDSTONE_LAMP.defaultBlockState()
                            : Blocks.CYAN_STAINED_GLASS.defaultBlockState());
        }

        for (int z = 74; z <= 92; z += 3)
        {
            set(level, origin.offset(55, -4, z),
                    Blocks.IRON_BLOCK.defaultBlockState());
            set(level, origin.offset(55, -3, z),
                    Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
            set(level, origin.offset(55, -2, z),
                    Blocks.CYAN_STAINED_GLASS.defaultBlockState());
            set(level, origin.offset(54, -2, z),
                    Blocks.SEA_LANTERN.defaultBlockState());
        }
        for (int x = 30; x <= 55; x++)
        {
            set(level, origin.offset(x, -5, 94),
                    Blocks.CYAN_CONCRETE.defaultBlockState());
        }
        for (int z = 72; z <= 94; z++)
        {
            set(level, origin.offset(56, 0, z),
                    Math.floorMod(z, 6) == 0
                            ? Blocks.CYAN_STAINED_GLASS.defaultBlockState()
                            : Blocks.BLACK_CONCRETE.defaultBlockState());
        }
        for (int partitionZ : new int[] {79, 86})
        {
            for (int x = 35; x <= 41; x++)
            {
                for (int y = -3; y <= 0; y++)
                {
                    set(level, origin.offset(x, y, partitionZ),
                            Blocks.CYAN_STAINED_GLASS.defaultBlockState());
                }
            }
        }
    }
    /** Builds three physical 16:9 surfaces for authenticated cockpit frames. */
    private static void buildVideoWall(ServerLevel level, BlockPos origin,
                                       boolean localCommand)
    {
        BlockPos anchor = localCommand
                ? origin.offset(0, 17, 58)
                : origin.offset(0, 7, DISPLAY_Z + 1);
        for (int x = -18; x <= 18; x++)
        {
            for (int y = 0; y <= 8; y++)
            {
                boolean frame = y == 0 || y == 8
                        || x == -18 || x == -6 || x == 6 || x == 18;
                BlockState state = frame
                        ? (y == 0 && Math.floorMod(x, 6) == 0
                                ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                                : Blocks.POLISHED_DEEPSLATE.defaultBlockState())
                        : Blocks.BLACK_CONCRETE.defaultBlockState();
                set(level, anchor.offset(x, y, -1), state);
            }
        }
        for (int x : new int[] {-12, 0, 12})
        {
            set(level, anchor.offset(x, 0, -1),
                    Blocks.SEA_LANTERN.defaultBlockState());
        }
    }
    private static void buildAccessStairs(ServerLevel level, BlockPos origin)
    {
        BlockState stair = Blocks.SMOOTH_QUARTZ_STAIRS.defaultBlockState()
                .setValue(StairBlock.FACING, Direction.NORTH);
        for (int step = 0; step <= 5; step++)
        {
            int y = 2 + step;
            int z = 22 - step;
            for (int x = -14; x <= -12; x++)
            {
                for (int clearY = y + 1; clearY <= y + 3; clearY++)
                {
                    set(level, origin.offset(x, clearY, z), Blocks.AIR.defaultBlockState());
                }
                set(level, origin.offset(x, y, z), stair);
            }
        }
    }

    private static void buildLiftTransit(ServerLevel level, BlockPos origin)
    {
        for (int laneX : TRANSIT_X)
        {
            BlockState accent = laneX < 0 ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                    : laneX > 0 ? Blocks.RED_CONCRETE.defaultBlockState()
                    : Blocks.PURPLE_CONCRETE.defaultBlockState();
            for (int z = -61; z <= -28; z++)
            {
                for (int x = -3; x <= 3; x++)
                {
                    set(level, origin.offset(laneX + x, 1, z),
                            x == 0 ? accent : Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
                    for (int y = 2; y <= 5; y++)
                    {
                        set(level, origin.offset(laneX + x, y, z),
                                Blocks.AIR.defaultBlockState());
                    }
                    set(level, origin.offset(laneX + x, 6, z),
                            x == 0 && Math.floorMod(z, 7) == 0
                                    ? Blocks.SEA_LANTERN.defaultBlockState()
                                    : Blocks.IRON_BLOCK.defaultBlockState());
                }
                for (int y = 2; y <= 5; y++)
                {
                    set(level, origin.offset(laneX - 4, y, z),
                            Blocks.GRAY_CONCRETE.defaultBlockState());
                    set(level, origin.offset(laneX + 4, y, z),
                            Blocks.GRAY_CONCRETE.defaultBlockState());
                }
            }
        }
    }

    private static boolean hasConnectedLowerRoutes(ServerLevel level, BlockPos origin)
    {
        for (int z = -61; z <= 36; z++)
        {
            if (z > -18 || z < -28)
            {
                // The exterior command bridge deliberately rises one block at
                // z=35.  Audit the player's feet above that deck instead of
                // mistaking the accessible transition for an obstruction.
                int feetY = z >= 35 ? 3 : 2;
                if (!walkable(level, origin.offset(0, feetY, z)))
                {
                    return false;
                }
            }
        }
        for (int laneX : TRANSIT_X)
        {
            int minimum = Math.min(0, laneX);
            int maximum = Math.max(0, laneX);
            for (int x = minimum; x <= maximum; x++)
            {
                if (!walkable(level, origin.offset(x, 2, -23)))
                {
                    return false;
                }
            }
            for (int z = -61; z <= -28; z++)
            {
                if (!walkable(level, origin.offset(laneX, 2, z)))
                {
                    return false;
                }
            }
        }
        for (int step = 0; step <= 5; step++)
        {
            int y = 2 + step;
            int z = 22 - step;
            if (!level.getBlockState(origin.offset(-13, y, z))
                    .is(Blocks.SMOOTH_QUARTZ_STAIRS)
                    || !level.getBlockState(origin.offset(-13, y + 1, z)).isAir()
                    || !level.getBlockState(origin.offset(-13, y + 2, z)).isAir())
            {
                return false;
            }
        }
        return true;
    }

    private static boolean hasSafeAnnexRoutes(ServerLevel level,
                                               BlockPos origin)
    {
        for (int x = -29; x <= 29; x++)
        {
            for (int z = 95; z <= 97; z++)
            {
                if (!walkable(level, origin.offset(x, -4, z)))
                {
                    return false;
                }
            }
        }
        for (int x = -55; x <= -30; x++)
        {
            if (!walkable(level, origin.offset(x, -4, 94)))
            {
                return false;
            }
        }
        for (int x = 30; x <= 55; x++)
        {
            if (!walkable(level, origin.offset(x, -4, 94)))
            {
                return false;
            }
        }
        for (int z = 72; z <= 94; z++)
        {
            if (!walkable(level, origin.offset(-32, -4, z)))
            {
                return false;
            }
            if (!walkable(level, origin.offset(53, -4, z)))
            {
                return false;
            }
        }
        for (int z = -41; z <= -33; z++)
        {
            if (!walkable(level, origin.offset(-1, -20, z)))
            {
                return false;
            }
        }
        return true;
    }
    private static boolean walkable(ServerLevel level, BlockPos feet)
    {
        level.getChunkAt(feet);
        BlockPos floor = feet.below();
        BlockState floorState = level.getBlockState(floor);
        return !floorState.isAir()
                && floorState.getFluidState().isEmpty()
                && !floorState.getCollisionShape(level, floor).isEmpty()
                && level.getBlockState(feet).isAir()
                && level.getBlockState(feet.above()).isAir();
    }

    private static void repairConnectedLowerRoutes(ServerLevel level,
                                                    BlockPos origin)
    {
        for (int z = -61; z <= 36; z++)
        {
            if (z > -18 || z < -28)
            {
                int feetY = z >= 35 ? 3 : 2;
                BlockState floor = z >= 35
                        ? Blocks.IRON_BLOCK.defaultBlockState()
                        : z < -28
                        ? Blocks.PURPLE_CONCRETE.defaultBlockState()
                        : Blocks.POLISHED_BLACKSTONE.defaultBlockState();
                repairWalkway(level, origin.offset(0, feetY, z), floor);
            }
        }
        for (int laneX : TRANSIT_X)
        {
            BlockState laneFloor = laneX < 0
                    ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                    : laneX > 0
                    ? Blocks.RED_CONCRETE.defaultBlockState()
                    : Blocks.PURPLE_CONCRETE.defaultBlockState();
            int minimum = Math.min(0, laneX);
            int maximum = Math.max(0, laneX);
            for (int x = minimum; x <= maximum; x++)
            {
                repairWalkway(level, origin.offset(x, 2, -23),
                        Blocks.POLISHED_BLACKSTONE.defaultBlockState());
            }
            for (int z = -61; z <= -28; z++)
            {
                repairWalkway(level, origin.offset(laneX, 2, z), laneFloor);
            }
        }

        BlockState stair = Blocks.SMOOTH_QUARTZ_STAIRS.defaultBlockState()
                .setValue(StairBlock.FACING, Direction.NORTH);
        for (int step = 0; step <= 5; step++)
        {
            int y = 2 + step;
            int z = 22 - step;
            BlockPos position = origin.offset(-13, y, z);
            level.getChunkAt(position);
            set(level, position, stair);
            set(level, position.above(), Blocks.AIR.defaultBlockState());
            set(level, position.above(2), Blocks.AIR.defaultBlockState());
        }
    }

    private static void repairWalkway(ServerLevel level, BlockPos feet,
                                       BlockState replacementFloor)
    {
        level.getChunkAt(feet);
        BlockPos floor = feet.below();
        BlockState currentFloor = level.getBlockState(floor);
        if (currentFloor.isAir()
                || !currentFloor.getFluidState().isEmpty()
                || currentFloor.getCollisionShape(level, floor).isEmpty())
        {
            set(level, floor, replacementFloor);
        }
        set(level, feet, Blocks.AIR.defaultBlockState());
        set(level, feet.above(), Blocks.AIR.defaultBlockState());
    }

    private static void set(ServerLevel level, BlockPos position, BlockState state)
    {
        if (!level.getBlockState(position).equals(state))
        {
            level.setBlock(position, state, UPDATE_CLIENTS);
        }
    }

    public record OperationsAudit(boolean valid, boolean entrance,
                                  boolean tacticalTable, boolean display,
                                  boolean stairs, int consoles,
                                  int transitLinks, boolean connectedRoutes,
                                  boolean facilityLinks,
                                  boolean videoWall, boolean safeAnnex,
                                  int telemetryScreens,
                                  NervOperationsConsole.ConsoleAudit commandConsole)
    {
        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s entrance=%s tacticalTable=%s display=%s stairs=%s "
                            + "consoles=%d/3 transit=%d/3 connectedRoutes=%s "
                            + "facilityLinks=%s videoWall=%s safeAnnex=%s",
                    this.valid, this.entrance, this.tacticalTable, this.display,
                    this.stairs, this.consoles, this.transitLinks,
                    this.connectedRoutes, this.facilityLinks,
                    this.videoWall, this.safeAnnex)
                    + String.format(Locale.ROOT, " telemetry=%d/%d",
                    this.telemetryScreens, NervCommandTelemetry.SCREEN_COUNT)
                    + " commandConsole={" + this.commandConsole.summary() + "}";
        }
    }
}
