package com.projectseele.world;

import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;

/** Level cage and launch pads connected by a rounded, inclined transfer guide. */
public final class CarrierGuidePath
{
    public static double height(Vec3 from,Vec3 to,double progress)
    {
        double dy=to.y-from.y,dz=to.z-from.z;
        if(Math.abs(dy)<4||Math.abs(dz)<64)return Mth.lerp(progress,from.y,to.y);
        Vec3 low=from.y<to.y?from:to,high=from.y<to.y?to:from;
        double sign=Math.signum(high.z-low.z);
        double start=low.z+sign*28,end=high.z-sign*16;
        double length=(end-start)*sign;
        double z=Mth.lerp(progress,from.z,to.z),d=Mth.clamp((z-start)*sign,0,length);
        double blend=Math.min(6,length*.15),effective=length-blend;
        double rise=d<blend?rounded(d,blend):d>length-blend?effective-rounded(length-d,blend):d-blend*.5;
        return Mth.lerp(rise/effective,low.y,high.y);
    }
    private static double rounded(double distance,double blend)
    {
        return distance*.5-blend/(2*Math.PI)*Math.sin(Math.PI*distance/blend);
    }
    private CarrierGuidePath(){}
}
