package com.projectseele;

import com.projectseele.alarm.AngelAlarmSystem;
import com.projectseele.entity.Angel;
import com.projectseele.entity.RamielEntity;
import com.projectseele.event.ThirdImpactDirector;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Mob;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingChangeTargetEvent;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppedEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
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

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent event)
    {
        if (event.phase == TickEvent.Phase.END && event.getServer().getTickCount() % 20 == 0)
        {
            AngelAlarmSystem.validate(event.getServer());
        }
    }

    @SubscribeEvent
    public static void onPlayerLoggedIn(PlayerEvent.PlayerLoggedInEvent event)
    {
        if (event.getEntity() instanceof ServerPlayer player)
        {
            AngelAlarmSystem.syncTo(player);
            ThirdImpactDirector.syncTo(player);
        }
    }

    @SubscribeEvent
    public static void onPlayerChangedDimension(PlayerEvent.PlayerChangedDimensionEvent event)
    {
        if (event.getEntity() instanceof ServerPlayer player)
        {
            ThirdImpactDirector.syncTo(player);
        }
    }

    @SubscribeEvent
    public static void onPlayerRespawn(PlayerEvent.PlayerRespawnEvent event)
    {
        if (event.getEntity() instanceof ServerPlayer player)
        {
            ThirdImpactDirector.syncTo(player);
        }
    }

    @SubscribeEvent
    public static void onServerStopped(ServerStoppedEvent event)
    {
        AngelAlarmSystem.reset();
    }
}
