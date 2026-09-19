package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.*;
import com.projectseele.entity.*;
import net.minecraft.client.renderer.*;
import org.joml.Vector3f;

/** Low intensity glow follows the physical whip, rather than an unrelated beam. */
final class ShamshelWhipLight
{
    static void render(ShamshelEntity actor,float partial,PoseStack pose,MultiBufferSource buffers)
    {
        if(!actor.isSweeping())return;
        float age=actor.sweepAge(partial),weight=ShamshelWhipMotion.envelope(age);if(weight<.04)return;
        var points=ShamshelWhipMotion.points(actor,age,partial);var origin=actor.getPosition(partial);var target=buffers.getBuffer(RenderType.lightning());
        for(int i=1;i<points.size();i++)
        {
            Vector3f a=points.get(i-1).subtract(origin).toVector3f(),b=points.get(i).subtract(origin).toVector3f();
            Vector3f axis=new Vector3f(b).sub(a).normalize(),normal=new Vector3f(axis).cross(0,1,0);
            if(normal.lengthSquared()<.001)normal.set(1,0,0);normal.normalize();var binormal=new Vector3f(axis).cross(normal).normalize();
            for(int ring=0;ring<6;ring++)
            {
                float t0=(float)(Math.PI*2*ring/6),t1=(float)(Math.PI*2*(ring+1)/6),radius=.25F;
                var n0=new Vector3f(normal).mul((float)Math.cos(t0)*radius).fma((float)Math.sin(t0)*radius,binormal);
                var n1=new Vector3f(normal).mul((float)Math.cos(t1)*radius).fma((float)Math.sin(t1)*radius,binormal);
                vertex(target,pose,new Vector3f(a).add(n0),weight);vertex(target,pose,new Vector3f(b).add(n0),weight);
                vertex(target,pose,new Vector3f(b).add(n1),weight);vertex(target,pose,new Vector3f(a).add(n1),weight);
            }
        }
    }
    private static void vertex(VertexConsumer target,PoseStack pose,Vector3f p,float alpha)
    {target.vertex(pose.last().pose(),p.x,p.y,p.z).color(.88F,.57F,.91F,alpha*.30F).endVertex();}
    private ShamshelWhipLight(){}
}
