package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.capability.EvaPilotCapability;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.world.EvaMotionLabDirector;
import net.minecraft.core.BlockPos;
import net.minecraft.network.protocol.game.ClientboundTeleportEntityPacket;
import net.minecraft.server.level.*;
import net.minecraft.world.level.*;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.ForgeMod;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Tests actual client-driven motion, native collision and damage in the disposable lab. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class EvaMobilityR08Review
{
    public static final boolean ENABLED="r08-mobility".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile boolean finished,jump;
    public static volatile int forward;
    public static volatile int unitId;
    public static volatile boolean clientTracked,clientMounted;
    public static volatile String clientStatus="waiting";
    private static boolean mountPending;
    private static int age,stage,ticks,jumpCase,jumpStart=-1,initialSequence;
    private static ServerPlayer pilot;private static EvaUnit01Entity eva;
    private static final JsonArray checks=new JsonArray(),jumps=new JsonArray(),trace=new JsonArray();
    private static double peak,maxDeviation;private static float pilotHealth,hullHealth;
    private static final TicketType<ChunkPos> TICKET=TicketType.create("r08_mobility_review",Comparator.comparingLong(ChunkPos::toLong),100);
    private static void check(String name,boolean pass,String detail)
    {
        JsonObject r=new JsonObject();r.addProperty("name",name);r.addProperty("passed",pass);r.addProperty("detail",detail);checks.add(r);
        if(!pass)throw new IllegalStateException(name+": "+detail);
        ProjectSeele.LOGGER.info("R08 MOBILITY PASS {} {}",name,detail);
    }
    private static void place(ServerLevel level,double x,double z)
    {
        forward=0;jump=false;pilot.stopRiding();eva.prepareForMotionLab();eva.setNoGravity(false);
        eva.moveTo(x,-60,z,0,0);eva.yRotO=eva.yBodyRot=eva.yHeadRot=0;eva.setDeltaMovement(Vec3.ZERO);eva.setOnGround(true);eva.fallDistance=0;
        for(var player:level.players())player.connection.send(new ClientboundTeleportEntityPacket(eva));
        pilot.teleportTo(level,x,-58,z+20,0,0);pilot.fallDistance=0;unitId=eva.getId();clientTracked=false;mountPending=true;
        ticks=0;maxDeviation=0;peak=0;jumpStart=-1;
    }
    private static void terrain(ServerLevel level)
    {
        Block[] props={Blocks.STONE_PRESSURE_PLATE,Blocks.LANTERN,Blocks.FLOWER_POT,Blocks.IRON_BARS,Blocks.OAK_FENCE,Blocks.WHITE_CARPET,Blocks.RAIL};
        for(int i=0;i<props.length;i++)for(int x=-77;x<=-63;x+=2)
            level.setBlock(new BlockPos(x,-60,-30+i*9),props[i].defaultBlockState(),2);
        for(BlockPos pos:BlockPos.betweenClosed(-92,-60,45,-48,-53,47))level.setBlock(pos,Blocks.STONE_BRICKS.defaultBlockState(),2);
        for(BlockPos pos:BlockPos.betweenClosed(55,-60,-10,88,-60,22))level.setBlock(pos,Blocks.SMOOTH_STONE_SLAB.defaultBlockState(),2);
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;var server=event.getServer();
        if(server.getPlayerList().getPlayers().isEmpty()||++age<100)return;
        Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_EVA_MOBILITY_REVIEW_R08"))throw new IllegalStateException("R08 mobility is laboratory-only");
        ServerLevel level=server.overworld();level.resetEmptyTime();
        try
        {
            if(age%20==0)for(int x=-10;x<=10;x++)for(int z=-10;z<=10;z++){ChunkPos p=new ChunkPos(x,z);level.getChunkSource().addRegionTicket(TICKET,p,2,p);}
            if(stage==0)
            {
                pilot=server.getPlayerList().getPlayers().get(0);if(!pilot.isAlive())pilot=server.getPlayerList().respawn(pilot,false);
                pilot.stopRiding();pilot.setGameMode(GameType.SURVIVAL);pilot.setHealth(pilot.getMaxHealth());pilot.getFoodData().setFoodLevel(20);server.setFlightAllowed(true);
                pilot.getCapability(EvaPilotCapability.DATA).ifPresent(d->d.setSynchronization(100));
                EvaMotionLabDirector.setup(level,true);eva=EvaMotionLabDirector.unit(level,1);check("managed_unit",eva!=null,"fresh disposable lab unit");
                terrain(level);place(level,-70.5,-52.5);stage=1;return;
            }
            ticks++;if(!pilot.isAlive())throw new IllegalStateException("Review pilot died");
            if(mountPending)
            {
                if(ticks>=20&&clientTracked)
                {check("native_boarding_stage_"+stage,eva.boardFromExternalPlug(pilot,100),"tracked entity "+eva.getId());mountPending=false;ticks=0;}
                else if(ticks>200)throw new IllegalStateException("Client did not track review airframe");
                return;
            }
            if(ticks%60==0)ProjectSeele.LOGGER.info("R08 CONTROL TRACE stage={} id={} passenger={} powered={} y={} client={}",stage,eva.getId(),eva.getControllingPassenger(),eva.isPoweredOn(),eva.position(),clientStatus);
            if(ticks%2==0){JsonArray row=new JsonArray();row.add(stage);row.add(ticks);row.add(eva.getX());row.add(eva.getY());row.add(eva.getZ());row.add(eva.getDeltaMovement().y);trace.add(row);}
            if(stage==1)
            {
                if(ticks==30){check("client_driver",clientMounted,clientStatus);forward=1;}
                if(ticks>30)maxDeviation=Math.max(maxDeviation,Math.abs(eva.getY()+60));
                if(ticks==190)
                {
                    forward=0;check("small_street_props",eva.getZ()>30&&maxDeviation<.15,"end="+eva.position()+", max vertical disturbance="+maxDeviation);
                    check("full_wall_retained",eva.getBoundingBox().maxZ<=45.01,"solid eight-block wall still blocks the airframe");
                    place(level,71.5,-40.5);stage=2;return;
                }
            }
            if(stage==2)
            {
                if(ticks==30)forward=1;
                if(eva.getZ()>=3&&ticks>30)
                {
                    forward=0;check("structural_slab_retained",Math.abs(eva.getY()+59.5)<.05,eva.position().toString());
                    place(level,.5,-80.5);stage=3;return;
                }
            }
            if(stage==3)
            {
                if(ticks==30)
                {
                    check("gravity_profile",Math.abs(eva.getAttributeValue(ForgeMod.ENTITY_GRAVITY.get())-.18)<.00001,"0.18 blocks/tick squared");
                    if(eva.isAtFieldOn())eva.toggleAtField(pilot);float p=pilot.getHealth(),h=eva.getHealth();eva.hurt(level.damageSources().generic(),40);
                    check("pilot_isolated_from_hull_damage",eva.getHealth()<h&&pilot.getHealth()==p,"sync="+EvaPilotCapability.synchronization(pilot)+", hull="+h+"->"+eva.getHealth()+", pilot="+p+"->"+pilot.getHealth());
                    h=eva.getHealth();eva.causeFallDamage(160,1,level.damageSources().fall());eva.hurt(level.damageSources().fall(),200);
                    check("fall_damage_rejected",eva.getHealth()==h,"native landing callback and explicit fall DamageSource");
                    place(level,.5,-80.5);stage=4;return;
                }
            }
            if(stage==4)
            {
                if(ticks==25&&jumpCase==1)eva.smashAttack(pilot);
                if(ticks==30){initialSequence=eva.getJumpSequence();pilotHealth=pilot.getHealth();hullHealth=eva.getHealth();jump=true;forward=jumpCase==2?1:0;}
                if(ticks==36)jump=false;
                if(eva.getJumpSequence()!=initialSequence&&jumpStart<0&&ticks>=30)jumpStart=ticks;
                if(jumpStart>=0)peak=Math.max(peak,eva.getY()+60);
                if(ticks==48){check("jump_"+jumpCase+"/input_ack",jumpStart>=0,"real Space input acknowledged");if(jumpCase==1)check("jump_interrupts_ground_heavy",!eva.isHeavyMotionActive(),"ground heavy releases pose ownership");}
                if(jumpStart>=0&&peak>10&&eva.onGround()&&eva.getY()<-59.85&&ticks-jumpStart>20)
                {
                    // aiStep applies 0.98 Y damping before travel applies gravity and
                    // a second 0.98 damping. That native recurrence predicts 40.274,
                    // not the 50.969 of a travel-only model (old profile: 37.575).
                    int flight=ticks-jumpStart;check("jump_"+jumpCase+"/trajectory",Math.abs(peak-40.2743)<1.0&&flight<=57,"peak="+peak+", air ticks="+flight);
                    check("jump_"+jumpCase+"/safe_landing",pilot.getHealth()==pilotHealth&&eva.getHealth()==hullHealth,"pilot and hull health preserved");
                    JsonObject r=new JsonObject();r.addProperty("case",jumpCase);r.addProperty("height",peak);r.addProperty("ticks",flight);jumps.add(r);forward=0;
                    if(++jumpCase<3){place(level,.5,-80.5);return;}
                    finish(level,world,null);return;
                }
            }
            if(ticks>350)throw new IllegalStateException("Mobility timeout stage="+stage+" position="+eva.position());
        }
        catch(Exception failure){finish(level,world,failure);}
    }
    private static void finish(ServerLevel level,Path world,Exception failure)
    {
        forward=0;jump=false;finished=true;if(pilot!=null){pilot.stopRiding();pilot.setGameMode(GameType.CREATIVE);pilot.teleportTo(level,.5,-59,-150.5,0,0);pilot.fallDistance=0;}
        JsonObject result=new JsonObject();result.addProperty("passed",failure==null);result.add("checks",checks);result.add("jumps",jumps);result.add("trace",trace);
        if(failure!=null){result.addProperty("failure",failure.toString());ProjectSeele.LOGGER.error("R08 MOBILITY REVIEW FAILED",failure);}
        try{Files.writeString(world.resolve("r08_mobility_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(result));}catch(Exception ignored){}
    }
}
