package com.projectseele.client.render;

import com.projectseele.entity.UNTransportEntity;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.*;
import net.minecraft.client.renderer.entity.*;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import com.google.gson.JsonParser;
import java.util.*;

public final class UNTransportRenderer extends EntityRenderer<UNTransportEntity>
{
    private static final ResourceLocation PAINT=new ResourceLocation("minecraft","textures/block/white_concrete.png");
    private static final Map<String,float[]> PARTS=new HashMap<>();
    private static final int[] TRIANGLE_AS_QUAD={0,1,2,2};
    private static void draw(String name,PoseStack poses,MultiBufferSource buffers,int light)
    {
        if(PARTS.isEmpty())
        {
            try(var reader=net.minecraft.client.Minecraft.getInstance().getResourceManager().getResource(new ResourceLocation("projectseele","mesh/tv_facilities_r16.json")).orElseThrow().openAsReader())
            {
                for(var row:JsonParser.parseReader(reader).getAsJsonObject().getAsJsonObject("parts").entrySet())
                    if(row.getKey().startsWith("un_")){var a=row.getValue().getAsJsonArray();float[] values=new float[a.size()];for(int i=0;i<a.size();i++)values[i]=a.get(i).getAsFloat();PARTS.put(row.getKey(),values);}
            }
            catch(Exception error){throw new IllegalStateException("UN aircraft mesh could not be loaded",error);}
        }
        var a=PARTS.get(name);if(a==null)return;var out=buffers.getBuffer(RenderType.entityCutoutNoCull(PAINT));var m=poses.last().pose();var normal=poses.last().normal();
        for(int i=0;i<a.length;i+=18)
        {
            float ux=a[i+6]-a[i],uy=a[i+7]-a[i+1],uz=a[i+8]-a[i+2],vx=a[i+12]-a[i],vy=a[i+13]-a[i+1],vz=a[i+14]-a[i+2];
            float nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx,length=(float)Math.sqrt(nx*nx+ny*ny+nz*nz);if(length<1e-6)continue;nx/=length;ny/=length;nz/=length;
            for(int j:TRIANGLE_AS_QUAD)
            {
                int k=i+j*6;out.vertex(m,a[k],a[k+1],a[k+2]).color((int)a[k+3],(int)a[k+4],(int)a[k+5],255).uv(j==0?0:1,j<2?0:1).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(light).normal(normal,nx,ny,nz).endVertex();
            }
        }
    }
    public UNTransportRenderer(EntityRendererProvider.Context context){super(context);shadowRadius=0;}
    @Override public ResourceLocation getTextureLocation(UNTransportEntity entity){return com.projectseele.client.UNIdentityClient.logoTexture();}
    @Override public void render(UNTransportEntity entity,float yaw,float partial,PoseStack poses,MultiBufferSource buffers,int light)
    {
        poses.pushPose();
        if(entity.carrying()&&entity.level().getEntity(entity.cargoEntityId()) instanceof com.projectseele.entity.EvaPrototypeEntity eva)
        {
            var wanted=eva.hasActiveCarrierMotion()?eva.carrierRenderPosition(partial):eva.getPosition(partial);var current=entity.getPosition(partial);
            poses.translate(wanted.x-current.x,wanted.y+84-current.y,wanted.z-current.z);yaw=eva.getYRot();
        }
        poses.mulPose(Axis.YP.rotationDegrees(-yaw));
        if(entity.groundCart()){draw("un_ground_carrier",poses,buffers,light);poses.popPose();return;}
        draw("un_transport_body",poses,buffers,light);
        poses.pushPose();poses.translate(0,-11,0);poses.scale(1,.08F+.92F*entity.rig(partial),1);poses.translate(0,11,0);
        draw("un_transport_clamps",poses,buffers,light);
        for(int side:new int[]{-1,1}){poses.pushPose();poses.translate(side*4*entity.jaws(partial),0,0);draw("un_transport_jaw_"+side,poses,buffers,light);poses.popPose();}
        poses.popPose();
        int i=0;
        for(int[] rotor:new int[][]{{-29,-11},{29,-11},{-49,9},{49,9}})
        {
            poses.pushPose();poses.translate(rotor[0],4.8,rotor[1]);poses.mulPose(Axis.YP.rotationDegrees((entity.tickCount+partial)*47*(i%2==0?1:-1)));
            draw("un_transport_rotor_"+i++,poses,buffers,light);poses.popPose();
        }
        var texture=getTextureLocation(entity);
        if(texture!=null)
        {
            var out=buffers.getBuffer(RenderType.entityCutoutNoCull(texture));var m=poses.last().pose();var n=poses.last().normal();
            for(int side:new int[]{-1,1})
            {
                float x=side*12.04F;
                out.vertex(m,x,4,-8).color(255,255,255,255).uv(0,0).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(light).normal(n,side,0,0).endVertex();
                out.vertex(m,x,4,5).color(255,255,255,255).uv(1,0).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(light).normal(n,side,0,0).endVertex();
                out.vertex(m,x,-3,5).color(255,255,255,255).uv(1,1).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(light).normal(n,side,0,0).endVertex();
                out.vertex(m,x,-3,-8).color(255,255,255,255).uv(0,1).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(light).normal(n,side,0,0).endVertex();
            }
        }
        poses.popPose();super.render(entity,yaw,partial,poses,buffers,light);
    }
}
