package com.projectseele.world;

import java.util.Locale;

import com.projectseele.ProjectSeele;
import com.projectseele.registry.ModFluids;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.FluidTags;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LadderBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.Fluids;

/** Full underground GeoFront sphere and its NERV command pyramid. */
public final class GeoFrontBuilder
{
    public static final int CAVERN_RADIUS = 320;
    /** Sphere centre relative to the NERV floor origin. */
    public static final int CAVERN_CENTRE_Y = 112;
    public static final int CAVERN_CENTRE_Z = -76;
    public static final int CAVERN_TOP_Y = CAVERN_CENTRE_Y + CAVERN_RADIUS;
    public static final int CAVERN_BOTTOM_Y = CAVERN_CENTRE_Y - CAVERN_RADIUS;
    public static final int OBSERVATION_Z = 100;
    public static final int OBSERVATION_Y = 24;
    public static final int[] LIFT_X = {-28, 0, 28};

    // The downloaded command module occupies X=-28..27, Y=-21..55 and
    // Z=-33..95. The NERV shell deliberately encloses that complete volume
    // instead of treating the command centre as an exterior annex.
    public static final int PYRAMID_BASE_CENTRE_Z = 31;
    public static final int PYRAMID_CENTRE_Z = 31;
    public static final int PYRAMID_BASE_Y = -22;
    public static final int PYRAMID_APEX_Y = 200;
    public static final int PYRAMID_BASE_HALF_X = 70;
    public static final int PYRAMID_BASE_HALF_Z = 100;
    private static final int PYRAMID_APEX_HALF = 0;
    private static final int PYRAMID_AUDIT_Y = 57;
    private static final ResourceLocation SKYWEAVE_ID =
            new ResourceLocation("ars_nouveau", "sky_block");
    private static boolean warnedMissingSkyweave;

    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;

    private GeoFrontBuilder() {}

    public static void build(ServerLevel level, BlockPos origin)
    {
        build(level, origin, false);
    }

    /** Builds the playable NERV facilities inside the complete buried sphere. */
    public static void build(ServerLevel level, BlockPos origin,
                             boolean preservePrivateShell)
    {
        buildSkyweaveSphere(level, origin);
        buildCavernFloor(level, origin);
        clearLegacyArtificialSun(level, origin);
        buildNaturalLake(level, origin);
        buildLclLake(level, origin);
        buildNervPyramid(level, origin);
        NervOperationsCentreBuilder.build(level, origin);
        MagiDeepLabBuilder.build(level, origin);
        TerminalDogmaBuilder.build(level, origin);
        NervOperationsCentreBuilder.linkFacilities(level, origin);
        buildEvaLiftTerminals(level, origin);
        buildCommandBridge(level, origin);
        buildForestRing(level, origin);
        buildObservationDeck(level, origin);
        repairCavernLighting(level, origin);
    }

    public static GeoFrontAudit inspect(ServerLevel level, BlockPos origin)
    {
        boolean floor = level.getBlockState(origin.offset(150, 0,
                CAVERN_CENTRE_Z)).is(Blocks.GRASS_BLOCK);
        BlockPos sphereCentre = cavernCentre(origin);
        BlockState expectedSky = skyweaveState();
        boolean skySphere = level.getBlockState(sphereCentre.offset(
                CAVERN_RADIUS, 0, 0)).is(expectedSky.getBlock())
                && level.getBlockState(sphereCentre.offset(
                -CAVERN_RADIUS, 0, 0)).is(expectedSky.getBlock())
                // The three audited launch shafts deliberately pierce the
                // absolute north pole. Sample the intact upper shoulder.
                && level.getBlockState(sphereCentre.offset(
                64, 248, 0)).is(expectedSky.getBlock())
                && level.getBlockState(sphereCentre.offset(
                0, -CAVERN_RADIUS, 0)).is(expectedSky.getBlock())
                && level.getBlockState(sphereCentre.offset(
                0, 0, CAVERN_RADIUS)).is(expectedSky.getBlock())
                && level.getBlockState(sphereCentre.offset(
                0, 0, -CAVERN_RADIUS)).is(expectedSky.getBlock());
        boolean lake = level.getFluidState(origin.offset(48, 1, 0))
                .getFluidType() == ModFluids.LCL_TYPE.get();
        boolean naturalLake = level.getFluidState(origin.offset(-125, 0, -125))
                .is(Fluids.WATER);
        boolean pyramid = level.getBlockState(origin.offset(
                        -PYRAMID_BASE_HALF_X, PYRAMID_BASE_Y,
                        PYRAMID_BASE_CENTRE_Z - PYRAMID_BASE_HALF_Z))
                .is(Blocks.CHISELED_DEEPSLATE)
                && level.getBlockState(origin.offset(
                        pyramidHalfXAt(PYRAMID_AUDIT_Y), PYRAMID_AUDIT_Y,
                        PYRAMID_CENTRE_Z
                                + pyramidHalfZAt(PYRAMID_AUDIT_Y)))
                .is(Blocks.CRYING_OBSIDIAN)
                && level.getBlockState(origin.offset(
                        0, PYRAMID_APEX_Y + 1, PYRAMID_CENTRE_Z))
                .is(Blocks.BEACON);
        boolean legacyInnerPyramidGone =
                level.getBlockState(origin.offset(34, 2, 0)).isAir()
                        && level.getBlockState(origin.offset(0, 2, -34)).isAir();
        boolean realSky = BuiltInRegistries.BLOCK.containsKey(SKYWEAVE_ID)
                && expectedSky.getBlock() == BuiltInRegistries.BLOCK.get(SKYWEAVE_ID);
        boolean cavernLighting = level.getBlockState(origin.offset(
                200, 0, CAVERN_CENTRE_Z)).is(Blocks.SEA_LANTERN)
                && level.getBlockState(origin.offset(216, 24, CAVERN_CENTRE_Z)).is(Blocks.LIGHT);
        int lifts = 0;
        int gantries = 0;
        for (int x : LIFT_X)
        {
            if (level.getBlockState(origin.offset(x, 1, -76)).is(Blocks.LODESTONE))
            {
                lifts++;
            }
            if (level.getBlockState(origin.offset(x, 27, -63)).is(Blocks.LADDER)
                    && !level.getBlockState(origin.offset(x, 27, -70)).isAir())
            {
                gantries++;
            }
        }
        boolean bridge = level.getBlockState(origin.offset(0, 2, 70))
                .is(Blocks.IRON_BLOCK);
        boolean observation = level.getBlockState(
                origin.offset(0, OBSERVATION_Y, OBSERVATION_Z)).is(Blocks.LODESTONE);
        NervOperationsCentreBuilder.OperationsAudit operations =
                NervOperationsCentreBuilder.inspect(level, origin);
        MagiDeepLabBuilder.MagiAudit magi =
                MagiDeepLabBuilder.inspect(level, origin);
        TerminalDogmaBuilder.TerminalDogmaAudit terminalDogma =
                TerminalDogmaBuilder.inspect(level, origin);
        int vanillaLavaSamples = countVanillaLavaSamples(level, origin);
        boolean valid = floor && skySphere && lake && naturalLake
                && pyramid && legacyInnerPyramidGone && lifts == 3
                && cavernLighting && gantries == 3
                && bridge && observation && operations.valid() && magi.valid()
                && terminalDogma.valid() && vanillaLavaSamples == 0;
        return new GeoFrontAudit(valid, floor, skySphere, lake, naturalLake,
                pyramid, legacyInnerPyramidGone, realSky, cavernLighting,
                lifts, gantries, bridge, observation, operations,
                magi, terminalDogma, vanillaLavaSamples);
    }

