package com.projectseele.mixin.client;

import com.projectseele.client.CommanderPoseClient;
import com.projectseele.client.UltramanClientState;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.world.entity.LivingEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Applies the iconic elbows-supported, hands-before-mouth commander pose after
 * vanilla has resolved riding, held items and head tracking for this frame.
 */
@Mixin(PlayerModel.class)
public abstract class PlayerModelGendoPoseMixin
{
    @Inject(method = "setupAnim(Lnet/minecraft/world/entity/LivingEntity;FFFFF)V",
            at = @At("TAIL"))
    private void projectSeele$applyCommanderPose(LivingEntity entity,
            float limbSwing, float limbSwingAmount, float ageInTicks,
            float netHeadYaw, float headPitch, CallbackInfo callback)
    {
        if (entity instanceof AbstractClientPlayer player
                && UltramanClientState.hayataPose(player))
        {
            PlayerModel<?> model = (PlayerModel<?>)(Object)this;
            model.rightArm.xRot = (float)Math.toRadians(-164.0D);
            model.rightArm.yRot = (float)Math.toRadians(-8.0D);
            model.rightArm.zRot = (float)Math.toRadians(8.0D);
            model.leftArm.xRot = (float)Math.toRadians(-64.0D);
            model.leftArm.yRot = (float)Math.toRadians(18.0D);
            model.leftArm.zRot = (float)Math.toRadians(-24.0D);
            model.rightSleeve.copyFrom(model.rightArm);
            model.leftSleeve.copyFrom(model.leftArm);
            model.head.xRot = (float)Math.toRadians(-12.0D);
            model.hat.copyFrom(model.head);
            return;
        }
        if (!entity.isPassenger() || !CommanderPoseClient.isActive(entity))
        {
            return;
        }

        PlayerModel<?> model = (PlayerModel<?>)(Object)this;
        // The vanilla player arm is a single rigid cuboid, so it cannot place
        // an elbow on the desk and then bend the forearm back toward the face.
        // A dedicated two-segment render layer supplies both arms while this
        // pose is active; hide only the vanilla straight-arm geometry.
        model.rightArm.visible = false;
        model.leftArm.visible = false;
        model.rightSleeve.visible = false;
        model.leftSleeve.visible = false;
    }
}
