package com.projectseele.world;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;

import com.projectseele.ProjectSeele;
import com.projectseele.registry.ModBlocks;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LadderBlock;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Builds Tokyo-3 and GeoFront as two vertically separated parts of one map.
 * The three EVA shafts are real continuous block volumes; no portal or
 * dimension boundary exists between their lower and upper stations.
 */
public final class IntegratedNervMapBuilder
{
    public static final int MAP_VERSION = 17;
    /**
     * The 640-block Skyweave sphere is buried below a normal Tokyo-3 surface.
     * The lower NERV floor stays south of the city centre so the three launch
     * terminals remain in the same physical X/Z columns as their surface beds.
     */
    public static final BlockPos GEOFRONT_ORIGIN = new BlockPos(30, -444, 296);
    public static final BlockPos TOKYO3_ORIGIN = new BlockPos(30, 80, 220);
    public static final int[] LIFT_X = {-28, 0, 28};
    public static final int SHAFT_OUTER_RADIUS = 7;
    public static final int SHAFT_CLEAR_RADIUS = 5;
    public static final int SURFACE_HEADROOM = 40;

    private static final int LOWER_TERMINAL_Z = -76;
    private static final int LOWER_BED_ABOVE_ORIGIN = 1;
    private static final int SURFACE_BED_BELOW_ORIGIN = 1;
    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;
    private static final List<LiftLink> LIFT_LINKS = createLiftLinks();

    private IntegratedNervMapBuilder() {}

    /** Builds the city first, GeoFront second, then cuts the shafts last. */
    public static IntegratedAudit build(ServerLevel level)
    {
        requireBuildHeight(level);
        boolean stagedEvaWorld = LocalMapAssetLoader.stagedEvaWorld(level);
        ProjectSeele.LOGGER.info(
                "Local EVA map detection: stagedWorld={} role=native-surface localSkyscraper={}",
                stagedEvaWorld,
                LocalMapAssetLoader.skyscraperAvailable());

        int storedRetractionDepth =
                Tokyo3RetractionDirector.depth(level, TOKYO3_ORIGIN);
        ThirdTokyoSurfaceBuilder.buildDistrict(level, TOKYO3_ORIGIN);
        for (int depth = 1; depth <= storedRetractionDepth; depth++)
        {
            ThirdTokyoSurfaceBuilder.applyRetractionDepth(level, TOKYO3_ORIGIN,
                    depth - 1, depth);
        }
        Tokyo3LandscapeBuilder.build(level, TOKYO3_ORIGIN);
        Tokyo3RetractionDirector.register(level, TOKYO3_ORIGIN);
        int skyscrapers = LocalMapAssetLoader.placeTokyo3Skyscrapers(
                level, TOKYO3_ORIGIN, storedRetractionDepth);
        if (stagedEvaWorld || skyscrapers > 0)
        {
            LocalMapAssetLoader.markImportedTokyo3(level, TOKYO3_ORIGIN);
        }
        ProjectSeele.LOGGER.info(
                "Tokyo-3 surface built at {} with {}/3 private skyscrapers; "
                        + "local world staged={} and native buried GeoFront topology active",
                TOKYO3_ORIGIN, skyscrapers, stagedEvaWorld);

        GeoFrontBuilder.build(level, GEOFRONT_ORIGIN, false);
        GeoFrontLandscapeBuilder.build(level, GEOFRONT_ORIGIN);
        GeoFrontBuilder.repairCavernLighting(level, GEOFRONT_ORIGIN);
        for (LiftLink link : LIFT_LINKS)
        {
            buildContinuousShaft(level, link);
            buildSurfaceHead(level, link);
        }
        ensurePowerPylons(level);
        ensureArmamentRacks(level);
        buildControlMarkers(level);
        return inspect(level);
    }

