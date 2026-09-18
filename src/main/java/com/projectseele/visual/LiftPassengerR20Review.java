package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.world.*;
import com.supermartijn642.movingelevators.blocks.ControllerBlockEntity;
import net.minecraft.server.level.*;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Real native cabin trips with a moving, corner-standing human passenger. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class LiftPassengerR20Review
{
    private static final boolean DESCENT="r22-lift-descend".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final boolean ALL="r22-lifts-all".equals(System.getProperty("projectseele.regionalBuild",""));
    public static final boolean R22=ALL||DESCENT||"r22-lifts".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final boolean R21="r21-lifts".equals(System.getProperty("projectseele.regionalBuild",""));
    public static final boolean ENABLED=R22||R21||Set.of("r20-lift","r20-lift-rest").contains(System.getProperty("projectseele.regionalBuild",""));
    public static volatile net.minecraft.core.BlockPos controllerPosition;
    public static volatile boolean clientReady,finished,moving;
    public static volatile int tripAge;
    private static int age,index=DESCENT?3:R21?2:"r20-lift-rest".equals(System.getProperty("projectseele.regionalBuild",""))?4:0,stage,timer;
    private static final JsonArray results=new JsonArray();
    private static final JsonArray damageEvents=new JsonArray();
    @SubscribeEvent public static void hurt(net.minecraftforge.event.entity.living.LivingHurtEvent e)
    {
        if(!ENABLED||finished||!(e.getEntity() instanceof ServerPlayer p))return;
        JsonObject r=new JsonObject();r.addProperty("source",e.getSource().getMsgId());r.addProperty("amount",e.getAmount());r.addProperty("stage",stage);r.addProperty("timer",timer);r.addProperty("lift",IDS[Math.min(index,IDS.length-1)]);r.addProperty("position",p.position().toString());r.addProperty("fallDistance",p.fallDistance);
        JsonArray blocks=new JsonArray();for(var q:net.minecraft.core.BlockPos.betweenClosed(p.blockPosition().offset(-1,0,-1),p.blockPosition().offset(1,2,1)))if(!p.level().getBlockState(q).isAir())blocks.add(q.toShortString()+" "+p.level().getBlockState(q));r.add("nearbyBlocks",blocks);damageEvents.add(r);
        ProjectSeele.LOGGER.warn("R21 LIFT DAMAGE {}",r);
    }
    private static double minimumFloorError=100,maximumWallOverflow;
    private static final String[] IDS={S20PhysicalElevatorDirector.COMMAND_REAR_LIFT_ID,S20PhysicalElevatorDirector.COMMAND_REAR_LIFT_ID,S20PhysicalElevatorDirector.SURFACE_TRANSIT_LIFT_ID,S20PhysicalElevatorDirector.SURFACE_TRANSIT_LIFT_ID,NervLiftPassengerSync.GATEWAY,NervLiftPassengerSync.GATEWAY,S20PhysicalElevatorDirector.COMPACT_CAGE_LIFT_ID,S20PhysicalElevatorDirector.COMPACT_CAGE_LIFT_ID,S20PhysicalElevatorDirector.COMMANDER_OFFICE_LIFT_ID,S20PhysicalElevatorDirector.COMMANDER_OFFICE_LIFT_ID};
    private static final int[] FROM={-566,-448,-442,81,-466,81,-442,-370,-388,-340},TO={-448,-566,81,-442,81,-466,-370,-394,-340,-388};
    private static void require(boolean value,String why){if(!value)throw new IllegalStateException(why);}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent e)
    {
        if(!ENABLED||finished||e.phase!=TickEvent.Phase.END||!clientReady||e.getServer().getPlayerList().getPlayers().isEmpty())return;
        Path world=e.getServer().getWorldPath(LevelResource.ROOT).normalize();require(world.getFileName().toString().equals(R22?"SEELE_R22_REVIEW":R21?"SEELE_R21_REVIEW":"SEELE_R20_REVIEW"),"R20/R21/R22 review boundary");
        var player=e.getServer().getPlayerList().getPlayers().get(0);var level=e.getServer().getLevel(FacilitySchemaV2.DIMENSION);
        try
        {
            if(++age>15000)throw new IllegalStateException("R20 lift suite timeout");
            if(DESCENT&&index==4){write(world,"");finished=true;return;}
            if(R21||R22){FROM[3]=75;TO[2]=75;if(index==4&&!ALL)index=6;}
            if(index==IDS.length||R21&&index==8){write(world,"");finished=true;return;}
            var spec=NervLiftPassengerSync.managedLifts(level).stream().filter(s->s.id().equals(IDS[index])).findFirst().orElseThrow();
            var from=spec.stops().stream().filter(s->s.walkY()==FROM[index]).findFirst().orElseThrow();var to=spec.stops().stream().filter(s->s.walkY()==TO[index]).findFirst().orElseThrow();
            var base=S20MovingElevatorsAdapter.controllerPosition(spec,spec.lower());level.getChunkAt(base);
            controllerPosition=base;
            if(spec.id().equals(NervLiftPassengerSync.GATEWAY)){level.getChunkAt(RegionalGatewayDirector.controllerPos(81));if(stage==0)RegionalGatewayDirector.commission(level);}
            if(!(level.getBlockEntity(base) instanceof ControllerBlockEntity c)||c.getGroup()==null)return;
            var group=c.getGroup();timer++;
            if(stage==0)
            {
                ProjectSeele.LOGGER.info("R20 lift setup {} {} -> {}",spec.id(),FROM[index],TO[index]);
                var card=new net.minecraft.world.item.ItemStack(com.projectseele.registry.ModItems.TERMINAL_DOGMA_ACCESS_CARD.get());
                if(!player.getInventory().contains(card))player.getInventory().add(card);
                player.setGameMode(GameType.CREATIVE);player.getAbilities().flying=false;player.onUpdateAbilities();
                player.teleportTo(level,from.cabinCentre().getX()+.5,from.walkY(),from.cabinCentre().getZ()+(spec.id().equals(NervLiftPassengerSync.GATEWAY)?-11.5:7.5),180,0);
                if(spec.id().equals(NervLiftPassengerSync.GATEWAY))RegionalGatewayDirector.request(level,FROM[index],player);else group.onDisplayPress(FROM[index],0,player);stage=1;timer=0;
            }
            else if(stage==1)
            {
                if(group.isMoving()||!NervLiftPassengerSync.carPresent(level,spec,from)){require(timer<1800,"Empty cabin failed to arrive");return;}
                if(timer<30)return;
                double half=group.getCageSizeX()*.5D;
                player.teleportTo(level,from.cabinCentre().getX()+.5+half-1.36,from.walkY(),from.cabinCentre().getZ()+.5+half-1.36,180,0);
                player.setHealth(player.getMaxHealth());
                player.setGameMode(GameType.SURVIVAL);player.getAbilities().flying=false;player.onUpdateAbilities();
                stage=2;timer=0;minimumFloorError=100;maximumWallOverflow=0;
            }
            else if(stage==2)
            {
                // Start immediately after entry, including the old five-tick gap.
                if(timer==1){player.setGameMode(GameType.CREATIVE);if(spec.id().equals(NervLiftPassengerSync.GATEWAY))
                    {
                        boolean accepted=RegionalGatewayDirector.request(level,TO[index],player);
                        if(!accepted)
                        {
                            var anchor=group.getCageAnchorBlockPos(FROM[index]);var target=group.getCageAnchorBlockPos(TO[index]);var blocks=new TreeMap<String,Integer>();
                            for(var q:net.minecraft.core.BlockPos.betweenClosed(target,target.offset(14,8,14)))if(!level.getBlockState(q).isAir())blocks.merge(q.toShortString()+" "+level.getBlockState(q),1,Integer::sum);
                            ProjectSeele.LOGGER.error("R20 gateway diagnostic available={} sourceRule={} nativeCapture={} destinationBlocks={} controller={}",group.isCageAvailableAt(group.getFloorNumber(FROM[index]),true,player),S20MovingElevatorsAdapter.validCommandCageSource(level,group,anchor),com.supermartijn642.movingelevators.elevator.ElevatorCage.canCreateCage(level,anchor,15,9,15,player),blocks,level.getBlockEntity(RegionalGatewayDirector.controllerPos(TO[index])));
                        }
                    }
                    else group.onDisplayPress(TO[index],0,player);player.setGameMode(GameType.SURVIVAL);}
                if(group.isMoving()){stage=3;timer=0;moving=true;}
                require(timer<140,"Loaded cabin did not depart");
            }
            else if(stage==3)
            {
                tripAge=timer;
                if(group.isMoving())
                {
                    AABB b=group.getCage().bounds.move(group.getCageAnchorPos(group.getCurrentY()));double floor=b.minY+1;
                    double err=player.getY()-floor;minimumFloorError=Math.min(minimumFloorError,err);
                    double over=Math.max(Math.max(b.minX-player.getX(),player.getX()-b.maxX),Math.max(b.minZ-player.getZ(),player.getZ()-b.maxZ));maximumWallOverflow=Math.max(maximumWallOverflow,over);
                    require(err>-.35,"Passenger escaped below native floor: "+err);require(over<.35,"Passenger escaped lateral cabin: "+over);require(player.isAlive(),"Passenger died");
                }
                else
                {
                    moving=false;require(NervLiftPassengerSync.carPresent(level,spec,to),"Wrong arrival floor");
                    require(Math.abs(player.getY()-to.walkY())<1.8,"Passenger did not arrive with cabin");
                    require(level.noCollision(player,player.getBoundingBox().deflate(.03)),"Arrived inside cabin wall");require(player.getHealth()>=player.getMaxHealth()-.01,"Passenger took collision or fall damage");
                    JsonObject r=new JsonObject();r.addProperty("lift",IDS[index]);r.addProperty("from",FROM[index]);r.addProperty("to",TO[index]);r.addProperty("minFloorError",minimumFloorError);r.addProperty("maxLateralOverflow",maximumWallOverflow);r.addProperty("ticks",timer);r.addProperty("passed",true);results.add(r);
                    ProjectSeele.LOGGER.info("R20 native lift passenger pass {} {} -> {}",IDS[index],FROM[index],TO[index]);index++;stage=0;timer=0;
                }
                require(timer<1800,"Passenger trip stalled");
            }
        }
        catch(Exception failure)
        {
            ProjectSeele.LOGGER.error("R20 lift passenger review failed",failure);moving=false;finished=true;write(world,failure.toString());
        }
    }
    private static void write(Path world,String error)
    {
        try{JsonObject r=new JsonObject();r.addProperty("error",error);r.add("trips",results);r.add("damage",damageEvents);Files.writeString(world.resolve("r20_lift_review.json"),r.toString());}catch(Exception x){throw new IllegalStateException(x);}
    }
}
