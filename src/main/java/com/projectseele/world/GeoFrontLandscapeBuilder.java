package com.projectseele.world;

import java.util.Locale;

import com.projectseele.registry.ModFluids;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LadderBlock;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Adds the inhabited landscape between the NERV pyramid and the cavern wall.
 *
 * <p>The builder intentionally owns only the outer GeoFront ring.  The centre
 * pyramid, operations centre, command bridge and the three continuous EVA
 * shafts remain owned by their dedicated builders.  This makes the landscape
 * safe to rebuild without damaging an active sortie route.</p>
 */
public final class GeoFrontLandscapeBuilder
{
    private static final int SHORE_INNER_RADIUS = 73;
    private static final int SHORE_OUTER_RADIUS = 78;
    private static final int SERVICE_ROAD_INNER_RADIUS = 176;
    private static final int SERVICE_ROAD_OUTER_RADIUS = 182;
    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;

    private static final BlockPos PUMP_CENTRE = new BlockPos(84, 0, 28);
    private static final BlockPos MAINTENANCE_CENTRE = new BlockPos(-78, 0, 52);
    private static final BlockPos[] BLAST_BUNKERS = {
            new BlockPos(-98, 0, -22),
            new BlockPos(98, 0, -22)
    };
    private static final int[][] FOREST_CENTRES = {
            {-185, -130}, {-160, -80}, {-150, -20}, {-135, 55},
            {185, -130}, {160, -80}, {150, -20}, {135, 55},
            {-90, -250}, {0, -270}, {90, -250},
            {-105, 80}, {105, 80}
    };

    private GeoFrontLandscapeBuilder() {}

    public static LandscapeAudit build(ServerLevel level)
    {
        return build(level, IntegratedNervMapBuilder.GEOFRONT_ORIGIN);
    }

    public static LandscapeAudit build(ServerLevel level, BlockPos origin)
    {
        buildLclShore(level, origin);
        buildServiceRoad(level, origin);
        buildDocks(level, origin);
        buildPumpingStation(level, origin);
        buildMaintenanceTerrace(level, origin);
        buildBlastBunkers(level, origin);
        enrichForest(level, origin);
        return inspect(level, origin);
    }

    public static LandscapeAudit inspect(ServerLevel level)
    {
        return inspect(level, IntegratedNervMapBuilder.GEOFRONT_ORIGIN);
    }

    public static LandscapeAudit inspect(ServerLevel level, BlockPos origin)
    {
        boolean shore = level.getBlockState(origin.offset(75, 2, 0))
                .is(Blocks.CHISELED_DEEPSLATE);

        int docks = 0;
        for (int x : new int[] {-55, 55})
        {
            if (level.getBlockState(origin.offset(x, 2, 12))
                    .is(Blocks.SMOOTH_STONE))
            {
                docks++;
            }
        }

        boolean pumpHouse = level.getBlockState(origin.offset(
                PUMP_CENTRE.getX(), 8, PUMP_CENTRE.getZ()))
                .is(Blocks.LODESTONE);
        boolean lclIntake = level.getFluidState(origin.offset(72, 1, 28))
                .getFluidType() == ModFluids.LCL_TYPE.get()
                && level.getFluidState(origin.offset(
                PUMP_CENTRE.getX(), 2, PUMP_CENTRE.getZ()))
                .getFluidType() == ModFluids.LCL_TYPE.get();
        boolean serviceRoad = isServiceRoad(level.getBlockState(
                origin.offset(20, 0, GeoFrontBuilder.CAVERN_CENTRE_Z - 180)));
        boolean maintenance = level.getBlockState(origin.offset(
                MAINTENANCE_CENTRE.getX(), 9, MAINTENANCE_CENTRE.getZ()))
                .is(Blocks.LODESTONE);

        int bunkers = 0;
        for (BlockPos centre : BLAST_BUNKERS)
        {
            if (level.getBlockState(origin.offset(
                    centre.getX(), 7, centre.getZ())).is(Blocks.LODESTONE))
            {
                bunkers++;
            }
        }

        int forestGroves = 0;
        for (int[] centre : FOREST_CENTRES)
        {
            int groundY = forestGroundY(level, origin, centre[0], centre[1]);
            if (level.getBlockState(origin.offset(
                    centre[0], groundY + 1, centre[1]))
                    .is(Blocks.STRIPPED_DARK_OAK_LOG))
            {
                forestGroves++;
            }
        }

        int lclLakeSamples = 0;
        for (int[] sample : new int[][] {
                {60, 0}, {-60, 0}, {-42, -42}, {42, -42}})
        {
            if (level.getFluidState(origin.offset(sample[0], 1, sample[1]))
                    .getFluidType() == ModFluids.LCL_TYPE.get())
            {
                lclLakeSamples++;
            }
        }

        boolean protectedSites = level.getBlockState(origin.offset(
                        0, GeoFrontBuilder.PYRAMID_APEX_Y + 1,
                        GeoFrontBuilder.PYRAMID_CENTRE_Z)).is(Blocks.BEACON)
                && level.getBlockState(origin.offset(0, 2, 70))
                .is(Blocks.IRON_BLOCK);
        for (int x : IntegratedNervMapBuilder.LIFT_X)
        {
            protectedSites &= level.getBlockState(origin.offset(x, 1, -76))
                    .is(Blocks.LODESTONE);
        }

        boolean valid = shore && docks == 2 && pumpHouse && lclIntake
                && serviceRoad && maintenance && bunkers == BLAST_BUNKERS.length
                && forestGroves >= 10 && lclLakeSamples == 4 && protectedSites;
        return new LandscapeAudit(valid, shore, docks, pumpHouse, lclIntake,
                serviceRoad, maintenance, bunkers, forestGroves,
                lclLakeSamples, protectedSites);
    }