    /** Rebuilds only when the complete physical-map audit fails. */
    public static IntegratedAudit ensure(ServerLevel level)
    {
        ensureLowerBayWindows(level);
        ensurePowerPylons(level);
        ensureArmamentRacks(level);

        if (isInstalled(level))
        {
            // Text displays and button labels can enter the entity manager a
            // few ticks after their chunks. Repair those bounded runtime
            // layers before judging the immutable 640-block map, otherwise
            // every login needlessly rewrites Tokyo-3 and the complete sphere.
            NervOperationsCentreBuilder.repairRuntimeAccess(
                    level, GEOFRONT_ORIGIN);
            MagiDeepLabBuilder.repairRuntimeLabels(level, GEOFRONT_ORIGIN);
            TerminalDogmaBuilder.repairRuntimeSpecimen(
                    level, GEOFRONT_ORIGIN);
            Tokyo3RetractionDirector.register(level, TOKYO3_ORIGIN);
        }
        IntegratedAudit audit = inspect(level);
        if (audit.valid())
        {
            ProjectSeele.LOGGER.info(
                    "Integrated NERV map reused without full rebuild");
            return audit;
        }
        ProjectSeele.LOGGER.warn(
                "Integrated NERV map incremental audit failed; rebuilding: {}",
                audit.summary());
        return build(level);
    }

    /**
     * Repairs and checks only the structures which can inhibit a live sortie.
     * The explicit setup/audit commands retain the complete map inspection;
     * command-room buttons must not synchronously load every remote city,
     * forest and cavern landmark before they can release an EVA.
     */
    public static RuntimeAudit prepareRuntime(ServerLevel level)
    {
        long startedAt = System.nanoTime();
        boolean installed = isInstalled(level);
        if (!installed)
        {
            return new RuntimeAudit(false, false, false, false,
                    0, 0, 0, 0, false, false, 0,
                    elapsedMilliseconds(startedAt));
        }

        ensurePowerPylons(level);
        ensureArmamentRacks(level);
        boolean lowerBayWindows = lowerBayWindowsPresent(level);
        if (!lowerBayWindows)
        {
            ensureLowerBayWindows(level);
            lowerBayWindows = lowerBayWindowsPresent(level);
        }
        NervOperationsCentreBuilder.OperationsAudit operations =
                NervOperationsCentreBuilder.repairRuntimeAccess(
                        level, GEOFRONT_ORIGIN);
        MagiDeepLabBuilder.MagiAudit magi =
                MagiDeepLabBuilder.repairRuntimeLabels(level, GEOFRONT_ORIGIN);
        TerminalDogmaBuilder.repairRuntimeSpecimen(level, GEOFRONT_ORIGIN);
        boolean magiStructure = magi.physicalAccess() && magi.shaft()
                && magi.roomShell() && magi.pribnowBox()
                && magi.cores() == 3 && magi.controls() == 3;
        Tokyo3RetractionDirector.register(level, TOKYO3_ORIGIN);

        int lowerBeds = 0;
        int surfaceBeds = 0;
        int continuousShafts = 0;
        int clearExits = 0;
        for (LiftLink link : LIFT_LINKS)
        {
            if (level.getBlockState(link.lowerBed()).is(Blocks.LODESTONE))
            {
                lowerBeds++;
            }
            if (level.getBlockState(link.surfaceBed()).is(Blocks.LODESTONE))
            {
                surfaceBeds++;
            }
            if (shaftIsContinuous(level, link))
            {
                continuousShafts++;
            }
            if (surfaceExitIsClear(level, link))
            {
                clearExits++;
            }
        }
        boolean controlMarkers = controlMarkersPresent(level);
        boolean valid = controlMarkers && lowerBayWindows
                && powerPylonsPresent(level)
                && armamentRacksPresent(level)
                && lowerBeds == LIFT_LINKS.size()
                && surfaceBeds == LIFT_LINKS.size()
                && continuousShafts == LIFT_LINKS.size()
                && clearExits == LIFT_LINKS.size()
                && operations.valid() && magiStructure;
        RuntimeAudit audit = new RuntimeAudit(valid, true, controlMarkers,
                lowerBayWindows, lowerBeds, surfaceBeds, continuousShafts,
                clearExits, operations.valid(), magiStructure, magi.labels(),
                elapsedMilliseconds(startedAt));
        ProjectSeele.LOGGER.info("Integrated NERV runtime gate: {}",
                audit.summary());
        return audit;
    }

