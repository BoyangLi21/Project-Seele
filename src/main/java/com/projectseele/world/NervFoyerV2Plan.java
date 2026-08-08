package com.projectseele.world;

import java.util.List;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Continuous public-security foyer between the GeoFront station and H-01.
 *
 * <p>The north H-01 threshold is twenty-four blocks above the south station
 * threshold. Two broad, axis-aligned switchbacks make that change without
 * teleportation, diagonal stairs or unsupported exits.</p>
 */
public final class NervFoyerV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "NERV_FOYER";
    private static final String STAGE = "S02_E_NERV_FOYER";
    private static final String PLAN_VERSION = "nerv-foyer-v2-a2";

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
    private static final BlockState RED =
            Blocks.RED_CONCRETE.defaultBlockState();
    private static final BlockState GLASS =
            Blocks.GRAY_STAINED_GLASS.defaultBlockState();
    private static final BlockState LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState RAIL =
            Blocks.IRON_BARS.defaultBlockState();
    private static final BlockState NORTH_STAIR =
            Blocks.SMOOTH_QUARTZ_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.NORTH);
    private static final BlockState EAST_STAIR =
            Blocks.SMOOTH_QUARTZ_STAIRS.defaultBlockState()
                    .setValue(StairBlock.FACING, Direction.EAST);

    private final FacilitySchemaV2.IntBox owner;
    private final int centreX;
    private final int centreZ;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public NervFoyerV2Plan(FacilitySchemaV2.ResolvedManifest manifest)
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

        if (x == -72 || x == 71 || z == 96 || z == 183
                || y == -368 || y == -321)
        {
            return shellPattern(x, y, z);
        }
        return AIR;
    }

    private BlockState authoredBlock(int x, int y, int z)
    {
        BlockState deck = decks(x, y, z);
        if (deck != null)
        {
            return deck;
        }

        BlockState stair = switchbackStairs(x, y, z);
        if (stair != null)
        {
            return stair;
        }

        BlockState wall = enclosureAndSupports(x, y, z);
        if (wall != null)
        {
            return wall;
        }

        BlockState furnishing = furnishings(x, y, z);
        if (furnishing != null)
        {
            return furnishing;
        }

        return safetyAndLighting(x, y, z);
    }

    private BlockState decks(int x, int y, int z)
    {
        // H-01 upper vestibule, centred on the registered north port.
        if (y == -333 && inBox(x, z, -12, 12, 97, 120))
        {
            return floorPattern(x, z);
        }

        // The first flight reaches a real turn landing. The second flight
        // leaves its east edge, so there is no diagonal or floating shortcut.
        if (y == -345 && inBox(x, z, -38, -20, 120, 148))
        {
            return floorPattern(x, z);
        }

        // GeoFront station/security floor. A west return at its north edge
        // meets the first flight while the central aisle remains unobstructed.
        if (y == -357 && (inBox(x, z, -32, 32, 160, 183)
                || inBox(x, z, -40, 32, 158, 166)))
        {
            return floorPattern(x, z);
        }

        // Short upper threshold joins the eastbound flight to H-01.
        if (y == -333 && inBox(x, z, -8, 12, 116, 132))
        {
            return FLOOR;
        }
        return null;
    }

    private BlockState switchbackStairs(int x, int y, int z)
    {
        // Flight A rises due north from the lower security deck. It occupies
        // one lane only; the remaining contract envelope is its approach and
        // turn landing.
        for (int step = 0; step < 12; step++)
        {
            int stepZ = 159 - step;
            int treadY = -356 + step;
            if (x >= -36 && x < -24 && z == stepZ)
            {
                if (y == treadY)
                {
                    return NORTH_STAIR;
                }
                if (y >= -367 && y < treadY)
                {
                    return STRUCTURE;
                }
            }
        }

        // Flight B turns exactly ninety degrees and rises due east. No tread
        // changes X and Z in the same step.
        for (int step = 0; step < 12; step++)
        {
            int stepX = -20 + step;
            int treadY = -344 + step;
            if (x == stepX && z >= 120 && z < 132)
            {
                if (y == treadY)
                {
                    return EAST_STAIR;
                }
                if (y >= -367 && y < treadY)
                {
                    return STRUCTURE;
                }
            }
        }
        return null;
    }

    private BlockState enclosureAndSupports(int x, int y, int z)
    {
        // Four monumental side piers read as a real underground load path.
        if ((inBox(x, z, -62, -57, 104, 176)
                || inBox(x, z, 57, 62, 104, 176))
                && y >= -367 && y <= -322)
        {
            return Math.floorMod(y + 368, 8) == 0 ? ORANGE : STRUCTURE;
        }

        // Upper and lower vestibules are pressure-safe rooms rather than
        // apertures exposed directly to the enormous atrium.
        if (inBox(x, z, -14, 14, 97, 112)
                && y >= -332 && y <= -325)
        {
            boolean edge = x == -14 || x == 13 || z == 111;
            boolean roof = y == -325;
            boolean southDoor = z == 111 && x >= -4 && x <= 3
                    && y <= -327;
            if ((edge || roof) && !southDoor)
            {
                return y == -329 && edge ? GLASS : STRUCTURE;
            }
        }
        if (inBox(x, z, -18, 18, 168, 183)
                && y >= -356 && y <= -349)
        {
            boolean edge = x == -18 || x == 17 || z == 168;
            boolean roof = y == -349;
            boolean northDoor = z == 168 && x >= -4 && x <= 3
                    && y <= -351;
            if ((edge || roof) && !northDoor)
            {
                return y == -353 && edge ? GLASS : STRUCTURE;
            }
        }

        // Visible supports follow the actual route footprint rather than
        // holding up the former full-width decorative galleries.
        if (y >= -367
                && ((y < -333 && (x == -10 || x == 9)
                && (z == 100 || z == 116))
                || (y < -345 && (x == -36 || x == -21)
                && (z == 122 || z == 144))
                || (y < -357 && (x == -30 || x == 29)
                && (z == 162 || z == 180))))
        {
            return STRUCTURE;
        }
        return null;
    }

    private BlockState furnishings(int x, int y, int z)
    {
        // Security/check-in desk faces the arriving public at the lower
        // vestibule. Its centre stays open as a staffed passage.
        if (y == -356 && z >= 164 && z <= 166
                && ((x >= -24 && x <= -6) || (x >= 5 && x <= 23)))
        {
            if (z == 164 && (x == -24 || x == 23))
            {
                return RED;
            }
            return Math.floorMod(x, 7) == 0 ? LIGHT : DARK;
        }
        if (y == -355 && z == 165
                && (x == -18 || x == -10 || x == 10 || x == 18))
        {
            return Blocks.CYAN_STAINED_GLASS.defaultBlockState();
        }

        // Large NERV colour datum on the north wall makes orientation clear
        // without relying on floating signs.
        if (z == 98 && y >= -348 && y <= -337
                && Math.abs(x) <= 38)
        {
            int diagonal = Math.abs(Math.abs(x) - (y + 349) * 3);
            if (diagonal <= 1 || Math.abs(x) <= 2)
            {
                return RED;
            }
        }
        return null;
    }

    private BlockState safetyAndLighting(int x, int y, int z)
    {
        // Guard rails follow the single authored path and stop at every
        // threshold. They cannot imply a second, inaccessible route.
        if (y == -332 && z == 119
                && x >= -12 && x < -8)
        {
            return RAIL;
        }
        if (y == -344 && z == 119
                && x >= -38 && x < -20)
        {
            return RAIL;
        }
        if (y == -356 && z == 157
                && x >= -24 && x < 32)
        {
            return RAIL;
        }
        if ((x == -37 || x == -24) && z >= 148 && z < 160)
        {
            int step = 159 - z;
            if (y == -355 + step)
            {
                return RAIL;
            }
        }
        if ((z == 119 || z == 132) && x >= -20 && x < -8)
        {
            int step = x + 20;
            if (y == -343 + step)
            {
                return RAIL;
            }
        }

        // Repeating wall and ceiling luminaires keep the long underground
        // approach readable without a synthetic sun.
        if ((x == -70 || x == 69) && y >= -360 && y <= -328
                && Math.floorMod(y + 360, 8) == 0
                && Math.floorMod(z - 100, 12) <= 2)
        {
            return LIGHT;
        }
        if (y == -322 && Math.floorMod(x + 64, 16) <= 2
                && Math.floorMod(z - 100, 18) <= 2)
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
        if (Math.floorMod(x, 12) == 0 || Math.floorMod(z, 12) == 0)
        {
            return DARK;
        }
        return Math.floorMod(x + z, 17) == 0 ? LIGHT : FLOOR;
    }

    private static BlockState shellPattern(int x, int y, int z)
    {
        if (Math.floorMod(x + z, 24) <= 1
                || Math.floorMod(y + 368, 12) == 0)
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
