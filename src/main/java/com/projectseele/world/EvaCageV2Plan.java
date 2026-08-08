package com.projectseele.world;

import java.util.List;
import java.util.Set;

import com.projectseele.registry.ModFluids;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.AttachFace;

/**
 * One of three mirrored wet EVA cages. The visual grammar is shared while
 * every unit keeps an independent owner, access port and carrier exit.
 */
public final class EvaCageV2Plan implements FacilityZonePlan
{
    private static final Set<String> SUPPORTED = Set.of(
            "UNIT00_CAGE", "UNIT01_CAGE", "UNIT02_CAGE");

    private static final int BED_Y = -464;
    private static final int WALK_Y = -408;
    private static final int EVA_Z = 804;

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
            Blocks.TINTED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState RAIL =
            Blocks.IRON_BARS.defaultBlockState();
    private static final BlockState CONTROL_BUTTON =
            Blocks.STONE_BUTTON.defaultBlockState()
                    .setValue(ButtonBlock.FACE, AttachFace.FLOOR)
                    .setValue(ButtonBlock.FACING, Direction.SOUTH);

    private final String zoneId;
    private final String unit;
    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final int lineX;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public EvaCageV2Plan(
            FacilitySchemaV2.ResolvedManifest manifest, String zoneId)
    {
        if (!SUPPORTED.contains(zoneId))
        {
            throw new IllegalArgumentException(
                    "Unsupported EVA cage owner " + zoneId);
        }
        this.zoneId = zoneId;
        this.unit = zoneId.substring(4, 6);
        this.owner = manifest.requireZone(zoneId).owner();
        this.centreX = manifest.centre().getX();
        this.centreZ = manifest.centre().getZ();
        this.lineX = (this.owner.minX() + this.owner.maxX()) / 2
                - this.centreX;
        this.ports = manifest.ports().stream()
                .filter(port -> zoneId.equals(port.zoneId()))
                .toList();
        this.buildPlanHash = FacilityV2Hashing.buildPlanHash(
                zoneId, stage(), "eva-cage-s19-a5", this.owner);
    }

    @Override
    public String zoneId()
    {
        return this.zoneId;
    }

    @Override
    public String stage()
    {
        return "S19_EVA_CAGE_" + this.unit;
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

        BlockState access = accessAndObservation(x, y, z);
        if (access != null)
        {
            return access;
        }
        BlockState machinery = cageMachinery(x, y, z);
        if (machinery != null)
        {
            return machinery;
        }

        int dx = x - this.lineX;
        boolean inShell = Math.abs(dx) <= 84
                && z >= 741 && z <= 861
                && y >= -496 && y <= -340;
        if (!inShell)
        {
            return null;
        }

        boolean carrierDoor = z == 861 && Math.abs(dx) <= 32
                && y >= -496 && y <= -392;
        boolean observationDoor = z == 741 && Math.abs(dx) <= 6
                && y >= WALK_Y && y <= WALK_Y + 6;
        boolean boundary = Math.abs(dx) == 84 || z == 741 || z == 861
                || y == -496 || y == -340;
        if (boundary && !carrierDoor && !observationDoor)
        {
            boolean rib = Math.floorMod(y + 496, 16) <= 1
                    || Math.floorMod(z - 741, 20) <= 1;
            return rib ? accent() : SHELL;
        }
        return AIR;
    }

