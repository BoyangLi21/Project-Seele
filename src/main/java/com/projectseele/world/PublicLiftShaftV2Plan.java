package com.projectseele.world;

import java.util.List;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.block.LadderBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.AttachFace;

/**
 * Permanent H-01 public lift shaft between Tokyo-3 and the GeoFront.
 *
 * <p>The construction plan owns only fixed civil works: shaft, landings,
 * pressure thresholds and an emergency ladder. The saved cabin, interlocks
 * and moving doors are installed by the runtime lift director.</p>
 */
public final class PublicLiftShaftV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "PUBLIC_LIFT_SHAFT";
    private static final String STAGE = "S02_G_PUBLIC_LIFT_SHAFT";
    private static final String PLAN_VERSION = "public-lift-shaft-v2-a2";

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();
    private static final BlockState SHELL =
            Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
    private static final BlockState STRUCTURE =
            Blocks.DEEPSLATE_TILES.defaultBlockState();
    private static final BlockState FLOOR =
            Blocks.SMOOTH_STONE.defaultBlockState();
    private static final BlockState DARK =
            Blocks.BLACK_CONCRETE.defaultBlockState();
    private static final BlockState ORANGE =
            Blocks.ORANGE_CONCRETE.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.GRAY_STAINED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState RAIL =
            Blocks.IRON_BARS.defaultBlockState();
    private static final BlockState LADDER =
            Blocks.LADDER.defaultBlockState()
                    .setValue(LadderBlock.FACING, Direction.WEST);
    private static final BlockState LOWER_BUTTON =
            Blocks.STONE_BUTTON.defaultBlockState()
                    .setValue(ButtonBlock.FACE, AttachFace.WALL)
                    .setValue(ButtonBlock.FACING, Direction.EAST);
    private static final BlockState UPPER_BUTTON =
            Blocks.STONE_BUTTON.defaultBlockState()
                    .setValue(ButtonBlock.FACE, AttachFace.WALL)
                    .setValue(ButtonBlock.FACING, Direction.WEST);

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final int surfaceY;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public PublicLiftShaftV2Plan(
            FacilitySchemaV2.ResolvedManifest manifest)
    {
        this.owner = manifest.requireZone(ZONE_ID).owner();
        this.centreX = manifest.centre().getX();
        this.centreZ = manifest.centre().getZ();
        this.surfaceY = manifest.surfaceY();
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
        if (x == -12 || x == 11 || z == 220 || z == 243
                || y == -368 || y == this.surfaceY + 15)
        {
            return shellPattern(x, y, z);
        }
        return AIR;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        if (x == -9 && y == -350 && z == 223)
        {
            return LOWER_BUTTON;
        }
        if (x == -9 && y == -349 && z == 223)
        {
            return LOWER_BUTTON;
        }
        if (x == 8 && y == this.surfaceY + 2 && z == 240)
        {
            return UPPER_BUTTON;
        }
        if (x == 8 && y == this.surfaceY + 3 && z == 240)
        {
            return UPPER_BUTTON;
        }

        // Central 10x12 clear shaft, sized for the persistent 5x5 cabin plus
        // inspection clearance. Its walls exist for the full journey.
        if (x >= -6 && x <= 5 && z >= 226 && z <= 237
                && y >= -367 && y <= this.surfaceY + 14)
        {
            boolean wall = x == -6 || x == 5 || z == 226 || z == 237;
            boolean lowerDoor = z == 226 && x >= -3 && x <= 2
                    && y >= -352 && y <= -347;
            boolean upperDoor = z == 237 && x >= -3 && x <= 2
                    && y >= this.surfaceY
                    && y <= this.surfaceY + 5;
            if (wall && !lowerDoor && !upperDoor)
            {
                if (Math.floorMod(y + 368, 16) == 0
                        && (x == -6 || x == 5))
                {
                    return LIGHT;
                }
                return STRUCTURE;
            }
            if (!wall && y == -367)
            {
                return Math.floorMod(x + z, 5) == 0 ? ORANGE : FLOOR;
            }
        }

        // Lower GeoFront landing and upper Tokyo-3 landing. Both have full
        // floors, ceiling, side walls and a six-block-deep cabin threshold.
        BlockState lower = landing(x, y, z, -353, 220, 227,
                Direction.NORTH);
        if (lower != null)
        {
            return lower;
        }
        BlockState upper = landing(x, y, z, this.surfaceY - 1, 237, 244,
                Direction.SOUTH);
        if (upper != null)
        {
            return upper;
        }

        // A continuous emergency ladder and refuge ledges mean a power loss
        // cannot turn the vertical link into an inaccessible teleport tube.
        if (x == 10 && z == 232 && y >= -351 && y <= this.surfaceY + 1)
        {
            return LADDER;
        }
        if (x == 11 && z == 232 && y >= -352 && y <= this.surfaceY + 2)
        {
            return STRUCTURE;
        }
        if (Math.floorMod(y + 352, 16) == 0
                && y >= -352 && y <= this.surfaceY
                && x >= 6 && x <= 10 && z >= 229 && z <= 235)
        {
            if (x == 10 && z == 232)
            {
                return AIR;
            }
            return FLOOR;
        }
        if (Math.floorMod(y + 351, 16) == 0
                && y >= -351 && y <= this.surfaceY + 1
                && ((x == 6 && z >= 229 && z <= 235)
                || (z == 229 && x >= 6 && x <= 10)
                || (z == 235 && x >= 6 && x <= 10)))
        {
            return RAIL;
        }

        // Vertical service rails and alternating warning datum.
        if ((x == -9 || x == 8) && (z == 223 || z == 240)
                && y >= -367 && y <= this.surfaceY + 14)
        {
            return Math.floorMod(y + 368, 12) <= 1 ? ORANGE : SHELL;
        }
        return null;
    }

    private BlockState landing(int x, int y, int z, int floorY,
                               int minZ, int maxZ, Direction exterior)
    {
        if (x < -10 || x > 9 || z < minZ || z >= maxZ)
        {
            return null;
        }
        if (y == floorY)
        {
            return Math.floorMod(x + z, 9) == 0 ? LIGHT : FLOOR;
        }
        if (y == floorY + 7)
        {
            return Math.floorMod(x - z, 7) == 0 ? LIGHT : STRUCTURE;
        }
        boolean lowerControlBacking = exterior == Direction.NORTH
                && x == -10 && z == minZ + 3;
        boolean upperControlBacking = exterior == Direction.SOUTH
                && x == 9 && z == maxZ - 4;
        if ((lowerControlBacking || upperControlBacking)
                && y >= floorY + 2 && y <= floorY + 5)
        {
            return y == floorY + 2 ? LIGHT : DARK;
        }
        if ((x == -10 || x == 9) && y > floorY && y < floorY + 7)
        {
            return y == floorY + 3 ? GLASS : STRUCTURE;
        }

        int innerZ = exterior == Direction.NORTH ? maxZ - 1 : minZ;
        if (z == innerZ && y > floorY && y < floorY + 7
                && (x < -3 || x > 2))
        {
            return y == floorY + 3 ? ORANGE : STRUCTURE;
        }

        // Large fixed panels flank the doorway. The call and destination
        // buttons are permanent fixtures; a missing cabin leaves them
        // visibly present but the runtime reports OUT OF SERVICE.
        int panelZ = exterior == Direction.NORTH ? minZ + 2 : maxZ - 3;
        if (z == panelZ && (x == -8 || x == 7)
                && y >= floorY + 1 && y <= floorY + 5)
        {
            return y == floorY + 3 ? LIGHT : DARK;
        }
        return null;
    }

    private static BlockState shellPattern(int x, int y, int z)
    {
        if (Math.floorMod(y + 368, 16) <= 1
                || Math.floorMod(x + z, 18) == 0)
        {
            return ORANGE;
        }
        return SHELL;
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
