package com.projectseele.entity;

public final class CombatMotionR29Test
{
    private static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);}
    public static void main(String[] args)
    {
        for(double boundary:new double[]{0,3,7,17,24})
        {
            double before=CombatMotionR29.recoil(boundary-.0001),after=CombatMotionR29.recoil(boundary+.0001);
            check(Math.abs(after-before)<.00001,"recoil jump at "+boundary);
            check(Math.abs(after-before)/.0002<.001,"recoil velocity discontinuity at "+boundary);
        }
        check(CombatMotionR29.recoil(3)==1,"impact peak");
        check(Math.abs(CombatMotionR29.recoil(17)+.08)<1e-10,"bounded recovery overshoot");
        for(float t=0;t<=42;t+=.01F)
        {
            check(CombatMotionR29.weight(t)>=0&&CombatMotionR29.weight(t)<=1,"IK blend bounds");
            if(t>=16&&t<=27)check(CombatMotionR29.weight(t)>.9999,"full hand contact during damage window");
        }
        check(CombatMotionR29.weight(0)==0&&CombatMotionR29.weight(42)==0,"no entry/exit pose snap");
        System.out.println("R29 combat: continuous recoil, bounded recovery, exact contact blend passed");
    }
}
