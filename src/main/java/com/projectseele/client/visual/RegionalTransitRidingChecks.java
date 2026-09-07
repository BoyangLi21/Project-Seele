package com.projectseele.client.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.visual.RegionalNativeTransitInspection;
import com.projectseele.world.FacilitySchemaV2;
import net.minecraft.client.Minecraft;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.function.Consumer;

/** Boards actual native floor geometry and lets MTR's client/server rider code carry the player. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, value = Dist.CLIENT)
public final class RegionalTransitRidingChecks
{
    private static final boolean ENABLED="transit-riding".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final List<String> TRACE=new ArrayList<>();
    private static boolean entered, boarded, done, finishing;
    private static int age, mode, timer, ridingTicks, dismountTicks;
    private static long vehicleId;
    private static Vec3 start, previous;
    private static double travel, highestY;
    private static GameType savedMode;
    private static volatile Exception registrationFailure;

    private static Object call(Object target,String method) throws ReflectiveOperationException
    { return target.getClass().getMethod(method).invoke(target); }
    private static double axis(Object vector,String field) throws ReflectiveOperationException
    { return vector.getClass().getField(field).getDouble(vector); }

    @SubscribeEvent
    public static void client(TickEvent.ClientTickEvent event)
    {
        if(!ENABLED || event.phase!=TickEvent.Phase.END)return;
        Minecraft mc=Minecraft.getInstance();mc.options.pauseOnLostFocus=false;mc.options.renderDistance().set(8);
        if(done){mc.stop();return;}
        if(finishing)return;
        if(mc.player==null || mc.level==null || mc.getSingleplayerServer()==null)return;
        var server=mc.getSingleplayerServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))throw new IllegalStateException("Wrong transit review save");
        try
        {
            if(Files.exists(world.resolve("regional_stop_requested")))
            {Files.delete(world.resolve("regional_stop_requested"));log("STOP requested");finish(mc);return;}
            if(registrationFailure!=null)throw new IllegalStateException("Native server rider registration",registrationFailure);
            require(++age<24000,"transit passenger timeout");timer++;
            if(!entered)
            {
                entered=true;timer=0;
                server.execute(()->{
                    var p=server.getPlayerList().getPlayers().get(0);savedMode=p.gameMode.getGameModeForPlayer();
                    p.setGameMode(GameType.CREATIVE);p.getAbilities().flying=false;p.onUpdateAbilities();
                    p.teleportTo(server.getLevel(FacilitySchemaV2.DIMENSION),-330.5,-466,777.5,0,0);
                });
                return;
            }
            Class<?> riding=Class.forName("org.mtr.mod.client.VehicleRidingMovement");
            if(dismountTicks>0)
            {
                mc.options.keyShift.setDown(true);
                if(--dismountTicks==0)
                {
                    mc.options.keyShift.setDown(false);mode++;timer=0;boarded=false;
                    if(mode==2)
                    {
                        Files.writeString(world.resolve("regional_transit_riding_checks.txt"),String.join("\n",TRACE)+"\nCOMPLETE native train and airplane passenger rides\n");
                        finish(mc);return;
                    }
                    server.execute(()->server.getPlayerList().getPlayers().get(0).teleportTo(
                            server.getLevel(FacilitySchemaV2.DIMENSION),650.5,81,1235.5,0,0));
                }
                return;
            }
            if(boarded)
            {
                boolean nativeRiding=(Boolean)riding.getMethod("isRiding",long.class).invoke(null,vehicleId);
                require(nativeRiding,"native rider remains attached");
                if(++ridingTicks<60){start=mc.player.position();previous=start;return;}
                Vec3 pos=mc.player.position();double step=pos.distanceTo(previous);previous=pos;travel+=step;highestY=Math.max(highestY,pos.y);
                require(step<15,"native passenger movement continuity "+step);
                if(ridingTicks%100==0)log("RIDE "+(mode==0?"U1":"F1")+" distance="+Math.round(travel)+" y="+Math.round(pos.y));
                boolean passed=mode==0?pos.distanceTo(start)>80:highestY>160 && pos.distanceTo(start)>240;
                if(passed)
                {
                    long id=vehicleId;
                    server.execute(()->{
                        try
                        {
                            Object simulator=RegionalNativeTransitInspection.simulator();
                            boolean registered=(Boolean)simulator.getClass().getMethod("isRiding",java.util.UUID.class,long.class)
                                    .invoke(simulator,server.getPlayerList().getPlayers().get(0).getUUID(),id);
                            if(!registered)throw new IllegalStateException("MTR server has no passenger registration");
                            log("PASS "+(mode==0?"U1 train":"F1 airplane")+" native client motion and server passenger registration");
                        }
                        catch(Exception e){registrationFailure=e;ProjectSeele.LOGGER.error("REGIONAL NATIVE RIDER REGISTRATION FAILED",e);}
                    });
                    dismountTicks=60;
                }
                return;
            }
            if(timer<100)return;
            Object data=Class.forName("org.mtr.mod.client.MinecraftClientData").getMethod("getInstance").invoke(null);
            for(Object vehicle:(Iterable<?>)data.getClass().getField("vehicles").get(data))
            {
                Object extra=vehicle.getClass().getField("vehicleExtraData").get(vehicle);
                String number=(String)call(extra,"getThisRouteNumber");
                if(!number.equals(mode==0?"U1":"F1"))continue;
                Object head=call(vehicle,"getHeadPosition");
                if(head==null || axis(head,"y")>100 || (Double)call(vehicle,"getSpeed")>.001)continue;
                var cars=(List<?>)extra.getClass().getField("immutableVehicleCars").get(extra);
                if(cars.isEmpty())continue;
                Object car=cars.get(0);String carId=(String)call(car,"getVehicleId");
                Class<?> transport=Class.forName("org.mtr.core.data.TransportMode");
                Object transportMode=transport.getField(mode==0?"TRAIN":"AIRPLANE").get(null);
                Object[] resourceHolder={null};
                Consumer<Object> consumer=pair->{try{resourceHolder[0]=pair.getClass().getMethod("left").invoke(pair);}catch(Exception e){throw new IllegalStateException(e);}};
                Class.forName("org.mtr.mod.client.CustomResourceLoader").getMethod("getVehicleById",transport,String.class,Consumer.class)
                        .invoke(null,transportMode,carId,consumer);
                Object resource=resourceHolder[0];if(resource==null)continue;
                Object cache=resource.getClass().getMethod("getCachedVehicleResource",int.class,int.class,boolean.class).invoke(resource,0,cars.size(),false);
                if(cache==null)continue;
                Collection<?> floors=(Collection<?>)cache.getClass().getField("floors").get(cache);
                if(floors.isEmpty())continue;
                Object floor=null;double largest=-1;
                for(Object candidate:floors)
                {
                    double width=(Double)call(candidate,"getMaxXMapped")-(Double)call(candidate,"getMinXMapped");
                    double length=(Double)call(candidate,"getMaxZMapped")-(Double)call(candidate,"getMinZMapped");
                    if(width>=.6 && length>=.6 && width*length>largest){largest=width*length;floor=candidate;}
                }
                if(floor==null)continue;
                double x=((Double)call(floor,"getMinXMapped")+(Double)call(floor,"getMaxXMapped"))/2;
                double y=(Double)call(floor,"getMaxYMapped");
                double z=((Double)call(floor,"getMinZMapped")+(Double)call(floor,"getMaxZMapped"))/2;
                Class<?> listType=Class.forName("org.mtr.libraries.it.unimi.dsi.fastutil.objects.ObjectArrayList");
                Object floorList=listType.getConstructor(Collection.class).newInstance(floors);
                vehicleId=(Long)call(vehicle,"getId");
                Method startRiding=riding.getMethod("startRiding",listType,long.class,long.class,long.class,int.class,double.class,double.class,double.class,double.class);
                startRiding.invoke(null,floorList,(Long)call(extra,"getDepotId"),(Long)call(extra,"getSidingId"),vehicleId,0,x,y,z,0D);
                if(!(Boolean)riding.getMethod("isRiding",long.class).invoke(null,vehicleId))continue;
                // The ordinary caller boards inside vehicle rendering and immediately
                // runs movePlayer. A test tick needs that first render-frame grace;
                // every subsequent keepalive and displacement belongs to native MTR.
                var grace=riding.getDeclaredField("ridingVehicleCooldown");grace.setAccessible(true);grace.setInt(null,0);
                boarded=true;ridingTicks=0;travel=0;highestY=-1000;
                log("BOARD "+number+" resource="+carId+" nativeFloor="+x+","+y+","+z+" vehicle="+vehicleId);
                break;
            }
            if(timer%600==0)log("WAIT native stopped "+(mode==0?"U1":"F1")+" at boarding station");
        }
        catch(Exception exception)
        {
            ProjectSeele.LOGGER.error("REGIONAL TRANSIT RIDING FAILED",exception);
            try{Files.writeString(world.resolve("regional_transit_riding_failure.txt"),String.join("\n",TRACE)+"\n"+exception);}catch(Exception ignored){}
            finish(mc);
        }
    }

    private static void finish(Minecraft mc)
    {
        finishing=true;
        mc.options.keyShift.setDown(false);
        mc.getSingleplayerServer().execute(()->{
            var p=mc.getSingleplayerServer().getPlayerList().getPlayers().get(0);
            if(savedMode!=null)p.setGameMode(savedMode);
            p.teleportTo(mc.getSingleplayerServer().getLevel(FacilitySchemaV2.DIMENSION),-359.5,81,695.5,0,0);
            done=true;
        });
    }
    private static void require(boolean condition,String reason){if(!condition)throw new IllegalStateException(reason);}
    private static void log(String line){TRACE.add(line);ProjectSeele.LOGGER.info("REGIONAL TRANSIT RIDER {}",line);}
}
