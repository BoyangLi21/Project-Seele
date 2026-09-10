package com.projectseele.entity;

import java.util.ArrayList;
import java.util.Comparator;

/** Behavioral checks for network jitter, pause, cue gates and saved-scene clocks. */
public final class FirstBattleClockProbe
{
    private static int checks;
    private static void require(boolean result,String name)
    {
        if(!result)throw new AssertionError(name);checks++;System.out.println("PASS "+name);
    }
    public static void main(String[] args)
    {
        record Packet(long at,int age) {}
        var packets=new ArrayList<Packet>();
        for(int age=1;age<=300;age++)packets.add(new Packet(age*50_000_000L+(age%7==0?95_000_000L:age%5==0?40_000_000L:0),age));
        packets.sort(Comparator.comparingLong(Packet::at));
        var clock=new FirstBattleClock(0,0);int cursor=0,confirmed=0,oldAge=0,newHolds=0,oldHolds=0;long oldAt=0;double last=0,oldFrom=0,oldTo=0,oldLast=0,maxLead=0,maxStep=0;
        for(int frame=1;frame<=890;frame++)
        {
            long now=Math.round(frame*1e9/60);
            while(cursor<packets.size()&&packets.get(cursor).at<=now){confirmed=Math.max(confirmed,packets.get(cursor).age);cursor++;}
            double value=clock.sample(confirmed,now,false);if(value+1e-9<last)throw new AssertionError("clock moved backwards");
            maxLead=Math.max(maxLead,value-confirmed);maxStep=Math.max(maxStep,value-last);if(value-last<1e-7)newHolds++;
            double oldCurrent=oldFrom+(oldTo-oldFrom)*Math.min(1,(now-oldAt)/50_000_000D);
            if(confirmed!=oldAge){oldFrom=oldCurrent;oldTo=confirmed;oldAge=confirmed;oldAt=now;}
            double oldValue=oldFrom+(oldTo-oldFrom)*Math.min(1,(now-oldAt)/50_000_000D);if(oldValue-oldLast<1e-7)oldHolds++;oldLast=oldValue;last=value;
            if(clock.sample(confirmed,now,false)!=value)throw new AssertionError("two actors received different frame times");
        }
        require(maxLead<=2.000001,"extrapolation bounded to two ticks");require(maxStep<.5,"jitter correction has no large frame jump");require(newHolds<oldHolds,"fewer packet-gap pauses: "+newHolds+" versus "+oldHolds);require(true,"monotonic and identical time for every actor in a frame");
        clock=new FirstBattleClock(100,0);double held=clock.sample(100,16_000_000,true);
        for(int i=2;i<90;i++)if(clock.sample(100,i*16_000_000L,true)!=held)throw new AssertionError("paused clock advanced");
        require(true,"integrated-server pause holds the presentation");require(clock.sample(1,2_000_000_000L,false)==1,"new encounter resets an existing actor clock");
        clock=new FirstBattleClock(140,0);require(clock.sample(140,0,false)==140,"saved encounter resumes at its saved age");
        require(clock.sample(140,1_000_000_000L,false)<=142,"long packet silence cannot run away");
        for(int cue:new int[]{372,432,460})
        {
            clock=new FirstBattleClock(cue-1,0);double previous=cue-1;
            for(int i=1;i<=60;i++)previous=clock.sample(cue-1,i*16_666_667L,false);
            require(previous<cue,"cue "+cue+" waits for server confirmation");
            require(clock.sample(cue,1_100_000_000L,false)>=previous,"cue "+cue+" releases without reversing");
        }
        System.out.println("PASSED "+checks+" checks; jitter holds="+newHolds+" old="+oldHolds+" maxLead="+maxLead+" maxStep="+maxStep);
    }
}
