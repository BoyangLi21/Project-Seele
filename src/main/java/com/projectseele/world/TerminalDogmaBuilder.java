package com.projectseele.world;

import java.util.Locale;

import com.projectseele.entity.LilithEntity;
import com.projectseele.registry.ModEntities;
import com.projectseele.registry.ModFluids;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LadderBlock;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Physical Central-Dogma descent and the sealed Terminal-Dogma chamber.
 *
 * <p>The downloaded command module ends at the eastern edge of the lower
 * concourse.  This builder starts there, outside its bounding box, and keeps
 * every deep facility below the imported GeoFront shell.  The player can walk
 * and climb the complete route; the command shortcut is never required.</p>
 */
public final class TerminalDogmaBuilder
{
    /** Moves the complete deep facility down while its shaft still opens at NERV. */
    public static final int FACILITY_Y_OFFSET = -64;
    public static final int SHAFT_X = 42;
    public static final int SHAFT_Z = -23;
    public static final int SHAFT_TOP_Y = 65;
    public static final int SHAFT_BOTTOM_Y = -59;
    public static final int CHAMBER_CENTRE_Y = -58;
    public static final int CHAMBER_RADIUS_X = 24;
    public static final int CHAMBER_RADIUS_Y = 22;
    public static final int CHAMBER_RADIUS_Z = 28;
    public static final int OBSERVATION_Y = -59;
    public static final int OBSERVATION_Z = 22;
    public static final int LCL_SURFACE_Y = -75;
    public static final int MIN_RELATIVE_Y = -81;

    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;
    private static final int SHAFT_RADIUS = 5;

    private TerminalDogmaBuilder() {}

    public static TerminalDogmaAudit build(ServerLevel level, BlockPos origin)
    {
        BlockPos facilityOrigin = origin.offset(0, FACILITY_Y_OFFSET, 0);
        buildChamber(level, facilityOrigin);
        buildLclSealLake(level, facilityOrigin);
        buildContainmentCross(level, facilityOrigin);
        spawnLilith(level, facilityOrigin);
        buildObservationCatwalk(level, facilityOrigin);
        buildContainmentLighting(level, facilityOrigin);
        buildCentralDogmaShaft(level, facilityOrigin);
        buildTopAccess(level, facilityOrigin);
        buildDeepAccess(level, facilityOrigin);
        return inspect(level, origin);
    }


