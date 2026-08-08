package com.projectseele.world;

import java.util.List;
import java.util.Set;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Orthogonal public/service corridors outside the continuous command volume.
 *
 * <p>One implementation owns the repeated corridor grammar while each plan
 * remains constrained to exactly one manifest owner. Ends with unfinished
 * peers are closed by {@link FacilityV2RouteGateDirector}.</p>
 */
public final class PyramidCirculationV2Plan implements FacilityZonePlan
{
    private static final Set<String> SUPPORTED = Set.of(
            "WEST_SERVICE_SPINE",
            "EAST_SERVICE_SPINE",
            "STAFF_SERVICE_CONNECTOR");

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();
    private static final BlockState SHELL =
            Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
    private static final BlockState FLOOR =
            Blocks.POLISHED_DEEPSLATE.defaultBlockState();
    private static final BlockState DARK =
            Blocks.BLACK_CONCRETE.defaultBlockState();
    private static final BlockState ORANGE =
            Blocks.ORANGE_CONCRETE.defaultBlockState();
    private static final BlockState CYAN =
            Blocks.CYAN_CONCRETE.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.GRAY_STAINED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();

    private final String zoneId;
    private final String stage;
    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final int walkY;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public PyramidCirculationV2Plan(
            FacilitySchemaV2.ResolvedManifest manifest, String zoneId)
    {
        if (!SUPPORTED.contains(zoneId))
        {
            throw new IllegalArgumentException(
                    "Unsupported pyramid circulation owner " + zoneId);
        }
        this.zoneId = zoneId;
        this.stage = "S02_J_" + zoneId;
        this.owner = manifest.requireZone(zoneId).owner();
        this.centreX = manifest.centre().getX();
        this.centreZ = manifest.centre().getZ();
        this.walkY = "STAFF_SERVICE_CONNECTOR".equals(zoneId)
                ? -408 : -348;
        this.ports = manifest.ports().stream()
                .filter(port -> zoneId.equals(port.zoneId()))
                .toList();
        this.buildPlanHash = FacilityV2Hashing.buildPlanHash(
                zoneId, this.stage, "pyramid-circulation-v2-a1",
                this.owner);
    }

    @Override
    public String zoneId()
    {
        return this.zoneId;
    }

    @Override
    public String stage()
    {
        return this.stage;
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

        int minX = this.owner.minX() - this.centreX;
        int maxX = this.owner.maxX() - this.centreX - 1;
        int minZ = this.owner.minZ() - this.centreZ;
        int maxZ = this.owner.maxZ() - this.centreZ - 1;

        if (y == this.walkY - 1)
        {
            if (Math.floorMod(x, 16) == 0)
            {
                return LIGHT;
            }
            return Math.floorMod(z, 7) == 0 ? DARK : FLOOR;
        }
        if (y == this.walkY + 7)
        {
            return Math.floorMod(x, 12) <= 1 ? LIGHT : SHELL;
        }
        if ((z == minZ || z == maxZ)
                && y >= this.walkY && y <= this.walkY + 6)
        {
            if (y == this.walkY + 3
                    && Math.floorMod(x - minX, 12) >= 3
                    && Math.floorMod(x - minX, 12) <= 8)
            {
                return GLASS;
            }
            if (y == this.walkY + 1 || y == this.walkY + 2)
            {
                return "STAFF_SERVICE_CONNECTOR".equals(this.zoneId)
                        ? CYAN : ORANGE;
            }
            return SHELL;
        }
        if ((x == minX || x == maxX)
                && y >= this.walkY - 1 && y <= this.walkY + 7)
        {
            return SHELL;
        }
        if (y < this.walkY - 1)
        {
            // A regular support grid makes long corridors structurally
            // legible from the GeoFront instead of floating in the cavern.
            boolean support = Math.floorMod(x - minX, 20) <= 2
                    && (z <= minZ + 2 || z >= maxZ - 2);
            return support ? SHELL : null;
        }
        if (y >= this.walkY && y <= this.walkY + 6)
        {
            return AIR;
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
