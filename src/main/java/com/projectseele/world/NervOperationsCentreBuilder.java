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
        buildLowerConcourse(level, origin);
        buildOperationsHall(level, origin);
        buildAccessStairs(level, origin);
        buildLiftTransit(level, origin);
    }

    public static OperationsAudit inspect(ServerLevel level, BlockPos origin)
    {
        boolean entrance = level.getBlockState(origin.offset(0, 7, 34))
                .is(Blocks.ORANGE_CONCRETE);
        boolean tacticalTable = level.getBlockState(origin.offset(0, 8, 0))
                .is(Blocks.BEACON);
        boolean display = level.getBlockState(origin.offset(0, 11, DISPLAY_Z))
                .is(Blocks.RED_STAINED_GLASS);
        boolean stairs = level.getBlockState(origin.offset(-13, 2, 22))
                .is(Blocks.SMOOTH_QUARTZ_STAIRS);
        int consoles = 0;
        for (int x : new int[] {-10, 0, 10})
        {
            if (level.getBlockState(origin.offset(x, 9, 6)).is(Blocks.COMPARATOR))
            {
                consoles++;
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
        boolean valid = entrance && tacticalTable && display && stairs
                && consoles == 3 && transitLinks == 3 && connectedRoutes;
        return new OperationsAudit(valid, entrance, tacticalTable, display,
                stairs, consoles, transitLinks, connectedRoutes);
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

    private static boolean walkable(ServerLevel level, BlockPos feet)
    {
        return !level.getBlockState(feet.below()).isAir()
                && level.getBlockState(feet).isAir()
                && level.getBlockState(feet.above()).isAir();
    }

    private static void set(ServerLevel level, BlockPos position, BlockState state)
    {
        level.setBlock(position, state, UPDATE_CLIENTS);
    }

    public record OperationsAudit(boolean valid, boolean entrance,
                                  boolean tacticalTable, boolean display,
                                  boolean stairs, int consoles,
                                  int transitLinks, boolean connectedRoutes)
    {
        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s entrance=%s tacticalTable=%s display=%s stairs=%s "
                            + "consoles=%d/3 transit=%d/3 connectedRoutes=%s",
                    this.valid, this.entrance, this.tacticalTable, this.display,
                    this.stairs, this.consoles, this.transitLinks,
                    this.connectedRoutes);
        }
    }
}
