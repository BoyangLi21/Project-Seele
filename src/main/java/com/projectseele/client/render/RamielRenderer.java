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
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Vector3f;

/**
 * Renders Ramiel as a mathematically exact octahedron: a translucent blue
 * crystal shell around a glowing red core. No model file needed.
 */
public class RamielRenderer extends EntityRenderer<RamielEntity>
{
    private static final ResourceLocation TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/ramiel.png");

    public RamielRenderer(EntityRendererProvider.Context context)
    {
        super(context);
        this.shadowRadius = 0.0F;
    }

    @Override
    public void render(RamielEntity entity, float entityYaw, float partialTick, PoseStack poseStack,
                       MultiBufferSource buffer, int packedLight)
    {
        poseStack.pushPose();
        poseStack.translate(0.0D, entity.getBbHeight() * 0.5D, 0.0D);
        poseStack.mulPose(Axis.YP.rotationDegrees(entity.getSpin(partialTick)));

        VertexConsumer consumer = buffer.getBuffer(RenderType.entityTranslucent(TEXTURE));
        int fullBright = LightTexture.FULL_BRIGHT;

        // Core first so the translucent shell blends over it.
        float corePulse = entity.isCharging()
                ? 1.1F + 0.3F * Mth.sin((entity.tickCount + partialTick) * 0.5F)
                : 0.95F;
        drawOctahedron(poseStack, consumer, 1.05F * corePulse, 1.0F, 0.12F, 0.18F, 1.0F, fullBright);
        drawOctahedron(poseStack, consumer, 3.3F, 0.45F, 0.72F, 1.0F, 0.7F, fullBright);

        poseStack.popPose();
        super.render(entity, entityYaw, partialTick, poseStack, buffer, packedLight);
    }

    private static void drawOctahedron(PoseStack poseStack, VertexConsumer consumer, float size,
                                       float red, float green, float blue, float alpha, int packedLight)
    {
        Matrix4f pose = poseStack.last().pose();
        Matrix3f normalPose = poseStack.last().normal();

        Vector3f[] v = {
                new Vector3f(0.0F, size, 0.0F),   // 0: top apex
                new Vector3f(0.0F, -size, 0.0F),  // 1: bottom apex
                new Vector3f(size, 0.0F, 0.0F),   // 2: +X
                new Vector3f(0.0F, 0.0F, size),   // 3: +Z
                new Vector3f(-size, 0.0F, 0.0F),  // 4: -X
                new Vector3f(0.0F, 0.0F, -size)   // 5: -Z
        };
        int[][] faces = {
                {0, 2, 3}, {0, 3, 4}, {0, 4, 5}, {0, 5, 2},
                {1, 3, 2}, {1, 4, 3}, {1, 5, 4}, {1, 2, 5}
        };
        float[][] uvs = {{0.5F, 0.0F}, {0.0F, 1.0F}, {1.0F, 1.0F}};

        for (int f = 0; f < faces.length; f++)
        {
            Vector3f a = v[faces[f][0]];
            Vector3f b = v[faces[f][1]];
            Vector3f c = v[faces[f][2]];
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
