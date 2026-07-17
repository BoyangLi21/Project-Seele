package com.projectseele.world;

import java.util.Locale;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LadderBlock;
import net.minecraft.world.level.block.state.BlockState;

/** Deterministic clean-room GeoFront development cavern and NERV command pyramid. */
public final class GeoFrontBuilder
{
    public static final int CAVERN_RADIUS = 112;
    public static final int CAVERN_HEIGHT = 72;
    public static final int ARTIFICIAL_SUN_Y = 88;
    public static final int OBSERVATION_Z = 100;
    public static final int OBSERVATION_Y = 24;
    public static final int[] LIFT_X = {-28, 0, 28};

    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;

    private GeoFrontBuilder() {}

    public static void build(ServerLevel level, BlockPos origin)
    {
        buildCavernFloor(level, origin);
        buildCavernWall(level, origin);
        buildCeilingRibs(level, origin);
        buildLclLake(level, origin);
        buildNervPyramid(level, origin);
        NervOperationsCentreBuilder.build(level, origin);
        buildEvaLiftTerminals(level, origin);
        buildCommandBridge(level, origin);
        buildArtificialSun(level, origin);
        buildForestRing(level, origin);
        buildObservationDeck(level, origin);
    }

    public static GeoFrontAudit inspect(ServerLevel level, BlockPos origin)
    {
        boolean floor = level.getBlockState(origin.offset(CAVERN_RADIUS - 12, 0, 0))
                .is(Blocks.DEEPSLATE_TILES);
        boolean wall = isCavernStone(level.getBlockState(
                origin.offset(CAVERN_RADIUS, 32, 0)));
        boolean lake = level.getBlockState(origin.offset(48, 1, 0))
                .is(Blocks.ORANGE_STAINED_GLASS);
        boolean pyramid = level.getBlockState(origin.offset(0, 29, 0))
                .is(Blocks.BEACON);
        boolean sun = level.getBlockState(origin.offset(0, ARTIFICIAL_SUN_Y, 0))
                .is(Blocks.SEA_LANTERN);
        int lifts = 0;
        int gantries = 0;
        for (int x : LIFT_X)
        {
            if (level.getBlockState(origin.offset(x, 1, -76)).is(Blocks.LODESTONE))
            {
                lifts++;
            }
            if (level.getBlockState(origin.offset(x, 27, -63)).is(Blocks.LADDER)
                    && !level.getBlockState(origin.offset(x, 27, -70)).isAir())
            {
                gantries++;
            }
        }
        boolean bridge = level.getBlockState(origin.offset(0, 2, 70))
                .is(Blocks.IRON_BLOCK);
        boolean observation = level.getBlockState(
                origin.offset(0, OBSERVATION_Y, OBSERVATION_Z)).is(Blocks.LODESTONE);
        NervOperationsCentreBuilder.OperationsAudit operations =
                NervOperationsCentreBuilder.inspect(level, origin);
        boolean valid = floor && wall && lake && pyramid && sun && lifts == 3
                && gantries == 3
                && bridge && observation && operations.valid();
        return new GeoFrontAudit(valid, floor, wall, lake, pyramid, sun,
                lifts, gantries, bridge, observation, operations);
    }

    private static void buildCavernFloor(ServerLevel level, BlockPos origin)
    {
        int radiusSqr = CAVERN_RADIUS * CAVERN_RADIUS;
        int innerSqr = (CAVERN_RADIUS - 12) * (CAVERN_RADIUS - 12);
        for (int x = -CAVERN_RADIUS; x <= CAVERN_RADIUS; x++)
        {
            for (int z = -CAVERN_RADIUS; z <= CAVERN_RADIUS; z++)
            {
                int distanceSqr = x * x + z * z;
                if (distanceSqr > radiusSqr)
                {
                    continue;
                }
                BlockState surface = distanceSqr >= innerSqr
                        ? Blocks.DEEPSLATE_TILES.defaultBlockState()
                        : Blocks.TUFF.defaultBlockState();
                set(level, origin.offset(x, -2, z),
                        Blocks.DEEPSLATE_BRICKS.defaultBlockState());
                set(level, origin.offset(x, -1, z),
                        Blocks.POLISHED_DEEPSLATE.defaultBlockState());
                set(level, origin.offset(x, 0, z), surface);
            }
        }
    }

