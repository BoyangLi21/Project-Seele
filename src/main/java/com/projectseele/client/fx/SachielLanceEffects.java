package com.projectseele.client.fx;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.SachielEntity;
import com.projectseele.entity.SachielStrike;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** A visible forearm bone shaft; no invisible remote damage or explosion. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class SachielLanceEffects
{
    @SubscribeEvent public static void render(RenderLevelStageEvent event)
    {
        if(event.getStage()!=RenderLevelStageEvent.Stage.AFTER_ENTITIES)return;var mc=Minecraft.getInstance();if(mc.level==null)return;
        var buffers=mc.renderBuffers().bufferSource();var buffer=buffers.getBuffer(RenderType.debugQuads());var stack=event.getPoseStack();Vec3 camera=event.getCamera().getPosition();
        for(var e:mc.level.entitiesForRendering())if(e instanceof SachielEntity actor&&actor.isStrikeActive()&&!actor.isFirstBattleActive())
        {
            var f=SachielStrike.sample(actor,event.getPartialTick());if(f.extend()<.02)continue;Vec3 axis=f.direction(),x=axis.cross(Math.abs(axis.y)<.9?new Vec3(0,1,0):new Vec3(1,0,0)).normalize(),y=axis.cross(x);Vec3 a=f.hand().subtract(camera),b=f.tip().subtract(camera);
            for(int i=0;i<8;i++)
            {
                double s=i*Math.PI/4,t=(i+1)*Math.PI/4;Vec3 p=x.scale(Math.cos(s)*.48).add(y.scale(Math.sin(s)*.48)),q=x.scale(Math.cos(t)*.48).add(y.scale(Math.sin(t)*.48));
                for(Vec3 v:new Vec3[]{a.add(p),a.add(q),b,b})buffer.vertex(stack.last().pose(),(float)v.x,(float)v.y,(float)v.z).color(242,224,165,255).endVertex();
            }
        }
        buffers.endBatch(RenderType.debugQuads());
    }
}
