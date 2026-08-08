package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import com.projectseele.entity.NervCarrierPlatformEntity;
import com.projectseele.world.EvaHangarBuilder;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.block.BlockRenderDispatcher;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.inventory.InventoryMenu;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/** Industrial carrier silhouette rendered by one tracked entity. */
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
        if (entity.isArmamentLift())
        {
            poses.pushPose();
            poses.mulPose(Axis.YP.rotationDegrees(entity.getYRot()));
            renderArmamentLift(entity, poses, buffers, packedLight);
            poses.popPose();
            super.render(entity, yaw, partialTick, poses, buffers,
                    packedLight);
            return;
        }
        if (entity.isPersonnelLift())
        {
            poses.pushPose();
            poses.mulPose(Axis.YP.rotationDegrees(entity.getYRot()));
            renderPersonnelLift(entity, poses, buffers, packedLight);
            poses.popPose();
            super.render(entity, yaw, partialTick, poses, buffers, packedLight);
            return;
        }
        float half = EvaHangarBuilder.CARRIER_HALF_EXTENT;
        float inner = half * 2.0F - 1.0F;
        float full = half * 2.0F + 1.0F;
        BlockState accent = switch (entity.getUnitVariant())
        {
            case 0 -> Blocks.ORANGE_CONCRETE.defaultBlockState();
            case 2 -> Blocks.RED_CONCRETE.defaultBlockState();
            default -> Blocks.PURPLE_CONCRETE.defaultBlockState();
        };
        renderBlock(poses, buffers, packedLight,
                Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState(),
                -half + 0.5F, -0.28F, -half + 0.5F,
                inner, 0.35F, inner);
        renderBlock(poses, buffers, packedLight,
                Blocks.IRON_BLOCK.defaultBlockState(),
                -half - 0.5F, -0.27F, -half - 0.5F,
                full, 0.55F, 1.0F);
        renderBlock(poses, buffers, packedLight,
                Blocks.IRON_BLOCK.defaultBlockState(),
                -half - 0.5F, -0.27F, half - 0.5F,
                full, 0.55F, 1.0F);
        renderBlock(poses, buffers, packedLight,
                Blocks.IRON_BLOCK.defaultBlockState(),
                -half - 0.5F, -0.27F, -half + 0.5F,
                1.0F, 0.55F, inner);
        renderBlock(poses, buffers, packedLight,
                Blocks.IRON_BLOCK.defaultBlockState(),
                half - 0.5F, -0.27F, -half + 0.5F,
                1.0F, 0.55F, inner);
        renderBlock(poses, buffers, packedLight, accent,
                -0.5F, 0.08F, -half + 0.5F,
                1.0F, 0.16F, inner);
        super.render(entity, yaw, partialTick, poses, buffers, packedLight);
    }

    /** Payload-only cradle: low deck, four guide shoes and visible clamps. */
    private void renderArmamentLift(NervCarrierPlatformEntity entity,
                                    PoseStack poses,
                                    MultiBufferSource buffers,
                                    int packedLight)
    {
        BlockState accent = switch (entity.getUnitVariant())
        {
            case 0 -> Blocks.ORANGE_CONCRETE.defaultBlockState();
            case 2 -> Blocks.RED_CONCRETE.defaultBlockState();
            default -> Blocks.PURPLE_CONCRETE.defaultBlockState();
        };
        BlockState frame = Blocks.POLISHED_DEEPSLATE.defaultBlockState();
        BlockState deck = Blocks.IRON_BLOCK.defaultBlockState();
        BlockState lamp = Blocks.SEA_LANTERN.defaultBlockState();

        renderBlock(poses, buffers, packedLight, frame,
                -4.0F, -0.28F, -4.0F, 8.0F, 0.34F, 8.0F);
        renderBlock(poses, buffers, packedLight, deck,
                -3.55F, 0.06F, -3.55F, 7.1F, 0.20F, 7.1F);
        renderBlock(poses, buffers, packedLight, accent,
                -0.22F, 0.26F, -3.55F, 0.44F, 0.12F, 7.1F);
        renderBlock(poses, buffers, packedLight, accent,
                -3.55F, 0.26F, -0.22F, 7.1F, 0.12F, 0.44F);

        for (float x : new float[] {-3.75F, 3.35F})
        {
            for (float z : new float[] {-3.75F, 3.35F})
            {
                renderBlock(poses, buffers, packedLight, frame,
                        x, -0.12F, z, 0.40F, 1.0F, 0.40F);
                renderBlock(poses, buffers, packedLight, lamp,
                        x + 0.06F, 0.88F, z + 0.06F,
                        0.28F, 0.22F, 0.28F);
            }
        }

        // Opposed hydraulic jaws stay visibly closed while the payload rides.
        renderBlock(poses, buffers, packedLight, frame,
                -2.65F, 0.28F, -0.55F, 2.15F, 0.72F, 1.1F);
        renderBlock(poses, buffers, packedLight, frame,
                0.50F, 0.28F, -0.55F, 2.15F, 0.72F, 1.1F);
        renderBlock(poses, buffers, packedLight, accent,
                -0.58F, 0.70F, -0.65F, 1.16F, 0.18F, 1.3F);
    }

    /**
     * Fully enclosed five-by-five personnel car.
     *
     * <p>The first smooth-cabin prototype rendered an open maintenance deck
     * with rails.  That made the shaft wall look like the back of the lift and
     * removed the familiar enclosed car, door and floor controls.  Keep the
     * continuously moving entity, but render the same closed room silhouette
     * as the proven block cabin.  Local +Z is the doorway and the entity yaw
     * is aligned to the audited landing exit.</p>
     */
    private void renderPersonnelLift(NervCarrierPlatformEntity entity,
                                     PoseStack poses,
                                     MultiBufferSource buffers,
                                     int packedLight)
    {
        BlockState accent = switch (entity.getLiftAccent())
        {
            case 1 -> Blocks.PURPLE_CONCRETE.defaultBlockState();
            case 2 -> Blocks.CYAN_CONCRETE.defaultBlockState();
            case 3 -> Blocks.RED_CONCRETE.defaultBlockState();
            case 4 -> Blocks.YELLOW_CONCRETE.defaultBlockState();
            default -> Blocks.ORANGE_CONCRETE.defaultBlockState();
        };
        BlockState frame = Blocks.POLISHED_DEEPSLATE.defaultBlockState();
        BlockState shell = Blocks.IRON_BLOCK.defaultBlockState();
        BlockState lining = Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState();
        BlockState deck = Blocks.POLISHED_DEEPSLATE.defaultBlockState();
        BlockState lamp = Blocks.SEA_LANTERN.defaultBlockState();
        BlockState panel = Blocks.BLACK_CONCRETE.defaultBlockState();
        BlockState door = Blocks.GRAY_STAINED_GLASS.defaultBlockState();

        // Structural floor and ceiling: no open shaft is visible from inside.
        renderBlock(poses, buffers, packedLight, frame,
                -2.4F, -0.20F, -2.4F, 4.8F, 0.20F, 4.8F);
        renderBlock(poses, buffers, packedLight, deck,
                -2.15F, 0.00F, -2.15F, 4.3F, 0.16F, 4.3F);
        renderBlock(poses, buffers, packedLight, shell,
                -2.4F, 3.24F, -2.4F, 4.8F, 0.22F, 4.8F);

        // Back and side walls are continuous slabs, not railings.
        renderBlock(poses, buffers, packedLight, shell,
                -2.4F, 0.00F, -2.4F, 4.8F, 3.24F, 0.18F);
        renderBlock(poses, buffers, packedLight, lining,
                -2.18F, 0.18F, -2.18F, 4.36F, 2.88F, 0.10F);
        renderBlock(poses, buffers, packedLight, shell,
                -2.4F, 0.00F, -2.4F, 0.18F, 3.24F, 4.8F);
        renderBlock(poses, buffers, packedLight, shell,
                2.22F, 0.00F, -2.4F, 0.18F, 3.24F, 4.8F);

        // Narrow front jambs leave a three-block-wide passenger aperture.
        renderBlock(poses, buffers, packedLight, shell,
                -2.4F, 0.00F, 2.22F, 0.90F, 3.24F, 0.18F);
        renderBlock(poses, buffers, packedLight, shell,
                1.50F, 0.00F, 2.22F, 0.90F, 3.24F, 0.18F);

        // Two real sliding leaves.  Open leaves park behind the jambs.
        if (entity.isLiftDoorOpen())
        {
            renderBlock(poses, buffers, packedLight, door,
                    -2.20F, 0.12F, 2.10F, 0.62F, 2.92F, 0.12F);
            renderBlock(poses, buffers, packedLight, door,
                    1.58F, 0.12F, 2.10F, 0.62F, 2.92F, 0.12F);
        }
        else
        {
            renderBlock(poses, buffers, packedLight, door,
                    -1.50F, 0.12F, 2.10F, 1.50F, 2.92F, 0.12F);
            renderBlock(poses, buffers, packedLight, door,
                    0.00F, 0.12F, 2.10F, 1.50F, 2.92F, 0.12F);
        }

        // Ceiling light and an unmistakable two-key UP/DOWN panel.
        renderBlock(poses, buffers, packedLight, lamp,
                -0.80F, 3.05F, -0.75F, 1.60F, 0.16F, 1.50F);
        renderBlock(poses, buffers, packedLight, panel,
                2.10F, 0.88F, 0.62F, 0.12F, 1.42F, 0.74F);
        renderBlock(poses, buffers, packedLight,
                Blocks.LIME_CONCRETE.defaultBlockState(),
                2.02F, 1.72F, 0.80F, 0.10F, 0.24F, 0.24F);
        renderBlock(poses, buffers, packedLight,
                Blocks.ORANGE_CONCRETE.defaultBlockState(),
                2.02F, 1.22F, 0.80F, 0.10F, 0.24F, 0.24F);
        renderBlock(poses, buffers, packedLight, accent,
                -0.10F, 0.17F, -2.08F, 0.20F, 0.05F, 4.12F);
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
