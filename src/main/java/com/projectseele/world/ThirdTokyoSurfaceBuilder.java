package com.projectseele.world;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

import com.projectseele.registry.ModBlocks;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;

/**
 * Deterministic original Tokyo-3 surface district around the three NERV bays.
 * The inner grid carries retractable armour towers while a wider permanent
 * ward gives EVA-scale streets enough depth to read as a city rather than a
 * compact test pad.
 */
public final class ThirdTokyoSurfaceBuilder
{
    public static final int DISTRICT_HALF_SIZE = 208;
    public static final int FOUNDATION_HALF_SIZE = 224;
    public static final int OBSERVATION_Z = 216;
    public static final int OBSERVATION_Y = 38;
    public static final int ARMOURED_LOT_HALF_SIZE = 12;

    private static final int ROAD_SPACING = 40;
    private static final int ROAD_OFFSET = 20;
    private static final int ROAD_HALF_WIDTH = 4;
    private static final int SIDEWALK_HALF_WIDTH = 7;
    private static final int LOT_HALF_SIZE = ARMOURED_LOT_HALF_SIZE;
    private static final int[] LOT_CENTRES =
            {-160, -120, -80, -40, 0, 40, 80, 120, 160};
    private static final int[] OUTER_LOT_CENTRES =
            {-200, -160, -120, -80, -40, 0, 40, 80, 120, 160, 200};

    private static final int[][] PYLONS = {
            {-180, -160}, {-180, 0}, {-180, 160},
            {180, -160}, {180, 0}, {180, 160},
    };
    private static final int[][] ROAD_AUDIT_POINTS = {
            {-180, -180}, {-180, 180}, {180, -180}, {180, 180},
            {-140, -180}, {140, 180}, {-180, 140}, {180, -140},
    };
    private static final int CEILING_SHELL_CLEARANCE = 4;
    private static final List<TowerSpec> ARMOURED_TOWERS = createArmouredTowers();
    private static final List<TowerSpec> OUTER_WARD_TOWERS = createOuterWardTowers();
    private static final List<TowerSpec> MOVABLE_BUILDINGS = createMovableBuildings();
    private static final int EXPECTED_TOWERS = ARMOURED_TOWERS.size();
    private static final int EXPECTED_OUTER_WARDS = OUTER_WARD_TOWERS.size();
    private static final int MAX_RETRACTION_DEPTH = MOVABLE_BUILDINGS.stream()
            .mapToInt(tower -> ceilingTravelDepth(tower) + tower.height())
            .max().orElse(0);
    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;
    // Layer travel only ever moves full cubes, so the six recursive
    // updateShape calls vanilla runs per placement are pure cost across the
    // thousands of blocks a single layer rewrites.
    private static final int UPDATE_TRAVEL =
            Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE;

    private ThirdTokyoSurfaceBuilder() {}