    /**
     * Upgrades an installed save without rebuilding the complete chamber.
     * The legacy quartz marker is intentionally specific so normal logins only
     * perform one bounded entity query and never rewrite the crucifix.
     */
    public static boolean repairRuntimeSpecimen(ServerLevel level,
                                                BlockPos origin)
    {
        BlockPos facilityOrigin = origin.offset(0, FACILITY_Y_OFFSET, 0);
        AABB bounds = specimenBounds(facilityOrigin);
        boolean missing = level.getEntitiesOfClass(
                LilithEntity.class, bounds).isEmpty();
        BlockState legacyMarker = level.getBlockState(
                facilityOrigin.offset(0, -43, -22));
        boolean legacy = legacyMarker.is(Blocks.SMOOTH_QUARTZ)
                || legacyMarker.is(Blocks.QUARTZ_BLOCK)
                || legacyMarker.is(Blocks.CALCITE);
        if (missing || legacy)
        {
            buildContainmentCross(level, facilityOrigin);
            spawnLilith(level, facilityOrigin);
        }
        return !level.getEntitiesOfClass(LilithEntity.class,
                bounds).isEmpty();
    }
    public static TerminalDogmaAudit inspect(ServerLevel level, BlockPos origin)
    {
        origin = origin.offset(0, FACILITY_Y_OFFSET, 0);
        boolean topAccess = isWalkable(level,
                origin.offset(34, SHAFT_TOP_Y, SHAFT_Z));
        int ladders = 0;
        for (int y = SHAFT_BOTTOM_Y + 1; y <= SHAFT_TOP_Y + 1; y++)
        {
            if (level.getBlockState(origin.offset(
                    SHAFT_X, y, SHAFT_Z - 4)).is(Blocks.LADDER))
            {
                ladders++;
            }
        }
        boolean shaftApertures = level.getBlockState(origin.offset(
                SHAFT_X, -11, SHAFT_Z - 3)).isAir()
                && level.getBlockState(origin.offset(
                SHAFT_X, -23, SHAFT_Z - 3)).isAir();
        boolean shaft = ladders == SHAFT_TOP_Y - SHAFT_BOTTOM_Y + 1
                && level.getBlockState(origin.offset(
                SHAFT_X, SHAFT_BOTTOM_Y, SHAFT_Z)).is(Blocks.LODESTONE)
                && shaftApertures;
        boolean deepAccess = isWalkable(level,
                origin.offset(24, SHAFT_BOTTOM_Y, -10));
        boolean chamber = level.getBlockState(origin.offset(
                0, CHAMBER_CENTRE_Y + CHAMBER_RADIUS_Y, 0))
                .is(Blocks.CALCITE)
                && level.getBlockState(origin.offset(
                0, CHAMBER_CENTRE_Y, -CHAMBER_RADIUS_Z))
                .is(Blocks.POLISHED_BASALT)
                && level.getBlockState(origin.offset(
                0, -58, -12)).is(Blocks.LIGHT);
        boolean lclSeal = level.getFluidState(origin.offset(
                0, LCL_SURFACE_Y, 0)).getFluidType()
                == ModFluids.LCL_TYPE.get();
        boolean containmentCross = level.getBlockState(origin.offset(
                0, -50, -25)).is(Blocks.REDSTONE_BLOCK)
                && level.getBlockState(origin.offset(
                20, -50, -23)).is(Blocks.RED_STAINED_GLASS);
        boolean sealedSpecimen = !level.getEntitiesOfClass(LilithEntity.class,
                AABB.ofSize(Vec3.atCenterOf(origin.offset(0, -59, 0)),
                        64.0D, 48.0D, 96.0D)).isEmpty();
        boolean observation = level.getBlockState(origin.offset(
                0, OBSERVATION_Y, OBSERVATION_Z)).is(Blocks.LODESTONE)
                && level.getBlockState(origin.offset(
                23, -68, 18)).is(Blocks.LADDER);
        boolean valid = topAccess && shaft && deepAccess && chamber
                && lclSeal && containmentCross && sealedSpecimen
                && observation;
        return new TerminalDogmaAudit(valid, topAccess, ladders,
                shaftApertures, shaft,
                deepAccess, chamber, lclSeal, containmentCross,
                sealedSpecimen, observation);
    }

    private static boolean isWalkable(ServerLevel level, BlockPos floor)
    {
        return !level.getBlockState(floor).isAir()
                && level.getBlockState(floor.above()).isAir()
                && level.getBlockState(floor.above(2)).isAir();
    }

    private static void buildChamber(ServerLevel level, BlockPos origin)
    {
        for (int x = -CHAMBER_RADIUS_X; x <= CHAMBER_RADIUS_X; x++)
        {
            for (int y = -CHAMBER_RADIUS_Y; y <= CHAMBER_RADIUS_Y; y++)
            {
                for (int z = -CHAMBER_RADIUS_Z; z <= CHAMBER_RADIUS_Z; z++)
                {
                    double distance = square(x / (double) CHAMBER_RADIUS_X)
                            + square(y / (double) CHAMBER_RADIUS_Y)
                            + square(z / (double) CHAMBER_RADIUS_Z);
                    if (distance > 1.0D)
                    {
                        continue;
                    }
                    BlockPos position = origin.offset(
                            x, CHAMBER_CENTRE_Y + y, z);
                    if (distance >= 0.86D)
                    {
                        // Deliberate concentric ribs read as an engineered
                        // containment shell.  The previous random calcite
                        // flecks became bright visual noise and hid the
                        // crucifix at normal gameplay exposure.
                        boolean horizontalRib = Math.floorMod(y, 7) == 0;
                        boolean verticalRib = Math.floorMod(x + 24, 12) == 0
                                && Math.floorMod(z + 28, 8) <= 1;
                        BlockState shell = horizontalRib
                                ? Blocks.POLISHED_BASALT.defaultBlockState()
                                : (verticalRib
                                ? Blocks.DEEPSLATE_TILES.defaultBlockState()
                                : Blocks.DEEPSLATE_BRICKS.defaultBlockState());
                        set(level, position, shell);
                    }
                    else
                    {
                        clear(level, position);
                    }
                }
            }
        }

        // Deterministic audit ribs at the crown and east equator.
        set(level, origin.offset(0,
                CHAMBER_CENTRE_Y + CHAMBER_RADIUS_Y, 0),
                Blocks.CALCITE.defaultBlockState());
        // East is opened by the tunnel and both side equators are crossed by
        // the U-shaped observation deck. The sealed north rib is the stable
        // structural marker and never competes with a traversable route.
        set(level, origin.offset(0, CHAMBER_CENTRE_Y,
                -CHAMBER_RADIUS_Z),
                Blocks.POLISHED_BASALT.defaultBlockState());
    }

