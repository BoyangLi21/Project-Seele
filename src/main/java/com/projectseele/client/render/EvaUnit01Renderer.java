package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.math.Axis;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import org.joml.Matrix3f;
import org.joml.Matrix4f;

/**
 * Placeholder Unit-01: a direct-vertex box humanoid in the classic
 * purple/green scheme with white shoulder pylons and the horn. Model space:
 * origin at the feet, front is -Z (the render method turns it to face the
 * entity yaw). Swappable for a proper GeckoLib model later without touching
 * the entity.
 */
public class EvaUnit01Renderer extends EntityRenderer<EvaUnit01Entity>
{
    private static final ResourceLocation TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva_unit01.png");

    // Palette.
    private static final float[] PURPLE = {0.34F, 0.16F, 0.58F};
    private static final float[] PURPLE_DARK = {0.22F, 0.10F, 0.40F};
    private static final float[] GREEN = {0.30F, 1.00F, 0.42F};
    private static final float[] WHITE = {0.90F, 0.90F, 0.94F};
    private static final float[] ORANGE = {1.00F, 0.55F, 0.10F};

    private static final float HIP_Y = 5.4F;
    private static final float SHOULDER_Y = 9.2F;

    public EvaUnit01Renderer(EntityRendererProvider.Context context)
    {
        super(context);
        this.shadowRadius = 1.8F;
    }

    @Override
    public void render(EvaUnit01Entity entity, float entityYaw, float partialTick, PoseStack poseStack,
                       MultiBufferSource buffer, int packedLight)
    {
        poseStack.pushPose();
        float bodyYaw = Mth.rotLerp(partialTick, entity.yBodyRotO, entity.yBodyRot);
        poseStack.mulPose(Axis.YP.rotationDegrees(180.0F - bodyYaw));

        VertexConsumer consumer = buffer.getBuffer(RenderType.entityTranslucent(TEXTURE));
        int overlay = OverlayTexture.pack(0.0F, entity.hurtTime > 0);

        float swingPos = entity.walkAnimation.position(partialTick);
        float swingAmp = Math.min(entity.walkAnimation.speed(partialTick), 1.0F);
        float swing = Mth.cos(swingPos * 0.35F) * 0.55F * swingAmp;

        // ----- legs (swing about the hip) -----
        renderLimb(poseStack, consumer, packedLight, overlay, HIP_Y, swing,
                0.35F, 1.15F, 0.0F, HIP_Y, -0.55F, 0.55F, PURPLE_DARK);
        renderLimb(poseStack, consumer, packedLight, overlay, HIP_Y, -swing,
                -1.15F, -0.35F, 0.0F, HIP_Y, -0.55F, 0.55F, PURPLE_DARK);

        // ----- pelvis & torso -----
        drawBox(poseStack, consumer, -1.20F, HIP_Y, -0.60F, 1.20F, 6.2F, 0.60F,
                PURPLE_DARK, packedLight, overlay);
        drawBox(poseStack, consumer, -1.35F, 6.2F, -0.75F, 1.35F, 9.6F, 0.75F,
                PURPLE, packedLight, overlay);
        // Chest plate accents.
        drawBox(poseStack, consumer, -0.95F, 8.2F, -0.82F, 0.95F, 9.4F, -0.72F,
                GREEN, LightTexture.FULL_BRIGHT, overlay);
        // The core, front and centre.
        drawBox(poseStack, consumer, -0.28F, 7.4F, -0.92F, 0.28F, 7.96F, -0.70F,
                GREEN, LightTexture.FULL_BRIGHT, overlay);

        // ----- arms (counter-swing) -----
        renderLimb(poseStack, consumer, packedLight, overlay, SHOULDER_Y, -swing * 0.8F,
                1.35F, 2.05F, 5.6F, SHOULDER_Y + 0.2F, -0.40F, 0.40F, PURPLE);
        renderLimb(poseStack, consumer, packedLight, overlay, SHOULDER_Y, swing * 0.8F,
                -2.05F, -1.35F, 5.6F, SHOULDER_Y + 0.2F, -0.40F, 0.40F, PURPLE);

        // ----- shoulder pylons -----
        drawBox(poseStack, consumer, 1.40F, 9.2F, -0.90F, 2.30F, 10.6F, 0.90F,
                WHITE, packedLight, overlay);
        drawBox(poseStack, consumer, -2.30F, 9.2F, -0.90F, -1.40F, 10.6F, 0.90F,
                WHITE, packedLight, overlay);

        // ----- head, horn, eyes -----
        drawBox(poseStack, consumer, -0.48F, 10.4F, -0.52F, 0.48F, 11.5F, 0.52F,
                PURPLE, packedLight, overlay);
        drawBox(poseStack, consumer, -0.10F, 11.1F, -0.78F, 0.10F, 12.7F, -0.52F,
                WHITE, packedLight, overlay);
        drawBox(poseStack, consumer, 0.12F, 10.95F, -0.56F, 0.34F, 11.18F, -0.50F,
                GREEN, LightTexture.FULL_BRIGHT, overlay);
        drawBox(poseStack, consumer, -0.34F, 10.95F, -0.56F, -0.12F, 11.18F, -0.50F,
                GREEN, LightTexture.FULL_BRIGHT, overlay);
        // Jaw guard.
        drawBox(poseStack, consumer, -0.30F, 10.4F, -0.62F, 0.30F, 10.75F, -0.50F,
                ORANGE, packedLight, overlay);

        poseStack.popPose();
        super.render(entity, entityYaw, partialTick, poseStack, buffer, packedLight);
    }