    private static void buildCavernWall(ServerLevel level, BlockPos origin)
    {
        final int samples = 1440;
        for (int y = 1; y <= CAVERN_HEIGHT; y++)
        {
            int inset = Math.max(0, y - 48) / 3;
            int radius = CAVERN_RADIUS - inset;
            for (int sample = 0; sample < samples; sample++)
            {
                double angle = Math.PI * 2.0D * sample / samples;
                for (int thickness = 0; thickness <= 2; thickness++)
                {
                    int x = (int) Math.round(Math.cos(angle) * (radius - thickness));
                    int z = (int) Math.round(Math.sin(angle) * (radius - thickness));
                    BlockState wall = Math.floorMod(sample + y * 3, 29) < 3
                            ? Blocks.CALCITE.defaultBlockState()
                            : (y % 11 == 0
                            ? Blocks.POLISHED_BASALT.defaultBlockState()
                            : Blocks.DEEPSLATE.defaultBlockState());
                    set(level, origin.offset(x, y, z), wall);
                }
            }
        }
    }

    private static void buildCeilingRibs(ServerLevel level, BlockPos origin)
    {
        for (int rib = 0; rib < 24; rib++)
        {
            double angle = Math.PI * 2.0D * rib / 24.0D;
            for (int radius = 12; radius <= 104; radius++)
            {
                int x = (int) Math.round(Math.cos(angle) * radius);
                int z = (int) Math.round(Math.sin(angle) * radius);
                int y = ARTIFICIAL_SUN_Y
                        - (int) Math.round(radius * 16.0D / 104.0D);
                set(level, origin.offset(x, y, z),
                        rib % 3 == 0 ? Blocks.IRON_BLOCK.defaultBlockState()
                                : Blocks.POLISHED_BASALT.defaultBlockState());
            }
        }
    }

    private static void buildLclLake(ServerLevel level, BlockPos origin)
    {
        int outer = 72;
        int inner = 40;
        for (int x = -outer; x <= outer; x++)
        {
            for (int z = -outer; z <= outer; z++)
            {
                int distanceSqr = x * x + z * z;
                if (distanceSqr > outer * outer || distanceSqr < inner * inner)
                {
                    continue;
                }
                BlockState bed = Math.floorMod(x * 17 + z * 31, 37) == 0
                        ? Blocks.SEA_LANTERN.defaultBlockState()
                        : Blocks.ORANGE_CONCRETE.defaultBlockState();
                set(level, origin.offset(x, 0, z), bed);
                set(level, origin.offset(x, 1, z),
                        Blocks.ORANGE_STAINED_GLASS.defaultBlockState());
            }
        }
    }

    private static void buildNervPyramid(ServerLevel level, BlockPos origin)
    {
        fillSquare(level, origin, 1, 35,
                Blocks.POLISHED_DEEPSLATE.defaultBlockState());
        for (int y = 2; y <= 28; y++)
        {
            int half = Math.max(4, 36 - y);
            BlockState wall = y == 8 || y == 16 || y == 24
                    ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                    : (y % 4 <= 1 ? Blocks.SMOOTH_QUARTZ.defaultBlockState()
                    : Blocks.GRAY_CONCRETE.defaultBlockState());
            squarePerimeter(level, origin, y, half, wall);
            if (y % 7 == 0)
            {
                fillSquare(level, origin, y, half - 1,
                        Blocks.SMOOTH_STONE.defaultBlockState());
            }
        }
        for (int depth = 1; depth <= 20; depth++)
        {
            int half = Math.max(1, 22 - depth);
            squarePerimeter(level, origin, -2 - depth, half,
                    depth % 5 == 0 ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                            : Blocks.DEEPSLATE_BRICKS.defaultBlockState());
        }
        set(level, origin.offset(0, 28, 0), Blocks.REDSTONE_BLOCK.defaultBlockState());
        set(level, origin.offset(0, 29, 0), Blocks.BEACON.defaultBlockState());
        set(level, origin.offset(0, 30, 0),
                Blocks.RED_STAINED_GLASS.defaultBlockState());
    }

