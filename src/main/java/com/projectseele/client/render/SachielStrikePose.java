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
        model.getBone("torso_upper").ifPresent(b->{b.setRotY(b.getRotY()-.12F*w);b.setRotX(b.getRotX()-.07F*w);});
        var upper=model.getBone("arm_r").orElse(null);var lower=model.getBone("forearm_r").orElse(null);var hand=model.getBone("hand_r").orElse(null);if(upper==null||lower==null||hand==null)return;
        var rotation=new Quaternionf().rotationTo(new Vector3f(0,0,-1),frame.direction().toVector3f());
        EvaRigTransforms.solveGenericArm(upper,lower,hand,frame.hand().toVector3f(),rotation,new Vector3f(-1,-.5F,.2F),SachielStrike.root(actor,partial));
        model.getBone("head").ifPresent(b->b.setRotX(b.getRotX()-.04F*w));
    }
    private SachielStrikePose() {}
}
