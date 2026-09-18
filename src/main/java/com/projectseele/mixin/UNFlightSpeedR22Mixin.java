package com.projectseele.mixin;
import com.projectseele.world.UNFlightSpeedR22;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
@Pseudo
@Mixin(targets="org.mtr.core.data.PathData",remap=false)
public abstract class UNFlightSpeedR22Mixin
{
    @Inject(method="getSpeedLimitKilometersPerHour",at=@At("RETURN"),cancellable=true,remap=false)
    private void projectSeele$fastCruise(CallbackInfoReturnable<Long> ci)
    {ci.setReturnValue(UNFlightSpeedR22.adjust(ci.getReturnValue(),this));}
}
