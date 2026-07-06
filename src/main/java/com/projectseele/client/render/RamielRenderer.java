package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.math.Axis;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.RamielEntity;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Vector3f;

/**
 * Renders Ramiel as a mathematically exact octahedron: a translucent blue
 * crystal shell with glowing edges around a pulsing red core. The charge-up
 * light convergence and the positron beam itself are drawn here too, from
 * entity-synced state — no particles, no model files.
 */
public class RamielRenderer extends EntityRenderer<RamielEntity>
{
    private static final ResourceLocation TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/ramiel.png");

    // Beam palette: white-hot core sheathed in violet-pink, matching the charge dust.
    private static final float[] BEAM_CORE_RGB = {1.0F, 0.98F, 0.96F};
    private static final float[] BEAM_HALO_RGB = {0.95F, 0.45F, 0.90F};
    private static final float[] RAY_RGB = {1.0F, 0.35F, 0.50F};

    public RamielRenderer(EntityRendererProvider.Context context)
    {
        super(context);
        this.shadowRadius = 0.0F;
    }

    @Override
    public void render(RamielEntity entity, float entityYaw, float partialTick, PoseStack poseStack,
                       MultiBufferSource buffer, int packedLight)
    {
        float coreHeight = entity.getBbHeight() * 0.5F;
        float beamTicks = entity.getBeamTicks() - partialTick;
        // 1 while the beam is solid, easing to 0 across the afterglow window.
        float beamGlow = beamTicks <= 0.0F ? 0.0F
                : Mth.clamp(beamTicks / (RamielEntity.BEAM_RENDER_TICKS - RamielEntity.BEAM_SOLID_TICKS), 0.0F, 1.0F);

        if (beamTicks > 0.0F)
        {
            renderBeam(entity, partialTick, beamTicks, poseStack, buffer, coreHeight);
        }

        if (entity.isDrilling() && entity.getDrillDepth() > 0.1F)
        {
            renderDrill(entity, partialTick, poseStack, buffer, coreHeight);
        }

        // ----- crystal body (spins around Y) -----
        poseStack.pushPose();
        poseStack.translate(0.0D, coreHeight, 0.0D);
        poseStack.mulPose(Axis.YP.rotationDegrees(entity.getSpin(partialTick)));

        VertexConsumer body = buffer.getBuffer(RenderType.entityTranslucent(TEXTURE));
        int fullBright = LightTexture.FULL_BRIGHT;

        float corePulse = entity.isCharging()
                ? 1.1F + 0.3F * Mth.sin((entity.tickCount + partialTick) * 0.5F)
                : 0.95F;
        drawOctahedron(poseStack, body, 1.05F * corePulse, 1.0F, 0.12F, 0.18F, 1.0F, fullBright);
        // Shell flashes toward white while the beam is live.
        float shellR = Mth.lerp(beamGlow, 0.45F, 1.0F);
        float shellG = Mth.lerp(beamGlow, 0.72F, 0.95F);
        float shellB = 1.0F;
        drawOctahedron(poseStack, body, 3.3F, shellR, shellG, shellB, 0.7F, fullBright);

        VertexConsumer glow = buffer.getBuffer(RenderType.lightning());
        drawOctahedronEdges(poseStack, glow, 3.3F, 0.05F,
                0.75F, 0.92F, 1.0F, 0.55F + 0.4F * beamGlow);

        poseStack.popPose();

        // ----- charge-up light convergence (world-aligned, does not spin) -----
        if (entity.isCharging())
        {
            poseStack.pushPose();
            poseStack.translate(0.0D, coreHeight, 0.0D);
            drawChargeRays(entity, partialTick, poseStack, buffer.getBuffer(RenderType.lightning()));
            poseStack.popPose();
        }

        super.render(entity, entityYaw, partialTick, poseStack, buffer, packedLight);
    }

    // =====================================================================
    // Beam
    // =====================================================================