    public static IntegratedAudit inspect(ServerLevel level)
    {
        GeoFrontBuilder.GeoFrontAudit geoFront =
                GeoFrontBuilder.inspect(level, GEOFRONT_ORIGIN);
        int storedRetractionDepth =
                Tokyo3RetractionDirector.depth(level, TOKYO3_ORIGIN);
        ThirdTokyoSurfaceBuilder.DistrictAudit tokyo3 =
                ThirdTokyoSurfaceBuilder.inspect(level, TOKYO3_ORIGIN,
                        storedRetractionDepth);
        Tokyo3LandscapeBuilder.LandscapeAudit tokyo3Landscape =
                Tokyo3LandscapeBuilder.inspect(level, TOKYO3_ORIGIN);
        GeoFrontLandscapeBuilder.LandscapeAudit geoFrontLandscape =
                GeoFrontLandscapeBuilder.inspect(level, GEOFRONT_ORIGIN);
        int lowerBeds = 0;
        int surfaceBeds = 0;
        int continuousShafts = 0;
        int clearExits = 0;
        for (LiftLink link : LIFT_LINKS)
        {
            if (level.getBlockState(link.lowerBed()).is(Blocks.LODESTONE))
            {
                lowerBeds++;
            }
            if (level.getBlockState(link.surfaceBed()).is(Blocks.LODESTONE))
            {
                surfaceBeds++;
            }
            if (shaftIsContinuous(level, link))
            {
                continuousShafts++;
            }
            if (surfaceExitIsClear(level, link))
            {
                clearExits++;
            }
        }
        boolean controlMarkers = controlMarkersPresent(level);
        boolean powerPylons = powerPylonsPresent(level);
        int sphereTop = GEOFRONT_ORIGIN.getY()
                + GeoFrontBuilder.CAVERN_TOP_Y;
        int rockCover = TOKYO3_ORIGIN.getY() - sphereTop;
        int sphereBottom = GEOFRONT_ORIGIN.getY()
                + GeoFrontBuilder.CAVERN_BOTTOM_Y;
        int bedrockClearance = sphereBottom - level.getMinBuildHeight();
        boolean deeplyBuried = rockCover >= 80 && bedrockClearance >= 16;
        boolean valid = geoFront.valid() && geoFrontLandscape.valid()
                && tokyo3.valid() && tokyo3Landscape.valid() && controlMarkers
                && powerPylons && armamentRacksPresent(level)
                && deeplyBuried
                && lowerBeds == LIFT_LINKS.size()
                && surfaceBeds == LIFT_LINKS.size()
                && continuousShafts == LIFT_LINKS.size()
                && clearExits == LIFT_LINKS.size();
        return new IntegratedAudit(valid, geoFront, geoFrontLandscape, tokyo3,
                tokyo3Landscape, deeplyBuried, rockCover, bedrockClearance,
                controlMarkers, lowerBeds, surfaceBeds, continuousShafts,
                clearExits);
    }

    /**
     * Cheap persistent readiness check for navigation commands. It loads only
     * the two marker chunks and cannot trigger a map rebuild.
     */
    public static boolean isInstalled(ServerLevel level)
    {
        level.getChunkAt(lowerControlMarker());
        level.getChunkAt(surfaceControlMarker());
        return controlMarkersPresent(level);
    }

    public static BlockPos geoFrontOrigin()
    {
        return GEOFRONT_ORIGIN;
    }

    public static BlockPos tokyo3Origin()
    {
        return TOKYO3_ORIGIN;
    }

    public static List<LiftLink> liftLinks()
    {
        return LIFT_LINKS;
    }

    public static LiftLink lift(int index)
    {
        if (index < 0 || index >= LIFT_LINKS.size())
        {
            throw new IllegalArgumentException("EVA lift index must be 0, 1 or 2");
        }
        return LIFT_LINKS.get(index);
    }

    /** Unit variants 00/01/02 use lift indices 0/1/2 respectively. */
    public static LiftLink liftForUnitVariant(int unitVariant)
    {
        return lift(unitVariant);
    }

    /** Resolves a real station only while its lodestone marker is present. */
    public static Optional<LiftLink> readLiftMarker(ServerLevel level, BlockPos marker)
    {
        if (!level.getBlockState(marker).is(Blocks.LODESTONE))
        {
            return Optional.empty();
        }
        return findLift(marker);
    }

