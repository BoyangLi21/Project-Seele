package com.projectseele.client.fx;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.client.render.RibbonRenderer;
import com.projectseele.network.ClientboundCrossExplosionPacket;
import com.projectseele.registry.ModSounds;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Matrix4f;
import org.joml.Vector3f;

/**
 * Owns every transient world-space visual that is not tied to an entity
 * renderer. Instances are spawned by S2C packets, aged by the client tick and
 * drawn after particles so they blend over the whole scene.
 */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class ClientFxManager
{
    private static final List<CrossExplosion> CROSS_EXPLOSIONS = new ArrayList<>();

    private ClientFxManager() {}

    public static void addCrossExplosion(ClientboundCrossExplosionPacket packet)
    {
        // fxIntensity 0 disables the visual entirely; the sound still plays.
        if (com.projectseele.config.SeeleConfig.FX_INTENSITY.get() > 0.0D)
        {
            CROSS_EXPLOSIONS.add(new CrossExplosion(new Vec3(packet.x, packet.y, packet.z), packet.scale));
        }
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level != null)
        {
            minecraft.level.playLocalSound(packet.x, packet.y, packet.z,
                    ModSounds.CROSS_EXPLOSION.get(), SoundSource.HOSTILE, 4.0F, 1.0F, false);
        }
    }

    public static void clear()
    {
        CROSS_EXPLOSIONS.clear();
    }

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END || Minecraft.getInstance().isPaused())
        {
            return;
        }
        if (Minecraft.getInstance().level == null)
        {
            CROSS_EXPLOSIONS.clear();
            return;
        }
        Iterator<CrossExplosion> it = CROSS_EXPLOSIONS.iterator();
        while (it.hasNext())
        {
            CrossExplosion fx = it.next();
            if (++fx.age >= CrossExplosion.LIFETIME)
            {
                it.remove();
            }
        }
    }

    @SubscribeEvent
    public static void onRenderLevelStage(RenderLevelStageEvent event)
    {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_PARTICLES || CROSS_EXPLOSIONS.isEmpty())
        {
            return;
        }
        PoseStack poseStack = event.getPoseStack();
        Vec3 cam = event.getCamera().getPosition();
        MultiBufferSource.BufferSource buffer = Minecraft.getInstance().renderBuffers().bufferSource();
        VertexConsumer consumer = buffer.getBuffer(RenderType.lightning());

        for (CrossExplosion fx : CROSS_EXPLOSIONS)
        {
            poseStack.pushPose();
            poseStack.translate(fx.pos.x - cam.x, fx.pos.y - cam.y, fx.pos.z - cam.z);
            fx.render(poseStack, consumer, event.getPartialTick());
            poseStack.popPose();
        }
        buffer.endBatch(RenderType.lightning());
    }

    // =====================================================================

    /**
     * The EVA signature: a tall vertical pillar of light with a shorter cross
     * arm, expanding out of the ground, holding, then dissolving — plus a
     * ground-level shockwave ring.
     */
    private static final class CrossExplosion
    {
        static final int LIFETIME = 70;
        private static final int EXPAND_END = 10;
        private static final int HOLD_END = 34;

        final Vec3 pos;
        final float scale;
        int age;

        CrossExplosion(Vec3 pos, float scale)
        {
            this.pos = pos;
            this.scale = scale;
        }

        void render(PoseStack poseStack, VertexConsumer consumer, float partialTick)
        {
            float t = this.age + partialTick;
            Matrix4f pose = poseStack.last().pose();

            float expand = easeOutCubic(Mth.clamp(t / EXPAND_END, 0.0F, 1.0F));
            float fade = t <= HOLD_END ? 1.0F
                    : Mth.clamp(1.0F - (t - HOLD_END) / (LIFETIME - HOLD_END), 0.0F, 1.0F);
            // Slight breathing while the cross holds.
            float pulse = 1.0F + 0.06F * Mth.sin(t * 0.6F);
            float alpha = fade * pulse
                    * com.projectseele.config.SeeleConfig.FX_INTENSITY.get().floatValue();
            float widthMul = (1.0F + 0.35F * (1.0F - fade)) * this.scale;

            float height = 26.0F * this.scale * expand;
            float armReach = 9.0F * this.scale * easeOutCubic(Mth.clamp((t - 4.0F) / EXPAND_END, 0.0F, 1.0F));
            float armY = height * 0.62F;

            // Vertical pillar: violet-white core in an orange sheath.
            Vector3f base = new Vector3f(0.0F, -2.0F * this.scale, 0.0F);
            Vector3f top = new Vector3f(0.0F, height, 0.0F);
            RibbonRenderer.drawStarRibbon(pose, consumer, base, top,
                    2.0F * widthMul, 1.5F * widthMul, 1.0F, 0.55F, 0.22F, alpha * 0.5F);
            RibbonRenderer.drawStarRibbon(pose, consumer, base, top,
                    0.9F * widthMul, 0.65F * widthMul, 1.0F, 0.97F, 0.90F, alpha * 0.95F);

            if (armReach > 0.05F)
            {
                Vector3f left = new Vector3f(-armReach, armY, 0.0F);
                Vector3f right = new Vector3f(armReach, armY, 0.0F);
                RibbonRenderer.drawStarRibbon(pose, consumer, left, right,
                        1.5F * widthMul, 1.5F * widthMul, 1.0F, 0.55F, 0.22F, alpha * 0.5F);
                RibbonRenderer.drawStarRibbon(pose, consumer, left, right,
                        0.7F * widthMul, 0.7F * widthMul, 1.0F, 0.97F, 0.90F, alpha * 0.95F);
            }

            // Shockwave ring racing outward along the ground.
            float ringT = Mth.clamp((t - 2.0F) / 28.0F, 0.0F, 1.0F);
            if (ringT < 1.0F && ringT > 0.0F)
            {
                float radius = 30.0F * this.scale * easeOutCubic(ringT);
                float ringAlpha = (1.0F - ringT) * 0.55F;
                poseStack.pushPose();
                poseStack.translate(0.0D, 0.15D, 0.0D);
                RibbonRenderer.drawGroundRing(poseStack.last().pose(), consumer, radius,
                        1.0F * this.scale, 1.0F, 0.62F, 0.30F, ringAlpha);
                poseStack.popPose();
            }
        }

        private static float easeOutCubic(float x)
        {
            float inv = 1.0F - x;
            return 1.0F - inv * inv * inv;
        }
    }
}
