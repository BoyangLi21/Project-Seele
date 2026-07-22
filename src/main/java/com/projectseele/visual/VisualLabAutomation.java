package com.projectseele.visual;

import java.util.UUID;

import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.event.Tokyo3RamielBattleDirector;
import com.projectseele.network.ClientboundGeoFrontSortieCapturePacket;
import com.projectseele.network.ClientboundSiloCapturePacket;
import com.projectseele.network.ClientboundGeoFrontCapturePacket;
import com.projectseele.network.ClientboundTokyo3CapturePacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.world.Tokyo3RetractionDirector;
import com.projectseele.world.IntegratedNervMapBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.network.PacketDistributor;

/** Dev-only unattended Visual Lab runner enabled by -PvisualCapture=true. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class VisualLabAutomation
{
    private static final boolean ENABLED = Boolean.getBoolean("projectseele.visualCapture");
    private static final String[] ALL_POSES = {
            "idle", "walk_contact", "run_contact", "jump", "fall",
            "crouch", "crouch_walk", "prone", "crawl", "prone_cannon",
            "knife_ready",
            "knife_windup", "knife_contact", "knife_recovery",
            "lance_ready", "lance_windup", "lance_contact", "lance_recovery", "cannon",
            "crouch_knife_contact", "prone_knife_contact",
            "crouch_lance_contact", "prone_lance_contact", "n2_ready",
            "rifle_walk_contact", "crouch_rifle_contact", "prone_rifle", "rifle",
            "live_melee", "live_knife", "live_knife_heavy", "live_lance",
            "live_rifle", "live_jump"
    };
    private static final String[] ALL_MASS_POSES = {
            "idle", "move", "attack", "revive", "ritual"
    };
    private static final String REQUESTED_POSE = System.getProperty("projectseele.visualCapturePose", "all");
    private static final String CAPTURE_UNIT =
            System.getProperty("projectseele.visualCaptureUnit", "unit01");
    private static final boolean IMPACT_CAPTURE = CAPTURE_UNIT.equals("impact");
    private static final boolean MASS_CAPTURE = CAPTURE_UNIT.equals("mass");
    private static final boolean SILO_CAPTURE = CAPTURE_UNIT.equals("silo");
    private static final boolean TOKYO3_CAPTURE = CAPTURE_UNIT.equals("tokyo3");
    private static final boolean TOKYO3_RETRACTION_CAPTURE =
            CAPTURE_UNIT.equals("tokyo3_retraction");
    private static final boolean TOKYO3_RAMIEL_CAPTURE =
            CAPTURE_UNIT.equals("tokyo3_battle");
    private static final boolean GEOFRONT_CAPTURE = CAPTURE_UNIT.equals("geofront");
    private static final boolean GEOFRONT_SORTIE_CAPTURE =
            CAPTURE_UNIT.equals("geofront_sortie");
    private static final String[] POSES = REQUESTED_POSE.equals("all")
            ? ALL_POSES : REQUESTED_POSE.split(",");
    private static final String[] MASS_POSES = REQUESTED_POSE.equals("all")
            ? ALL_MASS_POSES : REQUESTED_POSE.split(",");
    private static UUID playerId;
    private static UUID subjectId;
    private static int ticks;
    private static int nextPose;
    private static int tokyo3RestoreAt;
    private static boolean geoFrontSortieSurfaceAudited;

    private VisualLabAutomation() {}

    @SubscribeEvent
    public static void onLogin(PlayerEvent.PlayerLoggedInEvent event)
    {
        if (ENABLED && event.getEntity() instanceof ServerPlayer player)
        {
            // A previous unattended run may have closed while its client-only
            // camera was below the cavern. Always begin automation from a
            // vanilla-safe location before any capture-specific setup runs.
            if (!player.isAlive())
            {
                player.setHealth(player.getMaxHealth());
            }
            player.setNoGravity(false);
            player.setDeltaMovement(0.0D, 0.0D, 0.0D);
            player.fallDistance = 0.0F;
            MinecraftServer server = player.getServer();
            if (server != null)
            {
                player.teleportTo(server.overworld(), 0.5D, 97.0D, 0.5D,
                        180.0F, 0.0F);
            }
            playerId = player.getUUID();
            subjectId = null;
            ticks = 0;
            nextPose = 0;
            tokyo3RestoreAt = -1;
            geoFrontSortieSurfaceAudited = false;
            ProjectSeele.LOGGER.info("Visual Lab automation armed for {}", player.getGameProfile().getName());
        }
    }

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent event)
    {
        if (TOKYO3_RAMIEL_CAPTURE
                && event.getEntity() instanceof ServerPlayer player
                && player.serverLevel().dimension().equals(GeoFrontCommands.GEOFRONT))
        {
            Tokyo3RamielBattleDirector.abort(player.serverLevel(),
                    IntegratedNervMapBuilder.TOKYO3_ORIGIN);
        }
        if (playerId != null && playerId.equals(event.getEntity().getUUID()))
        {
            playerId = null;
            subjectId = null;
        }
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent event)
    {
        if (!ENABLED || event.phase != TickEvent.Phase.END || playerId == null)
        {
            return;
        }
        MinecraftServer server = event.getServer();
        ServerPlayer player = server.getPlayerList().getPlayer(playerId);
        if (player == null)
        {
            return;
        }
        ticks++;
        try
        {
            if (ticks == 40)
            {
                if (GEOFRONT_SORTIE_CAPTURE)
                {
                    player.stopRiding();
                    player.teleportTo(server.overworld(), 0.5D, 97.0D, 0.5D,
                            180.0F, 0.0F);
                }
                else if (GEOFRONT_CAPTURE)
                {
                    GeoFrontCommands.setupVisualCapture(player.createCommandSourceStack());
                    SeeleNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player),
                            new ClientboundGeoFrontCapturePacket(GeoFrontCommands.ORIGIN));
                    ProjectSeele.LOGGER.info(
                            "Visual Lab armed GeoFront cavern capture at {} immediately after audit",
                            GeoFrontCommands.ORIGIN);
                    playerId = null;
                }
                else if (TOKYO3_CAPTURE || TOKYO3_RETRACTION_CAPTURE
                        || TOKYO3_RAMIEL_CAPTURE)
                {
                    ThirdTokyoCommands.setupVisualCapture(player.createCommandSourceStack());
                }
                else if (SILO_CAPTURE)
                {
                    LaunchSiloCommands.setupVisualCapture(player.createCommandSourceStack());
                }
                else
                {
                    VisualLabCommands.setup(player.createCommandSourceStack(),
                            IMPACT_CAPTURE ? "unit01" : CAPTURE_UNIT);
                    if (!MASS_CAPTURE)
                    {
                        String expectedUnit = IMPACT_CAPTURE ? "unit01" : CAPTURE_UNIT;
                        subjectId = VisualLabCommands.findUnitId(player, expectedUnit);
                        ProjectSeele.LOGGER.info(
                                "Visual Lab pinned {} subject {} for this matrix",
                                expectedUnit, subjectId);
                    }
                }
            }
            if (GEOFRONT_SORTIE_CAPTURE)
            {
                if (ticks == 50)
                {
                    GeoFrontCommands.preloadVisualSortie(player);
                }
                if (ticks == 65)
                {
                    if (GeoFrontCommands.linkVisualCapture(
                            player.createCommandSourceStack()) != 1)
                    {
                        throw new IllegalStateException(
                                "Visual GeoFront sortie link command failed");
                    }
                    ProjectSeele.LOGGER.info(
                            "Visual Lab linked the three GeoFront terminals to Tokyo-3");
                }
                if (ticks == 100)
                {
                    GeoFrontCommands.pruneVisualSortieDuplicates(player.serverLevel());
                    GeoFrontCommands.SortieAudit audit = GeoFrontCommands.inspectSortie(
                            server, player.serverLevel());
                    if (!audit.valid())
                    {
                        throw new IllegalStateException(
                                "Visual GeoFront sortie audit failed: " + audit.summary());
                    }
                    EvaUnit01Entity unit = LaunchSiloCommands.nearestCagedUnit(player);
                    SeeleNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player),
                            new ClientboundGeoFrontSortieCapturePacket(
                                    unit.getId(), GeoFrontCommands.ORIGIN));
                    ProjectSeele.LOGGER.info(
                            "Visual Lab armed GeoFront-to-Tokyo-3 sortie capture for {}",
                            unit.getStringUUID());
                }
                if (ticks == 160)
                {
                    if (LaunchSiloCommands.board(player.createCommandSourceStack()) != 1)
                    {
                        throw new IllegalStateException(
                                "Visual GeoFront sortie boarding command failed");
                    }
                    ProjectSeele.LOGGER.info(
                            "Visual Lab started linked GeoFront catapult sequence");
                }
                if (!geoFrontSortieSurfaceAudited && ticks > 300
                        && player.serverLevel().dimension().equals(GeoFrontCommands.GEOFRONT)
                        && player.getVehicle() instanceof EvaUnit01Entity unit
                        && unit.getY() >= IntegratedNervMapBuilder.surfaceLiftBed(1).getY() + 1.0D
                        && !unit.isLaunchSequenceActive())
                {
                    IntegratedNervMapBuilder.IntegratedAudit audit =
                            IntegratedNervMapBuilder.inspect(player.serverLevel());
                    if (!audit.valid())
                    {
                        throw new IllegalStateException(
                                "Tokyo-3 post-sortie continuous-map audit failed: "
                                        + audit.summary());
                    }
                    geoFrontSortieSurfaceAudited = true;
                    ProjectSeele.LOGGER.info(
                            "Visual Lab verified same-dimension Tokyo-3 arrival after {} blocks",
                            IntegratedNervMapBuilder.ascentDistance());
                }
                if (ticks > 600)
                {
                    ProjectSeele.LOGGER.error(
                            "VISUAL GEOFRONT SORTIE INVALID: sequence exceeded 600 ticks");
                    playerId = null;
                }
                return;
            }
            if (GEOFRONT_CAPTURE)
            {
                return;
            }
            if (TOKYO3_RETRACTION_CAPTURE)
            {
                BlockPos origin = ThirdTokyoCommands.fixedVisualOrigin(player.serverLevel());
                if (ticks == 80)
                {
                    SeeleNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player),
                            new ClientboundTokyo3CapturePacket(origin, true));
                    ProjectSeele.LOGGER.info(
                            "Visual Lab armed Tokyo-3 retraction capture at {}", origin);
                }
                if (ticks == 160)
                {
                    Tokyo3RetractionDirector.request(player.serverLevel(), origin, true);
                    ProjectSeele.LOGGER.info(
                            "Visual Lab started Tokyo-3 emergency tower descent");
                }
                Tokyo3RetractionDirector.Status status =
                        Tokyo3RetractionDirector.status(player.serverLevel(), origin);
                if (ticks > 160 && tokyo3RestoreAt < 0
                        && status.phase().equals("RETRACTED"))
                {
                    tokyo3RestoreAt = ticks + 80;
                    ProjectSeele.LOGGER.info(
                            "Visual Lab observed fully retracted Tokyo-3; restoration queued");
                }
                if (ticks == tokyo3RestoreAt)
                {
                    Tokyo3RetractionDirector.request(player.serverLevel(), origin, false);
                    ProjectSeele.LOGGER.info(
                            "Visual Lab started Tokyo-3 all-clear tower restoration");
                }
                if (ticks > 15000)
                {
                    ProjectSeele.LOGGER.error(
                            "VISUAL TOKYO3 RETRACTION INVALID: sequence exceeded 15000 ticks");
                    playerId = null;
                }
                return;
            }
            if (TOKYO3_RAMIEL_CAPTURE)
            {
                BlockPos origin = ThirdTokyoCommands.fixedVisualOrigin(
                        player.serverLevel());
                if (ticks == 80)
                {
                    var result = Tokyo3RamielBattleDirector.start(
                            player.serverLevel(), origin, player);
                    if (!result.accepted())
                    {
                        throw new IllegalStateException(
                                "Visual Operation Yashima start failed: "
                                        + result.message());
                    }
                    ProjectSeele.LOGGER.info(
                            "Visual Lab started Operation Yashima at {}", origin);
                }
                if (ticks == 110)
                {
                    SeeleNetwork.CHANNEL.send(
                            PacketDistributor.PLAYER.with(() -> player),
                            new ClientboundTokyo3CapturePacket(
                                    origin, false, true));
                    ProjectSeele.LOGGER.info(
                            "Visual Lab armed Tokyo-3 Ramiel battle capture at {} status={}",
                            origin, Tokyo3RamielBattleDirector.status(
                                    player.serverLevel(), origin).summary());
                    // Client capture owns shutdown. onLogout aborts the
                    // fixture and restores Tokyo-3 before the save closes.
                    playerId = null;
                }
                return;
            }
            if (TOKYO3_CAPTURE)
            {
                if (ticks == 80)
                {
                    BlockPos origin = ThirdTokyoCommands.fixedVisualOrigin(player.serverLevel());
                    SeeleNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player),
                            new ClientboundTokyo3CapturePacket(origin));
                    ProjectSeele.LOGGER.info(
                            "Visual Lab armed Tokyo-3 full-scene capture at {}", origin);
                    playerId = null;
                }
                return;
            }
            if (SILO_CAPTURE)
            {
                if (ticks == 55)
                {
                    EvaUnit01Entity unit = LaunchSiloCommands.nearestCagedUnit(player);
                    SeeleNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player),
                            new ClientboundSiloCapturePacket(unit.getId()));
                    ProjectSeele.LOGGER.info(
                            "Visual Lab armed launch-silo scene capture for {}", unit.getStringUUID());
                }
                if (ticks == 120)
                {
                    if (LaunchSiloCommands.board(player.createCommandSourceStack()) != 1)
                    {
                        throw new IllegalStateException("Visual Silo boarding command failed");
                    }
                    ProjectSeele.LOGGER.info(
                            "Visual Lab started real entry-plug synchronization and catapult sequence");
                }
                if (ticks > 500)
                {
                    ProjectSeele.LOGGER.error(
                            "VISUAL SILO AUTOMATION INVALID: launch sequence exceeded 500 ticks");
                    playerId = null;
                }
                return;
            }
            if (IMPACT_CAPTURE)
            {
                if (ticks == 100)
                {
                    VisualLabCommands.impact(player.createCommandSourceStack());
                    ProjectSeele.LOGGER.info(
                            "Visual Lab queued Third Impact front capture");
                    // The client-side capture session owns shutdown from here.
                    playerId = null;
                }
                return;
            }
            if (MASS_CAPTURE)
            {
                if (ticks >= 100 && nextPose < MASS_POSES.length
                        && ticks == 100 + nextPose * 140)
                {
                    String pose = MASS_POSES[nextPose++].trim();
                    VisualLabCommands.poseMass(player.createCommandSourceStack(), pose);
                    VisualLabCommands.captureMass(player.createCommandSourceStack());
                    ProjectSeele.LOGGER.info(
                            "Visual Lab queued Mass Production EVA pose {} ({}/{})",
                            pose, nextPose, MASS_POSES.length);
                }
                if (ticks == 100 + MASS_POSES.length * 140)
                {
                    ProjectSeele.LOGGER.info(
                            "Visual Lab Mass Production EVA matrix finished; screenshots are ready for review");
                    playerId = null;
                }
                return;
            }
            if (ticks >= 100 && nextPose < POSES.length && ticks == 100 + nextPose * 140)
            {
                String pose = POSES[nextPose++];
                if (subjectId == null)
                {
                    throw new IllegalStateException("Visual Lab EVA subject was not pinned");
                }
                VisualLabCommands.pose(player.createCommandSourceStack(), pose,
                        subjectId, CAPTURE_UNIT);
                VisualLabCommands.capture(player.createCommandSourceStack(),
                        subjectId, CAPTURE_UNIT);
                ProjectSeele.LOGGER.info("Visual Lab queued pose {} ({}/{})", pose, nextPose, POSES.length);
            }
            if (ticks == 100 + POSES.length * 140)
            {
                ProjectSeele.LOGGER.info("Visual Lab automation finished; screenshots are ready for review");
                playerId = null;
            }
        }
        catch (CommandSyntaxException | RuntimeException exception)
        {
            ProjectSeele.LOGGER.error("Visual Lab automation failed", exception);
            if (SILO_CAPTURE)
            {
                // Hand the integrated client an invalid subject deliberately;
                // its capture manager records the failure and closes the
                // unattended game instead of leaving it parked in-world.
                SeeleNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player),
                        new ClientboundSiloCapturePacket(-1));
            }
            if (TOKYO3_CAPTURE)
            {
                SeeleNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player),
                        new ClientboundTokyo3CapturePacket(
                                new BlockPos(0, -2048, 0)));
            }
            if (GEOFRONT_CAPTURE)
            {
                SeeleNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player),
                        new ClientboundGeoFrontCapturePacket(
                                new BlockPos(0, -2048, 0)));
            }
            if (GEOFRONT_SORTIE_CAPTURE)
            {
                SeeleNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player),
                        new ClientboundGeoFrontSortieCapturePacket(
                                -1, new BlockPos(0, -2048, 0)));
            }
            playerId = null;
        }
    }
}