    /**
     * Samples the full inhabited volume instead of scanning seventy million
     * interior blocks. A fresh dimension generates air below the surface, so
     * any vanilla lava at these distributed points proves stale/contaminated
     * chunks and rejects the map before a player is sent underground.
     */
    public static int countVanillaLavaSamples(ServerLevel level, BlockPos origin)
    {
        BlockPos centre = cavernCentre(origin);
        int[] horizontal = {-192, -128, -64, 0, 64, 128, 192};
        int[] vertical = {-224, -160, -104, -64, 0, 64, 128, 192};
        int safeRadius = CAVERN_RADIUS - 20;
        int safeRadiusSqr = safeRadius * safeRadius;
        int lava = 0;
        for (int x : horizontal)
        {
            for (int y : vertical)
            {
                for (int z : horizontal)
                {
                    if (x * x + y * y + z * z > safeRadiusSqr)
                    {
                        continue;
                    }
                    if (level.getFluidState(centre.offset(x, y, z))
                            .is(FluidTags.LAVA))
                    {
                        lava++;
                    }
                }
            }
        }
        return lava;
    }

    private static void buildCavernFloor(ServerLevel level, BlockPos origin)
    {
        BlockPos centre = cavernCentre(origin);
        int floorDeltaY = origin.getY() - centre.getY();
        int floorRadius = (int) Math.floor(Math.sqrt(
                CAVERN_RADIUS * CAVERN_RADIUS - floorDeltaY * floorDeltaY)) - 8;
        int radiusSqr = floorRadius * floorRadius;
        for (int x = -floorRadius; x <= floorRadius; x++)
        {
            for (int z = -floorRadius; z <= floorRadius; z++)
            {
                int distanceSqr = x * x + z * z;
                if (distanceSqr > radiusSqr)
                {
                    continue;
                }
                int distance = (int) Math.sqrt(distanceSqr);
                int terrainY = distance <= 170 ? 0
                        : Math.floorMod(x * 31 + z * 17, 5) - 2;
                BlockPos column = new BlockPos(
                        centre.getX() + x, origin.getY(), centre.getZ() + z);
                for (int y = -5; y <= terrainY - 3; y++)
                {
                    set(level, column.offset(0, y, 0),
                            Blocks.STONE.defaultBlockState());
                }
                set(level, column.offset(0, terrainY - 2, 0),
                        Blocks.DIRT.defaultBlockState());
                set(level, column.offset(0, terrainY - 1, 0),
                        Blocks.DIRT.defaultBlockState());
                set(level, column.offset(0, terrainY, 0),
                        distance >= floorRadius - 3
                                ? Blocks.STONE.defaultBlockState()
                                : Blocks.GRASS_BLOCK.defaultBlockState());
            }
        }
    }

    private static void buildSkyweaveSphere(ServerLevel level, BlockPos origin)
    {
        BlockPos centre = cavernCentre(origin);
        BlockState sky = skyweaveState();
        int radiusSqr = CAVERN_RADIUS * CAVERN_RADIUS;
        for (int y = -CAVERN_RADIUS; y <= CAVERN_RADIUS; y++)
        {
            int horizontalRadius = (int) Math.round(Math.sqrt(
                    Math.max(0, radiusSqr - y * y)));
            int poleStep = Math.min(CAVERN_RADIUS, Math.abs(y) + 1);
            int nextRadius = (int) Math.round(Math.sqrt(
                    Math.max(0, radiusSqr - poleStep * poleStep)));
            int innerRadius = Math.max(0, nextRadius - 1);
            for (int radius = innerRadius; radius <= horizontalRadius; radius++)
            {
                int samples = Math.max(8, (int) Math.ceil(
                        Math.PI * 2.0D * Math.max(1, radius) * 1.25D));
                for (int sample = 0; sample < samples; sample++)
                {
                    double angle = Math.PI * 2.0D * sample / samples;
                    int x = (int) Math.round(Math.cos(angle) * radius);
                    int z = (int) Math.round(Math.sin(angle) * radius);
                    set(level, centre.offset(x, y, z), sky);
                }
            }
        }
        // Exact cardinal blocks are both visual seams and deterministic audit
        // markers; the annular raster above may otherwise choose an adjacent
        // rounded voxel at a pole.
        set(level, centre.offset(CAVERN_RADIUS, 0, 0), sky);
        set(level, centre.offset(-CAVERN_RADIUS, 0, 0), sky);
        set(level, centre.offset(0, CAVERN_RADIUS, 0), sky);
        set(level, centre.offset(64, 248, 0), sky);
        set(level, centre.offset(0, -CAVERN_RADIUS, 0), sky);
        set(level, centre.offset(0, 0, CAVERN_RADIUS), sky);
        set(level, centre.offset(0, 0, -CAVERN_RADIUS), sky);
    }

