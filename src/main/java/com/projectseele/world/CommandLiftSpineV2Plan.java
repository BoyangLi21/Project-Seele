package com.projectseele.world;

import java.util.List;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.AttachFace;

/**
 * Secure command circulation outside the shared command-room owner.
 *
 * <p>The east-west ports are joined by real floors. A permanent shaft and an
 * enclosed orthogonal emergency stair occupy separate lanes, so neither the
 * commander platform nor the CommandSuite can ever terminate in open air.</p>
 */
public final class CommandLiftSpineV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "CMD_LIFT_SPINE";
    private static final String STAGE = "S02_B_COMMAND_CIRCULATION";
    private static final String PLAN_VERSION = "command-lift-spine-v2-a5";

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();
    private static final BlockState SHELL =
            Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
    private static final BlockState FLOOR =
            Blocks.POLISHED_DEEPSLATE.defaultBlockState();
    private static final BlockState STRUCTURE =
            Blocks.DEEPSLATE_TILES.defaultBlockState();
    private static final BlockState ORANGE =
            Blocks.ORANGE_CONCRETE.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.GRAY_STAINED_GLASS.defaultBlockState();
    private static final BlockState BUTTON =
            Blocks.STONE_BUTTON.defaultBlockState()
                    .setValue(ButtonBlock.FACE, AttachFace.WALL)
                    .setValue(ButtonBlock.FACING, Direction.WEST);
    private static final BlockState SOUTH_STAIR =
            Blocks.POLISHED_DEEPSLATE_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.SOUTH);
    private static final BlockState EAST_STAIR =
            Blocks.POLISHED_DEEPSLATE_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.EAST);

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public CommandLiftSpineV2Plan(
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

        if (x == 56 || x == 71 || z == -32 || z == 55
                || y == -352 || y == -305)
        {
            return Math.floorMod(x + y + z, 17) == 0 ? ORANGE : SHELL;
        }
        return AIR;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        // Each landing has a call button and a separate destination button.
        // Both are mounted on the permanent shaft frame; pressing either one
        // never creates a cabin.
        if (x == 63 && z == 45
                && (y == -330 || y == -329
                || y == -322 || y == -321))
        {
            return BUTTON;
        }

        // L3 secure spine from the supported command vestibule to the suite.
        if (x >= 56 && x < 64 && z >= -4 && z < 44)
        {
            if (y == -325)
            {
                return Math.floorMod(z, 9) == 0 ? LIGHT : FLOOR;
            }
            if (y == -316)
            {
                return Math.floorMod(z, 11) == 0 ? LIGHT : STRUCTURE;
            }
            if ((x == 56 || x == 63) && y >= -324 && y < -316)
            {
                /*
                 * The only west-side L3 port is in the separate lift lobby
                 * at z=48. Older geometry also opened z[-3,3] and z[21,27]
                 * here even though neither aperture exists in the manifest;
                 * those holes exposed the secure spine to empty CommandVolume
                 * space. Keep this corridor enclosed and let isPortTunnel()
                 * open only declared, reciprocal ports.
                 */
                return y == -321 ? GLASS : STRUCTURE;
            }
        }

        // East turn into CommandSuite. The registered suite port lands on a
        // full floor and never opens directly into the lift well.
        if (x >= 64 && x < 72 && z >= -4 && z < 8)
        {
            if (y == -325)
            {
                return Math.floorMod(x + z, 7) == 0 ? LIGHT : FLOOR;
            }
            if (y == -316)
            {
                return STRUCTURE;
            }
            if ((z == -4 || z == 7) && y >= -324 && y < -316)
            {
                return y == -321 ? GLASS : STRUCTURE;
            }
        }

        // L3 command-lift lobby.
        if (x >= 56 && x < 64 && z >= 40 && z < 56)
        {
            if (y == -325)
            {
                return Math.floorMod(x + z, 7) == 0 ? LIGHT : FLOOR;
            }
            if (y == -316)
            {
                return STRUCTURE;
            }
            if ((x == 56 || z == 55) && y >= -324 && y < -316)
            {
                return y == -321 ? GLASS : STRUCTURE;
            }
        }

        // L2 lower landing and lift approach from CV-OFFICE.
        if (x >= 56 && x < 64 && z >= 18 && z < 54)
        {
            if (y == -333)
            {
                return Math.floorMod(x + z, 8) == 0 ? LIGHT : FLOOR;
            }
            if (y == -326)
            {
                return STRUCTURE;
            }
            if (x == 56 && y >= -332 && y < -326
                    && !(z >= 21 && z <= 27))
            {
                return y == -329 ? GLASS : STRUCTURE;
            }
        }

        // Orthogonal emergency stair, independent of the cabin.
        if (y == -325 && x >= 64 && x < 72 && z >= 32 && z < 40)
        {
            return FLOOR;
        }
        for (int step = 1; step <= 4; step++)
        {
            int stepZ = 32 - step;
            int treadY = -324 - step;
            if (x >= 64 && x < 71 && z == stepZ)
            {
                if (y == treadY)
                {
                    return SOUTH_STAIR;
                }
                if (y >= -351 && y < treadY)
                {
                    return STRUCTURE;
                }
            }
        }
        // Full 90-degree turn landing. Its former z=18..23 footprint
        // stopped four blocks short of the northbound flight.
        if (y == -329 && x >= 64 && x < 71 && z >= 24 && z < 32)
        {
            return FLOOR;
        }
        for (int step = 1; step <= 4; step++)
        {
            int stepX = 64 - step;
            int treadY = -328 - step;
            if (x == stepX && z >= 24 && z < 30)
            {
                if (y == treadY)
                {
                    return EAST_STAIR;
                }
                if (y >= -351 && y < treadY)
                {
                    return STRUCTURE;
                }
            }
        }

        // Permanently reserved 8x10 shaft. Both landing doors are on its west
        // side; no public corridor crosses the moving-cabin volume.
        if (x >= 64 && x < 72 && z >= 44 && z < 54)
        {
            boolean wall = x == 64 || x == 71 || z == 44 || z == 53;
            boolean l2Door = x == 64 && z >= 46 && z <= 51
                    && y >= -332 && y <= -327;
            boolean l3Door = x == 64 && z >= 46 && z <= 51
                    && y >= -324 && y <= -319;
            if (wall && !l2Door && !l3Door
                    && y >= -351 && y <= -306)
            {
                return Math.floorMod(y + 352, 8) == 0
                        ? LIGHT : STRUCTURE;
            }
            if (!wall && y == -350)
            {
                return Math.floorMod(x + z, 7) == 0 ? ORANGE : FLOOR;
            }
        }

        // Large fixed status panels flank the cabin door at both stops.
        if (x == 63 && z >= 47 && z <= 50
                && ((y >= -323 && y <= -320)
                || (y >= -331 && y <= -328)))
        {
            return y == -321 || y == -329 ? LIGHT
                    : Blocks.IRON_BLOCK.defaultBlockState();
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
