package com.projectseele.world;

import java.util.List;
import java.util.Set;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Civil works shared by the three straight cage-to-surface EVA lines.
 *
 * <p>Every unit has a distinct owner. No plan turns through another line and
 * no surface roof block is ever placed in the launch sweep.</p>
 */
public final class EvaLogisticsV2Plan implements FacilityZonePlan
{
    private static final Set<String> SUPPORTED = Set.of(
            "UNIT00_CARRIER", "UNIT00_SWITCHYARD",
            "UNIT00_SILO", "UNIT00_SURFACE_HEAD",
            "UNIT01_CARRIER", "UNIT01_SWITCHYARD",
            "UNIT01_SILO", "UNIT01_SURFACE_HEAD",
            "UNIT02_CARRIER", "UNIT02_SWITCHYARD",
            "UNIT02_SILO", "UNIT02_SURFACE_HEAD");

    private static final int EVA_DECK_Y = -465;

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();
    private static final BlockState SHELL =
            Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
    private static final BlockState STRUCTURE =
            Blocks.DEEPSLATE_TILES.defaultBlockState();
    private static final BlockState FLOOR =
            Blocks.POLISHED_DEEPSLATE.defaultBlockState();
    private static final BlockState DARK =
            Blocks.BLACK_CONCRETE.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.GRAY_STAINED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState RAIL =
            Blocks.IRON_BARS.defaultBlockState();

    private final String zoneId;
    private final String unit;
    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final int lineX;
    private final int minZ;
    private final int maxZ;
    private final int surfaceY;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public EvaLogisticsV2Plan(
            FacilitySchemaV2.ResolvedManifest manifest, String zoneId)
    {
        if (!SUPPORTED.contains(zoneId))
        {
            throw new IllegalArgumentException(
                    "Unsupported EVA logistics owner " + zoneId);
        }
        this.zoneId = zoneId;
        this.unit = zoneId.substring(4, 6);
        this.owner = manifest.requireZone(zoneId).owner();
        this.centreX = manifest.centre().getX();
        this.centreZ = manifest.centre().getZ();
        this.lineX = (this.owner.minX() + this.owner.maxX()) / 2
                - this.centreX;
        this.minZ = this.owner.minZ() - this.centreZ;
        this.maxZ = this.owner.maxZ() - this.centreZ - 1;
        this.surfaceY = manifest.surfaceY();
        this.ports = manifest.ports().stream()
                .filter(port -> zoneId.equals(port.zoneId()))
                .toList();
        this.buildPlanHash = FacilityV2Hashing.buildPlanHash(
                zoneId, stage(), "eva-logistics-s19-a2", this.owner);
    }

    @Override
    public String zoneId()
    {
        return this.zoneId;
    }

    @Override
    public String stage()
    {
        return "S19_EVA_LOGISTICS_" + this.zoneId;
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
        if (isPortTunnel(position))
        {
            return AIR;
        }

        int x = position.getX() - this.centreX;
        int y = position.getY();
        int z = position.getZ() - this.centreZ;
        if (this.zoneId.endsWith("_CARRIER"))
        {
            return carrier(x - this.lineX, y, z);
        }
        if (this.zoneId.endsWith("_SWITCHYARD"))
        {
            return switchyard(x - this.lineX, y, z);
        }
        if (this.zoneId.endsWith("_SILO"))
        {
            return silo(x - this.lineX, y, z);
        }
        return surfaceHead(x - this.lineX, y, z);
    }

    private BlockState carrier(int dx, int y, int z)
    {
        boolean inside = Math.abs(dx) <= 39 && z >= this.minZ
                && z <= this.maxZ && y >= -504 && y <= -385;
        if (!inside)
        {
            return null;
        }
        if (y == EVA_DECK_Y && Math.abs(dx) <= 34)
        {
            boolean rail = Math.abs(dx) >= 29
                    || Math.floorMod(z - this.minZ, 8) <= 1;
            return rail ? LIGHT : (Math.abs(dx) <= 2 ? accent() : FLOOR);
        }
        boolean boundary = Math.abs(dx) == 39
                || z == this.minZ || z == this.maxZ
                || y == -504 || y == -385;
        boolean evaDoor = (z == this.minZ || z == this.maxZ)
                && Math.abs(dx) <= 32
                && y >= -504 && y <= -392;
        if (boundary && !evaDoor)
        {
            boolean rib = Math.floorMod(z - this.minZ, 8) <= 1
                    || Math.floorMod(y + 504, 16) <= 1;
            return rib ? accent() : SHELL;
        }
        return AIR;
    }

