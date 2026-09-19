package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.util.Mth;
import org.joml.Matrix4f;
import org.joml.Vector3f;

/**
 * Shared direct-vertex helpers for luminous energy geometry (beams, crosses,
 * rays). Uses POSITION_COLOR luminous passes, including lightning and the
 * depth-tested, non-depth-writing cross glow. Quads are emitted double-sided.
 */
public final class RibbonRenderer
{
    private RibbonRenderer() {}

    /**
     * Draws a beam as four flat ribbons crossed at 45° around the axis, so it
     * reads as a volumetric column from every angle. Width tapers start→end.
     */
    public static void drawStarRibbon(Matrix4f pose, VertexConsumer consumer, Vector3f start, Vector3f end,
                                      float startWidth, float endWidth, float r, float g, float b, float a)
    {
        Vector3f axis = new Vector3f(end).sub(start);
        if (axis.lengthSquared() < 1.0E-4F)
        {
            return;
        }
        axis.normalize();
        // Any vector not parallel to the axis yields a perpendicular basis.
        Vector3f seed = Math.abs(axis.y()) > 0.98F ? new Vector3f(1.0F, 0.0F, 0.0F) : new Vector3f(0.0F, 1.0F, 0.0F);
        Vector3f u = new Vector3f(axis).cross(seed).normalize();
        Vector3f v = new Vector3f(axis).cross(u).normalize();

        for (int i = 0; i < 4; i++)
        {
            float angle = (float) (i * Math.PI / 4.0D);
            float cos = Mth.cos(angle);
            float sin = Mth.sin(angle);
            Vector3f w = new Vector3f(
                    u.x() * cos + v.x() * sin,
                    u.y() * cos + v.y() * sin,
                    u.z() * cos + v.z() * sin);
            Vector3f s0 = new Vector3f(start).add(new Vector3f(w).mul(startWidth));
            Vector3f s1 = new Vector3f(start).sub(new Vector3f(w).mul(startWidth));
            Vector3f e0 = new Vector3f(end).add(new Vector3f(w).mul(endWidth));
            Vector3f e1 = new Vector3f(end).sub(new Vector3f(w).mul(endWidth));
            quadBothSides(pose, consumer, s0, s1, e1, e0, r, g, b, a);
        }
    }

    /** Continuous edge falloff for large light pillars, without opaque card edges. */
    public static void drawSoftStarRibbon(Matrix4f pose,VertexConsumer consumer,Vector3f start,Vector3f end,
                                         float startWidth,float endWidth,float r,float g,float b,float alpha)
    {
        Vector3f axis=new Vector3f(end).sub(start);if(axis.lengthSquared()<1e-4F)return;axis.normalize();
        Vector3f seed=Math.abs(axis.y())>.98F?new Vector3f(1,0,0):new Vector3f(0,1,0);
        Vector3f u=new Vector3f(axis).cross(seed).normalize(),v=new Vector3f(axis).cross(u).normalize();
        for(int plane=0;plane<4;plane++)
        {
            float angle=(float)(plane*Math.PI/4);Vector3f direction=new Vector3f(u).mul(Mth.cos(angle)).add(new Vector3f(v).mul(Mth.sin(angle)));
            for(int band=0;band<8;band++)
            {
                float left=-1+band*.25F,right=left+.25F;
                float a0=alpha*(1-left*left)*(1-left*left),a1=alpha*(1-right*right)*(1-right*right);
                Vector3f s0=new Vector3f(start).add(new Vector3f(direction).mul(startWidth*left));
                Vector3f s1=new Vector3f(start).add(new Vector3f(direction).mul(startWidth*right));
                Vector3f e0=new Vector3f(end).add(new Vector3f(direction).mul(endWidth*left));
                Vector3f e1=new Vector3f(end).add(new Vector3f(direction).mul(endWidth*right));
                putColorVertex(pose,consumer,s0,r,g,b,a0);putColorVertex(pose,consumer,s1,r,g,b,a1);
                putColorVertex(pose,consumer,e1,r,g,b,a1);putColorVertex(pose,consumer,e0,r,g,b,a0);
                putColorVertex(pose,consumer,e0,r,g,b,a0);putColorVertex(pose,consumer,e1,r,g,b,a1);
                putColorVertex(pose,consumer,s1,r,g,b,a1);putColorVertex(pose,consumer,s0,r,g,b,a0);
            }
        }
    }

