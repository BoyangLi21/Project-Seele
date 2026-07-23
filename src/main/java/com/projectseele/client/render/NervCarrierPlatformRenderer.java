package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.projectseele.entity.NervCarrierPlatformEntity;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.block.BlockRenderDispatcher;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.inventory.InventoryMenu;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/** Industrial 11x11 carrier silhouette rendered by one tracked entity. */
public final class NervCarrierPlatformRenderer
        extends EntityRenderer<NervCarrierPlatformEntity>
{
    private final BlockRenderDispatcher blocks;

    public NervCarrierPlatformRenderer(EntityRendererProvider.Context context)
    {
        super(context);
        this.blocks = context.getBlockRenderDispatcher();
        this.shadowRadius = 0.0F;
    }

    @Override
    public void render(NervCarrierPlatformEntity entity, float yaw,
                       float partialTick, PoseStack poses,
                       MultiBufferSource buffers, int packedLight)
    {
        BlockState accent = switch (entity.getUnitVariant())
        {
            case 0 -> Blocks.ORANGE_CONCRETE.defaultBlockState();
            case 2 -> Blocks.RED_CONCRETE.defaultBlockState();
            default -> Blocks.PURPLE_CONCRETE.defaultBlockState();
        };
        renderBlock(poses, buffers, packedLight,
                Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState(),
                -4.5F, -0.28F, -4.5F, 9.0F, 0.35F, 9.0F);
        renderBlock(poses, buffers, packedLight,
                Blocks.IRON_BLOCK.defaultBlockState(),
                -5.5F, -0.27F, -5.5F, 11.0F, 0.55F, 1.0F);
        renderBlock(poses, buffers, packedLight,
                Blocks.IRON_BLOCK.defaultBlockState(),
                -5.5F, -0.27F, 4.5F, 11.0F, 0.55F, 1.0F);
        renderBlock(poses, buffers, packedLight,
                Blocks.IRON_BLOCK.defaultBlockState(),
                -5.5F, -0.27F, -4.5F, 1.0F, 0.55F, 9.0F);
        renderBlock(poses, buffers, packedLight,
                Blocks.IRON_BLOCK.defaultBlockState(),
                4.5F, -0.27F, -4.5F, 1.0F, 0.55F, 9.0F);
        renderBlock(poses, buffers, packedLight, accent,
                -0.5F, 0.08F, -4.5F, 1.0F, 0.16F, 9.0F);
        super.render(entity, yaw, partialTick, poses, buffers, packedLight);
    }

    private void renderBlock(PoseStack poses, MultiBufferSource buffers,
                             int packedLight, BlockState state,
                             float x, float y, float z,
                             float scaleX, float scaleY, float scaleZ)
    {
        poses.pushPose();
        poses.translate(x, y, z);
        poses.scale(scaleX, scaleY, scaleZ);
        this.blocks.renderSingleBlock(state, poses, buffers, packedLight,
                OverlayTexture.NO_OVERLAY);
        poses.popPose();
    }

    @Override
    public ResourceLocation getTextureLocation(
            NervCarrierPlatformEntity entity)
    {
        return InventoryMenu.BLOCK_ATLAS;
    }
}