    public static Optional<LiftLink> findLift(BlockPos stationBed)
    {
        return LIFT_LINKS.stream()
                .filter(link -> link.lowerBed().equals(stationBed)
                        || link.surfaceBed().equals(stationBed))
                .findFirst();
    }

    public static boolean isLowerStation(BlockPos stationBed)
    {
        return LIFT_LINKS.stream().anyMatch(link -> link.lowerBed().equals(stationBed));
    }

    public static boolean isSurfaceStation(BlockPos stationBed)
    {
        return LIFT_LINKS.stream().anyMatch(link -> link.surfaceBed().equals(stationBed));
    }

    public static int ascentDistance()
    {
        return lift(0).ascentBlocks();
    }

    public static BlockPos lowerLiftBed(int index)
    {
        return lift(index).lowerBed();
    }

    public static BlockPos surfaceLiftBed(int index)
    {
        return lift(index).surfaceBed();
    }

    public static BlockPos lowerControlMarker()
    {
        return GEOFRONT_ORIGIN.offset(0, 1, -104);
    }

    public static BlockPos surfaceControlMarker()
    {
        return TOKYO3_ORIGIN.offset(0, -2, 16);
    }

    private static List<LiftLink> createLiftLinks()
    {
        List<LiftLink> links = new ArrayList<>(LIFT_X.length);
        for (int index = 0; index < LIFT_X.length; index++)
        {
            int relativeX = LIFT_X[index];
            int worldX = TOKYO3_ORIGIN.getX() + relativeX;
            int worldZ = TOKYO3_ORIGIN.getZ();
            BlockPos lowerBed = GEOFRONT_ORIGIN.offset(relativeX,
                    LOWER_BED_ABOVE_ORIGIN, LOWER_TERMINAL_Z);
            BlockPos surfaceBed = TOKYO3_ORIGIN.offset(relativeX,
                    -SURFACE_BED_BELOW_ORIGIN, 0);
            if (lowerBed.getX() != surfaceBed.getX()
                    || lowerBed.getZ() != surfaceBed.getZ()
                    || lowerBed.getX() != worldX
                    || lowerBed.getZ() != worldZ)
            {
                throw new IllegalStateException(
                        "GeoFront and Tokyo-3 lift stations must share one physical X/Z column");
            }
            links.add(new LiftLink(index, worldX, worldZ,
                    lowerBed, surfaceBed));
        }
        return List.copyOf(links);
    }

    private static void buildContinuousShaft(ServerLevel level, LiftLink link)
    {
        BlockState accent = accent(link.index());
        int bottomY = link.lowerBed().getY() + 1;
        int topY = link.surfaceBed().getY();
        for (int y = bottomY; y <= topY; y++)
        {
            int relativeY = y - bottomY;
            for (int x = -SHAFT_OUTER_RADIUS; x <= SHAFT_OUTER_RADIUS; x++)
            {
                for (int z = -SHAFT_OUTER_RADIUS; z <= SHAFT_OUTER_RADIUS; z++)
                {
                    BlockPos position = new BlockPos(
                            link.x() + x, y, link.z() + z);
                    int edge = Math.max(Math.abs(x), Math.abs(z));
                    if (edge <= SHAFT_CLEAR_RADIUS)
                    {
                        clear(level, position);
                    }
                    else if (edge == SHAFT_OUTER_RADIUS)
                    {
                        boolean lowerObservationWindow = relativeY <= 27
                                && z == SHAFT_OUTER_RADIUS
                                && Math.abs(x) <= SHAFT_CLEAR_RADIUS;
                        set(level, position, lowerObservationWindow
                                ? Blocks.GRAY_STAINED_GLASS.defaultBlockState()
                                : shaftWall(relativeY, x, z, accent));
                    }
                    else
                    {
                        clear(level, position);
                    }
                }
            }

            // Four continuous guide rails remain outside the audited 11x11 path.
            for (int x : new int[] {-6, 6})
            {
                for (int z : new int[] {-6, 6})
                {
                    set(level, new BlockPos(
                                    link.x() + x, y, link.z() + z),
                            Blocks.POLISHED_BASALT.defaultBlockState());
                }
            }
            set(level, new BlockPos(link.x(), y, link.z() + 6),
                    Blocks.LADDER.defaultBlockState()
                            .setValue(LadderBlock.FACING, Direction.NORTH));
        }

        // Preserve the GeoFront dorsal access opening cut by the lower gantry.
        int accessDeckY = GEOFRONT_ORIGIN.getY() + 27;
        for (int x = -2; x <= 2; x++)
        {
            for (int y = accessDeckY + 1; y <= accessDeckY + 3; y++)
            {
                clear(level, new BlockPos(link.x() + x, y, link.z() + 7));
            }
        }

        // A single physical carrier marker closes the upper station at Y=363.
        set(level, link.surfaceBed(), Blocks.LODESTONE.defaultBlockState());
        for (int y = TOKYO3_ORIGIN.getY();
             y <= TOKYO3_ORIGIN.getY() + SURFACE_HEADROOM; y++)
        {
            for (int x = -SHAFT_CLEAR_RADIUS; x <= SHAFT_CLEAR_RADIUS; x++)
            {
                for (int z = -SHAFT_CLEAR_RADIUS; z <= SHAFT_CLEAR_RADIUS; z++)
                {
                    clear(level, new BlockPos(
                            link.x() + x, y, link.z() + z));
                }
            }
        }
    }

