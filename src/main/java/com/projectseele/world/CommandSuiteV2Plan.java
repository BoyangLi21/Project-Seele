package com.projectseele.world;

import java.util.List;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Separate executive suite reached through the secure command spine.
 *
 * <p>The suite contains a full-size commander's office, conversation room and
 * a supported vestibule. It is intentionally not faked as a door immediately
 * behind the commander's seat.</p>
 */
public final class CommandSuiteV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "COMMAND_SUITE";
    private static final String STAGE = "S02_C_COMMAND_SUITE";
    private static final String PLAN_VERSION = "command-suite-v2-a4";

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();
    private static final BlockState SHELL =
            Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
    private static final BlockState FLOOR =
            Blocks.SMOOTH_STONE.defaultBlockState();
    private static final BlockState WALL =
            Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState();
    private static final BlockState DARK =
            Blocks.BLACK_CONCRETE.defaultBlockState();
    private static final BlockState RED =
            Blocks.RED_CONCRETE.defaultBlockState();
    private static final BlockState ORANGE =
            Blocks.ORANGE_CONCRETE.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.TINTED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState CHAIR =
            Blocks.POLISHED_BLACKSTONE_BRICK_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.NORTH);
    private static final BlockState SOUTH_STAIR =
            Blocks.SMOOTH_QUARTZ_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.SOUTH);

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public CommandSuiteV2Plan(
            FacilitySchemaV2.ResolvedManifest manifest)
    {
        this.owner = manifest.requireZone(ZONE_ID).owner();
        this.centreX = manifest.centre().getX();
        this.centreZ = manifest.centre().getZ();
        this.ports = manifest.ports().stream()
                .filter(port -> ZONE_ID.equals(port.zoneId()))
                .toList();
        this.buildPlanHash = FacilityV2Hashing.buildPlanHash(
                ZONE_ID, STAGE, PLAN_VERSION, this.owner);
    }

    @Override
    public String zoneId()
    {
        return ZONE_ID;
    }

    @Override
    public String stage()
    {
        return STAGE;
    }

    @Override
    public String buildPlanHash()
    {
        return this.buildPlanHash;
    }

    @Override
    public FacilitySchemaV2.IntBox owner()
    {
        return this.owner;
    }

    @Override
    public BlockState blockAt(BlockPos position)
    {
        int x = position.getX() - this.centreX;
        int y = position.getY();
        int z = position.getZ() - this.centreZ;

        if (isPortTunnel(position))
        {
            return AIR;
        }

        BlockState authored = authoredBlock(x, y, z);
        if (authored != null)
        {
            return authored;
        }
        if (x == 72 || x == 127 || z == -56 || z == 55
                || y == -344 || y == -313)
        {
            return Math.floorMod(x + y + z, 19) == 0 ? ORANGE : SHELL;
        }
        return AIR;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        // Twelve-block secure anteroom plus a separate eight-block corridor.
        // The suite port first lands here rather than opening into an office.
        if (x >= 72 && x < 98 && z >= -5 && z < 5)
        {
            if (y == -325)
            {
                return floorPattern(x, z);
            }
            if (y == -319)
            {
                return Math.floorMod(x + z, 9) == 0 ? LIGHT : DARK;
            }
            if ((z == -5 || z == 4) && y >= -324 && y < -319)
            {
                return y == -321 ? GLASS : WALL;
            }
        }

        // Gendo's office: independent 32 x 48 x 16 volume.
        if (x >= 92 && x < 124 && z >= -48 && z < 0
                && y >= -328 && y < -312)
        {
            boolean floor = y == -328;
            boolean ceiling = y == -313;
            boolean wall = x == 92 || x == 123
                    || z == -48 || z == -1;
            boolean doorway = z == -1 && x >= 98 && x <= 104
                    && y >= -324 && y <= -319;
            boolean stairThreshold = z == -1
                    && x >= 98 && x <= 104 && y == -325;
            if (doorway)
            {
                return AIR;
            }
            if (floor)
            {
                return Math.floorMod(x + z, 13) == 0 ? RED : DARK;
            }
            if (ceiling)
            {
                return Math.floorMod(x - z, 8) == 0 ? LIGHT : WALL;
            }
            if (wall && !stairThreshold)
            {
                boolean windowBand = y >= -324 && y <= -318
                        && (x == 92 || x == 123);
                return windowBand ? GLASS : WALL;
            }
        }

        // Axial office approach and three-step descent.
        if (x >= 96 && x < 106 && z >= -6 && z < 2)
        {
            // z=-3..-1 is the real three-tread descent into the office.
            // A former continuous y=-325 approach floor covered the lower
            // two stair blocks and made the doorway appear level while the
            // office floor sat three blocks below.
            if (y == -325 && (z < -3 || z > -1))
            {
                return floorPattern(x, z);
            }
            if ((x == 96 || x == 105) && y >= -324 && y <= -319)
            {
                return WALL;
            }
        }
        for (int step = 1; step <= 3; step++)
        {
            int stepZ = -step;
            int treadY = -324 - step;
            if (x >= 98 && x <= 104 && z == stepZ)
            {
                if (y == treadY)
                {
                    return SOUTH_STAIR;
                }
                if (y >= -343 && y < treadY)
                {
                    return WALL;
                }
            }
        }

        // Fuyutsuki/Gendo conversation room: 24 x 18 x 10.
        if (x >= 92 && x < 116 && z >= 12 && z < 30
                && y >= -326 && y < -316)
        {
            boolean floor = y == -326;
            boolean ceiling = y == -317;
            boolean wall = x == 92 || x == 115
                    || z == 12 || z == 29;
            boolean doorway = z == 12 && x >= 98 && x <= 104
                    && y >= -325 && y <= -320;
            if (doorway)
            {
                return AIR;
            }
            if (floor)
            {
                return Math.floorMod(x + z, 9) == 0 ? ORANGE : FLOOR;
            }
            if (ceiling)
            {
                return Math.floorMod(x - z, 7) == 0 ? LIGHT : DARK;
            }
            if (wall)
            {
                return y == -322 ? GLASS : WALL;
            }
        }

        // Conversation-room approach and one-block threshold descent.
        if (x >= 96 && x <= 106 && z >= 4 && z <= 13)
        {
            if (y == -325)
            {
                return floorPattern(x, z);
            }
            if ((x == 96 || x == 106) && y >= -324 && y <= -319)
            {
                return WALL;
            }
        }
        if (x >= 98 && x <= 104 && z == 11 && y == -326)
        {
            return FLOOR;
        }

        // Office desk, two seats and a restrained ceiling datum. These are
        // legible landmarks rather than an invented "official" floor plan.
        if (y == -327 && z >= -34 && z <= -30
                && x >= 98 && x <= 118)
        {
            return x == 98 || x == 118 ? RED : DARK;
        }
        if (y == -327 && z == -28 && (x == 102 || x == 112))
        {
            return CHAIR;
        }
        if (y == -314 && x >= 94 && x <= 120
                && z >= -44 && z <= -8
                && (x == 94 || x == 120 || z == -44 || z == -8
                || x == 107))
        {
            return RED;
        }
        return null;
    }

    private static BlockState floorPattern(int x, int z)
    {
        if (Math.floorMod(x, 8) == 0 || Math.floorMod(z, 8) == 0)
        {
            return DARK;
        }
        return Math.floorMod(x + z, 15) == 0 ? LIGHT : FLOOR;
    }

    private boolean isPortTunnel(BlockPos position)
    {
        for (FacilitySchemaV2.PortSpec port : this.ports)
        {
            FacilitySchemaV2.IntBox aperture = port.aperture();
            FacilitySchemaV2.IntBox inner = aperture.offset(
                    -port.facing().getStepX(),
                    -port.facing().getStepY(),
                    -port.facing().getStepZ());
            if (contains(aperture, position) || contains(inner, position))
            {
                return true;
            }
        }
        return false;
    }

    private static boolean contains(FacilitySchemaV2.IntBox box,
                                    BlockPos position)
    {
        return position.getX() >= box.minX()
                && position.getX() < box.maxX()
                && position.getY() >= box.minY()
                && position.getY() < box.maxY()
                && position.getZ() >= box.minZ()
                && position.getZ() < box.maxZ();
    }
}
