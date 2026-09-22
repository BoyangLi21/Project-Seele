package com.projectseele.world;

import com.projectseele.entity.EvaBodyPose;
import com.projectseele.entity.EvaPrototypeEntity;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import java.util.List;

/** Measured restrained airframe slices; a wide shoulder is not a deep chest. */
public final class UNCarrierClearanceR30
{
    public static boolean clear(EvaPrototypeEntity eva,Vec3 wanted)
    {
        var hulls=EvaBodyPose.carrierHulls(eva);
        if(hulls.isEmpty())return Entity.collideBoundingBox(eva,wanted,eva.getBoundingBox().deflate(.08),eva.level(),List.of()).subtract(wanted).lengthSqr()<1e-6;
        double yaw=Math.toRadians(180-eva.getYRot()),c=Math.cos(yaw),s=Math.sin(yaw);
        for(var local:hulls)
        {
            double x0=Double.POSITIVE_INFINITY,z0=x0,x1=Double.NEGATIVE_INFINITY,z1=x1;
            for(double x:new double[]{local.minX,local.maxX})for(double z:new double[]{local.minZ,local.maxZ})
            {double xx=c*x+s*z,zz=-s*x+c*z;x0=Math.min(x0,xx);x1=Math.max(x1,xx);z0=Math.min(z0,zz);z1=Math.max(z1,zz);}
            var box=new AABB(x0+eva.getX(),local.minY+eva.getY(),z0+eva.getZ(),x1+eva.getX(),local.maxY+eva.getY(),z1+eva.getZ()).deflate(.025);
            if(Entity.collideBoundingBox(eva,wanted,box,eva.level(),List.of()).subtract(wanted).lengthSqr()>1e-6)return false;
        }
        return true;
    }
    private UNCarrierClearanceR30() {}
}