    private static BlockState shaftWall(int relativeY, int x, int z,
                                        BlockState accent)
    {
        if (relativeY % 32 == 0)
        {
            return accent;
        }
        if (relativeY % 8 == 0 && (x == 0 || z == 0))
        {
            return Blocks.SEA_LANTERN.defaultBlockState();
        }
        if (Math.abs(x) == SHAFT_OUTER_RADIUS
                && Math.abs(z) == SHAFT_OUTER_RADIUS)
        {
            return Blocks.IRON_BLOCK.defaultBlockState();
        }
        return Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
    }

    private static void buildSurfaceHead(ServerLevel level, LiftLink link)
    {
        BlockState accent = accent(link.index());
        int groundY = TOKYO3_ORIGIN.getY();
        // Earlier prototypes surrounded every sortie with four pylons and an
        // overhead frame. Tokyo-3 should release an EVA directly onto an open
        // battle street, so rebuilds actively clear that obsolete enclosure.
        for (int x = -9; x <= 9; x++)
        {
            for (int z = -9; z <= 9; z++)
            {
                for (int y = 1; y <= 13; y++)
                {
                    clear(level, new BlockPos(
                            link.x() + x, groundY + y, link.z() + z));
                }
            }
        }
        for (int x = -9; x <= 9; x++)
        {
            for (int z = -9; z <= 9; z++)
            {
                int edge = Math.max(Math.abs(x), Math.abs(z));
                BlockPos position = new BlockPos(
                        link.x() + x, groundY, link.z() + z);
                if (edge <= SHAFT_CLEAR_RADIUS)
                {
                    clear(level, position);
                }
                else if (edge <= 7)
                {
                    set(level, position, Math.floorMod(x + z, 4) < 2
                            ? accent : Blocks.BLACK_CONCRETE.defaultBlockState());
                }
                else if (edge == 8)
                {
                    set(level, position, Blocks.IRON_BLOCK.defaultBlockState());
                }
                else
                {
                    set(level, position, Blocks.SMOOTH_STONE.defaultBlockState());
                }
            }
        }
    }

    public static BlockPos lowerPowerPylon(int index)
    {
        return lift(index).lowerBed().offset(10, 1, 0);
    }

    public static BlockPos surfacePowerPylon(int index)
    {
        return lift(index).surfaceBed().offset(11, 2, 0);
    }

    public static BlockPos lowerArmamentRack(int index)
    {
        return lift(index).lowerBed().offset(-10, 1, 0);
    }

    private static void ensureArmamentRacks(ServerLevel level)
    {
        for (int index = 0; index < LIFT_LINKS.size(); index++)
        {
            BlockPos position = lowerArmamentRack(index);
            boolean newlyPlaced = !level.getBlockState(position)
                    .is(ModBlocks.EVA_ARMAMENT_RACK.get());
            if (newlyPlaced)
            {
                set(level, position,
                        ModBlocks.EVA_ARMAMENT_RACK.get().defaultBlockState());
            }
            if (!(level.getBlockEntity(position)
                    instanceof EvaArmamentRackBlockEntity rack))
            {
                level.removeBlock(position, false);
                set(level, position,
                        ModBlocks.EVA_ARMAMENT_RACK.get().defaultBlockState());
                newlyPlaced = true;
            }
            if (newlyPlaced && level.getBlockEntity(position)
                    instanceof EvaArmamentRackBlockEntity rack)
            {
                rack.stockStandardLoadout();
            }
        }
    }

