package com.projectseele.world;

import java.util.List;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockState;

/** Monumental, supported descent from the Dogma lift to the Lilith gate. */
public final class DogmaSpineV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "DOGMA_SPINE";
    private static final String STAGE = "S02_O_DOGMA_SPINE";
    private static final String PLAN_VERSION = "dogma-spine-v2-a2";

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();
    private static final BlockState SHELL =
            Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
    private static final BlockState STRUCTURE =
            Blocks.DEEPSLATE_TILES.defaultBlockState();
    private static final BlockState FLOOR =
            Blocks.POLISHED_DEEPSLATE.defaultBlockState();
    private static final BlockState DARK =
            Blocks.BLACK_CONCRETE.defaultBlockState();
    private static final BlockState RED =
            Blocks.RED_CONCRETE.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.RED_STAINED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState RAIL =
            Blocks.IRON_BARS.defaultBlockState();
    private static final BlockState NORTH_STAIR =
            Blocks.POLISHED_DIORITE_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.NORTH);

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public DogmaSpineV2Plan(FacilitySchemaV2.ResolvedManifest manifest)
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
        if (x == -40 || x == 79 || z == 184 || z == 319
                || y == -656 || y == -521)
        {
            return Math.floorMod(y + z, 19) <= 1 ? RED : SHELL;
        }
        return AIR;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        // Upper lift hall.
        if (y == -577 && x >= 18 && x <= 46
                && z >= 184 && z < 212)
        {
            return floorPattern(x, z);
        }

        // Thirty-six broad north-facing steps descend south from the lift
        // hall to the Terminal Dogma datum.
        for (int step = 0; step < 36; step++)
        {
            int stepZ = 212 + step;
            int treadY = -578 - step;
            if (x >= 24 && x <= 40 && z == stepZ)
            {
                if (y == treadY)
                {
                    return NORTH_STAIR;
                }
                if (y >= -655 && y < treadY)
                {
                    return STRUCTURE;
                }
            }
        }

        // Lower processional gallery turns once onto the registered Lilith
        // centreline. Wide landings keep the turn explicit and supported.
        if (y == -613 && x >= -12 && x <= 44
                && z >= 247 && z <= 266)
        {
            return floorPattern(x, z);
        }
        if (y == -613 && x >= -8 && x <= 8
                && z >= 266 && z <= 319)
        {
            return floorPattern(x, z);
        }

        if (((x == -12 || x == 44) && z >= 247 && z <= 266)
                || ((x == -8 || x == 8) && z >= 266 && z <= 319))
        {
            if (y >= -612 && y <= -600)
            {
                return y == -606 ? GLASS : STRUCTURE;
            }
        }
        if (y == -599
                && ((x >= -12 && x <= 44 && z >= 247 && z <= 266)
                || (x >= -8 && x <= 8 && z >= 266 && z <= 319)))
        {
            return Math.floorMod(x + z, 9) <= 1 ? LIGHT : SHELL;
        }

        // Repeated blast ribs and warning pylons create Central Dogma scale
        // without filling the chamber with disconnected decorative stairs.
        if (z >= 272 && z <= 312
                && Math.floorMod(z - 272, 10) == 0
                && (x == -11 || x == 11)
                && y >= -613 && y <= -592)
        {
            return y == -602 ? RED : STRUCTURE;
        }
        if (y == -612 && z >= 248 && z <= 318
                && (x == -13 || x == 45))
        {
            return RAIL;
        }
        return null;
    }

    private static BlockState floorPattern(int x, int z)
    {
        if (Math.floorMod(x, 8) == 0 || Math.floorMod(z, 8) == 0)
        {
            return DARK;
        }
        return Math.floorMod(x + z, 13) == 0 ? LIGHT : FLOOR;
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
