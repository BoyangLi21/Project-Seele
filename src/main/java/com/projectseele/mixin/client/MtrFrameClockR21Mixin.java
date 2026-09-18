package com.projectseele.mixin.client;

import com.projectseele.client.AircraftRenderClockR21;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** MTR's frame-duration fallback can advance twice during auxiliary views. */
@Pseudo
@Mixin(targets="org.mtr.mod.render.MainRenderer",remap=false)
public abstract class MtrFrameClockR21Mixin
{
    @Inject(method="getMillisElapsed()J",at=@At("RETURN"),cancellable=true,remap=false)
    private static void projectSeele$singleSimulationClock(CallbackInfoReturnable<Long> callback)
    {
        callback.setReturnValue(AircraftRenderClockR21.simulationMillis());
    }
}
