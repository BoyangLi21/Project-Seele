package com.projectseele.entity;

/** Contact accents with zero velocity at phase boundaries; no free oscillation. */
public final class CombatMotionR29
{
    public static double ease(double t)
    {
        t=Math.max(0,Math.min(1,t));return t*t*t*(t*(t*6-15)+10);
    }
    public static double recoil(double ticks)
    {
        if(ticks<0||ticks>=24)return 0;
        if(ticks<3)return ease(ticks/3);
        if(ticks<7)return 1-.24*ease((ticks-3)/4);
        if(ticks<17)return .76-.84*ease((ticks-7)/10);
        return -.08*(1-ease((ticks-17)/7));
    }
    public static double brace(double ticks)
    {return ease(ticks/5)*(1-ease((ticks-7)/17));}
    public static float chamber(float age){return (float)ease(age/12);}
    public static float drive(float age){return (float)ease((age-12)/7);}
    public static float release(float age){return (float)ease((age-27)/15);}
    public static float weight(float age){return chamber(age)*(1-release(age));}
    public static float twist(float age){return (.18F*chamber(age)-.34F*drive(age))*(1-release(age));}
    private CombatMotionR29() {}
}
