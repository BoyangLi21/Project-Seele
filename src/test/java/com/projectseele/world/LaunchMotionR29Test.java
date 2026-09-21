package com.projectseele.world;

/** Behavioural rail-motion contract, independent of Minecraft's runtime. */
public final class LaunchMotionR29Test
{
    private static void require(boolean value,String why){if(!value)throw new AssertionError(why);}
    private static double speed(double t){double h=1e-6;return (LaunchMotionR29.progress(t+h)-LaunchMotionR29.progress(t-h))/(2*h);}
    public static void main(String[] ignored)
    {
        require(LaunchMotionR29.progress(-1)==0&&LaunchMotionR29.progress(2)==1,"bounded endpoints");
        double previous=0,early=0,middle=0;
        for(int i=1;i<=10000;i++)
        {
            double t=i/10000D,p=LaunchMotionR29.progress(t);require(p>=previous&&p<=1,"monotonic ascent");previous=p;
            if(t<.12)early=Math.max(early,speed(t));if(t>.3&&t<.8)middle=Math.max(middle,speed(t));
        }
        require(LaunchMotionR29.progress(12/164D)>.13,"perceptible initial catapult");
        require(early>middle*1.6,"climb settles after initial impulse");
        require(LaunchMotionR29.progress(.2)<.35,"initial kick does not skip the shaft");
        for(double knot:new double[]{.073,.2,.9})require(Math.abs(speed(knot-1e-5)-speed(knot+1e-5))<.01,"continuous velocity");
        require(speed(.000001)<.01&&speed(.999999)<.01,"resting entry and arrival");
        System.out.println("R29 launch motion PASS: strong first segment, monotonic climb, continuous velocity and settled arrival");
    }
}
