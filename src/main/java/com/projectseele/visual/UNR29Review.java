package com.projectseele.visual;

import com.google.gson.JsonObject;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.registry.ModItems;
import com.projectseele.world.*;
import net.minecraft.server.level.*;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Original identities, real UN phone commands, occupied return, and native flying controls. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class UNR29Review
{
    public static final boolean ENABLED="r29-un".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile boolean ready,finished;
    public static volatile String input="",photo="",flightKeys="";
    public static volatile Vec3 lookTarget;
    public static final Set<String> inputs=java.util.concurrent.ConcurrentHashMap.newKeySet(),photos=java.util.concurrent.ConcurrentHashMap.newKeySet();
    private static int stage,age,timer,serial,powerSamples;
    private static ServerLevel level;private static ServerPlayer player;private static Path world;
    private static final UUID[] units=new UUID[2],plugs=new UUID[2];private static final JsonObject checks=new JsonObject();
    private static final boolean[] resetRequested=new boolean[2];
    private static Vec3 flightStart;private static double peak,travel;
    private static final Set<String> observed=new HashSet<>();
    private static void check(String key,boolean value){checks.addProperty(key,value);if(!value)throw new IllegalStateException(key);}
    private static void next(int value){stage=value;timer=0;input="";flightKeys="";photo="";lookTarget=null;ProjectSeele.LOGGER.info("R29 UN REVIEW stage={} serial={}",stage,serial);}
    private static EvaPrototypeEntity eva(){return level.getEntity(units[serial]) instanceof EvaPrototypeEntity e?e:null;}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||!ready||finished||event.phase!=TickEvent.Phase.END)return;
        try
        {
            var server=event.getServer();if(server.getPlayerList().getPlayers().isEmpty())return;
            if(world==null)
            {
                world=server.getWorldPath(LevelResource.ROOT).normalize();check("isolated_world",world.getFileName().toString().equals("SEELE_FIELD_R29_REVIEW"));
                level=server.getLevel(FacilitySchemaV2.DIMENSION);player=server.getPlayerList().getPlayers().get(0);player.stopRiding();player.setGameMode(GameType.CREATIVE);player.setInvulnerable(true);
                player.getInventory().add(new net.minecraft.world.item.ItemStack(ModItems.UN_SATELLITE_PHONE.get()));player.teleportTo(level,6380.5,84,-6124.5,0,0);
                for(int i=0;i<2;i++){units[i]=UNRecoveryR22.identity(level,i);check("original_unit_registered_"+i,units[i]!=null);}
            }
            age++;timer++;check("bounded_run",age<28000);level.resetEmptyTime();
            var eva=eva();
            if(stage==0)
            {
                if(!resetRequested[serial]&&!UNAirLiftR29.active(level,serial))
                {UNRecoveryR22.request(player.createCommandSourceStack(),serial,true);resetRequested[serial]=true;timer=0;return;}
                if(timer%20==0)UNCommandR29.receive(player,"status",serial,0,0);
                if(eva==null)return;var plug=UNPlugDirector.capsule(eva);if(plug==null)return;plugs[serial]=plug.getUUID();
                if(UNAirLiftR29.active(level,serial))
                {
                    if(timer<80)return;
                    UNAirLiftR29.resumeReview(level,serial,player);check("resumed_original_delivery_"+serial,!UNAirLiftR29.phaseName(level,serial).equals("HOLD"));next(2);input="close";return;
                }
                if(timer<80)return;UNCommandR29.receive(player,"open",serial,0,0);input="deliver"+serial;next(1);input="deliver"+serial;return;
            }
            if(eva==null)return;
            check("same_eva_"+serial,eva.getUUID().equals(units[serial]));var plug=UNPlugDirector.capsule(eva);if(plug!=null)check("same_plug_"+serial,plug.getUUID().equals(plugs[serial]));
            String phase=UNAirLiftR29.phaseName(level,serial);
            if(UNAirLiftR29.active(level,serial))
            {
                check("no_transport_fault_"+serial,!phase.equals("HOLD"));observed.add(serial+":"+phase);
                if(stage==2&&!player.isPassenger()&&timer%20==0)
                {
                    player.getAbilities().flying=true;player.onUpdateAbilities();Vec3 at=eva.position().add(90,75,90);player.teleportTo(level,at.x,at.y,at.z,135,15);
                }
                lookTarget=stage==2&&!player.isPassenger()?eva.position().add(0,40,0):null;
                if(stage==2&&timer%20==10&&phase.equals("CLAMP"))photo="un"+serial+"_pickup";
                if(stage==2&&timer%20==10&&phase.equals("CRUISE"))photo="un"+serial+"_carried";
                if(stage==2&&timer%20==10&&phase.equals("RELEASE"))photo="un"+serial+"_release";
            }
            if(eva.getPilotEntity()==player)
            {
                check("reactor_full_"+serial,eva.getPowerTicks()==eva.getPowerCapacityTicks());check("no_cable_"+serial,!eva.isUmbilicalConnected()&&eva.getUmbilicalAnchor()==null);powerSamples++;
            }
            switch(stage)
            {
                case 1 -> {if(UNAirLiftR29.active(level,serial)){next(2);input="close";}else if(timer>200)throw new IllegalStateException("Phone did not start delivery");}
                case 2 ->
                {
                    if(!UNAirLiftR29.active(level,serial)&&timer>200)
                    {
                        check("delivered_away_from_home_"+serial,eva.position().distanceTo(UNRecoveryR22.home(serial))>120);check("delivered_unlocked_"+serial,!eva.isNervLogisticsLocked());
                        player.teleportTo(level,eva.getX()+20,eva.getY()+1,eva.getZ()+20,135,0);next(3);
                    }
                }
                case 3 -> {if(timer==30)UNCommandR29.receive(player,"board",serial,0,0);if(eva.getPilotEntity()==player&&eva.getActivationTicks()==0&&timer>100){next(4);input="flight"+serial;}if(timer>260)throw new IllegalStateException("Original capsule boarding failed");}
                case 4 ->
                {
                    if(serial==0&&timer>60){check("un00_cannot_fly",!eva.isUNFlying());next(8);}
                    else if(serial==1&&eva.isUNFlying()){flightStart=eva.position();peak=eva.getY();next(5);flightKeys="up";}
                    else if(timer>160)throw new IllegalStateException("UN01 flight did not engage");
                }
                case 5 -> {flightKeys="up";peak=Math.max(peak,eva.getY());if(timer>65){check("flight_ascent",peak>flightStart.y+18);next(6);flightKeys="forward";}}
                case 6 -> {flightKeys="forward";travel=eva.position().subtract(flightStart).horizontalDistance();photo="un01_flying";if(timer>80){check("flight_translation",travel>45);next(7);input="land";}}
                case 7 -> {if(!eva.isUNFlying()&&timer>60){check("flight_landed",eva.onGround());next(8);}if(timer>650)throw new IllegalStateException("UN01 automatic landing stalled");}
                case 8 -> {if(timer==20){UNCommandR29.receive(player,"recover",serial,0,0);}if(UNAirLiftR29.active(level,serial))next(9);else if(timer>160)throw new IllegalStateException("Occupied recovery did not start");}
                case 9 ->
                {
                    if(!phase.equals("RETREAT")&&!phase.equals("RETURN_FLIGHT")&&!phase.equals("IDLE"))check("ride_retained_"+serial,eva.getPilotEntity()==player&&player.getVehicle()==plug);
                    else check("safe_extraction_chain_"+serial,!player.isPassenger()||player.getVehicle()==plug);
                    if(!UNAirLiftR29.active(level,serial)&&timer>200)
                    {
                        check("home_return_"+serial,eva.position().distanceTo(UNRecoveryR22.home(serial))<.2);
                        eva.exitEva(player);next(10);
                    }
                }
                case 10 ->
                {
                    if(!player.isPassenger()&&timer>220)
                    {
                        if(serial==0){serial=1;next(0);player.teleportTo(level,6240.5,84,-6124.5,0,0);}
                        else
                        {
                            check("reactor_samples",powerSamples>400);
                            for(int i=0;i<2;i++)for(String name:List.of("ROLL_OUT","CLAMP","ASCEND","CRUISE","DESCEND","RELEASE","ROLL_IN"))check("phase_"+i+"_"+name,observed.contains(i+":"+name));
                            checks.addProperty("power_samples",powerSamples);checks.addProperty("flight_peak",peak);checks.addProperty("flight_displacement",travel);checks.addProperty("passed",true);Files.writeString(world.resolve("r29_un_pass.json"),checks.toString());finished=true;ProjectSeele.LOGGER.info("R29 UN PASS {}",checks);
                        }
                    }
                    if(timer>650)throw new IllegalStateException("UN extraction did not return pilot to standby");
                }
            }
        }
        catch(Exception error)
        {
            ProjectSeele.LOGGER.error("R29 UN REVIEW FAILED",error);finished=true;flightKeys="";
            try{Files.writeString(world.resolve("r29_un_failure.txt"),error.toString());}catch(Exception ignored){}
        }
    }
    private UNR29Review() {}
}
