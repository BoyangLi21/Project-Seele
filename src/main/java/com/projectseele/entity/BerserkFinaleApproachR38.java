package com.projectseele.entity;

import com.projectseele.event.FirstBattleDirector;
import com.projectseele.physics.CombatBodyDynamics;
import com.projectseele.util.WeakIdentityMap;
import net.minecraft.world.entity.MoverType;
import net.minecraft.world.phys.Vec3;

/** A rejected scene start is a positioning problem, not an indefinite idle state. */
public final class BerserkFinaleApproachR38
{
    private static final class State {int since,next,blocked;Vec3 goal;}
    private static final WeakIdentityMap<EvaUnit01Entity,State> STATES=new WeakIdentityMap<>();
    public static void clear(EvaUnit01Entity eva){STATES.remove(eva);}
    public static boolean tick(EvaUnit01Entity eva,SachielEntity angel)
    {
        if(FirstBattleDirector.tryStart(angel,eva,false)){STATES.remove(eva);return true;}
        var s=STATES.computeIfAbsent(eva,e->{var value=new State();value.since=e.tickCount;return value;});
        if(CombatBodyDynamics.active(angel))return eva.tickCount-s.since<120;
        if(eva.tickCount>=s.next)
        {s.goal=FirstBattleDirector.stagingPosition(eva,angel,s.blocked>8?1:0);s.next=eva.tickCount+20;}
        // Continue combat when no safe scene footprint exists. The previous
        // implementation stopped every attack even when tryStart returned false.
        if(s.goal==null)return false;
        Vec3 delta=s.goal.subtract(eva.position()).multiply(1,0,1);
        if(delta.length()<.6)return false;
        Vec3 step=delta.normalize().scale(Math.min(.8,delta.length()));Vec3 before=eva.position();boolean grounded=eva.onGround();
        eva.move(MoverType.SELF,CombatSpacingR32.clip(eva,step));eva.setDeltaMovement(0,eva.getDeltaMovement().y,0);
        if(grounded&&eva.level().getBlockCollisions(eva,eva.getBoundingBox().deflate(.1).move(0,-.18,0)).iterator().hasNext())eva.setOnGround(true);
        s.blocked=eva.position().distanceToSqr(before)<.0009?s.blocked+1:0;
        return s.blocked<16;
    }
    private BerserkFinaleApproachR38(){}
}
