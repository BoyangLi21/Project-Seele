package com.projectseele.world;

import java.util.Locale;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Deterministic original Tokyo-3 surface district around the three NERV bays.
 * The layout is intentionally compact enough for a development world while
 * preserving EVA-scale streets, retractable armour towers and a power grid.
 */
public final class ThirdTokyoSurfaceBuilder
{
    public static final int DISTRICT_HALF_SIZE = 104;
    public static final int FOUNDATION_HALF_SIZE = 120;
    public static final int OBSERVATION_Z = 112;
    public static final int OBSERVATION_Y = 38;

    private static final int ROAD_SPACING = 40;
    private static final int ROAD_OFFSET = 20;
    private static final int ROAD_HALF_WIDTH = 4;
    private static final int SIDEWALK_HALF_WIDTH = 7;
    private static final int LOT_HALF_SIZE = 12;
    private static final int[] LOT_CENTRES = {-80, -40, 0, 40, 80};
    private static final int[][] PYLONS = {
            {-100, -80}, {-100, 0}, {-100, 80},
            {100, -80}, {100, 0}, {100, 80},
    };
    private static final int[][] ROAD_AUDIT_POINTS = {
            {-100, -100}, {-100, 100}, {100, -100}, {100, 100},
            {-60, -100}, {60, 100}, {-100, 60}, {100, -60},
    };
    private static final int EXPECTED_TOWERS = 13;
    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;

    private ThirdTokyoSurfaceBuilder() {}

    public static void buildDistrict(ServerLevel level, BlockPos origin)
    {
        buildFoundation(level, origin);
        buildRoadGrid(level, origin);

        for (int x : LOT_CENTRES)
        {
            for (int z : LOT_CENTRES)
            {
                if (Math.abs(x) <= 40 && Math.abs(z) <= 40)
                {
                    continue;
                }
                BlockPos centre = origin.offset(x, 0, z);
                if ((x == 0 && z == -80) || (x == 80 && z == 0))
                {
                    buildSubstation(level, centre);
                }
                else if (x == 0 && z == 80)
                {
                    buildBattlePlaza(level, centre);
                }
                else
                {
                    buildArmouredTower(level, centre, towerHeight(x, z), x, z);
                }
            }
        }

        for (int[] pylon : PYLONS)
        {
            buildPowerPylon(level, origin.offset(pylon[0], 0, pylon[1]));
        }
        connectPowerGrid(level, origin, -100);
        connectPowerGrid(level, origin, 100);
        buildSortieGate(level, origin.offset(0, 1, 52));
        buildObservationDeck(level, origin.offset(0, 0, OBSERVATION_Z));
    }

    public static DistrictAudit inspect(ServerLevel level, BlockPos origin)
    {
        int roads = 0;
        for (int[] point : ROAD_AUDIT_POINTS)
        {
            if (isRoad(level.getBlockState(origin.offset(point[0], 0, point[1]))))
            {
                roads++;
            }
        }

        int towers = 0;
        for (int x : LOT_CENTRES)
        {
            for (int z : LOT_CENTRES)
            {
                if (Math.abs(x) <= 40 && Math.abs(z) <= 40
                        || (x == 0 && z == -80)
                        || (x == 80 && z == 0)
                        || (x == 0 && z == 80))
                {
                    continue;
                }
                int height = towerHeight(x, z);
                if (level.getBlockState(origin.offset(x, height + 1, z))
                        .is(Blocks.REDSTONE_LAMP))
                {
                    towers++;
                }
            }
        }

        int substations = 0;
        if (level.getBlockState(origin.offset(0, 1, -80)).is(Blocks.COPPER_BLOCK))
        {
            substations++;
        }
        if (level.getBlockState(origin.offset(80, 1, 0)).is(Blocks.COPPER_BLOCK))
        {
            substations++;
        }

        int pylons = 0;
        for (int[] pylon : PYLONS)
        {
            if (level.getBlockState(origin.offset(pylon[0], 28, pylon[1]))
                    .is(Blocks.IRON_BLOCK))
            {
                pylons++;
            }
        }

        boolean battleBeacon = level.getBlockState(origin.offset(0, 1, 80))
                .is(Blocks.BEACON);
        boolean sortieLane = isRoad(level.getBlockState(origin.offset(0, 0, 60)));
        boolean observationDeck = level.getBlockState(
                origin.offset(0, OBSERVATION_Y, OBSERVATION_Z)).is(Blocks.LODESTONE);
        boolean foundation = level.getBlockState(
                origin.offset(FOUNDATION_HALF_SIZE, -4, 0)).is(Blocks.DEEPSLATE_BRICKS);
        boolean valid = roads == ROAD_AUDIT_POINTS.length
                && towers == EXPECTED_TOWERS && substations == 2
                && pylons == PYLONS.length && battleBeacon
                && sortieLane && observationDeck && foundation;
        return new DistrictAudit(valid, roads, towers, substations, pylons,
                battleBeacon, sortieLane, observationDeck, foundation);
    }

