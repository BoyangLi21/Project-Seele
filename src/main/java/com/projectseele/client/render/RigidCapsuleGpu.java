package com.projectseele.client.render;

import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.*;
import com.projectseele.ProjectSeele;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.ShaderInstance;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterShadersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Matrix4f;
import java.io.IOException;
import java.util.IdentityHashMap;
import java.util.Map;

/** Rigid local parts keep their real bone matrices and exact UVs on the GPU. Weighted seams stay on their existing path. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT,bus=Mod.EventBusSubscriber.Bus.MOD)
public final class RigidCapsuleGpu
{
    private static ShaderInstance shader;
    private static final Map<Object,VertexBuffer> PARTS=new IdentityHashMap<>();
    public static long drawCalls;
    @SubscribeEvent public static void register(RegisterShadersEvent event)throws IOException
    {
        event.registerShader(new ShaderInstance(event.getResourceProvider(),new ResourceLocation(ProjectSeele.MODID,"rigid_capsule"),DefaultVertexFormat.NEW_ENTITY),instance->{shader=instance;ProjectSeele.LOGGER.info("Rigid local-mesh GPU shader ready");});
    }
    public static boolean draw(Object key,float[] vertices,int stride,float px,float py,float pz,
                               ResourceLocation texture,PoseStack poses,int light,int overlay)
    {
        if(shader==null||Boolean.getBoolean("projectseele.disableRigidCapsuleGpu"))return false;
        VertexBuffer mesh=PARTS.get(key);
        if(mesh==null)
        {
            int count=vertices.length/stride/3*4;
            BufferBuilder builder=new BufferBuilder(Math.max(1024,count*DefaultVertexFormat.NEW_ENTITY.getVertexSize()+64));
            builder.begin(VertexFormat.Mode.QUADS,DefaultVertexFormat.NEW_ENTITY);
            for(int i=0;i+stride*3<=vertices.length;i+=stride*3)
            {
                vertex(builder,vertices,i,px,py,pz);vertex(builder,vertices,i+stride,px,py,pz);vertex(builder,vertices,i+stride*2,px,py,pz);vertex(builder,vertices,i+stride*2,px,py,pz);
            }
            mesh=new VertexBuffer(VertexBuffer.Usage.STATIC);mesh.bind();mesh.upload(builder.end());VertexBuffer.unbind();PARTS.put(key,mesh);
            if(PARTS.size()==1)ProjectSeele.LOGGER.info("Rigid local-mesh GPU draw path active; first part vertices={}",count);
        }
        var type=RenderType.entityCutoutNoCull(texture);type.setupRenderState();RenderSystem.setShader(()->shader);
        shader.safeGetUniform("BoneMat").set(poses.last().pose());shader.safeGetUniform("BoneNormal").set(poses.last().normal());
        shader.safeGetUniform("FrameLight").set((float)(light&65535),(float)(light>>>16&65535));
        shader.safeGetUniform("FrameOverlay").set((float)(overlay&65535),(float)(overlay>>>16&65535));
        mesh.bind();mesh.drawWithShader(RenderSystem.getModelViewMatrix(),RenderSystem.getProjectionMatrix(),shader);VertexBuffer.unbind();type.clearRenderState();drawCalls++;return true;
    }
    private static void vertex(BufferBuilder b,float[] a,int i,float px,float py,float pz)
    {
        b.vertex(-(a[i]+px)/16,(a[i+1]+py)/16,(a[i+2]+pz)/16,1,1,1,1,a[i+3],a[i+4],0,0,-a[i+5],a[i+6],a[i+7]);
    }
    public static void clear()
    {
        Runnable release=()->{PARTS.values().forEach(VertexBuffer::close);PARTS.clear();};
        if(RenderSystem.isOnRenderThread())release.run();else RenderSystem.recordRenderCall(release::run);
    }
    private RigidCapsuleGpu() {}
}