    private static boolean armamentRacksPresent(ServerLevel level)
    {
        for (int index = 0; index < LIFT_LINKS.size(); index++)
        {
            BlockPos position = lowerArmamentRack(index);
            if (!level.getBlockState(position).is(ModBlocks.EVA_ARMAMENT_RACK.get())
                    || !(level.getBlockEntity(position)
                    instanceof EvaArmamentRackBlockEntity))
            {
                return false;
            }
        }
        return true;
    }

    private static void ensurePowerPylons(ServerLevel level)
    {
        for (int index = 0; index < LIFT_LINKS.size(); index++)
        {
            set(level, lowerPowerPylon(index),
                    ModBlocks.UMBILICAL_PYLON.get().defaultBlockState());
            set(level, surfacePowerPylon(index),
                    ModBlocks.UMBILICAL_PYLON.get().defaultBlockState());
        }
    }

    private static boolean powerPylonsPresent(ServerLevel level)
    {
        for (int index = 0; index < LIFT_LINKS.size(); index++)
        {
            if (!level.getBlockState(lowerPowerPylon(index))
                    .is(ModBlocks.UMBILICAL_PYLON.get())
                    || !level.getBlockState(surfacePowerPylon(index))
                    .is(ModBlocks.UMBILICAL_PYLON.get()))
            {
                return false;
            }
        }
        return true;
    }

    private static void buildControlMarkers(ServerLevel level)
    {
        BlockPos lower = lowerControlMarker();
        set(level, lower, Blocks.CHISELED_DEEPSLATE.defaultBlockState());
        set(level, lower.east(), Blocks.ORANGE_CONCRETE.defaultBlockState());
        set(level, lower.west(), Blocks.BLACK_CONCRETE.defaultBlockState());
        BlockPos surface = surfaceControlMarker();
        set(level, surface, Blocks.CHISELED_QUARTZ_BLOCK.defaultBlockState());
        set(level, surface.east(), Blocks.ORANGE_CONCRETE.defaultBlockState());
        set(level, surface.west(), Blocks.BLACK_CONCRETE.defaultBlockState());
    }

    private static boolean controlMarkersPresent(ServerLevel level)
    {
        BlockPos lower = lowerControlMarker();
        BlockPos surface = surfaceControlMarker();
        return level.getBlockState(lower).is(Blocks.CHISELED_DEEPSLATE)
                && level.getBlockState(lower.east()).is(Blocks.ORANGE_CONCRETE)
                && level.getBlockState(lower.west()).is(Blocks.BLACK_CONCRETE)
                && level.getBlockState(surface).is(Blocks.CHISELED_QUARTZ_BLOCK)
                && level.getBlockState(surface.east()).is(Blocks.ORANGE_CONCRETE)
                && level.getBlockState(surface.west()).is(Blocks.BLACK_CONCRETE);
    }

    private static boolean shaftIsContinuous(ServerLevel level, LiftLink link)
    {
        int bottom = link.lowerBed().getY() + 2;
        int top = link.surfaceBed().getY() - 2;
        for (int y = bottom; y <= top; y++)
        {
            if (!shaftLayerIsClear(level, link, y))
            {
                return false;
            }
        }
        return true;
    }

