package com.projectseele.world;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.UltramanAvatarEntity;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.EntityEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Lifecycle, collision size and avatar reconciliation for Ultraman. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID,
        bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class UltramanTransformEvents
{
    private UltramanTransformEvents() {}

    @SubscribeEvent
    public static void onPlayerTick(TickEvent.PlayerTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END
                || !(event.player instanceof ServerPlayer player))
        {
            return;
        }
        if (!UltramanTransformState.needsTick(player))
        {
            UltramanAvatarEntity.remove(player.serverLevel(), player);
            return;
        }
        float scale = UltramanTransformState.scale(player, 0.0F);
        player.refreshDimensions();
        if (scale > 1.01F)
        {
            UltramanAvatarEntity.reconcile(player.serverLevel(), player,
                    scale);
        }
        else
        {
            UltramanAvatarEntity.remove(player.serverLevel(), player);
        }
        UltramanTransformState.finishShrink(player);
    }

    @SubscribeEvent
    public static void onSize(EntityEvent.Size event)
    {
        if (!(event.getEntity() instanceof ServerPlayer player))
        {
            return;
        }
        float scale = UltramanTransformState.scale(player, 0.0F);
        if (scale <= 1.001F)
        {
            return;
        }
        event.setNewSize(event.getNewSize().scale(scale));
        event.setNewEyeHeight(event.getNewEyeHeight() * scale);
    }

    @SubscribeEvent
    public static void onStartTracking(PlayerEvent.StartTracking event)
    {
        if (event.getEntity() instanceof ServerPlayer viewer
                && event.getTarget() instanceof ServerPlayer subject)
        {
            UltramanTransformState.syncTo(viewer, subject);
        }
    }

    @SubscribeEvent
    public static void onLogin(PlayerEvent.PlayerLoggedInEvent event)
    {
        if (event.getEntity() instanceof ServerPlayer player)
        {
            UltramanTransformState.clear(player);
        }
    }

    @SubscribeEvent
    public static void onClone(PlayerEvent.Clone event)
    {
        if (event.getEntity() instanceof ServerPlayer player)
        {
            UltramanTransformState.clear(player);
        }
    }
}