    public static BlockPos cavernCentre(BlockPos origin)
    {
        return origin.offset(0, CAVERN_CENTRE_Y, CAVERN_CENTRE_Z);
    }

    public static boolean skyweaveAvailable()
    {
        return BuiltInRegistries.BLOCK.containsKey(SKYWEAVE_ID);
    }

    private static BlockState skyweaveState()
    {
        if (skyweaveAvailable())
        {
            return BuiltInRegistries.BLOCK.get(SKYWEAVE_ID).defaultBlockState();
        }
        if (!warnedMissingSkyweave)
        {
            warnedMissingSkyweave = true;
            ProjectSeele.LOGGER.warn(
                    "Ars Nouveau Skyweave is unavailable; GeoFront sphere uses blue glass fallback");
        }
        return Blocks.LIGHT_BLUE_STAINED_GLASS.defaultBlockState();
    }

    private static void clearLegacyArtificialSun(ServerLevel level,
                                                  BlockPos origin)
    {
        for (int x = -11; x <= 11; x++)
        {
            for (int z = -11; z <= 11; z++)
            {
                for (int y = 79; y <= 92; y++)
                {
                    BlockPos position = origin.offset(x, y, z);
                    BlockState state = level.getBlockState(position);
                    if (state.is(Blocks.SEA_LANTERN)
                            || state.is(Blocks.YELLOW_STAINED_GLASS)
                            || state.is(Blocks.LIGHT))
                    {
                        set(level, position, Blocks.AIR.defaultBlockState());
                    }
                }
            }
        }
    }

    private static void buildLclLake(ServerLevel level, BlockPos origin)
    {
        int outer = 72;
        int inner = 40;
        for (int x = -outer; x <= outer; x++)
        {
            for (int z = -outer; z <= outer; z++)
            {
                int distanceSqr = x * x + z * z;
                if (distanceSqr > outer * outer || distanceSqr < inner * inner)
                {
                    continue;
                }
                BlockState bed = Math.floorMod(x * 17 + z * 31, 37) == 0
                        ? Blocks.SEA_LANTERN.defaultBlockState()
                        : Blocks.ORANGE_CONCRETE.defaultBlockState();
                set(level, origin.offset(x, -4, z), bed);
                for (int y = -3; y <= 1; y++)
                {
                    set(level, origin.offset(x, y, z),
                            ModFluids.LCL_SOURCE.get().defaultFluidState()
                                    .createLegacyBlock());
                }
            }
        }
    }

    /** A separate freshwater lake makes the Skyweave interior a real biome. */
    private static void buildNaturalLake(ServerLevel level, BlockPos origin)
    {
        BlockPos centre = origin.offset(-125, 0, -125);
        final int radiusX = 52;
        final int radiusZ = 34;
        for (int x = -58; x <= 58; x++)
        {
            for (int z = -40; z <= 40; z++)
            {
                double distance = square(x / (double) radiusX)
                        + square(z / (double) radiusZ);
                if (distance <= 1.0D)
                {
                    BlockState bed = Math.floorMod(x * 19 + z * 23, 13) == 0
                            ? Blocks.CLAY.defaultBlockState()
                            : Blocks.SAND.defaultBlockState();
                    set(level, centre.offset(x, -5, z), bed);
                    for (int y = -4; y <= 0; y++)
                    {
                        set(level, centre.offset(x, y, z),
                                Fluids.WATER.defaultFluidState().createLegacyBlock());
                    }
                    for (int y = 1; y <= 4; y++)
                    {
                        set(level, centre.offset(x, y, z),
                                Blocks.AIR.defaultBlockState());
                    }
                }
                else if (distance <= 1.24D)
                {
                    set(level, centre.offset(x, 0, z),
                            Math.floorMod(x + z, 5) == 0
                                    ? Blocks.GRAVEL.defaultBlockState()
                                    : Blocks.SAND.defaultBlockState());
                }
            }
        }
    }

