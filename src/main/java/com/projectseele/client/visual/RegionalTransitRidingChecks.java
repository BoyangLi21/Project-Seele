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
    private static final String MODE=System.getProperty("projectseele.regionalBuild","");
    private static final boolean PORT=MODE.equals("port-boarding");
    private static final boolean ENABLED=PORT||MODE.equals("transit-riding")||MODE.equals("flight-riding")||MODE.equals("circle-riding")||MODE.equals("train-boarding")||MODE.equals("bay-boarding");
    private static final List<String> TRACE=new ArrayList<>();
    private static boolean entered, boarded, finishing;
    private static boolean dispatchRequested;
    private static volatile boolean dispatchReady;
    private static boolean boardingAligned;
    private static int alignTicks,alignmentAge,finishTicks,nativeBoardingTicks,stepInsideTicks;
    private static volatile boolean serverRegistered;
    private static volatile java.util.Set<Long> serverVehicleIds=java.util.Set.of();
    private static volatile java.util.Map<Long,Vec3> serverVehicleHeads=java.util.Map.of();
    private static volatile java.util.Map<Long,Double> serverVehicleSpeeds=java.util.Map.of();
    private static volatile boolean done;
    private static final String[] SERVICES=PORT?new String[]{"P1"}:new String[]{"U1","S1","S2","F1","C1"};
    private static final Vec3[] BOARDING=PORT?new Vec3[]{new Vec3(512.5,81,469.5)}:new Vec3[]{new Vec3(-330.5,-466,777.5),new Vec3(-1669.5,66,-274.5),new Vec3(-2751.5,71,-967.5),new Vec3(650.5,81,1235.5),new Vec3(-119.5,81,-207.5)};
    private static int mode=MODE.equals("flight-riding")||MODE.equals("bay-boarding")?3:MODE.equals("circle-riding")?4:0;
    private static int age, timer, ridingTicks, dismountTicks;
    private static long vehicleId;
    private static Vec3 start, previous;
    private static long previousMotionNanos;
    private static double previousCarrierSpeed;
    private static Vec3 boardingInterior;
    private static double travel, highestY;
    private static GameType savedMode;
    private static Vec3 savedPosition;
    private static net.minecraft.resources.ResourceKey<net.minecraft.world.level.Level> savedDimension;
    private static float savedYaw,savedPitch;
    private static boolean savedFlying,savedPause;
    private static int savedDistance;
    private static volatile Exception registrationFailure;
    private static float boardingYaw;
    private static boolean flightVisitedOther,flightOriginHakone,circleVisitedWest;
    private static volatile boolean flightDockChosen;
    private static Object flightCache,flightCar;

    private static Object call(Object target,String method) throws ReflectiveOperationException
    { return target.getClass().getMethod(method).invoke(target); }
    private static double axis(Object vector,String field) throws ReflectiveOperationException
    { return vector.getClass().getField(field).getDouble(vector); }

    @SubscribeEvent
    public static void boardingInput(net.minecraftforge.client.event.MovementInputUpdateEvent event)
    {
        // MTR detects an unregistered passenger at render cadence. Walk slowly
        // across its narrow doorway when capture stalls several client ticks.
        if(ENABLED&&!boarded&&nativeBoardingTicks>0)
            event.getInput().forwardImpulse*=.2F;
    }

    @SubscribeEvent
    public static void client(TickEvent.ClientTickEvent event)
    {
        if(!ENABLED || event.phase!=TickEvent.Phase.END)return;
        Minecraft mc=Minecraft.getInstance();
        if(done){if(TransitMovieR16Client.finishAndReady())mc.stop();return;}
        if(finishing)
        {
            if(finishTicks<80)mc.options.keyShift.setDown(true);
            if(++finishTicks==80)restorePlayer(mc);
            return;
        }
        if(mc.player==null || mc.level==null || mc.getSingleplayerServer()==null)return;
        var server=mc.getSingleplayerServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906")
                &&!(TransitMovieR16Client.ENABLED&&world.getFileName().toString().equals("SEELE_TV_FACILITIES_R16")))throw new IllegalStateException("Wrong transit review save");
        try
        {
            if(Files.exists(world.resolve("regional_stop_requested")))
            {Files.delete(world.resolve("regional_stop_requested"));log("STOP requested");finish(mc);return;}
            if(registrationFailure!=null)throw new IllegalStateException("Native server rider registration",registrationFailure);
            require(++age<36000,"transit passenger timeout");timer++;
            if(PORT)require(age<5000,"P1 passenger trip timeout");
            if(PORT&&!boarded&&boardingAligned&&nativeBoardingTicks==0&&++alignmentAge>100)boardingAligned=false;
            if(!boarded&&nativeBoardingTicks>0)
                require(++nativeBoardingTicks<(mode==3?300:150),"real stair boarding window expired at "+mc.player.position());
            if(!entered)
            {
                entered=true;timer=0;savedPause=mc.options.pauseOnLostFocus;savedDistance=mc.options.renderDistance().get();mc.options.pauseOnLostFocus=false;mc.options.renderDistance().set(TransitMovieR16Client.ENABLED&&!Boolean.getBoolean("projectseele.nativeCapture")?4:8);mc.options.broadcastOptions();
                server.execute(()->{
                    var p=server.getPlayerList().getPlayers().get(0);savedMode=p.gameMode.getGameModeForPlayer();
                    savedPosition=p.position();savedDimension=p.level().dimension();savedYaw=p.getYRot();savedPitch=p.getXRot();savedFlying=p.getAbilities().flying;
                    p.setGameMode(GameType.CREATIVE);p.getAbilities().flying=false;p.onUpdateAbilities();
                    beginService(mc);
                });
                return;
            }
            Class<?> riding=Class.forName("org.mtr.mod.client.VehicleRidingMovement");
            if(!boarded&&nativeBoardingTicks>0&&(Boolean)riding.getMethod("isRiding",long.class).invoke(null,vehicleId))
            {
                boarded=true;stepInsideTicks=mode==3?12:6;ridingTicks=0;travel=0;highestY=-1000;serverRegistered=false;
                log("BOARD "+SERVICES[mode]+" using actual native platform entry at "+mc.player.position());
            }
            if(timer%(PORT?20:100)==0)
            {
                String service=SERVICES[mode];
                server.execute(()->{
                    try
                    {
                        Object simulator=RegionalNativeTransitInspection.simulator();java.util.Set<Long> ids=new java.util.HashSet<>();
                        var heads=new java.util.HashMap<Long,Vec3>();var speeds=new java.util.HashMap<Long,Double>();
                        for(Object siding:(Iterable<?>)simulator.getClass().getField("sidings").get(simulator))
                        {
                            if(!((String)call(siding,"getName")).startsWith(service+" "))continue;
                            var field=siding.getClass().getDeclaredField("vehicles");field.setAccessible(true);
                            for(Object vehicle:(Iterable<?>)field.get(siding))
                            {
                                long id=(Long)call(vehicle,"getId");ids.add(id);
                                Object nativeHead=call(vehicle,"getHeadPosition");
                                if(nativeHead!=null){heads.put(id,new Vec3(axis(nativeHead,"x"),axis(nativeHead,"y"),axis(nativeHead,"z")));speeds.put(id,(Boolean)call(vehicle,"isMoving")?1D:0D);}
                                if(service.equals("F1")&&!flightDockChosen&&!boarded&&!(Boolean)call(vehicle,"isMoving"))
                                {
                                    Object head=call(vehicle,"getHeadPosition");if(head==null)continue;
                                    double x=axis(head,"x"),y=axis(head,"y"),z=axis(head,"z");
                                    var dwell=Class.forName("org.mtr.core.generated.data.VehicleSchema").getDeclaredField("elapsedDwellTime");dwell.setAccessible(true);
                                    boolean bay=x>600&&x<700&&Math.abs(z-1240.5)<2;
                                    boolean hakone=x<-1550&&x>-1660&&Math.abs(z+209.5)<2;
                                    if((bay||hakone&&!MODE.equals("bay-boarding"))&&Math.abs(y-80)<.5&&dwell.getLong(vehicle)<8000)
                                    {
                                        flightDockChosen=true;
                                        Vec3 entrance=aircraftEntrance(world,bay?"bay":"hakone",new Vec3(x,y+1,z-7));
                                        server.getPlayerList().getPlayers().get(0).teleportTo(server.getLevel(FacilitySchemaV2.DIMENSION),entrance.x,entrance.y,entrance.z,0,0);
                                        log("PREPARE native stopped aircraft at "+new Vec3(x,y,z));
                                    }
                                }
                            }
                        }
                        serverVehicleHeads=java.util.Map.copyOf(heads);serverVehicleSpeeds=java.util.Map.copyOf(speeds);serverVehicleIds=java.util.Set.copyOf(ids);
                    }
                    catch(Exception e){registrationFailure=e;}
                });
            }
            if(!dispatchRequested && timer>=100)
            {
                dispatchRequested=true;dispatchReady=false;serverVehicleIds=java.util.Set.of();serverVehicleHeads=java.util.Map.of();serverVehicleSpeeds=java.util.Map.of();if(PORT){boardingAligned=false;alignTicks=0;}server.execute(()->dispatchService(mc));return;
            }
            if(dismountTicks>0)
            {
                mc.options.keyShift.setDown(true);
                if(--dismountTicks==0)
                {
                    require(!(Boolean)riding.getMethod("isRiding",long.class).invoke(null,vehicleId),"native dismount completed");
                    mc.options.keyShift.setDown(false);mode++;timer=0;boarded=false;dispatchRequested=false;boardingAligned=false;nativeBoardingTicks=0;boardingYaw=0;serverVehicleIds=java.util.Set.of();
                    if(mode==(MODE.equals("train-boarding")?3:MODE.equals("bay-boarding")||TransitMovieR16Client.ENABLED&&MODE.equals("flight-riding")?4:SERVICES.length))
                    {
                        Files.writeString(world.resolve(PORT?"r07_port_riding_checks.txt":"regional_transit_riding_checks.txt"),String.join("\n",TRACE)+"\nCOMPLETE "+(PORT?(TransitMovieR16Client.ENABLED?"P1 native passenger initialization, full trip and harbor arrival":"P1 natural boarding, full trip and harbor arrival"):MODE.equals("flight-riding")?(TransitMovieR16Client.ENABLED?"F1 round trip":"F1 round trip and C1 circuit"):MODE.equals("circle-riding")?"C1 circuit":MODE.equals("bay-boarding")?"Bay aircraft natural boarding and taxi travel":MODE.equals("train-boarding")?"U1/S1/S2 natural boarding and passenger travel":"U1/S1/S2 trains, F1 round trip and C1 circuit")+" passenger rides\n");
                        Files.deleteIfExists(world.resolve("regional_transit_riding_failure.txt"));
                        finish(mc);return;
                    }
                    server.execute(()->beginService(mc));
                }
                return;
            }
            if(boarded)
            {
                if(stepInsideTicks>0)
                {
                    // Native MTR moves inside the car during rendering, not
                    // each client tick. End the walk by position: a tick-only
                    // pulse can begin and end before MTR sees a single frame.
                    Vec3 heading=new Vec3(-Math.sin(Math.toRadians(boardingYaw)),0,Math.cos(Math.toRadians(boardingYaw)));
                    boolean inside=boardingInterior==null||boardingInterior.subtract(mc.player.position()).dot(heading)<.12;
                    mc.options.keyUp.setDown(!inside);if(inside){stepInsideTicks=0;log("INSIDE "+SERVICES[mode]+" "+mc.player.position());}
                }
                boolean nativeRiding=(Boolean)riding.getMethod("isRiding",long.class).invoke(null,vehicleId);
                require(nativeRiding,"native rider remains attached");
                if(++ridingTicks<60){start=mc.player.position();previous=start;previousMotionNanos=System.nanoTime();return;}
                Vec3 pos=mc.player.position();double step=pos.distanceTo(previous);
                if(mode==3&&(ridingTicks%20==0||step>=15))log("FLIGHT position="+pos+" previous="+previous+" step="+step+" vehicle="+vehicleState());
                Object motionVehicle=currentVehicle();require(motionVehicle!=null,"native passenger vehicle remains streamed");
                double speed=(Double)call(motionVehicle,"getSpeed");long now=System.nanoTime();
                if(step>1e-5)
                {
                    double seconds=(now-previousMotionNanos)/1e9;
                    // A render stall can combine several seconds of native
                    // travel into one sample. Verify against the actual car
                    // and elapsed motion, rather than treating that as a warp.
                    if(TransitMovieR16Client.ENABLED)
                        require(step<Math.max(15,Math.max(speed,previousCarrierSpeed)*1000*seconds*2+5),"recorded passenger movement matches elapsed native speed");
                    else require(step<15,"native passenger movement continuity "+step+" from="+previous+" to="+pos+" vehicle="+vehicleState());
                    if(step>=15)log("CAPTURE GAP seconds="+seconds+" passenger="+step);
                    previousCarrierSpeed=speed;previousMotionNanos=now;
                }
                previous=pos;travel+=step;highestY=Math.max(highestY,pos.y);
                if(ridingTicks%100==0)log("RIDE "+SERVICES[mode]+" distance="+Math.round(travel)+" position="+pos+" "+vehicleState());
                boolean atOtherAirport=flightOriginHakone?pos.x>600&&Math.abs(pos.z-1240.5)<4:pos.x<-1500&&Math.abs(pos.z+209.5)<4;
                if(mode==3&&!flightVisitedOther&&highestY>160&&atOtherAirport&&pos.y<86)
                {
                    Object aircraft=currentVehicle();
                    if(aircraft!=null&&(Double)call(aircraft,"getSpeed")<.001&&(Double)call(aircraft.getClass().getField("persistentVehicleData").get(aircraft),"getDoorValue")>.5)
                    {flightVisitedOther=true;writeAircraftGeometry(aircraft,flightCache,flightCar,flightOriginHakone?"bay":"hakone");log("FLIGHT stopped at opposite airport; checking return flight");}
                }
                if(mode==4&&pos.x<-660&&pos.y>90)circleVisitedWest=true;
                boolean atOriginAirport=flightOriginHakone?pos.x<-1500&&Math.abs(pos.z+209.5)<4:pos.x>600&&pos.x<710&&Math.abs(pos.z-1240.5)<4;
                boolean passed=mode==3?flightVisitedOther&&travel>6000&&atOriginAirport&&pos.y<86
                        :mode==4?circleVisitedWest&&travel>2200&&Math.abs(pos.z+199.5)<4&&pos.x>-160&&pos.x<-50
                        :mode==1?pos.x<-1760 && pos.distanceTo(start)>80:pos.distanceTo(start)>80;
                if(MODE.equals("bay-boarding"))passed=pos.distanceTo(start)>80;
                if(PORT)
                {
                    Object arrived=currentVehicle();
                    passed=travel>500&&pos.x>1145&&pos.y<74&&arrived!=null&&(Double)call(arrived,"getSpeed")<.001&&(Double)call(arrived.getClass().getField("persistentVehicleData").get(arrived),"getDoorValue")>.5;
                }
                if(passed&&(mode==3||mode==4)&&!MODE.equals("bay-boarding"))
                {
                    Object arrived=currentVehicle();
                    passed=arrived!=null&&(Double)call(arrived,"getSpeed")<.001&&(Double)call(arrived.getClass().getField("persistentVehicleData").get(arrived),"getDoorValue")>.5;
                }
                if(ridingTicks%20==0 && !serverRegistered)
                {
                    long id=vehicleId;
                    server.execute(()->{
                        try
                        {
                            Object simulator=RegionalNativeTransitInspection.simulator();
                            boolean registered=(Boolean)simulator.getClass().getMethod("isRiding",java.util.UUID.class,long.class)
                                    .invoke(simulator,server.getPlayerList().getPlayers().get(0).getUUID(),id);
                            serverRegistered=registered;
                            if(!registered)log("REGISTER pending "+SERVICES[mode]+" vehicleStillExists="+serverVehicleIds.contains(id));
                        }
                        catch(Exception e){registrationFailure=e;ProjectSeele.LOGGER.error("REGIONAL NATIVE RIDER REGISTRATION FAILED",e);}
                    });
                }
                require(serverRegistered || ridingTicks<300,"server passenger registration timeout");
                if(passed && serverRegistered){log("PASS "+SERVICES[mode]+" native client motion and server passenger registration");dismountTicks=60;}
                return;
            }
            if(alignTicks>0){alignTicks--;return;}
            if(timer<100)return;
            if(!dispatchReady)return;
            if(mode==3&&!flightDockChosen)return;
            Object data=Class.forName("org.mtr.mod.client.MinecraftClientData").getMethod("getInstance").invoke(null);
            List<String> candidates=new ArrayList<>();int vehicleCount=0;
            for(Object vehicle:(Iterable<?>)data.getClass().getField("vehicles").get(data))
            {
                vehicleCount++;
                Object extra=vehicle.getClass().getField("vehicleExtraData").get(vehicle);
                String number=(String)call(extra,"getThisRouteNumber");
                Object head=call(vehicle,"getHeadPosition");
                long candidateId=(Long)call(vehicle,"getId");
                if(timer%100==0)candidates.add("id="+candidateId+" live="+serverVehicleIds.contains(candidateId)+" head="+(head==null?"null":new Vec3(axis(head,"x"),axis(head,"y"),axis(head,"z")))+" speed="+call(vehicle,"getSpeed"));
                if(!serverVehicleIds.contains(candidateId))continue;
                if(head==null || mode==3 && axis(head,"y")>100 || (Double)call(vehicle,"getSpeed")>.001)continue;
                Vec3 headPos=new Vec3(axis(head,"x"),axis(head,"y"),axis(head,"z"));
                if(TransitMovieR16Client.ENABLED)
                {
                    Vec3 authority=serverVehicleHeads.get(candidateId);
                    if(authority==null||authority.distanceTo(headPos)>1.5||serverVehicleSpeeds.getOrDefault(candidateId,1D)>.001)continue;
                }
                if(headPos.distanceTo(mc.player.position())>64)continue;
                Object persistent=vehicle.getClass().getField("persistentVehicleData").get(vehicle);
                if(timer%100==0)candidates.add("near="+Math.round(headPos.distanceTo(mc.player.position()))+" door="+call(persistent,"getDoorValue"));
                if((Double)call(persistent,"getDoorValue")<.5)continue;
                var cars=(List<?>)extra.getClass().getField("immutableVehicleCars").get(extra);
                if(cars.isEmpty())continue;
                Object car=cars.get(0);String carId=(String)call(car,"getVehicleId");
                Class<?> transport=Class.forName("org.mtr.core.data.TransportMode");
                Object transportMode=transport.getField(mode==3?"AIRPLANE":"TRAIN").get(null);
                Object[] resourceHolder={null};
                Consumer<Object> consumer=pair->{try{resourceHolder[0]=pair.getClass().getMethod("left").invoke(pair);}catch(Exception e){throw new IllegalStateException(e);}};
                Class.forName("org.mtr.mod.client.CustomResourceLoader").getMethod("getVehicleById",transport,String.class,Consumer.class)
                        .invoke(null,transportMode,carId,consumer);
                Object resource=resourceHolder[0];if(resource==null)continue;
                Object cache=resource.getClass().getMethod("getCachedVehicleResource",int.class,int.class,boolean.class).invoke(resource,0,cars.size(),true);
                if(cache==null)continue;
                if(PORT&&!boardingAligned)writeAircraftGeometry(vehicle,cache,car,"port");
                if(mode==3){flightOriginHakone=headPos.x<0;flightCache=cache;flightCar=car;writeAircraftGeometry(vehicle,cache,car,flightOriginHakone?"hakone":"bay");}
                if(!boardingAligned&&!TransitMovieR16Client.ENABLED)
                {
                    double length=(Double)call(car,"getLength");boardingAligned=true;alignmentAge=0;alignTicks=20;
                    if(mode==3&&Files.exists(world.resolve("regional_boarding_gates.json")))
                    {
                        alignTicks=5;Vec3 doorApproach=trainEntrance(vehicle,cache,car);
                        Vec3 entry=aircraftEntrance(world,headPos.x<0?"hakone":"bay",mc.player.position());
                        if(Math.abs(doorApproach.x-entry.x)>.2)
                            server.execute(()->server.getPlayerList().getPlayers().get(0).teleportTo(server.getLevel(FacilitySchemaV2.DIMENSION),doorApproach.x,entry.y,entry.z,0,0));
                        boardingYaw=0;break;
                    }
                    double facingSign=mode==3&&headPos.x<0?-1:1;
                    Vec3 approach=new Vec3(headPos.x-facingSign*length/2,headPos.y+1,headPos.z-7);
                    if(naturalBoarding(world)){approach=trainEntrance(vehicle,cache,car);alignTicks=5;}
                    Vec3 setup=approach;
                    server.execute(()->{var p=server.getPlayerList().getPlayers().get(0);p.teleportTo(server.getLevel(FacilitySchemaV2.DIMENSION),setup.x,setup.y,setup.z,boardingYaw,0);p.fallDistance=0;p.setDeltaMovement(Vec3.ZERO);});
                    break;
                }
                Collection<?> floors=(Collection<?>)cache.getClass().getField("floors").get(cache);
                if(timer%100==0)candidates.add("resource="+carId+" floors="+floors.size());
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
                if(naturalBoarding(world))
                {
                    nativeBoardingTicks=Math.max(1,nativeBoardingTicks);
                    if(!(Boolean)riding.getMethod("isRiding",long.class).invoke(null,vehicleId))
                    {
                        mc.player.setYRot(boardingYaw);mc.player.setXRot(0);mc.options.keyUp.setDown(true);break;
                    }
                    stepInsideTicks=mode==3?12:6;boarded=true;ridingTicks=0;travel=0;highestY=-1000;serverRegistered=false;
                    log("BOARD "+SERVICES[mode]+" through actual native platform doorway; "+mc.player.position());break;
                }
                Method startRiding=riding.getMethod("startRiding",listType,long.class,long.class,long.class,int.class,double.class,double.class,double.class,double.class);
                startRiding.invoke(null,floorList,(Long)call(extra,"getDepotId"),(Long)call(extra,"getSidingId"),vehicleId,0,x,y,z,0D);
                if(timer%100==0)candidates.add("attempt="+x+","+y+","+z+" attached="+riding.getMethod("isRiding",long.class).invoke(null,vehicleId));
                if(!(Boolean)riding.getMethod("isRiding",long.class).invoke(null,vehicleId))continue;
                // The ordinary caller boards inside vehicle rendering and immediately
                // runs movePlayer. A test tick needs that first render-frame grace;
                // every subsequent keepalive and displacement belongs to native MTR.
                var grace=riding.getDeclaredField("ridingVehicleCooldown");grace.setAccessible(true);grace.setInt(null,0);
                // Use the ordinary client packet for the initial registration;
                // never insert a rider directly into the server simulator.
                var update=riding.getDeclaredMethod("sendUpdate",boolean.class);update.setAccessible(true);update.invoke(null,false);
                boarded=true;ridingTicks=0;travel=0;highestY=-1000;serverRegistered=false;
                log("BOARD "+SERVICES[mode]+" displayRoute="+number+" resource="+carId+" nativeFloor="+x+","+y+","+z+" head="+headPos+" vehicle="+vehicleId);
                break;
            }
            if(timer%100==0)log("WAIT "+SERVICES[mode]+" player="+mc.player.position()+" nativeVehicles="+vehicleCount+" serverIds="+serverVehicleIds+" "+candidates);
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
        finishing=true;finishTicks=0;mc.options.keyUp.setDown(false);mc.options.keyShift.setDown(true);
    }
    private static void restorePlayer(Minecraft mc)
    {
        mc.options.keyShift.setDown(false);
        mc.options.pauseOnLostFocus=savedPause;mc.options.renderDistance().set(savedDistance);
        mc.getSingleplayerServer().execute(()->{
            var p=mc.getSingleplayerServer().getPlayerList().getPlayers().get(0);
            if(savedMode!=null)p.setGameMode(savedMode);
            if(savedPosition!=null)p.teleportTo(mc.getSingleplayerServer().getLevel(savedDimension),savedPosition.x,savedPosition.y,savedPosition.z,savedYaw,savedPitch);
            p.fallDistance=0;p.setDeltaMovement(Vec3.ZERO);
            p.getAbilities().flying=savedFlying;p.onUpdateAbilities();
            done=true;
        });
    }
    private static void beginService(Minecraft mc)
    {
        var server=mc.getSingleplayerServer();var player=server.getPlayerList().getPlayers().get(0);Vec3 point=BOARDING[mode];
        player.teleportTo(server.getLevel(FacilitySchemaV2.DIMENSION),point.x,point.y,point.z,0,0);player.fallDistance=0;
    }
    private static void dispatchService(Minecraft mc)
    {
        try
        {
            Object simulator=RegionalNativeTransitInspection.simulator();Object chosenRoute=null;
            for(Object siding:(Iterable<?>)simulator.getClass().getField("sidings").get(simulator))
            {
                if(!((String)call(siding,"getName")).startsWith(SERVICES[mode]+" "))continue;
                var field=siding.getClass().getDeclaredField("vehicles");field.setAccessible(true);
                for(Object vehicle:(Iterable<?>)field.get(siding))if((Boolean)call(vehicle,"getIsOnRoute"))
                {if(mode==3)flightDockChosen=false;dispatchReady=true;log("USE ACTIVE "+SERVICES[mode]+" native service without resetting its trajectory");return;}
            }
            for(Object route:(Iterable<?>)simulator.getClass().getField("routes").get(simulator))if(SERVICES[mode].equals(call(route,"getRouteNumber"))){chosenRoute=route;break;}
            require(chosenRoute!=null,"native service exists "+SERVICES[mode]);long routeId=(Long)call(chosenRoute,"getId");List<Object> selected=new ArrayList<>();
            for(Object depot:(Iterable<?>)simulator.getClass().getField("depots").get(simulator))
            {Object ids=call(depot,"getRouteIds");if((Boolean)ids.getClass().getMethod("contains",long.class).invoke(ids,routeId))selected.add(depot);}
            require(selected.size()==1,"one native depot for "+SERVICES[mode]);
            Class<?> listType=Class.forName("org.mtr.libraries.it.unimi.dsi.fastutil.objects.ObjectArrayList");Object list=listType.getConstructor(Collection.class).newInstance(selected);
            simulator.getClass().getMethod("instantDeployDepots",listType).invoke(simulator,list);serverVehicleIds=java.util.Set.of();serverVehicleHeads=java.util.Map.of();serverVehicleSpeeds=java.util.Map.of();if(mode==3)flightDockChosen=false;dispatchReady=true;log("DISPATCH "+SERVICES[mode]+" through native depot");
        }
        catch(Exception e){registrationFailure=e;}
    }
    private static String vehicleState() throws ReflectiveOperationException
    {
        Object data=Class.forName("org.mtr.mod.client.MinecraftClientData").getMethod("getInstance").invoke(null);
        for(Object vehicle:(Iterable<?>)data.getClass().getField("vehicles").get(data))
        {
            if((Long)call(vehicle,"getId")!=vehicleId)continue;
            Object head=call(vehicle,"getHeadPosition");Object extra=vehicle.getClass().getField("vehicleExtraData").get(vehicle);
            return "head="+(head==null?"null":new Vec3(axis(head,"x"),axis(head,"y"),axis(head,"z")))+" speed="+call(vehicle,"getSpeed")+" reversed="+call(vehicle,"getReversed")+" onRoute="+call(vehicle,"getIsOnRoute")+" stop="+call(extra,"getStopIndex");
        }
        return "not streamed";
    }
    private static Object currentVehicle() throws ReflectiveOperationException
    {
        Object data=Class.forName("org.mtr.mod.client.MinecraftClientData").getMethod("getInstance").invoke(null);
        for(Object v:(Iterable<?>)data.getClass().getField("vehicles").get(data))if((Long)call(v,"getId")==vehicleId)return v;
        return null;
    }
    public record MovieView(String service,boolean boarded,boolean inside,int ridingTicks,double travel,
                            Vec3 head,double speed,double length,boolean doors,boolean ending) {}
    /** Read-only camera telemetry; the normal MTR passenger controller retains ownership. */
    public static MovieView movieView()
    {
        if(!ENABLED||mode>=SERVICES.length)return null;
        try
        {
            Object vehicle=currentVehicle();var mc=Minecraft.getInstance();
            if(vehicle==null&&mc.player!=null)
            {
                Object data=Class.forName("org.mtr.mod.client.MinecraftClientData").getMethod("getInstance").invoke(null);double closest=Double.MAX_VALUE;
                for(Object v:(Iterable<?>)data.getClass().getField("vehicles").get(data))
                {
                    if(!serverVehicleIds.contains((Long)call(v,"getId")))continue;
                    Object h=call(v,"getHeadPosition");if(h==null)continue;
                    Vec3 point=new Vec3(axis(h,"x"),axis(h,"y"),axis(h,"z"));double distance=mc.player.position().distanceToSqr(point);
                    if(distance<closest){closest=distance;vehicle=v;}
                }
            }
            if(vehicle==null)return null;Object h=call(vehicle,"getHeadPosition");if(h==null)return null;
            Object extra=vehicle.getClass().getField("vehicleExtraData").get(vehicle);double length=0;
            for(Object car:(Iterable<?>)extra.getClass().getField("immutableVehicleCars").get(extra))length+=(Double)call(car,"getLength");
            double doors=(Double)call(vehicle.getClass().getField("persistentVehicleData").get(vehicle),"getDoorValue");
            return new MovieView(SERVICES[mode],boarded,boarded&&stepInsideTicks==0,ridingTicks,travel,new Vec3(axis(h,"x"),axis(h,"y"),axis(h,"z")),(Double)call(vehicle,"getSpeed"),length,doors>.5,finishing||done);
        }
        catch(ReflectiveOperationException e){return null;}
    }
    private static Vec3 aircraftEntrance(java.nio.file.Path world,String airport,Vec3 fallback) throws Exception
    {
        var path=world.resolve("regional_boarding_gates.json");if(!Files.exists(path))return fallback;
        var plan=com.google.gson.JsonParser.parseString(Files.readString(path)).getAsJsonObject();
        for(var entry:plan.getAsJsonArray("gates"))
        {
            var gate=entry.getAsJsonObject();if(!airport.equals(gate.get("id").getAsString()))continue;
            var p=gate.getAsJsonArray("entry");return new Vec3(p.get(0).getAsDouble(),p.get(1).getAsDouble(),p.get(2).getAsDouble());
        }
        return fallback;
    }
    private static boolean naturalBoarding(java.nio.file.Path world)
    {
        // Review films begin with the native passenger interface. Walking
        // doorway checks remain a separate test and must not be reported as
        // passing merely because the subsequent recorded journey succeeds.
        if(TransitMovieR16Client.ENABLED)return false;
        return Files.exists(world.resolve(mode==3?"regional_boarding_gates.json":"regional_native_platforms_ready.json"));
    }
    public static Object nativeBodyFrame(Object vehicle,Object car) throws Exception
    {return nativeBodyFrame(vehicle,car,false);}
    public static Object nativeBodyFrame(Object vehicle,Object car,boolean displayed) throws Exception
    {
        Class<?> vector=Class.forName("org.mtr.core.tool.Vector"),frame=Class.forName("org.mtr.mod.render.PositionAndRotation");
        Class<?> list=Class.forName("org.mtr.libraries.it.unimi.dsi.fastutil.objects.ObjectArrayList");
        // Zero elapsed time reads the native display smoothing without
        // advancing its correction a second time in the same render frame.
        Object pairs=displayed?vehicle.getClass().getMethod("getSmoothedVehicleCarsAndPositions",long.class).invoke(vehicle,0L):call(vehicle,"getVehicleCarsAndPositions");
        Object pair=((List<?>)pairs).get(0);
        Collection<Object> frames=new ArrayList<>();
        for(Object bogies:(Iterable<?>)call(pair,"right"))frames.add(frame.getConstructor(vector,vector,boolean.class).newInstance(call(bogies,"left"),call(bogies,"right"),true));
        return frame.getConstructor(list,Class.forName("org.mtr.core.data.VehicleCar"),boolean.class)
                .newInstance(list.getConstructor(Collection.class).newInstance(frames),car,true);
    }
    private static Vec3 trainEntrance(Object vehicle,Object cache,Object car) throws Exception
    {
        Object body=nativeBodyFrame(vehicle,car);Class<?> frame=body.getClass();Object p=frame.getField("position").get(body);
        double yaw=frame.getField("yaw").getDouble(body),c=Math.cos(yaw),s=Math.sin(yaw),best=Double.MAX_VALUE;Vec3 chosen=null;
        for(Object box:(Iterable<?>)cache.getClass().getField("doorways").get(cache))
        {
            double x=((Double)call(box,"getMinXMapped")+(Double)call(box,"getMaxXMapped"))/2;
            double z=((Double)call(box,"getMinZMapped")+(Double)call(box,"getMaxZMapped"))/2;
            double sign=Math.signum(x);Vec3 outward=new Vec3(sign*c,0,-sign*s);
            if(Math.abs(s)>.5?outward.z>-.5:outward.x>-.5)continue;
            double floorY=Double.NEGATIVE_INFINITY,insideX=x-sign*.4;
            for(Object floor:(Iterable<?>)cache.getClass().getField("floors").get(cache))
                if(insideX>=(Double)call(floor,"getMinXMapped")-.05&&insideX<=(Double)call(floor,"getMaxXMapped")+.05
                        &&z>=(Double)call(floor,"getMinZMapped")-.05&&z<=(Double)call(floor,"getMaxZMapped")+.05)
                    floorY=Math.max(floorY,(Double)call(floor,"getMaxYMapped"));
            if(!Double.isFinite(floorY))continue;
            Vec3 door=new Vec3(axis(p,"x")+x*c+z*s,axis(p,"y")+floorY,axis(p,"z")+z*c-x*s);
            double distance=door.distanceTo(Minecraft.getInstance().player.position());
            if(distance<best)
            {
                best=distance;chosen=door.add(outward.scale(1.2));boardingInterior=door.subtract(outward.scale(1.1));boardingYaw=(float)Math.toDegrees(Math.atan2(outward.x,-outward.z));
                var level=Minecraft.getInstance().level;double standing=Double.NaN;
                for(int yy=net.minecraft.util.Mth.floor(door.y)-2;yy<=net.minecraft.util.Mth.floor(door.y);yy++)
                {
                    var pos=net.minecraft.core.BlockPos.containing(chosen.x,yy,chosen.z);var shape=level.getBlockState(pos).getCollisionShape(level,pos);
                    if(!shape.isEmpty()){double top=yy+shape.max(net.minecraft.core.Direction.Axis.Y);if(Math.abs(top-door.y)<=1)standing=top;}
                }
                if(Double.isFinite(standing))chosen=new Vec3(chosen.x,standing+.025,chosen.z);
            }
        }
        require(chosen!=null,"native train has an accessible platform-side doorway");log("PLATFORM ENTRY "+chosen+" yaw="+boardingYaw+" nativeBodyY="+axis(p,"y"));return chosen;
    }
    private static void writeAircraftGeometry(Object vehicle,Object cache,Object car,String airport) throws Exception
    {
        Object body=nativeBodyFrame(vehicle,car);Class<?> frame=body.getClass();
        Object position=frame.getField("position").get(body);
        com.google.gson.JsonObject out=new com.google.gson.JsonObject();
        out.addProperty("airport",airport);out.addProperty("x",axis(position,"x"));out.addProperty("y",axis(position,"y"));out.addProperty("z",axis(position,"z"));
        Object head=call(vehicle,"getHeadPosition");com.google.gson.JsonArray nativeHead=new com.google.gson.JsonArray();
        for(String axis:List.of("x","y","z"))nativeHead.add(axis(head,axis));out.add("head",nativeHead);
        out.addProperty("yaw",frame.getField("yaw").getDouble(body));out.addProperty("pitch",frame.getField("pitch").getDouble(body));
        for(String kind:List.of("floors","doorways"))
        {
            com.google.gson.JsonArray boxes=new com.google.gson.JsonArray();
            for(Object box:(Iterable<?>)cache.getClass().getField(kind).get(cache))
            {
                com.google.gson.JsonArray a=new com.google.gson.JsonArray();
                for(String bound:List.of("MinX","MinY","MinZ","MaxX","MaxY","MaxZ"))a.add((Double)call(box,"get"+bound+"Mapped"));
                boxes.add(a);
            }
            out.add(kind,boxes);
        }
        Files.writeString(Minecraft.getInstance().getSingleplayerServer().getWorldPath(LevelResource.ROOT).resolve("quality_aircraft_geometry_"+airport+".json"),out.toString());
    }
    private static void require(boolean condition,String reason){if(!condition)throw new IllegalStateException(reason);}
    private static void log(String line){TRACE.add(line);ProjectSeele.LOGGER.info("REGIONAL TRANSIT RIDER {}",line);}
}
