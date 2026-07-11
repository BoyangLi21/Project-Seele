package com.projectseele.client.fx;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.client.render.RibbonRenderer;
import com.projectseele.network.ClientboundAtFieldRipplePacket;
import com.projectseele.network.ClientboundCannonBeamPacket;
import com.projectseele.network.ClientboundCrossExplosionPacket;
import com.projectseele.fx.TreeOfLifeLayout;
import com.projectseele.network.ClientboundThirdImpactPacket;
import com.projectseele.registry.ModSounds;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.sounds.SoundSource;
import net.minecraft.sounds.SoundEvents;
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
    private static final List<WorldFx> ACTIVE = new ArrayList<>();

    private ClientFxManager() {}

    public static void addCrossExplosion(ClientboundCrossExplosionPacket packet)
    {
        // fxIntensity 0 disables the visual entirely; the sound still plays.
        if (com.projectseele.config.SeeleConfig.FX_INTENSITY.get() > 0.0D)
        {
            ACTIVE.add(new CrossExplosion(new Vec3(packet.x, packet.y, packet.z), packet.scale));
        }
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level != null)
        {
            minecraft.level.playLocalSound(packet.x, packet.y, packet.z,
                    ModSounds.CROSS_EXPLOSION.get(), SoundSource.HOSTILE, 4.0F, 1.0F, false);
        }
    }

    public static void addAtFieldRipple(ClientboundAtFieldRipplePacket packet)
    {
        if (com.projectseele.config.SeeleConfig.FX_INTENSITY.get() > 0.0D)
        {
            ACTIVE.add(new AtFieldRipple(new Vec3(packet.x, packet.y, packet.z),
                    new Vector3f(packet.nx, packet.ny, packet.nz)));
        }
    }

    public static void addCannonBeam(ClientboundCannonBeamPacket packet)
    {
        ACTIVE.add(new CannonBeam(new Vec3(packet.x1, packet.y1, packet.z1),
                new Vec3(packet.x2, packet.y2, packet.z2)));
    }

    public static void addNukeFx(com.projectseele.network.ClientboundNukeFxPacket packet)
    {
        Vec3 pos = new Vec3(packet.x, packet.y, packet.z);
        if (com.projectseele.config.SeeleConfig.FX_INTENSITY.get() > 0.0D)
        {
            ACTIVE.add(new NukeExplosion(pos, packet.scale));
            if (packet.angelCross)
            {
                ACTIVE.add(new CrossExplosion(pos, packet.scale * 0.5F));
            }
        }
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level != null)
        {
            minecraft.level.playLocalSound(packet.x, packet.y, packet.z,
                    packet.angelCross ? ModSounds.CROSS_EXPLOSION.get() : SoundEvents.GENERIC_EXPLODE,
                    packet.angelCross ? SoundSource.HOSTILE : SoundSource.PLAYERS,
                    5.0F, packet.angelCross ? 0.72F : 0.58F, false);
        }
    }

    public static void addThirdImpact(ClientboundThirdImpactPacket packet)
    {
        // The server dictates the facing so the light geometry lands exactly
        // on the Mass-Production Evas it parked on the Sephirot.
        ACTIVE.add(new KabbalahTree(new Vec3(packet.x, packet.y, packet.z), packet.yaw, packet.hasUnit));
    }

    public static void clear()
    {
        ACTIVE.clear();
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
            ACTIVE.clear();
            return;
        }
        Iterator<WorldFx> it = ACTIVE.iterator();
        while (it.hasNext())
        {
            WorldFx fx = it.next();
            if (++fx.age >= fx.lifetime())
            {
                it.remove();
            }
        }
    }

    @SubscribeEvent
    public static void onRenderLevelStage(RenderLevelStageEvent event)
    {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_PARTICLES || ACTIVE.isEmpty())
        {
            return;
        }
        PoseStack poseStack = event.getPoseStack();
        Vec3 cam = event.getCamera().getPosition();
        MultiBufferSource.BufferSource buffer = Minecraft.getInstance().renderBuffers().bufferSource();
        VertexConsumer consumer = buffer.getBuffer(RenderType.lightning());

        for (WorldFx fx : ACTIVE)
        {
            poseStack.pushPose();
            poseStack.translate(fx.pos.x - cam.x, fx.pos.y - cam.y, fx.pos.z - cam.z);
            fx.render(poseStack, consumer, event.getPartialTick());
            poseStack.popPose();
        }
        buffer.endBatch(RenderType.lightning());
    }

    private static float fxIntensity()
    {
        return com.projectseele.config.SeeleConfig.FX_INTENSITY.get().floatValue();
    }

    // =====================================================================

    /** A transient effect anchored at a world position. */
    private abstract static class WorldFx
    {
        final Vec3 pos;
        int age;

        WorldFx(Vec3 pos)
        {
            this.pos = pos;
        }

        abstract int lifetime();

        abstract void render(PoseStack poseStack, VertexConsumer consumer, float partialTick);
    }

    /**
     * The EVA signature: a tall vertical pillar of light with a shorter cross
     * arm, expanding out of the ground, holding, then dissolving — plus a
     * ground-level shockwave ring.
     */
    private static final class CrossExplosion extends WorldFx
    {
        static final int LIFETIME = 70;
        private static final int EXPAND_END = 10;
        private static final int HOLD_END = 34;

        final float scale;

        CrossExplosion(Vec3 pos, float scale)
        {
            super(pos);
            // Angel crosses are skyline-scale, not ordinary particle bursts.
            this.scale = scale * 5.0F;
        }

        @Override
        int lifetime()
        {
            return LIFETIME;
        }

        @Override
        void render(PoseStack poseStack, VertexConsumer consumer, float partialTick)
        {
            float t = this.age + partialTick;
            Matrix4f pose = poseStack.last().pose();

            float expand = easeOutCubic(Mth.clamp(t / EXPAND_END, 0.0F, 1.0F));
            float fade = t <= HOLD_END ? 1.0F
                    : Mth.clamp(1.0F - (t - HOLD_END) / (LIFETIME - HOLD_END), 0.0F, 1.0F);
            // Slight breathing while the cross holds.
            float pulse = 1.0F + 0.06F * Mth.sin(t * 0.6F);
            float alpha = fade * pulse * fxIntensity();
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
                float ringAlpha = (1.0F - ringT) * 0.55F * fxIntensity();
                poseStack.pushPose();
                poseStack.translate(0.0D, 0.15D, 0.0D);
                RibbonRenderer.drawGroundRing(poseStack.last().pose(), consumer, radius,
                        1.0F * this.scale, 1.0F, 0.62F, 0.30F, ringAlpha);
                poseStack.popPose();
            }
        }
    }

    /**
     * A.T. Field impact: three nested orange hexagons expanding in the impact
     * plane and fading — the universal "your weapons are useless" sign.
     */
    private static final class AtFieldRipple extends WorldFx
    {
        static final int LIFETIME = 18;

        private final Vector3f u;
        private final Vector3f v;

        AtFieldRipple(Vec3 pos, Vector3f normal)
        {
            super(pos);
            Vector3f[] basis = RibbonRenderer.planeBasis(normal);
            this.u = basis[0];
            this.v = basis[1];
        }

        @Override
        int lifetime()
        {
            return LIFETIME;
        }

        @Override
        void render(PoseStack poseStack, VertexConsumer consumer, float partialTick)
        {
            float t = (this.age + partialTick) / LIFETIME;
            float alpha = (1.0F - t) * 0.85F * fxIntensity();
            Matrix4f pose = poseStack.last().pose();
            for (int ring = 0; ring < 3; ring++)
            {
                float lag = ring * 0.13F;
                float progress = Mth.clamp(t * 1.35F - lag, 0.0F, 1.0F);
                if (progress <= 0.0F)
                {
                    continue;
                }
                float radius = (1.2F + 3.8F * progress) * (1.0F + ring * 0.55F);
                RibbonRenderer.drawPolyRing(pose, consumer, this.u, this.v, 6, radius,
                        0.22F - 0.04F * ring, 1.0F, 0.60F, 0.18F, alpha * (1.0F - ring * 0.22F));
            }
        }
    }

    /**
     * Nuke-grade beam impact: a blinding radial flash, an expanding fireball
     * of light ribbons and a fast double shockwave. The mushroom smoke itself
     * is server-side particles. Angel callers may add a separate cross.
     */
    private static final class NukeExplosion extends WorldFx
    {
        static final int LIFETIME = 44;

        private static final Vector3f[] BURST_DIRS = buildBurstDirs();

        final float scale;

        NukeExplosion(Vec3 pos, float scale)
        {
            super(pos);
            this.scale = scale;
        }

        @Override
        int lifetime()
        {
            return LIFETIME;
        }

        @Override
        void render(PoseStack poseStack, VertexConsumer consumer, float partialTick)
        {
            float t = this.age + partialTick;
            Matrix4f pose = poseStack.last().pose();
            float intensity = fxIntensity();

            // Blinding radial flash for the first half second.
            if (t < 9.0F)
            {
                float flashT = t / 9.0F;
                float len = (6.0F + 14.0F * easeOutCubic(flashT)) * this.scale;
                float alpha = (1.0F - flashT) * 0.95F * intensity;
                for (Vector3f dir : BURST_DIRS)
                {
                    Vector3f end = new Vector3f(dir).mul(len);
                    RibbonRenderer.drawStarRibbon(pose, consumer, new Vector3f(0.0F, 0.0F, 0.0F), end,
                            1.3F * this.scale, 0.12F, 1.0F, 0.99F, 0.92F, alpha);
                }
            }

            // Rising fireball: stacked luminous rings swelling and lifting.
            float ballT = Mth.clamp(t / 30.0F, 0.0F, 1.0F);
            float ballAlpha = (1.0F - ballT) * 0.65F * intensity;
            if (ballAlpha > 0.01F)
            {
                float radius = (2.0F + 9.0F * easeOutCubic(ballT)) * this.scale;
                float lift = 6.0F * ballT * this.scale;
                Vector3f ux = new Vector3f(1.0F, 0.0F, 0.0F);
                Vector3f uz = new Vector3f(0.0F, 0.0F, 1.0F);
                for (int layer = -1; layer <= 1; layer++)
                {
                    float layerR = radius * (1.0F - 0.28F * Math.abs(layer));
                    poseStack.pushPose();
                    poseStack.translate(0.0D, lift + layer * radius * 0.45F, 0.0D);
                    RibbonRenderer.drawPolyRing(poseStack.last().pose(), consumer, ux, uz, 12,
                            layerR, layerR * 0.45F, 1.0F, 0.52F, 0.16F, ballAlpha);
                    poseStack.popPose();
                }
            }

            // Twin ground shockwaves racing outward.
            for (int wave = 0; wave < 2; wave++)
            {
                float waveT = Mth.clamp((t - wave * 5.0F) / 26.0F, 0.0F, 1.0F);
                if (waveT <= 0.0F || waveT >= 1.0F)
                {
                    continue;
                }
                float radius = 42.0F * this.scale * easeOutCubic(waveT);
                float alpha = (1.0F - waveT) * (0.5F - wave * 0.15F) * intensity;
                poseStack.pushPose();
                poseStack.translate(0.0D, 0.2D + wave * 0.5D, 0.0D);
                RibbonRenderer.drawGroundRing(poseStack.last().pose(), consumer, radius,
                        1.4F * this.scale, 1.0F, 0.72F, 0.35F, alpha);
                poseStack.popPose();
            }
        }

        private static Vector3f[] buildBurstDirs()
        {
            // 14 fixed directions: 6 axes + 8 diagonals, normalized.
            float d = 0.5774F;
            return new Vector3f[] {
                    new Vector3f(1, 0, 0), new Vector3f(-1, 0, 0),
                    new Vector3f(0, 1, 0), new Vector3f(0, -1, 0),
                    new Vector3f(0, 0, 1), new Vector3f(0, 0, -1),
                    new Vector3f(d, d, d), new Vector3f(-d, d, d),
                    new Vector3f(d, d, -d), new Vector3f(-d, d, -d),
                    new Vector3f(d, -d, d), new Vector3f(-d, -d, d),
                    new Vector3f(d, -d, -d), new Vector3f(-d, -d, -d)
            };
        }
    }

    /** One positron sniper shot: brilliant flash, quick fade. */
    private static final class CannonBeam extends WorldFx
    {
        static final int LIFETIME = 14;

        private final Vector3f end;

        CannonBeam(Vec3 from, Vec3 to)
        {
            super(from);
            this.end = new Vector3f((float) (to.x - from.x), (float) (to.y - from.y), (float) (to.z - from.z));
        }

        @Override
        int lifetime()
        {
            return LIFETIME;
        }

        @Override
        void render(PoseStack poseStack, VertexConsumer consumer, float partialTick)
        {
            float t = this.age + partialTick;
            float alpha = Mth.clamp(1.0F - t / LIFETIME, 0.0F, 1.0F);
            float flash = t < 2.0F ? 1.5F : 1.0F;
            Matrix4f pose = poseStack.last().pose();
            Vector3f start = new Vector3f(0.0F, 0.0F, 0.0F);
            RibbonRenderer.drawStarRibbon(pose, consumer, start, this.end,
                    0.65F * flash, 0.40F * flash, 0.55F, 0.80F, 1.0F, alpha * 0.5F);
            RibbonRenderer.drawStarRibbon(pose, consumer, start, this.end,
                    0.28F * flash, 0.16F * flash, 1.0F, 0.99F, 0.95F, alpha * 0.95F);
        }
    }

    /**
     * The End-of-Evangelion Sephirothic tree, sharing TreeOfLifeLayout with
     * the server: upright Golden Dawn diagram (Keter apex, Malkuth base),
     * ring-shaped Sephirot joined by burning double lines, igniting down the
     * emanation order. The outer rings frame the real Mass-Production Eva
     * entities the server parked there; Tiferet carries the crucified
     * Unit-01 with wings of light.
     */
    private static final class KabbalahTree extends WorldFx
    {
        private static final int LIFETIME = 20 * 180;
        /** Node reveal cadence: Keter first, then down the tree. */
        private static final int NODE_LIGHT_INTERVAL = 9;
        private static final int NODE_LIGHT_TIME = 24;
        private static final int TIFERET = TreeOfLifeLayout.TIFERET;

        private final float faceYaw;
        private final boolean hasUnit;

        KabbalahTree(Vec3 pos, float faceYaw, boolean hasUnit)
        {
            super(pos);
            this.faceYaw = faceYaw;
            this.hasUnit = hasUnit;
        }

        private static Vector3f node(int index)
        {
            return new Vector3f(TreeOfLifeLayout.localX(index), TreeOfLifeLayout.localY(index), 0.0F);
        }

        @Override
        int lifetime()
        {
            return LIFETIME;
        }

        /** 0..1 ignition of one Sephira: Keter first, down the emanations. */
        private static float nodeLight(float t, int index)
        {
            return Mth.clamp((t - 10.0F - index * NODE_LIGHT_INTERVAL) / NODE_LIGHT_TIME, 0.0F, 1.0F);
        }

        @Override
        void render(PoseStack poseStack, VertexConsumer consumer, float partialTick)
        {
            float t = this.age + partialTick;
            float endFade = Mth.clamp((LIFETIME - t) / 80.0F, 0.0F, 1.0F);
            float breathe = 0.80F + 0.14F * Mth.sin(t * 0.045F);
            float base = endFade * breathe * fxIntensity();
            if (base <= 0.003F)
            {
                return;
            }

            poseStack.pushPose();
            poseStack.mulPose(com.mojang.math.Axis.YP.rotation(this.faceYaw));
            Matrix4f pose = poseStack.last().pose();

            // Paths: burning double lines, lit once both endpoints burn.
            for (int[] path : TreeOfLifeLayout.PATHS)
            {
                float lit = Math.min(nodeLight(t, path[0]), nodeLight(t, path[1]));
                if (lit <= 0.0F)
                {
                    continue;
                }
                Vector3f a = node(path[0]);
                Vector3f b = node(path[1]);
                Vector3f dir = new Vector3f(b).sub(a).normalize();
                // In-plane normal (the tree stands in local XY).
                Vector3f offset = new Vector3f(-dir.y, dir.x, 0.0F).mul(1.2F);
                Vector3f mid = new Vector3f(a).lerp(b, 0.5F);
                Vector3f grow = new Vector3f(b).sub(a).mul(0.5F * lit);
                Vector3f from = new Vector3f(mid).sub(grow);
                Vector3f to = new Vector3f(mid).add(grow);
                float alpha = base * lit;
                for (int s = -1; s <= 1; s += 2)
                {
                    Vector3f shift = new Vector3f(offset).mul(s);
                    RibbonRenderer.drawStarRibbon(pose, consumer,
                            new Vector3f(from).add(shift), new Vector3f(to).add(shift),
                            0.78F, 0.78F, 1.0F, 0.0F, 0.0F, alpha * 0.58F);
                    RibbonRenderer.drawStarRibbon(pose, consumer,
                            new Vector3f(from).add(shift), new Vector3f(to).add(shift),
                            0.28F, 0.28F, 1.0F, 0.0F, 0.0F, alpha);
                }
            }

            // Sephirot rings. The outer nodes frame the real Mass-Production
            // Eva entities parked there by the server; Tiferet carries the
            // crucified Unit-01 with wings of light (EoE staging).
            Vector3f axisX = new Vector3f(1.0F, 0.0F, 0.0F);
            Vector3f axisY = new Vector3f(0.0F, 1.0F, 0.0F);
            for (int i = 0; i < TreeOfLifeLayout.NODES.length; i++)
            {
                float lit = nodeLight(t, i);
                if (lit <= 0.0F)
                {
                    continue;
                }
                Vector3f c = node(i);
                boolean centre = i == TIFERET;
                float radius = (centre ? 18.0F : 14.0F) * (0.9F + 0.1F * lit)
                        * (1.0F + 0.045F * Mth.sin(t * 0.07F + i * 1.7F));
                float alpha = base * lit;
                poseStack.pushPose();
                poseStack.translate(c.x, c.y, c.z);
                Matrix4f nodePose = poseStack.last().pose();
                RibbonRenderer.drawPolyRing(nodePose, consumer, axisX, axisY, 32,
                        radius, 1.4F, 1.0F, 0.0F, 0.0F, alpha * 0.85F);
                RibbonRenderer.drawPolyRing(nodePose, consumer, axisX, axisY, 32,
                        radius * 0.72F, 0.55F, 1.0F, 0.0F, 0.0F, alpha);
                if (centre)
                {
                    drawTiferetGlory(nodePose, consumer, t, alpha, this.hasUnit);
                }
                poseStack.popPose();
            }
            poseStack.popPose();
        }

        /** Tiferet centrepiece: red wings of light; the cross body only when
         *  no real Unit-01 was nailed there by the scenario item. */
        private static void drawTiferetGlory(Matrix4f pose, VertexConsumer consumer,
                                             float t, float alpha, boolean hasUnit)
        {
            float s = 2.0F;
            float pr = 1.0F;
            float pg = 0.0F;
            float pb = 0.0F;
            // Wings of light first, so the body draws over them.
            float shimmer = 0.9F + 0.1F * Mth.sin(t * 0.06F);
            for (int side = -1; side <= 1; side += 2)
            {
                for (int f = 0; f < 3; f++)
                {
                    float ang = (28.0F + f * 22.0F) * Mth.DEG_TO_RAD;
                    float len = (22.0F - f * 4.5F) * shimmer * s;
                    Vector3f tip = new Vector3f(side * Mth.cos(ang) * len, 2.0F * s + Mth.sin(ang) * len, 0.4F);
                    RibbonRenderer.drawStarRibbon(pose, consumer, new Vector3f(0.0F, 2.0F * s, 0.4F), tip,
                            (2.6F - f * 0.6F) * s, 0.4F, 1.0F, 0.0F, 0.0F, alpha * (0.55F - f * 0.12F));
                }
            }
            if (hasUnit)
            {
                return; // the real Unit-01 hangs here; wings only
            }
            // The cross pose: pure-red torso, outstretched arms, horned head.
            Vector3f hip = new Vector3f(0.0F, -4.6F * s, 0.0F);
            Vector3f neck = new Vector3f(0.0F, 3.4F * s, 0.0F);
            RibbonRenderer.drawStarRibbon(pose, consumer, hip, neck, 1.35F * s, 1.0F * s, pr, pg, pb, alpha);
            RibbonRenderer.drawStarRibbon(pose, consumer,
                    new Vector3f(-8.2F * s, 2.6F * s, 0.0F), new Vector3f(8.2F * s, 2.6F * s, 0.0F),
                    0.95F * s, 0.95F * s, pr, pg, pb, alpha);
            RibbonRenderer.drawStarRibbon(pose, consumer, neck,
                    new Vector3f(0.0F, 4.9F * s, 0.0F), 0.68F * s, 0.55F * s, pr, pg, pb, alpha);
            // The horn.
            RibbonRenderer.drawStarRibbon(pose, consumer,
                    new Vector3f(0.0F, 4.9F * s, -0.3F), new Vector3f(0.0F, 6.6F * s, -0.9F),
                    0.22F * s, 0.06F, 1.0F, 0.0F, 0.0F, alpha);
            // Legs together, crucified.
            RibbonRenderer.drawStarRibbon(pose, consumer, hip,
                    new Vector3f(0.0F, -9.6F * s, 0.0F), 0.9F * s, 0.5F * s, pr, pg, pb, alpha * 0.95F);
            // Core glow.
            RibbonRenderer.drawStarRibbon(pose, consumer,
                    new Vector3f(-0.9F * s, 0.8F * s, 0.5F), new Vector3f(0.9F * s, 0.8F * s, 0.5F),
                    0.8F * s, 0.8F * s, 1.0F, 0.0F, 0.0F, alpha);
        }
    }

    private static float easeOutCubic(float x)
    {
        float inv = 1.0F - x;
        return 1.0F - inv * inv * inv;
    }
}
