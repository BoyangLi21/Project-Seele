package com.projectseele.client.render;

import com.projectseele.entity.*;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.BakedGeoModel;

public final class SachielStrikePose
{
    public static void apply(SachielEntity actor,BakedGeoModel model,float partial)
    {
        if(!actor.isStrikeActive()||actor.isFirstBattleActive())return;
        var frame=SachielStrike.sample(actor,partial);float w=frame.weight();
        float age=actor.strikeAge(partial),twist=CombatMotionR29.twist(age),drive=CombatMotionR29.drive(age)*(1-CombatMotionR29.release(age));
        model.getBone("torso_lower").ifPresent(b->{b.setRotY(b.getRotY()+twist*.32F);b.setRotX(b.getRotX()-.035F*drive);});
        model.getBone("torso_upper").ifPresent(b->{b.setRotY(b.getRotY()+twist*.68F);b.setRotX(b.getRotX()+.05F*w-.12F*drive);});
        var upper=model.getBone("arm_r").orElse(null);var lower=model.getBone("forearm_r").orElse(null);var hand=model.getBone("hand_r").orElse(null);if(upper==null||lower==null||hand==null)return;
        var bones=new software.bernie.geckolib.cache.object.GeoBone[]{upper,lower,hand};
        var before=new float[3][6];
        for(int i=0;i<3;i++){var b=bones[i];before[i]=new float[]{b.getRotX(),b.getRotY(),b.getRotZ(),b.getPosX(),b.getPosY(),b.getPosZ()};}
        var rotation=new Quaternionf().rotationTo(new Vector3f(0,0,-1),frame.direction().toVector3f());
        double solvedError=EvaRigTransforms.solveGenericArm(upper,lower,hand,frame.hand().toVector3f(),rotation,new Vector3f(-1,-.5F,.2F),SachielStrike.root(actor,partial));
        // Full IK only during contact. Blend back to the live walk pose, not a hard-coded idle.
        float blend=CombatMotionR29.weight(age);
        for(int i=0;i<3;i++)
        {
            var b=bones[i];var a=before[i];var from=new Quaternionf().rotationZYX(a[2],a[1],a[0]);
            var to=new Quaternionf().rotationZYX(b.getRotZ(),b.getRotY(),b.getRotX());
            var r=EvaMotionEngineV2.motionQuaternionToAuthoredEuler(from.slerp(to,blend));
            b.setRotX(r.x);b.setRotY(r.y);b.setRotZ(r.z);
            b.setPosX(a[3]+(b.getPosX()-a[3])*blend);b.setPosY(a[4]+(b.getPosY()-a[4])*blend);b.setPosZ(a[5]+(b.getPosZ()-a[5])*blend);
        }
        model.getBone("head").ifPresent(b->b.setRotX(b.getRotX()-.04F*w));
        if(com.projectseele.visual.CombatR29Review.ENABLED&&age>=16&&age<=27)
        {
            double error=EvaRigTransforms.point(hand,EvaRigTransforms.pivot(hand),SachielStrike.root(actor,partial)).distance(frame.hand().toVector3f());
            if(error>com.projectseele.visual.CombatR29Review.maxHandError+.1)
                com.projectseele.ProjectSeele.LOGGER.info("R29 HAND ERROR age={} solved={} after={} target={} shoulder={} pivotUpper={} pivotLower={} pivotHand={} actual={}",age,solvedError,error,frame.hand(),EvaRigTransforms.point(upper,EvaRigTransforms.pivot(upper),SachielStrike.root(actor,partial)),EvaRigTransforms.pivot(upper),EvaRigTransforms.pivot(lower),EvaRigTransforms.pivot(hand),EvaRigTransforms.point(hand,EvaRigTransforms.pivot(hand),SachielStrike.root(actor,partial)));
            com.projectseele.visual.CombatR29Review.maxHandError=Math.max(com.projectseele.visual.CombatR29Review.maxHandError,error);com.projectseele.visual.CombatR29Review.handSamples++;
        }
    }
    private SachielStrikePose() {}
}
