package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.entity.*;
import com.projectseele.world.*;
import com.projectseele.ProjectSeele;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.*;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Longer-than-maintenance chair sit, live rack charging, catapult and surface handoff. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class FieldR28Review
{
    public static volatile boolean seatsFinished;
    public static volatile int receivedRifleTracers;
    public static volatile int ntwSoundsPlayed;
    public static final java.util.List<Long> rifleTicks=new java.util.ArrayList<>();
    private static double ascentStart,lastAscent,earlyRise,earlySpeed,climbSpeed;
    private static boolean tallGate;
    private static int age,sitting,rackFrames,ascentFrames,surfaceFrames,firstAscentTicks=-1;
    private static boolean saved,rackCharged;
    private static NervCommandSeatEntity seat;
    private static void require(boolean value,String why){if(!value)throw new IllegalStateException(why);}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!FactoryR20Review.R28||!FactoryR20Review.ready||saved||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        try
        {
            require(world.getFileName().toString().equals(FactoryR20Review.R29?"SEELE_FIELD_R29_REVIEW":"SEELE_FIELD_R28_REVIEW"),"Review boundary");
            ServerLevel level=server.getLevel(FacilitySchemaV2.DIMENSION);ServerPlayer player=server.getPlayerList().getPlayers().get(0);age++;
            if(!seatsFinished)
            {
                if(FactoryR20Review.R29){seatsFinished=true;return;}
                if(age==1){player.stopRiding();player.teleportTo(level,28.5,-409,286.5,0,0);}
                if(age<80)return;
                if(seat==null)
                {
                    var at=new BlockPos(28,-409,288);var state=level.getBlockState(at);
                    require(state.getBlock() instanceof NervOfficeChairBlock,"Office chair missing");
                    state.use(level,player,net.minecraft.world.InteractionHand.MAIN_HAND,new net.minecraft.world.phys.BlockHitResult(net.minecraft.world.phys.Vec3.atCenterOf(at),net.minecraft.core.Direction.UP,at,false));
                    require(player.getVehicle() instanceof NervCommandSeatEntity,"Could not sit");seat=(NervCommandSeatEntity)player.getVehicle();
                }
                require(player.getVehicle()==seat&&seat.isAlive(),"Chair discarded its occupant");
                if(++sitting>=640){player.stopRiding();seatsFinished=true;ProjectSeele.LOGGER.info("R28 chair stayed mounted for {} ticks",sitting);}
                return;
            }
            var eva=EvaLogisticsDirector.canonicalUnit(level,1);if(eva==null)return;
            if(eva.isCarrierPowerConnected())
            {
                rackFrames++;require(eva.getUmbilicalAnchor()==null,"Rack power must not use a fixed underground pylon");
                if(eva.getPowerTicks()>=eva.getPowerCapacityTicks()-1)rackCharged=true;
            }
            if(eva.getLaunchPhase()==EvaUnit01Entity.LAUNCH_ASCENT)
            {
                ascentFrames++;if(firstAscentTicks<0)firstAscentTicks=eva.getLaunchTicks();
                if(ascentFrames==1)ascentStart=lastAscent=eva.getY();
                double dy=eva.getY()-lastAscent;lastAscent=eva.getY();
                if(ascentFrames<=13){earlyRise=eva.getY()-ascentStart;earlySpeed=Math.max(earlySpeed,dy);}
                if(ascentFrames>=50&&ascentFrames<=125)climbSpeed=Math.max(climbSpeed,dy);
                require(eva.isCarrierPowerConnected(),"Rack feed lost during catapult ascent");
            }
            if(FactoryR20Review.R29&&age%20==0)
                tallGate|=level.getEntitiesOfClass(NervHangarDoorEntity.class,new net.minecraft.world.phys.AABB(10,-445,-217,50,-435,-209),g->g.getVariant()==1&&Math.abs(g.visualHeight()-72)<.01).size()==1;
            if(eva.getY()>=80&&eva.getLaunchPhase()!=EvaUnit01Entity.LAUNCH_ASCENT&&eva.getUmbilicalAnchor()!=null)
            {require(eva.getUmbilicalAnchor().getZ()==3,"Connected obsolete north socket");surfaceFrames++;}
            if(FactoryR20Review.finished)
            {
                require(!Files.exists(world.resolve("r20_factory_failure.txt")),"Factory cycle failed");
                require(rackFrames>100&&rackCharged,"Rack did not recharge");require(FactoryR20Review.R29?firstAscentTicks>=150&&firstAscentTicks<=180:firstAscentTicks>0&&firstAscentTicks<=34,"Catapult duration incorrect");require(surfaceFrames>30,"Surface handoff absent");
                if(FactoryR20Review.R28_VISUAL)
                {
                    require(receivedRifleTracers>=2,"Native rifle shots were not received by client");
                    require(ntwSoundsPlayed>=2,"Client did not resolve and play NTW-20 sounds");
                }
                JsonObject proof=new JsonObject();proof.addProperty("passed",true);proof.addProperty("chair_seated_ticks",sitting);proof.addProperty("rack_power_ticks",rackFrames);proof.addProperty("battery_recharged",rackCharged);proof.addProperty("catapult_ticks",firstAscentTicks);proof.addProperty("ascent_samples",ascentFrames);proof.addProperty("surface_socket_samples",surfaceFrames);
                proof.addProperty("rifle_tracer_packets",receivedRifleTracers);proof.addProperty("visual_weapon_pass",FactoryR20Review.R28_VISUAL);
                proof.addProperty("ntw20_sound_events",ntwSoundsPlayed);
                if(FactoryR20Review.R29)
                {
                    require(earlyRise>50&&earlyRise<110&&earlySpeed>climbSpeed*1.4,"Initial impulse and slower climb were not distinct");
                    require(tallGate,"72m gate model was not present");require(rifleTicks.size()>=18,"Rifle did not sustain the faster cadence");
                    for(int i=1;i<rifleTicks.size();i++)require(rifleTicks.get(i)-rifleTicks.get(i-1)==2,"Unexpected rifle cadence");
                    proof.addProperty("initial_12_tick_rise",earlyRise);proof.addProperty("early_peak_speed",earlySpeed);proof.addProperty("climb_peak_speed",climbSpeed);proof.addProperty("rifle_server_shots",rifleTicks.size());proof.addProperty("rifle_interval_ticks",2);proof.addProperty("gate_height",72);
                }
                Files.writeString(world.resolve(FactoryR20Review.R29?"r29_field_pass.json":"r28_field_pass.json"),proof.toString());saved=true;ProjectSeele.LOGGER.info("R28 FIELD PASS {}",proof);
            }
        }
        catch(Exception e)
        {
            ProjectSeele.LOGGER.error("R28 FIELD REVIEW FAILED",e);try{Files.writeString(world.resolve(FactoryR20Review.R29?"r29_field_failure.txt":"r28_field_failure.txt"),e.toString());}catch(Exception ignored){}
            saved=true;FactoryR20Review.finished=true;
        }
    }
    private FieldR28Review(){}
}
