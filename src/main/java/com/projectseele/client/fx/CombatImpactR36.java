package com.projectseele.client.fx;

import com.projectseele.network.ClientboundCombatImpactR36;
import com.projectseele.config.SeeleConfig;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Matrix4f;
import java.util.ArrayList;

/** Brief directional contact streaks; no blast, damage radius or terrain edits. */
@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class CombatImpactR36
{
    private record Hit(ClientboundCombatImpactR36 value,long start){}
    private static final ArrayList<Hit> HITS=new ArrayList<>();
    private static Object world;
    public static void add(ClientboundCombatImpactR36 value)
    {
        var level=Minecraft.getInstance().level;if(level==null)return;
        if(world!=level){HITS.clear();world=level;}
        if(!Double.isFinite(value.point().lengthSqr())||!Float.isFinite(value.strength()))return;
        if(HITS.size()>=48)HITS.remove(0);HITS.add(new Hit(value,level.getGameTime()));
    }
    @SubscribeEvent public static void render(RenderLevelStageEvent event)
    {
        if(event.getStage()!=RenderLevelStageEvent.Stage.AFTER_PARTICLES)return;var mc=Minecraft.getInstance();if(mc.level==null)return;
        if(world!=mc.level){HITS.clear();world=mc.level;return;}
        double now=mc.level.getGameTime()+event.getPartialTick();HITS.removeIf(h->now-h.start>6||now<h.start);
        float intensity=SeeleConfig.FX_INTENSITY.get().floatValue();if(HITS.isEmpty()||intensity<=0)return;
        var buffers=mc.renderBuffers().bufferSource();var type=RenderType.lightning();var out=buffers.getBuffer(type);var matrix=event.getPoseStack().last().pose();var camera=event.getCamera().getPosition();
        for(var h:HITS)
        {
            float age=(float)(now-h.start),u=age/6;var p=h.value;
            Vec3 n=p.direction().scale(-1).normalize(),x=n.cross(Math.abs(n.y)<.9?new Vec3(0,1,0):new Vec3(1,0,0)).normalize(),y=n.cross(x);
            Vec3 centre=p.point().subtract(camera);float alpha=(1-u)*(1-u)*Math.min(1,intensity);double radius=(2.8+4.5*p.strength())*(.35+.65*Math.sqrt(u));
            for(int i=0;i<9;i++)
            {
                double angle=i*Math.PI*2/9+.13;Vec3 direction=x.scale(Math.cos(angle)).add(y.scale(Math.sin(angle))).add(n.scale(.25)).normalize();
                double length=radius*(.58+(i*17%7)*.07);Vec3 tail=centre.add(direction.scale(length*(.12+.58*u))),tip=centre.add(direction.scale(length));
                Vec3 width=direction.cross(centre.add(camera).subtract(event.getCamera().getPosition()).normalize()).normalize().scale((p.armor()?.17:.13)*(1-u));
                vertex(out,matrix,tail.subtract(width),alpha,p.armor());vertex(out,matrix,tail.add(width),alpha,p.armor());vertex(out,matrix,tip,0,p.armor());vertex(out,matrix,tip,0,p.armor());
            }
        }
        buffers.endBatch(type);
    }
    private static void vertex(VertexConsumer out,Matrix4f m,Vec3 p,float alpha,boolean armor)
    {out.vertex(m,(float)p.x,(float)p.y,(float)p.z).color(1F,armor?.82F:.91F,armor?.51F:.81F,alpha).endVertex();}
    private CombatImpactR36(){}
}