    private static void buildFoundation(ServerLevel level, BlockPos origin)
    {
        BlockState surface = Blocks.SMOOTH_STONE.defaultBlockState();
        BlockState retainingWall = Blocks.DEEPSLATE_BRICKS.defaultBlockState();
        for (int x = -FOUNDATION_HALF_SIZE; x <= FOUNDATION_HALF_SIZE; x++)
        {
            for (int z = -FOUNDATION_HALF_SIZE; z <= FOUNDATION_HALF_SIZE; z++)
            {
                set(level, origin.offset(x, 0, z), surface);
            }
        }
        for (int depth = 1; depth <= 6; depth++)
        {
            for (int span = -FOUNDATION_HALF_SIZE; span <= FOUNDATION_HALF_SIZE; span++)
            {
                set(level, origin.offset(-FOUNDATION_HALF_SIZE, -depth, span),
                        retainingWall);
                set(level, origin.offset(FOUNDATION_HALF_SIZE, -depth, span),
                        retainingWall);
                set(level, origin.offset(span, -depth, -FOUNDATION_HALF_SIZE),
                        retainingWall);
                set(level, origin.offset(span, -depth, FOUNDATION_HALF_SIZE),
                        retainingWall);
            }
        }
    }

    private static void buildRoadGrid(ServerLevel level, BlockPos origin)
    {
        BlockState asphalt = Blocks.BLACK_CONCRETE.defaultBlockState();
        BlockState roadEdge = Blocks.GRAY_CONCRETE.defaultBlockState();
        BlockState sidewalk = Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState();
        BlockState lane = Blocks.YELLOW_CONCRETE.defaultBlockState();

        for (int x = -DISTRICT_HALF_SIZE; x <= DISTRICT_HALF_SIZE; x++)
        {
            int roadX = distanceToRoadAxis(x);
            for (int z = -DISTRICT_HALF_SIZE; z <= DISTRICT_HALF_SIZE; z++)
            {
                if (insideSortieApron(x, z))
                {
                    continue;
                }
                int roadZ = distanceToRoadAxis(z);
                boolean verticalRoad = roadX <= ROAD_HALF_WIDTH;
                boolean horizontalRoad = roadZ <= ROAD_HALF_WIDTH;
                boolean sidewalkCell = roadX <= SIDEWALK_HALF_WIDTH
                        || roadZ <= SIDEWALK_HALF_WIDTH;
                if (!verticalRoad && !horizontalRoad && !sidewalkCell)
                {
                    continue;
                }

                BlockState state = sidewalk;
                if (verticalRoad || horizontalRoad)
                {
                    state = asphalt;
                    if (roadX == ROAD_HALF_WIDTH || roadZ == ROAD_HALF_WIDTH)
                    {
                        state = roadEdge;
                    }
                    boolean dashed = Math.floorMod(verticalRoad ? z : x, 10) < 5;
                    if (dashed && ((verticalRoad && roadX == 0 && !horizontalRoad)
                            || (horizontalRoad && roadZ == 0 && !verticalRoad)))
                    {
                        state = lane;
                    }
                }
                set(level, origin.offset(x, 0, z), state);
                if (verticalRoad || horizontalRoad)
                {
                    clearHeadroom(level, origin.offset(x, 0, z), 3);
                }
            }
        }
    }

