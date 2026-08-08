package com.projectseele.world;

import java.util.List;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Fixed Tokyo-3 surface station and boulevard approach.
 *
 * <p>Only the route envelope is cleared. Natural terrain, vegetation and the
 * future city outside the authored right-of-way remain untouched.</p>
 */
public final class SurfaceTransitV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "SURFACE_TRANSIT";
    private static final String STAGE = "S02_H_SURFACE_TRANSIT";
    private static final String PLAN_VERSION = "surface-transit-v2-a1";

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

    public SurfaceTransitV2Plan(
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

        // Clear only the station and boulevard headroom, not the entire
        // surface owner. This keeps the route embedded in a normal world.
        if (inRightOfWay(x, z) && y >= this.surfaceY
                && y <= this.surfaceY + 12)
        {
            BlockState authored = authoredBlock(x, y, z);
            return authored == null ? AIR : authored;
        }

        BlockState authored = authoredBlock(x, y, z);
        return authored;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        // Continuous, level boulevard between the lift and city apron.
        if (y == this.surfaceY - 1 && x >= -22 && x <= 22
                && z >= 244 && z <= 371)
        {
            if (Math.abs(x) >= 19)
            {
                return WHITE;
            }
            if (x == 0 && Math.floorMod(z - 244, 8) < 4)
            {
                return ORANGE;
            }
            return Math.floorMod(x + z, 23) == 0 ? LIGHT : ROAD;
        }

        // Fill downward only under the built route. This resolves uneven
        // natural terrain without flattening the surrounding continent.
        if (y >= this.surfaceY - 16 && y < this.surfaceY - 1
                && x >= -22 && x <= 22 && z >= 244 && z <= 371)
        {
            boolean edgeSupport = Math.abs(x) >= 20;
            boolean pier = Math.floorMod(z - 244, 16) <= 2
                    && Math.floorMod(x + 20, 10) <= 2;
            return edgeSupport || pier ? STRUCTURE : null;
        }

        // Enclosed station head around the upper lift landing.
        if (x >= -28 && x <= 28 && z >= 245 && z <= 279
                && y >= this.surfaceY && y <= this.surfaceY + 9)
        {
            boolean side = x == -28 || x == 28;
            boolean north = z == 245;
            boolean roof = y == this.surfaceY + 9;
            boolean southFrame = z == 279 && (Math.abs(x) >= 18
                    || y >= this.surfaceY + 7);
            if (side || north || roof || southFrame)
            {
                if (roof && Math.floorMod(x + z, 9) <= 1)
                {
                    return LIGHT;
                }
                if (y >= this.surfaceY + 2
                        && y <= this.surfaceY + 7 && (side || north))
                {
                    return GLASS;
                }
                return Math.floorMod(x + y + z, 17) == 0
                        ? ORANGE : STRUCTURE;
            }
        }

        // Platform barriers end with the station. The open-city boulevard
        // deliberately has no endless fence after reaching land.
        if (y == this.surfaceY && z >= 246 && z <= 279
                && (x == -23 || x == 23))
        {
            return RAIL;
        }

        // Regular boulevard lights use solid pylons and do not form a fence.
        if (z >= 288 && z <= 368
                && Math.floorMod(z - 288, 24) == 0
                && (x == -27 || x == 27))
        {
            if (y >= this.surfaceY - 1 && y <= this.surfaceY + 6)
            {
                return y == this.surfaceY + 6 ? LIGHT : STRUCTURE;
            }
            if (y == this.surfaceY + 7 && Math.abs(x) == 27)
            {
                return LIGHT;
            }
        }
        return null;
    }

    private static boolean inRightOfWay(int x, int z)
    {
        return x >= -30 && x <= 30 && z >= 244 && z <= 371;
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