    /** Raised retaining wall and a dry promenade around the five-block lake. */
    private static void buildLclShore(ServerLevel level, BlockPos origin)
    {
        int innerSqr = SHORE_INNER_RADIUS * SHORE_INNER_RADIUS;
        int outerSqr = SHORE_OUTER_RADIUS * SHORE_OUTER_RADIUS;
        for (int x = -SHORE_OUTER_RADIUS; x <= SHORE_OUTER_RADIUS; x++)
        {
            for (int z = -SHORE_OUTER_RADIUS; z <= SHORE_OUTER_RADIUS; z++)
            {
                int distanceSqr = x * x + z * z;
                if (distanceSqr < innerSqr || distanceSqr > outerSqr
                        || isProtected(x, z))
                {
                    continue;
                }

                double distance = Math.sqrt(distanceSqr);
                if (distance < SHORE_INNER_RADIUS + 1.6D)
                {
                    for (int y = -3; y <= 1; y++)
                    {
                        set(level, origin.offset(x, y, z), y == 1
                                ? Blocks.POLISHED_BASALT.defaultBlockState()
                                : Blocks.DEEPSLATE_BRICKS.defaultBlockState());
                    }
                }

                BlockState deck = Math.floorMod(x * 11 + z * 17, 19) == 0
                        ? Blocks.CHISELED_DEEPSLATE.defaultBlockState()
                        : Blocks.POLISHED_DEEPSLATE.defaultBlockState();
                set(level, origin.offset(x, 2, z), deck);
                clear(level, origin.offset(x, 3, z));
                clear(level, origin.offset(x, 4, z));

                if (distance > SHORE_OUTER_RADIUS - 0.8D
                        && Math.floorMod(x * 5 + z * 7, 11) == 0)
                {
                    set(level, origin.offset(x, 3, z),
                            Blocks.IRON_BARS.defaultBlockState());
                    set(level, origin.offset(x, 4, z),
                            Blocks.SEA_LANTERN.defaultBlockState());
                }
            }
        }

        // Stable signature kept outside every reserved route.
        set(level, origin.offset(75, 2, 0),
                Blocks.CHISELED_DEEPSLATE.defaultBlockState());
    }

    private static void buildServiceRoad(ServerLevel level, BlockPos origin)
    {
        int innerSqr = SERVICE_ROAD_INNER_RADIUS * SERVICE_ROAD_INNER_RADIUS;
        int outerSqr = SERVICE_ROAD_OUTER_RADIUS * SERVICE_ROAD_OUTER_RADIUS;
        for (int x = -SERVICE_ROAD_OUTER_RADIUS; x <= SERVICE_ROAD_OUTER_RADIUS; x++)
        {
            for (int centredZ = -SERVICE_ROAD_OUTER_RADIUS;
                 centredZ <= SERVICE_ROAD_OUTER_RADIUS; centredZ++)
            {
                int z = GeoFrontBuilder.CAVERN_CENTRE_Z + centredZ;
                int distanceSqr = x * x + centredZ * centredZ;
                if (distanceSqr < innerSqr || distanceSqr > outerSqr
                        || isProtected(x, z))
                {
                    continue;
                }
                BlockState road = Math.floorMod(x + z, 9) == 0
                        ? Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState()
                        : Blocks.BLACK_CONCRETE.defaultBlockState();
                set(level, origin.offset(x, 0, z), road);
                clearHeadroom(level, origin.offset(x, 1, z), 4);
            }
        }

        buildRoadSpur(level, origin, 75, 96, 25, 31);
        buildRoadSpur(level, origin, -94, -67, 49, 55);
    }

