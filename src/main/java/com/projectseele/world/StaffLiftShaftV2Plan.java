package com.projectseele.world;

import java.util.List;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.block.LadderBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.AttachFace;

/** Fixed three-landing staff/service lift installation. */
public final class StaffLiftShaftV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "STAFF_LIFT_SHAFT";
    private static final String STAGE = "S02_K_STAFF_LIFT_SHAFT";
    private static final String PLAN_VERSION = "staff-lift-shaft-v2-a3";

    private static final int[] LANDINGS = {-408, -348, -332};

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();
    private static final BlockState SHELL =
            Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
    private static final BlockState STRUCTURE =
            Blocks.DEEPSLATE_TILES.defaultBlockState();
    private static final BlockState FLOOR =
            Blocks.SMOOTH_STONE.defaultBlockState();
    private static final BlockState DARK =
            Blocks.BLACK_CONCRETE.defaultBlockState();
    private static final BlockState CYAN =
            Blocks.CYAN_CONCRETE.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.GRAY_STAINED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState LADDER =
            Blocks.LADDER.defaultBlockState()
                    .setValue(LadderBlock.FACING, Direction.WEST);
    private static final BlockState WEST_BUTTON =
            Blocks.STONE_BUTTON.defaultBlockState()
                    .setValue(ButtonBlock.FACE, AttachFace.WALL)
                    .setValue(ButtonBlock.FACING, Direction.EAST);
    private static final BlockState EAST_BUTTON =
            Blocks.STONE_BUTTON.defaultBlockState()
                    .setValue(ButtonBlock.FACE, AttachFace.WALL)
                    .setValue(ButtonBlock.FACING, Direction.WEST);

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public StaffLiftShaftV2Plan(
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
        if (x == 56 || x == 71 || z == 56 || z == 71
                || y == -416 || y == -305)
        {
            return Math.floorMod(y + 416, 12) <= 1 ? CYAN : SHELL;
        }
        return AIR;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        // Permanent 8x8 vertical well with visible rails and service lights.
        if (x >= 60 && x <= 68 && z >= 60 && z <= 68
                && y >= -415 && y <= -306)
        {
            boolean wall = x == 60 || x == 68 || z == 60 || z == 68;
            boolean westDoor = x == 60 && z >= 61 && z <= 66
                    && atDoorHeight(y);
            boolean eastDoor = x == 68 && z >= 61 && z <= 66
                    && y >= -348 && y <= -343;
            if (wall && !westDoor && !eastDoor)
            {
                if ((x == 60 || x == 68)
                        && Math.floorMod(y + 416, 12) == 0)
                {
                    return LIGHT;
                }
                return STRUCTURE;
            }
        }

        // Actual controls sit inside large illuminated wall panels; the
        // button is not a lone floating stone pixel.
        if (x == 58 && z >= 58 && z <= 60 && isControlY(y))
        {
            return WEST_BUTTON;
        }

        for (int landing : LANDINGS)
        {
            BlockState deck = landing(x, y, z, landing);
            if (deck != null)
            {
                return deck;
            }
        }

        // A separate emergency ladder with regular refuge ledges keeps the
        // lift a navigable building even when the cabin is in fault state.
        if (x == 70 && z == 58 && y >= -407 && y <= -331)
        {
            return LADDER;
        }
        if (x == 71 && z == 58 && y >= -408 && y <= -330)
        {
            return STRUCTURE;
        }
        if (Math.floorMod(y + 408, 16) == 0
                && y >= -408 && y <= -332
                && x >= 68 && x <= 70 && z >= 57 && z <= 61)
        {
            return FLOOR;
        }
        return null;
    }

    private BlockState landing(int x, int y, int z, int walkY)
    {
        // The bottom cabin door faces west while the declared mechanical
        // trunk port leaves south. A fixed U-shaped landing passes behind the
        // well without occupying its swept 8x8 cabin volume.
        boolean lowerSouthReturn = walkY == -408
                && x >= 57 && x <= 70 && z >= 69 && z <= 71;
        boolean regularLanding = ((x >= 57 && x <= 60)
                || (x >= 68 && x <= 70))
                && z >= 57 && z <= 70;
        if (y == walkY - 1
                && (regularLanding || lowerSouthReturn))
        {
            return Math.floorMod(x + z, 7) == 0 ? LIGHT : FLOOR;
        }
        if (y >= walkY && y <= walkY + 5
                && ((x == 58 && z >= 57 && z <= 60)
                || (x == 69 && z >= 68 && z <= 70)))
        {
            if (y == walkY + 2)
            {
                return LIGHT;
            }
            return y == walkY + 3 ? GLASS : DARK;
        }
        return null;
    }

    private static boolean atDoorHeight(int y)
    {
        for (int landing : LANDINGS)
        {
            if (y >= landing && y <= landing + 5)
            {
                return true;
            }
        }
        return false;
    }

    private static boolean isControlY(int y)
    {
        for (int landing : LANDINGS)
        {
            if (y == landing + 2)
            {
                return true;
            }
        }
        return false;
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
