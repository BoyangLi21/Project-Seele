package com.projectseele.world;

import java.util.List;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.block.LadderBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.AttachFace;

/** Fixed high-security lift shaft between MAGI level and Central Dogma. */
public final class DogmaLiftShaftV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "DOGMA_LIFT_SHAFT";
    private static final String STAGE = "S02_N_DOGMA_LIFT_SHAFT";
    private static final String PLAN_VERSION = "dogma-lift-shaft-v2-a1";

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
    private static final BlockState LADDER =
            Blocks.LADDER.defaultBlockState()
                    .setValue(LadderBlock.FACING, Direction.WEST);
    private static final BlockState NORTH_BUTTON =
            Blocks.STONE_BUTTON.defaultBlockState()
                    .setValue(ButtonBlock.FACE, AttachFace.WALL)
                    .setValue(ButtonBlock.FACING, Direction.SOUTH);
    private static final BlockState SOUTH_BUTTON =
            Blocks.STONE_BUTTON.defaultBlockState()
                    .setValue(ButtonBlock.FACE, AttachFace.WALL)
                    .setValue(ButtonBlock.FACING, Direction.NORTH);

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public DogmaLiftShaftV2Plan(
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
        if (x == 24 || x == 39 || z == 160 || z == 183
                || y == -632 || y == -389)
        {
            return Math.floorMod(y + 632, 16) <= 1 ? RED : SHELL;
        }
        return AIR;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        if (x == 26 && z == 162 && (y == -393 || y == -392))
        {
            return NORTH_BUTTON;
        }
        if (x == 37 && z == 181 && (y == -574 || y == -573))
        {
            return SOUTH_BUTTON;
        }

        // 8x8 persistent cabin well.
        if (x >= 28 && x <= 36 && z >= 168 && z <= 176
                && y >= -631 && y <= -390)
        {
            boolean wall = x == 28 || x == 36 || z == 168 || z == 176;
            boolean upperDoor = z == 168 && x >= 29 && x <= 34
                    && y >= -395 && y <= -390;
            boolean lowerDoor = z == 176 && x >= 29 && x <= 34
                    && y >= -576 && y <= -571;
            if (wall && !upperDoor && !lowerDoor)
            {
                return Math.floorMod(y + 632, 18) == 0
                        ? LIGHT : STRUCTURE;
            }
        }

        BlockState upper = landing(x, y, z, -395, 160, 169);
        if (upper != null)
        {
            return upper;
        }
        BlockState lower = landing(x, y, z, -576, 176, 184);
        if (lower != null)
        {
            return lower;
        }

        if (x == 38 && z == 181 && y >= -575 && y <= -394)
        {
            return LADDER;
        }
        if (x == 39 && z == 181 && y >= -576 && y <= -393)
        {
            return STRUCTURE;
        }
        if (Math.floorMod(y + 576, 20) == 0
                && y >= -576 && y <= -395
                && x >= 36 && x <= 38 && z >= 178 && z <= 182)
        {
            return FLOOR;
        }
        return null;
    }

    private static BlockState landing(int x, int y, int z, int walkY,
                                      int minZ, int maxZ)
    {
        if (x < 25 || x > 38 || z < minZ || z >= maxZ)
        {
            return null;
        }
        if (y == walkY - 1)
        {
            return Math.floorMod(x + z, 7) == 0 ? LIGHT : FLOOR;
        }
        if (y == walkY + 7)
        {
            return STRUCTURE;
        }
        if ((x == 25 || x == 38) && y >= walkY && y <= walkY + 6)
        {
            return y == walkY + 3 ? GLASS : STRUCTURE;
        }
        if (y >= walkY && y <= walkY + 6
                && ((z == minZ + 1 && x <= 28)
                || (z == maxZ - 2 && x >= 35)))
        {
            return y == walkY + 2 ? LIGHT : DARK;
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
