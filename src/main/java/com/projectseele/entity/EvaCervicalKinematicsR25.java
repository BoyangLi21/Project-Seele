package com.projectseele.entity;

import net.minecraft.util.Mth;

/** The low-stance cervical hinge sits behind the jaw, beside the sealed nape. */
public final class EvaCervicalKinematicsR25
{
    public static float modelOffset(EvaUnit01Entity eva,float partial)
    {
        // The UN airframes have a lower, independently measured dorsal port.
        // The original TV rig's high nape plate must not rebase those helmets.
        if(eva instanceof EvaPrototypeEntity||eva.isNervLogisticsLocked()||eva.isFirstBattleActive())return 0;
        float p=Mth.clamp(eva.rifleProneBlend(partial),0,1);
        return 16F*p*p*p*(10+p*(-15+6*p));
    }
    private EvaCervicalKinematicsR25() {}
}
