package com.projectseele.client.fx;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaPrototypeEntity;
import com.projectseele.client.render.*;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.RenderType;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Vector3f;
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class EvaUNLaserEffects
{
    @SubscribeEvent public static void render(RenderLevelStageEvent event)
    {
        if(event.getStage()!=RenderLevelStageEvent.Stage.AFTER_PARTICLES)return;var mc=Minecraft.getInstance();if(mc.level==null)return;var buffers=mc.renderBuffers().bufferSource();var type=RenderType.debugQuads();var v=buffers.getBuffer(type);var stack=event.getPoseStack();boolean used=false;
        for(var e:mc.level.entitiesForRendering())if(e instanceof EvaPrototypeEntity un&&un.isEyeLaserActive())
        {
            float t=un.eyeLaserAge(event.getPartialTick());var eye=EvaUNLaserPose.eye(un,event.getPartialTick());var cam=event.getCamera().getPosition();stack.pushPose();stack.translate(eye.x-cam.x,eye.y-cam.y,eye.z-cam.z);var pose=stack.last().pose();var direction=net.minecraft.world.phys.Vec3.directionFromRotation(un.eyeAimPitch(),un.eyeAimYaw()).toVector3f();var basis=RibbonRenderer.planeBasis(direction);
            if(t<8)RibbonRenderer.drawPolyRing(pose,v,basis[0],basis[1],24,.16F+t*.035F,.045F,1,.75F,.25F,Math.min(1,t/4));
            else
            {
                float a=Math.max(0,1-(t-8)/12);var end=un.eyeLaserEnd().subtract(eye).toVector3f();RibbonRenderer.drawStarRibbon(pose,v,new Vector3f(),end,.26F,.16F,1,.63F,.14F,a*.6F);RibbonRenderer.drawStarRibbon(pose,v,new Vector3f(),end,.09F,.06F,1,.98F,.82F,a);
            }
            stack.popPose();used=true;
        }
        if(used)buffers.endBatch(type);
    }
}