    private static void renderBeam(RamielEntity entity, float partialTick, float beamTicks,
                                   PoseStack poseStack, MultiBufferSource buffer, float coreHeight)
    {
        Vec3 entityPos = entity.getPosition(partialTick);
        Vec3 endWorld = entity.getBeamEnd();
        Vector3f start = new Vector3f(0.0F, coreHeight, 0.0F);
        Vector3f end = new Vector3f(
                (float) (endWorld.x - entityPos.x),
                (float) (endWorld.y - entityPos.y),
                (float) (endWorld.z - entityPos.z));

        float fadeWindow = RamielEntity.BEAM_RENDER_TICKS - RamielEntity.BEAM_SOLID_TICKS;
        float alpha = beamTicks >= fadeWindow ? 1.0F : beamTicks / fadeWindow;
        // Brief muzzle flash right as the shot lands.
        float flash = beamTicks > RamielEntity.BEAM_RENDER_TICKS - 2.0F ? 1.45F : 1.0F;

        VertexConsumer consumer = buffer.getBuffer(RenderType.lightning());
        poseStack.pushPose();
        Matrix4f pose = poseStack.last().pose();

        // Outer violet halo, then inner white-hot core.
        drawStarRibbon(pose, consumer, start, end, 1.25F * flash, 0.70F * flash,
                BEAM_HALO_RGB[0], BEAM_HALO_RGB[1], BEAM_HALO_RGB[2], alpha * 0.55F);
        drawStarRibbon(pose, consumer, start, end, 0.50F * flash, 0.30F * flash,
                BEAM_CORE_RGB[0], BEAM_CORE_RGB[1], BEAM_CORE_RGB[2], alpha * 0.95F);

        poseStack.popPose();
    }

    private static void drawStarRibbon(Matrix4f pose, VertexConsumer consumer, Vector3f start, Vector3f end,
                                       float startWidth, float endWidth, float r, float g, float b, float a)
    {
        RibbonRenderer.drawStarRibbon(pose, consumer, start, end, startWidth, endWidth, r, g, b, a);
    }

    /** Downward boring column while the phase-two drill is active. */
    private static void renderDrill(RamielEntity entity, float partialTick,
                                    PoseStack poseStack, MultiBufferSource buffer, float coreHeight)
    {
        float time = entity.tickCount + partialTick;
        float flicker = 0.75F + 0.25F * Mth.sin(time * 1.7F);
        Vector3f start = new Vector3f(0.0F, coreHeight, 0.0F);
        Vector3f end = new Vector3f(0.0F, coreHeight - entity.getDrillDepth(), 0.0F);

        VertexConsumer consumer = buffer.getBuffer(RenderType.lightning());
        poseStack.pushPose();
        Matrix4f pose = poseStack.last().pose();
        drawStarRibbon(pose, consumer, start, end, 1.6F, 1.1F,
                BEAM_HALO_RGB[0], BEAM_HALO_RGB[1], BEAM_HALO_RGB[2], 0.45F * flicker);
        drawStarRibbon(pose, consumer, start, end, 0.7F, 0.45F,
                BEAM_CORE_RGB[0], BEAM_CORE_RGB[1], BEAM_CORE_RGB[2], 0.9F * flicker);
        poseStack.popPose();
    }

    private static void drawChargeRays(RamielEntity entity, float partialTick,
                                       PoseStack poseStack, VertexConsumer consumer)
    {
        Matrix4f pose = poseStack.last().pose();
        float time = entity.tickCount + partialTick;
        for (int i = 0; i < 8; i++)
        {
            float azimuth = (float) Math.toRadians(i * 45.0F + time * 1.8F);
            float pitch = (float) Math.toRadians((i % 2 == 0 ? 24.0F : -18.0F)
                    + 8.0F * Mth.sin(time * 0.11F + i));
            float radius = 8.5F;
            Vector3f outer = new Vector3f(
                    radius * Mth.cos(pitch) * Mth.cos(azimuth),
                    radius * Mth.sin(pitch),
                    radius * Mth.cos(pitch) * Mth.sin(azimuth));
            float pulse = 0.28F + 0.30F * Mth.sin(time * 0.35F + i * 1.3F);
            // Rays thicken toward the core: energy pouring inward.
            drawStarRibbon(pose, consumer, outer, new Vector3f(0.0F, 0.0F, 0.0F),
                    0.03F, 0.30F, RAY_RGB[0], RAY_RGB[1], RAY_RGB[2], Math.max(pulse, 0.05F));
        }
    }

