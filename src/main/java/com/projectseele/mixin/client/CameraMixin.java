package com.projectseele.mixin.client;

import com.projectseele.entity.EntryPlugCarrierEntity;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.world.EvaPilotResolver;
import com.projectseele.client.UltramanClientState;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.phys.Vec3;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.ModifyVariable;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Third-person camera cannot frame a 60-block war machine at the vanilla
 * 4-block orbit. Scale the requested zoom distance while piloting; the
 * method's own raycast still clamps it against walls.
 */
@Mixin(Camera.class)
public abstract class CameraMixin
{
    @Shadow
    protected abstract void setPosition(double x, double y, double z);

    @Inject(method = "setup", at = @At("TAIL"))
    private void projectseele$smoothEntryPlugCamera(BlockGetter level,
            Entity subject, boolean detached, boolean mirrored,
            float partialTick, CallbackInfo callback)
    {
        if (detached
                || !(subject.getVehicle() instanceof EntryPlugCarrierEntity plug))
        {
            return;
        }
        Vec3 eye = plug.getInterpolatedPilotEyePosition(partialTick);
        EvaUnit01Entity eva = plug.getLinkedEva();
        if (plug.isLockedToEva() && eva != null
                && eva.isActivationCinematicActive())
        {
            // Continue from the physical capsule eye into the EVA optical
            // socket during the final 30% of synchronization.  Both endpoints
            // are world-space positions, so no camera frame can escape the
            // cabin or jump to the exterior at the nested-ride transition.
            float raw = (eva.getActivationProgress(partialTick) - 0.70F)
                    / 0.30F;
            float t = Math.max(0.0F, Math.min(1.0F, raw));
            float blend = t * t * (3.0F - 2.0F * t);
            Vec3 evaEye = eva.getPilotCameraSeatPosition(subject)
                    .add(0.0D, subject.getEyeHeight(), 0.0D);
            eye = eye.lerp(evaEye, blend);
        }
        this.setPosition(eye.x, eye.y, eye.z);
    }

    @ModifyVariable(method = "getMaxZoom", at = @At("HEAD"), argsOnly = true)
    private double projectseele$extendPlugZoom(double desired)
    {
        Entity subject = ((Camera) (Object) this).getEntity();
        if (subject != null
                && subject.getVehicle() instanceof EntryPlugCarrierEntity plug
                && !plug.isLockedToEva())
        {
            // F5 during black standby/insertion must frame the suspended
            // capsule and crane instead of remaining at vanilla arm's length.
            return desired * 8.0D;
        }
        EvaUnit01Entity eva = subject == null
                ? null : EvaPilotResolver.controlTarget(subject);
        if (eva != null)
        {
            if (eva.isPilotProne())
            {
                return desired * 24.0D;
            }
            // The forward-facing orbit sits in front of the cannon muzzle and
            // needs much more clearance. Keep the normal rear chase camera
            // close enough that the Unit still fills the frame.
            return desired * (Minecraft.getInstance().options.getCameraType().isMirrored()
                    ? 22.0D : 11.6D);
        }
        if (subject instanceof AbstractClientPlayer player)
        {
            float scale = UltramanClientState.scale(player, 0.0F);
            if (scale > 1.01F)
            {
                double multiplier = scale *
                        (Minecraft.getInstance().options.getCameraType()
                                .isMirrored() ? 0.55D : 0.42D);
                return desired * Math.max(1.0D, multiplier);
            }
        }
        return desired;
    }
}