    private static void buildRoadSpur(ServerLevel level, BlockPos origin,
                                      int minX, int maxX, int minZ, int maxZ)
    {
        for (int x = minX; x <= maxX; x++)
        {
            for (int z = minZ; z <= maxZ; z++)
            {
                if (isProtected(x, z))
                {
                    continue;
                }
                boolean edge = x == minX || x == maxX || z == minZ || z == maxZ;
                set(level, origin.offset(x, 0, z), edge
                        ? Blocks.YELLOW_CONCRETE.defaultBlockState()
                        : Blocks.BLACK_CONCRETE.defaultBlockState());
                clearHeadroom(level, origin.offset(x, 1, z), 4);
            }
        }
    }

    private static void buildDocks(ServerLevel level, BlockPos origin)
    {
        buildDock(level, origin, 1);
        buildDock(level, origin, -1);
    }

    private static void buildDock(ServerLevel level, BlockPos origin, int side)
    {
        for (int distance = 52; distance <= 77; distance++)
        {
            int x = side * distance;
            for (int z = 10; z <= 14; z++)
            {
                set(level, origin.offset(x, 2, z),
                        Blocks.SMOOTH_STONE.defaultBlockState());
                clear(level, origin.offset(x, 3, z));
                clear(level, origin.offset(x, 4, z));
            }
            for (int z : new int[] {9, 15})
            {
                set(level, origin.offset(x, 3, z),
                        distance % 5 == 0 ? Blocks.SEA_LANTERN.defaultBlockState()
                                : Blocks.IRON_BARS.defaultBlockState());
            }
        }
        int endX = side * 52;
        for (int z : new int[] {10, 14})
        {
            for (int y = -2; y <= 2; y++)
            {
                set(level, origin.offset(endX, y, z),
                        Blocks.POLISHED_BASALT.defaultBlockState());
            }
            set(level, origin.offset(endX, 3, z),
                    Blocks.CHAIN.defaultBlockState());
        }
    }

    private static void buildPumpingStation(ServerLevel level, BlockPos origin)
    {
        int centreX = PUMP_CENTRE.getX();
        int centreZ = PUMP_CENTRE.getZ();

        // A covered source channel visibly joins the lake to the pump house.
        for (int x = 55; x <= 77; x++)
        {
            set(level, origin.offset(x, 0, centreZ),
                    Blocks.IRON_BLOCK.defaultBlockState());
            set(level, origin.offset(x, 1, centreZ),
                    ModFluids.LCL_SOURCE.get().defaultFluidState()
                            .createLegacyBlock());
            set(level, origin.offset(x, 1, centreZ - 1),
                    Blocks.POLISHED_DEEPSLATE.defaultBlockState());
            set(level, origin.offset(x, 1, centreZ + 1),
                    Blocks.POLISHED_DEEPSLATE.defaultBlockState());
            set(level, origin.offset(x, 2, centreZ),
                    Blocks.ORANGE_STAINED_GLASS.defaultBlockState());
        }

        for (int x = -8; x <= 8; x++)
        {
            for (int z = -9; z <= 9; z++)
            {
                set(level, origin.offset(centreX + x, 1, centreZ + z),
                        Blocks.POLISHED_DEEPSLATE.defaultBlockState());
                for (int y = 2; y <= 7; y++)
                {
                    clear(level, origin.offset(centreX + x, y, centreZ + z));
                }
                set(level, origin.offset(centreX + x, 8, centreZ + z),
                        Math.floorMod(x + z, 5) == 0
                                ? Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState()
                                : Blocks.GRAY_CONCRETE.defaultBlockState());
            }
        }

        for (int y = 2; y <= 7; y++)
        {
            for (int x = -8; x <= 8; x++)
            {
                setPumpWall(level, origin.offset(centreX + x, y, centreZ - 9),
                        x, y);
                setPumpWall(level, origin.offset(centreX + x, y, centreZ + 9),
                        x, y);
            }
            for (int z = -8; z <= 8; z++)
            {
                setPumpWall(level, origin.offset(centreX - 8, y, centreZ + z),
                        z, y);
                setPumpWall(level, origin.offset(centreX + 8, y, centreZ + z),
                        z, y);
            }
        }

        // The west wall faces the lake and remains a traversable pressure gate.
        for (int y = 2; y <= 5; y++)
        {
            for (int z = -2; z <= 2; z++)
            {
                clear(level, origin.offset(centreX - 8, y, centreZ + z));
            }
        }

        buildLclHeaderTank(level, origin, centreX, centreZ);
        buildPumpMachinery(level, origin, centreX, centreZ);
        set(level, origin.offset(centreX, 8, centreZ),
                Blocks.LODESTONE.defaultBlockState());
    }

