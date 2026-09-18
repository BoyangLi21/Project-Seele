package com.projectseele.client;

/** Bounded correction of packet error; the native simulation retains travel. */
public final class AircraftCorrectionR21
{
    public static double forwardPresentation(double previous,double candidate,double speed)
    {return Math.abs(speed)>.001?Math.max(previous,candidate):candidate;}
    public static double budget(double error,double metresPerSecond,double seconds)
    {
        if(seconds<=0||!Double.isFinite(error)||!Double.isFinite(seconds))return 0;
        double speed=Math.abs(metresPerSecond);
        double rate=error<0&&speed>0?speed*.85:Math.max(3,speed*.85);
        return Math.min(8,Math.min(Math.abs(error)*-Math.expm1(-seconds/.25),rate*seconds));
    }
    private AircraftCorrectionR21(){}
}
