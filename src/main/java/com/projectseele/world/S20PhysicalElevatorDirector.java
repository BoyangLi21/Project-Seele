package com.projectseele.world;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.NervCarrierPlatformEntity;
import com.projectseele.registry.ModEntities;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.AttachFace;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.AABB;

/**
 * Bounded S20 personnel elevator.
 *
 * <p>This class deliberately has no event-bus or command registration. The
 * S20 bootstrap owner must explicitly call {@link #install},
 * {@link #tick(ServerLevel, LiftSpec)} and
 * {@link #handleUse(ServerPlayer, BlockPos, LiftSpec)} after both route
 * anchors have been visually approved.</p>
 *
 * <p>The shaft, landing decks and interlocked landing doors remain physical
 * blocks. The cabin itself is one saved entity that is present before a call,
 * accelerates continuously, carries mounted riders and recovers from rest
 * after a reload. The pre-S20 per-tick block copier remains below only as a
 * save migration reader and is never entered after cabin revision 1.</p>
 */
public final class S20PhysicalElevatorDirector
{
    /*
     * R28 shipped with the block-cabin controller below.  The later entity
     * cabin conversion changed the working doors and in-car floor buttons and
     * left existing saves in permanent IN_TRANSIT/FAULT states.  Keep the
     * entity implementation readable for save recovery, but make the proven
     * block cabin authoritative again.  Escalators are a separate system.
     */
    private static final boolean USE_LEGACY_BLOCK_CABIN = true;
    public static final String COMMAND_REAR_LIFT_ID =
            "s20-command-rear-x12-z253-v4";
    public static final String OBSERVATION_HANGAR_LIFT_ID =
            "s20-observation-hangar-x94-z241-v2";
    public static final String SURFACE_TRANSIT_LIFT_ID =
            "s20-surface-transit-v2";
    private static final int CABIN_RADIUS = 2;
    private static final int CABIN_HEIGHT = 5;
    private static final int CABIN_DOOR_DISTANCE = CABIN_RADIUS;
    private static final int LANDING_DOOR_DISTANCE = 4;
    private static final int THRESHOLD_END = 6;
    private static final int ROUTE_HANDOFF_DISTANCE = 7;
    private static final int CABIN_DOOR_HALF_WIDTH = 1;
    private static final int LANDING_DOOR_HALF_WIDTH = 2;
    private static final int DOOR_HEIGHT = 3;
    private static final int CLOSE_TICKS = 12;
    private static final int OPEN_TICKS = 10;
    private static final int ENTITY_CABIN_REVISION = 2;
    private static final int ENTITY_MISSING_GRACE_TICKS = 100;
    /** One relative movement update every client interpolation frame. */
    private static final int MOVE_INTERVAL_TICKS = 1;
    private static final int UPDATE =
            Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE;

    private static final BlockState CABIN_FLOOR =
            Blocks.POLISHED_DEEPSLATE.defaultBlockState();
    private static final BlockState CABIN_WALL =
            Blocks.IRON_BLOCK.defaultBlockState();
    private static final BlockState CABIN_ROOF =
            Blocks.SMOOTH_QUARTZ.defaultBlockState();
    private static final BlockState CABIN_PANEL =
            Blocks.BLACK_CONCRETE.defaultBlockState();
    private static final BlockState CABIN_DOOR =
            Blocks.LIGHT_GRAY_STAINED_GLASS.defaultBlockState();
    private static final BlockState LANDING_FRAME =
            Blocks.REINFORCED_DEEPSLATE.defaultBlockState();
    private static final BlockState LANDING_ACCENT =
            Blocks.ORANGE_CONCRETE.defaultBlockState();
    private static final BlockState LANDING_LIGHT =
            Blocks.SEA_LANTERN.defaultBlockState();
    private static final BlockState LANDING_DOOR =
            Blocks.GRAY_STAINED_GLASS.defaultBlockState();
    private static final BlockState AIR = Blocks.AIR.defaultBlockState();

    private S20PhysicalElevatorDirector() {}

    /**
     * Short personnel lift behind the original command-room rear passage.
     *
     * <p>The upper landing uses the measured command-room threshold at
     * y=-423 and opens south into the supported authored route beginning at
     * z=258.  The previous y=-406 north-facing endpoint opened into air.</p>
     */
    public static LiftSpec commandRearLift()
    {
        return new LiftSpec(COMMAND_REAR_LIFT_ID,
                new Landing("B-40 LOWER INTERCHANGE",
                        new BlockPos(12, -448, 253), Direction.SOUTH),
                new Landing("B-20 COMMAND BRIDGE",
                        new BlockPos(12, -423, 253), Direction.SOUTH));
    }

    /** Physical link from the lowered launch observation hall to the hangar. */
    public static LiftSpec observationHangarLift()
    {
        return new LiftSpec(OBSERVATION_HANGAR_LIFT_ID,
                new Landing("B-40 LAUNCH OBSERVATION",
                        new BlockPos(94, -418, 241), Direction.WEST),
                new Landing("B-16 EVA HANGAR ACCESS",
                        new BlockPos(94, -394, 241), Direction.EAST));
    }

    /**
     * Measured old compact-cage lift axis retained by the human-approved map.
     *
     * <p>The lower stop serves the wet-cage logistics floor. The upper stop
     * serves its observation/command-access circulation. It is intentionally
     * exposed as a factory rather than installed automatically.</p>
     */
    public static LiftSpec oldCommandToCompactCageLift()
    {
        return new LiftSpec("s20-old-compact-cage",
                new Landing("B-40 EVA CAGES",
                        new BlockPos(108, -442, 192), Direction.SOUTH),
                new Landing("B-14 COMMAND ACCESS",
                        new BlockPos(108, -394, 192), Direction.NORTH));
    }

    /**
     * Permanent same-world public lift between the B-40 interchange and the
     * Tokyo-3 street pavilion. The shaft shell and both route handoffs are
     * compiled independently by {@link S20SurfaceTransitDirector}.
     */
    public static LiftSpec surfaceTransitLift()
    {
        return new LiftSpec(SURFACE_TRANSIT_LIFT_ID,
                new Landing("B-40 GEOFRONT TRANSIT",
                        new BlockPos(
                                S20SurfaceTransitDirector.AXIS_X,
                                S20SurfaceTransitDirector.LOWER_WALK_Y,
                                S20SurfaceTransitDirector.AXIS_Z),
                        Direction.WEST),
                new Landing("TOKYO-3 SURFACE",
                        new BlockPos(
                                S20SurfaceTransitDirector.AXIS_X,
                                S20SurfaceTransitDirector.UPPER_WALK_Y,
                                S20SurfaceTransitDirector.AXIS_Z),
                        Direction.WEST));
    }

    /**
     * The complete S20 personnel chain. Order is command room first, then the
     * retained compact-cage observation lift reached through B-40.
     */
    public static List<LiftSpec> s20Lifts()
    {
        return List.of(commandRearLift(),
                observationHangarLift(),
                oldCommandToCompactCageLift(),
                surfaceTransitLift());
    }

    /** Command lift whose fixed shaft/cabin voxels were approved in R10. */
    public static boolean isR10ApprovedLift(LiftSpec spec)
    {
        return spec.id().equals(COMMAND_REAR_LIFT_ID);
    }

    /** Corrected observation/hangar lift gated by its offline receipt. */
    public static boolean isR14ApprovedLift(LiftSpec spec)
    {
        return spec.id().equals(OBSERVATION_HANGAR_LIFT_ID);
    }

    /** Existing 523-block same-world surface shaft; never a map generator. */
    public static boolean isSurfaceTransitLift(LiftSpec spec)
    {
        return spec.id().equals(SURFACE_TRANSIT_LIFT_ID);
    }

    /** Retained compact-cage personnel lift already present in the authored map. */
    public static boolean isRetainedCompactCageLift(LiftSpec spec)
    {
        return spec.id().equals("s20-old-compact-cage");
    }

    /**
     * Read-only runtime evidence used by the spatial-freeze gate.  This never
     * installs geometry; it only permits an already persisted, non-faulted
     * authored lift to keep ticking and accepting its existing buttons.
     */
    public static boolean hasHealthyRuntime(
            ServerLevel level, LiftSpec spec)
    {
        LiftRuntime runtime = RuntimeData.get(level)
                .find(spec.id()).orElse(null);
        return runtime != null
                && runtime.fingerprint.equals(spec.fingerprint());
    }

    /**
     * Checks the complete five-by-five swept cabin volume and both route
     * handoffs without writing any block.
     */
    public static PreflightResult preflight(
            ServerLevel level, LiftSpec spec)
    {
        Objects.requireNonNull(level, "level");
        Objects.requireNonNull(spec, "spec");
        List<String> failures = new ArrayList<>();
        if (!FacilityWorldPolicy.isS20Rebuild(level.getServer()))
        {
            failures.add("not an authorised S20 rebuild");
            return new PreflightResult(false, List.copyOf(failures));
        }
        if (!level.hasChunkAt(spec.lower().cabinCentre())
                || !level.hasChunkAt(spec.upper().cabinCentre()))
        {
            failures.add("one or both landing chunks are not loaded");
            return new PreflightResult(false, List.copyOf(failures));
        }

        for (int y = spec.lower().walkY() - 1;
             y <= spec.upper().walkY() + CABIN_HEIGHT - 1; y++)
        {
            if (level.isOutsideBuildHeight(y))
            {
                failures.add("swept cabin leaves build height at y=" + y);
                break;
            }
            for (int dx = -CABIN_RADIUS; dx <= CABIN_RADIUS; dx++)
            {
                for (int dz = -CABIN_RADIUS; dz <= CABIN_RADIUS; dz++)
                {
                    BlockPos position = new BlockPos(
                            spec.lower().cabinCentre().getX() + dx, y,
                            spec.lower().cabinCentre().getZ() + dz);
                    BlockState state = level.getBlockState(position);
                    if (!state.isAir()
                            && !legacyEndpointStateAllowed(
                                    spec, position, state))
                    {
                        addFailure(failures,
                                "shaft obstruction at " + position
                                        + ": " + state);
                    }
                }
            }
        }
        inspectRouteHandoff(level, spec, spec.lower(), failures);
        inspectRouteHandoff(level, spec, spec.upper(), failures);
        return new PreflightResult(failures.isEmpty(),
                List.copyOf(failures));
    }

