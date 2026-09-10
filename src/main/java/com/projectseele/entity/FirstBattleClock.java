package com.projectseele.entity;

/** Monotonic presentation clock with at most two ticks of network extrapolation. */
final class FirstBattleClock
{
    private static final int[] CUES={372,432,460};
    private int age;
    private long confirmedAt,frameAt;
    private double display;

    FirstBattleClock(int age,long now)
    {
        this.age=age;display=age;confirmedAt=frameAt=now;
    }

    double sample(int confirmed,long now,boolean paused)
    {
        if(now==frameAt)return display;
        if(confirmed<age||Math.abs(confirmed-display)>8)
        {
            age=confirmed;display=confirmed;confirmedAt=frameAt=now;return display;
        }
        if(confirmed!=age){age=confirmed;confirmedAt=now;}
        double elapsed=Math.max(0,Math.min(.10,(now-frameAt)/1e9));frameAt=now;
        if(paused){confirmedAt=now;return display;}
        double prediction=age+Math.max(0,Math.min(2,(now-confirmedAt)/50_000_000D))-1;
        double rate=Math.max(.75,Math.min(1.25,1+(prediction-display)*.18));
        double ceiling=age+2;
        // Presentation may anticipate a missing packet, never a gameplay outcome.
        for(int cue:CUES)if(age<cue)ceiling=Math.min(ceiling,cue-.001);
        display=Math.max(display,Math.min(ceiling,display+elapsed*20*rate));
        return display;
    }
}
