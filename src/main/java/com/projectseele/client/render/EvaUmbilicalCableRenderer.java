package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.core.BlockPos;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Matrix4f;
import org.joml.Vector3f;

/** Client-only catenary lead and rigid upper-back plug for connected EVAs. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, value = Dist.CLIENT,
        bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class EvaUmbilicalCableRenderer
{
    private static final double RENDER_RANGE = 160.0D;

    private EvaUmbilicalCableRenderer() {}

    @SubscribeEvent
    public static void onRenderLevel(RenderLevelStageEvent event)
    {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_PARTICLES)
        {
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        ClientLevel level = minecraft.level;
        if (level == null || minecraft.player == null)
        {
            return;
        }

        AABB visible = minecraft.player.getBoundingBox().inflate(RENDER_RANGE);
        var units = level.getEntitiesOfClass(EvaUnit01Entity.class, visible,
                EvaUnit01Entity::isUmbilicalConnected);
        if (units.isEmpty())
        {
            return;
        }

        PoseStack poseStack = event.getPoseStack();
        Vec3 camera = event.getCamera().getPosition();
        MultiBufferSource.BufferSource buffers = minecraft.renderBuffers().bufferSource();
        // This is painted industrial hardware, not an energy beam.  The old
        // lightning layer was fullbright/additive and visibly flashed against
        // the armour as the camera moved. debugQuads is a stable POSITION_COLOR
        // layer with ordinary alpha blending and no emissive pulse.
        RenderType hardwareLayer = RenderType.debugQuads();
        VertexConsumer consumer = buffers.getBuffer(hardwareLayer);
        poseStack.pushPose();
        poseStack.translate(-camera.x, -camera.y, -camera.z);
        Matrix4f pose = poseStack.last().pose();
        for (EvaUnit01Entity unit : units)
        {
            BlockPos anchor = unit.getUmbilicalAnchor();
            if (anchor == null)
            {
                continue;
            }
            Vec3 pylon = Vec3.atCenterOf(anchor).add(0.0D, 0.65D, 0.0D);
            var attachment=EvaPowerAttachmentR25.frame(unit,event.getPartialTick());
            Vec3 armourMount = attachment.mount();
            Vec3 plugTail = attachment.socket();
            Vec3 rear = attachment.rear();
            Vec3 right = attachment.right();
            Vec3 up = attachment.up();
            Vec3 collarOuter = plugTail.add(rear.scale(0.35D));

            // A small fuel-nozzle-like plug: armour collar, dark rectangular
            // body, orange safety band and a short lower grip.  Drawing real
            // closed boxes gives the cable an unmistakable physical endpoint
            // without borrowing a luminous beam material.
            drawOrientedBox(pose, consumer,
                    armourMount.lerp(plugTail, 0.16D), right, up, rear,
                    1.12F, 0.92F, 0.36F,
                    0.28F, 0.31F, 0.34F, 1.0F);
            drawOrientedBox(pose, consumer,
                    armourMount.lerp(plugTail, 0.57D), right, up, rear,
                    0.78F, 0.70F, 1.05F,
                    0.10F, 0.12F, 0.14F, 1.0F);
            drawOrientedBox(pose, consumer,
                    armourMount.lerp(plugTail, 0.76D), right, up, rear,
                    0.88F, 0.76F, 0.18F,
                    0.88F, 0.30F, 0.04F, 1.0F);
            Vec3 gripCentre = plugTail.subtract(up.scale(0.72D))
                    .subtract(rear.scale(0.22D));
            drawOrientedBox(pose, consumer, gripCentre, right, up, rear,
                    0.34F, 0.78F, 0.30F,
                    0.11F, 0.12F, 0.13F, 1.0F);
            drawOrientedBox(pose, consumer, collarOuter, right, up, rear,
                    0.72F, 0.66F, 0.32F,
                    0.22F, 0.24F, 0.26F, 1.0F);

            var route=new java.util.ArrayList<Vec3>();route.add(collarOuter);
            Vec3 exit=collarOuter.add(rear.scale(2.2));route.add(exit);
            var hull=unit.getBoundingBox().inflate(1.5);
            if(hull.clip(exit,pylon).isPresent())
            {
                // When the unit turns its front towards the reel, take the
                // lead around the flank instead of drawing it through its chest.
                Vec3 lateral=new Vec3(right.x,0,right.z).normalize();
                if(pylon.subtract(unit.position()).dot(lateral)<0)lateral=lateral.scale(-1);
                double width=Math.max(16,unit.getBbWidth()*.5+6);
                Vec3 side=unit.getPosition(event.getPartialTick()).add(lateral.scale(width));
                route.add(new Vec3(side.x,Math.max(unit.getY()+1.5,
                        Math.min(exit.y-2,pylon.y+2)),side.z));
            }
            route.add(pylon);
            // Round the support-route corners before applying gravity. Hard
            // ninety-degree joints made a prone EVA's lead look like a rail.
            var rounded=new java.util.ArrayList<Vec3>();rounded.add(route.get(0));
            for(int corner=1;corner<route.size()-1;corner++)
            {
                Vec3 previous=route.get(corner-1),joint=route.get(corner),next=route.get(corner+1);
                double radius=Math.min(6,Math.min(previous.distanceTo(joint),joint.distanceTo(next))*.4);
                Vec3 entry=joint.add(previous.subtract(joint).normalize().scale(radius));
                Vec3 leave=joint.add(next.subtract(joint).normalize().scale(radius));
                rounded.add(entry);
                for(int step=1;step<=12;step++)
                {
                    double t=step/12.0;
                    rounded.add(entry.scale((1-t)*(1-t)).add(joint.scale(2*(1-t)*t)).add(leave.scale(t*t)));
                }
            }
            rounded.add(pylon);
            for(int leg=1;leg<rounded.size();leg++)
            {
                Vec3 a=rounded.get(leg-1),b=rounded.get(leg);double span=a.distanceTo(b);
                double sag=span<4?0:Math.min(16,span*.10);int segments=Math.max(2,Math.min(128,(int)Math.ceil(span/2)));
                Vec3 previous=a;
                for(int segment=1;segment<=segments;segment++)
                {
                    Vec3 current=cablePoint(a,b,sag,segment/(double)segments);
                    tube(pose,consumer,previous,current,.22F);previous=current;
                }
            }
        }
        poseStack.popPose();
        buffers.endBatch(hardwareLayer);
    }

    private static Vec3 cablePoint(Vec3 start, Vec3 end, double sag, double t)
    {
        Vec3 point = start.lerp(end, t).add(0.0D, -Math.sin(Math.PI * t) * sag, 0.0D);
        // Reel and back socket sit above the floor. Do not let increased
        // cable length turn the decorative sag into a subterranean loop.
        return new Vec3(point.x,Math.max(Math.min(start.y,end.y)-.55,point.y),point.z);
    }

    private static void tube(Matrix4f pose, VertexConsumer consumer, Vec3 a, Vec3 b, float radius)
    {
        Vec3 axis=b.subtract(a).normalize();
        Vec3 u=axis.cross(Math.abs(axis.y)>.95?new Vec3(1,0,0):new Vec3(0,1,0)).normalize();
        Vec3 v=axis.cross(u).normalize();
        for(int side=0;side<10;side++)
        {
            double t0=side*Math.PI/5,t1=(side+1)*Math.PI/5;
            Vec3 r0=u.scale(Math.cos(t0)*radius).add(v.scale(Math.sin(t0)*radius));
            Vec3 r1=u.scale(Math.cos(t1)*radius).add(v.scale(Math.sin(t1)*radius));
            float shade=.10F+.08F*(float)Math.max(0,u.scale(Math.cos((t0+t1)/2)).add(v.scale(Math.sin((t0+t1)/2))).y);
            RibbonRenderer.quadBothSides(pose,consumer,vector(a.add(r0)),vector(b.add(r0)),vector(b.add(r1)),vector(a.add(r1)),shade*.9F,shade,shade*1.05F,1);
        }
    }

    private static Vector3f vector(Vec3 value)
    {
        return new Vector3f((float) value.x, (float) value.y, (float) value.z);
    }

    private static void drawOrientedBox(Matrix4f pose, VertexConsumer consumer,
                                        Vec3 centre, Vec3 right, Vec3 up,
                                        Vec3 rear, float halfRight,
                                        float halfUp, float halfRear,
                                        float red, float green, float blue,
                                        float alpha)
    {
        Vector3f c = vector(centre);
        Vector3f r = vector(right.scale(halfRight));
        Vector3f u = vector(up.scale(halfUp));
        Vector3f b = vector(rear.scale(halfRear));
        Vector3f p000 = corner(c, r, u, b, -1, -1, -1);
        Vector3f p001 = corner(c, r, u, b, -1, -1, 1);
        Vector3f p010 = corner(c, r, u, b, -1, 1, -1);
        Vector3f p011 = corner(c, r, u, b, -1, 1, 1);
        Vector3f p100 = corner(c, r, u, b, 1, -1, -1);
        Vector3f p101 = corner(c, r, u, b, 1, -1, 1);
        Vector3f p110 = corner(c, r, u, b, 1, 1, -1);
        Vector3f p111 = corner(c, r, u, b, 1, 1, 1);
        RibbonRenderer.quadBothSides(pose, consumer, p000, p100, p110, p010,
                red, green, blue, alpha);
        RibbonRenderer.quadBothSides(pose, consumer, p101, p001, p011, p111,
                red, green, blue, alpha);
        RibbonRenderer.quadBothSides(pose, consumer, p001, p000, p010, p011,
                red, green, blue, alpha);
        RibbonRenderer.quadBothSides(pose, consumer, p100, p101, p111, p110,
                red, green, blue, alpha);
        RibbonRenderer.quadBothSides(pose, consumer, p010, p110, p111, p011,
                red, green, blue, alpha);
        RibbonRenderer.quadBothSides(pose, consumer, p001, p101, p100, p000,
                red, green, blue, alpha);
    }

    private static Vector3f corner(Vector3f centre, Vector3f right,
                                   Vector3f up, Vector3f rear,
                                   int rightSign, int upSign, int rearSign)
    {
        return new Vector3f(centre)
                .add(new Vector3f(right).mul(rightSign))
                .add(new Vector3f(up).mul(upSign))
                .add(new Vector3f(rear).mul(rearSign));
    }
}