    /**
     * Installs one bounded cabin, two thresholds, doors and control panels.
     *
     * <p>Installation rejects any unknown block in the swept shaft. It never
     * clears a broad owner box and never constructs a shaft shell or support
     * pillar.</p>
     */
    public static boolean install(ServerLevel level, LiftSpec spec)
    {
        RuntimeData data = RuntimeData.get(level);
        Optional<LiftRuntime> existing = data.find(spec.id());
        if (existing.isPresent())
        {
            LiftRuntime runtime = existing.get();
            if (!runtime.fingerprint.equals(spec.fingerprint()))
            {
                ProjectSeele.LOGGER.error(
                        "S20 physical lift {} rejected: saved anchors {} "
                                + "do not match requested anchors {}",
                        spec.id(), runtime.fingerprint,
                        spec.fingerprint());
                return false;
            }
            if (USE_LEGACY_BLOCK_CABIN)
            {
                return ensureLegacyBlockCabin(level, spec, runtime, data);
            }
            return ensurePersistentCabin(level, spec, runtime, data)
                    != null;
        }

        LiftRuntime recovered = recoverExistingCabin(level, spec);
        if (recovered != null)
        {
            data.put(spec.id(), recovered);
            ProjectSeele.LOGGER.info(
                    "S20 physical lift recovered from world blocks: "
                            + "id={} currentY={} facing={}",
                    spec.id(), recovered.currentY,
                    recovered.cabinExit);
            return USE_LEGACY_BLOCK_CABIN
                    ? ensureLegacyBlockCabin(level, spec, recovered, data)
                    : ensurePersistentCabin(level, spec, recovered, data)
                    != null;
        }

        PreflightResult result = preflight(level, spec);
        if (!result.safe())
        {
            ProjectSeele.LOGGER.error(
                    "S20 physical lift {} preflight rejected: {}",
                    spec.id(), String.join(" | ", result.failures()));
            return false;
        }

        clearSweptCabinVolume(level, spec);
        buildLanding(level, spec.lower());
        buildLanding(level, spec.upper());
        LiftRuntime runtime = LiftRuntime.installed(spec);
        data.put(spec.id(), runtime);
        if (USE_LEGACY_BLOCK_CABIN)
        {
            return ensureLegacyBlockCabin(level, spec, runtime, data);
        }
        NervCarrierPlatformEntity cabin = ensurePersistentCabin(
                level, spec, runtime, data);
        if (cabin == null)
        {
            return false;
        }
        ProjectSeele.LOGGER.info(
                "S20 physical lift installed: id={} axis=({}, {}) "
                        + "walkY={}->{} lowerExit={} upperExit={} "
                        + "persistentCabin=true landingControls=4",
                spec.id(), spec.lower().cabinCentre().getX(),
                spec.lower().cabinCentre().getZ(),
                spec.lower().walkY(), spec.upper().walkY(),
                spec.lower().exit(), spec.upper().exit());
        return true;
    }

    /**
     * Re-authors the two landing interfaces after a fixed shaft-shell pass.
     * Shaft construction is intentionally allowed to run before this method;
     * otherwise its west wall can overwrite the door aperture and call panel.
     */
    public static void repairLandingHardware(ServerLevel level, LiftSpec spec)
    {
        buildLanding(level, spec.lower());
        buildLanding(level, spec.upper());
        LiftRuntime runtime = RuntimeData.get(level)
                .find(spec.id()).orElse(null);
        if (USE_LEGACY_BLOCK_CABIN)
        {
            if (runtime != null)
            {
                Landing current = spec.landingAt(runtime.currentY);
                setLandingDoor(level, spec.lower(),
                        current == spec.lower()
                                && runtime.mode == Mode.IDLE_OPEN);
                setLandingDoor(level, spec.upper(),
                        current == spec.upper()
                                && runtime.mode == Mode.IDLE_OPEN);
            }
            return;
        }
        NervCarrierPlatformEntity cabin = runtime == null ? null
                : resolvePersistentCabin(level, spec, runtime);
        if (cabin != null && cabin.isAtLiftY(spec.lower().walkY()))
        {
            buildLandingDeck(level, spec.lower());
            clearLandingDeck(level, spec.upper());
        }
        else if (cabin != null
                && cabin.isAtLiftY(spec.upper().walkY()))
        {
            clearLandingDeck(level, spec.lower());
            buildLandingDeck(level, spec.upper());
        }
        setLandingDoor(level, spec.lower(), cabin != null
                && cabin.canOpenLandingDoorAt(spec.lower().walkY()));
        setLandingDoor(level, spec.upper(), cabin != null
                && cabin.canOpenLandingDoorAt(spec.upper().walkY()));
    }

    private static LiftRuntime recoverExistingCabin(
            ServerLevel level, LiftSpec spec)
    {
        for (Landing landing : List.of(spec.lower(), spec.upper()))
        {
            BlockPos centre = landing.cabinCentre();
            if (!cabinFloorPresent(level, centre))
            {
                continue;
            }
            int roofMatches = 0;
            int wallMatches = 0;
            for (int dx = -CABIN_RADIUS; dx <= CABIN_RADIUS; dx++)
            {
                for (int dz = -CABIN_RADIUS; dz <= CABIN_RADIUS; dz++)
                {
                    if (level.getBlockState(centre.offset(
                            dx, CABIN_HEIGHT - 1, dz)).equals(CABIN_ROOF))
                    {
                        roofMatches++;
                    }
                    if (Math.abs(dx) != CABIN_RADIUS
                            && Math.abs(dz) != CABIN_RADIUS)
                    {
                        continue;
                    }
                    for (int dy = 0; dy < CABIN_HEIGHT - 1; dy++)
                    {
                        BlockState state = level.getBlockState(
                                centre.offset(dx, dy, dz));
                        if (state.equals(CABIN_WALL)
                                || state.equals(CABIN_DOOR))
                        {
                            wallMatches++;
                        }
                    }
                }
            }
            if (roofMatches == 25 && wallMatches >= 48)
            {
                return LiftRuntime.recovered(spec, landing);
            }
        }
        return null;
    }

    /**
     * Advances one installed lift. The caller should invoke this once per
     * server tick only after the S20 marker and both route owners are active.
     */
    public static void tick(ServerLevel level, LiftSpec spec)
    {
        if (!FacilityWorldPolicy.isS20Rebuild(level.getServer()))
        {
            return;
        }
        RuntimeData data = RuntimeData.get(level);
        LiftRuntime runtime = data.find(spec.id()).orElse(null);
        if (runtime == null)
        {
            return;
        }
        if (!runtime.fingerprint.equals(spec.fingerprint()))
        {
            fault(level, spec, runtime, data,
                    "runtime anchor fingerprint changed");
            return;
        }
        if (USE_LEGACY_BLOCK_CABIN)
        {
            if (!ensureLegacyBlockCabin(level, spec, runtime, data)
                    || runtime.mode == Mode.FAULT)
            {
                return;
            }
            switch (runtime.mode)
            {
                case IDLE_OPEN -> maintainIdle(level, spec, runtime, data);
                case CLOSING -> tickClosing(level, spec, runtime, data);
                case MOVING -> tickMoving(level, spec, runtime, data);
                case OPENING -> tickOpening(level, spec, runtime, data);
                case FAULT ->
                {
                    // Faults remain closed until an explicit repair.
                }
            }
            return;
        }
        NervCarrierPlatformEntity cabin = ensurePersistentCabin(
                level, spec, runtime, data);
        if (cabin != null)
        {
            tickPersistentCabin(level, spec, runtime, cabin, data);
            return;
        }
        if (runtime.cabinRevision >= ENTITY_CABIN_REVISION)
        {
            return;
        }
        if (runtime.mode == Mode.FAULT)
        {
            return;
        }
        switch (runtime.mode)
        {
            case IDLE_OPEN -> maintainIdle(level, spec, runtime, data);
            case CLOSING -> tickClosing(level, spec, runtime, data);
            case MOVING -> tickMoving(level, spec, runtime, data);
            case OPENING -> tickOpening(level, spec, runtime, data);
            case FAULT ->
            {
                // Faults are fail-closed and require an explicit migration.
            }
        }
    }

    /**
     * Handles the two exterior call buttons and the two buttons moving inside
     * the cabin. Event registration intentionally remains outside this class.
     */
    public static boolean handleUse(
            ServerPlayer player, BlockPos clicked, LiftSpec spec)
    {
        ServerLevel level = player.serverLevel();
        if (!FacilityWorldPolicy.isS20Rebuild(level.getServer())
                || !level.dimension().equals(FacilitySchemaV2.DIMENSION))
        {
            return false;
        }
        RuntimeData data = RuntimeData.get(level);
        LiftRuntime runtime = data.find(spec.id()).orElse(null);
        if (runtime == null)
        {
            return false;
        }

        /*
         * A player can reach a call button before the next scheduled lift
         * tick after loading the save.  The rejected entity-cabin prototype
         * persisted IN_TRANSIT/FAULT in that window, so the first click merely
         * reported a dead lift even though the rollback code was available.
         * Reconcile the bounded 5x5 block cabin at the interaction boundary;
         * this is the same idempotent migration used by tick()/install().
         */
        if (USE_LEGACY_BLOCK_CABIN
                && !ensureLegacyBlockCabin(level, spec, runtime, data))
        {
            return false;
        }

        NervCarrierPlatformEntity cabin = USE_LEGACY_BLOCK_CABIN ? null
                : ensurePersistentCabin(level, spec, runtime, data);
        if (!USE_LEGACY_BLOCK_CABIN && cabin != null)
        {
            return handlePersistentUse(player, clicked, spec,
                    runtime, cabin, data);
        }

        Landing requested = requestedLanding(
                level, clicked, spec, runtime);
        if (requested == null)
        {
            return false;
        }
        if (runtime.mode == Mode.FAULT)
        {
            message(player, "NERV LIFT  OUT OF SERVICE",
                    ChatFormatting.RED);
            return true;
        }
        if (runtime.mode != Mode.IDLE_OPEN)
        {
            message(player, "NERV LIFT  IN TRANSIT",
                    ChatFormatting.GOLD);
            return true;
        }
        if (runtime.currentY == requested.walkY())
        {
            maintainIdle(level, spec, runtime, data);
            message(player, "NERV LIFT  READY / " + requested.label(),
                    ChatFormatting.GREEN);
            return true;
        }

        runtime.targetY = requested.walkY();
        runtime.mode = Mode.CLOSING;
        runtime.phaseTicks = 0;
        closeAllLandingDoors(level, spec);
        setCabinDoor(level, spec.centreAt(runtime.currentY),
                runtime.cabinExit, false);
        data.markDirty();
        level.playSound(null, clicked, SoundEvents.PISTON_EXTEND,
                SoundSource.BLOCKS, 0.8F, 0.72F);
        message(player, "NERV LIFT  DOORS CLOSING / "
                        + requested.label(),
                ChatFormatting.AQUA);
        return true;
    }

