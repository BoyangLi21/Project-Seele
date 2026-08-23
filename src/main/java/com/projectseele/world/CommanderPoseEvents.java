package com.projectseele.world;

import com.projectseele.ProjectSeele;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Lifecycle reconciliation for a pose that is valid only while seated. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID,
        bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class CommanderPoseEvents
{
    private CommanderPoseEvents()
    {
    }

    @SubscribeEvent
    public static void onPlayerTick(TickEvent.PlayerTickEvent event)
    {
        if (event.phase == TickEvent.Phase.END
                && event.player instanceof ServerPlayer player
                && CommanderPoseState.isActive(player)
                && !player.isPassenger())
        {
            CommanderPoseState.setActive(player, false);
        }
    }

    @SubscribeEvent
    public static void onStartTracking(PlayerEvent.StartTracking event)
    {
        if (event.getEntity() instanceof ServerPlayer viewer
                && event.getTarget() instanceof ServerPlayer subject)
        {
            CommanderPoseState.syncTo(viewer, subject);
        }
    }

    @SubscribeEvent
    public static void onLogin(PlayerEvent.PlayerLoggedInEvent event)
    {
        if (event.getEntity() instanceof ServerPlayer player)
        {
            player.getPersistentData().remove("ProjectSeeleCommanderPose");
        }
    }
}
