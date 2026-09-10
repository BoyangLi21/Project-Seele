package com.projectseele.client;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaImpactResponse;
import com.projectseele.network.ClientboundImpactResponsePacket;
import com.projectseele.world.EvaPilotResolver;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class EvaImpactClient
{
    public static void receive(ClientboundImpactResponsePacket p)
    {
        var level=Minecraft.getInstance().level;if(level!=null&&level.getEntity(p.entity()) instanceof LivingEntity actor)EvaImpactResponse.add(actor,p.tick(),p.direction(),p.strength(),p.height());
    }
    @SubscribeEvent public static void camera(ViewportEvent.ComputeCameraAngles event)
    {
        var mc=Minecraft.getInstance();if(mc.player==null||mc.getCameraEntity()!=mc.player||!mc.options.getCameraType().isFirstPerson())return;var eva=EvaPilotResolver.controlTarget(mc.player);if(eva==null||eva.isFirstBattleActive())return;
        var p=EvaImpactResponse.sample(eva,(float)event.getPartialTick());float scale=com.projectseele.config.SeeleConfig.FX_INTENSITY.get().floatValue();event.setRoll(event.getRoll()+(p.roll()+p.pitch()*.22F)*7*scale);
    }
    private EvaImpactClient() {}
}
