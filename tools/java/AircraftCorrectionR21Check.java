import com.projectseele.client.AircraftCorrectionR21;

/** Regression scenarios from a 180 m late correction followed by taxi braking. */
public final class AircraftCorrectionR21Check
{
    private static void require(boolean p,String why){if(!p)throw new AssertionError(why);}
    public static void main(String[] args)
    {
        double error=180;
        for(int frame=0;frame<100;frame++)error-=AircraftCorrectionR21.budget(error,83.333,.05);
        require(error<.05,"Cruise correction must converge before slow taxi, not linger for minutes: "+error);
        for(double speed:new double[]{0,.2,1.1,12.5,83.333})for(double dt:new double[]{.016,.05,.15,.7,2.55})
        {
            double correction=AircraftCorrectionR21.budget(180,speed,dt);
            require(correction<=8&&correction>=0,"Per-frame correction bound");
            require(speed*dt+correction<=Math.max(15,speed*dt*2+5),"Passenger continuity during braking/render stalls");
            double ahead=AircraftCorrectionR21.budget(-180,speed,dt);
            if(speed>0)require(speed*dt-ahead>=0,"A moving aircraft must not rewind");
        }
        require(AircraftCorrectionR21.budget(180,0,0)==0,"Observation must not advance smoothing");
        double raw=1000,shown=1000,offset=0;
        for(int frame=0;frame<1500;frame++)
        {
            double dt=frame%41==0?.7:frame%13==0?.2:.06;
            raw+=83.333*dt;
            double amount=AircraftCorrectionR21.budget(offset,83.333,dt);
            offset-=Math.copySign(amount,offset);
            shown=AircraftCorrectionR21.forwardPresentation(shown,raw-offset,83.333);
            offset=raw-shown;
            require(Math.abs(raw-shown)<.001,"Native travel must not accumulate presentation debt at varying frame rates");
        }
        offset=180;
        for(int frame=0;frame<300;frame++)
        {
            raw+=83.333*.05;
            offset-=Math.copySign(AircraftCorrectionR21.budget(offset,83.333,.05),offset);
            shown=AircraftCorrectionR21.forwardPresentation(shown,raw-offset,83.333);
            offset=raw-shown;
        }
        require(Math.abs(offset)<.01,"Packet error converges independently of native travel");
        require(AircraftCorrectionR21.forwardPresentation(1000,995,83.333)==1000,"Moving prediction never rewinds after a server acknowledgement");
        System.out.println("R21 aircraft correction regression PASS: cruise, taxi, stopped, stalls, duplicate read, negative correction");
    }
}