    private static void buildNervPyramid(ServerLevel level, BlockPos origin)
    {
        boolean preserveCommandAsset =
                LocalMapAssetLoader.commandMarkersPresent(level, origin);
        clearBentEnvelopePyramid(level, origin, preserveCommandAsset);
        clearPreviousEnvelopePyramid(level, origin, preserveCommandAsset);
        clearLegacyNervPyramid(level, origin, preserveCommandAsset);

        fillPyramidRectangle(level, origin, PYRAMID_BASE_Y,
                PYRAMID_BASE_CENTRE_Z, PYRAMID_BASE_HALF_X,
                PYRAMID_BASE_HALF_Z,
                Blocks.POLISHED_DEEPSLATE.defaultBlockState(),
                preserveCommandAsset);

        for (int y = PYRAMID_BASE_Y + 1; y <= PYRAMID_APEX_Y; y++)
        {
            int halfX = pyramidHalfXAt(y);
            int halfZ = pyramidHalfZAt(y);
            int centreZ = pyramidCentreZAt(y);
            int nextHalfX = y == PYRAMID_APEX_Y ? 0 : pyramidHalfXAt(y + 1);
            int nextHalfZ = y == PYRAMID_APEX_Y ? 0 : pyramidHalfZAt(y + 1);
            int nextCentreZ = y == PYRAMID_APEX_Y
                    ? centreZ : pyramidCentreZAt(y + 1);
            rectangularPyramidShellLayer(level, origin, y,
                    centreZ, halfX, halfZ, nextCentreZ,
                    nextHalfX, nextHalfZ,
                    pyramidShellState(y), preserveCommandAsset);

            // Continuous dark corner ribs and orange cardinal ribs make the
            // huge envelope read as one NERV pyramid from cavern distance.
            BlockState corner = Blocks.BLACK_CONCRETE.defaultBlockState();
            BlockState accent = Blocks.ORANGE_CONCRETE.defaultBlockState();
            pyramidSet(level, origin, -halfX, y,
                    centreZ - halfZ, corner, preserveCommandAsset);
            pyramidSet(level, origin, halfX, y,
                    centreZ - halfZ, corner, preserveCommandAsset);
            pyramidSet(level, origin, -halfX, y,
                    centreZ + halfZ, corner, preserveCommandAsset);
            pyramidSet(level, origin, halfX, y,
                    centreZ + halfZ, corner, preserveCommandAsset);
            pyramidSet(level, origin, 0, y,
                    centreZ - halfZ, accent, preserveCommandAsset);
            pyramidSet(level, origin, 0, y,
                    centreZ + halfZ, accent, preserveCommandAsset);
            pyramidSet(level, origin, -halfX, y,
                    centreZ, accent, preserveCommandAsset);
            pyramidSet(level, origin, halfX, y,
                    centreZ, accent, preserveCommandAsset);
        }

        // Version-specific structural markers keep old, undersized shells from
        // passing the audit merely because a command-module marker exists.
        set(level, origin.offset(-PYRAMID_BASE_HALF_X, PYRAMID_BASE_Y,
                        PYRAMID_BASE_CENTRE_Z - PYRAMID_BASE_HALF_Z),
                Blocks.CHISELED_DEEPSLATE.defaultBlockState());
        set(level, origin.offset(pyramidHalfXAt(PYRAMID_AUDIT_Y),
                        PYRAMID_AUDIT_Y,
                        PYRAMID_CENTRE_Z + pyramidHalfZAt(PYRAMID_AUDIT_Y)),
                Blocks.CRYING_OBSIDIAN.defaultBlockState());
        set(level, origin.offset(0, PYRAMID_APEX_Y, PYRAMID_CENTRE_Z),
                Blocks.REDSTONE_BLOCK.defaultBlockState());
        set(level, origin.offset(0, PYRAMID_APEX_Y + 1, PYRAMID_CENTRE_Z),
                Blocks.BEACON.defaultBlockState());
        set(level, origin.offset(0, PYRAMID_APEX_Y + 2, PYRAMID_CENTRE_Z),
                Blocks.RED_STAINED_GLASS.defaultBlockState());
        buildPyramidApron(level, origin, preserveCommandAsset);
    }

    /**
     * Replaces the accidental grass carpet around NERV with a restrained
     * service apron. Existing LCL and the private command-module interior are
     * never overwritten.
     */
    private static void buildPyramidApron(ServerLevel level, BlockPos origin,
                                          boolean preserveCommandAsset)
    {
        int margin = 10;
        for (int x = -PYRAMID_BASE_HALF_X - margin;
             x <= PYRAMID_BASE_HALF_X + margin; x++)
        {
            for (int z = PYRAMID_BASE_CENTRE_Z - PYRAMID_BASE_HALF_Z - margin;
                 z <= PYRAMID_BASE_CENTRE_Z + PYRAMID_BASE_HALF_Z + margin; z++)
            {
                if (preserveCommandAsset
                        && LocalMapAssetLoader.commandEnvelopeContains(x, 0, z))
                {
                    continue;
                }
                BlockPos position = origin.offset(x, 0, z);
                if (!level.getFluidState(position).isEmpty()
                        || !level.getFluidState(position.above()).isEmpty())
                {
                    continue;
                }
                BlockState state = level.getBlockState(position);
                if (!state.is(Blocks.GRASS_BLOCK) && !state.is(Blocks.DIRT)
                        && !state.is(Blocks.MOSS_BLOCK) && !state.is(Blocks.STONE)
                        && !state.is(Blocks.GRAVEL) && !state.is(Blocks.SAND))
                {
                    continue;
                }
                BlockState apron = Math.floorMod(x + z, 11) == 0
                        ? Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState()
                        : Blocks.POLISHED_DEEPSLATE.defaultBlockState();
                set(level, position, apron);
            }
        }
    }

    /**
     * Removes the v15 two-stage, drifting envelope. Its shoulder kink and
     * moving centre made the lower half read wider and unrelated to the top.
     */
    private static void clearBentEnvelopePyramid(ServerLevel level,
                                                 BlockPos origin,
                                                 boolean preserveCommandAsset)
    {
        BlockPos baseMarker = origin.offset(-70, -22, -100);
        BlockPos shoulderMarker = origin.offset(46, 57, 93);
        if (!level.getBlockState(baseMarker).is(Blocks.CHISELED_DEEPSLATE)
                || !level.getBlockState(shoulderMarker)
                .is(Blocks.CRYING_OBSIDIAN))
        {
            return;
        }
        for (int x = -70; x <= 70; x++)
        {
            for (int z = -100; z <= 100; z++)
            {
                clearLegacyPyramidBlock(level, origin, x, -22, z,
                        preserveCommandAsset);
            }
        }
        for (int y = -21; y <= 84; y++)
        {
            int halfX = y <= 57
                    ? steppedLerp(70, 46, y + 22, 79)
                    : steppedLerp(46, 5, y - 57, 27);
            int halfZ = y <= 57
                    ? steppedLerp(100, 62, y + 22, 79)
                    : steppedLerp(62, 5, y - 57, 27);
            int centreZ = y <= 57
                    ? steppedLerp(0, 31, y + 22, 79) : 31;
            int nextHalfX = y == 84 ? 0 : (y + 1 <= 57
                    ? steppedLerp(70, 46, y + 23, 79)
                    : steppedLerp(46, 5, y + 1 - 57, 27));
            int nextHalfZ = y == 84 ? 0 : (y + 1 <= 57
                    ? steppedLerp(100, 62, y + 23, 79)
                    : steppedLerp(62, 5, y + 1 - 57, 27));
            int nextCentreZ = y == 84 ? centreZ : (y + 1 <= 57
                    ? steppedLerp(0, 31, y + 23, 79) : 31);
            int minZ = centreZ - halfZ;
            int maxZ = centreZ + halfZ;
            int nextMinZ = nextCentreZ - nextHalfZ;
            int nextMaxZ = nextCentreZ + nextHalfZ;
            for (int x = -halfX; x <= halfX; x++)
            {
                for (int z = minZ; z <= maxZ; z++)
                {
                    if (Math.abs(x) >= nextHalfX
                            || z <= nextMinZ || z >= nextMaxZ)
                    {
                        clearLegacyPyramidBlock(level, origin, x, y, z,
                                preserveCommandAsset);
                    }
                }
            }
        }
        clearLegacyPyramidBlock(level, origin, 0, 85, 31,
                preserveCommandAsset);
        clearLegacyPyramidBlock(level, origin, 0, 86, 31,
                preserveCommandAsset);
    }

