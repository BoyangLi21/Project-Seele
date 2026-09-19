import java.lang.instrument.Instrumentation;
import java.util.*;
public final class R24CampaignStateAgent
{
    public static void agentmain(String input,Instrumentation instrumentation)throws Exception
    {
        if(!"r24-campaign".equals(System.getProperty("projectseele.regionalBuild")))throw new IllegalStateException("Wrong JVM");
        Map<String,Class<?>> types=new HashMap<>();for(var c:instrumentation.getAllLoadedClasses())types.put(c.getName(),c);
        Object mc=types.get("net.minecraft.client.Minecraft").getMethod("getInstance").invoke(null);
        Runnable read=()->{
            try
            {
                var review=types.get("com.projectseele.visual.TvCampaignR24Review");var field=review.getDeclaredField("eva");field.setAccessible(true);Object server=field.get(null);
                Object level=mc.getClass().getField("level").get(mc);int id=(Integer)server.getClass().getMethod("getId").invoke(server);
                Object client=level.getClass().getMethod("getEntity",int.class).invoke(level,id);
                for(Object e:new Object[]{server,client})
                {
                    Object signal=e.getClass().getMethod("firstBattleSignals").invoke(e);
                    Object clock=null;for(var m:signal.getClass().getMethods())if(m.getName().equals("age")&&m.getParameterCount()==1)clock=m.invoke(signal,e);
                    System.out.println("R24 DEEP entity="+e+" tickCount="+e.getClass().getField("tickCount").get(e)+" age="+clock+" noPhysics="+e.getClass().getField("noPhysics").get(e));
                }
                Object player=mc.getClass().getField("player").get(mc);
                System.out.println("R24 DEEP playerTicks="+player.getClass().getField("tickCount").get(player)+" paused="+mc.getClass().getMethod("isPaused").invoke(mc));
                Object camera=mc.getClass().getField("gameRenderer").get(mc);camera=camera.getClass().getMethod("getMainCamera").invoke(camera);
                System.out.println("R24 DEEP camera="+camera.getClass().getMethod("getPosition").invoke(camera));
            }
            catch(Exception e){e.printStackTrace();}
        };
        mc.getClass().getMethod("execute",Runnable.class).invoke(mc,read);
    }
}