    private static void buildLclSealLake(ServerLevel level, BlockPos origin)
    {
        final int radiusX = 18;
        final int radiusZ = 13;
        for (int x = -20; x <= 20; x++)
        {
            for (int z = -15; z <= 15; z++)
            {
                double distance = square(x / (double) radiusX)
                        + square(z / (double) radiusZ);
                if (distance <= 1.0D)
                {
                    BlockState bed = Math.floorMod(x * 19 + z * 29, 17) == 0
                            ? Blocks.SEA_LANTERN.defaultBlockState()
                            : Blocks.ORANGE_CONCRETE.defaultBlockState();
                    set(level, origin.offset(x, -79, z), bed);
                    for (int y = -78; y <= LCL_SURFACE_Y; y++)
                    {
                        set(level, origin.offset(x, y, z),
                                ModFluids.LCL_SOURCE.get().defaultFluidState()
                                        .createLegacyBlock());
                    }
                }
                else if (distance <= 1.24D)
                {
                    set(level, origin.offset(x, LCL_SURFACE_Y, z),
                            Math.floorMod(x + z, 5) == 0
                                    ? Blocks.SEA_LANTERN.defaultBlockState()
                                    : Blocks.POLISHED_BLACKSTONE.defaultBlockState());
                }
            }
        }
    }

