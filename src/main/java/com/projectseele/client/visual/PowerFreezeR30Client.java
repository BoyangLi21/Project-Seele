package com.projectseele.client.visual;

import com.projectseele.visual.PowerFreezeR30Review;
import com.projectseele.entity.*;
import com.projectseele.client.render.*;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.*;
import net.minecraftforge.fml.common.Mod;
import java.util.*;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class PowerFreezeR30Client
{
    private static int end;private static float[] frozen;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!PowerFreezeR30Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        if(mc.screen instanceof net.minecraft.client.gui.screens.DeathScreen){if(mc.player.isDeadOrDying())mc.player.respawn();mc.setScreen(null);return;}
        mc.options.pauseOnLostFocus=false;mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);mc.setCameraEntity(mc.player);
        PowerFreezeR30Review.tracked=mc.level.getEntity(PowerFreezeR30Review.actor)!=null;
        PowerFreezeR30Review.mounted=mc.player.getRootVehicle().getId()==PowerFreezeR30Review.actor;
        mc.options.keyUp.setDown(PowerFreezeR30Review.move);mc.player.setYRot(0);mc.player.setXRot(12);
        if(PowerFreezeR30Review.finished&&++end>30){mc.options.keyUp.setDown(false);mc.stop();}
    }
    @SubscribeEvent(priority=EventPriority.LOWEST) public static void frame(RenderLevelStageEvent event)
    {
        if(!PowerFreezeR30Review.ENABLED||event.getStage()!=RenderLevelStageEvent.Stage.AFTER_ENTITIES)return;var mc=Minecraft.getInstance();
        if(mc.level==null||!(mc.level.getEntity(PowerFreezeR30Review.actor) instanceof EvaUnit01Entity eva)||EvaShutdownR30.mode(eva)!=EvaShutdownR30.POWER_LOCK||eva.level().getGameTime()-EvaShutdownR30.since(eva)<20)return;
        PowerFreezeR30Review.firstPerson=mc.options.getCameraType().isFirstPerson()&&mc.getCameraEntity()==mc.player;
        if(!(mc.getEntityRenderDispatcher().getRenderer(eva) instanceof EvaUnit01Renderer renderer))return;
        var model=renderer.getGeoModel().getBakedModel(renderer.getGeoModel().getModelResource(eva));var values=new ArrayList<Float>();
        for(String name:EvaPoseGraph.contract().boneOrder())model.getBone(name).ifPresent(b->{for(float n:new float[]{b.getRotX(),b.getRotY(),b.getRotZ(),b.getPosX(),b.getPosY(),b.getPosZ()})values.add(n);});
        if(frozen==null){frozen=new float[values.size()];for(int i=0;i<frozen.length;i++)frozen[i]=values.get(i);}
        else for(int i=0;i<frozen.length;i++)if(!Float.isFinite(values.get(i))||Math.abs(frozen[i]-values.get(i))>1e-4)PowerFreezeR30Review.stable=false;
        PowerFreezeR30Review.frames++;
    }
    private PowerFreezeR30Client(){}
}
