package com.projectseele.client.visual;

import com.mojang.blaze3d.vertex.*;
import com.projectseele.client.render.MeshVertexWriter;
import com.google.gson.JsonObject;
import org.joml.Matrix4f;
import org.joml.Matrix3f;
import java.nio.*;
import java.nio.file.*;
import java.util.Random;

/** Compare actual NEW_ENTITY vertex bytes with the old Mojang matrix/attribute path. */
public final class NativeVertexR11Audit
{
    public static void run(Path file)throws Exception
    {
        Random random=new Random(1109);BufferBuilder original=new BufferBuilder(65536),fast=new BufferBuilder(65536);float positionError=0;int normalError=0,attributeDifferences=0,vertices=0;
        for(int scene=0;scene<200;scene++)
        {
            Matrix4f pose=new Matrix4f().translation(random.nextFloat()*400-200,random.nextFloat()*400-200,random.nextFloat()*400-200).rotateXYZ(random.nextFloat()*6,random.nextFloat()*6,random.nextFloat()*6).scale(.4F+random.nextFloat()*5,.4F+random.nextFloat()*5,.4F+random.nextFloat()*5);Matrix3f normal=pose.normal(new Matrix3f());
            original.begin(VertexFormat.Mode.QUADS,DefaultVertexFormat.NEW_ENTITY);fast.begin(VertexFormat.Mode.QUADS,DefaultVertexFormat.NEW_ENTITY);
            for(int i=0;i<4;i++)
            {
                float x=random.nextFloat()*24-12,y=random.nextFloat()*24,z=random.nextFloat()*24-12,u=random.nextFloat(),v=random.nextFloat(),nx=random.nextFloat()-.5F,ny=random.nextFloat()-.5F,nz=random.nextFloat()-.5F;int light=random.nextInt(16)<<20|random.nextInt(16)<<4,overlay=random.nextInt(16)<<16|random.nextInt(16);
                original.vertex(pose,x,y,z).color(255,255,255,255).uv(u,v).overlayCoords(overlay).uv2(light).normal(normal,nx,ny,nz).endVertex();
                MeshVertexWriter.emit(fast,pose,normal,x,y,z,u,v,light,overlay,nx,ny,nz);vertices++;
            }
            var a=original.end();var b=fast.end();ByteBuffer aa=a.vertexBuffer().order(ByteOrder.nativeOrder()),bb=b.vertexBuffer().order(ByteOrder.nativeOrder());int stride=DefaultVertexFormat.NEW_ENTITY.getVertexSize();
            if(aa.remaining()!=bb.remaining())throw new IllegalStateException("Vertex buffer size changed");
            for(int i=0;i<4;i++)
            {
                for(int n=0;n<12;n+=4)positionError=Math.max(positionError,Math.abs(aa.getFloat(i*stride+n)-bb.getFloat(i*stride+n)));
                for(int n=12;n<32;n++)if(aa.get(i*stride+n)!=bb.get(i*stride+n))attributeDifferences++;
                for(int n=32;n<35;n++)normalError=Math.max(normalError,Math.abs(aa.get(i*stride+n)-bb.get(i*stride+n)));
            }
            a.release();b.release();
        }
        boolean pass=positionError<.0002F&&normalError<=1&&attributeDifferences==0;JsonObject report=new JsonObject();report.addProperty("vertices",vertices);report.addProperty("max_position_error",positionError);report.addProperty("max_normal_byte_error",normalError);report.addProperty("uv_color_light_overlay_differences",attributeDifferences);report.addProperty("passed",pass);Files.writeString(file,report.toString());if(!pass)throw new IllegalStateException("R11 native vertex equivalence: "+report);
    }
    private NativeVertexR11Audit() {}
}
