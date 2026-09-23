package com.projectseele.entity;

import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;

/** Clip an authored step before two standing giant torsos pass through each other. */
public final class CombatSpacingR32
{
    public static Vec3 clip(LivingEntity actor,Vec3 motion)
    {
        if(motion.horizontalDistanceSqr()<1e-8||!actor.onGround())return motion;
        double fraction=1;
        for(var other:actor.level().getEntitiesOfClass(LivingEntity.class,actor.getBoundingBox().inflate(36,8,36),e->e!=actor&&e.isAlive()&&(e instanceof Angel||e instanceof EvaUnit01Entity)))
        {
            if(Math.abs(actor.getY()-other.getY())>12)continue;
            var reaction=CombatFeelR31.beat(other);if(reaction!=null&&(reaction.kind()==CombatFeelR31.DOWN||reaction.kind()==CombatFeelR31.THROWN))continue;
            if(other instanceof EvaUnit01Entity eva&&(eva.isNervLogisticsLocked()||eva.isPilotProne()||EvaShutdownR30.disabled(eva)))continue;
            Vec3 delta=actor.position().subtract(other.position()).multiply(1,0,1);double radius=Math.min(22,Math.max(20,(actor.getBbWidth()+other.getBbWidth())*.52));
            double a=motion.horizontalDistanceSqr(),b=2*delta.dot(motion),c=delta.horizontalDistanceSqr()-radius*radius;
            if(b>=0)continue;
            if(c<0){fraction=0;break;}
            double discriminant=b*b-4*a*c;if(discriminant<0)continue;
            double at=(-b-Math.sqrt(discriminant))/(2*a);if(at>=0&&at<1)fraction=Math.min(fraction,Math.max(0,at-.015));
        }
        return new Vec3(motion.x*fraction,motion.y,motion.z*fraction);
    }
    private CombatSpacingR32(){}
}