    /** Draws one limb box rotated about a horizontal axis at pivotY. */
    private static void renderLimb(PoseStack poseStack, VertexConsumer consumer, int light, int overlay,
                                   float pivotY, float angleRad,
                                   float x0, float x1, float y0, float y1, float z0, float z1, float[] color)
    {
        poseStack.pushPose();
        poseStack.translate(0.0F, pivotY, 0.0F);
        poseStack.mulPose(Axis.XP.rotation(angleRad));
        poseStack.translate(0.0F, -pivotY, 0.0F);
        drawBox(poseStack, consumer, x0, y0, z0, x1, y1, z1, color, light, overlay);
        poseStack.popPose();
    }

    /** Axis-aligned box in model space with simple per-face shading. */
    private static void drawBox(PoseStack poseStack, VertexConsumer consumer,
                                float x0, float y0, float z0, float x1, float y1, float z1,
                                float[] color, int light, int overlay)
    {
        Matrix4f pose = poseStack.last().pose();
        Matrix3f normal = poseStack.last().normal();
        float r = color[0];
        float g = color[1];
        float b = color[2];

        // +Y (top), -Y (bottom), ±Z, ±X — shaded like vanilla block lighting.
        quad(pose, normal, consumer, light, overlay, r, g, b, 1.00F, 0, 1, 0,
                x0, y1, z1, x1, y1, z1, x1, y1, z0, x0, y1, z0);
        quad(pose, normal, consumer, light, overlay, r, g, b, 0.55F, 0, -1, 0,
                x0, y0, z0, x1, y0, z0, x1, y0, z1, x0, y0, z1);
        quad(pose, normal, consumer, light, overlay, r, g, b, 0.88F, 0, 0, -1,
                x0, y1, z0, x1, y1, z0, x1, y0, z0, x0, y0, z0);
        quad(pose, normal, consumer, light, overlay, r, g, b, 0.82F, 0, 0, 1,
                x1, y1, z1, x0, y1, z1, x0, y0, z1, x1, y0, z1);
        quad(pose, normal, consumer, light, overlay, r, g, b, 0.72F, 1, 0, 0,
                x1, y1, z0, x1, y1, z1, x1, y0, z1, x1, y0, z0);
        quad(pose, normal, consumer, light, overlay, r, g, b, 0.72F, -1, 0, 0,
                x0, y1, z1, x0, y1, z0, x0, y0, z0, x0, y0, z1);
    }

    private static void quad(Matrix4f pose, Matrix3f normalPose, VertexConsumer consumer, int light, int overlay,
                             float r, float g, float b, float shade, float nx, float ny, float nz,
                             float ax, float ay, float az, float bx, float by, float bz,
                             float cx, float cy, float cz, float dx, float dy, float dz)
    {
        float[][] uv = {{0.0F, 0.0F}, {1.0F, 0.0F}, {1.0F, 1.0F}, {0.0F, 1.0F}};
        float[][] verts = {{ax, ay, az}, {bx, by, bz}, {cx, cy, cz}, {dx, dy, dz}};
        for (int i = 0; i < 4; i++)
        {
            consumer.vertex(pose, verts[i][0], verts[i][1], verts[i][2])
                    .color(r * shade, g * shade, b * shade, 1.0F)
                    .uv(uv[i][0], uv[i][1])
                    .overlayCoords(overlay)
                    .uv2(light)
                    .normal(normalPose, nx, ny, nz)
                    .endVertex();
        }
    }

    @Override
    public ResourceLocation getTextureLocation(EvaUnit01Entity entity)
    {
        return TEXTURE;
    }
}
