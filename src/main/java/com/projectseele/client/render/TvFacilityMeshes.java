package com.projectseele.client.render;

import com.google.gson.JsonParser;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaDorsalMechanism;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.SiloHatchMechanism;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.GameRenderer;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/** Original TV-style rigid machinery, with each moving assembly baked only once. */
public final class TvFacilityMeshes
{
    private static final Map<String,VertexBuffer> PARTS=new HashMap<>();
    private static boolean attempted;
    public static void clearCache()
    {
        Runnable release=()->{PARTS.values().forEach(VertexBuffer::close);PARTS.clear();attempted=false;};
        if(RenderSystem.isOnRenderThread())release.run();else RenderSystem.recordRenderCall(release::run);
    }
    private static void load()
    {
        if(attempted)return;attempted=true;
        try(var stream=Minecraft.getInstance().getResourceManager().open(new ResourceLocation(ProjectSeele.MODID,"mesh/tv_facilities_r16.json"));
            var reader=new InputStreamReader(stream,StandardCharsets.UTF_8))
        {
            var parts=JsonParser.parseReader(reader).getAsJsonObject().getAsJsonObject("parts");
            for(var part:parts.entrySet())
            {
                var vertices=part.getValue().getAsJsonArray();BufferBuilder builder=new BufferBuilder(262144);
                builder.begin(VertexFormat.Mode.TRIANGLES,DefaultVertexFormat.POSITION_COLOR);
                for(int i=0;i<vertices.size();i+=6)
                    builder.vertex(vertices.get(i).getAsDouble(),vertices.get(i+1).getAsDouble(),vertices.get(i+2).getAsDouble())
                            .color(vertices.get(i+3).getAsInt(),vertices.get(i+4).getAsInt(),vertices.get(i+5).getAsInt(),255).endVertex();
                VertexBuffer mesh=new VertexBuffer(VertexBuffer.Usage.STATIC);mesh.bind();mesh.upload(builder.end());VertexBuffer.unbind();PARTS.put(part.getKey(),mesh);
            }
            ProjectSeele.LOGGER.info("TV facility machinery loaded: {} rigid assemblies",PARTS.size());
        }
        catch(Exception e){ProjectSeele.LOGGER.error("TV facility machinery resource rejected",e);}
    }
    public static void draw(String part,PoseStack poses,int light)
    {
        load();VertexBuffer mesh=PARTS.get(part);if(mesh==null)return;
        var type=RenderType.debugQuads();type.setupRenderState();
        float illumination=.40F+.60F*Math.max((light>>4)&15,(light>>20)&15)/15F;
        RenderSystem.setShaderColor(illumination,illumination,illumination,1);
        mesh.bind();mesh.drawWithShader(poses.last().pose(),RenderSystem.getProjectionMatrix(),GameRenderer.getPositionColorShader());VertexBuffer.unbind();
        RenderSystem.setShaderColor(1,1,1,1);type.clearRenderState();
    }
    private static float ramp(float value,float a,float b){return EvaDorsalMechanism.smooth((value-a)/(b-a));}
    public static void cage(PoseStack poses,int light,float closed)
    {
        draw("cage_frame",poses,light);float opening=1-closed;
        for(int side:new int[]{-1,1})
        {
            poses.pushPose();poses.scale(side,1,1);
            float shoulder=5.35F*ramp(opening,.23F,.88F),arm=3.3F*ramp(opening,.12F,.83F),leg=7.4F*ramp(opening,.35F,.96F);
            poses.pushPose();poses.translate(shoulder,2.1*ramp(opening,0,.25F),0);draw("shoulder_pin",poses,light);poses.popPose();
            poses.pushPose();poses.translate(shoulder,0,0);draw("shoulder_jaw",poses,light);poses.popPose();
            rod(poses,light,"shoulder_rod",8.8F+shoulder,Math.max(.04F,5.1F-shoulder));
            poses.pushPose();poses.translate(arm,0,0);draw("arm_guard",poses,light);poses.popPose();
            rod(poses,light,"arm_rod",10.8F+arm,3.8F-arm);
            poses.pushPose();poses.translate(leg,0,0);draw("lower_jaw",poses,light);poses.popPose();
            rod(poses,light,"lower_rod",6.8F+leg,7.6F-leg);
            poses.pushPose();poses.translate(4.0*ramp(opening,0,.60F),0,0);draw("cage_front",poses,light);poses.popPose();
            poses.popPose();
        }
    }
    private static void rod(PoseStack poses,int light,String name,float x,float length)
    {
        poses.pushPose();poses.translate(x,0,0);poses.scale(length,1,1);draw(name,poses,light);poses.popPose();
    }
    public static void carrier(PoseStack poses,int light,EvaUnit01Entity unit,float partial)
    {
        draw("carrier_deck",poses,light);draw("carrier_spine",poses,light);
        float release=unit.getLaunchPhase()==EvaUnit01Entity.LAUNCH_CLEAR?ramp(1-(unit.getLaunchTicks()-partial)/18F,0,1):0;
        poses.pushPose();poses.translate(0,0,-3*release);draw("carrier_clamp",poses,light);poses.popPose();
    }
    public static void pressureDoors(PoseStack poses,int light,float open)
    {
        for(int side:new int[]{-1,1})
        {
            poses.pushPose();poses.scale(side,1,1);poses.translate(open*17,0,0);draw("pressure_leaf",poses,light);poses.popPose();
        }
    }
    public static void shaftHatch(PoseStack poses,int light,float open)
    {
        draw("hatch_frame",poses,light);
        for(int side:new int[]{-1,1})
        {
            poses.pushPose();poses.scale(side,1,1);
            draw("hatch_cassette",poses,light);
            for(int index=0;index<SiloHatchMechanism.PANELS;index++)
            {
                var panel=SiloHatchMechanism.panel(index,open);
                poses.pushPose();poses.translate(panel.x(),panel.y(),0);
                draw("hatch_panel",poses,light);poses.popPose();
            }
            poses.popPose();
        }
    }
    private TvFacilityMeshes() {}
}