    /** Removes the rejected v10 near-vertical envelope without touching its NBT interior. */
    private static void clearPreviousEnvelopePyramid(ServerLevel level,
                                                      BlockPos origin,
                                                      boolean preserveCommandAsset)
    {
        BlockPos previousMarker = origin.offset(34, 57, 99);
        BlockPos previousBaseMarker = origin.offset(-46, -22, -43);
        if (!level.getBlockState(previousMarker).is(Blocks.CRYING_OBSIDIAN)
                || !level.getBlockState(previousBaseMarker)
                .is(Blocks.CHISELED_DEEPSLATE))
        {
            return;
        }
        for (int x = -46; x <= 46; x++)
        {
            for (int z = -74; z <= 74; z++)
            {
                clearLegacyPyramidBlock(level, origin, x, -22, 31 + z,
                        preserveCommandAsset);
            }
        }
        for (int y = -21; y <= 84; y++)
        {
            int halfX = y <= 57
                    ? steppedLerp(46, 34, y + 22, 79)
                    : steppedLerp(34, 2, y - 57, 27);
            int halfZ = y <= 57
                    ? steppedLerp(74, 68, y + 22, 79)
                    : steppedLerp(68, 2, y - 57, 27);
            int nextHalfX = y == 84 ? 0 : (y + 1 <= 57
                    ? steppedLerp(46, 34, y + 23, 79)
                    : steppedLerp(34, 2, y + 1 - 57, 27));
            int nextHalfZ = y == 84 ? 0 : (y + 1 <= 57
                    ? steppedLerp(74, 68, y + 23, 79)
                    : steppedLerp(68, 2, y + 1 - 57, 27));
            for (int x = -halfX; x <= halfX; x++)
            {
                for (int z = -halfZ; z <= halfZ; z++)
                {
                    if (Math.abs(x) >= nextHalfX || Math.abs(z) >= nextHalfZ)
                    {
                        clearLegacyPyramidBlock(level, origin, x, y, 31 + z,
                                preserveCommandAsset);
                    }
                }
            }
        }
        clearLegacyPyramidBlock(level, origin, 0, 85, 31,
                preserveCommandAsset);
        clearLegacyPyramidBlock(level, origin, 0, 86, 31,
                preserveCommandAsset);
    }

    private static void clearLegacyNervPyramid(ServerLevel level,
                                                BlockPos origin,
                                                boolean preserveCommandAsset)
    {
        for (int x = -35; x <= 35; x++)
        {
            for (int z = -35; z <= 35; z++)
            {
                clearLegacyPyramidBlock(level, origin, x, 1, z,
                        preserveCommandAsset);
            }
        }
        for (int y = 2; y <= 28; y++)
        {
            int half = Math.max(4, 36 - y);
            for (int i = -half; i <= half; i++)
            {
                clearLegacyPyramidBlock(level, origin, -half, y, i,
                        preserveCommandAsset);
                clearLegacyPyramidBlock(level, origin, half, y, i,
                        preserveCommandAsset);
                clearLegacyPyramidBlock(level, origin, i, y, -half,
                        preserveCommandAsset);
                clearLegacyPyramidBlock(level, origin, i, y, half,
                        preserveCommandAsset);
            }
            if (y % 7 == 0)
            {
                for (int x = -half + 1; x < half; x++)
                {
                    for (int z = -half + 1; z < half; z++)
                    {
                        clearLegacyPyramidBlock(level, origin, x, y, z,
                                preserveCommandAsset);
                    }
                }
            }
        }
        for (int depth = 1; depth <= 20; depth++)
        {
            int y = -2 - depth;
            int half = Math.max(1, 22 - depth);
            for (int i = -half; i <= half; i++)
            {
                clearLegacyPyramidBlock(level, origin, -half, y, i,
                        preserveCommandAsset);
                clearLegacyPyramidBlock(level, origin, half, y, i,
                        preserveCommandAsset);
                clearLegacyPyramidBlock(level, origin, i, y, -half,
                        preserveCommandAsset);
                clearLegacyPyramidBlock(level, origin, i, y, half,
                        preserveCommandAsset);
            }
        }
        for (int y = 28; y <= 30; y++)
        {
            clearLegacyPyramidBlock(level, origin, 0, y, 0,
                    preserveCommandAsset);
        }
    }

    private static void clearLegacyPyramidBlock(ServerLevel level,
                                                 BlockPos origin,
                                                 int x, int y, int z,
                                                 boolean preserveCommandAsset)
    {
        if (preserveCommandAsset
                && (LocalMapAssetLoader.commandEnvelopeContains(x, y, z)
                    || LocalMapAssetLoader.isCommandMarkerOffset(x, y, z)))
        {
            return;
        }
        set(level, origin.offset(x, y, z), Blocks.AIR.defaultBlockState());
    }

    private static int pyramidHalfXAt(int y)
    {
        return steppedLerp(PYRAMID_BASE_HALF_X, PYRAMID_APEX_HALF,
                y - PYRAMID_BASE_Y,
                PYRAMID_APEX_Y - PYRAMID_BASE_Y);
    }

    private static int pyramidCentreZAt(int y)
    {
        return PYRAMID_CENTRE_Z;
    }