    /**
     * Routes the two rendered controls inside a moving cabin into the exact
     * same persisted trip request used by the fixed landing buttons.  The
     * entity performs hit testing only; it never owns a second floor state.
     */
    public static boolean handleCabinControl(
            ServerPlayer player, NervCarrierPlatformEntity cabin,
            boolean upperButton)
    {
        ServerLevel level = player.serverLevel();
        if (!FacilityWorldPolicy.isS20Rebuild(level.getServer())
                || !level.dimension().equals(FacilitySchemaV2.DIMENSION)
                || cabin == null || !cabin.isPersistentLift()
                || player.distanceToSqr(cabin) > 36.0D)
        {
            return false;
        }
        LiftSpec spec = s20Lifts().stream()
                .filter(candidate -> candidate.id().equals(cabin.getLiftId()))
                .findFirst().orElse(null);
        if (spec == null)
        {
            return false;
        }
        RuntimeData data = RuntimeData.get(level);
        LiftRuntime runtime = data.find(spec.id()).orElse(null);
        if (runtime == null || runtime.cabinUuid == null
                || !runtime.cabinUuid.equals(cabin.getUUID()))
        {
            return false;
        }
        if (!cabin.consumePersistentLiftControlDebounce())
        {
            return true;
        }
        Landing target = upperButton ? spec.upper() : spec.lower();
        return requestPersistentLanding(player, cabin.blockPosition(), spec,
                runtime, cabin, data, target);
    }

    public static String status(ServerLevel level, LiftSpec spec)
    {
        LiftRuntime runtime = RuntimeData.get(level)
                .find(spec.id()).orElse(null);
        if (runtime == null)
        {
            return spec.id() + " not installed";
        }
        NervCarrierPlatformEntity cabin = USE_LEGACY_BLOCK_CABIN ? null
                : resolvePersistentCabin(level, spec, runtime);
        if (!USE_LEGACY_BLOCK_CABIN && cabin != null)
        {
            return spec.id() + " cabin=ENTITY"
                    + " state=" + liftStateName(
                    cabin.getPersistentLiftState())
                    + " currentY=" + String.format(java.util.Locale.ROOT,
                    "%.2f", cabin.getY())
                    + " targetY=" + String.format(java.util.Locale.ROOT,
                    "%.2f", cabin.getPersistentLiftTargetY())
                    + " exit=" + cabin.getLiftExit();
        }
        return spec.id() + " mode=" + runtime.mode
                + " currentY=" + runtime.currentY
                + " targetY=" + runtime.targetY
                + " facing=" + runtime.cabinExit
                + (runtime.fault.isBlank()
                ? "" : " fault=" + runtime.fault);
    }

    /**
     * One-time compatibility rollback from the rejected entity cabin to the
     * R28 block cabin.  The method is idempotent and never writes outside the
     * five-by-five car, its two existing landing doors and their controls.
     */
    private static boolean ensureLegacyBlockCabin(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime,
            RuntimeData data)
    {
        if (!level.hasChunkAt(spec.lower().cabinCentre())
                || !level.hasChunkAt(spec.upper().cabinCentre()))
        {
            return false;
        }

        List<NervCarrierPlatformEntity> entityCabins =
                persistentCabinsInShaft(level, spec);
        boolean rollback = runtime.cabinRevision > 0
                || runtime.cabinUuid != null || !entityCabins.isEmpty()
                || runtime.mode == Mode.FAULT;
        if (rollback)
        {
            double lastY = runtime.currentY;
            for (NervCarrierPlatformEntity entityCabin : entityCabins)
            {
                lastY = entityCabin.getY();
                Landing safe = nearestLanding(spec, lastY);
                double safeX = safe.cabinCentre().getX() + 0.5D
                        + safe.exit().getStepX() * 5.0D;
                double safeZ = safe.cabinCentre().getZ() + 0.5D
                        + safe.exit().getStepZ() * 5.0D;
                for (Entity passenger
                        : List.copyOf(entityCabin.getPassengers()))
                {
                    passenger.stopRiding();
                    passenger.moveTo(safeX, safe.walkY(), safeZ,
                            passenger.getYRot(), passenger.getXRot());
                }
                entityCabin.discard();
            }

            clearPersistentInteriorControls(level, spec.lower());
            clearPersistentInteriorControls(level, spec.upper());
            clearLandingDeck(level, spec.lower());
            clearLandingDeck(level, spec.upper());
            Landing start = nearestLanding(spec, lastY);
            runtime.mode = Mode.IDLE_OPEN;
            runtime.currentY = start.walkY();
            runtime.targetY = start.walkY();
            runtime.phaseTicks = 0;
            runtime.cabinExit = start.exit();
            runtime.fault = "";
            runtime.cabinUuid = null;
            runtime.cabinRevision = 0;
            runtime.entityMissingTicks = 0;
            runtime.motionEpoch = 0L;
            data.markDirty();
            ProjectSeele.LOGGER.warn(
                    "S20 lift {} restored to R28 block-cabin controller at {}",
                    spec.id(), start.label());
        }

        BlockPos centre = spec.centreAt(runtime.currentY);
        Landing current = spec.landingAt(runtime.currentY);
        if (current == null && runtime.mode == Mode.IDLE_OPEN)
        {
            current = nearestLanding(spec, runtime.currentY);
            runtime.currentY = current.walkY();
            runtime.targetY = current.walkY();
            runtime.cabinExit = current.exit();
            runtime.mode = Mode.IDLE_OPEN;
            runtime.phaseTicks = 0;
            data.markDirty();
            centre = current.cabinCentre();
        }
        if (!legacyCabinPresent(level, centre, runtime.cabinExit,
                runtime.mode == Mode.IDLE_OPEN))
        {
            buildCabin(level, centre, runtime.cabinExit,
                    runtime.mode == Mode.IDLE_OPEN);
        }
        if (runtime.mode == Mode.IDLE_OPEN)
        {
            setLandingDoor(level, spec.lower(), current == spec.lower());
            setLandingDoor(level, spec.upper(), current == spec.upper());
            setCabinDoor(level, centre, runtime.cabinExit, true);
        }
        enforceSingleExteriorCallButton(level, spec.lower());
        enforceSingleExteriorCallButton(level, spec.upper());
        return true;
    }

    private static List<NervCarrierPlatformEntity> persistentCabinsInShaft(
            ServerLevel level, LiftSpec spec)
    {
        AABB shaft = new AABB(
                spec.lower().cabinCentre().getX() - 3.5D,
                spec.lower().walkY() - 6.0D,
                spec.lower().cabinCentre().getZ() - 3.5D,
                spec.lower().cabinCentre().getX() + 4.5D,
                spec.upper().walkY() + 8.0D,
                spec.lower().cabinCentre().getZ() + 4.5D);
        return level.getEntitiesOfClass(
                NervCarrierPlatformEntity.class, shaft,
                candidate -> candidate.isAlive()
                        && candidate.isPersistentLift()
                        && spec.id().equals(candidate.getLiftId()));
    }

    private static NervCarrierPlatformEntity ensurePersistentCabin(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime,
            RuntimeData data)
    {
        NervCarrierPlatformEntity cabin = resolvePersistentCabin(
                level, spec, runtime);
        if (cabin != null)
        {
            boolean changed = runtime.cabinRevision
                    < ENTITY_CABIN_REVISION
                    || !cabin.getUUID().equals(runtime.cabinUuid);
            if (runtime.cabinRevision < ENTITY_CABIN_REVISION)
            {
                migratePersistentCabinEntity(level, spec, runtime, cabin);
            }
            runtime.cabinRevision = ENTITY_CABIN_REVISION;
            runtime.cabinUuid = cabin.getUUID();
            if (runtime.entityMissingTicks != 0)
            {
                runtime.entityMissingTicks = 0;
                changed = true;
            }
            retireDuplicatePersistentCabins(level, spec, cabin);
            if (changed)
            {
                data.markDirty();
            }
            return cabin;
        }

        if (!level.hasChunkAt(spec.lower().cabinCentre())
                || !level.hasChunkAt(spec.upper().cabinCentre()))
        {
            return null;
        }

        /*
         * A commissioned UUID is an asset, not a spawn hint.  If it cannot
         * be resolved while the shaft chunk is loaded, wait for entity-region
         * recovery and then fail closed.  Automatically minting a second UUID
         * here was the elevator equivalent of the old fifteen-plug defect.
         */
        if (runtime.cabinRevision >= ENTITY_CABIN_REVISION
                && runtime.cabinUuid != null)
        {
            runtime.entityMissingTicks++;
            data.markDirty();
            if (runtime.entityMissingTicks >= ENTITY_MISSING_GRACE_TICKS)
            {
                runtime.mode = Mode.FAULT;
                runtime.fault = "commissioned cabin UUID unresolved after "
                        + ENTITY_MISSING_GRACE_TICKS + " loaded ticks";
                closeAllLandingDoors(level, spec);
                ProjectSeele.LOGGER.error(
                        "S20 physical lift {} fail-closed: {}",
                        spec.id(), runtime.fault);
            }
            return null;
        }

        if (runtime.cabinRevision < ENTITY_CABIN_REVISION)
        {
            migrateLegacyCabinBlocks(level, spec, runtime);
            resetRuntimeAtNearestLanding(spec, runtime);
        }
        Landing start = nearestLanding(spec, runtime.currentY);
        NervCarrierPlatformEntity replacement =
                ModEntities.NERV_LIFT_CABIN.get().create(level);
        if (replacement == null)
        {
            runtime.mode = Mode.FAULT;
            runtime.fault = "persistent cabin entity could not be created";
            data.markDirty();
            return null;
        }
        replacement.setPos(start.cabinCentre().getX() + 0.5D,
                start.walkY(), start.cabinCentre().getZ() + 0.5D);
        replacement.setYRot(start.exit().toYRot());
        replacement.configurePersistentLift(spec.id(),
                liftAccent(spec), spec.lower().walkY(),
                spec.upper().walkY());
        replacement.setLiftExit(start.exit());
        if (!level.addFreshEntity(replacement))
        {
            runtime.mode = Mode.FAULT;
            runtime.fault = "persistent cabin entity could not enter world";
            data.markDirty();
            return null;
        }

        runtime.cabinRevision = ENTITY_CABIN_REVISION;
        runtime.cabinUuid = replacement.getUUID();
        runtime.mode = Mode.IDLE_OPEN;
        runtime.currentY = start.walkY();
        runtime.targetY = start.walkY();
        runtime.phaseTicks = 0;
        runtime.cabinExit = start.exit();
        runtime.fault = "";
        runtime.entityMissingTicks = 0;
        setLandingDoor(level, spec.lower(),
                start == spec.lower());
        setLandingDoor(level, spec.upper(),
                start == spec.upper());
        data.markDirty();
        ProjectSeele.LOGGER.info(
                "S20 lift {} migrated to persistent cabin {} at y={}",
                spec.id(), replacement.getUUID(), start.walkY());
        return replacement;
    }

