package com.projectseele.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Coerce;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import java.util.List;

/** A repeating MTR path ends with an unbounded placeholder at the world origin. */
@Pseudo
@Mixin(targets="org.mtr.core.data.Vehicle",remap=false)
public abstract class MtrRouteEndpointMixin
{
    @Unique private Object projectSeele$endpointPathIdentity;
    @Unique private Object projectSeele$lastRealPath;
    @Unique private double projectSeele$endpointDistance;

    @Unique private static Object projectSeele$call(Object object,String method) throws ReflectiveOperationException
    {
        return object.getClass().getMethod(method).invoke(object);
    }
    @Unique private static double projectSeele$number(Object object,String method) throws ReflectiveOperationException
    {
        return ((Number)projectSeele$call(object,method)).doubleValue();
    }
    @Unique private static boolean projectSeele$origin(Object p) throws ReflectiveOperationException
    {
        return projectSeele$number(p,"getX")==0&&projectSeele$number(p,"getY")==0&&projectSeele$number(p,"getZ")==0;
    }
    @Inject(method="getPosition(DLorg/mtr/libraries/it/unimi/dsi/fastutil/doubles/DoubleArrayList;)Lorg/mtr/core/tool/Vector;",at=@At("HEAD"),cancellable=true,remap=false)
    private void projectSeele$sampleRealTerminal(double distance,@Coerce Object bogieHeights,CallbackInfoReturnable<Object> callback)
    {
        try
        {
            Object self=this;Object extra=self.getClass().getField("vehicleExtraData").get(self);
            if(extra==null)return;
            Object identity=extra.getClass().getField("immutablePath").get(extra);
            if(identity!=projectSeele$endpointPathIdentity)
            {
                projectSeele$endpointPathIdentity=identity;projectSeele$lastRealPath=null;
                List<?> path=(List<?>)identity;
                if(path.size()<2)return;
                Object sentinel=path.get(path.size()-1),last=path.get(path.size()-2);
                if(projectSeele$number(sentinel,"getEndDistance")!=Double.MAX_VALUE
                        ||!projectSeele$origin(projectSeele$call(sentinel,"getOrderedPosition1"))
                        ||!projectSeele$origin(projectSeele$call(sentinel,"getOrderedPosition2"))
                        ||projectSeele$number(last,"getDwellTime")<=0)return;
                projectSeele$lastRealPath=last;projectSeele$endpointDistance=projectSeele$number(last,"getEndDistance");
            }
            if(projectSeele$lastRealPath==null||distance<projectSeele$endpointDistance
                    ||distance>projectSeele$endpointDistance+projectSeele$number(extra,"getTotalVehicleLength")+2
                    ||!(Boolean)projectSeele$call(self,"getIsOnRoute"))return;
            // Native simulation still owns progress, braking, doors and repetition.
            // Only the read at the exact end (or a short smoothing overshoot) is clamped.
            Object last=projectSeele$lastRealPath;
            callback.setReturnValue(last.getClass().getMethod("getPosition",double.class)
                    .invoke(last,projectSeele$number(last,"getRailLength")));
        }
        catch(ReflectiveOperationException exception)
        {
            throw new IllegalStateException("MTR finite route endpoint compatibility",exception);
        }
    }
}
