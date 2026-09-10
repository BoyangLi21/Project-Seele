package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.VertexConsumer;
import org.joml.Matrix4f;
import org.joml.Matrix3f;

/** Preserve Minecraft's vertex format while using BufferBuilder's complete-vertex fast path. */
public final class MeshVertexWriter
{
    public static void emit(VertexConsumer out,Matrix4f pose,Matrix3f normal,
                            float x,float y,float z,float u,float v,int light,int overlay,
                            float nx,float ny,float nz)
    {
        float px=pose.m00()*x+pose.m10()*y+pose.m20()*z+pose.m30();
        float py=pose.m01()*x+pose.m11()*y+pose.m21()*z+pose.m31();
        float pz=pose.m02()*x+pose.m12()*y+pose.m22()*z+pose.m32();
        float ax=normal.m00()*nx+normal.m10()*ny+normal.m20()*nz;
        float ay=normal.m01()*nx+normal.m11()*ny+normal.m21()*nz;
        float az=normal.m02()*nx+normal.m12()*ny+normal.m22()*nz;
        out.vertex(px,py,pz,1,1,1,1,u,v,overlay,light,ax,ay,az);
    }
    private MeshVertexWriter() {}
}
