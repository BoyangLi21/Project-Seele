package com.projectseele.entity;

import com.projectseele.physics.CombatBodyDynamics;
import net.minecraft.util.Mth;

/** The displayed enemy, its contact sweep and its fall share one body pose. */
public final class SachielBodyPoseR35
{
    public static EvaBodyPose.Sample sample(SachielEntity actor,float partial)
    {
        var pose=SachielGameplayMotionR32.locomotion(actor,partial);
        if(actor.isStrikeActive())
        {
            float age=actor.strikeAge(partial),blend=Math.min(1,age/4)*(1-Mth.clamp((age-SachielStrike.duration(actor.strikeMode())+6)/6,0,1));
            var strike=SachielGameplayMotionR32.pose(actor,age);
            for(String n:pose.rig.keySet()){pose.rotations.get(n).slerp(strike.rotations.get(n),blend);pose.positions.get(n).lerp(strike.positions.get(n),blend);}pose.dirty();
        }
        if(EvaCombatR31.holds(actor))
        {
            float held=AngelGrappleSurfaceR31.heldWeight(actor,partial);
            pose.rotations.get("torso_upper").rotateX(-.18F*held);pose.rotations.get("head").rotateX(-.12F*held);
            for(String s:new String[]{"l","r"})
            {pose.rotations.get("arm_"+s).rotateX(.65F*held).rotateZ((s.equals("l")?.35F:-.35F)*held);pose.rotations.get("forearm_"+s).rotateX(2.0F*held);}
        }
        var hit=EvaImpactResponse.sample(actor,partial);
        pose.rotations.get("torso_lower").rotateX(hit.pitch()*.3F).rotateZ(hit.roll()*.3F);
        pose.rotations.get("torso_upper").rotateX(hit.pitch()*.7F).rotateZ(hit.roll()*.7F);
        pose.rotations.get("head").rotateX(hit.head());pose.dirty();CombatBodyDynamics.normalize(actor,pose);return pose;
    }
    private SachielBodyPoseR35(){}
}
