package com.projectseele;

import com.projectseele.alarm.AngelAlarmSystem;
import com.projectseele.capability.EvaPilotCapability;
import com.projectseele.capability.EvaPilotProvider;
import com.projectseele.entity.Angel;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.RamielEntity;
import com.projectseele.event.ThirdImpactDirector;
import com.projectseele.world.MagiDeepLabBuilder;
import com.projectseele.world.NervCommandTelemetry;
import com.projectseele.world.NervOperationsConsole;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
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
            if (event.getSource().getEntity() instanceof ServerPlayer pilot
                    && pilot.getVehicle() instanceof EvaUnit01Entity)
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

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END)
        {
            return;
        }
        if (event.getServer().getTickCount()
                % NervCommandTelemetry.REFRESH_INTERVAL_TICKS == 0)
        {
            NervCommandTelemetry.tick(event.getServer());
            MagiDeepLabBuilder.tick(event.getServer());
        }
        if (event.getServer().getTickCount() % 20 == 0)
        {
            AngelAlarmSystem.validate(event.getServer());
        }
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
    public static void onRightClickBlock(PlayerInteractEvent.RightClickBlock event)
    {
        if (event.getHand() == InteractionHand.MAIN_HAND
                && event.getEntity() instanceof ServerPlayer player)
        {
            // Do not cancel the vanilla button use: its powered animation and
            // click sound are the physical acknowledgement for the operator.
            if (!NervOperationsConsole.handleUse(player, event.getPos()))
            {
                MagiDeepLabBuilder.handleUse(player, event.getPos());
            }
        }
    }

    @SubscribeEvent
    public static void onEntityTravelToDimension(EntityTravelToDimensionEvent event)
    {
        EvaUnit01Entity eva = event.getEntity() instanceof EvaUnit01Entity unit ? unit
                : event.getEntity().getVehicle() instanceof EvaUnit01Entity ridden ? ridden : null;
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
    }
}