    private BlockState switchyard(int dx, int y, int z)
    {
        boolean inside = Math.abs(dx) <= 52 && z >= this.minZ
                && z <= this.maxZ && y >= -504 && y <= -385;
        if (!inside)
        {
            return null;
        }
        int centre = (this.minZ + this.maxZ) / 2;
        int dz = z - centre;
        if (y == EVA_DECK_Y)
        {
            double radius = Math.sqrt(square(dx) + square(dz));
            if (radius >= 34.0D && radius <= 37.0D)
            {
                return LIGHT;
            }
            if (Math.abs(dx) <= 2 || Math.abs(dz) <= 2)
            {
                return accent();
            }
            return FLOOR;
        }
        boolean boundary = Math.abs(dx) == 52
                || z == this.minZ || z == this.maxZ
                || y == -504 || y == -385;
        boolean evaDoor = (z == this.minZ || z == this.maxZ)
                && Math.abs(dx) <= 40
                && y >= -504 && y <= -392;
        if (boundary && !evaDoor)
        {
            return Math.floorMod(y + z, 18) <= 1 ? accent() : SHELL;
        }
        if (y >= -464 && y <= -392
                && (Math.abs(dx) >= 45 && Math.abs(dx) <= 48)
                && (Math.abs(dz) >= 19 && Math.abs(dz) <= 22))
        {
            return Math.floorMod(y + 464, 10) <= 1 ? LIGHT : STRUCTURE;
        }
        return AIR;
    }

    private BlockState silo(int dx, int y, int z)
    {
        int shaftZ = (this.minZ + this.maxZ) / 2;
        int dz = z - shaftZ;

        // The lower alignment chamber accepts the carrier straight from the
        // north and never introduces the old lateral turn.
        if (y >= -504 && y <= -385
                && Math.abs(dx) <= 52
                && z >= this.minZ && z <= this.maxZ)
        {
            if (y == EVA_DECK_Y
                    && (z <= shaftZ || Math.abs(dz) <= 32)
                    && Math.abs(dx) <= 40)
            {
                return Math.abs(dx) >= 30 ? LIGHT
                        : (Math.abs(dx) <= 2 ? accent() : FLOOR);
            }
            boolean lowerWall = Math.abs(dx) == 52
                    || z == this.minZ || z == this.maxZ
                    || y == -504 || y == -385;
            boolean northEntry = z == this.minZ && Math.abs(dx) <= 40
                    && y >= -504 && y <= -392;
            if (lowerWall && !northEntry)
            {
                return Math.floorMod(y + z, 20) <= 1
                        ? accent() : SHELL;
            }
            return AIR;
        }

        boolean inShaft = Math.abs(dx) <= 36 && Math.abs(dz) <= 36
                && y >= -384 && y <= this.surfaceY - 1;
        if (inShaft)
        {
            boolean wall = Math.abs(dx) == 36 || Math.abs(dz) == 36;
            if (wall)
            {
                return Math.floorMod(y + 384, 24) <= 1
                        ? accent() : STRUCTURE;
            }
            if (Math.floorMod(y + 384, 48) == 0
                    && (Math.abs(dx) >= 33 || Math.abs(dz) >= 33))
            {
                return FLOOR;
            }
            return AIR;
        }

        // Walkable maintenance rings are outside the 64x64 launch bore.
        if (y >= -384 && y <= this.surfaceY
                && Math.floorMod(y + 384, 48) == 0
                && Math.abs(dx) <= 44 && Math.abs(dz) <= 38
                && (Math.abs(dx) >= 37 || Math.abs(dz) >= 37))
        {
            return Math.abs(dx) == 44 || Math.abs(dz) == 38
                    ? RAIL : FLOOR;
        }
        return null;
    }

    private BlockState surfaceHead(int dx, int y, int z)
    {
        int baseY = this.surfaceY;
        int shaftZ = (this.minZ + this.maxZ) / 2;
        int dz = z - shaftZ;

        // The entire launch aperture remains open to the sky.
        if (Math.abs(dx) <= 32 && Math.abs(dz) <= 32)
        {
            return AIR;
        }

        if (y == baseY && Math.abs(dx) <= 52
                && z >= this.minZ && z <= this.maxZ)
        {
            return Math.floorMod(dx + dz, 10) <= 1 ? LIGHT : FLOOR;
        }

        // Four guide towers, no centre roof and no hidden obstruction.
        if (y >= baseY && y <= this.surfaceY + 68
                && Math.abs(dx) >= 38 && Math.abs(dx) <= 44
                && Math.abs(dz) >= 31 && Math.abs(dz) <= 37)
        {
            return Math.floorMod(y - baseY, 12) <= 1
                    ? accent() : STRUCTURE;
        }

        // A low, glazed service collar wraps rather than caps the bore.
        if (y >= baseY + 1 && y <= baseY + 12
                && Math.abs(dx) <= 52
                && z >= this.minZ && z <= this.maxZ)
        {
            boolean outer = Math.abs(dx) == 52
                    || z == this.minZ || z == this.maxZ;
            if (outer)
            {
                if (y >= baseY + 4 && y <= baseY + 8
                        && Math.floorMod(dx + dz, 12) <= 6)
                {
                    return GLASS;
                }
                return y == baseY + 6 ? accent() : SHELL;
            }
        }
        return null;
    }

    private BlockState accent()
    {
        return switch (this.unit)
        {
            case "00" -> Blocks.ORANGE_CONCRETE.defaultBlockState();
            case "02" -> Blocks.RED_CONCRETE.defaultBlockState();
            default -> Blocks.PURPLE_CONCRETE.defaultBlockState();
        };
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
