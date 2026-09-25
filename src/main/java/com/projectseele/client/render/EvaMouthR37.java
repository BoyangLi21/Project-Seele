package com.projectseele.client.render;

import com.projectseele.entity.*;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import java.util.*;

final class EvaMouthR37
{
    static EvaMotionEngineV2.BoneWrites apply(EvaUnit01Entity eva,BakedGeoModel model,float partial)
    {
        if(eva.getUnitVariant()!=EvaUnit01Entity.UNIT_01||eva.isExperimentalUnit()||model.getBone("r37_jaw").isEmpty())return EvaMotionEngineV2.BoneWrites.empty();
        float open=EvaBerserkMotionR34.mouth(eva,partial);
        model.getBone("r37_jaw").ifPresent(b->{b.setRotX(-(float)Math.toRadians(31)*open);b.setPosZ(-.8F*open);b.setHidden(false);});
        for(String name:List.of("r37_red_upper","r37_red_lower","r37_lining"))
            model.getBone(name).ifPresent(b->b.setHidden(open<.025F));
        return new EvaMotionEngineV2.BoneWrites(Set.of("r37_jaw"),Set.of("r37_jaw"),"MOTION_ENGINE_LIVE_ACTION");
    }
    private EvaMouthR37(){}
}
