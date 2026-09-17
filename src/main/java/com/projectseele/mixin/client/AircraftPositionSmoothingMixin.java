package com.projectseele.mixin.client;

import com.projectseele.ProjectSeele;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;
import java.lang.reflect.Field;

/** A fast aircraft can receive an ordinary correction longer than its fuselage. */
@Pseudo
@Mixin(targets="org.mtr.mod.data.PersistentVehicleData",remap=false)
public abstract class AircraftPositionSmoothingMixin
{
    @Unique private static Field projectSeele$mode;
    @Unique private static boolean projectSeele$reported;

    @ModifyVariable(method="update(DD)V",at=@At("HEAD"),argsOnly=true,ordinal=1,remap=false)
    private double projectSeele$aircraftCorrectionRange(double vehicleLength)
    {
        try
        {
            if(projectSeele$mode==null)
            {
                projectSeele$mode=this.getClass().getDeclaredField("transportMode");
                projectSeele$mode.setAccessible(true);
            }
            if(!"AIRPLANE".equals(String.valueOf(projectSeele$mode.get(this))))return vehicleLength;
            // MTR 4.0.5 clears its interpolation offset above length-1.
            // F1 is 30 m long but travels 83 m/s. Ordinary packet corrections
            // can cross that threshold. Preserve its speed-based smoothing
            // and still reset on large route changes.
            if(!projectSeele$reported)
            {
                projectSeele$reported=true;
                ProjectSeele.LOGGER.info("R19 native aircraft interpolation range active; original length={}",vehicleLength);
            }
            return Math.max(vehicleLength,256.0D);
        }
        catch(ReflectiveOperationException error)
        {
            throw new IllegalStateException("MTR 4.0.5 aircraft interpolation compatibility",error);
        }
    }
}
