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
            require(world.getFileName().toString().equals("SEELE_FIELD_R28_REVIEW"),"Review boundary");
            ServerLevel level=server.getLevel(FacilitySchemaV2.DIMENSION);ServerPlayer player=server.getPlayerList().getPlayers().get(0);age++;
            if(!seatsFinished)
            {
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
                require(eva.isCarrierPowerConnected(),"Rack feed lost during catapult ascent");
            }
            if(eva.getY()>=80&&eva.getLaunchPhase()!=EvaUnit01Entity.LAUNCH_ASCENT&&eva.getUmbilicalAnchor()!=null)
            {require(eva.getUmbilicalAnchor().getZ()==3,"Connected obsolete north socket");surfaceFrames++;}
            if(FactoryR20Review.finished)
            {
                require(!Files.exists(world.resolve("r20_factory_failure.txt")),"Factory cycle failed");
                require(rackFrames>100&&rackCharged,"Rack did not recharge");require(firstAscentTicks>0&&firstAscentTicks<=34,"Catapult was not accelerated");require(surfaceFrames>30,"Surface handoff absent");
                if(FactoryR20Review.R28_VISUAL)
                {
                    require(receivedRifleTracers>=2,"Native rifle shots were not received by client");
                    require(ntwSoundsPlayed>=2,"Client did not resolve and play NTW-20 sounds");
                }
                JsonObject proof=new JsonObject();proof.addProperty("passed",true);proof.addProperty("chair_seated_ticks",sitting);proof.addProperty("rack_power_ticks",rackFrames);proof.addProperty("battery_recharged",rackCharged);proof.addProperty("catapult_ticks",firstAscentTicks);proof.addProperty("ascent_samples",ascentFrames);proof.addProperty("surface_socket_samples",surfaceFrames);
                proof.addProperty("rifle_tracer_packets",receivedRifleTracers);proof.addProperty("visual_weapon_pass",FactoryR20Review.R28_VISUAL);
                proof.addProperty("ntw20_sound_events",ntwSoundsPlayed);
                Files.writeString(world.resolve("r28_field_pass.json"),proof.toString());saved=true;ProjectSeele.LOGGER.info("R28 FIELD PASS {}",proof);
            }
        }
        catch(Exception e)
        {
            ProjectSeele.LOGGER.error("R28 FIELD REVIEW FAILED",e);try{Files.writeString(world.resolve("r28_field_failure.txt"),e.toString());}catch(Exception ignored){}
            saved=true;FactoryR20Review.finished=true;
        }
    }
    private FieldR28Review(){}
}
