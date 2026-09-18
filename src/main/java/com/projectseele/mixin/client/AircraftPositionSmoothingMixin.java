package com.projectseele.mixin.client;

import com.projectseele.ProjectSeele;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import java.lang.reflect.Field;

/** A fast aircraft can receive an ordinary correction longer than its fuselage. */
@Pseudo
@Mixin(targets="org.mtr.mod.data.PersistentVehicleData",remap=false)
public abstract class AircraftPositionSmoothingMixin implements com.projectseele.client.AircraftCorrectionAccess
{
    @Unique private static Field projectSeele$mode;
    @Unique private static boolean projectSeele$reported;
    @Unique private long projectSeele$lastFrame=-1;
    @Unique private double projectSeele$pendingBudget=Double.NaN;
    @Unique private double projectSeele$seconds,projectSeele$speed,projectSeele$presented;
    @Unique private boolean projectSeele$observation;
    @Unique private boolean projectSeele$hasSample;
    @Unique private double projectSeele$lastRaw;
    @Unique private int projectSeele$coordinateEpoch;
    @Shadow private double railProgressSmoothingAdjustment;
    @Shadow private double smoothedRailProgress;
    @Override public String projectSeele$aircraftTimingState()
    {return "frameSeconds="+projectSeele$seconds+" correction="+railProgressSmoothingAdjustment+" display="+smoothedRailProgress+" extraPasses="+com.projectseele.client.AircraftRenderClockR21.duplicateMtrPasses;}
    @Override public int projectSeele$coordinateEpoch(){return projectSeele$coordinateEpoch;}

    @Override public double projectSeele$aircraftCorrectionBudget(long elapsedMillis,double metresPerSecond)
    {
        try
        {
            if(projectSeele$mode==null){projectSeele$mode=this.getClass().getDeclaredField("transportMode");projectSeele$mode.setAccessible(true);}
            if(!"AIRPLANE".equals(String.valueOf(projectSeele$mode.get(this))))return projectSeele$pendingBudget=Double.NaN;
            long frame=com.projectseele.client.AircraftRenderClockR21.frame;
            projectSeele$observation=elapsedMillis<=0||projectSeele$lastFrame==frame;projectSeele$speed=metresPerSecond;
            // Camera/geometry queries pass zero elapsed time. They must not
            // consume correction or change the render clock a second time.
            if(projectSeele$observation)return projectSeele$pendingBudget=0;
            projectSeele$lastFrame=frame;
            // Use exactly the time consumed by native simulation. Limit its
            // synchronization correction, not the legitimate travelled path.
            double seconds=elapsedMillis/1000D;
            projectSeele$seconds=seconds;
            return projectSeele$pendingBudget=com.projectseele.client.AircraftCorrectionR21.budget(railProgressSmoothingAdjustment,metresPerSecond,seconds);
        }
        catch(ReflectiveOperationException error){throw new IllegalStateException("MTR aircraft correction compatibility",error);}
    }
    @ModifyVariable(method="getSmoothedRailProgress(DD)D",at=@At("HEAD"),argsOnly=true,ordinal=1,remap=false)
    private double projectSeele$useBoundedCorrection(double original)
    {return Double.isFinite(projectSeele$pendingBudget)?projectSeele$pendingBudget:original;}
    @Inject(method="getSmoothedRailProgress(DD)D",at=@At("RETURN"),cancellable=true,remap=false)
    private void projectSeele$boundPresentedPosition(double target,double amount,CallbackInfoReturnable<Double> callback)
    {
        if(!Double.isFinite(projectSeele$pendingBudget))return;
        // A newly streamed vehicle has no prior displayed position. MTR's
        // default zero must not become kilometres of interpolation debt.
        // Likewise, a route restart resets its distance coordinate explicitly.
        if(!projectSeele$hasSample||target<projectSeele$lastRaw-256)
        {
            projectSeele$hasSample=true;projectSeele$lastRaw=target;projectSeele$coordinateEpoch++;
            railProgressSmoothingAdjustment=0;smoothedRailProgress=projectSeele$presented=target;
            callback.setReturnValue(smoothedRailProgress);return;
        }
        projectSeele$lastRaw=target;
        double visual=projectSeele$observation?projectSeele$presented:com.projectseele.client.AircraftCorrectionR21.forwardPresentation(projectSeele$presented,callback.getReturnValue(),projectSeele$speed);
        // A zero-time geometry query must not convert normal simulated travel
        // into correction debt. Only a real render advances this error state.
        if(!projectSeele$observation)railProgressSmoothingAdjustment=target-visual;
        smoothedRailProgress=projectSeele$presented=visual;callback.setReturnValue(visual);
    }

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
            return Math.max(vehicleLength,1_000_000.0D);
        }
        catch(ReflectiveOperationException error)
        {
            throw new IllegalStateException("MTR 4.0.5 aircraft interpolation compatibility",error);
        }
    }
}
