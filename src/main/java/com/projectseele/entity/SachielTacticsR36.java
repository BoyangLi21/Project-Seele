package com.projectseele.entity;

import com.projectseele.physics.CombatBodyDynamics;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.MoverType;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.phys.Vec3;
import java.util.EnumSet;

/** Approach, commit, recover space. Decisions read bodies, never player inputs. */
public final class SachielTacticsR36 extends Goal
{
    private final SachielEntity actor;
    private Vec3 velocity=Vec3.ZERO;
    private boolean wasStriking;
    private int regroup,choice,blocked;
    public SachielTacticsR36(SachielEntity actor){this.actor=actor;setFlags(EnumSet.of(Flag.MOVE,Flag.LOOK));}
    @Override public boolean canUse(){return SachielGameplayMotionR32.phrases()&&!actor.isFirstBattleActive()&&!actor.isSelfDestructing()&&actor.getTarget()!=null&&actor.getTarget().isAlive();}
    @Override public boolean requiresUpdateEveryTick(){return true;}
    @Override public void stop(){velocity=Vec3.ZERO;SachielTacticsR34.recordMotion(actor,Vec3.ZERO);actor.getNavigation().stop();}
    @Override public void tick()
    {
        actor.getNavigation().stop();LivingEntity target=actor.getTarget();if(target==null)return;
        if(actor.isStrikeActive()) {wasStriking=true;stop();return;}
        if(wasStriking){wasStriking=false;regroup=actor.lastStrikeConnectedR36()?9:16;}
        if(CombatFeelR31.restrained(actor)||CombatFeelR31.hitPaused(actor)||EvaCombatR31.holds(actor)){stop();return;}
        var delta=target.position().subtract(actor.position()).multiply(1,0,1);double range=delta.length();if(range<.01)return;
        var forward=delta.normalize();var lateral=new Vec3(forward.z,0,-forward.x);
        float yaw=(float)Math.toDegrees(Math.atan2(-forward.x,forward.z));actor.setYRot(Mth.approachDegrees(actor.getYRot(),yaw,4.5F));actor.yHeadRot=actor.yBodyRot=actor.getYRot();
        boolean facing=Math.abs(Mth.wrapDegrees(yaw-actor.getYRot()))<16,low=CombatBodyDynamics.active(target)||target instanceof EvaUnit01Entity eva&&eva.isPilotProne();
        if(regroup<=0&&facing&&actor.strikeReadyR34()&&actor.hasLineOfSight(target)&&range<42)
        {
            // Long bone-lance attacks claim space. Close pressure uses a palm
            // drive, with a visible recovery opening before another commitment.
            int mode=low&&range<26?SachielStrike.STOMP:range>32?SachielStrike.PILE:range<22?SachielStrike.SHOVE:
                    switch(choice%4){case 0->SachielStrike.HOOK;case 1->SachielStrike.PILE;case 2->SachielStrike.OVERHEAD;default->SachielStrike.JAB;};
            if(actor.beginStrike(target,mode)){choice++;wasStriking=true;stop();return;}
        }
        Vec3 wanted;
        if(regroup>0)
        {
            regroup--;
            wanted=range<32?forward.scale(-.82).add(lateral.scale((choice%2==0?1:-1)*.18)):Vec3.ZERO;
        }
        else wanted=range>39?forward.scale(1.1):range>30?forward.scale(.55):range<22?forward.scale(-.45):Vec3.ZERO;
        // Failed movement invokes navigation around a real obstacle, rather
        // than continually shuffling into its collision box.
        if(blocked>14&&range>35){actor.getNavigation().moveTo(target,1);blocked=0;}
        velocity=velocity.lerp(wanted,.20);Vec3 before=actor.position();boolean ground=actor.onGround();actor.move(MoverType.SELF,CombatSpacingR32.clip(actor,velocity));
        actor.setDeltaMovement(0,actor.getDeltaMovement().y,0);
        if(ground&&actor.level().getBlockCollisions(actor,actor.getBoundingBox().deflate(.1).move(0,-.18,0)).iterator().hasNext())actor.setOnGround(true);
        var moved=actor.position().subtract(before);SachielTacticsR34.recordMotion(actor,moved);
        if(moved.horizontalDistance()<.03&&wanted.lengthSqr()>.25)blocked++;else blocked=0;
    }
}
