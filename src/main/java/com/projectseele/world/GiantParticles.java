package com.projectseele.world;

import net.minecraft.core.particles.ParticleOptions;
import net.minecraft.server.level.ServerLevel;

/** A giant's cockpit is already beyond vanilla's 32-block particle radius. */
public final class GiantParticles
{
    public static <T extends ParticleOptions> void send(ServerLevel level,T type,double x,double y,double z,int count,double dx,double dy,double dz,double speed)
    {
        for(var player:level.players())if(player.distanceToSqr(x,y,z)<=192*192)
            level.sendParticles(player,type,true,x,y,z,count,dx,dy,dz,speed);
    }
    private GiantParticles(){}
}
