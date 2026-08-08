package com.projectseele;

import com.projectseele.alarm.AngelAlarmSystem;
import com.projectseele.capability.EvaPilotCapability;
import com.projectseele.capability.EvaPilotProvider;
import com.projectseele.config.SeeleConfig;
import com.projectseele.entity.Angel;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.RamielEntity;
import com.projectseele.event.ThirdImpactDirector;
import com.projectseele.network.ServerboundEvaVideoFramePacket;
import com.projectseele.world.MagiDeepLabBuilder;
import com.projectseele.world.NervCommandTelemetry;
import com.projectseele.world.NervCommandDisplayState;
import com.projectseele.world.NervFacilityTopologyBuilder;
import com.projectseele.world.NervOperationsConsole;
import com.projectseele.world.NervRuntimeMaintenance;
import com.projectseele.world.PerformanceCounters;
import com.projectseele.world.S20CommandPresentationDirector;
import com.projectseele.world.S20CommandRoomRepairs;
import com.projectseele.world.S20CommandTransitDirector;
import com.projectseele.world.S20EvaPlantDirector;
import com.projectseele.world.S20PersonnelRouteDirector;
import com.projectseele.world.S20PhysicalElevatorDirector;
import com.projectseele.world.S20SurfaceCleanupDirector;
import com.projectseele.world.S20SurfaceTransitDirector;
import com.projectseele.world.EvaLogisticsDirector;
import com.projectseele.world.EvaWeaponLiftDirector;
import com.projectseele.world.EvaPilotResolver;
import com.projectseele.world.EntryPlugDirector;
import com.projectseele.world.FacilityV2ArchitectureDirector;
import com.projectseele.world.FacilityV2BuildDirector;
import com.projectseele.world.FacilityV2BootstrapDirector;
import com.projectseele.world.FacilityV2CommandInteriorDirector;
import com.projectseele.world.FacilityV2ElevatorDirector;
import com.projectseele.world.FacilityV2ProgrammeDirector;
import com.projectseele.world.FacilityV2StagedBuildDirector;
import com.projectseele.world.FacilityWorldPolicy;
import com.projectseele.world.GeoFrontFabricDirector;
import com.projectseele.world.NervCarrierVisuals;
import com.projectseele.world.TrainingPilotDirector;
import com.projectseele.world.IntegratedNervMapBuilder;
import com.projectseele.world.Tokyo3RetractionDirector;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.event.AttachCapabilitiesEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingChangeTargetEvent;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.event.entity.EntityTravelToDimensionEvent;
import net.minecraftforge.event.entity.EntityJoinLevelEvent;
import net.minecraftforge.event.server.ServerStoppedEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.fml.common.Mod;

