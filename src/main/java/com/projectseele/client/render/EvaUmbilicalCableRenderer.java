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
            Vec3 start = Vec3.atCenterOf(anchor).add(0.0D, 0.65D, 0.0D);
            Vec3 backward = Vec3.directionFromRotation(0.0F, unit.getYRot())
                    .scale(-3.2D);
            Vec3 end = unit.position().add(backward).add(0.0D, 18.5D, 0.0D);
            double sag = Math.min(10.0D, start.distanceTo(end) * 0.18D);
            Vec3 previous = cablePoint(start, end, sag, 0.0D);
            for (int segment = 1; segment <= SEGMENTS; segment++)
            {
                double t = segment / (double) SEGMENTS;
                Vec3 current = cablePoint(start, end, sag, t);
                RibbonRenderer.drawStarRibbon(pose, consumer,
                        vector(previous), vector(current),
                        0.13F, 0.13F, 1.0F, 0.30F, 0.015F, 0.86F);
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