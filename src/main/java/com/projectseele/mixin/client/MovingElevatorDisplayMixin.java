package com.projectseele.mixin.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.supermartijn642.movingelevators.MovingElevators;
import com.supermartijn642.movingelevators.blocks.DisplayBlockEntity;
import com.supermartijn642.movingelevators.blocks.DisplayBlockEntityRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Centres the official floor name across Project SEELE's two-block fascia. */
@Mixin(value = DisplayBlockEntityRenderer.class, remap = false)
public abstract class MovingElevatorDisplayMixin
{
    @Unique
    private float projectSeele$wideTextOffset;

    @Unique
    private boolean projectSeele$textPosePushed;

    @Inject(method = "render(Lcom/supermartijn642/movingelevators/blocks/DisplayBlockEntity;FLcom/mojang/blaze3d/vertex/PoseStack;Lnet/minecraft/client/renderer/MultiBufferSource;II)V",
            at = @At("HEAD"), remap = false)
    private void projectSeele$locateWideFascia(
            DisplayBlockEntity entity, float partialTicks,
            PoseStack poseStack, MultiBufferSource bufferSource,
            int combinedLight, int combinedOverlay, CallbackInfo callback)
    {
        this.projectSeele$wideTextOffset = 0.0F;
        Level level = entity.getLevel();
        if (level == null || !entity.isBottomDisplay())
        {
            return;
        }
        Direction localRight = entity.getFacing().getClockWise();
        BlockPos origin = entity.getBlockPos();
        for (Direction candidate : new Direction[]{
                localRight, localRight.getOpposite()})
        {
            BlockPos companion = origin.relative(candidate);
            if (level.getBlockState(companion)
                    .is(MovingElevators.display_block)
                    && !level.getBlockState(companion.below())
                    .is(MovingElevators.button_block))
            {
                this.projectSeele$wideTextOffset =
                        candidate == localRight ? 0.5F : -0.5F;
                return;
            }
        }
    }

    @Inject(method = "drawString", at = @At("HEAD"), remap = false)
    private void projectSeele$centreAcrossTwoBlocks(
            PoseStack poseStack, MultiBufferSource bufferSource,
            int color, String text, CallbackInfo callback)
    {
        this.projectSeele$textPosePushed = false;
        if (this.projectSeele$wideTextOffset == 0.0F)
        {
            return;
        }
        poseStack.pushPose();
        poseStack.translate(this.projectSeele$wideTextOffset, 0.0D, 0.0D);
        this.projectSeele$textPosePushed = true;
    }

    @Inject(method = "drawString", at = @At("RETURN"), remap = false)
    private void projectSeele$restoreTextPose(
            PoseStack poseStack, MultiBufferSource bufferSource,
            int color, String text, CallbackInfo callback)
    {
        if (this.projectSeele$textPosePushed)
        {
            poseStack.popPose();
            this.projectSeele$textPosePushed = false;
        }
    }
}