    /**
     * Regular polygon ring in the plane spanned by (u, v), centred on the
     * local origin. Six sides = the A.T. Field hexagon.
     */
    public static void drawPolyRing(Matrix4f pose, VertexConsumer consumer, Vector3f u, Vector3f v,
                                    int sides, float radius, float halfWidth,
                                    float r, float g, float b, float a)
    {
        for (int i = 0; i < sides; i++)
        {
            float a0 = (float) (i * 2.0D * Math.PI / sides);
            float a1 = (float) ((i + 1) * 2.0D * Math.PI / sides);
            float in = radius - halfWidth;
            float out = radius + halfWidth;
            Vector3f d0 = new Vector3f(u).mul(Mth.cos(a0)).add(new Vector3f(v).mul(Mth.sin(a0)));
            Vector3f d1 = new Vector3f(u).mul(Mth.cos(a1)).add(new Vector3f(v).mul(Mth.sin(a1)));
            Vector3f p0 = new Vector3f(d0).mul(in);
            Vector3f p1 = new Vector3f(d0).mul(out);
            Vector3f p2 = new Vector3f(d1).mul(out);
            Vector3f p3 = new Vector3f(d1).mul(in);
            quadBothSides(pose, consumer, p0, p1, p2, p3, r, g, b, a);
        }
    }

    /** Builds an orthonormal basis (u, v) perpendicular to the given normal. */
    public static Vector3f[] planeBasis(Vector3f normal)
    {
        Vector3f n = new Vector3f(normal);
        if (n.lengthSquared() < 1.0E-6F)
        {
            n.set(0.0F, 1.0F, 0.0F);
        }
        n.normalize();
        Vector3f seed = Math.abs(n.y()) > 0.98F ? new Vector3f(1.0F, 0.0F, 0.0F) : new Vector3f(0.0F, 1.0F, 0.0F);
        Vector3f u = new Vector3f(n).cross(seed).normalize();
        Vector3f v = new Vector3f(n).cross(u).normalize();
        return new Vector3f[] {u, v};
    }

    /** Flat ring on the XZ plane centred on the local origin (shockwaves). */
    public static void drawGroundRing(Matrix4f pose, VertexConsumer consumer, float radius, float halfWidth,
                                      float r, float g, float b, float a)
    {
        int segments = 40;
        for (int i = 0; i < segments; i++)
        {
            float a0 = (float) (i * 2.0D * Math.PI / segments);
            float a1 = (float) ((i + 1) * 2.0D * Math.PI / segments);
            float in = radius - halfWidth;
            float out = radius + halfWidth;
            Vector3f p0 = new Vector3f(in * Mth.cos(a0), 0.0F, in * Mth.sin(a0));
            Vector3f p1 = new Vector3f(out * Mth.cos(a0), 0.0F, out * Mth.sin(a0));
            Vector3f p2 = new Vector3f(out * Mth.cos(a1), 0.0F, out * Mth.sin(a1));
            Vector3f p3 = new Vector3f(in * Mth.cos(a1), 0.0F, in * Mth.sin(a1));
            quadBothSides(pose, consumer, p0, p1, p2, p3, r, g, b, a);
        }
    }

    public static void quadBothSides(Matrix4f pose, VertexConsumer consumer,
                                     Vector3f a, Vector3f b, Vector3f c, Vector3f d,
                                     float r, float g, float bl, float al)
    {
        putColorVertex(pose, consumer, a, r, g, bl, al);
        putColorVertex(pose, consumer, b, r, g, bl, al);
        putColorVertex(pose, consumer, c, r, g, bl, al);
        putColorVertex(pose, consumer, d, r, g, bl, al);
        putColorVertex(pose, consumer, d, r, g, bl, al);
        putColorVertex(pose, consumer, c, r, g, bl, al);
        putColorVertex(pose, consumer, b, r, g, bl, al);
        putColorVertex(pose, consumer, a, r, g, bl, al);
    }

    public static void putColorVertex(Matrix4f pose, VertexConsumer consumer, Vector3f pos,
                                      float r, float g, float b, float a)
    {
        // Pulsing highlights may exceed 1. Packing 256 into an unsigned byte
        // wraps to zero, producing a dark flash at the brightest instant.
        consumer.vertex(pose, pos.x(), pos.y(), pos.z()).color(Mth.clamp(r,0,1),Mth.clamp(g,0,1),Mth.clamp(b,0,1),Mth.clamp(a,0,1)).endVertex();
    }
}
