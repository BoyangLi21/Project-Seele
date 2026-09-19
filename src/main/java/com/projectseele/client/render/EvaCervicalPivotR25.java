package com.projectseele.client.render;

import com.projectseele.entity.EvaCervicalKinematicsR25;
import com.projectseele.entity.EvaUnit01Entity;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.*;
import java.util.Map;
import java.util.WeakHashMap;

/** Rebase the hinge without changing bind vertices or accumulating a per-frame offset. */
final class EvaCervicalPivotR25
{
    private static final Map<GeoBone,Vector3f> BASE=new WeakHashMap<>();
    static void apply(EvaUnit01Entity eva,BakedGeoModel model,float partial)
    {
        model.getBone("head").ifPresent(head->{
            var base=BASE.computeIfAbsent(head,b->new Vector3f(b.getPivotX(),b.getPivotY(),b.getPivotZ()));
            float offset=EvaCervicalKinematicsR25.modelOffset(eva,partial);
            head.setPivotX(base.x);head.setPivotY(base.y+offset);head.setPivotZ(base.z+offset);
        });
    }
    private EvaCervicalPivotR25() {}
}