    private static void buildEvaLiftTerminals(ServerLevel level, BlockPos origin)
    {
        for (int x : LIFT_X)
        {
            BlockPos centre = origin.offset(x, 0, -76);
            clearLiftCorridor(level, centre);
            BlockState accent = x < 0 ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                    : x > 0 ? Blocks.RED_CONCRETE.defaultBlockState()
                    : Blocks.PURPLE_CONCRETE.defaultBlockState();
            fillSquare(level, centre, 0, 7,
                    Blocks.POLISHED_DEEPSLATE.defaultBlockState());
            set(level, centre.above(), Blocks.LODESTONE.defaultBlockState());
            for (int y = 1; y <= 20; y++)
            {
                set(level, centre.offset(-7, y, 0), Blocks.IRON_BLOCK.defaultBlockState());
                set(level, centre.offset(7, y, 0), Blocks.IRON_BLOCK.defaultBlockState());
            }
            for (int span = -7; span <= 7; span++)
            {
                set(level, centre.offset(span, 20, 0), span % 4 == 0
                        ? Blocks.REDSTONE_LAMP.defaultBlockState()
                        : Blocks.BLACK_CONCRETE.defaultBlockState());
            }
            for (int z = -75; z <= -36; z++)
            {
                for (int width = -3; width <= 3; width++)
                {
                    set(level, origin.offset(x + width, 1, z),
                            width == 0 && Math.floorMod(z, 6) < 3
                                    ? Blocks.YELLOW_CONCRETE.defaultBlockState()
                                    : Blocks.GRAY_CONCRETE.defaultBlockState());
                }
            }
            buildLiftGantry(level, centre, accent);
        }
    }

    /** Removes only carrier residue inside the three audited 11x11 lift paths. */
    private static void clearLiftCorridor(ServerLevel level, BlockPos centre)
    {
        for (int y = 2; y <= 32; y++)
        {
            for (int x = -5; x <= 5; x++)
            {
                for (int z = -5; z <= 5; z++)
                {
                    set(level, centre.offset(x, y, z), Blocks.AIR.defaultBlockState());
                }
            }
        }
    }

    /** Reachable rear service deck aligned with the real EVA entry-plug socket. */
    private static void buildLiftGantry(ServerLevel level, BlockPos centre,
                                         BlockState accent)
    {
        BlockState frame = Blocks.IRON_BLOCK.defaultBlockState();
        BlockState dark = Blocks.BLACK_CONCRETE.defaultBlockState();
        BlockState light = Blocks.SEA_LANTERN.defaultBlockState();
        BlockState ladder = Blocks.LADDER.defaultBlockState()
                .setValue(LadderBlock.FACING, Direction.NORTH);
        int gantryY = 27;

        for (int y = 2; y <= gantryY; y++)
        {
            set(level, centre.offset(0, y, 14), frame);
            set(level, centre.offset(0, y, 13), ladder);
            if (y % 4 == 0)
            {
                set(level, centre.offset(1, y, 14), light);
            }
        }
        for (int z = 6; z <= 14; z++)
        {
            for (int x = -3; x <= 3; x++)
            {
                BlockState deck = x == 0 && z == 13
                        ? ladder : (x == 0 && z % 3 == 0 ? accent : dark);
                set(level, centre.offset(x, gantryY, z), deck);
                if (Math.abs(x) == 3)
                {
                    set(level, centre.offset(x, gantryY + 1, z),
                            Blocks.IRON_BARS.defaultBlockState());
                    set(level, centre.offset(x, gantryY + 3, z), frame);
                }
            }
            set(level, centre.offset(0, gantryY + 4, z),
                    z % 3 == 0 ? light : frame);
        }
    }

    private static void buildCommandBridge(ServerLevel level, BlockPos origin)
    {
        for (int z = 35; z <= 100; z++)
        {
            for (int x = -4; x <= 4; x++)
            {
                set(level, origin.offset(x, 2, z), x == 0 && z % 8 < 4
                        ? Blocks.SEA_LANTERN.defaultBlockState()
                        : Blocks.IRON_BLOCK.defaultBlockState());
            }
            set(level, origin.offset(-5, 3, z), Blocks.IRON_BARS.defaultBlockState());
            set(level, origin.offset(5, 3, z), Blocks.IRON_BARS.defaultBlockState());
        }
    }

    private static void buildArtificialSun(ServerLevel level, BlockPos origin)
    {
        int radius = 11;
        for (int x = -radius; x <= radius; x++)
        {
            for (int z = -radius; z <= radius; z++)
            {
                if (x * x + z * z > radius * radius)
                {
                    continue;
                }
                set(level, origin.offset(x, ARTIFICIAL_SUN_Y, z),
                        Blocks.SEA_LANTERN.defaultBlockState());
                set(level, origin.offset(x, ARTIFICIAL_SUN_Y - 1, z),
                        Blocks.YELLOW_STAINED_GLASS.defaultBlockState());
            }
        }
        for (int y = ARTIFICIAL_SUN_Y - 8; y <= ARTIFICIAL_SUN_Y + 4; y++)
        {
            if (y == ARTIFICIAL_SUN_Y || y == ARTIFICIAL_SUN_Y - 1)
            {
                continue;
            }
            set(level, origin.offset(0, y, 0), Blocks.LIGHT.defaultBlockState());
        }
    }

