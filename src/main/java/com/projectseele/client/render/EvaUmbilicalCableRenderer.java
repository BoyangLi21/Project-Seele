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

/** Client-only catenary ribbon between a connected EVA and its power pylon. */
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
        VertexConsumer consumer = buffers.getBuffer(RenderType.lightning());
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
            Vec3 lumbarSocket = unit.getUmbilicalSocketPosition();
            Vec3 rear = unit.getRearDirection();
            Vec3 right = new Vec3(-rear.z, 0.0D, rear.x);
            Vec3 collarOuter = lumbarSocket.add(rear.scale(0.72D));
            Vec3 adapterHub = lumbarSocket.add(0.0D, 0.34D, 0.0D);
            Vec3 mountLeft = armourMount.subtract(right.scale(0.62D))
                    .add(0.0D, -0.16D, 0.0D);
            Vec3 mountRight = armourMount.add(right.scale(0.62D))
                    .add(0.0D, -0.16D, 0.0D);

            // A rigid silver/red three-point adapter is part of the EVA, not
            // unsupported cable.  It runs down the centreline from the rear
            // armour mount and provides a visible collar for the flexible lead.
            RibbonRenderer.drawStarRibbon(pose, consumer,
                    vector(armourMount), vector(lumbarSocket),
                    0.52F, 0.62F, 0.34F, 0.38F, 0.43F, 1.0F);
            RibbonRenderer.drawStarRibbon(pose, consumer,
                    vector(armourMount.add(0.0D, -0.22D, 0.0D)),
                    vector(lumbarSocket.add(0.0D, 0.18D, 0.0D)),
                    0.16F, 0.20F, 0.95F, 0.20F, 0.08F, 1.0F);
            RibbonRenderer.drawStarRibbon(pose, consumer,
                    vector(mountLeft), vector(adapterHub),
                    0.22F, 0.28F, 0.34F, 0.38F, 0.43F, 1.0F);
            RibbonRenderer.drawStarRibbon(pose, consumer,
                    vector(mountRight), vector(adapterHub),
                    0.22F, 0.28F, 0.34F, 0.38F, 0.43F, 1.0F);
            RibbonRenderer.drawStarRibbon(pose, consumer,
                    vector(lumbarSocket.subtract(rear.scale(0.12D))),
                    vector(collarOuter),
                    0.72F, 0.48F, 0.55F, 0.08F, 0.05F, 1.0F);

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
        buffers.endBatch(RenderType.lightning());
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
}