    private static void buildArmouredTower(ServerLevel level, BlockPos centre,
                                           int height, int gridX, int gridZ)
    {
        BlockState armor = Blocks.GRAY_CONCRETE.defaultBlockState();
        BlockState dark = Blocks.DEEPSLATE_TILES.defaultBlockState();
        BlockState glass = Math.floorMod(gridX + gridZ, 80) == 0
                ? Blocks.LIGHT_BLUE_STAINED_GLASS.defaultBlockState()
                : Blocks.CYAN_STAINED_GLASS.defaultBlockState();
        BlockState nervStripe = Blocks.ORANGE_CONCRETE.defaultBlockState();

        fillSquare(level, centre, 0, LOT_HALF_SIZE, Blocks.POLISHED_DEEPSLATE.defaultBlockState());
        for (int y = 1; y <= height; y++)
        {
            for (int i = -LOT_HALF_SIZE; i <= LOT_HALF_SIZE; i++)
            {
                set(level, centre.offset(-LOT_HALF_SIZE, y, i),
                        towerWall(y, i, armor, dark, glass, nervStripe));
                set(level, centre.offset(LOT_HALF_SIZE, y, i),
                        towerWall(y, i, armor, dark, glass, nervStripe));
                set(level, centre.offset(i, y, -LOT_HALF_SIZE),
                        towerWall(y, i, armor, dark, glass, nervStripe));
                set(level, centre.offset(i, y, LOT_HALF_SIZE),
                        towerWall(y, i, armor, dark, glass, nervStripe));
            }
        }
        cutInnerDoor(level, centre, gridX, gridZ);
        fillSquare(level, centre, height + 1, LOT_HALF_SIZE,
                Blocks.SMOOTH_STONE.defaultBlockState());
        set(level, centre.offset(0, height, 0), Blocks.REDSTONE_BLOCK.defaultBlockState());
        set(level, centre.offset(0, height + 1, 0), Blocks.REDSTONE_LAMP.defaultBlockState());
        for (int x : new int[] {-8, 8})
        {
            for (int z : new int[] {-8, 8})
            {
                set(level, centre.offset(x, height + 2, z),
                        Blocks.LIGHTNING_ROD.defaultBlockState());
            }
        }
    }

    private static BlockState towerWall(int y, int span, BlockState armor,
                                        BlockState dark, BlockState glass,
                                        BlockState nervStripe)
    {
        if (y <= 5)
        {
            return dark;
        }
        if (y == 6 || y % 12 == 0)
        {
            return nervStripe;
        }
        if (Math.abs(span) >= LOT_HALF_SIZE - 1)
        {
            return armor;
        }
        return y % 4 == 1 || y % 4 == 2 ? glass : armor;
    }

    private static void cutInnerDoor(ServerLevel level, BlockPos centre, int gridX, int gridZ)
    {
        boolean doorOnX = Math.abs(gridX) >= Math.abs(gridZ);
        int wall = doorOnX
                ? (gridX > 0 ? -LOT_HALF_SIZE : LOT_HALF_SIZE)
                : (gridZ > 0 ? -LOT_HALF_SIZE : LOT_HALF_SIZE);
        for (int y = 1; y <= 5; y++)
        {
            for (int side = -2; side <= 2; side++)
            {
                BlockPos door = doorOnX ? centre.offset(wall, y, side)
                        : centre.offset(side, y, wall);
                set(level, door, Blocks.AIR.defaultBlockState());
            }
        }
    }

