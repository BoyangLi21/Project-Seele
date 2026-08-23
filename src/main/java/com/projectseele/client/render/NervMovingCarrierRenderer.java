package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.projectseele.world.EvaHangarBuilder;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.block.BlockRenderDispatcher;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/** Frame-direct EVA carrier, following Moving Elevators' non-entity model. */
public final class NervMovingCarrierRenderer
{
    private NervMovingCarrierRenderer() {}

    public static void render(PoseStack poses, MultiBufferSource buffers,
                              int packedLight, int variant)
    {
        BlockRenderDispatcher blocks = Minecraft.getInstance()
                .getBlockRenderer();
        float half = EvaHangarBuilder.CARRIER_HALF_EXTENT;
        float inner = half * 2.0F - 1.0F;
        float full = half * 2.0F + 1.0F;
        BlockState accent = switch (variant)
        {
            case 0 -> Blocks.ORANGE_CONCRETE.defaultBlockState();
            case 2 -> Blocks.RED_CONCRETE.defaultBlockState();
            default -> Blocks.PURPLE_CONCRETE.defaultBlockState();
        };

        // Top surface ends at y=+0.07 relative to the EVA's feet, so it is
        // visible above the rail bed and physically reads as supporting it.
        block(blocks, poses, buffers, packedLight,
                Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState(),
                -half + 0.5F, -0.28F, -half + 0.5F,
                inner, 0.35F, inner);
        block(blocks, poses, buffers, packedLight,
                Blocks.IRON_BLOCK.defaultBlockState(),
                -half - 0.5F, -0.27F, -half - 0.5F,
                full, 0.55F, 1.0F);
        block(blocks, poses, buffers, packedLight,
                Blocks.IRON_BLOCK.defaultBlockState(),
                -half - 0.5F, -0.27F, half - 0.5F,
                full, 0.55F, 1.0F);
        block(blocks, poses, buffers, packedLight,
                Blocks.IRON_BLOCK.defaultBlockState(),
                -half - 0.5F, -0.27F, -half + 0.5F,
                1.0F, 0.55F, inner);
        block(blocks, poses, buffers, packedLight,
                Blocks.IRON_BLOCK.defaultBlockState(),
                half - 0.5F, -0.27F, -half + 0.5F,
                1.0F, 0.55F, inner);
        BlockState underframe = Blocks.REINFORCED_DEEPSLATE
                .defaultBlockState();
        block(blocks, poses, buffers, packedLight, underframe,
                -6.2F, -0.72F, -half + 1.5F,
                1.25F, 0.42F, inner - 2.0F);
        block(blocks, poses, buffers, packedLight, underframe,
                4.95F, -0.72F, -half + 1.5F,
                1.25F, 0.42F, inner - 2.0F);
        for (float z = -11.0F; z <= 11.0F; z += 5.5F)
        {
            block(blocks, poses, buffers, packedLight,
                    Blocks.CUT_COPPER.defaultBlockState(),
                    -10.0F, -0.62F, z,
                    20.0F, 0.30F, 0.70F);
        }
        for (float x : new float[]{-5.65F, 4.65F})
        {
            for (float z : new float[]{-9.0F, 8.0F})
            {
                block(blocks, poses, buffers, packedLight,
                        Blocks.POLISHED_BLACKSTONE.defaultBlockState(),
                        x, -0.78F, z, 1.0F, 0.50F, 2.0F);
                block(blocks, poses, buffers, packedLight,
                        Blocks.COPPER_BLOCK.defaultBlockState(),
                        x + 0.15F, -0.92F, z + 0.25F,
                        0.70F, 0.18F, 1.50F);
            }
        }
    }

    private static void block(BlockRenderDispatcher blocks,
                              PoseStack poses, MultiBufferSource buffers,
                              int packedLight, BlockState state,
                              float x, float y, float z,
                              float scaleX, float scaleY, float scaleZ)
    {
        poses.pushPose();
        poses.translate(x, y, z);
        poses.scale(scaleX, scaleY, scaleZ);
        blocks.renderSingleBlock(state, poses, buffers, packedLight,
                OverlayTexture.NO_OVERLAY);
        poses.popPose();
    }
}
