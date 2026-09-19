package com.projectseele.mixin;

import com.projectseele.entity.SbwRestCollisionR24;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import org.spongepowered.asm.mixin.*;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Pseudo
@Mixin(targets="com.atsuishio.superbwarfare.entity.vehicle.base.VehicleEntity",remap=false)
public abstract class SbwRestCollisionR24Mixin
{
    @Inject(method="vCollide",at=@At("HEAD"),cancellable=true)
    private void seele$restCollision(Vec3 input,CallbackInfoReturnable<Vec3> result)
    {Vec3 cached=SbwRestCollisionR24.before((Entity)(Object)this,input);if(cached!=null)result.setReturnValue(cached);}
    @Inject(method="vCollide",at=@At("RETURN"))
    private void seele$rememberCollision(Vec3 input,CallbackInfoReturnable<Vec3> result)
    {SbwRestCollisionR24.after((Entity)(Object)this,result.getReturnValue());}
}