    private static void buildSubstation(ServerLevel level, BlockPos centre)
    {
        fillSquare(level, centre, 0, LOT_HALF_SIZE, Blocks.SMOOTH_STONE.defaultBlockState());
        for (int i = -LOT_HALF_SIZE; i <= LOT_HALF_SIZE; i++)
        {
            set(level, centre.offset(-LOT_HALF_SIZE, 1, i), Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(LOT_HALF_SIZE, 1, i), Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(i, 1, -LOT_HALF_SIZE), Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(i, 1, LOT_HALF_SIZE), Blocks.IRON_BARS.defaultBlockState());
        }
        for (int x : new int[] {-7, 0, 7})
        {
            for (int z : new int[] {-6, 6})
            {
                for (int y = 1; y <= 5; y++)
                {
                    set(level, centre.offset(x, y, z),
                            y == 3 ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                                    : Blocks.CUT_COPPER.defaultBlockState());
                }
                set(level, centre.offset(x, 6, z), Blocks.LIGHTNING_ROD.defaultBlockState());
            }
        }
        for (int x = -9; x <= 9; x += 3)
        {
            set(level, centre.offset(x, 1, 0), Blocks.REDSTONE_LAMP.defaultBlockState());
        }
        // Place the audit/core block after the centre lamp strip so the strip
        // cannot silently overwrite both substation signatures.
        set(level, centre.above(), Blocks.COPPER_BLOCK.defaultBlockState());
    }

    private static void buildBattlePlaza(ServerLevel level, BlockPos centre)
    {
        fillSquare(level, centre, 0, LOT_HALF_SIZE, Blocks.SMOOTH_STONE.defaultBlockState());
        for (int ring = 4; ring <= 12; ring += 4)
        {
            for (int i = -ring; i <= ring; i++)
            {
                BlockState warning = Math.floorMod(i + ring, 4) < 2
                        ? Blocks.YELLOW_CONCRETE.defaultBlockState()
                        : Blocks.BLACK_CONCRETE.defaultBlockState();
                set(level, centre.offset(-ring, 0, i), warning);
                set(level, centre.offset(ring, 0, i), warning);
                set(level, centre.offset(i, 0, -ring), warning);
                set(level, centre.offset(i, 0, ring), warning);
            }
        }
        set(level, centre.above(), Blocks.BEACON.defaultBlockState());
        set(level, centre.above(2), Blocks.RED_STAINED_GLASS.defaultBlockState());
    }

    private static void buildPowerPylon(ServerLevel level, BlockPos centre)
    {
        for (int y = 1; y <= 28; y++)
        {
            int spread = Math.max(0, 4 - y / 7);
            set(level, centre.offset(-spread, y, 0), Blocks.IRON_BLOCK.defaultBlockState());
            set(level, centre.offset(spread, y, 0), Blocks.IRON_BLOCK.defaultBlockState());
            if (y % 6 == 0)
            {
                for (int x = -spread; x <= spread; x++)
                {
                    set(level, centre.offset(x, y, 0), Blocks.IRON_BARS.defaultBlockState());
                }
            }
        }
        for (int x = -5; x <= 5; x++)
        {
            set(level, centre.offset(x, 22, 0), Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(x, 27, 0), Blocks.IRON_BARS.defaultBlockState());
        }
        set(level, centre.offset(0, 28, 0), Blocks.IRON_BLOCK.defaultBlockState());
    }

    private static void connectPowerGrid(ServerLevel level, BlockPos origin, int x)
    {
        for (int startZ : new int[] {-80, 0})
        {
            for (int z = startZ + 1; z < startZ + 80; z++)
            {
                for (int wireX : new int[] {-4, 0, 4})
                {
                    set(level, origin.offset(x + wireX, 27, z),
                            Blocks.IRON_BARS.defaultBlockState());
                }
            }
        }
    }