    /**
     * Revision 2 adds the two durable landing coordinates used by the actual
     * in-car panel.  Revision-1 entities deserialize those fields as NaN; if
     * left untouched their rendered keys can never submit a valid floor.  A
     * migration always brakes and levels the existing UUID at the nearest
     * audited landing instead of spawning a replacement or opening mid-shaft.
     */
    private static void migratePersistentCabinEntity(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime,
            NervCarrierPlatformEntity cabin)
    {
        Landing landing = nearestLanding(spec, cabin.getY());
        closeAllLandingDoors(level, spec);
        cabin.configurePersistentLift(spec.id(), liftAccent(spec),
                spec.lower().walkY(), spec.upper().walkY());
        cabin.moveControlled(landing.cabinCentre().getX() + 0.5D,
                landing.walkY(), landing.cabinCentre().getZ() + 0.5D);
        cabin.setYRot(landing.exit().toYRot());
        cabin.setLiftExit(landing.exit());
        runtime.mode = Mode.IDLE_OPEN;
        runtime.currentY = landing.walkY();
        runtime.targetY = landing.walkY();
        runtime.phaseTicks = 0;
        runtime.cabinExit = landing.exit();
        runtime.fault = "";
        setLandingDoor(level, spec.lower(), landing == spec.lower());
        setLandingDoor(level, spec.upper(), landing == spec.upper());
        ProjectSeele.LOGGER.info(
                "S20 lift {} upgraded persistent cabin {} to revision {} at {}",
                spec.id(), cabin.getUUID(), ENTITY_CABIN_REVISION,
                landing.label());
    }

    private static NervCarrierPlatformEntity resolvePersistentCabin(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime)
    {
        if (runtime.cabinUuid != null)
        {
            Entity known = level.getEntity(runtime.cabinUuid);
            if (known instanceof NervCarrierPlatformEntity cabin
                    && cabin.isAlive() && cabin.isPersistentLift()
                    && spec.id().equals(cabin.getLiftId()))
            {
                return cabin;
            }
            if (runtime.cabinRevision >= ENTITY_CABIN_REVISION)
            {
                return null;
            }
        }
        AABB shaft = new AABB(
                spec.lower().cabinCentre().getX() - 3.5D,
                spec.lower().walkY() - 6.0D,
                spec.lower().cabinCentre().getZ() - 3.5D,
                spec.lower().cabinCentre().getX() + 4.5D,
                spec.upper().walkY() + 8.0D,
                spec.lower().cabinCentre().getZ() + 4.5D);
        List<NervCarrierPlatformEntity> matches =
                level.getEntitiesOfClass(
                        NervCarrierPlatformEntity.class, shaft,
                        candidate -> candidate.isAlive()
                                && candidate.isPersistentLift()
                                && spec.id().equals(candidate.getLiftId()));
        return matches.isEmpty() ? null : matches.get(0);
    }

    private static void retireDuplicatePersistentCabins(
            ServerLevel level, LiftSpec spec,
            NervCarrierPlatformEntity canonical)
    {
        AABB shaft = new AABB(
                spec.lower().cabinCentre().getX() - 3.5D,
                spec.lower().walkY() - 6.0D,
                spec.lower().cabinCentre().getZ() - 3.5D,
                spec.lower().cabinCentre().getX() + 4.5D,
                spec.upper().walkY() + 8.0D,
                spec.lower().cabinCentre().getZ() + 4.5D);
        List<NervCarrierPlatformEntity> duplicates =
                level.getEntitiesOfClass(
                        NervCarrierPlatformEntity.class, shaft,
                        candidate -> candidate.isAlive()
                                && candidate != canonical
                                && candidate.isPersistentLift()
                                && spec.id().equals(candidate.getLiftId()));
        for (NervCarrierPlatformEntity duplicate : duplicates)
        {
            boolean passengerTransferFailed = false;
            for (Entity passenger : List.copyOf(duplicate.getPassengers()))
            {
                passenger.stopRiding();
                if (!passenger.startRiding(canonical, true))
                {
                    passengerTransferFailed = true;
                    break;
                }
            }
            if (passengerTransferFailed)
            {
                canonical.forcePersistentLiftFault();
                duplicate.forcePersistentLiftFault();
                ProjectSeele.LOGGER.error(
                        "S20 lift {} duplicate cabin passenger transfer "
                                + "failed; both cabins frozen",
                        spec.id());
                continue;
            }
            ProjectSeele.LOGGER.warn(
                    "S20 lift {} retired duplicate persistent cabin {} "
                            + "in favour of {}",
                    spec.id(), duplicate.getUUID(), canonical.getUUID());
            duplicate.discard();
        }
    }

    private static void migrateLegacyCabinBlocks(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime)
    {
        BlockPos legacyCentre = spec.centreAt(runtime.currentY);
        if (cabinFloorPresent(level, legacyCentre))
        {
            clearCabin(level, legacyCentre);
        }
        buildLanding(level, spec.lower());
        buildLanding(level, spec.upper());
        Landing start = nearestLanding(spec, runtime.currentY);
        Landing away = start == spec.lower()
                ? spec.upper() : spec.lower();
        buildLandingDeck(level, start);
        clearLandingDeck(level, away);
    }

    private static void buildLandingDeck(
            ServerLevel level, Landing landing)
    {
        BlockPos centre = landing.cabinCentre();
        for (int dx = -CABIN_RADIUS; dx <= CABIN_RADIUS; dx++)
        {
            for (int dz = -CABIN_RADIUS; dz <= CABIN_RADIUS; dz++)
            {
                set(level, centre.offset(dx, -1, dz), CABIN_FLOOR);
            }
        }
    }

    private static void clearLandingDeck(
            ServerLevel level, Landing landing)
    {
        BlockPos centre = landing.cabinCentre();
        for (int dx = -CABIN_RADIUS; dx <= CABIN_RADIUS; dx++)
        {
            for (int dz = -CABIN_RADIUS; dz <= CABIN_RADIUS; dz++)
            {
                BlockPos position = centre.offset(dx, -1, dz);
                if (level.getBlockState(position).equals(CABIN_FLOOR))
                {
                    set(level, position, AIR);
                }
            }
        }
    }

    private static void resetRuntimeAtNearestLanding(
            LiftSpec spec, LiftRuntime runtime)
    {
        Landing landing = nearestLanding(spec, runtime.currentY);
        runtime.mode = Mode.IDLE_OPEN;
        runtime.currentY = landing.walkY();
        runtime.targetY = landing.walkY();
        runtime.phaseTicks = 0;
        runtime.cabinExit = landing.exit();
        runtime.fault = "";
    }

    private static Landing nearestLanding(LiftSpec spec, double y)
    {
        return Math.abs(y - spec.lower().walkY())
                <= Math.abs(y - spec.upper().walkY())
                ? spec.lower() : spec.upper();
    }

    private static int liftAccent(LiftSpec spec)
    {
        if (spec.id().equals(COMMAND_REAR_LIFT_ID))
        {
            return 4;
        }
        if (spec.id().equals(OBSERVATION_HANGAR_LIFT_ID))
        {
            return 1;
        }
        if (spec.id().equals(SURFACE_TRANSIT_LIFT_ID))
        {
            return 2;
        }
        return 3;
    }

    private static void tickPersistentCabin(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime,
            NervCarrierPlatformEntity cabin, RuntimeData data)
    {
        boolean lowerOpen = cabin.canOpenLandingDoorAt(
                spec.lower().walkY());
        boolean upperOpen = cabin.canOpenLandingDoorAt(
                spec.upper().walkY());
        setLandingDoor(level, spec.lower(), lowerOpen);
        setLandingDoor(level, spec.upper(), upperOpen);

        Landing current = cabin.isAtLiftY(spec.lower().walkY())
                ? spec.lower()
                : cabin.isAtLiftY(spec.upper().walkY())
                ? spec.upper() : null;
        if (current != null)
        {
            cabin.setLiftExit(current.exit());
            cabin.setYRot(current.exit().toYRot());
            int state = cabin.getPersistentLiftState();
            boolean atRest = state
                    == NervCarrierPlatformEntity.LIFT_IDLE_OPEN
                    || state
                    == NervCarrierPlatformEntity.LIFT_DOOR_CLOSING
                    || state
                    == NervCarrierPlatformEntity.LIFT_DOOR_OPENING
                    || state
                    == NervCarrierPlatformEntity.LIFT_RECOVERY_HOLD;
            if (atRest)
            {
                buildLandingDeck(level, current);
            }
            else
            {
                clearLandingDeck(level, current);
            }
            Landing away = current == spec.lower()
                    ? spec.upper() : spec.lower();
            clearLandingDeck(level, away);
            if (runtime.currentY != current.walkY())
            {
                runtime.currentY = current.walkY();
                runtime.targetY = current.walkY();
                runtime.cabinExit = current.exit();
                data.markDirty();
            }
        }

        updatePersistentInteriorControls(level, spec, cabin, current);

        boolean doorsClosed = landingDoorClosed(level, spec.lower())
                && landingDoorClosed(level, spec.upper());
        boolean motionAllowed = !cabin.isLiftDoorOpen()
                && doorsClosed;
        if (motionAllowed
                && cabin.getPersistentLiftPendingMotionEpoch()
                == runtime.motionEpoch)
        {
            cabin.activatePersistentLiftMotion(runtime.motionEpoch);
        }
        else if (!motionAllowed && cabin.isPersistentLiftTranslating())
        {
            cabin.revokePersistentLiftMotion();
        }
        if (motionAllowed && cabin.isPersistentLiftRecoveryHold())
        {
            Landing recovery = recoveryLanding(spec,
                    cabin.getPersistentLiftTargetY(), cabin.getY());
            long motionEpoch = Math.max(runtime.motionEpoch,
                    cabin.getPersistentLiftLastMotionEpoch()) + 1L;
            cabin.setLiftExit(recovery.exit());
            if (cabin.recoverPersistentLiftTo(
                    recovery.walkY(), motionEpoch))
            {
                runtime.motionEpoch = motionEpoch;
                runtime.targetY = recovery.walkY();
                runtime.cabinExit = recovery.exit();
                data.markDirty();
            }
        }
        if (cabin.getPersistentLiftState()
                == NervCarrierPlatformEntity.LIFT_FAULT
                && runtime.mode != Mode.FAULT)
        {
            runtime.mode = Mode.FAULT;
            runtime.fault = "persistent cabin entered fail-closed state";
            data.markDirty();
        }
    }