    /** Keeps later landscape passes outside the complete command-pyramid island. */
    public static boolean isWithinPyramidFootprint(int relativeX,
                                                   int relativeZ,
                                                   int margin)
    {
        return Math.abs(relativeX) <= PYRAMID_BASE_HALF_X + margin
                && relativeZ >= PYRAMID_BASE_CENTRE_Z
                        - PYRAMID_BASE_HALF_Z - margin
                && relativeZ <= PYRAMID_BASE_CENTRE_Z
                        + PYRAMID_BASE_HALF_Z + margin;
    }

    private static int pyramidHalfZAt(int y)
    {
        return steppedLerp(PYRAMID_BASE_HALF_Z, PYRAMID_APEX_HALF,
                y - PYRAMID_BASE_Y,
                PYRAMID_APEX_Y - PYRAMID_BASE_Y);
    }

    private static int steppedLerp(int start, int end,
                                   int numerator, int denominator)
    {
        float progress = Math.max(0.0F, Math.min(1.0F,
                numerator / (float) denominator));
        return Math.round(start + (end - start) * progress);
    }

    private static BlockState pyramidShellState(int y)
    {
        int band = Math.floorMod(y - PYRAMID_BASE_Y, 14);
        if (band <= 1)
        {
            return Blocks.ORANGE_CONCRETE.defaultBlockState();
        }
        if (y > 72 && band <= 4)
        {
            return Blocks.SMOOTH_QUARTZ.defaultBlockState();
        }
        return band % 4 <= 1 ? Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState()
                : Blocks.GRAY_CONCRETE.defaultBlockState();
    }

    private static void fillPyramidRectangle(ServerLevel level,
                                              BlockPos origin, int y,
                                              int centreZ, int halfX, int halfZ,
                                              BlockState state,
                                              boolean preserveCommandAsset)
    {
        for (int x = -halfX; x <= halfX; x++)
        {
            for (int z = -halfZ; z <= halfZ; z++)
            {
                pyramidSet(level, origin, x, y, centreZ + z,
                        state, preserveCommandAsset);
            }
        }
    }

    private static void rectangularPyramidShellLayer(ServerLevel level,
                                                      BlockPos origin, int y,
                                                      int centreZ,
                                                      int halfX, int halfZ,
                                                      int nextCentreZ,
                                                      int nextHalfX,
                                                      int nextHalfZ,
                                                      BlockState state,
                                                      boolean preserveCommandAsset)
    {
        int minZ = centreZ - halfZ;
        int maxZ = centreZ + halfZ;
        int nextMinZ = nextCentreZ - nextHalfZ;
        int nextMaxZ = nextCentreZ + nextHalfZ;
        for (int x = -halfX; x <= halfX; x++)
        {
            for (int z = minZ; z <= maxZ; z++)
            {
                if (Math.abs(x) >= nextHalfX
                        || z <= nextMinZ || z >= nextMaxZ)
                {
                    pyramidSet(level, origin, x, y, z, state,
                            preserveCommandAsset);
                }
            }
        }
    }

    private static void pyramidSet(ServerLevel level, BlockPos origin,
                                   int x, int y, int z, BlockState state,
                                   boolean preserveCommandAsset)
    {
        if (preserveCommandAsset
                && LocalMapAssetLoader.isCommandMarkerOffset(x, y, z))
        {
            return;
        }
        set(level, origin.offset(x, y, z), state);
    }

    private static void buildEvaLiftTerminals(ServerLevel level, BlockPos origin)
    {
        for (int x : LIFT_X)
        {
            BlockPos centre = origin.offset(x, 0, -76);
            clearLiftCorridor(level, centre);
            BlockState accent = x < 0 ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                    : x > 0 ? Blocks.RED_CONCRETE.defaultBlockState()
                    : Blocks.PURPLE_CONCRETE.defaultBlockState();
            fillSquare(level, centre, 0, 7,
                    Blocks.POLISHED_DEEPSLATE.defaultBlockState());
            set(level, centre.above(), Blocks.LODESTONE.defaultBlockState());
            for (int y = 1; y <= 20; y++)
            {
                set(level, centre.offset(-7, y, 0), Blocks.IRON_BLOCK.defaultBlockState());
                set(level, centre.offset(7, y, 0), Blocks.IRON_BLOCK.defaultBlockState());
            }
            for (int span = -7; span <= 7; span++)
            {
                set(level, centre.offset(span, 20, 0), span % 4 == 0
                        ? Blocks.REDSTONE_LAMP.defaultBlockState()
                        : Blocks.BLACK_CONCRETE.defaultBlockState());
            }
            for (int z = -75; z <= -36; z++)
            {
                for (int width = -3; width <= 3; width++)
                {
                    set(level, origin.offset(x + width, 1, z),
                            width == 0 && Math.floorMod(z, 6) < 3
                                    ? Blocks.YELLOW_CONCRETE.defaultBlockState()
                                    : Blocks.GRAY_CONCRETE.defaultBlockState());
                }
            }
            buildLiftGantry(level, centre, accent);
        }
    }

    /** Removes only carrier residue inside the three audited 11x11 lift paths. */
    private static void clearLiftCorridor(ServerLevel level, BlockPos centre)
    {
        for (int y = 2; y <= 32; y++)
        {
            for (int x = -5; x <= 5; x++)
            {
                for (int z = -5; z <= 5; z++)
                {
                    set(level, centre.offset(x, y, z), Blocks.AIR.defaultBlockState());
                }
            }
        }
    }

