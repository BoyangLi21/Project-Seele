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
    {draw(name,poses,buffers,light,0);}
    private static float hoistY(float y,float extension){return y-extension*net.minecraft.util.Mth.clamp((-11-y)/21,0,1);}
    private static void draw(String name,PoseStack poses,MultiBufferSource buffers,int light,float extension)
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
            float ux=a[i+6]-a[i],uy=hoistY(a[i+7],extension)-hoistY(a[i+1],extension),uz=a[i+8]-a[i+2],vx=a[i+12]-a[i],vy=hoistY(a[i+13],extension)-hoistY(a[i+1],extension),vz=a[i+14]-a[i+2];
            float nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx,length=(float)Math.sqrt(nx*nx+ny*ny+nz*nz);if(length<1e-6)continue;nx/=length;ny/=length;nz/=length;
            for(int j:TRIANGLE_AS_QUAD)
            {
                int k=i+j*6;out.vertex(m,a[k],hoistY(a[k+1],extension),a[k+2]).color((int)a[k+3],(int)a[k+4],(int)a[k+5],255).uv(j==0?0:1,j<2?0:1).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(light).normal(normal,nx,ny,nz).endVertex();
            }
        }
    }
    public UNTransportRenderer(EntityRendererProvider.Context context){super(context);shadowRadius=0;}
    @Override public ResourceLocation getTextureLocation(UNTransportEntity entity){return entity.isNerv()?com.projectseele.client.TreeOfLifeWallClient.nervLogoTexture(net.minecraft.client.Minecraft.getInstance()):com.projectseele.client.UNIdentityClient.logoTexture();}
    @Override public void render(UNTransportEntity entity,float yaw,float partial,PoseStack poses,MultiBufferSource buffers,int light)
    {
        poses.pushPose();
        if(entity.carrying()&&entity.level().getEntity(entity.cargoEntityId()) instanceof com.projectseele.entity.EvaUnit01Entity eva)
        {
            var wanted=eva.hasActiveCarrierMotion()?eva.carrierRenderPosition(partial):eva.getPosition(partial);var current=entity.getPosition(partial);
            poses.translate(wanted.x-current.x,wanted.y+entity.hoistDistance()-current.y,wanted.z-current.z);yaw=eva.getYRot();
        }
        poses.mulPose(Axis.YP.rotationDegrees(-yaw));
        if(entity.groundCart()){draw("un_ground_carrier",poses,buffers,light);poses.popPose();return;}
        draw("un_transport_body",poses,buffers,light);
        if(entity.rig(partial)>.001F)
        {
            float extension=entity.hoistDistance()-84;
            poses.pushPose();poses.translate(0,-11,0);poses.scale(1,entity.rig(partial),1);poses.translate(0,11,0);
            draw("un_transport_clamps",poses,buffers,light,extension);
            for(int side:new int[]{-1,1}){poses.pushPose();poses.translate(side*4*entity.jaws(partial),-extension,0);draw("un_transport_jaw_"+side,poses,buffers,light);poses.popPose();}
            poses.popPose();
        }
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
