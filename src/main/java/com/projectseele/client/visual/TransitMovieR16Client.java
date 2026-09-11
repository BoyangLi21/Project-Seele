package com.projectseele.client.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import net.minecraft.client.*;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.concurrent.*;

/** Native MTR exterior and real passenger cameras for the requested review films. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class TransitMovieR16Client
{
    public static final boolean ENABLED=Boolean.getBoolean("projectseele.tvTransitCapture");
    private static boolean initialized,closing,complete,oldGui;
    private static int oldFov,dropped;
    private static CameraType oldCamera;
    private static Path folder;private static long startNanos,lastNanos;
    private static String phase="waiting";
    private static Vec3 previousHead,forward=new Vec3(1,0,0);
    private static RegionalTransitRidingChecks.MovieView view;
    private static final JsonArray FRAMES=new JsonArray();
    private static final ThreadPoolExecutor WRITER=new ThreadPoolExecutor(2,2,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(8),r->{Thread t=new Thread(r,"transit-native-film");t.setDaemon(true);return t;});
    private static volatile String failure="";
    @SubscribeEvent(priority=net.minecraftforge.eventbus.api.EventPriority.HIGHEST)
    public static void hideOperator(net.minecraftforge.client.event.RenderPlayerEvent.Pre event)
    {if(ENABLED&&event.getEntity()==Minecraft.getInstance().player)event.setCanceled(true);}
    @SubscribeEvent public static void hideHands(net.minecraftforge.client.event.RenderHandEvent event)
    {if(ENABLED)event.setCanceled(true);}
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!ENABLED||event.phase!=TickEvent.Phase.END||closing)return;var mc=Minecraft.getInstance();if(mc.level==null||mc.player==null)return;
        if(!initialized)
        {
            initialized=true;oldGui=mc.options.hideGui;oldFov=mc.options.fov().get();oldCamera=mc.options.getCameraType();mc.options.hideGui=true;mc.options.fov().set(76);
            folder=mc.gameDirectory.toPath().resolve("../artifacts/tv_facilities_r16/transit_"+System.getProperty("projectseele.regionalBuild")+"_"+System.currentTimeMillis()).normalize();
            try{Files.createDirectories(folder);}catch(Exception e){throw new IllegalStateException(e);}
        }
        view=RegionalTransitRidingChecks.movieView();
        if(view!=null)
        {
            if(previousHead!=null)
            {
                Vec3 delta=view.head().subtract(previousHead);delta=new Vec3(delta.x,0,delta.z);
                if(delta.lengthSqr()>.0001&&delta.lengthSqr()<225)forward=delta.normalize();
            }
            else forward=new Vec3(view.head().x<0?-1:1,0,0);
            previousHead=view.head();
        }
    }
    public static boolean finishAndReady()
    {
        if(!ENABLED||!initialized)return true;if(complete)return true;var mc=Minecraft.getInstance();
        if(!closing){closing=true;mc.setCameraEntity(mc.player);mc.options.hideGui=oldGui;mc.options.fov().set(oldFov);mc.options.setCameraType(oldCamera);WRITER.shutdown();}
        if(!WRITER.isTerminated())return false;
        try
        {
            var manifest=new JsonObject();manifest.addProperty("source","Actual native MTR movement and passenger registration, captured from the Minecraft framebuffer");manifest.addProperty("dropped",dropped);manifest.addProperty("write_failure",failure);manifest.add("frames",FRAMES);Files.writeString(folder.resolve("frames.json"),manifest.toString());complete=true;
        }
        catch(Exception e){ProjectSeele.LOGGER.error("Transit movie manifest failed",e);complete=true;}
        return complete;
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!ENABLED||!initialized||closing)return;var mc=Minecraft.getInstance();if(mc.level==null||mc.player==null||view==null)return;
        var v=view;boolean flight=v.service().equals("F1");Vec3 right=new Vec3(-forward.z,0,forward.x);
        if(event.phase==TickEvent.Phase.START)
        {
            // MTR owns the camera's riding-relative transform. Use vanilla F5
            // and mouse angles, never replace its world-space camera position.
            if(!v.boarded())phase="station_boarding";
            else if(flight)
            {
                boolean cruise=v.head().y>155;
                phase=v.head().y<85?(v.doors()?"at_gate":"taxi"):v.head().y<155?"takeoff_or_landing":"cruise";
                if(v.ridingTicks()<70||cruise&&(v.ridingTicks()/180)%3==1)
                    phase=cruise?"passenger_cruise":"passenger_boarded";
            }
            else phase=v.travel()>460?(v.doors()?"station_arrival":"station_approach")
                    :v.travel()>100&&v.travel()<360?"passenger_ride":"station_departure";
            if(mc.options.getCameraType()!=CameraType.FIRST_PERSON)mc.options.setCameraType(CameraType.FIRST_PERSON);
            mc.options.hideGui=true;if(mc.getCameraEntity()!=mc.player)mc.setCameraEntity(mc.player);return;
        }

        if(v.ending())return;long now=System.nanoTime();if(now-lastNanos<33_333_333L)return;lastNanos=now;if(WRITER.getQueue().remainingCapacity()==0){dropped++;return;}if(startNanos==0)startNanos=now;
        var frame=new JsonObject();String name=String.format("frame_%05d.jpg",FRAMES.size());frame.addProperty("file",name);frame.addProperty("seconds",(now-startNanos)/1e9);frame.addProperty("phase",phase);frame.addProperty("service",v.service());frame.addProperty("riding",v.boarded());frame.addProperty("inside",v.inside());frame.addProperty("fps",mc.getFps());frame.addProperty("player_x",mc.player.getX());frame.addProperty("player_y",mc.player.getY());frame.addProperty("player_z",mc.player.getZ());frame.addProperty("riding_tick",v.ridingTicks());frame.addProperty("travel",v.travel());frame.addProperty("x",v.head().x);frame.addProperty("y",v.head().y);frame.addProperty("z",v.head().z);frame.addProperty("doors",v.doors());frame.addProperty("speed",v.speed());frame.addProperty("active",true);
        var image=Screenshot.takeScreenshot(mc.getMainRenderTarget());FRAMES.add(frame);
        WRITER.execute(()->{try(image){NativeReviewFrames.writeJpeg(image,folder.resolve(name));}catch(Exception e){failure=e.toString();ProjectSeele.LOGGER.error("Transit frame write failed",e);}});
    }
    private TransitMovieR16Client() {}
}
