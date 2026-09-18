package com.projectseele.mixin.client;

import com.projectseele.client.AircraftCorrectionAccess;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

/** MTR 4.0.5's stopped-speed multiplier can discard a large remaining offset. */
@Pseudo
@Mixin(targets="org.mtr.mod.data.VehicleExtension",remap=false)
public abstract class AircraftCorrectionBudgetMixin
{
    @Unique private static Field projectSeele$persistent;
    @Unique private static Method projectSeele$speed;
    @Inject(method="getSmoothedVehicleCarsAndPositions(J)Lorg/mtr/libraries/it/unimi/dsi/fastutil/objects/ObjectArrayList;",
            at=@At("HEAD"),remap=false)
    private void projectSeele$boundedAircraftCorrection(long elapsedMillis,CallbackInfoReturnable<Object> callback)
    {
        try
        {
            if(projectSeele$persistent==null)
            {
                projectSeele$persistent=this.getClass().getField("persistentVehicleData");
                projectSeele$speed=this.getClass().getMethod("getSpeed");
            }
            Object data=projectSeele$persistent.get(this);
            if(data instanceof AircraftCorrectionAccess correction)
            {
                correction.projectSeele$aircraftCorrectionBudget(elapsedMillis,((Number)projectSeele$speed.invoke(this)).doubleValue()*1000);
            }
        }
        catch(ReflectiveOperationException error){throw new IllegalStateException("MTR aircraft render correction compatibility",error);}
    }
}