    // =====================================================================
    // Octahedron body
    // =====================================================================

    private static final Vector3f[] UNIT_VERTS = {
            new Vector3f(0.0F, 1.0F, 0.0F),   // 0: top apex
            new Vector3f(0.0F, -1.0F, 0.0F),  // 1: bottom apex
            new Vector3f(1.0F, 0.0F, 0.0F),   // 2: +X
            new Vector3f(0.0F, 0.0F, 1.0F),   // 3: +Z
            new Vector3f(-1.0F, 0.0F, 0.0F),  // 4: -X
            new Vector3f(0.0F, 0.0F, -1.0F)   // 5: -Z
    };
    private static final int[][] FACES = {
            {0, 2, 3}, {0, 3, 4}, {0, 4, 5}, {0, 5, 2},
            {1, 3, 2}, {1, 4, 3}, {1, 5, 4}, {1, 2, 5}
    };
    private static final int[][] EDGES = {
            {0, 2}, {0, 3}, {0, 4}, {0, 5},
            {1, 2}, {1, 3}, {1, 4}, {1, 5},
            {2, 3}, {3, 4}, {4, 5}, {5, 2}
    };

    private static void drawOctahedron(PoseStack poseStack, VertexConsumer consumer, float size,
                                       float red, float green, float blue, float alpha, int packedLight)
    {
        Matrix4f pose = poseStack.last().pose();
        Matrix3f normalPose = poseStack.last().normal();
        float[][] uvs = {{0.5F, 0.0F}, {0.0F, 1.0F}, {1.0F, 1.0F}};

        for (int f = 0; f < FACES.length; f++)
        {
            Vector3f a = new Vector3f(UNIT_VERTS[FACES[f][0]]).mul(size);
            Vector3f b = new Vector3f(UNIT_VERTS[FACES[f][1]]).mul(size);
            Vector3f c = new Vector3f(UNIT_VERTS[FACES[f][2]]).mul(size);
            Vector3f normal = new Vector3f(b).sub(a).cross(new Vector3f(c).sub(a)).normalize();
            // Slight per-face shade variation sells the faceted crystal look.
            float shade = 0.82F + 0.06F * (f % 4);
            float r = red * shade;
            float g = green * shade;
            float bl = blue * shade;
            // Each triangle goes out as a quad with the last vertex repeated.
            putVertex(pose, normalPose, consumer, a, r, g, bl, alpha, uvs[0], normal, packedLight);
            putVertex(pose, normalPose, consumer, b, r, g, bl, alpha, uvs[1], normal, packedLight);
            putVertex(pose, normalPose, consumer, c, r, g, bl, alpha, uvs[2], normal, packedLight);
            putVertex(pose, normalPose, consumer, c, r, g, bl, alpha, uvs[2], normal, packedLight);
        }
    }

    /** Thin luminous ribbons along each edge give the crystal its cut. */
    private static void drawOctahedronEdges(PoseStack poseStack, VertexConsumer consumer, float size,
                                            float width, float r, float g, float b, float a)
    {
        Matrix4f pose = poseStack.last().pose();
        for (int[] edge : EDGES)
        {
            Vector3f from = new Vector3f(UNIT_VERTS[edge[0]]).mul(size);
            Vector3f to = new Vector3f(UNIT_VERTS[edge[1]]).mul(size);
            drawStarRibbon(pose, consumer, from, to, width, width, r, g, b, a);
        }
    }

    private static void putVertex(Matrix4f pose, Matrix3f normalPose, VertexConsumer consumer, Vector3f pos,
                                  float r, float g, float b, float a, float[] uv, Vector3f normal, int light)
    {
        consumer.vertex(pose, pos.x(), pos.y(), pos.z())
                .color(r, g, b, a)
                .uv(uv[0], uv[1])
                .overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(light)
                .normal(normalPose, normal.x(), normal.y(), normal.z())
                .endVertex();
    }

    @Override
    public ResourceLocation getTextureLocation(RamielEntity entity)
    {
        return TEXTURE;
    }
}
