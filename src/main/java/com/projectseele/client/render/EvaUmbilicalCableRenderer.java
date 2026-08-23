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
    private static final int SEGMENTS = 18;

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
            Vec3 armourMount = unit.getUmbilicalMountPosition();
            Vec3 plugTail = unit.getUmbilicalSocketPosition();
            Vec3 rear = unit.getRearDirection();
            Vec3 right = new Vec3(-rear.z, 0.0D, rear.x);
            Vec3 up = new Vec3(0.0D, 1.0D, 0.0D);
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

            double sag = Math.min(10.0D,
                    pylon.distanceTo(collarOuter) * 0.18D);
            Vec3 previous = cablePoint(pylon, collarOuter, sag, 0.0D);
            for (int segment = 1; segment <= SEGMENTS; segment++)
            {
                double t = segment / (double) SEGMENTS;
                Vec3 current = cablePoint(pylon, collarOuter, sag, t);
                RibbonRenderer.drawStarRibbon(pose, consumer,
                        vector(previous), vector(current),
                        0.18F, 0.18F, 0.07F, 0.075F, 0.085F, 1.0F);
                previous = current;
            }
        }
        poseStack.popPose();
        buffers.endBatch(hardwareLayer);
    }

    private static Vec3 cablePoint(Vec3 start, Vec3 end, double sag, double t)
    {
        return start.lerp(end, t).add(0.0D,
                -Math.sin(Math.PI * t) * sag, 0.0D);
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
