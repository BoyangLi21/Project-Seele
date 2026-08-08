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
 * Supported west service hall, exterior stair and B4 maintenance lift.
 *
 * <p>This owner supplies the facility half of the sole approved civil seam.
 * The seam remains a solid wall until both its facility and Fabric receipts
 * complete.</p>
 */
public final class WestSupportV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "WEST_SUPPORT";
    private static final String STAGE = "S04_A_WEST_SUPPORT";
    private static final String PLAN_VERSION = "west-support-v2-a3";

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();
    private static final BlockState SHELL =
            Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
    private static final BlockState STRUCTURE =
            Blocks.DEEPSLATE_TILES.defaultBlockState();
    private static final BlockState FLOOR =
            Blocks.POLISHED_DEEPSLATE.defaultBlockState();
    private static final BlockState DARK =
            Blocks.BLACK_CONCRETE.defaultBlockState();
    private static final BlockState ORANGE =
            Blocks.ORANGE_CONCRETE.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.GRAY_STAINED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState EAST_BUTTON =
            Blocks.STONE_BUTTON.defaultBlockState()
                    .setValue(ButtonBlock.FACE, AttachFace.WALL)
                    .setValue(ButtonBlock.FACING, Direction.WEST);
    private static final BlockState EAST_STAIR =
            Blocks.POLISHED_DEEPSLATE_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.EAST);
    private static final BlockState SOUTH_STAIR =
            Blocks.POLISHED_DEEPSLATE_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.SOUTH);

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public WestSupportV2Plan(
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

        BlockState lift = maintenanceLift(x, y, z);
        if (lift != null)
        {
            return lift;
        }

        BlockState route = mainRoute(x, y, z);
        if (route != null)
        {
            return route;
        }

        BlockState lowerBay = lowerServiceBay(x, y, z);
        if (lowerBay != null)
        {
            return lowerBay;
        }

        return null;
    }

    private BlockState mainRoute(int x, int y, int z)
    {
        if (!inBox(x, z, -208, -160, 24, 76)
                || y < -416 || y >= -339)
        {
            return null;
        }

        // The west hall is a real supported volume at exterior road datum.
        if (y == -361)
        {
            return Math.floorMod(x + z, 13) == 0 ? LIGHT : FLOOR;
        }
        if (y == -340)
        {
            return Math.floorMod(x - z, 12) == 0 ? LIGHT : SHELL;
        }
        if ((z == 24 || z == 75 || x == -208 || x == -161)
                && y >= -360 && y < -340)
        {
            if ((z == 24 || z == 75)
                    && y >= -354 && y <= -350
                    && Math.floorMod(x + 208, 12) >= 3
                    && Math.floorMod(x + 208, 12) <= 8)
            {
                return GLASS;
            }
            // x=-208 is intentionally solid here. The civil-seam director
            // opens only the reviewed aperture after both receipts exist.
            return Math.floorMod(y + 360, 8) == 0 ? ORANGE : SHELL;
        }
        if (y >= -360 && y < -340)
        {
            BlockState platform = raisedEntryAndStairs(x, y, z);
            return platform == null ? AIR : platform;
        }

        // Deep piers make the cavern-side hall visibly load-bearing.
        if (y < -361
                && ((x == -204 || x == -184 || x == -164)
                && (z == 28 || z == 72)))
        {
            return STRUCTURE;
        }
        return null;
    }

    private BlockState raisedEntryAndStairs(int x, int y, int z)
    {
        // L0 entry landing from WEST_SERVICE_SPINE.
        if (inBox(x, z, -180, -160, 50, 76)
                && y == -349)
        {
            return checkerFloor(x, z);
        }

        // Flight A descends due west from walkY -348 to -354.
        if (x >= -186 && x < -180 && z >= 56 && z < 64)
        {
            int step = -180 - x;
            int floorY = -348 - step;
            if (y == floorY)
            {
                return EAST_STAIR;
            }
            if (y < floorY && y >= -360)
            {
                return STRUCTURE;
            }
            if ((z == 56 || z == 63)
                    && y == floorY + 1)
            {
                return Blocks.IRON_BARS.defaultBlockState();
            }
        }

        // Full mid landing; the following flight turns ninety degrees.
        if (inBox(x, z, -200, -186, 48, 64)
                && y == -355)
        {
            return checkerFloor(x, z);
        }

        // Flight B descends due north to the exterior-road datum.
        if (x >= -200 && x < -192 && z >= 41 && z < 48)
        {
            int step = 48 - z;
            int floorY = -354 - step;
            if (y == floorY)
            {
                return SOUTH_STAIR;
            }
            if (y < floorY && y >= -360)
            {
                return STRUCTURE;
            }
            if ((x == -200 || x == -193)
                    && y == floorY + 1)
            {
                return Blocks.IRON_BARS.defaultBlockState();
            }
        }

        // The lower landing meets the reviewed facility-side seam.
        if (inBox(x, z, -208, -190, 24, 41)
                && y == -361)
        {
            return checkerFloor(x, z);
        }
        return null;
    }

    private BlockState lowerServiceBay(int x, int y, int z)
    {
        if (!inBox(x, z, -180, -160, 54, 76)
                || y < -409 || y > -400)
        {
            return null;
        }
        if (y == -409)
        {
            return checkerFloor(x, z);
        }
        if (y == -400)
        {
            return Math.floorMod(x + z, 9) == 0 ? LIGHT : SHELL;
        }
        if (x == -180 || x == -161 || z == 54 || z == 75)
        {
            return y == -405 ? ORANGE : SHELL;
        }
        return AIR;
    }

    private BlockState maintenanceLift(int x, int y, int z)
    {
        if (x == -173 && z >= 56 && z < 61
                && ((y >= -408 && y < -401)
                || (y >= -360 && y < -353)))
        {
            if (y == -404 || y == -356)
            {
                return Blocks.CYAN_STAINED_GLASS.defaultBlockState();
            }
            return Math.floorMod(y, 3) == 0 ? ORANGE : DARK;
        }
        // Two-button panels: hall call above, destination below.
        if (x == -174 && (y == -406 || y == -405
                || y == -358 || y == -357)
                && z == 58)
        {
            return EAST_BUTTON;
        }
        if (!inBox(x, z, -192, -176, 56, 72)
                || y < -416 || y >= -352)
        {
            return null;
        }
        boolean wall = x == -192 || x == -177
                || z == 56 || z == 71;
        boolean eastDoor = x == -177 && z >= 61 && z < 67
                && ((y >= -408 && y < -402)
                || (y >= -360 && y < -354));
        if (wall && !eastDoor)
        {
            return Math.floorMod(y + 416, 12) == 0 ? LIGHT : STRUCTURE;
        }
        if (x >= -191 && x < -177
                && z >= 57 && z < 71)
        {
            return AIR;
        }
        return null;
    }

    private BlockState checkerFloor(int x, int z)
    {
        if (Math.floorMod(x + z, 11) == 0)
        {
            return LIGHT;
        }
        return Math.floorMod(x + z, 2) == 0 ? FLOOR : DARK;
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

    private static boolean inBox(int x, int z, int minX, int maxX,
                                 int minZ, int maxZ)
    {
        return x >= minX && x < maxX && z >= minZ && z < maxZ;
    }
}
