package com.projectseele.mixin.client;

import com.projectseele.entity.EntryPlugCarrierEntity;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.world.EvaPilotResolver;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

/**
 * Third-person camera cannot frame a 60-block war machine at the vanilla
 * 4-block orbit. Scale the requested zoom distance while piloting; the
 * method's own raycast still clamps it against walls.
 */
@Mixin(Camera.class)
public abstract class CameraMixin
{
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
        return desired;
    }
}