    private static boolean handlePersistentUse(
            ServerPlayer player, BlockPos clicked, LiftSpec spec,
            LiftRuntime runtime, NervCarrierPlatformEntity cabin,
            RuntimeData data)
    {
        ServerLevel level = player.serverLevel();
        if (!(level.getBlockState(clicked).getBlock()
                instanceof ButtonBlock))
        {
            return false;
        }
        Landing origin;
        Landing directTarget = requestedPersistentInteriorLanding(
                clicked, spec, cabin);
        boolean destinationButton;
        if (directTarget != null)
        {
            origin = cabin.isAtLiftY(spec.lower().walkY())
                    ? spec.lower() : spec.upper();
            destinationButton = true;
        }
        else if (clicked.equals(exteriorCallPosition(spec.lower())))
        {
            origin = spec.lower();
            destinationButton = false;
        }
        else if (clicked.equals(exteriorDestinationPosition(
                spec.lower())))
        {
            origin = spec.lower();
            destinationButton = true;
        }
        else if (clicked.equals(exteriorCallPosition(spec.upper())))
        {
            origin = spec.upper();
            destinationButton = false;
        }
        else if (clicked.equals(exteriorDestinationPosition(
                spec.upper())))
        {
            origin = spec.upper();
            destinationButton = true;
        }
        else
        {
            return false;
        }

        Landing target;
        if (directTarget != null)
        {
            target = directTarget;
        }
        else if (!destinationButton || !cabin.isAtLiftY(origin.walkY()))
        {
            target = origin;
        }
        else
        {
            target = origin == spec.lower()
                    ? spec.upper() : spec.lower();
        }
        return requestPersistentLanding(player, clicked, spec, runtime,
                cabin, data, target);
    }

    private static boolean requestPersistentLanding(
            ServerPlayer player, BlockPos acknowledgement,
            LiftSpec spec, LiftRuntime runtime,
            NervCarrierPlatformEntity cabin, RuntimeData data,
            Landing target)
    {
        ServerLevel level = player.serverLevel();
        if (cabin.getPersistentLiftState()
                == NervCarrierPlatformEntity.LIFT_FAULT)
        {
            message(player, "NERV LIFT  OUT OF SERVICE",
                    ChatFormatting.RED);
            return true;
        }
        if (!cabin.isPersistentLiftIdle())
        {
            message(player, "NERV LIFT  IN TRANSIT",
                    ChatFormatting.GOLD);
            return true;
        }
        if (cabin.isAtLiftY(target.walkY()))
        {
            cabin.setLiftExit(target.exit());
            message(player, "NERV LIFT  READY / " + target.label(),
                    ChatFormatting.GREEN);
            return true;
        }

        cabin.setLiftExit(target.exit());
        long motionEpoch = Math.max(runtime.motionEpoch,
                cabin.getPersistentLiftLastMotionEpoch()) + 1L;
        if (!cabin.beginPersistentLiftTravel(
                target.walkY(), motionEpoch))
        {
            message(player, "NERV LIFT  CONTROL REJECTED",
                    ChatFormatting.RED);
            return true;
        }
        runtime.motionEpoch = motionEpoch;
        runtime.targetY = target.walkY();
        runtime.cabinExit = target.exit();
        runtime.mode = Mode.IDLE_OPEN;
        runtime.fault = "";
        data.markDirty();
        level.playSound(null, acknowledgement,
                SoundEvents.NOTE_BLOCK_PLING.value(),
                SoundSource.BLOCKS, 0.8F, 0.72F);
        message(player, "NERV LIFT  " + target.label()
                        + " / DOORS CLOSE IN 3 SECONDS",
                ChatFormatting.AQUA);
        return true;
    }

    private static Landing recoveryLanding(
            LiftSpec spec, double savedTargetY, double currentY)
    {
        if (Math.abs(savedTargetY - spec.lower().walkY()) <= 0.08D)
        {
            return spec.lower();
        }
        if (Math.abs(savedTargetY - spec.upper().walkY()) <= 0.08D)
        {
            return spec.upper();
        }
        return nearestLanding(spec, currentY);
    }

    /**
     * Materialises two real, clickable controls only while the persistent
     * cabin is level and fully open.  The blocks are removed before motion;
     * the rendered panel remains part of the same cabin entity in transit.
     */
    private static void updatePersistentInteriorControls(
            ServerLevel level, LiftSpec spec,
            NervCarrierPlatformEntity cabin, Landing current)
    {
        if (current == null || !cabin.isPersistentLiftIdle()
                || !cabin.isLiftDoorOpen())
        {
            clearPersistentInteriorControls(level, spec.lower());
            clearPersistentInteriorControls(level, spec.upper());
            return;
        }

        Landing away = current == spec.lower()
                ? spec.upper() : spec.lower();
        clearPersistentInteriorControls(level, away);

        Direction side = current.exit().getClockWise();
        BlockPos centre = current.cabinCentre();
        BlockPos lowerBacking = centre.relative(side, CABIN_RADIUS)
                .above(1);
        BlockPos upperBacking = lowerBacking.above();
        set(level, lowerBacking, CABIN_PANEL);
        set(level, upperBacking, CABIN_PANEL);
        set(level, interiorButtonPosition(centre, current.exit(), false),
                wallButton(side.getOpposite()));
        set(level, interiorButtonPosition(centre, current.exit(), true),
                wallButton(side.getOpposite()));
    }

    private static void clearPersistentInteriorControls(
            ServerLevel level, Landing landing)
    {
        Direction side = landing.exit().getClockWise();
        BlockPos centre = landing.cabinCentre();
        for (boolean upper : new boolean[] {false, true})
        {
            BlockPos button = interiorButtonPosition(
                    centre, landing.exit(), upper);
            if (level.getBlockState(button).getBlock()
                    instanceof ButtonBlock)
            {
                set(level, button, AIR);
            }
            BlockPos backing = centre.relative(side, CABIN_RADIUS)
                    .above(upper ? 2 : 1);
            if (level.getBlockState(backing).equals(CABIN_PANEL))
            {
                set(level, backing, AIR);
            }
        }
    }

    private static Landing requestedPersistentInteriorLanding(
            BlockPos clicked, LiftSpec spec,
            NervCarrierPlatformEntity cabin)
    {
        Landing current = cabin.isAtLiftY(spec.lower().walkY())
                ? spec.lower()
                : cabin.isAtLiftY(spec.upper().walkY())
                ? spec.upper() : null;
        if (current == null)
        {
            return null;
        }
        BlockPos centre = current.cabinCentre();
        if (clicked.equals(interiorButtonPosition(
                centre, current.exit(), false)))
        {
            return spec.lower();
        }
        return clicked.equals(interiorButtonPosition(
                centre, current.exit(), true))
                ? spec.upper() : null;
    }

    private static boolean landingDoorClosed(
            ServerLevel level, Landing landing)
    {
        Direction lateral = landing.exit().getClockWise();
        for (int side = -LANDING_DOOR_HALF_WIDTH;
             side <= LANDING_DOOR_HALF_WIDTH; side++)
        {
            for (int dy = 0; dy < DOOR_HEIGHT; dy++)
            {
                BlockPos position = landing.cabinCentre()
                        .relative(landing.exit(), LANDING_DOOR_DISTANCE)
                        .relative(lateral, side).above(dy);
                if (!level.getBlockState(position).equals(LANDING_DOOR))
                {
                    return false;
                }
            }
        }
        return true;
    }

    private static String liftStateName(int state)
    {
        return switch (state)
        {
            case NervCarrierPlatformEntity.LIFT_IDLE_OPEN -> "IDLE_OPEN";
            case NervCarrierPlatformEntity.LIFT_DOOR_CLOSING ->
                    "DOOR_CLOSING";
            case NervCarrierPlatformEntity.LIFT_STARTING -> "STARTING";
            case NervCarrierPlatformEntity.LIFT_MOVING -> "MOVING";
            case NervCarrierPlatformEntity.LIFT_BRAKING -> "BRAKING";
            case NervCarrierPlatformEntity.LIFT_LEVELING -> "LEVELING";
            case NervCarrierPlatformEntity.LIFT_DOOR_OPENING ->
                    "DOOR_OPENING";
            case NervCarrierPlatformEntity.LIFT_RECOVERY_HOLD ->
                    "RECOVERY_HOLD";
            case NervCarrierPlatformEntity.LIFT_FAULT -> "FAULT";
            default -> "UNKNOWN(" + state + ")";
        };
    }

    private static void maintainIdle(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime,
            RuntimeData data)
    {
        Landing current = spec.landingAt(runtime.currentY);
        if (current == null)
        {
            fault(level, spec, runtime, data,
                    "idle cabin is not level with a landing");
            return;
        }
        if (!cabinFloorPresent(level, spec.centreAt(runtime.currentY)))
        {
            fault(level, spec, runtime, data,
                    "physical cabin floor is missing");
            return;
        }
        runtime.cabinExit = current.exit();
        setCabinDoor(level, spec.centreAt(runtime.currentY),
                runtime.cabinExit, true);
        setLandingDoor(level, spec.lower(),
                current.walkY() == spec.lower().walkY());
        setLandingDoor(level, spec.upper(),
                current.walkY() == spec.upper().walkY());
    }

    private static void tickClosing(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime,
            RuntimeData data)
    {
        closeAllLandingDoors(level, spec);
        setCabinDoor(level, spec.centreAt(runtime.currentY),
                runtime.cabinExit, false);
        runtime.phaseTicks++;
        if (runtime.phaseTicks < CLOSE_TICKS)
        {
            data.markDirty();
            return;
        }
        if (!barriersClosed(level, spec, runtime))
        {
            fault(level, spec, runtime, data,
                    "door interlock did not close");
            return;
        }
        runtime.mode = Mode.MOVING;
        runtime.phaseTicks = 0;
        data.markDirty();
    }

