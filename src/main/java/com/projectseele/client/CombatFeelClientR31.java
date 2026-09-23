package com.projectseele.client;

import com.projectseele.entity.*;
import com.projectseele.network.ClientboundCombatFeelR31;
import com.projectseele.world.EvaPilotResolver;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class CombatFeelClientR31
{
    public static void receive(ClientboundCombatFeelR31 p)
    {
        var mc=Minecraft.getInstance();if(mc.level!=null&&mc.level.getEntity(p.entity()) instanceof LivingEntity actor)
        {CombatFeelR31.receive(actor,p.beat(),p.phase());if(p.beat().kind()==CombatFeelR31.THROWN)actor.setDeltaMovement(p.beat().direction());}
    }
    @SubscribeEvent public static void camera(ViewportEvent.ComputeCameraAngles e)
    {
        var mc=Minecraft.getInstance();if(mc.player==null||mc.getCameraEntity()!=mc.player)return;var eva=EvaPilotResolver.controlTarget(mc.player);if(eva==null)return;
        var b=CombatFeelR31.beat(eva);if(b==null)return;float t=CombatFeelR31.age(eva,(float)e.getPartialTick());
        float pulse=(float)(Math.exp(-t/3.5)*Math.sin(t*1.15))*b.strength()*com.projectseele.config.SeeleConfig.FX_INTENSITY.get().floatValue();
        e.setPitch(e.getPitch()+pulse*(b.kind()==CombatFeelR31.CONTACT?.65F:1.4F));
        e.setRoll(e.getRoll()+pulse*(b.kind()==CombatFeelR31.CONTACT?.22F:.6F));
    }
    private CombatFeelClientR31() {}
}