    private static void buildContainmentCross(ServerLevel level,
                                              BlockPos origin)
    {
        // A luminous pure-red crucifix has to remain the first readable
        // silhouette even at the deliberately low Terminal-Dogma exposure.
        fillBox(level, origin, -4, 4, -77, -36, -26, -24,
                Blocks.REDSTONE_BLOCK.defaultBlockState());
        fillBox(level, origin, -21, 21, -55, -47, -26, -24,
                Blocks.REDSTONE_BLOCK.defaultBlockState());
        // Red glass in front of a sparse luminous core retains a pure-red
        // face instead of collapsing into a black shape under the chamber's
        // low ambient light.  The specimen is built afterwards and therefore
        // naturally occludes the cross at the body contact points.
        fillBox(level, origin, -4, 4, -77, -36, -23, -23,
                Blocks.RED_STAINED_GLASS.defaultBlockState());
        fillBox(level, origin, -21, 21, -55, -47, -23, -23,
                Blocks.RED_STAINED_GLASS.defaultBlockState());
        for (int y = -76; y <= -37; y += 4)
        {
            set(level, origin.offset(0, y, -24),
                    Blocks.SHROOMLIGHT.defaultBlockState());
        }
        for (int x = -20; x <= 20; x += 4)
        {
            set(level, origin.offset(x, -50, -24),
                    Blocks.SHROOMLIGHT.defaultBlockState());
        }
        // White sealed giant: a block-built static structure, deliberately
        // separate from EVA animation/rendering until a reviewed model exists.
        for (int x = -4; x <= 4; x++)
        {
            for (int y = -5; y <= 5; y++)
            {
                for (int z = -2; z <= 2; z++)
                {
                    if (square(x / 4.5D) + square(y / 5.5D)
                            + square(z / 2.5D) <= 1.0D)
                    {
                        set(level, origin.offset(x, -43 + y, -22 + z),
                                Blocks.SMOOTH_QUARTZ.defaultBlockState());
                    }
                }
            }
        }
        // Crucified shoulders and arms are segmented and taper toward the
        // wrists instead of reading as one rectangular white crossbar.
        fillBox(level, origin, -6, 6, -51, -48, -23, -21,
                Blocks.CALCITE.defaultBlockState());
        for (int x = 7; x <= 18; x++)
        {
            int lift = (x - 7) / 6;
            fillBox(level, origin, x, x, -51 + lift, -49 + lift,
                    -23, -21, Blocks.SMOOTH_QUARTZ.defaultBlockState());
            fillBox(level, origin, -x, -x, -51 + lift, -49 + lift,
                    -23, -21, Blocks.SMOOTH_QUARTZ.defaultBlockState());
        }
        set(level, origin.offset(-19, -48, -21),
                Blocks.REDSTONE_BLOCK.defaultBlockState());
        set(level, origin.offset(19, -48, -21),
                Blocks.REDSTONE_BLOCK.defaultBlockState());
        for (int y = -48; y >= -63; y--)
        {
            int half = y >= -55 ? 6 - (-48 - y) / 2
                    : 3 + Math.max(0, (-59 - y) / 2);
            fillBox(level, origin, -half, half, y, y, -23, -21,
                    Math.floorMod(y, 4) == 0
                            ? Blocks.QUARTZ_BLOCK.defaultBlockState()
                            : Blocks.SMOOTH_QUARTZ.defaultBlockState());
        }
        for (int y = -64; y >= -75; y--)
        {
            int spread = Math.min(3, (-64 - y) / 4);
            fillBox(level, origin, -4 - spread, -2 - spread,
                    y, y, -23, -21,
                    Blocks.SMOOTH_QUARTZ.defaultBlockState());
            fillBox(level, origin, 2 + spread, 4 + spread,
                    y, y, -23, -21,
                    Blocks.SMOOTH_QUARTZ.defaultBlockState());
        }

        int[][] eyes = {
                {-2, -44}, {0, -45}, {2, -44},
                {-2, -42}, {0, -43}, {2, -42}, {0, -40}
        };
        for (int[] eye : eyes)
        {
            set(level, origin.offset(eye[0], eye[1], -19),
                    Blocks.REDSTONE_BLOCK.defaultBlockState());
        }
        set(level, origin.offset(0, -55, -22),
                Blocks.SEA_LANTERN.defaultBlockState());
        set(level, origin.offset(0, -55, -21),
                Blocks.RED_STAINED_GLASS.defaultBlockState());

        // A red forked sealing spear enters the chest from the east balcony.
        buildLine(level, origin, 22, -45, -18,
                0, -55, -20, Blocks.REDSTONE_BLOCK.defaultBlockState());
        buildLine(level, origin, 22, -45, -18,
                19, -41, -18, Blocks.REDSTONE_BLOCK.defaultBlockState());
        buildLine(level, origin, 22, -45, -18,
                19, -49, -18, Blocks.REDSTONE_BLOCK.defaultBlockState());

        // Remove the former block-built humanoid and block spear. The red
        // crucifix backing at z=-26..-24 remains; its front glass is restored
        // after the bounded clear so existing saves upgrade without overlap.
        for (int x = -22; x <= 22; x++)
        {
            for (int y = -77; y <= -36; y++)
            {
                for (int z = -23; z <= -18; z++)
                {
                    clear(level, origin.offset(x, y, z));
                }
            }
        }
        fillBox(level, origin, -4, 4, -77, -36, -23, -23,
                Blocks.RED_STAINED_GLASS.defaultBlockState());
        fillBox(level, origin, -21, 21, -55, -47, -23, -23,
                Blocks.RED_STAINED_GLASS.defaultBlockState());
    }

    private static void buildObservationCatwalk(ServerLevel level,
                                                BlockPos origin)
    {
        for (int x = -24; x <= 24; x++)
        {
            for (int z = -24; z <= 24; z++)
            {
                boolean deck = z >= 20 || Math.abs(x) >= 20;
                if (!deck)
                {
                    continue;
                }
                set(level, origin.offset(x, OBSERVATION_Y, z),
                        Math.floorMod(x * 3 + z, 9) == 0
                                ? Blocks.SEA_LANTERN.defaultBlockState()
                                : Blocks.POLISHED_BLACKSTONE.defaultBlockState());
                for (int y = OBSERVATION_Y + 1;
                     y <= OBSERVATION_Y + 4; y++)
                {
                    clear(level, origin.offset(x, y, z));
                }
            }
        }
        for (int x = -24; x <= 24; x++)
        {
            set(level, origin.offset(x, OBSERVATION_Y + 1, 25),
                    Blocks.IRON_BARS.defaultBlockState());
        }
        for (int z = -24; z <= 25; z++)
        {
            set(level, origin.offset(-25, OBSERVATION_Y + 1, z),
                    Blocks.IRON_BARS.defaultBlockState());
            set(level, origin.offset(25, OBSERVATION_Y + 1, z),
                    Blocks.IRON_BARS.defaultBlockState());
        }
        set(level, origin.offset(0, OBSERVATION_Y, OBSERVATION_Z),
                Blocks.LODESTONE.defaultBlockState());

        // A second physical route descends from the gallery to the LCL rim.
        BlockState ladder = Blocks.LADDER.defaultBlockState()
                .setValue(LadderBlock.FACING, Direction.WEST);
        for (int y = -77; y <= OBSERVATION_Y + 1; y++)
        {
            set(level, origin.offset(24, y, 18),
                    Blocks.BLACK_CONCRETE.defaultBlockState());
            if (y > -77)
            {
                set(level, origin.offset(23, y, 18), ladder);
            }
        }
        for (int x = 18; x <= 23; x++)
        {
            for (int z = 15; z <= 21; z++)
            {
                set(level, origin.offset(x, -77, z),
                        Blocks.POLISHED_BLACKSTONE.defaultBlockState());
            }
        }
    }

