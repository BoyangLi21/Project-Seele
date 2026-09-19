import java.lang.instrument.Instrumentation;
import java.nio.file.Path;
import java.util.*;

/** Read-only diagnostics, or normal timed teardown, for the isolated review JVM. */
public final class R24CampaignInspectAgent
{
    public static void agentmain(String command,Instrumentation instrumentation) throws Exception
    {
        if(!"r24-campaign".equals(System.getProperty("projectseele.regionalBuild")))throw new IllegalStateException("Wrong test mode");
        Map<String,Class<?>> classes=new HashMap<>();for(var c:instrumentation.getAllLoadedClasses())classes.put(c.getName(),c);
        var review=classes.get("com.projectseele.visual.TvCampaignR24Review");
        var world=review.getDeclaredField("world");world.setAccessible(true);
        if(!((Path)world.get(null)).getFileName().toString().equals("SEELE_R24_TV_REVIEW"))throw new IllegalStateException("Wrong test world");
        for(String name:List.of("stage","timer","age","clientBattleActive","clientEnemyTracked","clientView","finished"))
        {var f=review.getDeclaredField(name);f.setAccessible(true);System.out.println("R24 INSPECT "+name+"="+f.get(null));}
        var ef=review.getDeclaredField("eva");ef.setAccessible(true);Object serverEva=ef.get(null);
        System.out.println("R24 INSPECT server_eva="+describe(serverEva));
        Object minecraft=classes.get("net.minecraft.client.Minecraft").getMethod("getInstance").invoke(null);
        if("timeout".equals(command))
        {
            Object server=minecraft.getClass().getMethod("getSingleplayerServer").invoke(minecraft);
            Runnable stop=()->{try{var a=review.getDeclaredField("age");a.setAccessible(true);a.setInt(null,13999);}catch(Exception e){throw new RuntimeException(e);}};
            server.getClass().getMethod("execute",Runnable.class).invoke(server,stop);return;
        }
        if(!"inspect".equals(command))throw new IllegalArgumentException(command);
        Runnable inspect=()->{
            try
            {
                Object player=minecraft.getClass().getField("player").get(minecraft);
                Object level=minecraft.getClass().getField("level").get(minecraft);
                int id=(Integer)serverEva.getClass().getMethod("getId").invoke(serverEva);
                Object clientEva=level.getClass().getMethod("getEntity",int.class).invoke(level,id);
                System.out.println("R24 INSPECT client_eva="+describe(clientEva));
                System.out.println("R24 INSPECT client_player="+player+" vehicle="+player.getClass().getMethod("getVehicle").invoke(player));
                for(var m:classes.get("com.projectseele.world.EvaPilotResolver").getMethods())if(m.getName().equals("controlTarget")&&m.getParameterCount()==1)
                    System.out.println("R24 INSPECT client_resolved="+describe(m.invoke(null,player)));
                Object screen=minecraft.getClass().getField("screen").get(minecraft);System.out.println("R24 INSPECT screen="+screen);
                var shot=classes.get("net.minecraft.client.Screenshot");Object target=minecraft.getClass().getMethod("getMainRenderTarget").invoke(minecraft);
                for(var m:shot.getMethods())if(m.getName().equals("takeScreenshot")&&m.getParameterCount()==1)
                {
                    Object image=m.invoke(null,target);image.getClass().getMethod("writeToFile",Path.class).invoke(image,Path.of("../artifacts/facility_r24/validation/campaign14_waiting.png"));image.getClass().getMethod("close").invoke(image);
                }
            }
            catch(Exception e){e.printStackTrace();}
        };
        minecraft.getClass().getMethod("execute",Runnable.class).invoke(minecraft,inspect);
    }
    private static String describe(Object entity)throws Exception
    {
        if(entity==null)return "null";return entity+" active="+entity.getClass().getMethod("isFirstBattleActive").invoke(entity)+" position="+entity.getClass().getMethod("position").invoke(entity);
    }
}
