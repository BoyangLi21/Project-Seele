package com.projectseele.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.world.*;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.EntityJoinLevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** Real city and EVA controller cycles in the explicitly named preview only. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID)
public final class TvWorldSystemChecks
{
    private static final String MODE = System.getProperty("projectseele.tvWorldPreviewReview", "");
    private static final boolean ENABLED = MODE.equals("systemtest") || MODE.equals("evatest");
    private static final List<String> TRACE = new ArrayList<>();
    private static final UUID[] IDS = new UUID[3];
    private static int age, stage, phaseAge, variant;
    private static boolean initialized, done;
    private static String previousPhase = "";
    private static double previousX, previousY, previousZ, maxStep;
    private static boolean havePosition;
    private static int torchDrops;

    private TvWorldSystemChecks() {}

    @SubscribeEvent
    public static void itemJoined(EntityJoinLevelEvent event)
    {
        if (ENABLED && event.getLevel() instanceof ServerLevel level && TvWorldPreviewTerrain.active(level)
                && event.getEntity() instanceof net.minecraft.world.entity.item.ItemEntity item
                && item.getItem().is(net.minecraft.world.item.Items.TORCH)) torchDrops++;
    }

    @SubscribeEvent
    public static void tick(TickEvent.ServerTickEvent event)
    {
        if (!ENABLED || done || event.phase != TickEvent.Phase.END) return;
        MinecraftServer server = event.getServer();
        var world = server.getWorldPath(LevelResource.ROOT).normalize();
        if (!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))
            throw new IllegalStateException("TV system checks refused another world");
        try
        {
            if (Files.exists(world.resolve("tv_preview_stop_requested")))
            {
                Files.delete(world.resolve("tv_preview_stop_requested"));
                log("STOP requested; saving the current test state");
                done = true;
                TvWorldPreviewPreparation.completeExternalStage(server);
                return;
            }
            ServerLevel level = server.getLevel(FacilitySchemaV2.DIMENSION);
            if (++age < 120) return;
            require(age < 60000, "whole test timeout");
            require(TvWorldPreviewTerrain.active(level), "TV profile active");
            EvaFleetSavedData fleet = EvaFleetSavedData.get(server);
            if (!initialized)
            {
                for (int i = 0; i < 3; i++)
                    IDS[i] = fleet.canonicalId(i).orElseThrow();
                initialized = true;
                log("START canonical identities retained");
            }
            for (int i = 0; i < 3; i++)
                require(IDS[i].equals(fleet.canonicalId(i).orElse(null)), "canonical UUID changed for " + i);
            phaseAge++;
            require(phaseAge < 6000, "stage timeout " + stage + " variant=" + variant);
            var origin = IntegratedNervMapBuilder.TOKYO3_ORIGIN;
            if (stage == 0)
            {
                var city = Tokyo3RetractionDirector.status(level, origin);
                if (MODE.equals("evatest"))
                {
                    require(city.depth() == 0 && city.targetDepth() == 0, "verified city remains at surface");
                    log("EVA-only continuation after the recorded city down/up check");
                    stage = 3;
                    phaseAge = 0;
                    return;
                }
                if (city.targetDepth() == city.maximumDepth())
                {
                    log("CITY resume saved descent depth=" + city.depth());
                    next();
                    return;
                }
                var result = Tokyo3RetractionDirector.request(level, origin, true);
                require(result.accepted(), "city descent: " + result.message());
                log("CITY descent requested");
                next();
                return;
            }
            if (stage == 1 || stage == 2)
            {
                var city = Tokyo3RetractionDirector.status(level, origin);
                require(!city.phase().equals("FAULT"), "city fault at depth " + city.depth());
                if (age % 200 == 0) log("CITY " + city.phase() + " depth=" + city.depth());
                int target = stage == 1 ? city.maximumDepth() : 0;
                if (city.depth() != target || city.targetDepth() != target) return;
                var audit = ThirdTokyoSurfaceBuilder.inspect(level, origin, target);
                require(audit.valid(), "city geometry audit at " + target + ": " + audit);
                require(LocalMapAssetLoader.inspectTokyo3Skyscrapers(level, origin, target) == 3,
                        "all three imported buildings at their physical destinations");
                require(LocalMapAssetLoader.inspectTokyo3CargoMismatches(level, origin, target) == 0,
                        "complete imported cargo including torches");
                require(torchDrops == 0, "city movement generated torch item drops: " + torchDrops);
                log("CITY PASS depth=" + target + " generated=" + ThirdTokyoSurfaceBuilder.movableBuildings(level).size() + " imported=3");
                if (stage == 1)
                {
                    var result = Tokyo3RetractionDirector.request(level, origin, false);
                    require(result.accepted(), "city restoration: " + result.message());
                }
                else Files.writeString(world.resolve("tv_preview_city_checks.txt"), String.join("\n", TRACE)
                        + "\nComplete imported cargo retained; torch drops=0\n");
                next();
                return;
            }
            if (variant == 3)
            {
                for (int i = 0; i < 3; i++) if (TrainingPilotDirector.requiresRouteTicket(i)) return;
                Files.writeString(world.resolve("tv_preview_system_checks.txt"), String.join("\n", TRACE)
                        + "\nCOMPLETE city down/up; three EVA round trips; stable UUIDs; maxStep=" + maxStep + "\n");
                log("COMPLETE city down/up and all three EVA round trips; maxStep=" + maxStep);
                done = true;
                TvWorldPreviewPreparation.completeExternalStage(server);
                return;
            }
            if (age % 20 == 0) EvaLogisticsDirector.loadControlTarget(level, variant);
            EvaUnit01Entity unit = EvaLogisticsDirector.canonicalUnit(level, variant);
            if (unit == null) return;
            require(unit.getUUID().equals(IDS[variant]), "live airframe identity");
            require(unit.level() == level, "transport remains in the same dimension");
            if (havePosition)
            {
                double step = Math.sqrt(Math.pow(unit.getX() - previousX, 2)
                        + Math.pow(unit.getY() - previousY, 2) + Math.pow(unit.getZ() - previousZ, 2));
                maxStep = Math.max(maxStep, step);
                require(step < 64, "non-continuous airframe displacement " + step);
            }
            previousX = unit.getX(); previousY = unit.getY(); previousZ = unit.getZ();
            havePosition = true;
            var entry = fleet.entry(variant).orElseThrow();
            String currentPhase = entry.phase().name();
            if (!currentPhase.equals(previousPhase))
            {
                log("EVA-0" + variant + " " + currentPhase + " pos=" + unit.position());
                previousPhase = currentPhase;
            }
            require(entry.phase() != EvaFleetSavedData.Phase.PLUG_FAULT, "entry plug fault");
            if (stage == 3)
            {
                if (phaseAge < 80) return;
                require(entry.phase() == EvaFleetSavedData.Phase.PARKED, "EVA starts in wet cage");
                var result = TrainingPilotDirector.start(level, variant);
                require(result.accepted(), "dummy boarding route: " + result.message());
                next();
            }
            else if (stage == 4)
            {
                if (phaseAge % 200 == 0)
                    for (var pilot : TrainingPilotDirector.pilots(level))
                        if (pilot.getAssignedVariant() == variant)
                            log("BOARDING eva=" + variant + " pos=" + pilot.position()
                                    + " entityTick=" + pilot.tickCount + " vehicle=" + pilot.getVehicle());
                require(phaseAge < 1800, "training pilot did not board within 90 seconds");
                if (!EntryPlugDirector.hasBoardedPilot(level, variant, unit)) return;
                var result = EvaLogisticsDirector.requestPrepare(level, variant);
                require(result.accepted(), "preparation: " + result.message());
                next();
            }
            else if (stage == 5)
            {
                if (entry.phase() != EvaFleetSavedData.Phase.SILO_READY) return;
                var result = EvaLogisticsDirector.requestLaunch(level, variant);
                require(result.accepted(), "launch: " + result.message());
                next();
            }
            else if (stage == 6)
            {
                if (entry.phase() != EvaFleetSavedData.Phase.DEPLOYED || unit.getY() < 79) return;
                log("EVA-0" + variant + " reached surface with original UUID");
                next();
            }
            else if (stage == 7)
            {
                require(entry.phase() == EvaFleetSavedData.Phase.DEPLOYED, "no automatic recovery without authorization");
                if (phaseAge < 100) return;
                var result = EvaLogisticsDirector.requestRecovery(level, variant);
                require(result.accepted(), "recovery authorization: " + result.message());
                next();
            }
            else if (stage == 8)
            {
                if (entry.phase() != EvaFleetSavedData.Phase.PARKED) return;
                require(Math.abs(unit.getY() + 442) < 1 && Math.abs(unit.getZ() - 160.5) < 1,
                        "returned to assigned wet cage");
                TrainingPilotDirector.stop(level, variant);
                log("EVA-0" + variant + " ROUND TRIP PASS");
                variant++;
                stage = 3;
                phaseAge = 0;
                havePosition = false;
                previousPhase = "";
            }
        }
        catch (Exception exception)
        {
            ProjectSeele.LOGGER.error("TV SYSTEM CHECKS FAILED stage=" + stage + " variant=" + variant, exception);
            try { Files.writeString(world.resolve("tv_preview_system_failure.txt"), String.join("\n", TRACE) + "\n" + exception); }
            catch (Exception ignored) { }
            done = true;
            TvWorldPreviewPreparation.completeExternalStage(server);
        }
    }

    private static void next() { stage++; phaseAge = 0; }
    private static void require(boolean condition, String reason)
    {
        if (!condition) throw new IllegalStateException(reason);
    }
    private static void log(String line)
    {
        TRACE.add(line);
        ProjectSeele.LOGGER.info("TV SYSTEM CHECKS {}", line);
    }
}