    private static void buildForestRing(ServerLevel level, BlockPos origin)
    {
        for (int x = -96; x <= 96; x += 8)
        {
            for (int z = -96; z <= 96; z += 8)
            {
                int distanceSqr = x * x + z * z;
                if (distanceSqr < 76 * 76 || distanceSqr > 100 * 100
                        || Math.floorMod(x * 13 + z * 19, 5) > 1)
                {
                    continue;
                }
                int height = 3 + Math.floorMod(x * 7 + z * 11, 3);
                for (int y = 1; y <= height; y++)
                {
                    set(level, origin.offset(x, y, z),
                            Blocks.DARK_OAK_LOG.defaultBlockState());
                }
                for (int dx = -2; dx <= 2; dx++)
                {
                    for (int dz = -2; dz <= 2; dz++)
                    {
                        if (Math.abs(dx) + Math.abs(dz) <= 3)
                        {
                            set(level, origin.offset(x + dx, height + 1, z + dz),
                                    Blocks.DARK_OAK_LEAVES.defaultBlockState());
                        }
                    }
                }
            }
        }
    }

    private static void buildObservationDeck(ServerLevel level, BlockPos origin)
    {
        BlockPos centre = origin.offset(0, 0, OBSERVATION_Z);
        for (int y = 1; y <= OBSERVATION_Y; y++)
        {
            for (int x : new int[] {-5, 5})
            {
                for (int z : new int[] {-5, 5})
                {
                    set(level, centre.offset(x, y, z), Blocks.IRON_BLOCK.defaultBlockState());
                }
            }
        }
        fillSquare(level, centre, OBSERVATION_Y, 8,
                Blocks.SMOOTH_STONE.defaultBlockState());
        for (int i = -8; i <= 8; i++)
        {
            set(level, centre.offset(-8, OBSERVATION_Y + 1, i),
                    Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(8, OBSERVATION_Y + 1, i),
                    Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(i, OBSERVATION_Y + 1, -8),
                    Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(i, OBSERVATION_Y + 1, 8),
                    Blocks.IRON_BARS.defaultBlockState());
        }
        set(level, centre.offset(0, OBSERVATION_Y, 0),
                Blocks.LODESTONE.defaultBlockState());
    }

    private static boolean isCavernStone(BlockState state)
    {
        return state.is(Blocks.DEEPSLATE) || state.is(Blocks.CALCITE)
                || state.is(Blocks.POLISHED_BASALT);
    }

    private static void squarePerimeter(ServerLevel level, BlockPos centre,
                                        int y, int half, BlockState state)
    {
        for (int i = -half; i <= half; i++)
        {
            set(level, centre.offset(-half, y, i), state);
            set(level, centre.offset(half, y, i), state);
            set(level, centre.offset(i, y, -half), state);
            set(level, centre.offset(i, y, half), state);
        }
    }

    private static void fillSquare(ServerLevel level, BlockPos centre, int y,
                                   int half, BlockState state)
    {
        for (int x = -half; x <= half; x++)
        {
            for (int z = -half; z <= half; z++)
            {
                set(level, centre.offset(x, y, z), state);
            }
        }
    }

    private static void set(ServerLevel level, BlockPos position, BlockState state)
    {
        level.setBlock(position, state, UPDATE_CLIENTS);
    }

    public record GeoFrontAudit(boolean valid, boolean floor, boolean wall,
                                boolean lake, boolean pyramid, boolean sun,
                                int lifts, int gantries, boolean bridge,
                                boolean observation,
                                NervOperationsCentreBuilder.OperationsAudit operations)
    {
        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s floor=%s wall=%s lclLake=%s nervPyramid=%s "
                            + "artificialSun=%s lifts=%d/3 gantries=%d/3 "
                            + "commandBridge=%s observation=%s operations={%s}",
                    this.valid, this.floor, this.wall, this.lake, this.pyramid,
                    this.sun, this.lifts, this.gantries, this.bridge,
                    this.observation, this.operations.summary());
        }
    }
}