    private static void tickMoving(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime,
            RuntimeData data)
    {
        closeAllLandingDoors(level, spec);
        setCabinDoor(level, spec.centreAt(runtime.currentY),
                runtime.cabinExit, false);
        if (!barriersClosed(level, spec, runtime))
        {
            fault(level, spec, runtime, data,
                    "door interlock opened during motion");
            return;
        }
        runtime.phaseTicks++;
        if (runtime.phaseTicks % MOVE_INTERVAL_TICKS != 0)
        {
            data.markDirty();
            return;
        }
        int deltaY = Integer.compare(runtime.targetY, runtime.currentY);
        if (deltaY == 0)
        {
            runtime.mode = Mode.OPENING;
            runtime.phaseTicks = 0;
            data.markDirty();
            return;
        }
        if (!moveCabinOneBlock(level, spec, runtime, deltaY))
        {
            fault(level, spec, runtime, data,
                    "swept cabin became obstructed");
            return;
        }
        if (runtime.currentY == runtime.targetY)
        {
            runtime.mode = Mode.OPENING;
            runtime.phaseTicks = 0;
            level.playSound(null, spec.centreAt(runtime.currentY),
                    SoundEvents.PISTON_CONTRACT, SoundSource.BLOCKS,
                    0.8F, 1.08F);
        }
        else if (Math.floorMod(runtime.currentY, 8) == 0)
        {
            level.playSound(null, spec.centreAt(runtime.currentY),
                    SoundEvents.BEACON_AMBIENT, SoundSource.BLOCKS,
                    0.25F, deltaY > 0 ? 1.08F : 0.82F);
        }
        data.markDirty();
    }

    private static void tickOpening(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime,
            RuntimeData data)
    {
        Landing destination = spec.landingAt(runtime.currentY);
        if (destination == null)
        {
            fault(level, spec, runtime, data,
                    "arrival is not level with a landing");
            return;
        }
        closeAllLandingDoors(level, spec);
        setCabinDoor(level, spec.centreAt(runtime.currentY),
                runtime.cabinExit, false);
        runtime.phaseTicks++;
        if (runtime.phaseTicks < OPEN_TICKS)
        {
            data.markDirty();
            return;
        }
        runtime.cabinExit = destination.exit();
        buildCabin(level, spec.centreAt(runtime.currentY),
                runtime.cabinExit, true);
        setLandingDoor(level, destination, true);
        runtime.mode = Mode.IDLE_OPEN;
        runtime.phaseTicks = 0;
        runtime.targetY = runtime.currentY;
        data.markDirty();
        level.playSound(null, spec.centreAt(runtime.currentY),
                SoundEvents.BEACON_ACTIVATE, SoundSource.BLOCKS,
                0.55F, 1.2F);
    }

    private static boolean moveCabinOneBlock(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime,
            int deltaY)
    {
        BlockPos currentCentre = spec.centreAt(runtime.currentY);
        BlockPos nextCentre = currentCentre.above(deltaY);
        if (!canOccupyCabinAt(level, currentCentre, nextCentre))
        {
            return false;
        }
        List<ServerPlayer> riders = ridersInside(level, currentCentre);
        clearCabin(level, currentCentre);
        for (ServerPlayer rider : riders)
        {
            /*
             * MoverType.PISTON clamps an entity to roughly 0.51 blocks per
             * tick. The cabin moves one complete block, so a rider advanced
             * through that path inevitably fell through after a few steps.
             * Keep the 20 Hz cabin rate but lock riders to the same exact
             * integer delta until the entity-based smooth cabin replaces this
             * physical-block prototype.
             */
            rider.teleportTo(level, rider.getX(),
                    rider.getY() + deltaY, rider.getZ(),
                    rider.getYRot(), rider.getXRot());
            rider.setDeltaMovement(Vec3.ZERO);
            rider.resetFallDistance();
        }
        Landing target = spec.landingAt(runtime.targetY);
        Direction nextExit = target == null
                ? runtime.cabinExit : target.exit();
        buildCabin(level, nextCentre, nextExit, false);
        runtime.currentY += deltaY;
        runtime.cabinExit = nextExit;
        return cabinFloorPresent(level, nextCentre);
    }

    private static boolean canOccupyCabinAt(
            ServerLevel level, BlockPos currentCentre,
            BlockPos nextCentre)
    {
        if (!level.hasChunkAt(nextCentre))
        {
            return false;
        }
        for (int dx = -CABIN_RADIUS; dx <= CABIN_RADIUS; dx++)
        {
            for (int dz = -CABIN_RADIUS; dz <= CABIN_RADIUS; dz++)
            {
                for (int dy = -1; dy < CABIN_HEIGHT; dy++)
                {
                    BlockPos position = nextCentre.offset(dx, dy, dz);
                    BlockState state = level.getBlockState(position);
                    if (state.isAir())
                    {
                        continue;
                    }
                    if (insideCabinBounds(position, currentCentre)
                            && isCabinOwnedState(state))
                    {
                        continue;
                    }
                    return false;
                }
            }
        }
        return true;
    }

    private static List<ServerPlayer> ridersInside(
            ServerLevel level, BlockPos centre)
    {
        double x = centre.getX() + 0.5D;
        double z = centre.getZ() + 0.5D;
        AABB interior = new AABB(
                x - 1.45D, centre.getY() - 0.1D, z - 1.45D,
                x + 1.45D, centre.getY() + 3.9D, z + 1.45D);
        return new ArrayList<>(level.getEntitiesOfClass(
                ServerPlayer.class, interior,
                player -> player.isAlive() && !player.isPassenger()));
    }

    private static void buildCabin(
            ServerLevel level, BlockPos centre, Direction exit,
            boolean doorOpen)
    {
        for (int dx = -CABIN_RADIUS; dx <= CABIN_RADIUS; dx++)
        {
            for (int dz = -CABIN_RADIUS; dz <= CABIN_RADIUS; dz++)
            {
                set(level, centre.offset(dx, -1, dz), CABIN_FLOOR);
                set(level, centre.offset(dx, CABIN_HEIGHT - 1, dz),
                        CABIN_ROOF);
                if (Math.abs(dx) != CABIN_RADIUS
                        && Math.abs(dz) != CABIN_RADIUS)
                {
                    continue;
                }
                for (int dy = 0; dy < CABIN_HEIGHT - 1; dy++)
                {
                    BlockPos position = centre.offset(dx, dy, dz);
                    if (isCabinDoorCell(
                            centre, position, exit)
                            && dy < DOOR_HEIGHT)
                    {
                        set(level, position,
                                doorOpen ? AIR : CABIN_DOOR);
                    }
                    else
                    {
                        set(level, position, CABIN_WALL);
                    }
                }
            }
        }
        buildInteriorControls(level, centre, exit);
    }

    private static void clearCabin(
            ServerLevel level, BlockPos centre)
    {
        for (int dx = -CABIN_RADIUS; dx <= CABIN_RADIUS; dx++)
        {
            for (int dz = -CABIN_RADIUS; dz <= CABIN_RADIUS; dz++)
            {
                for (int dy = -1; dy < CABIN_HEIGHT; dy++)
                {
                    BlockPos position = centre.offset(dx, dy, dz);
                    if (isCabinOwnedState(level.getBlockState(position)))
                    {
                        set(level, position, AIR);
                    }
                }
            }
        }
    }

    private static void buildInteriorControls(
            ServerLevel level, BlockPos centre, Direction exit)
    {
        Direction side = exit.getClockWise();
        BlockPos backing = centre.relative(side, CABIN_RADIUS).above(1);
        set(level, backing, CABIN_PANEL);
        set(level, backing.above(), CABIN_PANEL);
        BlockState button = wallButton(side.getOpposite());
        set(level, backing.relative(side.getOpposite()), button);
        set(level, backing.above().relative(side.getOpposite()), button);
    }

    private static void buildLanding(
            ServerLevel level, Landing landing)
    {
        BlockPos centre = landing.cabinCentre();
        Direction exit = landing.exit();
        Direction lateral = exit.getClockWise();
        for (int depth = CABIN_DOOR_DISTANCE + 1;
             depth <= THRESHOLD_END; depth++)
        {
            for (int side = -2; side <= 2; side++)
            {
                BlockPos floor = centre.relative(exit, depth)
                        .relative(lateral, side).below();
                set(level, floor,
                        Math.floorMod(side + depth, 7) == 0
                                ? LANDING_LIGHT : CABIN_FLOOR);
                for (int dy = 0; dy < DOOR_HEIGHT; dy++)
                {
                    setIfReplaceable(level, floor.above(dy + 1), AIR);
                }
            }
        }

        for (int side : new int[] {-3, 3})
        {
            for (int dy = -1; dy <= CABIN_HEIGHT - 1; dy++)
            {
                BlockPos frame = centre
                        .relative(exit, LANDING_DOOR_DISTANCE)
                        .relative(lateral, side).above(dy);
                set(level, frame,
                        dy == 2 ? LANDING_ACCENT : LANDING_FRAME);
            }
        }
        for (int side = -2; side <= 2; side++)
        {
            BlockPos header = centre
                    .relative(exit, LANDING_DOOR_DISTANCE)
                    .relative(lateral, side)
                    .above(DOOR_HEIGHT);
            set(level, header,
                    side == 0 ? LANDING_LIGHT : LANDING_FRAME);
        }

        BlockPos callBacking = centre
                .relative(exit, LANDING_DOOR_DISTANCE)
                .relative(lateral, 3).above(1);
        set(level, callBacking, LANDING_ACCENT);
        set(level, callBacking.relative(exit), wallButton(exit));
        set(level, callBacking.above(), CABIN_PANEL);
        // One exterior call button only. Floor selection belongs inside the
        // car, where the proven R28 cabin has separate UP and DOWN buttons.
        set(level, callBacking.above().relative(exit), AIR);
        setLandingDoor(level, landing, false);
    }

    private static void enforceSingleExteriorCallButton(
            ServerLevel level, Landing landing)
    {
        BlockPos call = exteriorCallPosition(landing);
        set(level, call, wallButton(landing.exit()));
        set(level, call.above(), AIR);
    }

    private static void setLandingDoor(
            ServerLevel level, Landing landing, boolean open)
    {
        Direction lateral = landing.exit().getClockWise();
        for (int side = -LANDING_DOOR_HALF_WIDTH;
             side <= LANDING_DOOR_HALF_WIDTH; side++)
        {
            for (int dy = 0; dy < DOOR_HEIGHT; dy++)
            {
                BlockPos position = landing.cabinCentre()
                        .relative(landing.exit(),
                                LANDING_DOOR_DISTANCE)
                        .relative(lateral, side).above(dy);
                set(level, position, open ? AIR : LANDING_DOOR);
            }
        }
    }

    private static void setCabinDoor(
            ServerLevel level, BlockPos centre, Direction exit,
            boolean open)
    {
        Direction lateral = exit.getClockWise();
        for (int side = -CABIN_DOOR_HALF_WIDTH;
             side <= CABIN_DOOR_HALF_WIDTH; side++)
        {
            for (int dy = 0; dy < DOOR_HEIGHT; dy++)
            {
                BlockPos position = centre
                        .relative(exit, CABIN_DOOR_DISTANCE)
                        .relative(lateral, side).above(dy);
                set(level, position, open ? AIR : CABIN_DOOR);
            }
        }
    }

