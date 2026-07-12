package com.projectseele.visual;

import java.util.UUID;

import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.projectseele.ProjectSeele;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Dev-only unattended Visual Lab runner enabled by -PvisualCapture=true. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class VisualLabAutomation
{
    private static final boolean ENABLED = Boolean.getBoolean("projectseele.visualCapture");
    private static final String[] ALL_POSES = {
            "idle", "walk_contact", "crouch", "prone", "prone_cannon",
            "knife_windup", "knife_contact", "knife_recovery",
            "lance_windup", "lance_contact", "lance_recovery", "cannon"
    };
    private static final String REQUESTED_POSE = System.getProperty("projectseele.visualCapturePose", "all");
    private static final String[] POSES = REQUESTED_POSE.equals("all")
            ? ALL_POSES : REQUESTED_POSE.split(",");
    private static UUID playerId;
    private static int ticks;
    private static int nextPose;

    private VisualLabAutomation() {}

    @SubscribeEvent
    public static void onLogin(PlayerEvent.PlayerLoggedInEvent event)
    {
        if (ENABLED && event.getEntity() instanceof ServerPlayer player)
        {
            playerId = player.getUUID();
            ticks = 0;
            nextPose = 0;
            ProjectSeele.LOGGER.info("Visual Lab automation armed for {}", player.getGameProfile().getName());
        }
    }

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent event)
    {
        if (playerId != null && playerId.equals(event.getEntity().getUUID()))
        {
            playerId = null;
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
                VisualLabCommands.setup(player.createCommandSourceStack());
            }
            if (ticks >= 100 && nextPose < POSES.length && ticks == 100 + nextPose * 140)
            {
                String pose = POSES[nextPose++];
                VisualLabCommands.pose(player.createCommandSourceStack(), pose);
                VisualLabCommands.capture(player.createCommandSourceStack());
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
            playerId = null;
        }
    }
}