    /** Reachable rear service deck aligned with the real EVA entry-plug socket. */
    private static void buildLiftGantry(ServerLevel level, BlockPos centre,
                                         BlockState accent)
    {
        BlockState frame = Blocks.IRON_BLOCK.defaultBlockState();
        BlockState dark = Blocks.BLACK_CONCRETE.defaultBlockState();
        BlockState light = Blocks.SEA_LANTERN.defaultBlockState();
        BlockState ladder = Blocks.LADDER.defaultBlockState()
                .setValue(LadderBlock.FACING, Direction.NORTH);
        int gantryY = 27;

        for (int y = 2; y <= gantryY; y++)
        {
            set(level, centre.offset(0, y, 14), frame);
            set(level, centre.offset(0, y, 13), ladder);
            if (y % 4 == 0)
            {
                set(level, centre.offset(1, y, 14), light);
            }
        }
        for (int z = 6; z <= 14; z++)
        {
            for (int x = -3; x <= 3; x++)
            {
                BlockState deck = x == 0 && z == 13
                        ? ladder : (x == 0 && z % 3 == 0 ? accent : dark);
                set(level, centre.offset(x, gantryY, z), deck);
                if (Math.abs(x) == 3)
                {
                    set(level, centre.offset(x, gantryY + 1, z),
                            Blocks.IRON_BARS.defaultBlockState());
                    set(level, centre.offset(x, gantryY + 3, z), frame);
                }
            }
            set(level, centre.offset(0, gantryY + 4, z),
                    z % 3 == 0 ? light : frame);
        }
    }

    private static void buildCommandBridge(ServerLevel level, BlockPos origin)
    {
        int exteriorZ = PYRAMID_BASE_CENTRE_Z
                + PYRAMID_BASE_HALF_Z + 8;
        int pressureGateZ = PYRAMID_CENTRE_Z
                + pyramidHalfZAt(7) - 1;
        for (int z = 35; z <= exteriorZ; z++)
        {
            for (int x = -4; x <= 4; x++)
            {
                set(level, origin.offset(x, 2, z), x == 0 && z % 8 < 4
                        ? Blocks.SEA_LANTERN.defaultBlockState()
                        : Blocks.IRON_BLOCK.defaultBlockState());
                if (z >= pressureGateZ)
                {
                    for (int y = 3; y <= 7; y++)
                    {
                        set(level, origin.offset(x, y, z),
                                Blocks.AIR.defaultBlockState());
                    }
                }
            }
            set(level, origin.offset(-5, 3, z), Blocks.IRON_BARS.defaultBlockState());
            set(level, origin.offset(5, 3, z), Blocks.IRON_BARS.defaultBlockState());
        }
    }

    private static void removeArtificialSun(ServerLevel level, BlockPos origin)
    {
        clearLegacyArtificialSun(level, origin);
    }

    private static void buildForestRing(ServerLevel level, BlockPos origin)
    {
        BlockPos sphereCentre = cavernCentre(origin);
        for (int x = -205; x <= 205; x += 9)
        {
            for (int z = -205; z <= 205; z += 9)
            {
                int distanceSqr = x * x + z * z;
                int localX = sphereCentre.getX() + x - origin.getX();
                int localZ = sphereCentre.getZ() + z - origin.getZ();
                boolean naturalLake = square((localX + 125) / 58.0D)
                        + square((localZ + 125) / 40.0D) <= 1.25D;
                if (distanceSqr < 92 * 92 || distanceSqr > 205 * 205
                        || Math.floorMod(x * 13 + z * 19, 7) > 1
                        || naturalLake
                        || isWithinPyramidFootprint(localX, localZ, 16)
                        || Math.abs(localZ + 76) <= 12)
                {
                    continue;
                }
                BlockPos ground = findGrassSurface(level,
                        new BlockPos(sphereCentre.getX() + x,
                                origin.getY(), sphereCentre.getZ() + z));
                if (ground == null)
                {
                    continue;
                }
                int height = 4 + Math.floorMod(x * 7 + z * 11, 4);
                for (int y = 1; y <= height; y++)
                {
                    set(level, ground.offset(0, y, 0),
                            Blocks.DARK_OAK_LOG.defaultBlockState());
                }
                for (int dx = -2; dx <= 2; dx++)
                {
                    for (int dz = -2; dz <= 2; dz++)
                    {
                        if (Math.abs(dx) + Math.abs(dz) <= 3)
                        {
                            set(level, ground.offset(dx, height + 1, dz),
                                    Blocks.DARK_OAK_LEAVES.defaultBlockState());
                        }
                    }
                }
            }
        }
    }

    private static BlockPos findGrassSurface(ServerLevel level, BlockPos column)
    {
        for (int y = 4; y >= -4; y--)
        {
            BlockPos candidate = column.offset(0, y, 0);
            if (level.getBlockState(candidate).is(Blocks.GRASS_BLOCK))
            {
                return candidate;
            }
        }
        return null;
    }

    private static double square(double value)
    {
        return value * value;
    }