    private static void closeAllLandingDoors(
            ServerLevel level, LiftSpec spec)
    {
        setLandingDoor(level, spec.lower(), false);
        setLandingDoor(level, spec.upper(), false);
    }

    private static boolean barriersClosed(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime)
    {
        for (Landing landing : List.of(spec.lower(), spec.upper()))
        {
            Direction lateral = landing.exit().getClockWise();
            for (int side = -LANDING_DOOR_HALF_WIDTH;
                 side <= LANDING_DOOR_HALF_WIDTH; side++)
            {
                for (int dy = 0; dy < DOOR_HEIGHT; dy++)
                {
                    BlockPos position = landing.cabinCentre()
                            .relative(landing.exit(),
                                    LANDING_DOOR_DISTANCE)
                            .relative(lateral, side).above(dy);
                    if (!level.getBlockState(position)
                            .equals(LANDING_DOOR))
                    {
                        return false;
                    }
                }
            }
        }
        BlockPos centre = spec.centreAt(runtime.currentY);
        Direction lateral = runtime.cabinExit.getClockWise();
        for (int side = -CABIN_DOOR_HALF_WIDTH;
             side <= CABIN_DOOR_HALF_WIDTH; side++)
        {
            for (int dy = 0; dy < DOOR_HEIGHT; dy++)
            {
                BlockPos position = centre
                        .relative(runtime.cabinExit,
                                CABIN_DOOR_DISTANCE)
                        .relative(lateral, side).above(dy);
                if (!level.getBlockState(position).equals(CABIN_DOOR))
                {
                    return false;
                }
            }
        }
        return true;
    }

    private static Landing requestedLanding(
            ServerLevel level, BlockPos clicked, LiftSpec spec,
            LiftRuntime runtime)
    {
        if (!(level.getBlockState(clicked).getBlock()
                instanceof ButtonBlock))
        {
            return null;
        }
        if (clicked.equals(exteriorCallPosition(spec.lower())))
        {
            return spec.lower();
        }
        if (clicked.equals(exteriorCallPosition(spec.upper())))
        {
            return spec.upper();
        }
        BlockPos centre = spec.centreAt(runtime.currentY);
        BlockPos lowerButton = interiorButtonPosition(
                centre, runtime.cabinExit, false);
        BlockPos upperButton = interiorButtonPosition(
                centre, runtime.cabinExit, true);
        if (clicked.equals(lowerButton))
        {
            return spec.lower();
        }
        return clicked.equals(upperButton) ? spec.upper() : null;
    }

    public static BlockPos exteriorCallPosition(Landing landing)
    {
        Direction lateral = landing.exit().getClockWise();
        return landing.cabinCentre()
                .relative(landing.exit(), LANDING_DOOR_DISTANCE + 1)
                .relative(lateral, 3).above(1);
    }

    /**
     * Compatibility coordinate used only by the retired entity-cabin path.
     * The authoritative R28 block cabin deliberately leaves this position
     * empty: each landing has one call button and the car has two floor keys.
     */
    public static BlockPos exteriorDestinationPosition(Landing landing)
    {
        return exteriorCallPosition(landing).above();
    }

    public static BlockPos interiorButtonPosition(
            BlockPos cabinCentre, Direction exit, boolean upper)
    {
        Direction side = exit.getClockWise();
        return cabinCentre.relative(side, CABIN_RADIUS - 1)
                .above(upper ? 2 : 1);
    }

    private static void inspectRouteHandoff(
            ServerLevel level, LiftSpec spec, Landing landing,
            List<String> failures)
    {
        BlockPos feet = landing.cabinCentre()
                .relative(landing.exit(), ROUTE_HANDOFF_DISTANCE);
        if (!level.getBlockState(feet.below()).isCollisionShapeFullBlock(
                level, feet.below()))
        {
            addFailure(failures,
                    "landing route has no supporting floor at "
                            + feet.below());
        }
        if (!level.getBlockState(feet).isAir()
                || !level.getBlockState(feet.above()).isAir())
        {
            addFailure(failures,
                    "landing route lacks two-block headroom at " + feet);
        }
    }

    private static boolean legacyEndpointStateAllowed(
            LiftSpec spec, BlockPos position, BlockState state)
    {
        if (spec.id().equals(COMMAND_REAR_LIFT_ID)
                && (state.is(Blocks.IRON_BLOCK)
                || state.is(Blocks.BLACK_CONCRETE)
                || state.is(Blocks.WHITE_CONCRETE)
                || state.is(Blocks.ORANGE_CONCRETE)
                || state.is(Blocks.SEA_LANTERN)
                || state.is(Blocks.REINFORCED_DEEPSLATE)
                || state.is(Blocks.GRAY_STAINED_GLASS)
                || state.is(Blocks.LIGHT_GRAY_STAINED_GLASS)
                || state.is(Blocks.POLISHED_DEEPSLATE)
                || state.is(Blocks.POLISHED_BLACKSTONE)
                || state.is(Blocks.SMOOTH_QUARTZ)
                || state.is(Blocks.LIGHT_GRAY_CONCRETE)
                || state.getBlock() instanceof ButtonBlock))
        {
            /*
             * The approved reference contains three 5x5 maintenance plates
             * crossing this exact old service axis. They are inside the
             * bounded cabin sweep and are intentionally removed when the
             * persistent shaft is commissioned.
             */
            return true;
        }
        if (spec.id().equals(SURFACE_TRANSIT_LIFT_ID)
                && (state.is(Blocks.IRON_BLOCK)
                || state.is(Blocks.SMOOTH_QUARTZ)
                || state.is(Blocks.BLACK_CONCRETE)
                || state.is(Blocks.LIGHT_GRAY_STAINED_GLASS)
                || state.is(Blocks.GRAY_STAINED_GLASS)
                || state.is(Blocks.ORANGE_CONCRETE)
                || state.is(Blocks.SEA_LANTERN)
                || state.is(Blocks.REINFORCED_DEEPSLATE)
                || state.is(Blocks.POLISHED_DEEPSLATE)
                || state.is(Blocks.STONE_BUTTON)))
        {
            /*
             * A pyramid-clear pass removed the old cabin floor but left
             * other exact lift blocks on this same axis. The v2 identity
             * permits only those known states so installation can replace
             * the orphaned cabin without accepting arbitrary obstructions.
             */
            return true;
        }
        int y = position.getY();
        boolean endpointPlane =
                y == spec.lower().walkY() - 1
                        || y == spec.upper().walkY() - 1
                        || y == spec.lower().walkY()
                        + CABIN_HEIGHT - 1
                        || y == spec.upper().walkY()
                        + CABIN_HEIGHT - 1;
        boolean endpointInterior =
                Math.abs(y - spec.lower().walkY()) <= 3
                        || Math.abs(y - spec.upper().walkY()) <= 3;
        if (endpointPlane && (state.is(Blocks.POLISHED_DEEPSLATE)
                || state.is(Blocks.POLISHED_BLACKSTONE)
                || state.is(Blocks.REINFORCED_DEEPSLATE)
                || state.is(Blocks.SEA_LANTERN)
                || state.is(Blocks.SMOOTH_STONE)))
        {
            return true;
        }
        return endpointInterior
                && (state.is(Blocks.STONE_BUTTON)
                || state.is(Blocks.CYAN_CONCRETE));
    }

    private static void clearSweptCabinVolume(
            ServerLevel level, LiftSpec spec)
    {
        for (int y = spec.lower().walkY() - 1;
             y <= spec.upper().walkY() + CABIN_HEIGHT - 1; y++)
        {
            for (int dx = -CABIN_RADIUS; dx <= CABIN_RADIUS; dx++)
            {
                for (int dz = -CABIN_RADIUS; dz <= CABIN_RADIUS; dz++)
                {
                    set(level, new BlockPos(
                            spec.lower().cabinCentre().getX() + dx, y,
                            spec.lower().cabinCentre().getZ() + dz), AIR);
                }
            }
        }
    }

    private static boolean isCabinDoorCell(
            BlockPos centre, BlockPos position, Direction exit)
    {
        int forward = (position.getX() - centre.getX())
                * exit.getStepX()
                + (position.getZ() - centre.getZ())
                * exit.getStepZ();
        Direction lateral = exit.getClockWise();
        int side = (position.getX() - centre.getX())
                * lateral.getStepX()
                + (position.getZ() - centre.getZ())
                * lateral.getStepZ();
        return forward == CABIN_DOOR_DISTANCE
                && Math.abs(side) <= CABIN_DOOR_HALF_WIDTH;
    }

