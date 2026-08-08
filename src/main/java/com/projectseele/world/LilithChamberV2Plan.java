package com.projectseele.world;

import java.util.List;

import com.projectseele.registry.ModFluids;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Sealed Terminal Dogma containment cathedral and LCL lake.
 *
 * <p>The shell is an engineered ellipsoid inside the frozen owner. The
 * specimen itself is installed only after this plan receives a completion
 * receipt, so no persistent entity is spawned into a partial chamber.</p>
 */
public final class LilithChamberV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "LILITH_CHAMBER";
    private static final String STAGE = "S02_P_LILITH_CHAMBER";
    private static final String PLAN_VERSION = "lilith-chamber-v2-a1";

    private static final int CHAMBER_Y = -620;
    private static final int CHAMBER_Z = 432;
    private static final int LCL_Y = -652;
    private static final int LILITH_Z = 456;

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();
    private static final BlockState SHELL =
            Blocks.DEEPSLATE_BRICKS.defaultBlockState();
    private static final BlockState RIB =
            Blocks.POLISHED_BASALT.defaultBlockState();
    private static final BlockState STRUCTURE =
            Blocks.POLISHED_BLACKSTONE.defaultBlockState();
    private static final BlockState FLOOR =
            Blocks.POLISHED_DEEPSLATE.defaultBlockState();
    private static final BlockState DARK =
            Blocks.BLACK_CONCRETE.defaultBlockState();
    private static final BlockState RED =
            Blocks.REDSTONE_BLOCK.defaultBlockState();
    private static final BlockState RED_GLASS =
            Blocks.RED_STAINED_GLASS.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.TINTED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SHROOMLIGHT.defaultBlockState();
    private static final BlockState RAIL =
            Blocks.IRON_BARS.defaultBlockState();

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public LilithChamberV2Plan(
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

        double distance = square(x / 108.0D)
                + square((y - CHAMBER_Y) / 45.0D)
                + square((z - CHAMBER_Z) / 108.0D);
        if (distance > 1.0D)
        {
            return null;
        }
        if (distance >= 0.90D)
        {
            boolean horizontalRib = Math.floorMod(y - CHAMBER_Y, 8) == 0;
            boolean verticalRib = Math.floorMod(x + 108, 18) <= 1
                    && Math.floorMod(z - 324, 14) <= 1;
            return horizontalRib || verticalRib ? RIB : SHELL;
        }
        return AIR;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        // Sealed arrival vestibule and supported processional bridge.
        if (x >= -12 && x <= 12 && z >= 320 && z <= 352)
        {
            if (y == -613)
            {
                return Math.floorMod(x + z, 9) == 0 ? LIGHT : FLOOR;
            }
            if (y == -600)
            {
                return STRUCTURE;
            }
            if ((x == -12 || x == 12)
                    && y >= -612 && y <= -601)
            {
                return y == -606 ? RED_GLASS : STRUCTURE;
            }
        }
        if (y < -613 && y >= -667
                && (x == -10 || x == 10)
                && z >= 324 && z <= 352
                && Math.floorMod(z - 324, 12) <= 2)
        {
            return STRUCTURE;
        }

        // Observation bridge and U-shaped gallery remain outside the LCL
        // lake and face the specimen/cross as one readable composition.
        if (y == -613
                && ((x >= -10 && x <= 10 && z >= 352 && z <= 402)
                || (x >= -58 && x <= 58 && z >= 398 && z <= 410)
                || ((x >= -58 && x <= -50)
                || (x >= 50 && x <= 58))
                && z >= 410 && z <= 474))
        {
            return Math.floorMod(x + z, 11) == 0 ? LIGHT : FLOOR;
        }
        if (y == -612
                && ((x == -11 || x == 11) && z >= 352 && z <= 402
                || (z == 397 || z == 411) && Math.abs(x) <= 58
                || (x == -59 || x == 59) && z >= 410 && z <= 474))
        {
            return RAIL;
        }

        // Lower containment/service balcony.
        if (y == -641
                && ((Math.abs(x) >= 48 && Math.abs(x) <= 56
                && z >= 416 && z <= 490)
                || (Math.abs(x) <= 56 && z >= 482 && z <= 490)))
        {
            return Math.floorMod(x + z, 10) == 0 ? LIGHT : STRUCTURE;
        }

        // LCL lake with illuminated orange bed.
        double lake = square(x / 45.0D)
                + square((z - LILITH_Z) / 36.0D);
        if (lake <= 1.0D && y == -660)
        {
            return Math.floorMod(x * 17 + z * 29, 19) == 0
                    ? LIGHT : Blocks.ORANGE_CONCRETE.defaultBlockState();
        }
        if (lake <= 1.0D && y >= -659 && y <= LCL_Y)
        {
            return ModFluids.LCL_SOURCE.get().defaultFluidState()
                    .createLegacyBlock();
        }
        if (lake > 1.0D && lake <= 1.18D && y == LCL_Y)
        {
            return Math.floorMod(x + z, 7) == 0 ? LIGHT : STRUCTURE;
        }

        // Pure-red crucifix behind the local Lilith mesh.
        if (z >= LILITH_Z - 4 && z <= LILITH_Z - 2)
        {
            boolean vertical = Math.abs(x) <= 5
                    && y >= -655 && y <= -602;
            boolean horizontal = Math.abs(x) <= 28
                    && y >= -630 && y <= -621;
            if (vertical || horizontal)
            {
                boolean front = z == LILITH_Z - 2;
                if (front)
                {
                    return RED_GLASS;
                }
                if ((vertical && Math.floorMod(y + 655, 5) == 0)
                        || (horizontal && Math.floorMod(x + 28, 5) == 0))
                {
                    return LIGHT;
                }
                return RED;
            }
        }

        // Sparse quarantine pylons, intentionally not a wall of lights.
        if ((x == -72 || x == 72)
                && (z == 390 || z == 430 || z == 470 || z == 510)
                && y >= -652 && y <= -592)
        {
            if (Math.floorMod(y + 652, 12) <= 1)
            {
                return RED;
            }
            return Math.floorMod(y + 652, 6) == 0 ? LIGHT : DARK;
        }
        if (y == -651 && Math.abs(x) >= 48 && Math.abs(x) <= 76
                && z >= 388 && z <= 512
                && Math.floorMod(x + z, 13) <= 1)
        {
            return GLASS;
        }
        return null;
    }

    public BlockPos specimenAnchor()
    {
        return new BlockPos(this.centreX, LCL_Y,
                this.centreZ + LILITH_Z);
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

    private static double square(double value)
    {
        return value * value;
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
