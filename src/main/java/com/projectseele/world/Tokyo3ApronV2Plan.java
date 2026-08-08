package com.projectseele.world;

import java.util.List;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Authored Tokyo-3 arrival plaza at the public H-01 approach.
 *
 * <p>The north edge remains a physical construction wall until a later
 * schema epoch allocates the city streets. This owner therefore completes a
 * usable public destination without pretending that an unowned city exists.</p>
 */
public final class Tokyo3ApronV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "TOKYO3_APRON";
    private static final String STAGE = "S02_I_TOKYO3_APRON";
    private static final String PLAN_VERSION = "tokyo3-apron-v2-a1";

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();
    private static final BlockState STRUCTURE =
            Blocks.POLISHED_DEEPSLATE.defaultBlockState();
    private static final BlockState ROAD =
            Blocks.GRAY_CONCRETE.defaultBlockState();
    private static final BlockState DARK =
            Blocks.BLACK_CONCRETE.defaultBlockState();
    private static final BlockState WHITE =
            Blocks.WHITE_CONCRETE.defaultBlockState();
    private static final BlockState ORANGE =
            Blocks.ORANGE_CONCRETE.defaultBlockState();
    private static final BlockState RED =
            Blocks.RED_CONCRETE.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.LIGHT_BLUE_STAINED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState RAIL =
            Blocks.IRON_BARS.defaultBlockState();

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final int surfaceY;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public Tokyo3ApronV2Plan(
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

        // Remove terrain and foliage only inside the plaza construction
        // envelope. The surrounding continent is deliberately preserved.
        if (inBox(x, z, -58, 58, 372, 435)
                && y >= this.surfaceY && y <= this.surfaceY + 18)
        {
            return AIR;
        }
        return null;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        // The south boulevard enters a broad station plaza. Sidewalks,
        // service lanes and the centre guide remain readable from EVA scale.
        if (y == this.surfaceY - 1
                && inBox(x, z, -50, 50, 372, 428))
        {
            if (Math.abs(x) >= 43)
            {
                return WHITE;
            }
            if (Math.abs(x) >= 24)
            {
                return Math.floorMod(x + z, 17) == 0 ? LIGHT : DARK;
            }
            if (Math.abs(x) <= 1
                    && Math.floorMod(z - 372, 10) <= 4)
            {
                return ORANGE;
            }
            return ROAD;
        }

        // Route foundations absorb normal-world terrain variation without
        // flattening the rest of the city-side owner.
        if (y >= this.surfaceY - 16 && y < this.surfaceY - 1
                && inBox(x, z, -50, 50, 372, 428))
        {
            boolean perimeter = Math.abs(x) >= 47;
            boolean pier = Math.floorMod(x + 44, 16) <= 2
                    && Math.floorMod(z - 372, 16) <= 2;
            return perimeter || pier ? STRUCTURE : null;
        }

        // Covered arrival hall. It is large enough to read as civic
        // infrastructure rather than another tiny test booth.
        if (inBox(x, z, -54, 54, 386, 417)
                && y >= this.surfaceY && y <= this.surfaceY + 13)
        {
            boolean side = Math.abs(x) >= 51;
            boolean roof = y == this.surfaceY + 13;
            if (side || roof)
            {
                if (side && y >= this.surfaceY + 3
                        && y <= this.surfaceY + 10
                        && Math.floorMod(z - 386, 7) <= 4)
                {
                    return GLASS;
                }
                if (roof && Math.floorMod(x + 54, 12) <= 2)
                {
                    return LIGHT;
                }
                return STRUCTURE;
            }
        }

        // Four monumental portal pylons frame the future city boundary.
        if ((inBox(x, z, -51, -43, 424, 435)
                || inBox(x, z, 43, 51, 424, 435))
                && y >= this.surfaceY - 1
                && y <= this.surfaceY + 20)
        {
            if (Math.floorMod(y - this.surfaceY, 7) == 0)
            {
                return ORANGE;
            }
            return STRUCTURE;
        }

        // The current epoch has no legal city owner beyond this point.
        // Present that boundary as an intentional NERV construction gate,
        // never a road ending in exposed terrain or air.
        if (z >= 432 && z <= 435 && Math.abs(x) <= 42
                && y >= this.surfaceY - 1
                && y <= this.surfaceY + 12)
        {
            if (y == this.surfaceY + 4
                    || y == this.surfaceY + 5)
            {
                return RED;
            }
            if (Math.floorMod(x + 42, 12) <= 1)
            {
                return LIGHT;
            }
            return STRUCTURE;
        }

        // Independent lighting pylons stop before the sealed city gate and
        // do not become another continuous roadside fence.
        if ((x == -55 || x == 55)
                && (z == 378 || z == 402 || z == 426)
                && y >= this.surfaceY - 1
                && y <= this.surfaceY + 9)
        {
            return y >= this.surfaceY + 8 ? LIGHT : STRUCTURE;
        }
        if (y == this.surfaceY
                && (x == -51 || x == 50)
                && z >= 386 && z <= 417)
        {
            return RAIL;
        }
        return null;
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

    private static boolean inBox(int x, int z, int minX, int maxX,
                                 int minZ, int maxZ)
    {
        return x >= minX && x < maxX && z >= minZ && z < maxZ;
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