    public static void buildDistrict(ServerLevel level, BlockPos origin)
    {
        buildFoundation(level, origin);
        buildRoadGrid(level, origin);

        for (int x : LOT_CENTRES)
        {
            for (int z : LOT_CENTRES)
            {
                if (Math.abs(x) <= 40 && Math.abs(z) <= 40
                        || reservedPrivateSkyscraperLot(x, z))
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

        for (int x : OUTER_LOT_CENTRES)
        {
            for (int z : OUTER_LOT_CENTRES)
            {
                if (Math.max(Math.abs(x), Math.abs(z)) != 200
                        || reservedOuterTransitLot(x, z))
                {
                    continue;
                }
                buildOuterWardTower(level, origin.offset(x, 0, z),
                        outerWardHeight(x, z), x, z);
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
        return inspect(level, origin, 0);
    }

    public static DistrictAudit inspect(ServerLevel level, BlockPos origin,
                                        int retractionDepth)
    {
        int depth = Math.max(0, Math.min(MAX_RETRACTION_DEPTH, retractionDepth));
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
                        || (x == 0 && z == 80)
                        || reservedPrivateSkyscraperLot(x, z))
                {
                    continue;
                }
                int visibleHeight = Math.max(0, towerHeight(x, z) - depth);
                boolean signature = visibleHeight > 0
                        ? level.getBlockState(origin.offset(x, visibleHeight + 1, z))
                                .is(Blocks.REDSTONE_LAMP)
                        : level.getBlockState(origin.offset(x, 0, z))
                                .is(ModBlocks.RETRACTABLE_BUILDING_CORE.get())
                                && towerShellClear(level, origin.offset(x, 0, z));
                if (signature)
                {
                    towers++;
                }
            }
        }

        int outerWards = 0;
        for (int x : OUTER_LOT_CENTRES)
        {
            for (int z : OUTER_LOT_CENTRES)
            {
                if (Math.max(Math.abs(x), Math.abs(z)) != 200
                        || reservedOuterTransitLot(x, z))
                {
                    continue;
                }
                int height = outerWardHeight(x, z);
                int visibleHeight = Math.max(0, height - depth);
                boolean signature = visibleHeight > 0
                        ? level.getBlockState(origin.offset(x, visibleHeight + 1, z))
                                .is(Blocks.REDSTONE_LAMP)
                        : towerShellClear(level, origin.offset(x, 0, z), 9);
                if (signature)
                {
                    outerWards++;
                }
            }
        }

        int ceilingBuildings = 0;
        for (TowerSpec tower : MOVABLE_BUILDINGS)
        {
            if (ceilingStateMatches(level, origin, tower, depth))
            {
                ceilingBuildings++;
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
                && towers == EXPECTED_TOWERS
                && outerWards == EXPECTED_OUTER_WARDS
                && ceilingBuildings == MOVABLE_BUILDINGS.size()
                && substations == 2
                && pylons == PYLONS.length && battleBeacon
                && sortieLane && observationDeck && foundation;
        return new DistrictAudit(valid, roads, towers, outerWards,
                ceilingBuildings, substations, pylons,
                battleBeacon, sortieLane, observationDeck, foundation);
    }

    public static List<TowerSpec> armouredTowers()
    {
        return ARMOURED_TOWERS;
    }

    /** Every generated building that physically travels into the GeoFront. */
    public static List<TowerSpec> movableBuildings()
    {
        return MOVABLE_BUILDINGS;
    }

    public static int maximumRetractionDepth()
    {
        return MAX_RETRACTION_DEPTH;
    }

    /** Applies exactly one globally synchronized layer of tower travel. */
    public static void applyRetractionDepth(ServerLevel level, BlockPos origin,
                                            int oldDepth, int newDepth)
    {
        for (int index = 0; index < MOVABLE_BUILDINGS.size(); index++)
        {
            applyRetractionDepth(level, origin, oldDepth, newDepth, index);
        }
    }

    /**
     * Applies one layer of travel to a single tower. The director spreads a
     * layer across consecutive ticks so no tick pays for the whole district;
     * every tower still travels exactly one block per layer period.
     */
    public static void applyRetractionDepth(ServerLevel level, BlockPos origin,
                                            int oldDepth, int newDepth, int towerIndex)
    {
        if (Math.abs(newDepth - oldDepth) != 1
                || oldDepth < 0 || oldDepth > MAX_RETRACTION_DEPTH
                || newDepth < 0 || newDepth > MAX_RETRACTION_DEPTH)
        {
            throw new IllegalArgumentException(
                    "Tokyo-3 retraction depth must move by one layer");
        }
        TowerSpec tower = MOVABLE_BUILDINGS.get(towerIndex);
        int oldVisible = Math.max(0, tower.height() - oldDepth);
        int newVisible = Math.max(0, tower.height() - newDepth);
        int oldCeilingVisible = ceilingVisibleHeight(tower, oldDepth);
        int newCeilingVisible = ceilingVisibleHeight(tower, newDepth);
        if (oldVisible != newVisible)
        {
            BlockPos centre = origin.offset(tower.x(), 0, tower.z());
            if (newVisible < oldVisible)
            {
                descendTowerLayer(level, centre, tower, oldVisible, newVisible);
            }
            else
            {
                ascendTowerLayer(level, centre, tower, oldVisible, newVisible);
            }
        }
        if (oldCeilingVisible != newCeilingVisible)
        {
            if (newCeilingVisible > oldCeilingVisible)
            {
                emergeCeilingLayer(level, origin, tower,
                        oldCeilingVisible, newCeilingVisible);
            }
            else
            {
                withdrawCeilingLayer(level, origin, tower,
                        oldCeilingVisible, newCeilingVisible);
            }
        }
    }

    /**
     * One block of descent. The order matters far more than the block count:
     * vanilla rescans a column downwards whenever the block it removes was
     * that column's surface, and a tower is up to forty blocks of hollow
     * shell. Laying the lower cap before stripping the upper one turns six
     * hundred forty-block rescans into six hundred one-block rescans.
     */
    private static void descendTowerLayer(ServerLevel level, BlockPos centre,
                                          TowerSpec tower,
                                          int oldVisible, int newVisible)
    {
        if (newVisible > 0)
        {
            fillSquare(level, centre, newVisible + 1, tower.halfSize(),
                    Blocks.SMOOTH_STONE.defaultBlockState(), UPDATE_TRAVEL);
            if (!tower.outerWard())
            {
                set(level, centre.offset(0, newVisible, 0),
                        Blocks.REDSTONE_BLOCK.defaultBlockState(), UPDATE_TRAVEL);
            }
            set(level, centre.offset(0, newVisible + 1, 0),
                    Blocks.REDSTONE_LAMP.defaultBlockState(), UPDATE_TRAVEL);
        }
        setRoofMasts(level, centre, tower, oldVisible + 2,
                Blocks.AIR.defaultBlockState());
        fillSquare(level, centre, oldVisible + 1, tower.halfSize(),
                Blocks.AIR.defaultBlockState(), UPDATE_TRAVEL);
        if (newVisible > 0)
        {
            setRoofMasts(level, centre, tower, newVisible + 2,
                    Blocks.LIGHTNING_ROD.defaultBlockState());
            return;
        }
        // The last layer lays no cap, so its wall ring and beacon survive the
        // roof sweep and have to go explicitly.
        clearTowerWallLayer(level, centre, oldVisible, tower.halfSize());
        set(level, centre.offset(0, oldVisible, 0), Blocks.AIR.defaultBlockState(),
                UPDATE_TRAVEL);
    }

    /** One block of ascent, raising the new cap before dissolving the old. */
    private static void ascendTowerLayer(ServerLevel level, BlockPos centre,
                                         TowerSpec tower,
                                         int oldVisible, int newVisible)
    {
        fillSquare(level, centre, newVisible + 1, tower.halfSize(),
                Blocks.SMOOTH_STONE.defaultBlockState(), UPDATE_TRAVEL);
        set(level, centre.offset(0, newVisible + 1, 0),
                Blocks.REDSTONE_LAMP.defaultBlockState(), UPDATE_TRAVEL);
        setRoofMasts(level, centre, tower, newVisible + 2,
                Blocks.LIGHTNING_ROD.defaultBlockState());
        if (oldVisible > 0)
        {
            fillSquare(level, centre, oldVisible + 1, tower.halfSize(),
                    Blocks.AIR.defaultBlockState(), UPDATE_TRAVEL);
            set(level, centre.offset(0, oldVisible, 0),
                    Blocks.AIR.defaultBlockState(), UPDATE_TRAVEL);
        }
        buildTowerWallLayer(level, centre, tower, newVisible, newVisible);
        if (!tower.outerWard())
        {
            set(level, centre.offset(0, newVisible, 0),
                    Blocks.REDSTONE_BLOCK.defaultBlockState(), UPDATE_TRAVEL);
        }
    }

    private static void setRoofMasts(ServerLevel level, BlockPos centre,
                                     TowerSpec tower, int y, BlockState state)
    {
        if (tower.outerWard())
        {
            set(level, centre.offset(0, y, 0), state, UPDATE_TRAVEL);
            return;
        }
        for (int x : new int[] {-8, 8})
        {
            for (int z : new int[] {-8, 8})
            {
                set(level, centre.offset(x, y, z), state, UPDATE_TRAVEL);
            }
        }
    }

    /**
     * Builds one more layer below the curved GeoFront ceiling. A temporary
     * solid underside moves with the building, so from the cavern the city
     * reads as real mass descending rather than wall rings appearing in air.
     */
    private static void emergeCeilingLayer(ServerLevel level, BlockPos origin,
                                           TowerSpec tower,
                                           int oldVisible, int newVisible)
    {
        int roofY = ceilingRoofRelativeY(tower);
        BlockPos centre = origin.offset(tower.x(), 0, tower.z());
        if (oldVisible == 0)
        {
            fillSquare(level, centre, roofY, tower.halfSize(),
                    Blocks.SMOOTH_STONE.defaultBlockState(), UPDATE_TRAVEL);
            set(level, centre.offset(0, roofY, 0),
                    Blocks.REDSTONE_LAMP.defaultBlockState(), UPDATE_TRAVEL);
        }
        int wallY = roofY - newVisible;
        if (oldVisible > 0)
        {
            fillSquare(level, centre, wallY, tower.halfSize(),
                    Blocks.AIR.defaultBlockState(), UPDATE_TRAVEL);
        }
        int sourceY = tower.height() - newVisible + 1;
        buildTowerWallLayer(level, centre, tower, sourceY, wallY);
        fillSquare(level, centre, wallY - 1, tower.halfSize(),
                Blocks.POLISHED_DEEPSLATE.defaultBlockState(), UPDATE_TRAVEL);
        set(level, centre.offset(0, wallY - 1, 0),
                Blocks.SEA_LANTERN.defaultBlockState(), UPDATE_TRAVEL);
    }

    /** Exact inverse of {@link #emergeCeilingLayer}. */
    private static void withdrawCeilingLayer(ServerLevel level, BlockPos origin,
                                             TowerSpec tower,
                                             int oldVisible, int newVisible)
    {
        int roofY = ceilingRoofRelativeY(tower);
        BlockPos centre = origin.offset(tower.x(), 0, tower.z());
        int oldWallY = roofY - oldVisible;
        fillSquare(level, centre, oldWallY - 1, tower.halfSize(),
                Blocks.AIR.defaultBlockState(), UPDATE_TRAVEL);
        clearTowerWallLayer(level, centre, oldWallY, tower.halfSize());
        if (newVisible > 0)
        {
            fillSquare(level, centre, oldWallY, tower.halfSize(),
                    Blocks.POLISHED_DEEPSLATE.defaultBlockState(), UPDATE_TRAVEL);
            set(level, centre.offset(0, oldWallY, 0),
                    Blocks.SEA_LANTERN.defaultBlockState(), UPDATE_TRAVEL);
        }
        else
        {
            fillSquare(level, centre, roofY, tower.halfSize(),
                    Blocks.AIR.defaultBlockState(), UPDATE_TRAVEL);
        }
    }

    private static void buildFoundation(ServerLevel level, BlockPos origin)
    {
        BlockState surface = Blocks.SMOOTH_STONE.defaultBlockState();
        BlockState retainingWall = Blocks.DEEPSLATE_BRICKS.defaultBlockState();
        for (int x = -FOUNDATION_HALF_SIZE; x <= FOUNDATION_HALF_SIZE; x++)
        {
            for (int z = -FOUNDATION_HALF_SIZE; z <= FOUNDATION_HALF_SIZE; z++)
            {
                int worldX = origin.getX() + x;
                int worldZ = origin.getZ() + z;
                int nativeSurface = level.getHeight(
                        Heightmap.Types.WORLD_SURFACE_WG, worldX, worldZ) - 1;
                nativeSurface = Math.max(level.getMinBuildHeight(),
                        Math.min(nativeSurface, origin.getY() + 64));
                if (nativeSurface < origin.getY())
                {
                    for (int y = nativeSurface + 1; y < origin.getY(); y++)
                    {
                        BlockState fill = y >= origin.getY() - 3
                                ? Blocks.DIRT.defaultBlockState()
                                : Blocks.STONE.defaultBlockState();
                        set(level, new BlockPos(worldX, y, worldZ), fill);
                    }
                }
                else if (nativeSurface > origin.getY())
                {
                    for (int y = origin.getY() + 1; y <= nativeSurface; y++)
                    {
                        set(level, new BlockPos(worldX, y, worldZ),
                                Blocks.AIR.defaultBlockState());
                    }
                }
                set(level, new BlockPos(worldX, origin.getY(), worldZ), surface);
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
        set(level, centre, ModBlocks.RETRACTABLE_BUILDING_CORE.get()
                .defaultBlockState().setValue(RetractableBuildingCoreBlock.ARMED, false));
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

    private static void buildOuterWardTower(ServerLevel level, BlockPos centre,
                                            int height, int gridX, int gridZ)
    {
        int half = 9;
        BlockState frame = Math.floorMod(gridX * 3 + gridZ, 5) < 2
                ? Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState()
                : Blocks.GRAY_CONCRETE.defaultBlockState();
        BlockState glass = Math.floorMod(gridX + gridZ, 3) == 0
                ? Blocks.LIGHT_BLUE_STAINED_GLASS.defaultBlockState()
                : Blocks.CYAN_STAINED_GLASS.defaultBlockState();
        fillSquare(level, centre, 0, half,
                Blocks.POLISHED_DEEPSLATE.defaultBlockState());
        for (int y = 1; y <= height; y++)
        {
            for (int span = -half; span <= half; span++)
            {
                BlockState state = y <= 4 || y % 10 == 0
                        || Math.abs(span) >= half - 1 ? frame : glass;
                set(level, centre.offset(-half, y, span), state);
                set(level, centre.offset(half, y, span), state);
                set(level, centre.offset(span, y, -half), state);
                set(level, centre.offset(span, y, half), state);
            }
        }
        fillSquare(level, centre, height + 1, half,
                Blocks.SMOOTH_STONE.defaultBlockState());
        set(level, centre.offset(0, height + 1, 0),
                Blocks.REDSTONE_LAMP.defaultBlockState());
        set(level, centre.offset(0, height + 2, 0),
                Blocks.LIGHTNING_ROD.defaultBlockState());
        for (int y = 1; y <= 4; y++)
        {
            set(level, centre.offset(0, y, -half),
                    Blocks.AIR.defaultBlockState());
            set(level, centre.offset(1, y, -half),
                    Blocks.AIR.defaultBlockState());
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

    private static void clearTowerWallLayer(ServerLevel level, BlockPos centre,
                                            int y, int halfSize)
    {
        BlockState air = Blocks.AIR.defaultBlockState();
        for (int i = -halfSize; i <= halfSize; i++)
        {
            set(level, centre.offset(-halfSize, y, i), air, UPDATE_TRAVEL);
            set(level, centre.offset(halfSize, y, i), air, UPDATE_TRAVEL);
            set(level, centre.offset(i, y, -halfSize), air, UPDATE_TRAVEL);
            set(level, centre.offset(i, y, halfSize), air, UPDATE_TRAVEL);
        }
    }

    private static void buildTowerWallLayer(ServerLevel level, BlockPos centre,
                                            TowerSpec tower,
                                            int sourceY, int targetY)
    {
        BlockState armor = Blocks.GRAY_CONCRETE.defaultBlockState();
        BlockState dark = Blocks.DEEPSLATE_TILES.defaultBlockState();
        BlockState glass = Math.floorMod(tower.x() + tower.z(), 80) == 0
                ? Blocks.LIGHT_BLUE_STAINED_GLASS.defaultBlockState()
                : Blocks.CYAN_STAINED_GLASS.defaultBlockState();
        BlockState nervStripe = Blocks.ORANGE_CONCRETE.defaultBlockState();
        int half = tower.halfSize();
        for (int i = -half; i <= half; i++)
        {
            BlockState state = tower.outerWard()
                    ? outerWardWall(sourceY, i, tower)
                    : towerWall(sourceY, i, armor, dark, glass, nervStripe);
            set(level, centre.offset(-half, targetY, i), state, UPDATE_TRAVEL);
            set(level, centre.offset(half, targetY, i), state, UPDATE_TRAVEL);
            set(level, centre.offset(i, targetY, -half), state, UPDATE_TRAVEL);
            set(level, centre.offset(i, targetY, half), state, UPDATE_TRAVEL);
        }
        if (!tower.outerWard() && targetY == sourceY)
        {
            cutInnerDoor(level, centre, tower.x(), tower.z());
        }
    }

    private static BlockState outerWardWall(int y, int span, TowerSpec tower)
    {
        BlockState frame = Math.floorMod(tower.x() * 3 + tower.z(), 5) < 2
                ? Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState()
                : Blocks.GRAY_CONCRETE.defaultBlockState();
        BlockState glass = Math.floorMod(tower.x() + tower.z(), 3) == 0
                ? Blocks.LIGHT_BLUE_STAINED_GLASS.defaultBlockState()
                : Blocks.CYAN_STAINED_GLASS.defaultBlockState();
        return y <= 4 || y % 10 == 0
                || Math.abs(span) >= tower.halfSize() - 1 ? frame : glass;
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

    private static int outerWardHeight(int x, int z)
    {
        return 18 + Math.floorMod(x * 13 + z * 29, 5) * 5;
    }

    private static boolean reservedPrivateSkyscraperLot(int x, int z)
    {
        return x == -120 && z == -80
                || x == 120 && z == -80
                || x == 120 && z == 80;
    }

    private static boolean reservedOuterTransitLot(int x, int z)
    {
        // The east perimeter is the dedicated elevated-rail corridor. Building
        // towers there first only lets the railway cut their roofs and doors.
        return x == 200;
    }

    private static List<TowerSpec> createArmouredTowers()
    {
        List<TowerSpec> towers = new ArrayList<>();
        for (int x : LOT_CENTRES)
        {
            for (int z : LOT_CENTRES)
            {
                if (Math.abs(x) <= 40 && Math.abs(z) <= 40
                        || (x == 0 && z == -80)
                        || (x == 80 && z == 0)
                        || (x == 0 && z == 80)
                        || reservedPrivateSkyscraperLot(x, z))
                {
                    continue;
                }
                towers.add(new TowerSpec(x, z, towerHeight(x, z),
                        LOT_HALF_SIZE, false));
            }
        }
        return List.copyOf(towers);
    }

    private static List<TowerSpec> createOuterWardTowers()
    {
        List<TowerSpec> towers = new ArrayList<>();
        for (int x : OUTER_LOT_CENTRES)
        {
            for (int z : OUTER_LOT_CENTRES)
            {
                if (Math.max(Math.abs(x), Math.abs(z)) != 200
                        || reservedOuterTransitLot(x, z))
                {
                    continue;
                }
                towers.add(new TowerSpec(x, z, outerWardHeight(x, z),
                        9, true));
            }
        }
        return List.copyOf(towers);
    }

    private static List<TowerSpec> createMovableBuildings()
    {
        List<TowerSpec> towers = new ArrayList<>(
                ARMOURED_TOWERS.size() + OUTER_WARD_TOWERS.size());
        towers.addAll(ARMOURED_TOWERS);
        towers.addAll(OUTER_WARD_TOWERS);
        return List.copyOf(towers);
    }

    private static int ceilingVisibleHeight(TowerSpec tower, int depth)
    {
        return Math.max(0, Math.min(tower.height(),
                depth - ceilingTravelDepth(tower)));
    }

    private static int ceilingTravelDepth(TowerSpec tower)
    {
        return Math.max(tower.height(), -ceilingRoofRelativeY(tower));
    }

    /**
     * Relative Y of the roof cap just inside the real spherical shell. Outer
     * wards therefore hang lower than the central skyline instead of punching
     * through the curved GeoFront wall.
     */
    public static int ceilingRoofRelativeY(TowerSpec tower)
    {
        int horizontalSqr = tower.x() * tower.x() + tower.z() * tower.z();
        int radiusSqr = GeoFrontBuilder.CAVERN_RADIUS * GeoFrontBuilder.CAVERN_RADIUS;
        int shellRise = (int) Math.floor(Math.sqrt(
                Math.max(0, radiusSqr - horizontalSqr)));
        int worldY = IntegratedNervMapBuilder.GEOFRONT_ORIGIN.getY()
                + GeoFrontBuilder.CAVERN_CENTRE_Y + shellRise
                - CEILING_SHELL_CLEARANCE;
        return worldY - IntegratedNervMapBuilder.TOKYO3_ORIGIN.getY();
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

    private static boolean towerShellClear(ServerLevel level, BlockPos centre)
    {
        return towerShellClear(level, centre, LOT_HALF_SIZE);
    }

    private static boolean towerShellClear(ServerLevel level, BlockPos centre,
                                           int halfSize)
    {
        return level.getBlockState(centre.offset(-halfSize, 1, 0)).isAir()
                && level.getBlockState(centre.offset(halfSize, 1, 0)).isAir()
                && level.getBlockState(centre.offset(0, 1, -halfSize)).isAir()
                && level.getBlockState(centre.offset(0, 1, halfSize)).isAir();
    }

    private static boolean ceilingStateMatches(ServerLevel level, BlockPos origin,
                                               TowerSpec tower, int depth)
    {
        int visible = ceilingVisibleHeight(tower, depth);
        int roofY = ceilingRoofRelativeY(tower);
        BlockPos centre = origin.offset(tower.x(), 0, tower.z());
        if (visible == 0)
        {
            return level.getBlockState(centre.offset(0, roofY, 0)).isAir()
                    && level.getBlockState(
                            centre.offset(tower.halfSize(), roofY - 1, 0)).isAir();
        }
        int wallY = roofY - visible;
        return level.getBlockState(centre.offset(0, roofY, 0))
                        .is(Blocks.REDSTONE_LAMP)
                && level.getBlockState(centre.offset(0, wallY - 1, 0))
                        .is(Blocks.SEA_LANTERN)
                && !level.getBlockState(
                        centre.offset(tower.halfSize(), wallY, 0)).isAir();
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
        fillSquare(level, centre, y, halfSize, state, UPDATE_CLIENTS);
    }

    private static void fillSquare(ServerLevel level, BlockPos centre, int y,
                                   int halfSize, BlockState state, int flags)
    {
        for (int x = -halfSize; x <= halfSize; x++)
        {
            for (int z = -halfSize; z <= halfSize; z++)
            {
                set(level, centre.offset(x, y, z), state, flags);
            }
        }
    }

    private static void set(ServerLevel level, BlockPos position, BlockState state)
    {
        set(level, position, state, UPDATE_CLIENTS);
    }

    private static void set(ServerLevel level, BlockPos position, BlockState state,
                            int flags)
    {
        if (!level.getBlockState(position).equals(state))
        {
            level.setBlock(position, state, flags);
        }
    }

    public record TowerSpec(int x, int z, int height,
                            int halfSize, boolean outerWard) {}

    public record DistrictAudit(boolean valid, int roads, int towers,
                                int outerWards, int ceilingBuildings,
                                int substations, int pylons,
                                boolean battleBeacon,
                                boolean sortieLane, boolean observationDeck,
                                boolean foundation)
    {
        public static DistrictAudit imported()
        {
            return new DistrictAudit(true, 8, EXPECTED_TOWERS,
                    EXPECTED_OUTER_WARDS, MOVABLE_BUILDINGS.size(), 2, 6,
                    true, true, true, true);
        }

        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s roads=%d/8 towers=%d/%d outerWards=%d/%d "
                            + "ceilingBuildings=%d/%d substations=%d/2 "
                            + "pylons=%d/6 battleBeacon=%s sortieLane=%s "
                            + "observationDeck=%s foundation=%s",
                    this.valid, this.roads, this.towers, EXPECTED_TOWERS,
                    this.outerWards, EXPECTED_OUTER_WARDS,
                    this.ceilingBuildings, MOVABLE_BUILDINGS.size(),
                    this.substations, this.pylons,
                    this.battleBeacon, this.sortieLane,
                    this.observationDeck, this.foundation);
        }
    }
}
