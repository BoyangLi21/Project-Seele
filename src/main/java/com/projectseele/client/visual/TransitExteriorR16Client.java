package com.projectseele.client.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.visual.RegionalNativeTransitInspection;
import com.projectseele.world.FacilitySchemaV2;
import net.minecraft.client.*;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** A separate, non-riding observer films the actual scheduled native vehicles. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class TransitExteriorR16Client
{
    public static final boolean ENABLED="r16-exterior".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final String SERVICE=System.getProperty("projectseele.exteriorService","P1");
    public record View(Vec3 position,Vec3 target) {}
    private static volatile long id;
    private static volatile Vec3 serverHead,desiredEye;
    private static volatile boolean serverMoving;
    private static volatile String failure="";
    private static View shot;
    private static Object currentVehicle,currentCar;
    private static Vec3 renderedBody;
    private static boolean started,armed,departed,airborne,finishing,oldGui,oldPause,clientReady,originWest;
    private static int ticks,endTicks,dropped,oldFov,oldDistance;
    private static CameraType oldCamera;
    private static Vec3 previousHead,forward=new Vec3(1,0,0),head;
    private static double speed,length;
    private static boolean doors;
    private static Path folder;
    private static long firstNanos,lastNanos;
    private static final JsonArray FRAMES=new JsonArray();
    private static final ThreadPoolExecutor WRITER=new ThreadPoolExecutor(2,2,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(8),r->{Thread t=new Thread(r,"transit-exterior-film");t.setDaemon(true);return t;});
    public static View cameraView(){return ENABLED&&!finishing?shot:null;}
    @SubscribeEvent(priority=net.minecraftforge.eventbus.api.EventPriority.LOWEST,receiveCanceled=true)
    public static void reviewFog(net.minecraftforge.client.event.ViewportEvent.RenderFog event)
    {
        // The four-chunk capture ring must not fog out a complete airliner
        // or the ground below its normal cruise altitude.
        if(!ENABLED||event.getType()!=net.minecraft.world.level.material.FogType.NONE)return;
        event.setNearPlaneDistance(384);event.setFarPlaneDistance(1536);event.setCanceled(true);
    }
    private static Object call(Object o,String n)throws ReflectiveOperationException{return o.getClass().getMethod(n).invoke(o);}
    private static Vec3 point(Object o)throws ReflectiveOperationException{return new Vec3(o.getClass().getField("x").getDouble(o),o.getClass().getField("y").getDouble(o),o.getClass().getField("z").getDouble(o));}
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent e)
    {
        if(!ENABLED||e.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();var server=mc.getSingleplayerServer();if(mc.player==null||server==null)return;
        try
        {
            if(!started)
            {
                if(!server.getWorldPath(LevelResource.ROOT).normalize().getFileName().toString().equals("SEELE_TV_FACILITIES_R16"))throw new IllegalStateException("Review copy required");
                if(!Set.of("P1","F1").contains(SERVICE))throw new IllegalArgumentException("Unknown exterior service");
                started=true;oldGui=mc.options.hideGui;oldPause=mc.options.pauseOnLostFocus;oldFov=mc.options.fov().get();oldDistance=mc.options.renderDistance().get();oldCamera=mc.options.getCameraType();
                mc.options.hideGui=true;mc.options.pauseOnLostFocus=false;mc.options.fov().set(76);mc.options.renderDistance().set(Boolean.getBoolean("projectseele.nativeCapture")?8:4);mc.options.setCameraType(CameraType.FIRST_PERSON);mc.options.broadcastOptions();
                folder=mc.gameDirectory.toPath().resolve("../artifacts/tv_facilities_r16/exterior_"+SERVICE+"_"+System.currentTimeMillis()).normalize();Files.createDirectories(folder);
                server.execute(()->{try{server.getPlayerList().getPlayers().get(0).setGameMode(GameType.SPECTATOR);deploy();}catch(Exception ex){failure=ex.toString();}});
            }
            if(finishing){close(mc);return;}
            if(Files.deleteIfExists(server.getWorldPath(LevelResource.ROOT).resolve("regional_stop_requested"))){finish("Review stopped");return;}
            if(!failure.isEmpty())throw new IllegalStateException(failure);
            if(++ticks>20000)throw new IllegalStateException("Exterior journey timeout");
            if(ticks%5==0)server.execute(()->{
                try
                {
                    Object sim=RegionalNativeTransitInspection.simulator();
                    for(Object siding:(Iterable<?>)sim.getClass().getField("sidings").get(sim))
                    {
                        if(!((String)call(siding,"getName")).startsWith(SERVICE+" "))continue;
                        var field=siding.getClass().getDeclaredField("vehicles");field.setAccessible(true);
                        for(Object vehicle:(Iterable<?>)field.get(siding))
                        {
                            if(!(Boolean)call(vehicle,"getIsOnRoute"))continue;Object h=call(vehicle,"getHeadPosition");if(h==null)continue;
                            id=(Long)call(vehicle,"getId");serverHead=point(h);serverMoving=(Boolean)call(vehicle,"isMoving");break;
                        }
                    }
                    // Streaming follows the authoritative vehicle, even when
                    // a delayed client packet still describes an older place.
                    Vec3 p=serverHead==null?null:eye(serverHead);
                    if(p!=null)server.getPlayerList().getPlayers().get(0).teleportTo(server.getLevel(FacilitySchemaV2.DIMENSION),p.x,p.y-1.62,p.z,0,0);
                }
                catch(Exception ex){failure=ex.toString();}
            });
            Object data=Class.forName("org.mtr.mod.client.MinecraftClientData").getMethod("getInstance").invoke(null);
            Object selected=null;for(Object v:(Iterable<?>)data.getClass().getField("vehicles").get(data))if((Long)call(v,"getId")==id){selected=v;break;}
            if(selected==null){currentVehicle=null;clientReady=false;if(serverHead!=null)shot=new View(eye(serverHead),serverHead);return;}Object h=call(selected,"getHeadPosition");if(h==null)return;head=point(h);speed=(Double)call(selected,"getSpeed");
            clientReady=serverHead!=null&&serverHead.distanceTo(head)<96;
            Object extra=selected.getClass().getField("vehicleExtraData").get(selected);length=0;for(Object car:(Iterable<?>)extra.getClass().getField("immutableVehicleCars").get(extra))length+=(Double)call(car,"getLength");
            currentVehicle=selected;currentCar=((List<?>)extra.getClass().getField("immutableVehicleCars").get(extra)).get(0);
            doors=(Double)call(selected.getClass().getField("persistentVehicleData").get(selected),"getDoorValue")>.5;
            if(previousHead!=null){Vec3 d=head.subtract(previousHead);d=new Vec3(d.x,0,d.z);if(d.lengthSqr()>.0001&&d.lengthSqr()<900)forward=d.normalize();}previousHead=head;
            if(!armed&&serverHead!=null&&!serverMoving&&serverHead.distanceTo(head)<2&&speed<.001&&doors&&head.y<85&&(SERVICE.equals("F1")||head.x<560&&Math.abs(head.z-472.5)<2))
            {armed=true;originWest=head.x<0;ProjectSeele.LOGGER.info("R16 EXTERIOR {} capture armed at {}",SERVICE,head);}
            if(armed)
            {
                departed|=speed>.005;airborne|=head.y>160;
                boolean otherAirport=originWest?head.x>600&&Math.abs(head.z-1240.5)<4:head.x<-1500&&Math.abs(head.z+209.5)<4;
                boolean arrival=SERVICE.equals("F1")?airborne&&otherAirport&&head.y<85:head.x>1145&&Math.abs(head.z-472.5)<2;
                if(departed&&arrival&&speed<.001&&doors&&++endTicks>60)finish("");
            }
        }
        catch(Exception ex){ProjectSeele.LOGGER.error("R16 exterior review failed",ex);finish(ex.toString());}
    }
    private static Vec3 eye(Vec3 h)
    {
        double up=40-18*Math.max(0,Math.min(1,(h.y-120)/80));
        return SERVICE.equals("F1")?h.add(24,up,32):h.add(-16,3.8,-4);
    }
    private static void deploy()throws Exception
    {
        Object sim=RegionalNativeTransitInspection.simulator(),route=null;
        for(Object siding:(Iterable<?>)sim.getClass().getField("sidings").get(sim))
        {
            if(!((String)call(siding,"getName")).startsWith(SERVICE+" "))continue;
            var field=siding.getClass().getDeclaredField("vehicles");field.setAccessible(true);
            for(Object vehicle:(Iterable<?>)field.get(siding))if((Boolean)call(vehicle,"getIsOnRoute")){ProjectSeele.LOGGER.info("R16 exterior uses existing {} service",SERVICE);return;}
        }
        for(Object r:(Iterable<?>)sim.getClass().getField("routes").get(sim))if(SERVICE.equals(call(r,"getRouteNumber"))){route=r;break;}
        if(route==null)throw new IllegalStateException("Missing native service "+SERVICE);long routeId=(Long)call(route,"getId");var depots=new ArrayList<Object>();
        for(Object d:(Iterable<?>)sim.getClass().getField("depots").get(sim)){Object ids=call(d,"getRouteIds");if((Boolean)ids.getClass().getMethod("contains",long.class).invoke(ids,routeId))depots.add(d);}
        if(depots.size()!=1)throw new IllegalStateException("Expected one native depot");Class<?> list=Class.forName("org.mtr.libraries.it.unimi.dsi.fastutil.objects.ObjectArrayList");sim.getClass().getMethod("instantDeployDepots",list).invoke(sim,list.getConstructor(Collection.class).newInstance(depots));
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent e)
    {
        if(ENABLED&&started&&!finishing&&e.phase==TickEvent.Phase.START&&currentVehicle!=null)
        {
            try
            {
                // Use the same body frame the native renderer evaluates now;
                // its cached head getter can describe a preceding render.
                Object frame=RegionalTransitRidingChecks.nativeBodyFrame(currentVehicle,currentCar,true);
                renderedBody=point(frame.getClass().getField("position").get(frame));
                head=point(call(currentVehicle,"getHeadPosition"));
                clientReady=serverHead!=null&&renderedBody.distanceTo(serverHead)<96;
                shot=new View(eye(renderedBody),renderedBody.add(0,2,0));
            }
            catch(Exception ex){failure=ex.toString();clientReady=false;}
            return;
        }
        if(!ENABLED||!started||finishing||!armed||!clientReady||head==null||e.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();long now=System.nanoTime();if(now-lastNanos<33_333_333L)return;lastNanos=now;
        if(WRITER.getQueue().remainingCapacity()==0){dropped++;return;}if(firstNanos==0)firstNanos=now;
        var f=new JsonObject();String name=String.format("frame_%05d.jpg",FRAMES.size());f.addProperty("file",name);f.addProperty("seconds",(now-firstNanos)/1e9);f.addProperty("exterior",true);f.addProperty("riding",false);f.addProperty("service",SERVICE);f.addProperty("fps",mc.getFps());f.addProperty("x",head.x);f.addProperty("y",head.y);f.addProperty("z",head.z);f.addProperty("speed",speed);f.addProperty("doors",doors);f.addProperty("active",true);
        for(var row:Map.of("eye",shot.position(),"target",shot.target(),"body",renderedBody,"server",serverHead).entrySet()){var a=new JsonArray();a.add(row.getValue().x);a.add(row.getValue().y);a.add(row.getValue().z);f.add(row.getKey(),a);}
        f.addProperty("phase",SERVICE.equals("F1")?(head.y<85?(doors?"at_gate":"taxi"):head.y<155?"takeoff_or_landing":"cruise"):(doors?"station_arrival":head.x<620?"station_departure":head.x>1090?"station_approach":"train_travel"));
        var pixels=Screenshot.takeScreenshot(mc.getMainRenderTarget());FRAMES.add(f);WRITER.execute(()->{try(pixels){NativeReviewFrames.writeJpeg(pixels,folder.resolve(name));}catch(Exception ex){failure=ex.toString();}});
    }
    private static void finish(String error){if(!error.isEmpty())failure=error;finishing=true;WRITER.shutdown();}
    private static void close(Minecraft mc)throws Exception
    {
        if(!WRITER.isTerminated())return;var out=new JsonObject();out.addProperty("source","Actual native MTR vehicles observed by a separate non-riding spectator");out.addProperty("service",SERVICE);out.addProperty("write_failure",failure);out.addProperty("passed",failure.isEmpty()&&departed&&(SERVICE.equals("P1")||airborne)&&endTicks>60);out.addProperty("dropped",dropped);out.add("frames",FRAMES);Files.writeString(folder.resolve("frames.json"),out.toString());
        mc.options.hideGui=oldGui;mc.options.pauseOnLostFocus=oldPause;mc.options.fov().set(oldFov);mc.options.renderDistance().set(oldDistance);mc.options.setCameraType(oldCamera);mc.options.broadcastOptions();mc.stop();
    }
    private TransitExteriorR16Client(){}
}
