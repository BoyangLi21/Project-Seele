package com.projectseele.client.render;

import com.projectseele.entity.EvaUnit01Entity;
import java.util.Map;
import java.util.WeakHashMap;

final class EvaMechanicalResetR30
{
    private static final Map<EvaUnit01Entity,Integer> REVISIONS=new WeakHashMap<>();
    static void apply(EvaUnit01Entity eva)
    {
        int revision=eva.mechanicalRevisionR30();Integer previous=REVISIONS.put(eva,revision);
        if(previous==null||previous==revision)return;
        EvaMotionEngineV2.resetEntityR30(eva);EvaPoseTransition.resetEntityR30(eva);eva.resetClientMechanicalClocksR30();
    }
    private EvaMechanicalResetR30() {}
}
