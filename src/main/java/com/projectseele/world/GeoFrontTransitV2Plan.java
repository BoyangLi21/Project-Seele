package com.projectseele.world;

import java.util.List;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockState;

/**
 * H-01 GeoFront station connecting the public lift to the NERV foyer.
 */
public final class GeoFrontTransitV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "GEOFRONT_TRANSIT";
    private static final String STAGE = "S02_F_GEOFRONT_TRANSIT";
    private static final String PLAN_VERSION = "geofront-transit-v2-a2";

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
    private static final BlockState WHITE =
            Blocks.WHITE_CONCRETE.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.GRAY_STAINED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState RAIL =
            Blocks.IRON_BARS.defaultBlockState();
    private static final BlockState SOUTH_STAIR =
            Blocks.SMOOTH_QUARTZ_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.SOUTH);

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public GeoFrontTransitV2Plan(
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
        if (x == -64 || x == 63 || z == 184 || z == 219
                || y == -368 || y == -321)
        {
            return shellPattern(x, y, z);
        }
        return AIR;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        // Main H-01 station deck, level with the NERV foyer south port.
        if (y == -357 && inBox(x, z, -58, 58, 185, 201))
        {
            return floorPattern(x, z);
        }

        // Four broad risers rise due south to the public-lift concourse.
        // Both sides
        // have rails and solid backing; the lift is never reached by a jump.
        for (int step = 0; step < 4; step++)
        {
            int stepZ = 201 + step;
            int treadY = -356 + step;
            if (x >= -24 && x <= 24 && z == stepZ)
            {
                if (y == treadY)
                {
                    return SOUTH_STAIR;
                }
                if (y >= -367 && y < treadY)
                {
                    return STRUCTURE;
                }
            }
        }
        if (y == -353 && inBox(x, z, -58, 58, 204, 219))
        {
            return floorPattern(x, z);
        }

        // Permanent lift landing enclosure and deep jambs. The aperture is
        // left open only where the shaft-side reciprocal port exists.
        if (inBox(x, z, -16, 16, 210, 219)
                && y >= -352 && y <= -344)
        {
            boolean wall = x == -16 || x == 15 || z == 210;
            boolean roof = y == -344;
            boolean northDoor = z == 210 && x >= -5 && x <= 4
                    && y <= -347;
            if ((wall || roof) && !northDoor)
            {
                return y == -349 && wall ? GLASS : STRUCTURE;
            }
        }

        // Ticket/security islands leave a twelve-block central aisle.
        if (y == -356 && z >= 191 && z <= 194
                && ((x >= -46 && x <= -8) || (x >= 7 && x <= 45)))
        {
            return Math.floorMod(x, 9) == 0 ? LIGHT : DARK;
        }
        if (y == -355 && z == 193
                && (x == -36 || x == -20 || x == 20 || x == 36))
        {
            return GLASS;
        }

        // Readable H-01 wall band and destination board.
        if ((x == -62 || x == 61) && y >= -359 && y <= -340
                && z >= 188 && z <= 216)
        {
            if (y == -352 || y == -351)
            {
                return ORANGE;
            }
            return Math.floorMod(z - 188, 7) == 0 ? LIGHT : STRUCTURE;
        }
        if (z == 186 && y >= -349 && y <= -339
                && x >= -38 && x <= 38)
        {
            if (y == -348 || y == -340 || x == -38 || x == 38)
            {
                return WHITE;
            }
            return Math.floorMod(x + y, 8) == 0
                    ? Blocks.CYAN_STAINED_GLASS.defaultBlockState() : DARK;
        }

        // Rail the height transition without closing the central stair.
        if (y == -352 && z >= 201 && z <= 204
                && (x == -25 || x == 25))
        {
            return RAIL;
        }

        // Structural columns and a luminous ceiling datum make the station
        // a persistent place rather than a hollow tunnel.
        if (y >= -367 && y <= -322
                && (x == -56 || x == 55)
                && (z == 188 || z == 202 || z == 216))
        {
            return Math.floorMod(y + 368, 8) == 0 ? ORANGE : STRUCTURE;
        }
        if (y == -322 && Math.floorMod(x + 56, 14) <= 2
                && Math.floorMod(z - 188, 10) <= 2)
        {
            return LIGHT;
        }
        return null;
    }

    private static boolean inBox(int x, int z, int minX, int maxX,
                                 int minZ, int maxZ)
    {
        return x >= minX && x < maxX && z >= minZ && z < maxZ;
    }

    private static BlockState floorPattern(int x, int z)
    {
        if (Math.floorMod(x, 10) == 0 || Math.floorMod(z, 10) == 0)
        {
            return DARK;
        }
        return Math.floorMod(x + z, 19) == 0 ? LIGHT : FLOOR;
    }

    private static BlockState shellPattern(int x, int y, int z)
    {
        if (Math.floorMod(x + z, 20) <= 1
                || Math.floorMod(y + 368, 10) == 0)
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