    private static void buildSortieGate(ServerLevel level, BlockPos centre)
    {
        for (int y = 0; y <= 18; y++)
        {
            set(level, centre.offset(-10, y, 0), Blocks.IRON_BLOCK.defaultBlockState());
            set(level, centre.offset(10, y, 0), Blocks.IRON_BLOCK.defaultBlockState());
        }
        for (int x = -10; x <= 10; x++)
        {
            set(level, centre.offset(x, 18, 0), x % 4 == 0
                    ? Blocks.REDSTONE_LAMP.defaultBlockState()
                    : Blocks.BLACK_CONCRETE.defaultBlockState());
        }
    }

    private static void buildObservationDeck(ServerLevel level, BlockPos centre)
    {
        for (int y = 1; y <= OBSERVATION_Y; y++)
        {
            for (int x : new int[] {-4, 4})
            {
                for (int z : new int[] {-4, 4})
                {
                    set(level, centre.offset(x, y, z), Blocks.IRON_BLOCK.defaultBlockState());
                }
            }
        }
        fillSquare(level, centre, OBSERVATION_Y, 6, Blocks.SMOOTH_STONE.defaultBlockState());
        for (int i = -6; i <= 6; i++)
        {
            set(level, centre.offset(-6, OBSERVATION_Y + 1, i), Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(6, OBSERVATION_Y + 1, i), Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(i, OBSERVATION_Y + 1, -6), Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(i, OBSERVATION_Y + 1, 6), Blocks.IRON_BARS.defaultBlockState());
        }
        set(level, centre.offset(0, OBSERVATION_Y, 0), Blocks.LODESTONE.defaultBlockState());
    }

    private static int towerHeight(int x, int z)
    {
        int gridX = x / 40;
        int gridZ = z / 40;
        return 22 + Math.floorMod(gridX * 31 + gridZ * 17, 6) * 4;
    }

    private static int distanceToRoadAxis(int value)
    {
        int phase = Math.floorMod(value + ROAD_OFFSET, ROAD_SPACING);
        return Math.min(phase, ROAD_SPACING - phase);
    }

    private static boolean insideSortieApron(int x, int z)
    {
        return Math.abs(x) <= 48 && z >= -36 && z <= 44;
    }

    private static boolean isRoad(BlockState state)
    {
        return state.is(Blocks.BLACK_CONCRETE) || state.is(Blocks.GRAY_CONCRETE)
                || state.is(Blocks.YELLOW_CONCRETE)
                || state.is(Blocks.LIGHT_GRAY_CONCRETE);
    }

    private static void clearHeadroom(ServerLevel level, BlockPos floor, int height)
    {
        for (int y = 1; y <= height; y++)
        {
            BlockPos position = floor.above(y);
            if (!level.getBlockState(position).isAir())
            {
                set(level, position, Blocks.AIR.defaultBlockState());
            }
        }
    }

    private static void fillSquare(ServerLevel level, BlockPos centre, int y,
                                   int halfSize, BlockState state)
    {
        for (int x = -halfSize; x <= halfSize; x++)
        {
            for (int z = -halfSize; z <= halfSize; z++)
            {
                set(level, centre.offset(x, y, z), state);
            }
        }
    }

    private static void set(ServerLevel level, BlockPos position, BlockState state)
    {
        level.setBlock(position, state, UPDATE_CLIENTS);
    }

    public record DistrictAudit(boolean valid, int roads, int towers,
                                int substations, int pylons, boolean battleBeacon,
                                boolean sortieLane, boolean observationDeck,
                                boolean foundation)
    {
        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s roads=%d/8 towers=%d/13 substations=%d/2 "
                            + "pylons=%d/6 battleBeacon=%s sortieLane=%s "
                            + "observationDeck=%s foundation=%s",
                    this.valid, this.roads, this.towers, this.substations,
                    this.pylons, this.battleBeacon, this.sortieLane,
                    this.observationDeck, this.foundation);
        }
    }
}
