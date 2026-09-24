package com.projectseele.world;

import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;

/** Short pressure discharge from fixed launch-bed vents, not a cloud following the EVA. */
public final class LaunchSteamEffects
{
    public static void emit(ServerLevel level,BlockPos bed,int age)
    {
        if(age<0||age>12||age%2!=0)return;
        for(int side:new int[]{-1,1})for(int end:new int[]{-1,1})
        {
            double x=bed.getX()+.5+side*11.8,y=bed.getY()+1.25,z=bed.getZ()+.5+end*9.2;
            int count=age==0?20:Math.max(3,11-age/2);
            GiantParticles.send(level,ParticleTypes.CLOUD,x,y,z,count,1.0,.35,1.0,age==0?.20:.12);
        }
    }
    private LaunchSteamEffects(){}
}
