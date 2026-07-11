package com.projectseele.event;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.MassProductionEvaEntity;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.fx.CrossExplosionFX;
import com.projectseele.fx.TreeOfLifeLayout;
import com.projectseele.network.ClientboundNukeFxPacket;
import com.projectseele.network.ClientboundThirdImpactPacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.registry.ModEntities;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.network.PacketDistributor;

/** Server-authoritative timeline for the Third Impact tableau. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class ThirdImpactDirector
{
    private static final List<Impact> ACTIVE = new ArrayList<>();

    private ThirdImpactDirector() {}

    public static void start(ServerLevel level, Vec3 origin, float yaw, boolean hasUnit)
    {
        Impact impact = new Impact(level, origin, yaw, hasUnit);
        ACTIVE.add(impact);
        broadcast(impact, "message.projectseele.impact_ascent");
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END || ACTIVE.isEmpty())
        {
            return;
        }
        Iterator<Impact> iterator = ACTIVE.iterator();
        while (iterator.hasNext())
        {
            Impact impact = iterator.next();
            impact.ticks++;
            if (impact.ticks == 100)
            {
                deployVessels(impact);
                broadcast(impact, "message.projectseele.impact_formation");
            }
            else if (impact.ticks == 300)
            {
                SeeleNetwork.CHANNEL.send(PacketDistributor.ALL.noArg(),
                        new ClientboundThirdImpactPacket(impact.origin.x, impact.origin.y,
                                impact.origin.z, impact.yaw, impact.hasUnit));
                broadcast(impact, "message.projectseele.impact_tree");
            }
            else if (impact.ticks == 560)
            {
                Vec3 centre = TreeOfLifeLayout.worldNode(impact.origin, impact.yaw, TreeOfLifeLayout.TIFERET);
                SeeleNetwork.CHANNEL.send(PacketDistributor.ALL.noArg(),
                        new ClientboundNukeFxPacket(centre.x, centre.y, centre.z, 3.6F, true));
                CrossExplosionFX.spawn(impact.level, centre, 1.6F);
                broadcast(impact, "message.projectseele.impact_threshold");
            }
            else if (impact.ticks == 760)
            {
                applyLclPhase(impact);
                broadcast(impact, "message.projectseele.impact_instrumentality");
            }
            else if (impact.ticks >= 1200)
            {
                finish(impact);
                iterator.remove();
            }
        }
    }

    @SubscribeEvent
    public static void onLevelUnload(LevelEvent.Unload event)
    {
        if (event.getLevel() instanceof ServerLevel level)
        {
            ACTIVE.removeIf(impact -> impact.level == level);
        }
    }

    private static void deployVessels(Impact impact)
    {
        float formationYaw = -(float) Math.toDegrees(impact.yaw);
        for (int i = 0; i < TreeOfLifeLayout.NODES.length; i++)
        {
            if (i == TreeOfLifeLayout.TIFERET)
            {
                continue;
            }
            MassProductionEvaEntity mass = ModEntities.MASS_PRODUCTION_EVA.get().create(impact.level);
            if (mass == null)
            {
                continue;
            }
            Vec3 node = TreeOfLifeLayout.worldNode(impact.origin, impact.yaw, i);
            mass.moveTo(node.x, node.y - mass.getBbHeight() * 0.5D, node.z, formationYaw, 0.0F);
            mass.yRotO = formationYaw;
            mass.yBodyRot = formationYaw;
            mass.yBodyRotO = formationYaw;
            mass.yHeadRot = formationYaw;
            mass.yHeadRotO = formationYaw;
            mass.setNoGravity(true);
            mass.setNoAi(true);
            mass.setPersistenceRequired();
            impact.level.addFreshEntity(mass);
        }
    }

    private static void applyLclPhase(Impact impact)
    {
        AABB area = new AABB(impact.origin, impact.origin).inflate(220.0D);
        for (ServerPlayer player : impact.level.getEntitiesOfClass(ServerPlayer.class, area))
        {
            player.addEffect(new MobEffectInstance(MobEffects.SLOW_FALLING, 20 * 45, 0));
            player.addEffect(new MobEffectInstance(MobEffects.ABSORPTION, 20 * 45, 3));
            player.addEffect(new MobEffectInstance(MobEffects.GLOWING, 20 * 45, 0));
        }
    }

    private static void finish(Impact impact)
    {
        if (!impact.hasUnit)
        {
            broadcast(impact, "message.projectseele.impact_complete");
            return;
        }
        AABB area = new AABB(impact.origin, impact.origin).inflate(240.0D);
        boolean accepted = impact.level.getEntitiesOfClass(EvaUnit01Entity.class, area,
                EvaUnit01Entity::isCrucified).stream().findAny().isPresent();
        if (accepted)
        {
            broadcast(impact, "message.projectseele.impact_accepted");
        }
        else
        {
            // Releasing the crucified Unit before the final phase rejects the
            // scenario; the nine inert vessels fall apart with the tableau.
            for (MassProductionEvaEntity mass :
                    impact.level.getEntitiesOfClass(MassProductionEvaEntity.class, area, e -> e.isNoAi()))
            {
                mass.discard();
            }
            broadcast(impact, "message.projectseele.impact_rejected");
        }
    }

    private static void broadcast(Impact impact, String key)
    {
        for (ServerPlayer player : impact.level.players())
        {
            if (player.position().distanceToSqr(impact.origin) < 420.0D * 420.0D)
            {
                player.displayClientMessage(Component.translatable(key), false);
            }
        }
    }

    private static final class Impact
    {
        final ServerLevel level;
        final Vec3 origin;
        final float yaw;
        final boolean hasUnit;
        int ticks;

        Impact(ServerLevel level, Vec3 origin, float yaw, boolean hasUnit)
        {
            this.level = level;
            this.origin = origin;
            this.yaw = yaw;
            this.hasUnit = hasUnit;
        }
    }
}