    private static void setPumpWall(ServerLevel level, BlockPos position,
                                    int span, int y)
    {
        BlockState wall = y >= 4 && y <= 6 && Math.floorMod(span, 5) <= 1
                ? Blocks.ORANGE_STAINED_GLASS.defaultBlockState()
                : (y == 2 || y == 7
                ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                : Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
        set(level, position, wall);
    }

    private static void buildLclHeaderTank(ServerLevel level, BlockPos origin,
                                           int centreX, int centreZ)
    {
        for (int x = -2; x <= 2; x++)
        {
            for (int z = -2; z <= 2; z++)
            {
                set(level, origin.offset(centreX + x, 1, centreZ + z),
                        Blocks.ORANGE_CONCRETE.defaultBlockState());
                if (Math.abs(x) == 2 || Math.abs(z) == 2)
                {
                    set(level, origin.offset(centreX + x, 2, centreZ + z),
                            Blocks.ORANGE_STAINED_GLASS.defaultBlockState());
                    set(level, origin.offset(centreX + x, 3, centreZ + z),
                            Blocks.IRON_BARS.defaultBlockState());
                }
                else
                {
                    set(level, origin.offset(centreX + x, 2, centreZ + z),
                            ModFluids.LCL_SOURCE.get().defaultFluidState()
                                    .createLegacyBlock());
                }
            }
        }
    }

    private static void buildPumpMachinery(ServerLevel level, BlockPos origin,
                                           int centreX, int centreZ)
    {
        for (int z : new int[] {-6, 6})
        {
            for (int x = -5; x <= 5; x += 5)
            {
                set(level, origin.offset(centreX + x, 2, centreZ + z),
                        Blocks.PISTON.defaultBlockState());
                set(level, origin.offset(centreX + x, 3, centreZ + z),
                        Blocks.OBSERVER.defaultBlockState());
                set(level, origin.offset(centreX + x, 4, centreZ + z),
                        Blocks.IRON_BLOCK.defaultBlockState());
            }
        }
    }

    private static void buildMaintenanceTerrace(ServerLevel level, BlockPos origin)
    {
        int centreX = MAINTENANCE_CENTRE.getX();
        int centreZ = MAINTENANCE_CENTRE.getZ();
        for (int x = -9; x <= 9; x++)
        {
            for (int z = -7; z <= 7; z++)
            {
                set(level, origin.offset(centreX + x, 1, centreZ + z),
                        Math.floorMod(x + z, 6) == 0
                                ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                                : Blocks.SMOOTH_STONE.defaultBlockState());
                clear(level, origin.offset(centreX + x, 2, centreZ + z));
                clear(level, origin.offset(centreX + x, 3, centreZ + z));
            }
        }

        for (int x : new int[] {-9, 9})
        {
            for (int z = -7; z <= 7; z++)
            {
                set(level, origin.offset(centreX + x, 2, centreZ + z),
                        Blocks.IRON_BARS.defaultBlockState());
            }
        }
        for (int z : new int[] {-7, 7})
        {
            for (int x = -9; x <= 9; x++)
            {
                set(level, origin.offset(centreX + x, 2, centreZ + z),
                        Blocks.IRON_BARS.defaultBlockState());
            }
        }

        // Four narrow pylons support an elevated cavern observation deck.
        for (int x : new int[] {-6, 6})
        {
            for (int z : new int[] {-4, 4})
            {
                for (int y = 2; y <= 9; y++)
                {
                    set(level, origin.offset(centreX + x, y, centreZ + z),
                            Blocks.IRON_BLOCK.defaultBlockState());
                }
            }
        }
        for (int x = -7; x <= 7; x++)
        {
            for (int z = -5; z <= 5; z++)
            {
                set(level, origin.offset(centreX + x, 9, centreZ + z),
                        Blocks.POLISHED_BLACKSTONE_BRICKS.defaultBlockState());
            }
        }
        for (int y = 2; y <= 9; y++)
        {
            set(level, origin.offset(centreX - 7, y, centreZ - 4),
                    Blocks.LADDER.defaultBlockState()
                            .setValue(LadderBlock.FACING, Direction.WEST));
        }
        for (int x = -7; x <= 7; x++)
        {
            set(level, origin.offset(centreX + x, 10, centreZ - 5),
                    Blocks.IRON_BARS.defaultBlockState());
            set(level, origin.offset(centreX + x, 10, centreZ + 5),
                    Blocks.IRON_BARS.defaultBlockState());
        }
        set(level, origin.offset(centreX, 9, centreZ),
                Blocks.LODESTONE.defaultBlockState());
    }

    private static void buildBlastBunkers(ServerLevel level, BlockPos origin)
    {
        for (BlockPos centre : BLAST_BUNKERS)
        {
            buildBlastBunker(level, origin, centre);
        }
    }

    private static void buildBlastBunker(ServerLevel level, BlockPos origin,
                                         BlockPos centre)
    {
        int inward = centre.getX() < 0 ? 1 : -1;
        for (int x = -7; x <= 7; x++)
        {
            for (int z = -5; z <= 5; z++)
            {
                set(level, origin.offset(centre.getX() + x, 1,
                                centre.getZ() + z),
                        Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
                for (int y = 2; y <= 6; y++)
                {
                    clear(level, origin.offset(centre.getX() + x, y,
                            centre.getZ() + z));
                }
                set(level, origin.offset(centre.getX() + x, 7,
                                centre.getZ() + z),
                        Blocks.BLACK_CONCRETE.defaultBlockState());
            }
        }
        for (int y = 2; y <= 6; y++)
        {
            for (int x = -7; x <= 7; x++)
            {
                set(level, origin.offset(centre.getX() + x, y,
                                centre.getZ() - 5),
                        y == 4 && Math.floorMod(x, 4) == 0
                                ? Blocks.RED_STAINED_GLASS.defaultBlockState()
                                : Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
                set(level, origin.offset(centre.getX() + x, y,
                                centre.getZ() + 5),
                        Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
            }
            for (int z = -4; z <= 4; z++)
            {
                set(level, origin.offset(centre.getX() - 7, y,
                                centre.getZ() + z),
                        Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
                set(level, origin.offset(centre.getX() + 7, y,
                                centre.getZ() + z),
                        Blocks.REINFORCED_DEEPSLATE.defaultBlockState());
            }
        }

        int entranceX = centre.getX() + inward * 7;
        for (int y = 2; y <= 5; y++)
        {
            for (int z = -2; z <= 2; z++)
            {
                clear(level, origin.offset(entranceX, y, centre.getZ() + z));
            }
        }
        for (int z = -4; z <= 4; z++)
        {
            set(level, origin.offset(centre.getX(), 2, centre.getZ() + z),
                    z % 2 == 0 ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                            : Blocks.IRON_BLOCK.defaultBlockState());
        }
        set(level, origin.offset(centre.getX(), 7, centre.getZ()),
                Blocks.LODESTONE.defaultBlockState());
    }

    private static void enrichForest(ServerLevel level, BlockPos origin)
    {
        for (int index = 0; index < FOREST_CENTRES.length; index++)
        {
            int x = FOREST_CENTRES[index][0];
            int z = FOREST_CENTRES[index][1];
            if (isProtected(x, z) || inServiceRoad(x, z))
            {
                continue;
            }
            buildTreeGrove(level, origin, x, z, 6 + Math.floorMod(index, 4));
        }
    }

    private static void buildTreeGrove(ServerLevel level, BlockPos origin,
                                       int centreX, int centreZ, int height)
    {
        int groundY = forestGroundY(level, origin, centreX, centreZ);
        for (int x = -3; x <= 3; x++)
        {
            for (int z = -3; z <= 3; z++)
            {
                if (x * x + z * z <= 10)
                {
                    set(level, origin.offset(centreX + x, groundY, centreZ + z),
                            Math.floorMod(x * 3 + z * 5, 7) == 0
                                    ? Blocks.MOSS_BLOCK.defaultBlockState()
                                    : Blocks.GRASS_BLOCK.defaultBlockState());
                }
            }
        }
        for (int y = 1; y <= height; y++)
        {
            set(level, origin.offset(centreX, groundY + y, centreZ),
                    Blocks.STRIPPED_DARK_OAK_LOG.defaultBlockState());
            if (y <= 3)
            {
                set(level, origin.offset(centreX + 1, groundY + y, centreZ),
                        Blocks.DARK_OAK_LOG.defaultBlockState());
            }
        }
        for (int x = -3; x <= 3; x++)
        {
                for (int y = -2; y <= 2; y++)
            {
                for (int z = -3; z <= 3; z++)
                {
                    if (x * x + y * y + z * z <= 11)
                    {
                    set(level, origin.offset(centreX + x,
                                    groundY + height + y,
                                        centreZ + z),
                                Math.floorMod(x * 7 + y * 11 + z * 13, 9) == 0
                                        ? Blocks.FLOWERING_AZALEA_LEAVES.defaultBlockState()
                                        : Blocks.AZALEA_LEAVES.defaultBlockState());
                    }
                }
            }
        }
        set(level, origin.offset(centreX, groundY + height + 1, centreZ),
                Blocks.DARK_OAK_LOG.defaultBlockState());
    }

    private static int forestGroundY(ServerLevel level, BlockPos origin,
                                     int x, int z)
    {
        for (int y = 4; y >= -4; y--)
        {
            BlockState state = level.getBlockState(origin.offset(x, y, z));
            if (state.is(Blocks.GRASS_BLOCK) || state.is(Blocks.MOSS_BLOCK)
                    || state.is(Blocks.DIRT) || state.is(Blocks.STONE))
            {
                return y;
            }
        }
        return 0;
    }

    /** Hard exclusions shared by every surface pass in this builder. */
    private static boolean isProtected(int x, int z)
    {
        if (Math.abs(x) <= 45 && z >= -170 && z <= -34)
        {
            return true;
        }
        if (GeoFrontBuilder.isWithinPyramidServiceApron(x, z)
                || GeoFrontBuilder.isWithinPyramidPublicAccess(x, z))
        {
            return true;
        }
        if (Math.abs(x) <= 40 && Math.abs(z) <= 40)
        {
            return true;
        }
        if (Math.abs(x) <= 10 && z >= 30)
        {
            return true;
        }
        if (Math.abs(x) <= 12 && z >= 88)
        {
            return true;
        }
        if (Math.abs(x) <= 6 && z <= -98)
        {
            return true;
        }
        for (int liftX : IntegratedNervMapBuilder.LIFT_X)
        {
            if (Math.abs(x - liftX) <= 9 && z >= -86 && z <= -34)
            {
                return true;
            }
        }
        return false;
    }

    private static boolean inServiceRoad(int x, int z)
    {
        int centredZ = z - GeoFrontBuilder.CAVERN_CENTRE_Z;
        int distanceSqr = x * x + centredZ * centredZ;
        return distanceSqr >= SERVICE_ROAD_INNER_RADIUS * SERVICE_ROAD_INNER_RADIUS
                && distanceSqr <= SERVICE_ROAD_OUTER_RADIUS * SERVICE_ROAD_OUTER_RADIUS;
    }

    private static boolean isServiceRoad(BlockState state)
    {
        return state.is(Blocks.BLACK_CONCRETE)
                || state.is(Blocks.LIGHT_GRAY_CONCRETE)
                || state.is(Blocks.YELLOW_CONCRETE);
    }

    private static void clearHeadroom(ServerLevel level, BlockPos feet, int height)
    {
        for (int y = 0; y < height; y++)
        {
            clear(level, feet.above(y));
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

    public record LandscapeAudit(boolean valid, boolean shore, int docks,
                                 boolean pumpHouse, boolean lclIntake,
                                 boolean serviceRoad, boolean maintenance,
                                 int bunkers, int forestGroves,
                                 int lclLakeSamples, boolean protectedSites)
    {
        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s shore=%s docks=%d/2 pumpHouse=%s lclIntake=%s "
                            + "serviceRoad=%s maintenance=%s bunkers=%d/2 "
                            + "forestGroves=%d/%d lclLake=%d/4 protectedSites=%s",
                    this.valid, this.shore, this.docks, this.pumpHouse,
                    this.lclIntake, this.serviceRoad, this.maintenance,
                    this.bunkers, this.forestGroves, FOREST_CENTRES.length,
                    this.lclLakeSamples, this.protectedSites);
        }
    }
}
