package com.projectseele.entity;

import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;

/** Clip an authored step before two standing giant torsos pass through each other. */
public final class CombatSpacingR32
{
    public static Vec3 clip(LivingEntity actor,Vec3 motion)
    {
        if(motion.horizontalDistanceSqr()<1e-8)return motion;
        if(!actor.onGround())
        {
            var box=actor.getBoundingBox();var sole=new net.minecraft.world.phys.AABB(box.minX+.1,box.minY-.18,box.minZ+.1,box.maxX-.1,box.minY+.01,box.maxZ-.1);
            if(!actor.level().getBlockCollisions(actor,sole).iterator().hasNext())return motion;
        }
        Vec3 clipped=motion;
        for(var other:actor.level().getEntitiesOfClass(LivingEntity.class,actor.getBoundingBox().inflate(36,8,36),e->e!=actor&&e.isAlive()&&(e instanceof Angel||e instanceof EvaUnit01Entity)))
        {
            if(Math.abs(actor.getY()-other.getY())>12)continue;
            if(com.projectseele.physics.CombatBodyDynamics.active(other))continue;
            var reaction=CombatFeelR31.beat(other);if(reaction!=null&&(reaction.kind()==CombatFeelR31.DOWN||reaction.kind()==CombatFeelR31.THROWN))continue;
            if(other instanceof EvaUnit01Entity eva&&(eva.isNervLogisticsLocked()||eva.isPilotProne()||EvaShutdownR30.disabled(eva)))continue;
            Vec3 delta=actor.position().subtract(other.position()).multiply(1,0,1);double radius=Math.min(22,Math.max(20,(actor.getBbWidth()+other.getBbWidth())*.52));
            if(delta.lengthSqr()>1e-8)
            {
                var away=delta.normalize();double here=com.projectseele.physics.CombatBodyContacts.torsoFrontage(actor,away.scale(-1)),there=com.projectseele.physics.CombatBodyContacts.torsoFrontage(other,away);
                if(Double.isFinite(here)&&Double.isFinite(there))radius=Math.max(18,Math.min(34,here+there+.8));
            }
            double a=clipped.horizontalDistanceSqr(),b=2*delta.dot(clipped),c=delta.horizontalDistanceSqr()-radius*radius;
            if(a<1e-9)break;
            if(b>=0)continue;
            if(c<0)
            {
                Vec3 normal=delta.normalize();double inward=clipped.dot(normal);
                clipped=clipped.subtract(normal.scale(Math.min(0,inward)));continue;
            }
            double discriminant=b*b-4*a*c;if(discriminant<0)continue;
            double at=(-b-Math.sqrt(discriminant))/(2*a);
            if(at>=0&&at<1)
            {
                at=Math.max(0,at-.015);Vec3 advance=clipped.scale(at),remaining=clipped.scale(1-at);
                Vec3 normal=delta.add(advance).normalize();
                // Preserve the tangential step at contact. Cancelling the
                // complete vector also cancelled strafing, pinning both giants
                // together every time one tried to circle the other.
                clipped=advance.add(remaining.subtract(normal.scale(Math.min(0,remaining.dot(normal)))));
            }
        }
        return new Vec3(clipped.x,motion.y,clipped.z);
    }
    private CombatSpacingR32(){}
}
