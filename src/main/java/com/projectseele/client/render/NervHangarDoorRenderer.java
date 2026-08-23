package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.client.TreeOfLifeWallClient;
import com.projectseele.entity.NervHangarDoorEntity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.culling.Frustum;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.client.renderer.texture.TextureAtlas;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import org.joml.Matrix3f;
import org.joml.Matrix4f;

/** Paired sideways pressure doors at the rear of each wet cage. */
public final class NervHangarDoorRenderer
        extends EntityRenderer<NervHangarDoorEntity>
{
    private static final BlockState DOOR =
            Blocks.DEEPSLATE_TILES.defaultBlockState();

    public NervHangarDoorRenderer(EntityRendererProvider.Context context)
    {
        super(context);
        this.shadowRadius = 0.0F;
    }

    @Override
    public boolean shouldRender(NervHangarDoorEntity entity, Frustum frustum,
            double cameraX, double cameraY, double cameraZ)
    {
        /*
         * The server entity deliberately owns a one-block AABB, while its two
         * visual leaves span up to 67 x 65 blocks.  Testing only the origin
         * made a door vanish when the camera saw a leaf but not that origin.
         * At most three transient gates exist, so keeping tracked gates
         * renderable is deterministic and cheaper than a giant server AABB.
         */
        return true;
    }

    @Override
    public void render(NervHangarDoorEntity door, float yaw,
            float partialTick, PoseStack poses, MultiBufferSource buffers,
            int packedLight)
    {
        int facilityLight = LightTexture.FULL_BRIGHT;
        double slide = door.getOpenProgress(partialTick) * 17.0D;
        poses.pushPose();
        panel(poses, buffers, facilityLight,
                -16.5D - slide, 0.0D, -0.25D,
                16.5F, 65.0F, 0.5F);
        panel(poses, buffers, facilityLight,
                slide, 0.0D, -0.25D,
                16.5F, 65.0F, 0.5F);
        splitLogo(poses, buffers, slide);
        poses.popPose();
        super.render(door, yaw, partialTick, poses, buffers, packedLight);
    }

    private static void splitLogo(PoseStack poses,
            MultiBufferSource buffers, double slide)
    {
        ResourceLocation texture = TreeOfLifeWallClient.nervLogoTexture(
                Minecraft.getInstance());
        if (texture == null) return;
        VertexConsumer consumer = buffers.getBuffer(
                RenderType.entityTranslucent(texture));
        logoHalf(poses, consumer, -12.0D - slide, -slide,
                18.0D, 46.0D, -0.515D, 1.0F, 0.5F);
        logoHalf(poses, consumer, slide, 12.0D + slide,
                18.0D, 46.0D, -0.515D, 0.5F, 0.0F);
    }

    private static void logoHalf(PoseStack poses, VertexConsumer consumer,
            double x0, double x1, double y0, double y1, double z,
            float u0, float u1)
    {
        Matrix4f matrix = poses.last().pose();
        Matrix3f normal = poses.last().normal();
        vertex(consumer, matrix, normal, x0, y0, z, u0, 1.0F);
        vertex(consumer, matrix, normal, x1, y0, z, u1, 1.0F);
        vertex(consumer, matrix, normal, x1, y1, z, u1, 0.0F);
        vertex(consumer, matrix, normal, x0, y1, z, u0, 0.0F);
    }

    private static void vertex(VertexConsumer consumer, Matrix4f pose,
            Matrix3f normal, double x, double y, double z, float u, float v)
    {
        consumer.vertex(pose, (float)x, (float)y, (float)z)
                .color(255, 255, 255, 255).uv(u, v)
                .overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(0x00F000F0).normal(normal, 0.0F, 0.0F, -1.0F)
                .endVertex();
    }

    private static void panel(PoseStack poses, MultiBufferSource buffers,
            int light, double x, double y, double z,
            float sx, float sy, float sz)
    {
        poses.pushPose();
        poses.translate(x, y, z);
        poses.scale(sx, sy, sz);
        Minecraft.getInstance().getBlockRenderer().renderSingleBlock(
                DOOR, poses, buffers, light, OverlayTexture.NO_OVERLAY);
        poses.popPose();
    }

    @Override
    public ResourceLocation getTextureLocation(NervHangarDoorEntity entity)
    {
        return TextureAtlas.LOCATION_BLOCKS;
    }
}