    private static void buildContainmentLighting(ServerLevel level,
                                                 BlockPos origin)
    {
        // Invisible light blocks preserve the black sealed-chamber material
        // while making the white giant, red cross and orange LCL readable.
        // They have no collision and therefore do not interrupt the gallery.
        for (int x = -18; x <= 18; x += 6)
        {
            for (int y : new int[] {-70, -58, -46})
            {
                set(level, origin.offset(x, y, -12),
                        Blocks.LIGHT.defaultBlockState());
                set(level, origin.offset(x, y, 10),
                        Blocks.LIGHT.defaultBlockState());
            }
        }
        for (int z = -18; z <= 12; z += 6)
        {
            set(level, origin.offset(-16, -54, z),
                    Blocks.LIGHT.defaultBlockState());
            set(level, origin.offset(16, -54, z),
                    Blocks.LIGHT.defaultBlockState());
        }
        for (int x : new int[] {-14, -9, 9, 14})
        {
            for (int y : new int[] {-60, -52, -44})
            {
                set(level, origin.offset(x, y, -19),
                        Blocks.LIGHT.defaultBlockState());
            }
        }
    }

    private static void buildCentralDogmaShaft(ServerLevel level,
                                               BlockPos origin)
    {
        for (int y = SHAFT_BOTTOM_Y; y <= SHAFT_TOP_Y + 6; y++)
        {
            for (int x = -SHAFT_RADIUS; x <= SHAFT_RADIUS; x++)
            {
                for (int z = -SHAFT_RADIUS; z <= SHAFT_RADIUS; z++)
                {
                    BlockPos position = origin.offset(
                            SHAFT_X + x, y, SHAFT_Z + z);
                    if (y == SHAFT_BOTTOM_Y)
                    {
                        set(level, position,
                                Blocks.POLISHED_DEEPSLATE.defaultBlockState());
                    }
                    else if (Math.abs(x) == SHAFT_RADIUS
                            || Math.abs(z) == SHAFT_RADIUS)
                    {
                        BlockState wall = Math.floorMod(y, 12) == 0
                                ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                                : Blocks.DEEPSLATE_TILES.defaultBlockState();
                        set(level, position, wall);
                    }
                    else
                    {
                        clear(level, position);
                    }
                }
            }
            if (y > SHAFT_BOTTOM_Y
                    && Math.floorMod(y - SHAFT_BOTTOM_Y, 6) == 0)
            {
                // Visible paired guide lights communicate the full descent
                // and give players a scale reference between landings.
                set(level, origin.offset(SHAFT_X - SHAFT_RADIUS,
                        y, SHAFT_Z), Blocks.SEA_LANTERN.defaultBlockState());
                set(level, origin.offset(SHAFT_X + SHAFT_RADIUS,
                        y, SHAFT_Z), Blocks.SEA_LANTERN.defaultBlockState());
            }
            if (y > SHAFT_BOTTOM_Y && Math.floorMod(y - SHAFT_BOTTOM_Y, 12) == 0)
            {
                for (int x = -3; x <= 4; x++)
                {
                    for (int z = -3; z <= 4; z++)
                    {
                        // A three-wide aperture beside the ladder keeps every
                        // landing climbable and exposes the vertical depth to
                        // the fixed inspection camera.
                        if (Math.abs(x) <= 1 && z <= -2)
                        {
                            clear(level, origin.offset(SHAFT_X + x, y,
                                    SHAFT_Z + z));
                            continue;
                        }
                        set(level, origin.offset(SHAFT_X + x, y,
                                SHAFT_Z + z),
                                Blocks.IRON_BLOCK.defaultBlockState());
                    }
                }
            }
            if (Math.floorMod(y, 8) == 0)
            {
                set(level, origin.offset(SHAFT_X, y, SHAFT_Z + 5),
                        Blocks.SEA_LANTERN.defaultBlockState());
            }
        }

        BlockState ladder = Blocks.LADDER.defaultBlockState()
                .setValue(LadderBlock.FACING, Direction.SOUTH);
        for (int y = SHAFT_BOTTOM_Y + 1; y <= SHAFT_TOP_Y + 1; y++)
        {
            set(level, origin.offset(SHAFT_X, y, SHAFT_Z - 4), ladder);
        }
        set(level, origin.offset(SHAFT_X, SHAFT_BOTTOM_Y, SHAFT_Z),
                Blocks.LODESTONE.defaultBlockState());
    }

