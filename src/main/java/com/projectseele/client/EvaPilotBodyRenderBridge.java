package com.projectseele.client;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.world.EvaPilotResolver;
import net.minecraft.client.Minecraft;
import net.minecraft.util.Mth;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** A head-height camera must not lose its own vehicle's hands to section culling. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class EvaPilotBodyRenderBridge
{
    private static int rendered=-1;
    public static void beginPass() { rendered=-1; }
    public static void mark(EvaUnit01Entity eva) { rendered=eva.getId(); }

    @SubscribeEvent
    public static void render(RenderLevelStageEvent event)
    {
        if(event.getStage()!=RenderLevelStageEvent.Stage.AFTER_ENTITIES)return;
        var mc=Minecraft.getInstance();
        if(mc.player==null||!mc.options.getCameraType().isFirstPerson())return;
        var eva=EvaPilotResolver.controlTarget(mc.getCameraEntity());
        if(eva==null||!eva.isPoweredOn()||rendered==eva.getId())return;
        float partial=event.getPartialTick();var camera=event.getCamera().getPosition();
        var buffers=mc.renderBuffers().bufferSource();var dispatcher=mc.getEntityRenderDispatcher();
        dispatcher.render(eva,Mth.lerp(partial,eva.xOld,eva.getX())-camera.x,
                Mth.lerp(partial,eva.yOld,eva.getY())-camera.y,Mth.lerp(partial,eva.zOld,eva.getZ())-camera.z,
                Mth.rotLerp(partial,eva.yRotO,eva.getYRot()),partial,event.getPoseStack(),buffers,
                dispatcher.getPackedLightCoords(eva,partial));
        buffers.endBatch();
    }
}