    /**
     * Lights the playable volume without a visible ceiling of lamps. The
     * dimension supplies broad reflected daylight; a tight ground plane keeps
     * paths mob-safe while a sparse 3-D lattice preserves local contrast.
     */
    public static void repairCavernLighting(ServerLevel level, BlockPos origin)
    {
        int floorDeltaY = origin.getY() - cavernCentre(origin).getY();
        int floorRadius = (int) Math.floor(Math.sqrt(
                CAVERN_RADIUS * CAVERN_RADIUS - floorDeltaY * floorDeltaY)) - 14;
        int floorRadiusSqr = floorRadius * floorRadius;

        for (int x = -floorRadius; x <= floorRadius; x += 20)
        {
            for (int z = -floorRadius; z <= floorRadius; z += 20)
            {
                if (x * x + z * z > floorRadiusSqr
                        || lightingExclusion(x, 0, z))
                {
                    continue;
                }
                BlockPos floor = origin.offset(x, 0, CAVERN_CENTRE_Z + z);
                BlockState state = level.getBlockState(floor);
                if (state.is(Blocks.GRASS_BLOCK) || state.is(Blocks.STONE)
                        || state.is(Blocks.DIRT) || state.is(Blocks.SAND)
                        || state.is(Blocks.GRAVEL) || state.is(Blocks.MOSS_BLOCK))
                {
                    set(level, floor, Blocks.SEA_LANTERN.defaultBlockState());
                }
            }
        }

        // A fourteen-block plane gives every walkable gap real block light;
        // ambient dimension light alone would look bright but still permit
        // zero-light hostile spawns.
        for (int x = -floorRadius; x <= floorRadius; x += 14)
        {
            for (int z = -floorRadius; z <= floorRadius; z += 14)
            {
                if (x * x + z * z > floorRadiusSqr
                        || lightingExclusion(x, 4, z))
                {
                    continue;
                }
                BlockPos position = origin.offset(x, 4, CAVERN_CENTRE_Z + z);
                if (level.getBlockState(position).isAir())
                {
                    set(level, position, Blocks.LIGHT.defaultBlockState());
                }
            }
        }

        for (int relativeY = 32; relativeY <= CAVERN_TOP_Y - 28;
             relativeY += 32)
        {
            int sphereY = relativeY - CAVERN_CENTRE_Y;
            int horizontalRadius = (int) Math.floor(Math.sqrt(Math.max(0,
                    CAVERN_RADIUS * CAVERN_RADIUS - sphereY * sphereY))) - 18;
            int horizontalRadiusSqr = horizontalRadius * horizontalRadius;
            for (int x = -horizontalRadius; x <= horizontalRadius; x += 32)
            {
                for (int z = -horizontalRadius; z <= horizontalRadius; z += 32)
                {
                    if (x * x + z * z > horizontalRadiusSqr
                            || lightingExclusion(x, relativeY, z))
                    {
                        continue;
                    }
                    BlockPos position = origin.offset(x, relativeY,
                            CAVERN_CENTRE_Z + z);
                    if (level.getBlockState(position).isAir())
                    {
                        set(level, position, Blocks.LIGHT.defaultBlockState());
                    }
                }
            }
        }

        // Stable audit lights remain well outside every facility footprint.
        set(level, origin.offset(200, 0, CAVERN_CENTRE_Z),
                Blocks.SEA_LANTERN.defaultBlockState());
        set(level, origin.offset(216, 24, CAVERN_CENTRE_Z),
                Blocks.LIGHT.defaultBlockState());
    }

    private static boolean lightingExclusion(int x, int y, int centredZ)
    {
        int relativeZ = CAVERN_CENTRE_Z + centredZ;
        if (y <= PYRAMID_APEX_Y + 16
                && isWithinPyramidFootprint(x, relativeZ, 18))
        {
            return true;
        }
        for (int liftX : LIFT_X)
        {
            if (Math.abs(x - liftX) <= 12
                    && Math.abs(relativeZ - CAVERN_CENTRE_Z) <= 22)
            {
                return true;
            }
        }
        return false;
    }

    private static void buildObservationDeck(ServerLevel level, BlockPos origin)
    {
        BlockPos centre = origin.offset(0, 0, OBSERVATION_Z);
        for (int y = 1; y <= OBSERVATION_Y; y++)
        {
            for (int x : new int[] {-5, 5})
            {
                for (int z : new int[] {-5, 5})
                {
                    set(level, centre.offset(x, y, z), Blocks.IRON_BLOCK.defaultBlockState());
                }
            }
        }
        fillSquare(level, centre, OBSERVATION_Y, 8,
                Blocks.SMOOTH_STONE.defaultBlockState());
        for (int i = -8; i <= 8; i++)
        {
            set(level, centre.offset(-8, OBSERVATION_Y + 1, i),
                    Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(8, OBSERVATION_Y + 1, i),
                    Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(i, OBSERVATION_Y + 1, -8),
                    Blocks.IRON_BARS.defaultBlockState());
            set(level, centre.offset(i, OBSERVATION_Y + 1, 8),
                    Blocks.IRON_BARS.defaultBlockState());
        }
        set(level, centre.offset(0, OBSERVATION_Y, 0),
                Blocks.LODESTONE.defaultBlockState());
    }

    private static boolean isCavernStone(BlockState state)
    {
        return state.is(Blocks.DEEPSLATE) || state.is(Blocks.CALCITE)
                || state.is(Blocks.POLISHED_BASALT);
    }

    private static void squarePerimeter(ServerLevel level, BlockPos centre,
                                        int y, int half, BlockState state)
    {
        for (int i = -half; i <= half; i++)
        {
            set(level, centre.offset(-half, y, i), state);
            set(level, centre.offset(half, y, i), state);
            set(level, centre.offset(i, y, -half), state);
            set(level, centre.offset(i, y, half), state);
        }
    }

    private static void fillSquare(ServerLevel level, BlockPos centre, int y,
                                   int half, BlockState state)
    {
        for (int x = -half; x <= half; x++)
        {
            for (int z = -half; z <= half; z++)
            {
                set(level, centre.offset(x, y, z), state);
            }
        }
    }

    private static void set(ServerLevel level, BlockPos position, BlockState state)
    {
        if (!level.getBlockState(position).equals(state))
        {
            level.setBlock(position, state, UPDATE_CLIENTS);
        }
    }

    public record GeoFrontAudit(boolean valid, boolean floor, boolean skySphere,
                                boolean lake, boolean naturalLake,
                                boolean pyramid, boolean legacyInnerPyramidGone,
                                boolean realSky, boolean cavernLighting,
                                int lifts, int gantries, boolean bridge,
                                boolean observation,
                                NervOperationsCentreBuilder.OperationsAudit operations,
                                MagiDeepLabBuilder.MagiAudit magi,
                                TerminalDogmaBuilder.TerminalDogmaAudit terminalDogma,
                                int vanillaLavaSamples)
    {
        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s floor=%s skySphere=%s lclLake=%s naturalLake=%s "
                            + "nervPyramid=%s legacyInnerGone=%s realSky=%s lighting=%s "
                            + "lifts=%d/3 gantries=%d/3 "
                            + "commandBridge=%s observation=%s operations={%s} "
                            + "magi={%s} terminalDogma={%s} vanillaLavaSamples=%d/0",
                    this.valid, this.floor, this.skySphere, this.lake,
                    this.naturalLake, this.pyramid,
                    this.legacyInnerPyramidGone, this.realSky, this.cavernLighting,
                    this.lifts, this.gantries, this.bridge,
                    this.observation, this.operations.summary(), this.magi.summary(),
                    this.terminalDogma.summary(), this.vanillaLavaSamples);
        }
    }
}