    private static boolean shaftLayerIsClear(ServerLevel level,
                                             LiftLink link, int y)
    {
        for (int x = -SHAFT_CLEAR_RADIUS; x <= SHAFT_CLEAR_RADIUS; x++)
        {
            for (int z = -SHAFT_CLEAR_RADIUS; z <= SHAFT_CLEAR_RADIUS; z++)
            {
                if (!level.getBlockState(new BlockPos(
                        link.x() + x, y, link.z() + z)).isAir())
                {
                    return false;
                }
            }
        }
        boolean northWall = isShaftWall(level.getBlockState(
                        new BlockPos(link.x(), y,
                                link.z() + SHAFT_OUTER_RADIUS)));
        int accessDeckY = GEOFRONT_ORIGIN.getY() + 27;
        boolean auditedGantryDoor = y >= accessDeckY + 1
                && y <= accessDeckY + 3
                && level.getBlockState(new BlockPos(
                        link.x(), y, link.z() + SHAFT_OUTER_RADIUS)).isAir();
        return isShaftWall(level.getBlockState(
                        new BlockPos(link.x() - SHAFT_OUTER_RADIUS,
                                y, link.z())))
                && isShaftWall(level.getBlockState(
                        new BlockPos(link.x() + SHAFT_OUTER_RADIUS,
                                y, link.z())))
                && isShaftWall(level.getBlockState(
                        new BlockPos(link.x(), y,
                                link.z() - SHAFT_OUTER_RADIUS)))
                && (northWall || auditedGantryDoor);
    }

    private static boolean surfaceExitIsClear(ServerLevel level, LiftLink link)
    {
        for (int y = TOKYO3_ORIGIN.getY();
             y <= TOKYO3_ORIGIN.getY() + SURFACE_HEADROOM; y++)
        {
            for (int x = -SHAFT_CLEAR_RADIUS; x <= SHAFT_CLEAR_RADIUS; x++)
            {
                for (int z = -SHAFT_CLEAR_RADIUS; z <= SHAFT_CLEAR_RADIUS; z++)
                {
                    if (!level.getBlockState(new BlockPos(
                            link.x() + x, y, link.z() + z)).isAir())
                    {
                        return false;
                    }
                }
            }
        }
        return true;
    }

    private static boolean isShaftWall(BlockState state)
    {
        return state.is(Blocks.REINFORCED_DEEPSLATE)
                || state.is(Blocks.IRON_BLOCK)
                || state.is(Blocks.SEA_LANTERN)
                || state.is(Blocks.GRAY_STAINED_GLASS)
                || state.is(Blocks.ORANGE_CONCRETE)
                || state.is(Blocks.PURPLE_CONCRETE)
                || state.is(Blocks.RED_CONCRETE);
    }

    private static boolean lowerBayWindowsPresent(ServerLevel level)
    {
        for (LiftLink link : LIFT_LINKS)
        {
            int wallZ = link.z() + SHAFT_OUTER_RADIUS;
            int bottom = link.lowerBed().getY() + 2;
            int accessDeckY = GEOFRONT_ORIGIN.getY() + 27;
            for (int y : new int[] {bottom, (bottom + accessDeckY) / 2,
                    accessDeckY - 1})
            {
                for (int x : new int[] {-SHAFT_CLEAR_RADIUS,
                        SHAFT_CLEAR_RADIUS})
                {
                    if (!level.getBlockState(new BlockPos(
                            link.x() + x, y, wallZ))
                            .is(Blocks.GRAY_STAINED_GLASS))
                    {
                        return false;
                    }
                }
            }
        }
        return true;
    }

    private static long elapsedMilliseconds(long startedAt)
    {
        return (System.nanoTime() - startedAt) / 1_000_000L;
    }

    /** Backfills the lower-bay glazing without rebuilding the imported map. */
    private static void ensureLowerBayWindows(ServerLevel level)
    {
        for (LiftLink link : LIFT_LINKS)
        {
            int wallZ = link.z() + SHAFT_OUTER_RADIUS;
            int bottom = link.lowerBed().getY() + 2;
            int top = bottom + 27;
            for (int y = bottom; y <= top; y++)
            {
                for (int x = -SHAFT_CLEAR_RADIUS;
                     x <= SHAFT_CLEAR_RADIUS; x++)
                {
                    int accessDeckY = GEOFRONT_ORIGIN.getY() + 27;
                    if (y >= accessDeckY + 1 && y <= accessDeckY + 3
                            && Math.abs(x) <= 2)
                    {
                        clear(level, new BlockPos(link.x() + x, y, wallZ));
                        continue;
                    }
                    set(level, new BlockPos(link.x() + x, y, wallZ),
                            Blocks.GRAY_STAINED_GLASS.defaultBlockState());
                }
            }
        }
    }