    private static boolean cabinFloorPresent(
            ServerLevel level, BlockPos centre)
    {
        for (int dx = -CABIN_RADIUS; dx <= CABIN_RADIUS; dx++)
        {
            for (int dz = -CABIN_RADIUS; dz <= CABIN_RADIUS; dz++)
            {
                if (!level.getBlockState(
                        centre.offset(dx, -1, dz))
                        .equals(CABIN_FLOOR))
                {
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * A floor alone is not evidence of a usable R28 cabin.  The abandoned
     * entity-cabin migration often left its temporary landing deck in the
     * same 5x5 footprint, so the old check accepted a room with missing walls,
     * roof or controls.  Verify the small authoritative shell before deciding
     * that rollback has already completed.
     */
    private static boolean legacyCabinPresent(
            ServerLevel level, BlockPos centre, Direction exit,
            boolean doorOpen)
    {
        if (!cabinFloorPresent(level, centre))
        {
            return false;
        }
        Direction controlSide = exit.getClockWise();
        BlockPos controlBacking = centre.relative(
                controlSide, CABIN_RADIUS).above(1);
        for (int dx = -CABIN_RADIUS; dx <= CABIN_RADIUS; dx++)
        {
            for (int dz = -CABIN_RADIUS; dz <= CABIN_RADIUS; dz++)
            {
                if (!level.getBlockState(centre.offset(
                        dx, CABIN_HEIGHT - 1, dz)).equals(CABIN_ROOF))
                {
                    return false;
                }
                if (Math.abs(dx) != CABIN_RADIUS
                        && Math.abs(dz) != CABIN_RADIUS)
                {
                    continue;
                }
                for (int dy = 0; dy < CABIN_HEIGHT - 1; dy++)
                {
                    BlockPos position = centre.offset(dx, dy, dz);
                    boolean doorCell = isCabinDoorCell(
                            centre, position, exit) && dy < DOOR_HEIGHT;
                    BlockState expected;
                    if (position.equals(controlBacking)
                            || position.equals(controlBacking.above()))
                    {
                        expected = CABIN_PANEL;
                    }
                    else
                    {
                        expected = doorCell && !doorOpen
                                ? CABIN_DOOR
                                : doorCell ? AIR : CABIN_WALL;
                    }
                    if (!level.getBlockState(position).equals(expected))
                    {
                        return false;
                    }
                }
            }
        }
        BlockPos lower = interiorButtonPosition(centre, exit, false);
        BlockPos upper = interiorButtonPosition(centre, exit, true);
        return level.getBlockState(lower).getBlock() instanceof ButtonBlock
                && level.getBlockState(upper).getBlock()
                instanceof ButtonBlock;
    }

    private static boolean insideCabinBounds(
            BlockPos position, BlockPos centre)
    {
        return Math.abs(position.getX() - centre.getX()) <= CABIN_RADIUS
                && Math.abs(position.getZ() - centre.getZ())
                <= CABIN_RADIUS
                && position.getY() >= centre.getY() - 1
                && position.getY() < centre.getY() + CABIN_HEIGHT;
    }

    private static boolean isCabinOwnedState(BlockState state)
    {
        return state.equals(CABIN_FLOOR)
                || state.equals(CABIN_WALL)
                || state.equals(CABIN_ROOF)
                || state.equals(CABIN_PANEL)
                || state.equals(CABIN_DOOR)
                || state.getBlock() instanceof ButtonBlock;
    }

    private static BlockState wallButton(Direction facing)
    {
        return Blocks.POLISHED_BLACKSTONE_BUTTON.defaultBlockState()
                .setValue(ButtonBlock.FACE, AttachFace.WALL)
                .setValue(ButtonBlock.FACING, facing);
    }

    private static void setIfReplaceable(
            ServerLevel level, BlockPos position, BlockState state)
    {
        BlockState current = level.getBlockState(position);
        if (current.isAir() || isCabinOwnedState(current)
                || current.is(Blocks.STONE_BUTTON)
                || current.is(Blocks.CYAN_CONCRETE))
        {
            set(level, position, state);
        }
    }

    private static void set(
            ServerLevel level, BlockPos position, BlockState state)
    {
        if (!level.getBlockState(position).equals(state))
        {
            level.setBlock(position, state, UPDATE);
        }
    }

    private static void fault(
            ServerLevel level, LiftSpec spec, LiftRuntime runtime,
            RuntimeData data, String reason)
    {
        runtime.mode = Mode.FAULT;
        runtime.fault = reason;
        runtime.phaseTicks = 0;
        closeAllLandingDoors(level, spec);
        setCabinDoor(level, spec.centreAt(runtime.currentY),
                runtime.cabinExit, false);
        data.markDirty();
        ProjectSeele.LOGGER.error(
                "S20 physical lift {} fail-closed: {}",
                spec.id(), reason);
    }

    private static void message(
            ServerPlayer player, String text, ChatFormatting colour)
    {
        player.displayClientMessage(
                Component.literal(text).withStyle(colour), true);
    }

    private static void addFailure(
            List<String> failures, String failure)
    {
        if (failures.size() < 24)
        {
            failures.add(failure);
        }
    }

    public record Landing(
            String label, BlockPos cabinCentre, Direction exit)
    {
        public Landing
        {
            if (label == null || label.isBlank())
            {
                throw new IllegalArgumentException(
                        "Lift landing label cannot be empty");
            }
            Objects.requireNonNull(cabinCentre, "cabinCentre");
            Objects.requireNonNull(exit, "exit");
            if (exit.getAxis() == Direction.Axis.Y)
            {
                throw new IllegalArgumentException(
                        "Lift landing exit must be horizontal");
            }
        }

        public int walkY()
        {
            return this.cabinCentre.getY();
        }
    }

    public record LiftSpec(
            String id, Landing lower, Landing upper)
    {
        public LiftSpec
        {
            if (id == null || id.isBlank())
            {
                throw new IllegalArgumentException(
                        "Physical lift id cannot be empty");
            }
            Objects.requireNonNull(lower, "lower");
            Objects.requireNonNull(upper, "upper");
            if (lower.walkY() >= upper.walkY())
            {
                throw new IllegalArgumentException(
                        "Physical lift lower stop must be below upper stop");
            }
            if (lower.cabinCentre().getX()
                    != upper.cabinCentre().getX()
                    || lower.cabinCentre().getZ()
                    != upper.cabinCentre().getZ())
            {
                throw new IllegalArgumentException(
                        "Physical lift stops must share one vertical axis");
            }
        }

        public BlockPos centreAt(int walkY)
        {
            return new BlockPos(this.lower.cabinCentre().getX(), walkY,
                    this.lower.cabinCentre().getZ());
        }

        public Landing landingAt(int walkY)
        {
            if (walkY == this.lower.walkY())
            {
                return this.lower;
            }
            return walkY == this.upper.walkY() ? this.upper : null;
        }

        public String fingerprint()
        {
            return this.lower.cabinCentre().asLong() + ":"
                    + this.lower.exit().name() + ":"
                    + this.upper.cabinCentre().asLong() + ":"
                    + this.upper.exit().name();
        }
    }

    public record PreflightResult(
            boolean safe, List<String> failures) {}

    private enum Mode
    {
        IDLE_OPEN,
        CLOSING,
        MOVING,
        OPENING,
        FAULT
    }

    private static final class LiftRuntime
    {
        private final String fingerprint;
        private Mode mode;
        private int currentY;
        private int targetY;
        private int phaseTicks;
        private Direction cabinExit;
        private String fault;
        private UUID cabinUuid;
        private int cabinRevision;
        private int entityMissingTicks;
        private long motionEpoch;

        private LiftRuntime(
                String fingerprint, Mode mode, int currentY,
                int targetY, int phaseTicks, Direction cabinExit,
                String fault, UUID cabinUuid, int cabinRevision,
                int entityMissingTicks, long motionEpoch)
        {
            this.fingerprint = fingerprint;
            this.mode = mode;
            this.currentY = currentY;
            this.targetY = targetY;
            this.phaseTicks = phaseTicks;
            this.cabinExit = cabinExit;
            this.fault = fault;
            this.cabinUuid = cabinUuid;
            this.cabinRevision = cabinRevision;
            this.entityMissingTicks = Math.max(0, entityMissingTicks);
            this.motionEpoch = Math.max(0L, motionEpoch);
        }

        private static LiftRuntime installed(LiftSpec spec)
        {
            return new LiftRuntime(spec.fingerprint(), Mode.IDLE_OPEN,
                    spec.lower().walkY(), spec.lower().walkY(), 0,
                    spec.lower().exit(), "", null, 0, 0, 0L);
        }

        private static LiftRuntime recovered(
                LiftSpec spec, Landing landing)
        {
            return new LiftRuntime(spec.fingerprint(), Mode.IDLE_OPEN,
                    landing.walkY(), landing.walkY(), 0,
                    landing.exit(), "", null, 0, 0, 0L);
        }

        private static LiftRuntime load(CompoundTag tag)
        {
            return new LiftRuntime(
                    tag.getString("Fingerprint"),
                    Mode.valueOf(tag.getString("Mode")),
                    tag.getInt("CurrentY"),
                    tag.getInt("TargetY"),
                    tag.getInt("PhaseTicks"),
                    Direction.valueOf(tag.getString("CabinExit")),
                    tag.getString("Fault"),
                    tag.hasUUID("CabinUuid")
                            ? tag.getUUID("CabinUuid") : null,
                    tag.getInt("CabinRevision"),
                    tag.getInt("EntityMissingTicks"),
                    tag.getLong("MotionEpoch"));
        }

        private CompoundTag save()
        {
            CompoundTag tag = new CompoundTag();
            tag.putString("Fingerprint", this.fingerprint);
            tag.putString("Mode", this.mode.name());
            tag.putInt("CurrentY", this.currentY);
            tag.putInt("TargetY", this.targetY);
            tag.putInt("PhaseTicks", this.phaseTicks);
            tag.putString("CabinExit", this.cabinExit.name());
            tag.putString("Fault", this.fault);
            if (this.cabinUuid != null)
            {
                tag.putUUID("CabinUuid", this.cabinUuid);
            }
            tag.putInt("CabinRevision", this.cabinRevision);
            tag.putInt("EntityMissingTicks", this.entityMissingTicks);
            tag.putLong("MotionEpoch", this.motionEpoch);
            return tag;
        }
    }

    private static final class RuntimeData extends SavedData
    {
        private static final String DATA_NAME =
                "projectseele_s20_physical_elevators_v1";
        private static final int VERSION = 4;
        private final Map<String, LiftRuntime> lifts =
                new LinkedHashMap<>();

        private static RuntimeData get(ServerLevel level)
        {
            return level.getDataStorage().computeIfAbsent(
                    RuntimeData::load, RuntimeData::new, DATA_NAME);
        }

        private static RuntimeData load(CompoundTag root)
        {
            RuntimeData data = new RuntimeData();
            int version = root.getInt("Version");
            if (version < 1 || version > VERSION)
            {
                return data;
            }
            ListTag list = root.getList("Lifts", Tag.TAG_COMPOUND);
            for (int index = 0; index < list.size(); index++)
            {
                CompoundTag entry = list.getCompound(index);
                String id = entry.getString("Id");
                if (id.isBlank())
                {
                    continue;
                }
                try
                {
                    data.lifts.put(id,
                            LiftRuntime.load(entry.getCompound("Runtime")));
                }
                catch (IllegalArgumentException exception)
                {
                    ProjectSeele.LOGGER.error(
                            "Ignoring malformed S20 lift state {}", id,
                            exception);
                }
            }
            return data;
        }

        private Optional<LiftRuntime> find(String id)
        {
            return Optional.ofNullable(this.lifts.get(id));
        }

        private void put(String id, LiftRuntime runtime)
        {
            this.lifts.put(id, runtime);
            this.setDirty();
        }

        private void markDirty()
        {
            this.setDirty();
        }

        @Override
        public CompoundTag save(CompoundTag root)
        {
            root.putInt("Version", VERSION);
            ListTag list = new ListTag();
            for (Map.Entry<String, LiftRuntime> entry
                    : this.lifts.entrySet())
            {
                CompoundTag lift = new CompoundTag();
                lift.putString("Id", entry.getKey());
                lift.put("Runtime", entry.getValue().save());
                list.add(lift);
            }
            root.put("Lifts", list);
            return root;
        }
    }
}
