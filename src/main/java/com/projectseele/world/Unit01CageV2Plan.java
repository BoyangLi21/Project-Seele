package com.projectseele.world;

import java.util.List;

import com.projectseele.registry.ModFluids;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Unit-01 wet cage with observation room, boarding circulation and carrier bay.
 */
public final class Unit01CageV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "UNIT01_CAGE";
    private static final String STAGE = "S02_Q_UNIT01_CAGE";
    private static final String PLAN_VERSION = "unit01-cage-v2-a1";

    private static final int BED_X = 240;
    private static final int BED_Y = -464;
    private static final int BED_Z = 0;
    private static final int OBSERVATION_WALK_Y = -416;

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();
    private static final BlockState SHELL =
            Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
    private static final BlockState STRUCTURE =
            Blocks.DEEPSLATE_TILES.defaultBlockState();
    private static final BlockState FLOOR =
            Blocks.POLISHED_DEEPSLATE.defaultBlockState();
    private static final BlockState DARK =
            Blocks.BLACK_CONCRETE.defaultBlockState();
    private static final BlockState PURPLE =
            Blocks.PURPLE_CONCRETE.defaultBlockState();
    private static final BlockState ORANGE =
            Blocks.ORANGE_CONCRETE.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.TINTED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState RAIL =
            Blocks.IRON_BARS.defaultBlockState();
    private static final BlockState EAST_DESCENT =
            Blocks.POLISHED_DIORITE_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.WEST);
    private static final BlockState WEST_DESCENT =
            Blocks.POLISHED_DIORITE_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.EAST);

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public Unit01CageV2Plan(
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

        // The actual cage shell is deliberately inset from its gross owner,
        // leaving audited room for service structures without making one
        // featureless 160x192 rectangular bunker.
        if (x >= 176 && x <= 304 && z >= -72 && z <= 72
                && y >= -480 && y <= -380)
        {
            boolean wall = x == 176 || x == 304
                    || z == -72 || z == 72;
            boolean floor = y == -480;
            boolean roof = y == -380;
            boolean carrierDoor = x == 304 && z >= -32 && z <= 32
                    && y >= -464 && y <= -385;
            if ((wall || floor || roof) && !carrierDoor)
            {
                boolean rib = Math.floorMod(y + 480, 12) <= 1
                        || Math.floorMod(z + 72, 18) <= 1;
                return rib ? PURPLE : SHELL;
            }
            return AIR;
        }
        return null;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        BlockState access = humanAccess(x, y, z);
        if (access != null)
        {
            return access;
        }

        // Supported carrier bed and straight eastbound extraction rails.
        if (y == BED_Y - 1 && x >= 204 && x <= 319
                && z >= -34 && z <= 34)
        {
            boolean rail = z == -30 || z == 30
                    || Math.floorMod(x - 204, 12) <= 1;
            return rail ? LIGHT : (Math.abs(z) <= 2 ? PURPLE : FLOOR);
        }
        if (y < BED_Y - 1 && y >= -479
                && x >= 204 && x <= 319
                && (z == -32 || z == 32)
                && Math.floorMod(x - 204, 14) <= 2)
        {
            return STRUCTURE;
        }

        // Shoulder-depth LCL basin. The EVA remains visibly dormant until a
        // later runtime controller energizes it.
        if (x >= 208 && x <= 272 && z >= -40 && z <= 40)
        {
            boolean ellipse = square((x - BED_X) / 32.0D)
                    + square(z / 40.0D) <= 1.0D;
            if (ellipse && y == BED_Y - 1)
            {
                return Math.floorMod(x + z, 13) == 0 ? LIGHT : ORANGE;
            }
            if (ellipse && y >= BED_Y && y <= -421)
            {
                return ModFluids.LCL_SOURCE.get().defaultFluidState()
                        .createLegacyBlock();
            }
        }

        // Massive restraint pylons and shoulder service arches.
        if ((x == 202 || x == 278) && (z == -46 || z == 46)
                && y >= BED_Y - 1 && y <= -390)
        {
            return Math.floorMod(y - BED_Y, 10) <= 1
                    ? LIGHT : STRUCTURE;
        }
        if (y >= -422 && y <= -414
                && (x >= 202 && x <= 278)
                && (Math.abs(z) >= 43 && Math.abs(z) <= 48))
        {
            return y == -418 ? PURPLE : STRUCTURE;
        }

        // Overhead crane rails reserve a real insertion mechanism envelope.
        // The moving plug itself is not posed here; it will use Pro's
        // canonical socket and swept-OBB contract.
        if (y >= -392 && y <= -389 && x >= 220 && x <= 294
                && (z >= -48 && z <= -44 || z >= 44 && z <= 48))
        {
            return Math.floorMod(x - 220, 10) <= 1 ? LIGHT : STRUCTURE;
        }

        // Boarding route runs around the north side of the restrained EVA,
        // then reaches the dorsal-service gantry from behind.
        if (y == OBSERVATION_WALK_Y - 1
                && ((x >= 194 && x <= 282 && z >= 38 && z <= 46)
                || (x >= 274 && x <= 282 && z >= -4 && z <= 46)))
        {
            return Math.floorMod(x + z, 9) == 0 ? LIGHT : FLOOR;
        }
        if (y == OBSERVATION_WALK_Y
                && ((z == 37 || z == 47) && x >= 194 && x <= 282
                || (x == 273 || x == 283) && z >= -4 && z <= 46))
        {
            return RAIL;
        }
        return null;
    }

    private BlockState humanAccess(int x, int y, int z)
    {
        // Upper service corridor from the registered observation port.
        if (x >= 160 && x <= 196 && z >= 56 && z <= 71)
        {
            if (y == -349)
            {
                return Math.floorMod(x + z, 8) == 0 ? LIGHT : FLOOR;
            }
            if (y == -342)
            {
                return STRUCTURE;
            }
            if ((z == 56 || z == 71) && y >= -348 && y <= -343)
            {
                return y == -346 ? GLASS : STRUCTURE;
            }
        }

        // Four orthogonal 17-step flights descend exactly 68 blocks.
        int[] starts = {-349, -366, -383, -400};
        for (int flight = 0; flight < 4; flight++)
        {
            boolean eastbound = flight % 2 == 0;
            int laneMinZ = eastbound ? 50 : 62;
            int laneMaxZ = laneMinZ + 6;
            for (int step = 0; step < 17; step++)
            {
                int stepX = eastbound ? 176 + step : 192 - step;
                int treadY = starts[flight] - step;
                if (x == stepX && z >= laneMinZ && z <= laneMaxZ)
                {
                    if (y == treadY)
                    {
                        return eastbound ? EAST_DESCENT : WEST_DESCENT;
                    }
                    if (y >= -479 && y < treadY)
                    {
                        return STRUCTURE;
                    }
                }
            }

            int landingY = starts[flight] - 17;
            boolean eastLanding = eastbound;
            int minX = eastLanding ? 190 : 174;
            int maxX = eastLanding ? 198 : 182;
            if (y == landingY && x >= minX && x <= maxX
                    && z >= 48 && z <= 70)
            {
                return Math.floorMod(x + z, 7) == 0 ? LIGHT : FLOOR;
            }
        }

        // Observation/control room faces west side of the EVA at shoulder
        // height. Its rear door lands on the final stair floor.
        if (x >= 176 && x <= 198 && z >= -30 && z <= 36
                && y >= -417 && y <= -402)
        {
            if (y == -417 || y == -402 || x == 176
                    || z == -30 || z == 36)
            {
                return Math.floorMod(x + z, 11) == 0 ? LIGHT : STRUCTURE;
            }
            if (x == 198)
            {
                return y >= -414 && y <= -405 ? GLASS : STRUCTURE;
            }
            return AIR;
        }
        return null;
    }

    public BlockPos evaBed()
    {
        return new BlockPos(this.centreX + BED_X, BED_Y,
                this.centreZ + BED_Z);
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