    private BlockState accessAndObservation(int x, int y, int z)
    {
        int dx = x - this.lineX;

        // PREPARE / RECALL / STATUS are three real, supported controls on one
        // observation-room desk. Their world coordinates are shared with
        // FacilityV2EvaRuntime and never float in empty space.
        if (z == 758 && (dx == -2 || dx == 0 || dx == 2))
        {
            if (y == WALK_Y)
            {
                return dx == 0 ? Blocks.RED_CONCRETE.defaultBlockState()
                        : accent();
            }
            if (y == WALK_Y + 1)
            {
                return CONTROL_BUTTON;
            }
        }

        // Rock-supported arrival sleeve from the personnel trunk.
        if (Math.abs(dx) <= 8 && z >= 737 && z <= 750)
        {
            if (y == WALK_Y - 1)
            {
                return Math.abs(dx) <= 1 ? accent() : FLOOR;
            }
            if (y == WALK_Y + 7)
            {
                return Math.floorMod(z, 6) <= 1 ? LIGHT : SHELL;
            }
            if (Math.abs(dx) == 8 && y >= WALK_Y && y <= WALK_Y + 6)
            {
                return SHELL;
            }
            if (y >= WALK_Y && y <= WALK_Y + 6)
            {
                return AIR;
            }
        }

        // Sealed observation/control room above the LCL shoulder line.
        if (Math.abs(dx) <= 50 && z >= 748 && z <= 775
                && y >= WALK_Y - 1 && y <= WALK_Y + 11)
        {
            boolean wall = Math.abs(dx) == 50 || z == 748 || z == 775;
            boolean floor = y == WALK_Y - 1;
            boolean roof = y == WALK_Y + 11;
            boolean northDoor = z == 748 && Math.abs(dx) <= 6
                    && y >= WALK_Y && y <= WALK_Y + 6;
            // The dorsal bridge runs out of the south-east corner.  Without
            // this opening the room and bridge are individually complete but
            // separated by the z=775 shell, forcing pilots into the LCL.
            boolean boardingDoor = z == 775 && dx >= 44 && dx <= 50
                    && y >= WALK_Y && y <= WALK_Y + 6;
            if (wall && z == 775 && y >= WALK_Y + 1
                    && y <= WALK_Y + 8 && Math.abs(dx) <= 42)
            {
                return GLASS;
            }
            if ((wall || floor || roof) && !northDoor && !boardingDoor)
            {
                if (roof && Math.floorMod(dx + 50, 12) <= 2)
                {
                    return LIGHT;
                }
                return floor && Math.abs(dx) <= 2 ? accent() : STRUCTURE;
            }
            return AIR;
        }

        // The boarding route bypasses the EVA's front on its east side, then
        // turns ninety degrees onto the dorsal/rear hatch. It never runs
        // through the face or chest.
        boolean sideBridge = dx >= 46 && dx <= 58
                && z >= 776 && z <= 828;
        boolean rearBridge = dx >= 0 && dx <= 58
                && z >= 820 && z <= 832;
        if ((sideBridge || rearBridge)
                && y >= WALK_Y - 1 && y <= WALK_Y + 2)
        {
            if (y == WALK_Y - 1)
            {
                return Math.floorMod(dx + z, 10) <= 1 ? LIGHT : FLOOR;
            }
            boolean edge = sideBridge
                    && (dx == 46 || dx == 58) && z < 820
                    || rearBridge && (z == 820 || z == 832);
            if (y == WALK_Y && edge)
            {
                return RAIL;
            }
            return AIR;
        }
        return null;
    }

    private BlockState cageMachinery(int x, int y, int z)
    {
        int dx = x - this.lineX;

        // Carrier bed continues straight through the cage's south door.
        if (y == BED_Y - 1 && Math.abs(dx) <= 36
                && z >= 770 && z <= 861)
        {
            boolean rail = Math.abs(dx) >= 30
                    || Math.floorMod(z - 770, 12) <= 1;
            return rail ? LIGHT : (Math.abs(dx) <= 2 ? accent() : FLOOR);
        }

        // Shoulder-depth LCL, with a solid service rim and lit drain bed.
        double basin = square(dx / 44.0D)
                + square((z - EVA_Z) / 32.0D);
        if (basin <= 1.0D)
        {
            if (y == BED_Y - 1)
            {
                return Math.floorMod(dx + z, 13) == 0 ? LIGHT : DARK;
            }
            if (y >= BED_Y && y <= -424)
            {
                return ModFluids.LCL_SOURCE.get().defaultFluidState()
                        .createLegacyBlock();
            }
        }
        if (basin > 1.0D && basin <= 1.22D
                && y >= BED_Y - 1 && y <= BED_Y + 2)
        {
            return accent();
        }

        // Four restraint pylons frame the shoulders without occupying the
        // central EVA or entry-plug swept volumes.
        if ((Math.abs(dx) >= 50 && Math.abs(dx) <= 54)
                && (z >= 780 && z <= 784 || z >= 824 && z <= 828)
                && y >= BED_Y - 1 && y <= -392)
        {
            return Math.floorMod(y - BED_Y, 12) <= 1 ? LIGHT : STRUCTURE;
        }

        // Side catwalks stay clear of the dorsal insertion line.
        if (y == -425 && z >= 782 && z <= 832
                && (Math.abs(dx) >= 48 && Math.abs(dx) <= 66))
        {
            return Math.floorMod(z, 10) <= 1 ? LIGHT : FLOOR;
        }
        if (y == -424 && z >= 782 && z <= 832
                && (Math.abs(dx) == 47 || Math.abs(dx) == 67))
        {
            return RAIL;
        }

        // Twin overhead rails reserve a visible suspended-plug mechanism.
        if (y >= -352 && y <= -349 && z >= 758 && z <= 832
                && (Math.abs(dx) >= 24 && Math.abs(dx) <= 28))
        {
            return Math.floorMod(z - 758, 12) <= 1 ? LIGHT : STRUCTURE;
        }
        if (y >= -392 && y <= -352
                && Math.abs(dx) >= 25 && Math.abs(dx) <= 27
                && (z == 764 || z == 826))
        {
            return STRUCTURE;
        }
        return null;
    }

    public BlockPos evaBed()
    {
        return new BlockPos(this.centreX + this.lineX, BED_Y,
                this.centreZ + EVA_Z);
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
