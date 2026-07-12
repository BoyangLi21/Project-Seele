package com.projectseele.client.fx;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.UUID;

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
import net.minecraft.client.gui.Font;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.locale.Language;
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
    private static ClientLevel activeLevel;
    // Lightning's additive pass vanished entirely in actual framebuffer
    // captures on the current NVIDIA/Forge stack. The Tree needs a stable
    // position-colour quad pass; other transient energy FX keep lightning.
    private static final RenderType TREE_GEOMETRY = RenderType.debugQuads();

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
        ensureActiveLevel();
        // The server dictates the facing so the light geometry lands exactly
        // on the Mass-Production Evas it parked on the Sephirot.
        Vec3 position = new Vec3(packet.x, packet.y, packet.z);
        // Resync the same server event in place. Replacing the Tree restarted
        // its reveal animation, while origin-only deduplication merged two
        // otherwise valid events staged at the same coordinates.
        for (WorldFx fx : ACTIVE)
        {
            if (fx instanceof KabbalahTree tree && tree.eventId.equals(packet.eventId))
            {
                tree.age = Math.max(tree.age,
                        Mth.clamp(packet.initialTreeAge, 0, KabbalahTree.LIFETIME - 1));
                return;
            }
        }
        ACTIVE.add(new KabbalahTree(packet.eventId, position, packet.yaw,
                packet.hasUnit, packet.initialTreeAge));
        if (Boolean.getBoolean("projectseele.visualCapture")
                && "impact".equals(System.getProperty("projectseele.visualCaptureUnit")))
        {
            com.projectseele.client.visual.VisualCaptureManager.startImpact(
                    new Vec3(packet.x, packet.y, packet.z), packet.yaw);
        }
    }

    public static void clear()
    {
        ACTIVE.clear();
        activeLevel = null;
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
            clear();
            return;
        }
        ensureActiveLevel();
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

    private static void ensureActiveLevel()
    {
        ClientLevel level = Minecraft.getInstance().level;
        if (activeLevel == null)
        {
            activeLevel = level;
        }
        else if (activeLevel != level)
        {
            ACTIVE.clear();
            activeLevel = level;
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
            VertexConsumer target = fx instanceof KabbalahTree
                    ? buffer.getBuffer(TREE_GEOMETRY) : consumer;
            fx.render(poseStack, target, event.getPartialTick());
            poseStack.popPose();
        }
        buffer.endBatch(RenderType.lightning());
        buffer.endBatch(TREE_GEOMETRY);

        // World-space lettering uses the same pose as the luminous geometry,
        // but a font render type. Keep it in a second pass so batching the
        // lightning ribbons cannot swallow or reorder the glyph quads.
        for (WorldFx fx : ACTIVE)
        {
            if (!(fx instanceof KabbalahTree tree))
            {
                continue;
            }
            poseStack.pushPose();
            poseStack.translate(fx.pos.x - cam.x, fx.pos.y - cam.y, fx.pos.z - cam.z);
            tree.renderLabels(poseStack, buffer, event.getPartialTick());
            poseStack.popPose();
        }
        buffer.endBatch();
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
     * The Angel signature: a tall vertical pillar of light with a shorter cross
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
     * the server: an inverted Golden Dawn diagram, ring-shaped Sephirot joined
     * by burning double lines and the 22 path letters. The outer rings frame
     * the real Mass-Production Eva entities; Tiferet carries the crucified
     * Unit-01 with wings of light.
     */
    private static final class KabbalahTree extends WorldFx
    {
        private static final int LIFETIME = 20 * 180;
        /** Node reveal cadence: Keter first, rising through the inverted tree. */
        private static final int NODE_LIGHT_INTERVAL = 9;
        private static final int NODE_LIGHT_TIME = 24;
        private static final int TIFERET = TreeOfLifeLayout.TIFERET;
        private static final String[] SEPHIRA_NAMES = {
                "KETER", "CHOKMAH", "BINAH", "CHESED", "GEVURAH",
                "TIFERET", "NETZACH", "HOD", "YESOD", "MALKUTH"
        };
        private static final String[] SEPHIRA_HEBREW = {
                "\u05DB\u05EA\u05E8", "\u05D7\u05DB\u05DE\u05D4", "\u05D1\u05D9\u05E0\u05D4",
                "\u05D7\u05E1\u05D3", "\u05D2\u05D1\u05D5\u05E8\u05D4", "\u05EA\u05E4\u05D0\u05E8\u05EA",
                "\u05E0\u05E6\u05D7", "\u05D4\u05D5\u05D3", "\u05D9\u05E1\u05D5\u05D3", "\u05DE\u05DC\u05DB\u05D5\u05EA"
        };
        // PATHS is arranged for geometry/label spacing rather than alphabetic
        // order.  Keep each letter beside its canonical Golden Dawn edge.
        private static final String[] PATH_LETTERS = {
                "\u05D0", "\u05D1", "\u05D2", "\u05D3", "\u05D5", "\u05D4", "\u05D7", "\u05D6",
                "\u05D8", "\u05D9", "\u05DB", "\u05DC", "\u05DE", "\u05E0", "\u05E2", "\u05E1",
                "\u05E4", "\u05E6", "\u05E8", "\u05E7", "\u05E9", "\u05EA"
        };
        /** Move names outside the ritual bodies; centre-column labels alternate sides. */
        private static final float[] LABEL_X_OFFSETS = {
                -28.0F, -28.0F, 28.0F, -28.0F, 28.0F,
                55.0F, -28.0F, 28.0F, -55.0F, 32.0F
        };
        /** Collision-searched offsets from each path midpoint, in local tree space. */
        private static final float[][] PATH_LABEL_OFFSETS = {
                {-2.173F,-3.358F},{2.173F,-3.358F},{-4.0F,0.0F},{0.0F,-4.0F},
                {-4.0F,0.0F},{3.273F,-2.299F},{-4.0F,0.0F},{3.273F,2.299F},
                {0.0F,-4.0F},{-1.713F,-5.391F},{-4.0F,0.0F},{1.839F,3.552F},
                {-4.0F,4.0F},{-0.706F,5.613F},{3.866F,8.066F},{4.0F,0.0F},
                {-8.0F,4.0F},{1.839F,-3.552F},{-1.839F,-3.552F},
                {3.165F,-2.446F},{-3.165F,-2.446F},{8.0F,0.0F}
        };

        private final UUID eventId;
        private final float faceYaw;
        private final boolean hasUnit;

        KabbalahTree(UUID eventId, Vec3 pos, float faceYaw, boolean hasUnit, int initialAge)
        {
            super(pos);
            this.eventId = eventId;
            this.faceYaw = faceYaw;
            this.hasUnit = hasUnit;
            this.age = Mth.clamp(initialAge, 0, LIFETIME - 1);
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

        /** 0..1 ignition of one Sephira: Keter first through the inversion. */
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
            // Keep the diagram as a luminous backplate. The ritual bodies sit
            // at local Z=0; a small negative offset stops the opaque stable
            // colour pass from painting over their silhouettes.
            poseStack.translate(0.0D, 0.0D, -8.0D);
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
                            0.70F, 0.70F, 1.0F, 0.0F, 0.0F, alpha * 0.72F);
                    RibbonRenderer.drawStarRibbon(pose, consumer,
                            new Vector3f(from).add(shift), new Vector3f(to).add(shift),
                            0.24F, 0.24F, 1.0F, 0.0F, 0.0F, alpha);
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
                float radius = (centre ? 16.5F : 13.5F) * (0.9F + 0.1F * lit)
                        * (1.0F + 0.045F * Mth.sin(t * 0.07F + i * 1.7F));
                float alpha = base * lit;
                poseStack.pushPose();
                poseStack.translate(c.x, c.y, c.z);
                Matrix4f nodePose = poseStack.last().pose();
                RibbonRenderer.drawPolyRing(nodePose, consumer, axisX, axisY, 32,
                        radius, 1.10F, 1.0F, 0.0F, 0.0F, alpha);
                RibbonRenderer.drawPolyRing(nodePose, consumer, axisX, axisY, 32,
                        radius * 0.72F, 0.40F, 1.0F, 0.0F, 0.0F, alpha);
                if (centre)
                {
                    drawTiferetGlory(nodePose, consumer, t, alpha, this.hasUnit);
                }
                poseStack.popPose();

                // Short leaders make the displaced bilingual node labels
                // unambiguous without drawing text over an EVA silhouette.
                float labelOffset = LABEL_X_OFFSETS[i];
                float sign = Math.signum(labelOffset);
                float lineStart = radius + 0.8F;
                float lineEnd = Math.abs(labelOffset) - 3.0F;
                if (lineEnd > lineStart)
                {
                    RibbonRenderer.drawStarRibbon(pose, consumer,
                            new Vector3f(c.x + sign * lineStart, c.y, c.z + 0.2F),
                            new Vector3f(c.x + sign * lineEnd, c.y, c.z + 0.2F),
                            0.18F, 0.18F, 1.0F, 0.0F, 0.0F, alpha * 0.9F);
                }
            }
            poseStack.popPose();
        }

        /** Full-bright red labels: ten Sephirot, ten Hebrew names and all 22 path letters. */
        void renderLabels(PoseStack poseStack, MultiBufferSource.BufferSource buffer, float partialTick)
        {
            float t = this.age + partialTick;
            float endFade = Mth.clamp((LIFETIME - t) / 80.0F, 0.0F, 1.0F);
            float base = endFade * fxIntensity();
            if (base <= 0.003F)
            {
                return;
            }

            poseStack.pushPose();
            poseStack.mulPose(com.mojang.math.Axis.YP.rotation(this.faceYaw));

            // The Kircher-style heading immediately distinguishes the ritual
            // glyph from ten anonymous circles.
            float top = TreeOfLifeLayout.localY(9);
            float titleLit = nodeLight(t, 9);
            drawLabel(poseStack, buffer, "SYSTEMA SEPHIROTHICVM",
                    new Vector3f(0.0F, top + 38.0F, 0.8F), 1.02F, base * titleLit);
            drawLabel(poseStack, buffer, "X DIVINORVM NOMINVM",
                    new Vector3f(0.0F, top + 31.0F, 0.8F), 0.87F, base * titleLit);
            drawLabel(poseStack, buffer, "OTZ CHIIM",
                    new Vector3f(0.0F, top + 24.5F, 0.8F), 0.78F, base * titleLit);
            drawLabel(poseStack, buffer, displayHebrew("\u05E2\u05E5 \u05D7\u05D9\u05D9\u05DD"),
                    new Vector3f(0.0F, top + 18.0F, 0.8F), 0.86F, base * titleLit);

            for (int i = 0; i < TreeOfLifeLayout.NODES.length; i++)
            {
                float lit = nodeLight(t, i);
                if (lit <= 0.0F)
                {
                    continue;
                }
                Vector3f c = node(i);
                float alpha = base * lit;
                float labelX = c.x + LABEL_X_OFFSETS[i];
                drawLabel(poseStack, buffer, (i + 1) + "  " + SEPHIRA_NAMES[i],
                        new Vector3f(labelX, c.y + 2.8F, 0.9F), 0.84F, alpha);
                drawLabel(poseStack, buffer, displayHebrew(SEPHIRA_HEBREW[i]),
                        new Vector3f(labelX, c.y - 3.0F, 0.9F), 1.05F, alpha);
            }

            for (int i = 0; i < TreeOfLifeLayout.PATHS.length; i++)
            {
                int[] path = TreeOfLifeLayout.PATHS[i];
                float lit = Math.min(nodeLight(t, path[0]), nodeLight(t, path[1]));
                if (lit <= 0.0F)
                {
                    continue;
                }
                Vector3f a = node(path[0]);
                Vector3f b = node(path[1]);
                Vector3f letterPos = new Vector3f(a).lerp(b, 0.5F)
                        .add(PATH_LABEL_OFFSETS[i][0], PATH_LABEL_OFFSETS[i][1], 1.0F);
                drawLabel(poseStack, buffer, PATH_LETTERS[i], letterPos, 1.05F, base * lit);
            }
            poseStack.popPose();
        }

        /** Vanilla only applies bidi shaping when the selected UI language is RTL. */
        private static String displayHebrew(String logical)
        {
            return Language.getInstance().isDefaultRightToLeft()
                    ? logical : new StringBuilder(logical).reverse().toString();
        }

        private static void drawLabel(PoseStack poseStack, MultiBufferSource.BufferSource buffer,
                                      String text, Vector3f position, float scale, float alpha)
        {
            if (alpha <= 0.01F)
            {
                return;
            }
            Font font = Minecraft.getInstance().font;
            int colour = Mth.clamp((int) (alpha * 255.0F), 0, 255) << 24 | 0x00FF0000;
            poseStack.pushPose();
            poseStack.translate(position.x, position.y, position.z);
            poseStack.scale(scale, -scale, scale);
            font.drawInBatch(text, -font.width(text) * 0.5F, -4.0F, colour, false,
                    poseStack.last().pose(), buffer, Font.DisplayMode.SEE_THROUGH,
                    0x00000000,
                    LightTexture.FULL_BRIGHT);
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
