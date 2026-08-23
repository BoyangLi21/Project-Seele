package com.projectseele.mixin.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.supermartijn642.movingelevators.MovingElevators;
import com.supermartijn642.movingelevators.blocks.ElevatorInputBlockEntity;
import com.supermartijn642.movingelevators.blocks.ElevatorInputBlockEntityRenderer;
import com.supermartijn642.movingelevators.blocks.RemoteControllerBlockEntity;
import net.minecraft.client.renderer.MultiBufferSource;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Hides the dependency's up/down arrows behind our labelled car selector. */
@Mixin(value = ElevatorInputBlockEntityRenderer.class, remap = false)
public abstract class MovingElevatorPanelMixin
{
    @Inject(method = "render", at = @At("HEAD"), cancellable = true,
            remap = false)
    private void projectSeele$hideBackingArrows(
            ElevatorInputBlockEntity entity, float partialTicks,
            PoseStack poseStack, MultiBufferSource bufferSource,
            int combinedLight, int combinedOverlay, CallbackInfo callback)
    {
        if (entity instanceof RemoteControllerBlockEntity
                && entity.getLevel() != null
                && entity.getLevel().getBlockState(entity.getBlockPos().above())
                .is(MovingElevators.display_block))
        {
            callback.cancel();
        }
    }
}
