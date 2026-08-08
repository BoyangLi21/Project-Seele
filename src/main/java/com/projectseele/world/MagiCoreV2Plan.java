package com.projectseele.world;

import java.util.List;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockState;

/** Three-core MAGI chamber below the continuous command volume. */
public final class MagiCoreV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "MAGI_CORE";
    private static final String STAGE = "S02_L_MAGI_CORE";
    private static final String PLAN_VERSION = "magi-core-v2-a3";

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
    private static final BlockState GREEN =
            Blocks.GREEN_CONCRETE.defaultBlockState();
    private static final BlockState PURPLE =
            Blocks.PURPLE_CONCRETE.defaultBlockState();
    private static final BlockState CYAN =
            Blocks.CYAN_CONCRETE.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.TINTED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState RAIL =
            Blocks.IRON_BARS.defaultBlockState();
    private static final BlockState SOUTH_STAIR =
            Blocks.POLISHED_DIORITE_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.SOUTH);

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public MagiCoreV2Plan(FacilitySchemaV2.ResolvedManifest manifest)
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
        if (x == -40 || x == 39 || z == -40 || z == 39
                || y == -400 || y == -369)
        {
            return Math.floorMod(x + z + y, 17) <= 1 ? RED : SHELL;
        }
        return AIR;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        // Lower observation/service ring and spokes.
        if (y == -396
                && ((Math.abs(x) >= 30 || Math.abs(z) >= 30)
                || Math.abs(x) <= 4 || Math.abs(z) <= 4))
        {
            return Math.floorMod(x + z, 11) == 0 ? LIGHT : FLOOR;
        }
        if (y == -395
                && ((Math.abs(x) == 29 && Math.abs(z) >= 7)
                || (Math.abs(z) == 29 && Math.abs(x) >= 7)))
        {
            return RAIL;
        }

        /*
         * A straight, supported secure descent from the command-room
         * aperture. The reciprocal vertical port clears y=-369 and its inner
         * safety layer y=-370 across x[25,31]/z[21,27]. The old first treads
         * occupied that cleared layer, leaving only two edge strips and a
         * long fall. A full landing now sits one block below the cleared
         * aperture, then the stairs descend due north to the MAGI ring.
         */
        for (int step = 0; step < 25; step++)
        {
            int stepZ = 16 - step;
            int treadY = -372 - step;
            if (x >= 24 && x <= 32 && z == stepZ)
            {
                if (y == treadY)
                {
                    return SOUTH_STAIR;
                }
                if (y >= -399 && y < treadY)
                {
                    return STRUCTURE;
                }
            }
            if ((x == 24 || x == 32) && z == stepZ
                    && y == treadY + 1)
            {
                return RAIL;
            }
        }
        if (y == -371 && x >= 20 && x <= 36
                && z >= 17 && z <= 32)
        {
            return FLOOR;
        }
        if (y == -370
                && (((x == 20 || x == 36)
                && z >= 17 && z <= 32)
                || (z == 32 && x >= 20 && x <= 36)))
        {
            return RAIL;
        }
        if (y == -396 && x >= 20 && x <= 36
                && z >= -8 && z <= 4)
        {
            return FLOOR;
        }

        BlockState core = magiCore(x, y, z, -23, -14, GREEN);
        if (core != null)
        {
            return core;
        }
        core = magiCore(x, y, z, 23, -14, PURPLE);
        if (core != null)
        {
            return core;
        }
        core = magiCore(x, y, z, 0, 18, CYAN);
        if (core != null)
        {
            return core;
        }

        // Southern secure gallery reaches the registered Dogma spine port.
        if (y == -396 && x >= 24 && x <= 39 && z >= 30 && z <= 39)
        {
            return Math.floorMod(x + z, 7) == 0 ? LIGHT : FLOOR;
        }
        if ((x == 24 || x == 39) && y >= -395 && y <= -389
                && z >= 30 && z <= 39)
        {
            return y == -392 ? RED : STRUCTURE;
        }
        return null;
    }

    private static BlockState magiCore(int x, int y, int z,
                                       int centreX, int centreZ,
                                       BlockState accent)
    {
        int dx = Math.abs(x - centreX);
        int dz = Math.abs(z - centreZ);
        if (dx > 9 || dz > 9 || y < -395 || y > -375)
        {
            return null;
        }
        boolean frame = dx >= 8 || dz >= 8 || y == -395 || y == -375;
        if (frame)
        {
            if (y == -392 || y == -378)
            {
                return accent;
            }
            return STRUCTURE;
        }
        if ((dx == 6 || dz == 6) && y >= -390 && y <= -380)
        {
            return GLASS;
        }
        if ((dx <= 2 || dz <= 2)
                && Math.floorMod(y + 395, 5) <= 1)
        {
            return Math.floorMod(x + z, 3) == 0 ? LIGHT : accent;
        }
        return DARK;
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
