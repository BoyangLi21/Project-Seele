package com.projectseele.client.render;

import com.projectseele.entity.*;
import software.bernie.geckolib.cache.object.BakedGeoModel;

final class ShamshelWhipPose
{
    static void apply(ShamshelEntity actor,BakedGeoModel model,float partial)
    {
        float age=actor.isSweeping()?actor.sweepAge(partial):-1;
        model.getBone("body").ifPresent(b->b.setRotX(ShamshelWhipMotion.bodyPitch(age)));
        for(int side:new int[]{-1,1})for(int segment=0;segment<4;segment++)
        {
            var r=ShamshelWhipMotion.rotation(side,segment,actor.sweepSide(),age,actor.tickCount+partial);
            model.getBone("whip_"+(side>0?"l":"r")+"_"+segment).ifPresent(b->{b.setRotX(r.x);b.setRotY(r.y);b.setRotZ(r.z);});
        }
        for(int i=0;i<4;i++)
        {
            final int segment=i;
            model.getBone("tail_"+i).ifPresent(b->b.setRotX((float)Math.sin((actor.tickCount+partial)*.038-segment*.6)*.025F));
        }
        if(com.projectseele.visual.TvCampaignR24Review.ENABLED&&actor.isSweeping())
        {
            var root=new org.joml.Matrix4f().translation(actor.getPosition(partial).toVector3f()).rotateY((float)Math.toRadians(180-actor.sweepYaw())).scale(5);
            var expected=ShamshelWhipMotion.points(actor,age,partial);int side=actor.sweepSide();
            for(int i=0;i<4;i++)
            {
                var bone=model.getBone("whip_"+(side>0?"l":"r")+"_"+i).orElseThrow();
                float error=EvaRigTransforms.point(bone,EvaRigTransforms.pivot(bone),root).distance(expected.get(i).toVector3f());
                com.projectseele.visual.TvCampaignR24Review.maxWhipRigError=Math.max(com.projectseele.visual.TvCampaignR24Review.maxWhipRigError,error);
                com.projectseele.visual.TvCampaignR24Review.whipRigSamples++;
            }
        }
    }
    private ShamshelWhipPose(){}
}
