package com.projectseele.world;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Locale;
import java.util.UUID;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.registry.ModEntities;
import com.projectseele.visual.GeoFrontCommands;
import com.projectseele.world.EvaFleetSavedData.FleetEntry;
import com.projectseele.world.EvaFleetSavedData.Phase;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.world.ForgeChunkManager;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Persistent wet-cage, rail-transfer, launch and recovery state machine. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class EvaLogisticsDirector
{
    private static final int FLUID_LAYER_TICKS = 4;
    private static final int BRIDGE_RETRACTION_TICKS = 40;
    private static final int PLUG_LOCK_TICKS = 60;
    private static final int HORIZONTAL_TRANSFER_TICKS = 160;
    private static final double VERTICAL_BLOCKS_PER_TICK = 2.0D;
    private static final double RECOVERY_RADIUS = 10.0D;
    private static final double RECOVERY_MAX_SPEED_SQR = 0.0025D;
    private static final int MAP_RADIUS = 400;
    private static final int ROUTE_CHUNK_MARGIN = 16;
    private static final Map<UUID, Boolean> ROUTE_TICKET_STATE = new HashMap<>();
    private static final Map<UUID, Long> PHASE_STARTED_AT = new HashMap<>();
    private static final Map<UUID, Integer> LAST_ENTITY_TICK = new HashMap<>();
    private static final Map<UUID, Integer> DORMANT_LAUNCH_TICKS = new HashMap<>();

    private EvaLogisticsDirector() {}

    /** Enforces the world-global UUID contract as entities enter loaded chunks. */
    public static boolean validateCanonical(EvaUnit01Entity unit)
    {
        if (!(unit.level() instanceof ServerLevel level))
        {
            return true;
        }
        int variant = unit.getUnitVariant();
        EvaFleetSavedData data = EvaFleetSavedData.get(level.getServer());
        FleetEntry current = data.entry(variant).orElse(null);
        if (current == null)
        {
            BlockPos bed = EvaHangarBuilder.hangarBed(
                    IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant);
            boolean parked = isAtAssignedHangar(level, unit, variant);
            data.put(variant, new FleetEntry(unit.getUUID(),
                    parked ? Phase.PARKED : Phase.DEPLOYED, 0,
                    parked ? bed.getZ() : Mth.floor(unit.getZ()),
                    parked ? EvaHangarBuilder.LCL_SHOULDER_LAYERS : 0));
            ProjectSeele.LOGGER.info(
                    "Claimed canonical EVA-0{} {} phase={} dimension={}",
                    variant, unit.getStringUUID(),
                    parked ? Phase.PARKED : Phase.DEPLOYED,
                    level.dimension().location());
            return true;
        }
        boolean accepted = current.canonicalId().equals(unit.getUUID());
        if (!accepted)
        {
            ProjectSeele.LOGGER.warn(
                    "Discarding non-canonical EVA-0{} duplicate {} (canonical={})",
                    variant, unit.getStringUUID(), current.canonicalId());
        }
        return accepted;
    }

    /** Migrates an old three-airframe map into the new canonical wet cages. */
    public static List<EvaUnit01Entity> ensureFleet(ServerLevel level)
    {
        EvaHangarBuilder.ensure(level, IntegratedNervMapBuilder.GEOFRONT_ORIGIN);
        loadFleetStations(level);
        EvaFleetSavedData data = EvaFleetSavedData.get(level.getServer());
        List<EvaUnit01Entity> result = new ArrayList<>(3);
        List<EvaUnit01Entity> loaded = loadedFleet(level);
        for (int variant = 0; variant < 3; variant++)
        {
            final int wantedVariant = variant;
            List<EvaUnit01Entity> candidates = loaded.stream()
                    .filter(unit -> unit.getUnitVariant() == wantedVariant)
                    .toList();
            UUID canonical = data.canonicalId(variant).orElse(null);
            EvaUnit01Entity globalCanonical = canonical == null ? null
                    : canonicalAnywhere(level.getServer(), canonical);
            EvaUnit01Entity unit = globalCanonical != null
                    && globalCanonical.level() == level ? globalCanonical : null;
            if (unit == null && canonical == null && !candidates.isEmpty())
            {
                BlockPos bed = EvaHangarBuilder.hangarBed(
                        IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant);
                unit = candidates.stream().min(Comparator.comparingDouble(
                        candidate -> candidate.distanceToSqr(bed.getCenter()))).orElse(null);
                if (unit != null)
                {
                    canonical = unit.getUUID();
                    Phase initialPhase = isAtAssignedHangar(level, unit, variant)
                            && !unit.isVehicle() && !unit.isLaunchSequenceActive()
                            ? Phase.PARKED : Phase.DEPLOYED;
                    data.put(variant, new FleetEntry(canonical, initialPhase, 0,
                            bed.getZ(), initialPhase == Phase.PARKED
                            ? EvaHangarBuilder.LCL_SHOULDER_LAYERS : 0));
                }
            }
            FleetEntry persisted = data.entry(variant).orElse(null);
            if (unit == null && globalCanonical == null && canonical != null
                    && persisted != null && persisted.phase() == Phase.PARKED)
            {
                // The hangar chunk was loaded above, so a PARKED canonical
                // that is still absent cannot merely be in an unloaded chunk.
                // This specifically repairs UUIDs left behind by old visual
                // cleanup code without ever cloning a deployed/in-transit EVA.
                ProjectSeele.LOGGER.warn(
                        "Repairing missing PARKED canonical EVA-0{} {} in its wet cage",
                        variant, canonical);
                unit = createParkedCanonical(level, data, variant);
                loaded.add(unit);
                canonical = unit.getUUID();
            }
            if (unit == null && canonical == null)
            {
                unit = createParkedCanonical(level, data, variant);
                loaded.add(unit);
            }
            if (unit == null)
            {
                // A deployed canonical may be in an unloaded chunk. Never
                // clone it merely to satisfy a local readiness screen.
                continue;
            }
            for (EvaUnit01Entity duplicate : candidates)
            {
                if (duplicate != unit)
                {
                    duplicate.discard();
                }
            }
            FleetEntry entry = data.entry(variant).orElseThrow();
            if (entry.phase() == Phase.PARKED && !unit.isVehicle())
            {
                BlockPos bed = EvaHangarBuilder.hangarBed(
                        IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant);
                placeAt(unit, bed);
                unit.setSortieDestination(level.dimension(),
                        IntegratedNervMapBuilder.surfaceLiftBed(variant));
                unit.setSortieParkingBed(bed);
                unit.setNervLogisticsLocked(true);
                EvaHangarBuilder.setBoardingBridgeExtension(level,
                        IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant,
                        EvaHangarBuilder.BRIDGE_SEGMENTS);
                EntryPlugDirector.ensureSuspended(level, variant, unit);
            }
            result.add(unit);
        }
        return result;
    }

    private static EvaUnit01Entity createParkedCanonical(
            ServerLevel level, EvaFleetSavedData data, int variant)
    {
        EvaUnit01Entity unit = createUnit(level, variant);
        if (unit == null)
        {
            throw new IllegalStateException("Failed to create canonical EVA-0" + variant);
        }
        BlockPos bed = EvaHangarBuilder.hangarBed(
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant);
        placeAt(unit, bed);
        unit.setPersistenceRequired();
        data.put(variant, new FleetEntry(unit.getUUID(), Phase.PARKED,
                0, bed.getZ(), EvaHangarBuilder.LCL_SHOULDER_LAYERS));
        if (!level.addFreshEntity(unit))
        {
            throw new IllegalStateException("Server rejected canonical EVA-0" + variant);
        }
        return unit;
    }

    public static ActionResult requestPrepare(ServerLevel level, int variant)
    {
        EvaUnit01Entity unit = canonical(level, variant);
        FleetEntry entry = entry(level, variant);
        if (unit == null || entry == null)
        {
            return new ActionResult(false, label(variant) + " is not loaded; use force reset.");
        }
        if (entry.phase() != Phase.PARKED)
        {
            return new ActionResult(false, label(variant) + " is " + entry.phase() + ".");
        }
        EntryPlugDirector.ensureSuspended(level, variant, unit);
        if (!EntryPlugDirector.hasBoardedPilot(level, variant, unit))
        {
            return new ActionResult(false, label(variant)
                    + " pilot must board the suspended external entry plug first.");
        }
        unit.clearSortieDestination();
        unit.setNervLogisticsLocked(true);
        int lcl = EvaHangarBuilder.lclLevel(level,
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant);
        put(level, variant, entry.withPhase(Phase.BRIDGE_RETRACTING, 0,
                EvaHangarBuilder.hangarZ(IntegratedNervMapBuilder.GEOFRONT_ORIGIN), lcl));
        level.playSound(null, unit.blockPosition(), SoundEvents.PISTON_CONTRACT,
                SoundSource.BLOCKS, 2.5F, 0.62F);
        return new ActionResult(true, label(variant)
                + " boarding bridge retraction and entry-plug insertion started.");
    }
    public static ActionResult requestRecovery(ServerLevel level, int variant)
    {
        EvaUnit01Entity unit = canonical(level, variant);
        FleetEntry entry = entry(level, variant);
        if (unit == null || entry == null)
        {
            return new ActionResult(false, label(variant) + " is not loaded; use force reset.");
        }
        if (entry.phase() != Phase.DEPLOYED)
        {
            return new ActionResult(false, label(variant) + " is " + entry.phase()
                    + "; recovery requires DEPLOYED.");
        }
        BlockPos surface = IntegratedNervMapBuilder.surfaceLiftBed(variant);
        double dx = unit.getX() - (surface.getX() + 0.5D);
        double dz = unit.getZ() - (surface.getZ() + 0.5D);
        double horizontal = Math.sqrt(dx * dx + dz * dz);
        if (horizontal > RECOVERY_RADIUS
                || Math.abs(unit.getY() - (surface.getY() + 1.0D)) > 8.0D)
        {
            return new ActionResult(false, label(variant)
                    + " must stand on its own Tokyo-3 recovery deck.");
        }
        if (unit.getDeltaMovement().lengthSqr() > RECOVERY_MAX_SPEED_SQR)
        {
            return new ActionResult(false, label(variant)
                    + " must be motionless before surface command authorizes recovery.");
        }
        unit.prepareForNervRecovery();
        unit.setNervLogisticsLocked(true);
        unit.moveOnNervCarrier(surface.getX() + 0.5D,
                surface.getY() + 1.0D, surface.getZ() + 0.5D,
                EvaUnit01Entity.SILO_BAY_YAW);
        put(level, variant, entry.withPhase(Phase.DESCENDING, 0,
                surface.getY(), 0));
        level.playSound(null, surface, SoundEvents.PISTON_CONTRACT,
                SoundSource.BLOCKS, 4.0F, 0.48F);
        return new ActionResult(true, label(variant)
                + " recovery deck locked; physical descent started.");
    }

    public static EvaUnit01Entity forceReset(ServerLevel level, int variant)
    {
        MinecraftServer server = level.getServer();
        for (ServerLevel dimension : server.getAllLevels())
        {
            for (EvaUnit01Entity unit : loadedFleet(dimension))
            {
                if (unit.getUnitVariant() == variant)
                {
                    for (Entity passenger : List.copyOf(unit.getPassengers()))
                    {
                        passenger.stopRiding();
                        if (passenger instanceof ServerPlayer player)
                        {
                            BlockPos gallery = IntegratedNervMapBuilder.GEOFRONT_ORIGIN.offset(
                                    IntegratedNervMapBuilder.LIFT_X[variant],
                                    EvaHangarBuilder.GALLERY_Y + 1,
                                    EvaHangarBuilder.GALLERY_Z + 2);
                            player.teleportTo(level, gallery.getX() + 0.5D,
                                    gallery.getY(), gallery.getZ() + 0.5D,
                                    180.0F, 0.0F);
                        }
                    }
                    NervCarrierVisuals.remove(dimension, unit);
                    unit.discard();
                }
            }
        }
        BlockPos recoveryDeck = IntegratedNervMapBuilder.surfaceLiftBed(variant);
        setVerticalCarrier(level, recoveryDeck, recoveryDeck.getY(), true);
        EvaUnit01Entity replacement = createUnit(level, variant);
        if (replacement == null)
        {
            throw new IllegalStateException("Failed to reset " + label(variant));
        }
        BlockPos bed = EvaHangarBuilder.hangarBed(
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant);
        placeAt(replacement, bed);
        replacement.setPersistenceRequired();
        replacement.setHealth(replacement.getMaxHealth());
        replacement.setNervLogisticsLocked(true);
        EvaFleetSavedData.get(server).put(variant, new FleetEntry(
                replacement.getUUID(), Phase.PARKED, 0, bed.getZ(),
                EvaHangarBuilder.LCL_SHOULDER_LAYERS));
        if (!level.addFreshEntity(replacement))
        {
            throw new IllegalStateException("Server rejected reset " + label(variant));
        }
        EntryPlugDirector.reset(level, variant, replacement);
        EvaHangarBuilder.setBoardingBridgeExtension(level,
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant,
                EvaHangarBuilder.BRIDGE_SEGMENTS);
        EvaHangarBuilder.setGate(level, IntegratedNervMapBuilder.GEOFRONT_ORIGIN,
                variant, false);
        EvaHangarBuilder.setLclLevel(level, IntegratedNervMapBuilder.GEOFRONT_ORIGIN,
                variant, EvaHangarBuilder.LCL_SHOULDER_LAYERS);
        EvaHangarBuilder.restoreStaticCarrier(level,
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant, bed);
        replacement.setSortieDestination(level.dimension(),
                IntegratedNervMapBuilder.surfaceLiftBed(variant));
        replacement.setSortieParkingBed(bed);
        ProjectSeele.LOGGER.warn("NERV forced canonical reset: {} uuid={} bed={}",
                label(variant), replacement.getStringUUID(), bed.toShortString());
        return replacement;
    }

    public static Status status(ServerLevel level, int variant)
    {
        FleetEntry entry = entry(level, variant);
        EvaUnit01Entity unit = canonical(level, variant);
        return entry == null
                ? new Status(variant, "UNREGISTERED", false, null, 0, 0)
                : new Status(variant, entry.phase().name(), unit != null,
                        entry.canonicalId(), entry.lclLayers(), entry.ticks());
    }

    /** Read-only canonical lookup shared by training and command systems. */
    public static EvaUnit01Entity canonicalUnit(ServerLevel level, int variant)
    {
        return canonical(level, variant);
    }

    /** Keeps deterministic screenshot fixtures out of the live parking loop. */
    public static void markDeployedForVisual(ServerLevel level,
                                             EvaUnit01Entity unit)
    {
        int variant = unit.getUnitVariant();
        FleetEntry current = entry(level, variant);
        if (current == null || !current.canonicalId().equals(unit.getUUID()))
        {
            EvaFleetSavedData.get(level.getServer()).put(variant,
                    new FleetEntry(unit.getUUID(), Phase.DEPLOYED, 0,
                            unit.blockPosition().getY(), 0));
        }
        else
        {
            put(level, variant, current.withPhase(Phase.DEPLOYED,
                    0, unit.blockPosition().getY(), 0));
        }
        unit.clearSortieDestination();
        unit.setNervLogisticsLocked(false);
    }
    /** Hangar preparation controls plus three supported Tokyo-3 recovery keys. */
    public static boolean handleUse(ServerPlayer player, BlockPos position)
    {
        if (!player.serverLevel().dimension().equals(GeoFrontCommands.GEOFRONT))
        {
            return false;
        }
        for (int variant = 0; variant < 3; variant++)
        {
            if (!Tokyo3RecoveryConsole.controlPosition(
                    IntegratedNervMapBuilder.TOKYO3_ORIGIN, variant)
                    .equals(position))
            {
                continue;
            }
            ActionResult result = requestRecovery(player.serverLevel(), variant);
            player.displayClientMessage(Component.literal("[TOKYO-3 RECOVERY] "
                    + result.message()).withStyle(result.accepted()
                    ? ChatFormatting.GREEN : ChatFormatting.RED), false);
            return true;
        }

        BlockPos origin = IntegratedNervMapBuilder.GEOFRONT_ORIGIN;
        for (int variant = 0; variant < 3; variant++)
        {
            for (boolean prepare : new boolean[] {true, false})
            {
                if (!EvaHangarBuilder.controlPosition(origin, variant, prepare)
                        .equals(position))
                {
                    continue;
                }
                handleHangarControl(player, variant, prepare);
                return true;
            }
        }
        return false;
    }

    /** The cyan underground key is deliberately read-only; recovery authority
     * lives exclusively at the supported Tokyo-3 surface command post. */
    private static void handleHangarControl(ServerPlayer player, int variant,
                                            boolean prepare)
    {
        if (prepare)
        {
            ActionResult result = requestPrepare(player.serverLevel(), variant);
            player.displayClientMessage(Component.literal("[NERV HANGAR] "
                    + result.message()).withStyle(result.accepted()
                    ? ChatFormatting.GREEN : ChatFormatting.RED), false);
            return;
        }
        Status snapshot = status(player.serverLevel(), variant);
        player.displayClientMessage(Component.literal(String.format(Locale.ROOT,
                "[NERV HANGAR STATUS] %s phase=%s loaded=%s LCL=%d/%d ticks=%d",
                label(variant), snapshot.phase(), snapshot.loaded(),
                snapshot.lclLayers(), EvaHangarBuilder.LCL_SHOULDER_LAYERS,
                snapshot.ticks())).withStyle(ChatFormatting.AQUA), false);
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END)
        {
            return;
        }
        ServerLevel level = event.getServer().getLevel(GeoFrontCommands.GEOFRONT);
        if (level == null || !IntegratedNervMapBuilder.isInstalled(level)
                || !EvaHangarBuilder.runtimeInfrastructurePresent(level,
                        IntegratedNervMapBuilder.GEOFRONT_ORIGIN))
        {
            return;
        }
        for (int variant = 0; variant < 3; variant++)
        {
            tickUnit(level, variant);
        }
    }

    private static void tickUnit(ServerLevel level, int variant)
    {
        FleetEntry entry = entry(level, variant);
        if (entry == null)
        {
            return;
        }
        boolean active = entry.phase() != Phase.PARKED
                && entry.phase() != Phase.DEPLOYED;
        maintainRouteChunks(level, variant, entry.canonicalId(), active);
        EvaUnit01Entity unit = canonical(level, variant);
        if (unit == null || !unit.isAlive())
        {
            if (active && entry.ticks() % 40 == 0)
            {
                ProjectSeele.LOGGER.warn(
                        "NERV EVA-0{} logistics waiting for canonical entity: phase={} ticks={} uuid={}",
                        variant, entry.phase(), entry.ticks(), entry.canonicalId());
            }
            return;
        }
        maintainDormantLaunch(unit, entry);
        if (active && entry.ticks() > 0 && entry.ticks() % 40 == 0)
        {
            long started = PHASE_STARTED_AT.getOrDefault(
                    entry.canonicalId(), System.nanoTime());
            ProjectSeele.LOGGER.info(
                    "NERV EVA-0{} logistics progress: phase={} ticks={} elapsedMs={} carrier={} lcl={}",
                    variant, entry.phase(), entry.ticks(),
                    (System.nanoTime() - started) / 1_000_000L,
                    entry.carrier(), entry.lclLayers());
        }
        BlockPos origin = IntegratedNervMapBuilder.GEOFRONT_ORIGIN;
        BlockPos hangar = EvaHangarBuilder.hangarBed(origin, variant);
        BlockPos silo = IntegratedNervMapBuilder.lowerLiftBed(variant);
        BlockPos surface = IntegratedNervMapBuilder.surfaceLiftBed(variant);
        switch (entry.phase())
        {
            case PARKED ->
            {
                unit.setNervLogisticsLocked(true);
                unit.setSortieDestination(level.dimension(), surface);
                unit.setSortieParkingBed(hangar);
                EntryPlugDirector.ensureSuspended(level, variant, unit);
            }
            case BRIDGE_RETRACTING ->
            {
                unit.setNervLogisticsLocked(true);
                int ticks = entry.ticks() + 1;
                if (ticks % 5 == 0 || ticks >= BRIDGE_RETRACTION_TICKS)
                {
                    int remaining = EvaHangarBuilder.BRIDGE_SEGMENTS
                            - Mth.ceil(ticks * EvaHangarBuilder.BRIDGE_SEGMENTS
                            / (double) BRIDGE_RETRACTION_TICKS);
                    EvaHangarBuilder.setBoardingBridgeExtension(level, origin,
                            variant, Math.max(0, remaining));
                }
                if (ticks >= BRIDGE_RETRACTION_TICKS)
                {
                    EntryPlugDirector.beginInsertion(level, variant, unit);
                    put(level, variant, entry.withPhase(Phase.PLUG_INSERTING,
                            0, entry.carrier(), entry.lclLayers()));
                    unit.playSound(SoundEvents.PISTON_EXTEND, 2.4F, 0.54F);
                }
                else
                {
                    put(level, variant, entry.withPhase(
                            Phase.BRIDGE_RETRACTING, ticks,
                            entry.carrier(), entry.lclLayers()));
                }
            }
            case PLUG_INSERTING ->
            {
                unit.setNervLogisticsLocked(true);
                int ticks = entry.ticks() + 1;
                boolean seated = EntryPlugDirector.tickInsertion(level,
                        variant, unit, ticks);
                if (seated)
                {
                    put(level, variant, entry.withPhase(Phase.PLUG_LOCKING,
                            0, entry.carrier(), entry.lclLayers()));
                    unit.playSound(SoundEvents.IRON_DOOR_CLOSE, 2.8F, 0.66F);
                }
                else if (ticks >= EntryPlugDirector.INSERTION_TICKS
                        && !EntryPlugDirector.hasBoardedPilot(level,
                        variant, unit))
                {
                    EvaHangarBuilder.setBoardingBridgeExtension(level,
                            origin, variant, EvaHangarBuilder.BRIDGE_SEGMENTS);
                    EntryPlugDirector.ensureSuspended(level, variant, unit);
                    put(level, variant, entry.withPhase(Phase.PARKED, 0,
                            hangar.getZ(), entry.lclLayers()));
                }
                else
                {
                    put(level, variant, entry.withPhase(Phase.PLUG_INSERTING,
                            ticks, entry.carrier(), entry.lclLayers()));
                }
            }
            case PLUG_LOCKING ->
            {
                unit.setNervLogisticsLocked(true);
                int ticks = entry.ticks() + 1;
                if (ticks >= PLUG_LOCK_TICKS)
                {
                    put(level, variant, entry.withPhase(Phase.DRAINING, 0,
                            entry.carrier(), entry.lclLayers()));
                }
                else
                {
                    put(level, variant, entry.withPhase(Phase.PLUG_LOCKING,
                            ticks, entry.carrier(), entry.lclLayers()));
                }
            }
            case DRAINING ->
            {
                unit.setNervLogisticsLocked(true);
                int ticks = entry.ticks() + 1;
                int lcl = entry.lclLayers();
                if (ticks % FLUID_LAYER_TICKS == 0 && lcl > 0)
                {
                    EvaHangarBuilder.setLclLayer(level, origin, variant, lcl, false);
                    lcl--;
                }
                if (lcl <= 0)
                {
                    EvaHangarBuilder.setGate(level, origin, variant, true);
                    EvaHangarBuilder.restoreStaticCarrier(level, origin, variant, hangar);
                    put(level, variant, entry.withPhase(Phase.TO_SILO,
                            0, hangar.getZ(), 0));
                    unit.playSound(SoundEvents.IRON_DOOR_OPEN, 2.8F, 0.62F);
                }
                else
                {
                    put(level, variant, entry.withPhase(Phase.DRAINING,
                            ticks, entry.carrier(), lcl));
                }
            }
            case TO_SILO -> tickHorizontal(level, variant, unit, entry,
                    hangar, silo, true);
            case SILO_READY ->
            {
                unit.setNervLogisticsLocked(true);
                unit.setSortieDestination(level.dimension(), surface);
                unit.setSortieParkingBed(silo);
                if (unit.isLaunchSequenceActive())
                {
                    return;
                }
                if (unit.getY() > silo.getY() + 64.0D)
                {
                    unit.setNervLogisticsLocked(false);
                    put(level, variant, entry.withPhase(Phase.DEPLOYED,
                            0, surface.getY(), 0));
                }
            }
            case DEPLOYED ->
            {
                double dx = unit.getX() - (surface.getX() + 0.5D);
                double dz = unit.getZ() - (surface.getZ() + 0.5D);
                boolean trainingStandby = unit.isTrainingPilotActive()
                        && dx * dx + dz * dz <= 2.25D
                        && Math.abs(unit.getY() - (surface.getY() + 1.0D)) <= 8.0D;
                if (trainingStandby)
                {
                    // A synthetic pilot has no real movement packets to hold
                    // the enormous chassis against mob AI and gravity. Treat
                    // its exact recovery-pad arrival as a stationary MAGI
                    // standby state until the surface console authorizes
                    // descent. Human pilots remain fully released.
                    unit.setNervLogisticsLocked(true);
                    unit.moveOnNervCarrier(surface.getX() + 0.5D,
                            surface.getY() + 1.0D, surface.getZ() + 0.5D,
                            EvaUnit01Entity.SILO_BAY_YAW);
                }
                else
                {
                    unit.setNervLogisticsLocked(false);
                }
            }
            case DESCENDING -> tickDescent(level, variant, unit, entry,
                    surface, silo);
            case TO_HANGAR -> tickHorizontal(level, variant, unit, entry,
                    silo, hangar, false);
            case FILLING ->
            {
                unit.setNervLogisticsLocked(true);
                int ticks = entry.ticks() + 1;
                int lcl = entry.lclLayers();
                if (ticks % FLUID_LAYER_TICKS == 0
                        && lcl < EvaHangarBuilder.LCL_SHOULDER_LAYERS)
                {
                    lcl++;
                    EvaHangarBuilder.setLclLayer(level, origin, variant, lcl, true);
                }
                if (lcl >= EvaHangarBuilder.LCL_SHOULDER_LAYERS)
                {
                    unit.setSortieDestination(level.dimension(), surface);
                    unit.setSortieParkingBed(hangar);
                    EvaHangarBuilder.setBoardingBridgeExtension(level, origin,
                            variant, EvaHangarBuilder.BRIDGE_SEGMENTS);
                    EntryPlugDirector.ensureSuspended(level, variant, unit);
                    put(level, variant, entry.withPhase(Phase.PARKED,
                            0, hangar.getZ(), lcl));
                    unit.playSound(SoundEvents.BEACON_ACTIVATE, 2.8F, 0.82F);
                }
                else
                {
                    put(level, variant, entry.withPhase(Phase.FILLING,
                            ticks, entry.carrier(), lcl));
                }
            }
        }
    }

    private static void tickHorizontal(ServerLevel level, int variant,
                                       EvaUnit01Entity unit, FleetEntry entry,
                                       BlockPos start, BlockPos end,
                                       boolean outbound)
    {
        int ticks = Math.min(HORIZONTAL_TRANSFER_TICKS, entry.ticks() + 1);
        double progress = ticks / (double) HORIZONTAL_TRANSFER_TICKS;
        double exactZ = Mth.lerp(progress, start.getZ(), end.getZ());
        int carrierZ = Mth.floor(exactZ + 0.5D);
        BlockPos origin = IntegratedNervMapBuilder.GEOFRONT_ORIGIN;
        if (entry.ticks() == 0)
        {
            EvaHangarBuilder.setCarrier(level, origin, variant,
                    start.getZ(), false);
        }
        NervCarrierVisuals.update(level, unit, start.getX() + 0.5D,
                start.getY(), exactZ + 0.5D);
        unit.setNervLogisticsLocked(true);
        unit.moveOnNervCarrier(start.getX() + 0.5D, start.getY() + 1.0D,
                exactZ + 0.5D, EvaUnit01Entity.SILO_BAY_YAW);
        if (ticks < HORIZONTAL_TRANSFER_TICKS)
        {
            put(level, variant, entry.withPhase(entry.phase(), ticks,
                    carrierZ, entry.lclLayers()));
            return;
        }
        // The final moving footprint is already centred on the station.
        // Repainting it as AIR and immediately rebuilding it doubled the
        // largest block update spike for no visible result.
        NervCarrierVisuals.remove(level, unit);
        EvaHangarBuilder.restoreStaticCarrier(level, origin, variant, end);
        unit.moveOnNervCarrier(end.getX() + 0.5D, end.getY() + 1.0D,
                end.getZ() + 0.5D, EvaUnit01Entity.SILO_BAY_YAW);
        if (outbound)
        {
            EvaHangarBuilder.setGate(level, origin, variant, false);
            unit.setSortieDestination(level.dimension(),
                    IntegratedNervMapBuilder.surfaceLiftBed(variant));
            unit.setSortieParkingBed(end);
            put(level, variant, entry.withPhase(Phase.SILO_READY,
                    0, end.getZ(), 0));
            unit.armPreparedLaunch(end);
            level.sendParticles(ParticleTypes.ELECTRIC_SPARK,
                    end.getX() + 0.5D, end.getY() + 1.2D, end.getZ() + 0.5D,
                    32, 4.0D, 0.5D, 4.0D, 0.05D);
        }
        else
        {
            EvaHangarBuilder.setGate(level, origin, variant, false);
            unit.setSortieDestination(level.dimension(),
                    IntegratedNervMapBuilder.surfaceLiftBed(variant));
            unit.setSortieParkingBed(end);
            put(level, variant, entry.withPhase(Phase.FILLING,
                    0, end.getZ(), 0));
        }
    }

    private static void tickDescent(ServerLevel level, int variant,
                                    EvaUnit01Entity unit, FleetEntry entry,
                                    BlockPos surface, BlockPos silo)
    {
        int distance = surface.getY() - silo.getY();
        int duration = Math.max(1, Mth.ceil(distance / VERTICAL_BLOCKS_PER_TICK));
        int ticks = Math.min(duration, entry.ticks() + 1);
        double progress = ticks / (double) duration;
        double exactY = Mth.lerp(progress, surface.getY(), silo.getY());
        int carrierY = Mth.floor(exactY + 0.5D);
        if (entry.ticks() == 0)
        {
            setVerticalCarrier(level, surface, surface.getY(), false);
        }
        NervCarrierVisuals.update(level, unit, surface.getX() + 0.5D,
                carrierY, surface.getZ() + 0.5D);
        unit.setNervLogisticsLocked(true);
        unit.moveOnNervCarrier(surface.getX() + 0.5D, exactY + 1.0D,
                surface.getZ() + 0.5D, EvaUnit01Entity.SILO_BAY_YAW);
        if (entry.carrier() >= surface.getY() - 34
                && carrierY < surface.getY() - 34)
        {
            setVerticalCarrier(level, surface, surface.getY(), true);
        }
        if (ticks < duration)
        {
            put(level, variant, entry.withPhase(Phase.DESCENDING,
                    ticks, carrierY, 0));
            return;
        }
        NervCarrierVisuals.remove(level, unit);
        EvaHangarBuilder.restoreStaticCarrier(level,
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant, silo);
        EvaHangarBuilder.setGate(level, IntegratedNervMapBuilder.GEOFRONT_ORIGIN,
                variant, true);
        unit.moveOnNervCarrier(silo.getX() + 0.5D, silo.getY() + 1.0D,
                silo.getZ() + 0.5D, EvaUnit01Entity.SILO_BAY_YAW);
        put(level, variant, entry.withPhase(Phase.TO_HANGAR,
                0, silo.getZ(), 0));
    }

    private static void setVerticalCarrier(ServerLevel level, BlockPos shaft,
                                           int y, boolean present)
    {
        for (int x = -5; x <= 5; x++)
        {
            for (int z = -5; z <= 5; z++)
            {
                BlockPos position = new BlockPos(shaft.getX() + x, y,
                        shaft.getZ() + z);
                if (present)
                {
                    boolean rim = Math.abs(x) == 5 || Math.abs(z) == 5;
                    level.setBlock(position, rim
                            ? net.minecraft.world.level.block.Blocks.IRON_BLOCK.defaultBlockState()
                            : net.minecraft.world.level.block.Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState(), 2);
                }
                else
                {
                    level.setBlock(position,
                            net.minecraft.world.level.block.Blocks.AIR.defaultBlockState(), 2);
                }
            }
        }
        if (present && y == shaft.getY())
        {
            level.setBlock(new BlockPos(shaft.getX(), y, shaft.getZ()),
                    net.minecraft.world.level.block.Blocks.LODESTONE.defaultBlockState(), 2);
        }
    }

    private static boolean isAtAssignedHangar(ServerLevel level,
                                               EvaUnit01Entity unit,
                                               int variant)
    {
        if (!level.dimension().equals(GeoFrontCommands.GEOFRONT))
        {
            return false;
        }
        BlockPos bed = EvaHangarBuilder.hangarBed(
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant);
        double horizontal = new Vec3(unit.getX(), 0.0D, unit.getZ())
                .distanceTo(new Vec3(bed.getX() + 0.5D, 0.0D,
                        bed.getZ() + 0.5D));
        return horizontal <= 12.0D
                && Math.abs(unit.getY() - (bed.getY() + 1.0D)) <= 8.0D;
    }

    private static EvaUnit01Entity canonicalAnywhere(MinecraftServer server,
                                                      UUID id)
    {
        for (ServerLevel dimension : server.getAllLevels())
        {
            Entity direct = dimension.getEntity(id);
            if (direct instanceof EvaUnit01Entity unit && unit.isAlive())
            {
                return unit;
            }
            for (EvaUnit01Entity unit : loadedFleet(dimension))
            {
                if (unit.getUUID().equals(id))
                {
                    return unit;
                }
            }
        }
        return null;
    }

    private static void maintainDormantLaunch(EvaUnit01Entity unit,
                                               FleetEntry entry)
    {
        UUID id = entry.canonicalId();
        if (entry.phase() != Phase.SILO_READY
                || !unit.isLaunchSequenceActive())
        {
            LAST_ENTITY_TICK.remove(id);
            DORMANT_LAUNCH_TICKS.remove(id);
            return;
        }
        int current = unit.tickCount;
        Integer previous = LAST_ENTITY_TICK.put(id, current);
        if (previous == null || previous != current)
        {
            int recovered = DORMANT_LAUNCH_TICKS.getOrDefault(id, 0);
            if (recovered > 0)
            {
                ProjectSeele.LOGGER.info(
                        "NERV dormant launch watchdog released: eva={} assistedTicks={}",
                        unit.getStringUUID(), recovered);
            }
            DORMANT_LAUNCH_TICKS.remove(id);
            return;
        }
        int assisted = DORMANT_LAUNCH_TICKS.merge(id, 1, Integer::sum);
        if (assisted == 1)
        {
            ProjectSeele.LOGGER.warn(
                    "NERV dormant launch watchdog engaged: eva={} y={} launchTicks={}",
                    unit.getStringUUID(),
                    String.format(Locale.ROOT, "%.3f", unit.getY()),
                    unit.getLaunchTicks());
        }
        unit.tickDormantNervLaunch();
    }

    /** Clears process-local UUID/tick state when an integrated server stops. */
    public static void resetRuntime()
    {
        ROUTE_TICKET_STATE.clear();
        PHASE_STARTED_AT.clear();
        LAST_ENTITY_TICK.clear();
        DORMANT_LAUNCH_TICKS.clear();
    }

    private static void maintainRouteChunks(ServerLevel level, int variant,
                                            UUID canonicalId, boolean forced)
    {
        Boolean previous = ROUTE_TICKET_STATE.put(canonicalId, forced);
        if (previous != null && previous == forced)
        {
            return;
        }
        BlockPos hangar = EvaHangarBuilder.hangarBed(
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant);
        BlockPos surface = IntegratedNervMapBuilder.surfaceLiftBed(variant);
        int minChunkX = (Math.min(hangar.getX(), surface.getX())
                - ROUTE_CHUNK_MARGIN) >> 4;
        int maxChunkX = (Math.max(hangar.getX(), surface.getX())
                + ROUTE_CHUNK_MARGIN) >> 4;
        int minChunkZ = (Math.min(hangar.getZ(), surface.getZ())
                - ROUTE_CHUNK_MARGIN) >> 4;
        int maxChunkZ = (Math.max(hangar.getZ(), surface.getZ())
                + ROUTE_CHUNK_MARGIN) >> 4;
        int changed = 0;
        for (int chunkX = minChunkX; chunkX <= maxChunkX; chunkX++)
        {
            for (int chunkZ = minChunkZ; chunkZ <= maxChunkZ; chunkZ++)
            {
                if (ForgeChunkManager.forceChunk(level, ProjectSeele.MODID,
                        canonicalId, chunkX, chunkZ, forced, true))
                {
                    changed++;
                }
            }
        }

        ProjectSeele.LOGGER.info(
                "NERV EVA-0{} logistics route tickets {}: changed={} range=[{},{}]..[{},{}]",
                variant, forced ? "ACQUIRED" : "RELEASED", changed,
                minChunkX, minChunkZ, maxChunkX, maxChunkZ);
    }

    private static void loadFleetStations(ServerLevel level)
    {
        for (int variant = 0; variant < 3; variant++)
        {
            level.getChunkAt(EvaHangarBuilder.hangarBed(
                    IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant));
            level.getChunkAt(IntegratedNervMapBuilder.lowerLiftBed(variant));
            level.getChunkAt(IntegratedNervMapBuilder.surfaceLiftBed(variant));
        }
    }

    private static List<EvaUnit01Entity> loadedFleet(ServerLevel level)
    {
        List<EvaUnit01Entity> units = new ArrayList<>();
        for (Entity entity : level.getAllEntities())
        {
            if (entity instanceof EvaUnit01Entity unit && unit.isAlive())
            {
                units.add(unit);
            }
        }
        return units;
    }
    private static EvaUnit01Entity canonical(ServerLevel level, int variant)
    {
        UUID id = EvaFleetSavedData.get(level.getServer())
                .canonicalId(variant).orElse(null);
        if (id == null)
        {
            return null;
        }
        Entity direct = level.getEntity(id);
        if (direct instanceof EvaUnit01Entity unit && unit.isAlive())
        {
            return unit;
        }
        return loadedFleet(level).stream()
                .filter(unit -> unit.getUUID().equals(id)).findFirst().orElse(null);
    }

    private static FleetEntry entry(ServerLevel level, int variant)
    {
        return EvaFleetSavedData.get(level.getServer()).entry(variant).orElse(null);
    }

    private static void put(ServerLevel level, int variant, FleetEntry entry)
    {
        EvaFleetSavedData data = EvaFleetSavedData.get(level.getServer());
        FleetEntry previous = data.entry(variant).orElse(null);
        long now = System.nanoTime();
        if (previous == null || previous.phase() != entry.phase())
        {
            long started = PHASE_STARTED_AT.getOrDefault(
                    entry.canonicalId(), now);
            ProjectSeele.LOGGER.info(
                    "NERV EVA-0{} logistics phase: {} -> {} elapsedMs={} phaseTicks={} carrier={} lcl={}",
                    variant, previous == null ? "UNREGISTERED" : previous.phase(),
                    entry.phase(), (now - started) / 1_000_000L,
                    previous == null ? 0 : previous.ticks(),
                    entry.carrier(), entry.lclLayers());
            PHASE_STARTED_AT.put(entry.canonicalId(), now);
        }
        else
        {
            PHASE_STARTED_AT.putIfAbsent(entry.canonicalId(), now);
        }
        data.put(variant, entry);
    }

    private static EvaUnit01Entity createUnit(ServerLevel level, int variant)
    {
        return switch (variant)
        {
            case EvaUnit01Entity.UNIT_00 -> ModEntities.EVA_UNIT00.get().create(level);
            case EvaUnit01Entity.UNIT_02 -> ModEntities.EVA_UNIT02.get().create(level);
            default -> ModEntities.EVA_UNIT01.get().create(level);
        };
    }

    private static void placeAt(EvaUnit01Entity unit, BlockPos bed)
    {
        unit.moveTo(bed.getX() + 0.5D, bed.getY() + 1.0D,
                bed.getZ() + 0.5D, EvaUnit01Entity.SILO_BAY_YAW, 0.0F);
        unit.setYRot(EvaUnit01Entity.SILO_BAY_YAW);
        unit.setYBodyRot(EvaUnit01Entity.SILO_BAY_YAW);
        unit.setYHeadRot(EvaUnit01Entity.SILO_BAY_YAW);
        unit.yRotO = EvaUnit01Entity.SILO_BAY_YAW;
        unit.yBodyRotO = EvaUnit01Entity.SILO_BAY_YAW;
        unit.yHeadRotO = EvaUnit01Entity.SILO_BAY_YAW;
        unit.setDeltaMovement(Vec3.ZERO);
        unit.setNoGravity(true);
        unit.setNervLogisticsLocked(true);
    }

    private static String label(int variant)
    {
        return String.format(Locale.ROOT, "EVA-%02d", variant);
    }

    public record ActionResult(boolean accepted, String message) {}

    public record Status(int variant, String phase, boolean loaded,
                         UUID canonicalId, int lclLayers, int ticks) {}
}
