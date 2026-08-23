package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.client.TreeOfLifeWallClient;
import com.projectseele.entity.NervSiloDoorEntity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
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

/** Left/right armoured doors for all three EVA launch-shaft surface heads. */
public final class NervSiloDoorRenderer
        extends EntityRenderer<NervSiloDoorEntity>
{
    private static final BlockState DOOR =
            Blocks.DEEPSLATE_TILES.defaultBlockState();
    private static final BlockState EDGE =
            Blocks.POLISHED_DEEPSLATE.defaultBlockState();

    public NervSiloDoorRenderer(EntityRendererProvider.Context context)
    {
        super(context);
        this.shadowRadius = 0.0F;
    }

    @Override
    public boolean shouldRender(NervSiloDoorEntity entity, Frustum frustum,
            double cameraX, double cameraY, double cameraZ)
    {
        // The paired 31-block leaves are much larger than their lightweight
        // one-block server entity.  Never cull a tracked hatch by its origin.
        return true;
    }

    @Override
    public void render(NervSiloDoorEntity door, float yaw,
            float partialTick, PoseStack poses, MultiBufferSource buffers,
            int packedLight)
    {
        float open = door.getOpenProgress(partialTick);
        double slide = open * 16.5D;
        poses.pushPose();
        /*
         * The physical shaft core is 31x31, but a leaf that ends exactly on
         * that boundary exposes a one-pixel/one-block-looking ring from
         * grazing camera angles.  Each closed pair now overlaps the armoured
         * collar by one block on all four sides.  The 16.5-block travel still
         * clears the complete 33-block aperture when the doors open.
         */
        renderPanel(poses, buffers, packedLight, DOOR,
                -16.5D - slide, 0.0D, -16.5D,
                16.5F, 0.55F, 33.0F);
        renderPanel(poses, buffers, packedLight, DOOR,
                slide, 0.0D, -16.5D,
                16.5F, 0.55F, 33.0F);
        // Complete perimeter trim: north, south and the two outside edges.
        renderPanel(poses, buffers, packedLight, EDGE,
                -16.5D - slide, 0.56D, -16.5D,
                16.5F, 0.12F, 1.0F);
        renderPanel(poses, buffers, packedLight, EDGE,
                slide, 0.56D, -16.5D,
                16.5F, 0.12F, 1.0F);
        renderPanel(poses, buffers, packedLight, EDGE,
                -16.5D - slide, 0.56D, 15.5D,
                16.5F, 0.12F, 1.0F);
        renderPanel(poses, buffers, packedLight, EDGE,
                slide, 0.56D, 15.5D,
                16.5F, 0.12F, 1.0F);
        renderPanel(poses, buffers, packedLight, EDGE,
                -16.5D - slide, 0.56D, -16.5D,
                1.0F, 0.12F, 33.0F);
        renderPanel(poses, buffers, packedLight, EDGE,
                15.5D + slide, 0.56D, -16.5D,
                1.0F, 0.12F, 33.0F);
        renderSplitLogo(poses, buffers, slide);
        poses.popPose();
        super.render(door, yaw, partialTick, poses, buffers, packedLight);
    }

    private static void renderSplitLogo(PoseStack poses,
            MultiBufferSource buffers, double slide)
    {
        ResourceLocation texture = TreeOfLifeWallClient.nervLogoTexture(
                Minecraft.getInstance());
        if (texture == null)
        {
            return;
        }
        VertexConsumer consumer = buffers.getBuffer(
                RenderType.entityTranslucent(texture));
        logoHalf(poses, consumer, -10.0D - slide, -slide,
                -10.0D, 10.0D, 0.60D, 0.0F, 0.5F);
        logoHalf(poses, consumer, slide, 10.0D + slide,
                -10.0D, 10.0D, 0.60D, 0.5F, 1.0F);
    }

    private static void logoHalf(PoseStack poses, VertexConsumer consumer,
            double x0, double x1, double z0, double z1, double y,
            float u0, float u1)
    {
        Matrix4f matrix = poses.last().pose();
        Matrix3f normal = poses.last().normal();
        logoVertex(consumer, matrix, normal, x0, y, z1, u0, 1.0F);
        logoVertex(consumer, matrix, normal, x1, y, z1, u1, 1.0F);
        logoVertex(consumer, matrix, normal, x1, y, z0, u1, 0.0F);
        logoVertex(consumer, matrix, normal, x0, y, z0, u0, 0.0F);
    }

    private static void logoVertex(VertexConsumer consumer, Matrix4f pose,
            Matrix3f normal, double x, double y, double z, float u, float v)
    {
        consumer.vertex(pose, (float)x, (float)y, (float)z)
                .color(255, 255, 255, 255).uv(u, v)
                .overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(0x00F000F0).normal(normal, 0.0F, 1.0F, 0.0F)
                .endVertex();
    }

    private static void renderPanel(PoseStack poses,
            MultiBufferSource buffers, int light, BlockState state,
            double x, double y, double z, float sizeX, float sizeY,
            float sizeZ)
    {
        poses.pushPose();
        poses.translate(x, y, z);
        poses.scale(sizeX, sizeY, sizeZ);
        Minecraft.getInstance().getBlockRenderer().renderSingleBlock(
                state, poses, buffers, light, OverlayTexture.NO_OVERLAY);
        poses.popPose();
    }

    @Override
    public ResourceLocation getTextureLocation(NervSiloDoorEntity entity)
    {
        return TextureAtlas.LOCATION_BLOCKS;
    }
}
