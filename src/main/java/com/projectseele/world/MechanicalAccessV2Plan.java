package com.projectseele.world;

import java.util.List;
import java.util.Set;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Supported, orthogonal personnel route from headquarters to the three
 * independent EVA lines.
 */
public final class MechanicalAccessV2Plan implements FacilityZonePlan
{
    private static final Set<String> SUPPORTED = Set.of(
            "MECH_ACCESS_SPINE",
            "MECH_AIRLOCK_LINK",
            "MECH_PERSONNEL_TRUNK",
            "MECH_OBS_LINK_00",
            "MECH_OBS_LINK_01",
            "MECH_OBS_LINK_02");

    private static final int FLOOR_Y = -409;
    private static final int ROOF_Y = -401;

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();
    private static final BlockState SHELL =
            Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
    private static final BlockState FLOOR =
            Blocks.POLISHED_DEEPSLATE.defaultBlockState();
    private static final BlockState DARK =
            Blocks.BLACK_CONCRETE.defaultBlockState();
    private static final BlockState ORANGE =
            Blocks.ORANGE_CONCRETE.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.GRAY_STAINED_GLASS.defaultBlockState();

    private final FacilitySchemaV2.ResolvedManifest manifest;
    private final String zoneId;
    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public MechanicalAccessV2Plan(
            FacilitySchemaV2.ResolvedManifest manifest, String zoneId)
    {
        if (!SUPPORTED.contains(zoneId))
        {
            throw new IllegalArgumentException(
                    "Unsupported mechanical access owner " + zoneId);
        }
        this.manifest = manifest;
        this.zoneId = zoneId;
        this.owner = manifest.requireZone(zoneId).owner();
        this.centreX = manifest.centre().getX();
        this.centreZ = manifest.centre().getZ();
        this.ports = manifest.ports().stream()
                .filter(port -> zoneId.equals(port.zoneId()))
                .toList();
        this.buildPlanHash = FacilityV2Hashing.buildPlanHash(
                zoneId, stage(), "mechanical-access-s19-a1", this.owner);
    }

    @Override
    public String zoneId()
    {
        return this.zoneId;
    }

    @Override
    public String stage()
    {
        return "S19_MECH_ACCESS_" + this.zoneId;
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
        if (!insideFootprint(x, z))
        {
            return supportAt(x, y, z);
        }

        if (y < FLOOR_Y || y > ROOF_Y)
        {
            return supportAt(x, y, z);
        }
        if (y == FLOOR_Y)
        {
            return lightBay(x, z) ? LIGHT
                    : (centreLine(x, z) ? ORANGE : FLOOR);
        }
        if (y == ROOF_Y)
        {
            return lightBay(x, z) ? LIGHT : SHELL;
        }

        boolean boundary = !insideFootprint(x - 1, z)
                || !insideFootprint(x + 1, z)
                || !insideFootprint(x, z - 1)
                || !insideFootprint(x, z + 1);
        if (boundary)
        {
            if (y == FLOOR_Y + 3 && glassBand(x, z))
            {
                return GLASS;
            }
            return airlockFrame(x, z) ? DARK : SHELL;
        }
        if (airlockFrame(x, z)
                && (y == FLOOR_Y + 1 || y == ROOF_Y - 1))
        {
            return DARK;
        }
        return AIR;
    }

    private boolean insideFootprint(int x, int z)
    {
        return switch (this.zoneId)
        {
            case "MECH_ACCESS_SPINE" ->
                    inRect(x, z, 84, 100, 88, 659)
                            || inRect(x, z, 61, 100, 72, 96);
            case "MECH_AIRLOCK_LINK" ->
                    inRect(x, z, 84, 100, 660, 689);
            case "MECH_PERSONNEL_TRUNK" ->
                    inRect(x, z, -600, 599, 700, 712)
                            || inRect(x, z, 84, 100, 690, 700)
                            || lineBranch(x, z, -389)
                            || lineBranch(x, z, 0)
                            || lineBranch(x, z, 389);
            default ->
            {
                int lineX = lineCentre();
                yield inRect(x, z, lineX - 8, lineX + 8,
                        721, 736);
            }
        };
    }

    private static boolean lineBranch(int x, int z, int lineX)
    {
        return inRect(x, z, lineX - 8, lineX + 8, 712, 720);
    }

    private int lineCentre()
    {
        String suffix = this.zoneId.substring(this.zoneId.length() - 2);
        return switch (suffix)
        {
            case "00" -> -389;
            case "01" -> 0;
            case "02" -> 389;
            default -> throw new IllegalStateException(
                    "Unknown observation line " + this.zoneId);
        };
    }

    private BlockState supportAt(int x, int y, int z)
    {
        if (y >= this.owner.minY() && y < FLOOR_Y
                && insideFootprint(x, z)
                && Math.floorMod(x + 600, 24) <= 1
                && Math.floorMod(z, 24) <= 1)
        {
            return SHELL;
        }
        return null;
    }

    private boolean lightBay(int x, int z)
    {
        if ("MECH_PERSONNEL_TRUNK".equals(this.zoneId))
        {
            return Math.floorMod(x + 600, 24) <= 2
                    && z >= 704 && z <= 708;
        }
        return Math.floorMod(z, 18) <= 2
                && Math.floorMod(x, 8) <= 2;
    }

    private boolean centreLine(int x, int z)
    {
        if ("MECH_PERSONNEL_TRUNK".equals(this.zoneId))
        {
            return z >= 705 && z <= 707;
        }
        return Math.floorMod(x, 92) == 0;
    }

    private boolean glassBand(int x, int z)
    {
        return "MECH_AIRLOCK_LINK".equals(this.zoneId)
                && (z == 660 || z == 689)
                && x >= 88 && x <= 96;
    }

    private boolean airlockFrame(int x, int z)
    {
        return "MECH_AIRLOCK_LINK".equals(this.zoneId)
                && (z >= 668 && z <= 669 || z >= 680 && z <= 681);
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

    private static boolean inRect(int x, int z, int minX, int maxX,
                                  int minZ, int maxZ)
    {
        return x >= minX && x <= maxX && z >= minZ && z <= maxZ;
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
