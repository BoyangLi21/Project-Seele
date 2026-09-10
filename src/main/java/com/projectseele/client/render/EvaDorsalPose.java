package com.projectseele.client.render;

import com.projectseele.entity.EvaDorsalMechanism;
import com.projectseele.entity.EvaUnit01Entity;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import java.util.Set;

/** Mechanical travel owns the upper body only while the socket is in use. */
public final class EvaDorsalPose
{
    public static EvaMotionEngineV2.BoneWrites apply(EvaUnit01Entity eva, BakedGeoModel model)
    {
        float open=EvaDorsalMechanism.open(eva), bow=EvaDorsalMechanism.bow(eva);
        model.getBone("dorsal_leaf_l").ifPresent(b -> b.setRotY((float)Math.toRadians(-106*open)));
        model.getBone("dorsal_leaf_r").ifPresent(b -> b.setRotY((float)Math.toRadians(106*open)));
        if (bow < .0001F && open < .0001F) return EvaMotionEngineV2.BoneWrites.empty();
        for (String name : new String[]{"torso_lower","torso_upper","neck","head"})
        {
            model.getBone(name).ifPresent(b -> {
                float weight=Math.max(bow,open);
                b.setRotX(b.getRotX()*(1-weight)+(name.equals("head") ? -.72F*bow : 0));
                b.setRotY(b.getRotY()*(1-weight)); b.setRotZ(b.getRotZ()*(1-weight));
            });
        }
        return new EvaMotionEngineV2.BoneWrites(Set.of("torso_lower","torso_upper","neck","head"),Set.of(),"MOTION_ENGINE_LIVE_ACTION");
    }
    private EvaDorsalPose() {}
}