/** Forge-bus glue: drives the Angel alarm and combat bookkeeping. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public class GameEvents
{
    @SubscribeEvent
    public static void onLivingChangeTarget(LivingChangeTargetEvent event)
    {
        if (event.getEntity() instanceof Angel && event.getEntity() instanceof Mob mob
                && event.getNewTarget() instanceof ServerPlayer)
        {
            AngelAlarmSystem.engage(mob);
        }
    }

    @SubscribeEvent
    public static void onLivingDeath(LivingDeathEvent event)
    {
        if (event.getEntity() instanceof Angel && event.getEntity().level().getServer() != null)
        {
            AngelAlarmSystem.disengage(event.getEntity().level().getServer(), event.getEntity().getUUID());
            if (event.getSource().getEntity() instanceof ServerPlayer pilot
                    && EvaPilotResolver.controlTarget(pilot) != null)
            {
                float gained = EvaPilotCapability.awardAngelKill(pilot);
                if (gained > 0.0F)
                {
                    pilot.displayClientMessage(Component.translatable(
                            "msg.projectseele.sync_angel_gain",
                            String.format("%.1f", gained),
                            String.format("%.1f", EvaPilotCapability.synchronization(pilot))),
                            false);
                }
            }
        }
    }

    @SubscribeEvent
    public static void onLivingDamage(LivingDamageEvent event)
    {
        // Track who the Angel managed to hurt, for the flawless-kill advancement.
        if (event.getSource().getEntity() instanceof RamielEntity ramiel
                && event.getEntity() instanceof ServerPlayer player)
        {
            ramiel.markPlayerHurt(player.getUUID());
        }
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onServerTickBoundary(TickEvent.ServerTickEvent event)
    {
        if (event.phase == TickEvent.Phase.START)
        {
            PerformanceCounters.beginServerTick(event.getServer());
        }
        else
        {
            PerformanceCounters.markServerEndPhase(event.getServer());
        }
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onServerTick(TickEvent.ServerTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END)
        {
            return;
        }
        PerformanceCounters.beginProjectTickWork(event.getServer());
        boolean brokenArchive =
                FacilityWorldPolicy.isReadOnlyBrokenArchive(
                        event.getServer());
        boolean cleanRebuild =
                FacilityWorldPolicy.isCleanRebuild(event.getServer());
        if (FacilityWorldPolicy.isS20Rebuild(event.getServer()))
        {
            boolean spatialFrozen =
                    FacilityWorldPolicy.isSpatialPreviewFrozen(
                            event.getServer());
            if (event.getServer().getTickCount() % 100 == 0)
            {
                MagiDeepLabBuilder.retireS20DuplicatePresentation(
                        event.getServer());
            }
            // R28 freezes architecture builders, but these two bounded
            // maintenance paths own only the three approved chair cells and
            // exact legacy Tokyo-3 roof/hatch signatures.  Keeping them
            // outside the spatial gate is what lets an immutable human-edited
            // save receive the requested runtime repairs.
            S20CommandPresentationDirector.tickRuntimePresentation(
                    event.getServer());
            // Same exemption, same discipline: one shot per server run over an
            // explicit coordinate list, and every cell must still hold the
            // state it was measured with.
            S20CommandRoomRepairs.tick(event.getServer());
            if (event.getServer().getTickCount() % 20 == 0)
            {
                ServerLevel surface = event.getServer().getLevel(
                        com.projectseele.world.FacilitySchemaV2.DIMENSION);
                if (surface != null)
                {
                    Tokyo3RetractionDirector.register(surface,
                            IntegratedNervMapBuilder.TOKYO3_ORIGIN);
                }
            }
            if (!spatialFrozen)
            {
                S20CommandPresentationDirector.tick(event.getServer());
                S20CommandTransitDirector.tick(event.getServer());
                S20PersonnelRouteDirector.tick(event.getServer());
                S20EvaPlantDirector.tick(event.getServer());
                S20SurfaceCleanupDirector.tick(event.getServer());
                S20SurfaceTransitDirector.tick(event.getServer());
            }
            ServerLevel geoFront = event.getServer().getLevel(
                    com.projectseele.world.FacilitySchemaV2.DIMENSION);
            if (geoFront != null)
            {
                for (S20PhysicalElevatorDirector.LiftSpec lift
                        : S20PhysicalElevatorDirector.s20Lifts())
                {
                    boolean frozenLiftRuntimeAllowed = spatialFrozen
                            && s20FrozenLiftRuntimeAllowed(
                                    event.getServer(), geoFront, lift);
                    if (spatialFrozen && !frozenLiftRuntimeAllowed)
                    {
                        continue;
                    }
                    boolean routeReady;
                    if (frozenLiftRuntimeAllowed)
                    {
                        routeReady = true;
                    }
                    else if (lift.id().equals(
                            S20PhysicalElevatorDirector
                                    .COMMAND_REAR_LIFT_ID))
                    {
                        routeReady =
                                S20CommandTransitDirector.installed(
                                        geoFront)
                                        && S20PersonnelRouteDirector
                                        .installed(geoFront);
                    }
                    else if (S20PhysicalElevatorDirector
                            .isSurfaceTransitLift(lift))
                    {
                        routeReady =
                                S20SurfaceTransitDirector.installed(
                                        geoFront);
                    }
                    else
                    {
                        routeReady =
                                S20EvaPlantDirector.installed(geoFront);
                    }
                    if (routeReady
                            && event.getServer().getTickCount() % 20 == 0
                            && geoFront.hasChunkAt(
                            lift.lower().cabinCentre())
                            && geoFront.hasChunkAt(
                            lift.upper().cabinCentre()))
                    {
                        S20PhysicalElevatorDirector.install(
                                geoFront, lift);
                    }
                    S20PhysicalElevatorDirector.tick(geoFront, lift);
                }
            }
            /*
             * The S20 freeze marker protects authored blocks; it must not
             * disable runtime command-room video.  Screen visibility,
             * capture demand and dummy/human pilot feeds do not write map
             * geometry, and operators still need them while the static
             * recovery world is locked against builders.
             */
            TrainingPilotDirector.tickFeeds(event.getServer());
        }
        else if (cleanRebuild && !brokenArchive)
        {
            FacilityV2BootstrapDirector.tick(event.getServer());
            FacilityV2ArchitectureDirector.tick(event.getServer());
            FacilityV2StagedBuildDirector.tick(event.getServer());
            FacilityV2BuildDirector.tick(event.getServer());
            FacilityV2ProgrammeDirector.tick(event.getServer());
            FacilityV2CommandInteriorDirector.tick(event.getServer());
            GeoFrontFabricDirector.tick(event.getServer());
            FacilityV2ElevatorDirector.tick(event.getServer());
        }
        else if (!brokenArchive)
        {
            /*
             * Legacy maintenance is a world generator in disguise. It is
             * legal only in ordinary pre-v2 saves, never in either the clean
             * rebuild or the archived failed rescue.
             */
            NervFacilityTopologyBuilder.tick(event.getServer());
            NervRuntimeMaintenance.tick(event.getServer());
            if (event.getServer().getTickCount()
                    % NervCommandTelemetry.REFRESH_INTERVAL_TICKS == 0)
            {
                NervCommandTelemetry.tick(event.getServer());
                if (SeeleConfig.runtimeWorldRepairEnabled())
                {
                    MagiDeepLabBuilder.tick(event.getServer());
                }
            }
            // The command room is ~195 blocks from the cages, well past a
            // client's render distance, so only the server sees both ends.
            TrainingPilotDirector.tickFeeds(event.getServer());
        }
        // Armament lifts are persistent gameplay machines, not map writers;
        // their same-UUID payload route remains live in S20 and ordinary saves.
        for (ServerLevel level : event.getServer().getAllLevels())
        {
            EvaWeaponLiftDirector.tick(level);
        }
        if (event.getServer().getTickCount() % 20 == 0)
        {
            AngelAlarmSystem.validate(event.getServer());
            ServerboundEvaVideoFramePacket.syncCaptureDemand(
                    event.getServer());
        }
        PerformanceCounters.endServerTick(event.getServer());
    }

    @SubscribeEvent
    public static void onAttachCapabilities(AttachCapabilitiesEvent<Entity> event)
    {
        if (event.getObject() instanceof Player)
        {
            event.addCapability(EvaPilotProvider.ID, new EvaPilotProvider());
        }
    }

    @SubscribeEvent
    public static void onPlayerClone(PlayerEvent.Clone event)
    {
        event.getOriginal().reviveCaps();
        event.getOriginal().getCapability(EvaPilotCapability.DATA).ifPresent(oldData ->
                event.getEntity().getCapability(EvaPilotCapability.DATA).ifPresent(
                        newData -> newData.copyFrom(oldData)));
        event.getOriginal().invalidateCaps();
    }

    @SubscribeEvent
    public static void onPlayerLoggedIn(PlayerEvent.PlayerLoggedInEvent event)
    {
        if (event.getEntity() instanceof ServerPlayer player)
        {
            AngelAlarmSystem.syncTo(player);
            ThirdImpactDirector.syncTo(player);
            NervCommandDisplayState.syncTo(player);
        }
    }

    @SubscribeEvent
    public static void onPlayerChangedDimension(PlayerEvent.PlayerChangedDimensionEvent event)
    {
        if (event.getEntity() instanceof ServerPlayer player)
        {
            ThirdImpactDirector.syncTo(player);
            NervCommandDisplayState.syncTo(player);
        }
    }

    @SubscribeEvent
    public static void onPlayerRespawn(PlayerEvent.PlayerRespawnEvent event)
    {
        if (event.getEntity() instanceof ServerPlayer player)
        {
            ThirdImpactDirector.syncTo(player);
            NervCommandDisplayState.syncTo(player);
        }
    }

    @SubscribeEvent
    public static void onRightClickBlock(PlayerInteractEvent.RightClickBlock event)
    {
        if (event.getHand() == InteractionHand.MAIN_HAND
                && event.getEntity() instanceof ServerPlayer player)
        {
            boolean cleanRebuild =
                    FacilityWorldPolicy.isCleanRebuild(player.getServer());
            boolean s20Rebuild =
                    FacilityWorldPolicy.isS20Rebuild(player.getServer());
            /*
             * Exact authored console controls outrank the deliberately broad
             * chair hit boxes.  The three ground-recovery buttons sit only
             * one block in front of the former Fuyutsuki chair; handling the
             * seat first mounted the operator instead of recalling an EVA.
             * Leave the vanilla button use uncancelled so it still clicks and
             * visibly depresses.
             */
            if (s20Rebuild && NervOperationsConsole.handleUse(
                    player, event.getPos()))
            {
                return;
            }
            if (S20CommandPresentationDirector.handleSeatUse(
                    player, event.getPos())
                    || cleanRebuild
                    && FacilityV2CommandInteriorDirector.handleSeatUse(
                    player, event.getPos()))
            {
                event.setCanceled(true);
                event.setCancellationResult(InteractionResult.SUCCESS);
                return;
            }
            // Do not cancel the vanilla button use: its powered animation and
            // click sound are the physical acknowledgement for the operator.
            if (s20Rebuild)
            {
                boolean handled = false;
                boolean spatialFrozen =
                        FacilityWorldPolicy.isSpatialPreviewFrozen(
                                player.getServer());
                for (S20PhysicalElevatorDirector.LiftSpec lift
                        : S20PhysicalElevatorDirector.s20Lifts())
                {
                    if (spatialFrozen
                            && !s20FrozenLiftRuntimeAllowed(
                                    player.getServer(),
                                    player.serverLevel(), lift))
                    {
                        continue;
                    }
                    if (S20PhysicalElevatorDirector.handleUse(
                            player, event.getPos(), lift))
                    {
                        handled = true;
                        break;
                    }
                }
                if (!handled)
                {
                    handled = NervOperationsConsole.handleUse(
                            player, event.getPos());
                }
                if (!handled)
                {
                    EvaLogisticsDirector.handleUse(player,
                            event.getPos());
                }
                return;
            }
            if (cleanRebuild)
            {
                /*
                 * Facility-v2 owns several independent physical control
                 * surfaces.  The old branch returned immediately after
                 * asking the lift director, even when the clicked block was
                 * not a lift control.  That swallowed every command-room
                 * launch key and every cage PREPARE / RECALL / STATUS key in
                 * the clean S19 world.  Route the click through the modern
                 * handlers in authority order and still leave vanilla's
                 * button animation/sound uncancelled.
                 */
                if (!FacilityV2ElevatorDirector.handleUse(
                        player, event.getPos())
                        && !NervOperationsConsole.handleUse(
                        player, event.getPos()))
                {
                    EvaLogisticsDirector.handleUse(
                            player, event.getPos());
                }
                return;
            }
            if (!NervOperationsConsole.handleUse(player, event.getPos()))
            {
                if (!EvaLogisticsDirector.handleUse(
                        player, event.getPos()))
                {
                    if (!FacilityV2ElevatorDirector.handleUse(
                            player, event.getPos())
                            && !NervFacilityTopologyBuilder.handleUse(
                            player, event.getPos()))
                    {
                        MagiDeepLabBuilder.handleUse(player, event.getPos());
                    }
                }
            }
        }
    }

    private static boolean s20FrozenLiftRuntimeAllowed(
            MinecraftServer server, ServerLevel level,
            S20PhysicalElevatorDirector.LiftSpec lift)
    {
        if (FacilityWorldPolicy.isR10R12Approved(server)
                && S20PhysicalElevatorDirector.isR10ApprovedLift(lift))
        {
            return true;
        }
        if (FacilityWorldPolicy.isR14R16Approved(server)
                && S20PhysicalElevatorDirector.isR14ApprovedLift(lift))
        {
            return true;
        }
        if (S20PhysicalElevatorDirector.isRetainedCompactCageLift(lift)
                && S20PhysicalElevatorDirector.hasHealthyRuntime(
                        level, lift))
        {
            return true;
        }
        return S20PhysicalElevatorDirector.isSurfaceTransitLift(lift)
                && (S20SurfaceTransitDirector.installed(level)
                || S20PhysicalElevatorDirector.hasHealthyRuntime(
                        level, lift));
    }

    @SubscribeEvent
    public static void onEntityJoinLevel(EntityJoinLevelEvent event)
    {
        if (event.getLevel() instanceof net.minecraft.server.level.ServerLevel level
                && FacilityWorldPolicy.legacyGenerationAllowed(
                        level.getServer())
                && NervRuntimeMaintenance.rejectJoin(level, event.getEntity()))
        {
            event.setCanceled(true);
            return;
        }
        if (!event.getLevel().isClientSide
                && event.getEntity() instanceof EvaUnit01Entity unit)
        {
            if (!EvaLogisticsDirector.validateCanonical(unit))
            {
                event.setCanceled(true);
            }
        }
    }
    @SubscribeEvent
    public static void onEntityTravelToDimension(EntityTravelToDimensionEvent event)
    {
        EvaUnit01Entity eva = event.getEntity() instanceof EvaUnit01Entity unit
                ? unit : EvaPilotResolver.controlTarget(event.getEntity());
        if (eva != null && eva.isLaunchSequenceActive())
        {
            event.setCanceled(true);
        }
    }

    @SubscribeEvent
    public static void onServerStopped(ServerStoppedEvent event)
    {
        AngelAlarmSystem.reset();
        NervCommandTelemetry.reset();
        NervOperationsConsole.reset();
        EvaLogisticsDirector.releaseRouteTickets(event.getServer());
        EntryPlugDirector.resetRuntime();
        NervCarrierVisuals.resetRuntime();
        EvaLogisticsDirector.resetRuntime();
        GeoFrontFabricDirector.resetRuntime();
        NervFacilityTopologyBuilder.resetRuntime();
        NervRuntimeMaintenance.reset();
        PerformanceCounters.reset();
    }
}