    private static BlockState accent(int index)
    {
        return switch (index)
        {
            case 0 -> Blocks.ORANGE_CONCRETE.defaultBlockState();
            case 2 -> Blocks.RED_CONCRETE.defaultBlockState();
            default -> Blocks.PURPLE_CONCRETE.defaultBlockState();
        };
    }

    private static void requireBuildHeight(ServerLevel level)
    {
        int requiredMin = GEOFRONT_ORIGIN.getY()
                + TerminalDogmaBuilder.FACILITY_Y_OFFSET
                + TerminalDogmaBuilder.MIN_RELATIVE_Y;
        int requiredMax = TOKYO3_ORIGIN.getY()
                + Math.max(SURFACE_HEADROOM, 44);
        if (requiredMin < level.getMinBuildHeight()
                || requiredMax >= level.getMaxBuildHeight())
        {
            throw new IllegalStateException(String.format(Locale.ROOT,
                    "Integrated NERV map requires Y=%d..%d but dimension provides %d..%d",
                    requiredMin, requiredMax, level.getMinBuildHeight(),
                    level.getMaxBuildHeight() - 1));
        }
    }

    private static void clear(ServerLevel level, BlockPos position)
    {
        if (!level.getBlockState(position).isAir())
        {
            set(level, position, Blocks.AIR.defaultBlockState());
        }
    }

    private static void set(ServerLevel level, BlockPos position, BlockState state)
    {
        if (!level.getBlockState(position).equals(state))
        {
            level.setBlock(position, state, UPDATE_CLIENTS);
        }
    }

    public record LiftLink(int index, int x, int z, BlockPos lowerBed,
                           BlockPos surfaceBed)
    {
        public int ascentBlocks()
        {
            return this.surfaceBed.getY() - this.lowerBed.getY();
        }

        public BlockPos surfaceExit()
        {
            return this.surfaceBed.above();
        }
    }

    public record RuntimeAudit(boolean valid, boolean installed,
                               boolean controlMarkers,
                               boolean lowerBayWindows, int lowerBeds,
                               int surfaceBeds, int continuousShafts,
                               int clearExits, boolean operations,
                               boolean magi, int magiLabels,
                               long elapsedMilliseconds)
    {
        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s installed=%s controlMarkers=%s windows=%s "
                            + "lowerBeds=%d/3 surfaceBeds=%d/3 "
                            + "continuousShafts=%d/3 clearExits=%d/3 "
                            + "operations=%s magi=%s magiLabels=%d/3 "
                            + "elapsed=%dms",
                    this.valid, this.installed, this.controlMarkers,
                    this.lowerBayWindows, this.lowerBeds, this.surfaceBeds,
                    this.continuousShafts, this.clearExits, this.operations,
                    this.magi, this.magiLabels, this.elapsedMilliseconds);
        }
    }

    public record IntegratedAudit(boolean valid,
                                  GeoFrontBuilder.GeoFrontAudit geoFront,
                                  GeoFrontLandscapeBuilder.LandscapeAudit geoFrontLandscape,
                                   ThirdTokyoSurfaceBuilder.DistrictAudit tokyo3,
                                   Tokyo3LandscapeBuilder.LandscapeAudit tokyo3Landscape,
                                   boolean deeplyBuried, int rockCover,
                                   int bedrockClearance,
                                   boolean controlMarkers, int lowerBeds,
                                  int surfaceBeds, int continuousShafts,
                                  int clearExits)
    {
        public String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s mapVersion=%d deeplyBuried=%s rockCover=%d "
                            + "bedrockClearance=%d controlMarkers=%s lowerBeds=%d/3 "
                            + "surfaceBeds=%d/3 continuousShafts=%d/3 clearExits=%d/3 "
                            + "geoFront={%s} geoFrontLandscape={%s} tokyo3={%s} "
                            + "tokyo3Landscape={%s}",
                    this.valid, MAP_VERSION, this.deeplyBuried, this.rockCover,
                    this.bedrockClearance, this.controlMarkers, this.lowerBeds,
                    this.surfaceBeds, this.continuousShafts, this.clearExits,
                    this.geoFront.summary(), this.geoFrontLandscape.summary(),
                    this.tokyo3.summary(), this.tokyo3Landscape.summary());
        }
    }
}
