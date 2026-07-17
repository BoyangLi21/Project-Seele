package com.projectseele.world;

import java.util.Locale;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LeavesBlock;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Builds the terrain and civil infrastructure around the compact Tokyo-3
 * district. The mountain basin is deliberately a walkable shell supported by
 * visible retaining strata rather than a solid 400-block-wide stone volume.
 *
 * <p>Call this after {@link ThirdTokyoSurfaceBuilder#buildDistrict} and before
 * the continuous lift shafts are cut by {@link IntegratedNervMapBuilder}.</p>
 */
public final class Tokyo3LandscapeBuilder
{
    public static final int CITY_PLATFORM_HALF_SIZE = 120;
    public static final int OUTER_TERRAIN_RADIUS = 225;
    public static final int RETAINING_DEPTH = 24;
    public static final int HIGHWAY_Z = -132;
    public static final int HIGHWAY_DECK_Y = 22;
    public static final int RAIL_X = 132;
    public static final int RAIL_DECK_Y = 12;
    public static final int ESTIMATED_MAX_BLOCK_WRITES = 225_000;

    private static final int DEEP_GRID_HALF_SIZE = 104;
    private static final int PERIMETER_DEFENCE_RADIUS = 210;
    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;
    private static final int[] LIFT_X = {-28, 0, 28};
    private static final int[][] RIDGE_AUDIT_POINTS = {
            {0, -205}, {205, 0}, {0, 205}, {-205, 0},
    };

    private Tokyo3LandscapeBuilder() {}

    public static LandscapeAudit build(ServerLevel level)
    {
        return build(level, IntegratedNervMapBuilder.TOKYO3_ORIGIN);
    }

    public static LandscapeAudit build(ServerLevel level, BlockPos origin)
    {
        requireBuildHeight(level, origin);
        buildRetainingStructure(level, origin);
        buildOuterTerrainShell(level, origin);
        buildPerimeterDefences(level, origin);
        buildElevatedExpressway(level, origin);
        buildRailwayAndStation(level, origin);
        buildLaunchSafetyDistrict(level, origin);
        buildMunicipalFacilities(level, origin);
        plantMountainForest(level, origin);
        return inspect(level, origin);
    }

    public static LandscapeAudit inspect(ServerLevel level)
    {
        return inspect(level, IntegratedNervMapBuilder.TOKYO3_ORIGIN);
    }

    public static LandscapeAudit inspect(ServerLevel level, BlockPos origin)
    {
        boolean retainingWall = isRetainingMaterial(level.getBlockState(
                origin.offset(CITY_PLATFORM_HALF_SIZE, -12, 72)));
        boolean underDeck = isStructuralMaterial(level.getBlockState(
                origin.offset(80, -1, 80)));
        boolean deepGrid = isStructuralMaterial(level.getBlockState(
                origin.offset(96, -RETAINING_DEPTH, 80)));

        int ridgePoints = 0;
        for (int[] point : RIDGE_AUDIT_POINTS)
        {
            int y = terrainHeight(point[0], point[1]);
            if (isTerrainSurface(level.getBlockState(
                    origin.offset(point[0], y, point[1]))))
            {
                ridgePoints++;
            }
        }

        boolean highway = isRoadSurface(level.getBlockState(
                origin.offset(0, HIGHWAY_DECK_Y, HIGHWAY_Z)));
        boolean westPortal = level.getBlockState(origin.offset(-164,
                HIGHWAY_DECK_Y + 8, HIGHWAY_Z)).is(Blocks.ORANGE_CONCRETE);
        boolean eastPortal = level.getBlockState(origin.offset(164,
                HIGHWAY_DECK_Y + 8, HIGHWAY_Z)).is(Blocks.ORANGE_CONCRETE);
        boolean railway = level.getBlockState(origin.offset(
                RAIL_X - 3, RAIL_DECK_Y + 1, 0)).is(Blocks.RAIL)
                || level.getBlockState(origin.offset(
                        RAIL_X - 3, RAIL_DECK_Y + 1, 0)).is(Blocks.POWERED_RAIL);
        boolean station = level.getBlockState(origin.offset(
                RAIL_X, RAIL_DECK_Y + 1, 0)).is(Blocks.LODESTONE);

        int safetyZones = 0;
        for (int liftX : LIFT_X)
        {
            BlockState marker = level.getBlockState(origin.offset(liftX, 0, 12));
            if (marker.is(Blocks.YELLOW_CONCRETE)
                    || marker.is(Blocks.BLACK_CONCRETE))
            {
                safetyZones++;
            }
        }
        boolean shaftHeadroom = shaftHeadroomClear(level, origin);
        boolean rescueCentre = level.getBlockState(origin.offset(
                -136, terrainHeight(-136, 58) + 1, 58)).is(Blocks.BEACON);

        boolean valid = retainingWall && underDeck && deepGrid
                && ridgePoints == RIDGE_AUDIT_POINTS.length
                && highway && westPortal && eastPortal && railway && station
                && safetyZones == LIFT_X.length && shaftHeadroom
                && rescueCentre;
        return new LandscapeAudit(valid, retainingWall, underDeck, deepGrid,
                ridgePoints, highway, westPortal, eastPortal, railway,
                station, safetyZones, shaftHeadroom, rescueCentre);
    }

    private static void buildRetainingStructure(ServerLevel level, BlockPos origin)
    {
        for (int depth = 1; depth <= RETAINING_DEPTH; depth++)
        {
            BlockState state = retainingState(depth);
            for (int span = -CITY_PLATFORM_HALF_SIZE;
                 span <= CITY_PLATFORM_HALF_SIZE; span++)
            {
                set(level, origin.offset(-CITY_PLATFORM_HALF_SIZE, -depth, span), state);
                set(level, origin.offset(CITY_PLATFORM_HALF_SIZE, -depth, span), state);
                set(level, origin.offset(span, -depth, -CITY_PLATFORM_HALF_SIZE), state);
                set(level, origin.offset(span, -depth, CITY_PLATFORM_HALF_SIZE), state);
            }
        }

        // A sparse under-deck lattice reads as a real engineered platform but
        // avoids another complete 241 x 241 layer.
        BlockState beam = Blocks.POLISHED_DEEPSLATE.defaultBlockState();
        for (int axis = -112; axis <= 112; axis += 16)
        {
            for (int span = -116; span <= 116; span++)
            {
                setUnlessShaft(level, origin, axis, -1, span, beam);
                setUnlessShaft(level, origin, span, -1, axis, beam);
            }
        }

        buildSquareContour(level, origin, 112, -8,
                Blocks.POLISHED_BASALT.defaultBlockState());
        buildSquareContour(level, origin, 108, -16,
                Blocks.CHISELED_DEEPSLATE.defaultBlockState());

        // The lower service shelf is a grid, not an expensive solid slab.
        for (int x = -DEEP_GRID_HALF_SIZE; x <= DEEP_GRID_HALF_SIZE; x++)
        {
            for (int z = -DEEP_GRID_HALF_SIZE; z <= DEEP_GRID_HALF_SIZE; z++)
            {
                if (Math.floorMod(x, 16) > 1 && Math.floorMod(z, 16) > 1)
                {
                    continue;
                }
                BlockState state = (x + z) % 32 == 0
                        ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                        : Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
                setUnlessShaft(level, origin, x, -RETAINING_DEPTH, z, state);
            }
        }

        for (int x = -96; x <= 96; x += 32)
        {
            for (int z = -96; z <= 96; z += 32)
            {
                buildSupportColumn(level, origin, x, z);
            }
        }
    }

    private static void buildSquareContour(ServerLevel level, BlockPos origin,
                                           int halfSize, int y,
                                           BlockState state)
    {
        for (int inset = 0; inset <= 1; inset++)
        {
            int edge = halfSize - inset;
            for (int span = -edge; span <= edge; span++)
            {
                setUnlessShaft(level, origin, -edge, y, span, state);
                setUnlessShaft(level, origin, edge, y, span, state);
                setUnlessShaft(level, origin, span, y, -edge, state);
                setUnlessShaft(level, origin, span, y, edge, state);
            }
        }
    }

    private static void buildSupportColumn(ServerLevel level, BlockPos origin,
                                           int centreX, int centreZ)
    {
        for (int y = -RETAINING_DEPTH + 1; y <= -2; y++)
        {
            BlockState state = y % 8 == 0
                    ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                    : Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
            for (int x = -1; x <= 1; x++)
            {
                for (int z = -1; z <= 1; z++)
                {
                    setUnlessShaft(level, origin, centreX + x, y,
                            centreZ + z, state);
                }
            }
        }
    }

    private static void buildOuterTerrainShell(ServerLevel level, BlockPos origin)
    {
        int radiusSquared = OUTER_TERRAIN_RADIUS * OUTER_TERRAIN_RADIUS;
        for (int x = -OUTER_TERRAIN_RADIUS; x <= OUTER_TERRAIN_RADIUS; x++)
        {
            for (int z = -OUTER_TERRAIN_RADIUS; z <= OUTER_TERRAIN_RADIUS; z++)
            {
                if (x * x + z * z > radiusSquared
                        || Math.max(Math.abs(x), Math.abs(z))
                                <= CITY_PLATFORM_HALF_SIZE)
                {
                    continue;
                }
                int y = terrainHeight(x, z);
                set(level, origin.offset(x, y, z), terrainSurface(x, y, z));
            }
        }

        // A sampled rock skirt closes the outer silhouette without filling the
        // mountain mass.
        for (int step = 0; step < 720; step++)
        {
            double angle = Math.PI * 2.0 * step / 720.0;
            int x = (int) Math.round(Math.cos(angle) * (OUTER_TERRAIN_RADIUS - 1));
            int z = (int) Math.round(Math.sin(angle) * (OUTER_TERRAIN_RADIUS - 1));
            int top = terrainHeight(x, z) - 1;
            for (int y = -12; y <= top; y++)
            {
                set(level, origin.offset(x, y, z), strataState(y, x, z));
            }
        }
    }

    private static void buildPerimeterDefences(ServerLevel level, BlockPos origin)
    {
        for (int step = 0; step < 720; step++)
        {
            double angle = Math.PI * 2.0 * step / 720.0;
            int x = (int) Math.round(Math.cos(angle) * PERIMETER_DEFENCE_RADIUS);
            int z = (int) Math.round(Math.sin(angle) * PERIMETER_DEFENCE_RADIUS);
            if (defenceOpening(x, z))
            {
                continue;
            }
            int ground = terrainHeight(x, z);
            for (int y = 1; y <= 4; y++)
            {
                BlockState state = y == 4 && step % 8 < 4
                        ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                        : Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
                set(level, origin.offset(x, ground + y, z), state);
            }
            if (step % 60 == 0)
            {
                buildDefencePylon(level, origin.offset(x, ground + 1, z));
            }
        }
    }

    private static void buildDefencePylon(ServerLevel level, BlockPos base)
    {
        for (int y = 0; y <= 12; y++)
        {
            BlockState state = y == 8 || y == 12
                    ? Blocks.REDSTONE_LAMP.defaultBlockState()
                    : Blocks.IRON_BLOCK.defaultBlockState();
            set(level, base.above(y), state);
        }
        for (int x = -2; x <= 2; x++)
        {
            set(level, base.offset(x, 9, 0), Blocks.IRON_BARS.defaultBlockState());
        }
    }

    private static void buildElevatedExpressway(ServerLevel level, BlockPos origin)
    {
        for (int x = -184; x <= 184; x++)
        {
            for (int z = -5; z <= 5; z++)
            {
                BlockState deck = Math.abs(z) == 5
                        ? Blocks.POLISHED_DEEPSLATE.defaultBlockState()
                        : Blocks.SMOOTH_STONE.defaultBlockState();
                BlockState road = z == 0
                        ? Blocks.YELLOW_CONCRETE.defaultBlockState()
                        : Math.abs(z) == 4
                                ? Blocks.GRAY_CONCRETE.defaultBlockState()
                                : Blocks.BLACK_CONCRETE.defaultBlockState();
                set(level, origin.offset(x, HIGHWAY_DECK_Y - 1,
                        HIGHWAY_Z + z), deck);
                set(level, origin.offset(x, HIGHWAY_DECK_Y,
                        HIGHWAY_Z + z), road);
            }
            set(level, origin.offset(x, HIGHWAY_DECK_Y + 1, HIGHWAY_Z - 6),
                    Blocks.IRON_BARS.defaultBlockState());
            set(level, origin.offset(x, HIGHWAY_DECK_Y + 1, HIGHWAY_Z + 6),
                    Blocks.IRON_BARS.defaultBlockState());
        }

        for (int x = -168; x <= 168; x += 24)
        {
            if (Math.abs(x - RAIL_X) <= 10)
            {
                continue;
            }
            int ground = terrainHeight(x, HIGHWAY_Z);
            for (int y = ground + 1; y < HIGHWAY_DECK_Y - 1; y++)
            {
                for (int dx = -1; dx <= 1; dx++)
                {
                    for (int dz = -1; dz <= 1; dz++)
                    {
                        set(level, origin.offset(x + dx, y,
                                HIGHWAY_Z + dz), Blocks.IRON_BLOCK.defaultBlockState());
                    }
                }
            }
        }

        buildHighwayTunnel(level, origin, -1);
        buildHighwayTunnel(level, origin, 1);
        buildHighwayLighting(level, origin);
    }

    private static void buildHighwayTunnel(ServerLevel level, BlockPos origin,
                                           int direction)
    {
        int start = direction < 0 ? -184 : 164;
        int end = direction < 0 ? -164 : 184;
        int minimum = Math.min(start, end);
        int maximum = Math.max(start, end);
        for (int x = minimum; x <= maximum; x++)
        {
            for (int z = -6; z <= 6; z++)
            {
                for (int y = 1; y <= 7; y++)
                {
                    BlockPos position = origin.offset(x, HIGHWAY_DECK_Y + y,
                            HIGHWAY_Z + z);
                    if (Math.abs(z) == 6 || y == 7)
                    {
                        set(level, position,
                                Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
                    }
                    else
                    {
                        clear(level, position);
                    }
                }
            }
        }

        int portalX = direction < 0 ? -164 : 164;
        for (int z = -7; z <= 7; z++)
        {
            set(level, origin.offset(portalX, HIGHWAY_DECK_Y + 8,
                    HIGHWAY_Z + z), Blocks.ORANGE_CONCRETE.defaultBlockState());
        }
        for (int y = 1; y <= 8; y++)
        {
            set(level, origin.offset(portalX, HIGHWAY_DECK_Y + y,
                    HIGHWAY_Z - 7), Blocks.ORANGE_CONCRETE.defaultBlockState());
            set(level, origin.offset(portalX, HIGHWAY_DECK_Y + y,
                    HIGHWAY_Z + 7), Blocks.ORANGE_CONCRETE.defaultBlockState());
        }
    }

    private static void buildHighwayLighting(ServerLevel level, BlockPos origin)
    {
        for (int x = -156; x <= 156; x += 24)
        {
            for (int side : new int[] {-7, 7})
            {
                for (int y = 1; y <= 6; y++)
                {
                    set(level, origin.offset(x, HIGHWAY_DECK_Y + y,
                            HIGHWAY_Z + side), Blocks.IRON_BARS.defaultBlockState());
                }
                set(level, origin.offset(x, HIGHWAY_DECK_Y + 6,
                        HIGHWAY_Z + side), Blocks.SEA_LANTERN.defaultBlockState());
            }
        }
    }

    private static void buildRailwayAndStation(ServerLevel level, BlockPos origin)
    {
        for (int z = -184; z <= 184; z++)
        {
            for (int x = -6; x <= 6; x++)
            {
                set(level, origin.offset(RAIL_X + x, RAIL_DECK_Y, z),
                        Math.abs(x) >= 5
                                ? Blocks.POLISHED_DEEPSLATE.defaultBlockState()
                                : Blocks.SMOOTH_STONE.defaultBlockState());
                for (int y = RAIL_DECK_Y + 1; y <= RAIL_DECK_Y + 7; y++)
                {
                    clear(level, origin.offset(RAIL_X + x, y, z));
                }
            }

            for (int trackX : new int[] {RAIL_X - 3, RAIL_X + 3})
            {
                BlockState rail = Math.floorMod(z, 16) == 0
                        ? Blocks.POWERED_RAIL.defaultBlockState()
                        : Blocks.RAIL.defaultBlockState();
                if (rail.is(Blocks.POWERED_RAIL))
                {
                    set(level, origin.offset(trackX, RAIL_DECK_Y, z),
                            Blocks.REDSTONE_BLOCK.defaultBlockState());
                }
                set(level, origin.offset(trackX, RAIL_DECK_Y + 1, z), rail);
            }

            int terrain = terrainHeight(RAIL_X, z);
            if (terrain > RAIL_DECK_Y + 1)
            {
                int wallTop = Math.min(terrain + 1, RAIL_DECK_Y + 8);
                for (int y = RAIL_DECK_Y + 1; y <= wallTop; y++)
                {
                    set(level, origin.offset(RAIL_X - 7, y, z),
                            Blocks.DEEPSLATE_BRICKS.defaultBlockState());
                    set(level, origin.offset(RAIL_X + 7, y, z),
                            Blocks.DEEPSLATE_BRICKS.defaultBlockState());
                }
                if (terrain >= RAIL_DECK_Y + 7)
                {
                    for (int x = -7; x <= 7; x++)
                    {
                        set(level, origin.offset(RAIL_X + x,
                                RAIL_DECK_Y + 8, z),
                                Blocks.DEEPSLATE_BRICKS.defaultBlockState());
                    }
                }
            }
        }
        buildRailStation(level, origin);
        buildRailPortal(level, origin, -170);
        buildRailPortal(level, origin, 170);
    }

    private static void buildRailStation(ServerLevel level, BlockPos origin)
    {
        for (int z = -28; z <= 28; z++)
        {
            for (int x = -1; x <= 1; x++)
            {
                set(level, origin.offset(RAIL_X + x, RAIL_DECK_Y + 1, z),
                        z % 8 == 0
                                ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                                : Blocks.SMOOTH_QUARTZ.defaultBlockState());
            }
            for (int x : new int[] {-8, 8})
            {
                set(level, origin.offset(RAIL_X + x, RAIL_DECK_Y + 1, z),
                        Blocks.SMOOTH_STONE.defaultBlockState());
                if (Math.floorMod(z, 8) == 0)
                {
                    for (int y = 2; y <= 9; y++)
                    {
                        set(level, origin.offset(RAIL_X + x,
                                RAIL_DECK_Y + y, z),
                                Blocks.IRON_BLOCK.defaultBlockState());
                    }
                }
            }
            for (int x = -9; x <= 9; x++)
            {
                set(level, origin.offset(RAIL_X + x, RAIL_DECK_Y + 10, z),
                        Math.floorMod(x + z, 9) == 0
                                ? Blocks.SEA_LANTERN.defaultBlockState()
                                : Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
            }
        }
        set(level, origin.offset(RAIL_X, RAIL_DECK_Y + 1, 0),
                Blocks.LODESTONE.defaultBlockState());
    }

    private static void buildRailPortal(ServerLevel level, BlockPos origin,
                                        int z)
    {
        for (int x = -8; x <= 8; x++)
        {
            set(level, origin.offset(RAIL_X + x, RAIL_DECK_Y + 9, z),
                    Blocks.ORANGE_CONCRETE.defaultBlockState());
        }
        for (int x : new int[] {-8, 8})
        {
            for (int y = 1; y <= 9; y++)
            {
                set(level, origin.offset(RAIL_X + x, RAIL_DECK_Y + y, z),
                        Blocks.ORANGE_CONCRETE.defaultBlockState());
            }
        }
    }

    private static void buildLaunchSafetyDistrict(ServerLevel level,
                                                  BlockPos origin)
    {
        for (int liftX : LIFT_X)
        {
            buildLaunchSafetyZone(level, origin, liftX);
        }
    }

    private static void buildLaunchSafetyZone(ServerLevel level, BlockPos origin,
                                              int liftX)
    {
        for (int x = -12; x <= 12; x++)
        {
            for (int z = -12; z <= 12; z++)
            {
                int edge = Math.max(Math.abs(x), Math.abs(z));
                if (edge < 10 || edge > 12)
                {
                    continue;
                }
                BlockState warning = Math.floorMod(x + z, 4) < 2
                        ? Blocks.YELLOW_CONCRETE.defaultBlockState()
                        : Blocks.BLACK_CONCRETE.defaultBlockState();
                set(level, origin.offset(liftX + x, 0, z), warning);
            }
        }

        for (int x : new int[] {-12, 12})
        {
            for (int z : new int[] {-12, 12})
            {
                for (int y = 1; y <= 8; y++)
                {
                    set(level, origin.offset(liftX + x, y, z),
                            y == 4 || y == 8
                                    ? Blocks.REDSTONE_LAMP.defaultBlockState()
                                    : Blocks.IRON_BLOCK.defaultBlockState());
                }
            }
        }
        buildLaunchControlBunker(level, origin.offset(liftX, 0, 20));
    }

    private static void buildLaunchControlBunker(ServerLevel level,
                                                 BlockPos centre)
    {
        for (int x = -5; x <= 5; x++)
        {
            for (int z = -3; z <= 3; z++)
            {
                set(level, centre.offset(x, 0, z),
                        Blocks.POLISHED_DEEPSLATE.defaultBlockState());
                set(level, centre.offset(x, 5, z),
                        Blocks.SMOOTH_STONE.defaultBlockState());
                for (int y = 1; y <= 4; y++)
                {
                    if (Math.abs(x) == 5 || Math.abs(z) == 3)
                    {
                        BlockState wall = y == 3 && Math.abs(x) < 4
                                ? Blocks.ORANGE_STAINED_GLASS.defaultBlockState()
                                : Blocks.GRAY_CONCRETE.defaultBlockState();
                        set(level, centre.offset(x, y, z), wall);
                    }
                    else
                    {
                        clear(level, centre.offset(x, y, z));
                    }
                }
            }
        }
        for (int y = 1; y <= 3; y++)
        {
            clear(level, centre.offset(0, y, -3));
        }
        set(level, centre.offset(0, 1, 2), Blocks.REDSTONE_LAMP.defaultBlockState());
    }

    private static void buildMunicipalFacilities(ServerLevel level,
                                                 BlockPos origin)
    {
        int rescueX = -136;
        int rescueZ = 58;
        int ground = terrainHeight(rescueX, rescueZ);
        BlockPos centre = origin.offset(rescueX, ground, rescueZ);
        for (int x = -10; x <= 10; x++)
        {
            for (int z = -7; z <= 7; z++)
            {
                set(level, centre.offset(x, 0, z),
                        Blocks.SMOOTH_STONE.defaultBlockState());
                set(level, centre.offset(x, 7, z),
                        Math.floorMod(x + z, 7) == 0
                                ? Blocks.REDSTONE_LAMP.defaultBlockState()
                                : Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
                for (int y = 1; y <= 6; y++)
                {
                    if (Math.abs(x) == 10 || Math.abs(z) == 7)
                    {
                        BlockState wall = y >= 3 && y <= 5 && z == -7
                                ? Blocks.RED_STAINED_GLASS.defaultBlockState()
                                : Blocks.WHITE_CONCRETE.defaultBlockState();
                        set(level, centre.offset(x, y, z), wall);
                    }
                    else
                    {
                        clear(level, centre.offset(x, y, z));
                    }
                }
            }
        }
        for (int x = -7; x <= 7; x++)
        {
            set(level, centre.offset(x, 0, -8),
                    Math.floorMod(x, 4) < 2
                            ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                            : Blocks.BLACK_CONCRETE.defaultBlockState());
        }
        set(level, centre.above(), Blocks.BEACON.defaultBlockState());

        buildHelipad(level, origin, -150, 96);
    }

    private static void buildHelipad(ServerLevel level, BlockPos origin,
                                     int centreX, int centreZ)
    {
        int ground = terrainHeight(centreX, centreZ) + 1;
        for (int x = -9; x <= 9; x++)
        {
            for (int z = -9; z <= 9; z++)
            {
                int radiusSquared = x * x + z * z;
                if (radiusSquared > 81)
                {
                    continue;
                }
                BlockState state = Math.abs(x) <= 1
                        || (Math.abs(z) <= 1 && Math.abs(x) <= 6)
                                ? Blocks.WHITE_CONCRETE.defaultBlockState()
                                : radiusSquared >= 64
                                        ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                                        : Blocks.GRAY_CONCRETE.defaultBlockState();
                set(level, origin.offset(centreX + x, ground, centreZ + z), state);
            }
        }
    }

    private static void plantMountainForest(ServerLevel level, BlockPos origin)
    {
        for (int x = -198; x <= 198; x += 11)
        {
            for (int z = -198; z <= 198; z += 11)
            {
                if (!insideOuterTerrain(x, z) || transitOrFacilityCorridor(x, z)
                        || Math.floorMod(hash(x, z), 19) != 0)
                {
                    continue;
                }
                int y = terrainHeight(x, z);
                if (y < 8 || y > 34)
                {
                    continue;
                }
                buildConifer(level, origin.offset(x, y + 1, z),
                        5 + Math.floorMod(hash(z, x), 4));
            }
        }
    }

    private static void buildConifer(ServerLevel level, BlockPos base,
                                     int height)
    {
        for (int y = 0; y < height; y++)
        {
            set(level, base.above(y), Blocks.SPRUCE_LOG.defaultBlockState());
        }
        BlockState leaves = Blocks.SPRUCE_LEAVES.defaultBlockState()
                .setValue(LeavesBlock.PERSISTENT, true);
        for (int y = 2; y <= height; y++)
        {
            int radius = y >= height - 1 ? 1 : (height - y) % 3 == 0 ? 3 : 2;
            for (int x = -radius; x <= radius; x++)
            {
                for (int z = -radius; z <= radius; z++)
                {
                    if (Math.abs(x) + Math.abs(z) > radius + 1
                            || x == 0 && z == 0 && y < height)
                    {
                        continue;
                    }
                    set(level, base.offset(x, y, z), leaves);
                }
            }
        }
    }

    private static int terrainHeight(int x, int z)
    {
        int maxAxis = Math.max(Math.abs(x), Math.abs(z));
        double radius = Math.sqrt((double) x * x + (double) z * z);
        if (maxAxis <= CITY_PLATFORM_HALF_SIZE || radius == 0.0)
        {
            return 0;
        }
        double innerRadius = CITY_PLATFORM_HALF_SIZE * radius / maxAxis;
        double span = Math.max(1.0, OUTER_TERRAIN_RADIUS - innerRadius);
        double progress = clamp((radius - innerRadius) / span, 0.0, 1.0);
        double angle = Math.atan2(z, x);
        double ridge = 34.0 * Math.sin(Math.PI * progress) + 6.0 * progress;
        double variation = (Math.sin(angle * 5.0) * 2.6
                + Math.sin(angle * 11.0 + 0.7) * 1.8)
                * Math.sin(Math.PI * progress);
        return Math.max(0, (int) Math.round(ridge + variation));
    }

    private static BlockState terrainSurface(int x, int y, int z)
    {
        int variation = Math.floorMod(hash(x, z), 13);
        if (y >= 35)
        {
            return variation < 4 ? Blocks.SNOW_BLOCK.defaultBlockState()
                    : Blocks.STONE.defaultBlockState();
        }
        if (y >= 20)
        {
            return variation < 4 ? Blocks.ANDESITE.defaultBlockState()
                    : variation == 12 ? Blocks.CALCITE.defaultBlockState()
                            : Blocks.STONE.defaultBlockState();
        }
        if (y <= 7)
        {
            return variation < 3 ? Blocks.COARSE_DIRT.defaultBlockState()
                    : Blocks.GRASS_BLOCK.defaultBlockState();
        }
        return variation < 2 ? Blocks.MOSS_BLOCK.defaultBlockState()
                : variation < 5 ? Blocks.COARSE_DIRT.defaultBlockState()
                        : Blocks.STONE.defaultBlockState();
    }

    private static BlockState strataState(int y, int x, int z)
    {
        if (y % 8 == 0)
        {
            return Blocks.CHISELED_DEEPSLATE.defaultBlockState();
        }
        if (Math.floorMod(x + z + y, 11) == 0)
        {
            return Blocks.TUFF.defaultBlockState();
        }
        return y < -4 ? Blocks.DEEPSLATE.defaultBlockState()
                : Blocks.STONE.defaultBlockState();
    }

    private static BlockState retainingState(int depth)
    {
        // Preserve the six-layer deepslate-brick foundation already owned by
        // ThirdTokyoSurfaceBuilder.  The deeper bands remain visually varied.
        if (depth <= 6)
        {
            return Blocks.DEEPSLATE_BRICKS.defaultBlockState();
        }
        if (depth % 8 == 0)
        {
            return Blocks.ORANGE_CONCRETE.defaultBlockState();
        }
        if (depth % 4 == 0)
        {
            return Blocks.CHISELED_DEEPSLATE.defaultBlockState();
        }
        return Blocks.DEEPSLATE_BRICKS.defaultBlockState();
    }

    private static boolean insideOuterTerrain(int x, int z)
    {
        return Math.max(Math.abs(x), Math.abs(z)) > CITY_PLATFORM_HALF_SIZE
                && x * x + z * z <= OUTER_TERRAIN_RADIUS * OUTER_TERRAIN_RADIUS;
    }

    private static boolean defenceOpening(int x, int z)
    {
        boolean highway = Math.abs(z - HIGHWAY_Z) <= 9 && Math.abs(x) >= 145;
        boolean railway = Math.abs(x - RAIL_X) <= 9 && Math.abs(z) >= 145;
        return highway || railway;
    }

    private static boolean transitOrFacilityCorridor(int x, int z)
    {
        if (Math.abs(z - HIGHWAY_Z) <= 14 || Math.abs(x - RAIL_X) <= 12)
        {
            return true;
        }
        if (Math.abs(x + 136) <= 18 && Math.abs(z - 58) <= 15
                || Math.abs(x + 150) <= 12 && Math.abs(z - 96) <= 12)
        {
            return true;
        }
        for (int liftX : LIFT_X)
        {
            if (Math.abs(x - liftX) <= 16 && Math.abs(z) <= 28)
            {
                return true;
            }
        }
        return false;
    }

    private static boolean shaftHeadroomClear(ServerLevel level, BlockPos origin)
    {
        for (int liftX : LIFT_X)
        {
            for (int y : new int[] {1, 20, 40})
            {
                if (!level.getBlockState(origin.offset(liftX, y, 0)).isAir())
                {
                    return false;
                }
            }
        }
        return true;
    }

    private static boolean isProtectedShaft(int x, int z)
    {
        for (int liftX : LIFT_X)
        {
            if (Math.abs(x - liftX) <= 7 && Math.abs(z) <= 7)
            {
                return true;
            }
        }
        return false;
    }

    private static boolean isRetainingMaterial(BlockState state)
    {
        return state.is(Blocks.DEEPSLATE_BRICKS)
                || state.is(Blocks.CHISELED_DEEPSLATE)
                || state.is(Blocks.ORANGE_CONCRETE);
    }

    private static boolean isStructuralMaterial(BlockState state)
    {
        return state.is(Blocks.POLISHED_DEEPSLATE)
                || state.is(Blocks.REINFORCED_DEEPSLATE)
                || state.is(Blocks.ORANGE_CONCRETE);
    }

    private static boolean isTerrainSurface(BlockState state)
    {
        return state.is(Blocks.GRASS_BLOCK) || state.is(Blocks.COARSE_DIRT)
                || state.is(Blocks.MOSS_BLOCK) || state.is(Blocks.STONE)
                || state.is(Blocks.ANDESITE) || state.is(Blocks.CALCITE)
                || state.is(Blocks.SNOW_BLOCK);
    }

    private static boolean isRoadSurface(BlockState state)
    {
        return state.is(Blocks.BLACK_CONCRETE) || state.is(Blocks.GRAY_CONCRETE)
                || state.is(Blocks.YELLOW_CONCRETE);
    }

    private static int hash(int x, int z)
    {
        return x * 73_428_767 ^ z * 91_293_191 ^ x * z * 31;
    }

    private static double clamp(double value, double minimum, double maximum)
    {
        return Math.max(minimum, Math.min(maximum, value));
    }

    private static void setUnlessShaft(ServerLevel level, BlockPos origin,
                                       int x, int y, int z, BlockState state)
    {
        if (!isProtectedShaft(x, z))
        {
            set(level, origin.offset(x, y, z), state);
        }
    }

    private static void requireBuildHeight(ServerLevel level, BlockPos origin)
    {
        int requiredMin = origin.getY() - RETAINING_DEPTH;
        int requiredMax = origin.getY() + 48;
        if (requiredMin < level.getMinBuildHeight()
                || requiredMax >= level.getMaxBuildHeight())
        {
            throw new IllegalStateException(String.format(Locale.ROOT,
                    "Tokyo-3 landscape requires Y=%d..%d but dimension provides %d..%d",
                    requiredMin, requiredMax, level.getMinBuildHeight(),
                    level.getMaxBuildHeight() - 1));
        }
    }

    private static void clear(ServerLevel level, BlockPos position)
    {
        if (!level.getBlockState(position).isAir())
        {
            set(level, position, Blocks.AIR.defaultBlockState());
        }
    }

    private static void set(ServerLevel level, BlockPos position, BlockState state)
    {
        if (!level.getBlockState(position).equals(state))
        {
            level.setBlock(position, state, UPDATE_CLIENTS);
        }
    }

    public record LandscapeAudit(boolean valid, boolean retainingWall,
                                 boolean underDeck, boolean deepGrid,
                                 int ridgePoints, boolean highway,
                                 boolean westPortal, boolean eastPortal,
                                 boolean railway, boolean station,
                                 int safetyZones, boolean shaftHeadroom,
                                 boolean rescueCentre)
    {
        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s retainingWall=%s underDeck=%s deepGrid=%s "
                            + "ridgePoints=%d/4 highway=%s portals=%s/%s "
                            + "railway=%s station=%s safetyZones=%d/3 "
                            + "shaftHeadroom=%s rescueCentre=%s budget<=%d",
                    this.valid, this.retainingWall, this.underDeck,
                    this.deepGrid, this.ridgePoints, this.highway,
                    this.westPortal, this.eastPortal, this.railway,
                    this.station, this.safetyZones, this.shaftHeadroom,
                    this.rescueCentre, ESTIMATED_MAX_BLOCK_WRITES);
        }
    }
}