    private static void buildTopAccess(ServerLevel level, BlockPos origin)
    {
        buildCorridorX(level, origin, 32, 37, SHAFT_TOP_Y, -26, -20);
        set(level, origin.offset(34, SHAFT_TOP_Y, SHAFT_Z),
                Blocks.ORANGE_CONCRETE.defaultBlockState());
    }

    private static void buildDeepAccess(ServerLevel level, BlockPos origin)
    {
        buildCorridorX(level, origin, 24, 37,
                SHAFT_BOTTOM_Y, -26, -20);
        for (int z = -23; z <= 2; z++)
        {
            for (int x = 21; x <= 27; x++)
            {
                set(level, origin.offset(x, SHAFT_BOTTOM_Y, z),
                        x == 24 && Math.floorMod(z, 5) < 2
                                ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                                : Blocks.POLISHED_BLACKSTONE.defaultBlockState());
                for (int y = SHAFT_BOTTOM_Y + 1;
                     y <= SHAFT_BOTTOM_Y + 6; y++)
                {
                    clear(level, origin.offset(x, y, z));
                }
                set(level, origin.offset(x, SHAFT_BOTTOM_Y + 7, z),
                        Math.floorMod(z, 6) == 0
                                ? Blocks.SEA_LANTERN.defaultBlockState()
                                : Blocks.IRON_BLOCK.defaultBlockState());
            }
            for (int y = SHAFT_BOTTOM_Y + 1;
                 y <= SHAFT_BOTTOM_Y + 6; y++)
            {
                set(level, origin.offset(20, y, z),
                        Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
                set(level, origin.offset(28, y, z),
                        Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
            }
        }
        set(level, origin.offset(24, SHAFT_BOTTOM_Y, -10),
                Blocks.LODESTONE.defaultBlockState());

        // Open quarantine ribs rather than a closed redstone door so the
        // route remains traversable in a fresh survival test world.
        for (int y = SHAFT_BOTTOM_Y + 1; y <= SHAFT_BOTTOM_Y + 6; y++)
        {
            set(level, origin.offset(20, y, -4),
                    Blocks.IRON_BLOCK.defaultBlockState());
            set(level, origin.offset(28, y, -4),
                    Blocks.IRON_BLOCK.defaultBlockState());
        }
        for (int x = 20; x <= 28; x++)
        {
            set(level, origin.offset(x, SHAFT_BOTTOM_Y + 7, -4),
                    x % 2 == 0 ? Blocks.REDSTONE_LAMP.defaultBlockState()
                            : Blocks.IRON_BLOCK.defaultBlockState());
        }
    }

    private static void buildCorridorX(ServerLevel level, BlockPos origin,
                                       int minX, int maxX, int floorY,
                                       int minZ, int maxZ)
    {
        for (int x = minX; x <= maxX; x++)
        {
            for (int z = minZ; z <= maxZ; z++)
            {
                set(level, origin.offset(x, floorY, z),
                        z == SHAFT_Z && Math.floorMod(x, 5) < 2
                                ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                                : Blocks.POLISHED_BLACKSTONE.defaultBlockState());
                for (int y = floorY + 1; y <= floorY + 5; y++)
                {
                    clear(level, origin.offset(x, y, z));
                }
                set(level, origin.offset(x, floorY + 6, z),
                        Math.floorMod(x, 6) == 0
                                ? Blocks.SEA_LANTERN.defaultBlockState()
                                : Blocks.IRON_BLOCK.defaultBlockState());
            }
            for (int y = floorY + 1; y <= floorY + 5; y++)
            {
                set(level, origin.offset(x, y, minZ - 1),
                        Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
                set(level, origin.offset(x, y, maxZ + 1),
                        Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
            }
        }
    }

    private static void spawnLilith(ServerLevel level, BlockPos origin)
    {
        BlockPos anchor = origin.offset(0, LCL_SURFACE_Y, -22);
        AABB bounds = specimenBounds(origin);
        var specimens = level.getEntitiesOfClass(LilithEntity.class, bounds);
        LilithEntity specimen;
        boolean created = specimens.isEmpty();
        if (created)
        {
            specimen = ModEntities.LILITH.get().create(level);
            if (specimen == null)
            {
                return;
            }
        }
        else
        {
            specimen = specimens.get(0);
            for (int index = 1; index < specimens.size(); index++)
            {
                specimens.get(index).discard();
            }
        }
        specimen.moveTo(anchor.getX() + 0.5D, anchor.getY(),
                anchor.getZ() + 0.5D, 180.0F, 0.0F);
        specimen.setNoAi(true);
        specimen.setNoGravity(true);
        specimen.setInvulnerable(true);
        specimen.setPersistenceRequired();
        specimen.addTag("projectseele.terminal_dogma_lilith");
        specimen.setHealth(specimen.getMaxHealth());
        if (created)
        {
            level.addFreshEntity(specimen);
        }
    }


    private static AABB specimenBounds(BlockPos origin)
    {
        return AABB.ofSize(Vec3.atCenterOf(origin.offset(0, -59, 0)),
                64.0D, 48.0D, 96.0D);
    }
    private static void buildLine(ServerLevel level, BlockPos origin,
                                  int x0, int y0, int z0,
                                  int x1, int y1, int z1,
                                  BlockState state)
    {
        int steps = Math.max(Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0)),
                Math.abs(z1 - z0));
        for (int step = 0; step <= steps; step++)
        {
            double amount = steps == 0 ? 0.0D : step / (double) steps;
            int x = (int) Math.round(x0 + (x1 - x0) * amount);
            int y = (int) Math.round(y0 + (y1 - y0) * amount);
            int z = (int) Math.round(z0 + (z1 - z0) * amount);
            set(level, origin.offset(x, y, z), state);
        }
    }

    private static void fillBox(ServerLevel level, BlockPos origin,
                                int minX, int maxX, int minY, int maxY,
                                int minZ, int maxZ, BlockState state)
    {
        for (int x = minX; x <= maxX; x++)
        {
            for (int y = minY; y <= maxY; y++)
            {
                for (int z = minZ; z <= maxZ; z++)
                {
                    set(level, origin.offset(x, y, z), state);
                }
            }
        }
    }

    private static double square(double value)
    {
        return value * value;
    }

    private static void clear(ServerLevel level, BlockPos position)
    {
        set(level, position, Blocks.AIR.defaultBlockState());
    }

    private static void set(ServerLevel level, BlockPos position,
                            BlockState state)
    {
        if (!level.getBlockState(position).equals(state))
        {
            level.setBlock(position, state, UPDATE_CLIENTS);
        }
    }

    public record TerminalDogmaAudit(boolean valid, boolean topAccess,
                                     int ladders, boolean shaftApertures,
                                     boolean shaft,
                                     boolean deepAccess, boolean chamber,
                                     boolean lclSeal,
                                     boolean containmentCross,
                                     boolean sealedSpecimen,
                                     boolean observation)
    {
        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s topAccess=%s ladder=%d/%d apertures=%s shaft=%s "
                            + "deepAccess=%s chamber=%s lclSeal=%s "
                            + "cross=%s specimen=%s observation=%s",
                    this.valid, this.topAccess, this.ladders,
                    SHAFT_TOP_Y - SHAFT_BOTTOM_Y + 1,
                    this.shaftApertures, this.shaft,
                    this.deepAccess, this.chamber, this.lclSeal,
                    this.containmentCross, this.sealedSpecimen,
                    this.observation);
        }
    }
}
