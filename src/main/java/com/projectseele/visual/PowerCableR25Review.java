package com.projectseele.visual;

import com.google.gson.*;
import com.mojang.authlib.GameProfile;
import com.projectseele.ProjectSeele;
import com.projectseele.config.SeeleConfig;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.registry.*;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.*;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.UUID;

/** Disposable native tick, damage and serialization checks for the long reel. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class PowerCableR25Review
{
    private static final boolean ENABLED="r25-power".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final BlockPos REEL=new BlockPos(0,250,0);
    private static final JsonObject checks=new JsonObject();
    private static int age,stage,timer;private static boolean finished;
    private static EvaUnit01Entity eva;private static ServerPlayer pilot;private static CompoundTag saved;
    private static void check(String key,boolean value){checks.addProperty(key,value);if(!value)throw new IllegalStateException(key);}
    private static void ticket(ServerLevel level,BlockPos pos)
    {var c=new ChunkPos(pos);level.getChunkSource().addRegionTicket(TicketType.PORTAL,c,2,pos);level.getChunk(c.x,c.z);}
    private static void move(ServerLevel level,double x)
    {ticket(level,BlockPos.containing(x,250,.5));eva.moveTo(x,250,.5,0,0);eva.setDeltaMovement(Vec3.ZERO);}
    private static void fresh(ServerLevel level)
    {
        if(eva!=null){pilot.stopRiding();eva.discard();}
        eva=ModEntities.EVA_UNIT01.get().create(level);eva.prepareForMotionLab();eva.setNoAi(true);eva.setNoGravity(true);
        move(level,8.5);check("fixture_spawn",level.addFreshEntity(eva));pilot.setPos(eva.position());check("fixture_board",eva.boardFromExternalPlug(pilot,100));
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_POWER_R25_REVIEW"))throw new IllegalStateException("Power fixture refuses a non-laboratory world");
        var level=server.overworld();level.resetEmptyTime();
        try
        {
            if(++age<80)return;if(age>900)throw new IllegalStateException("Power fixture timeout");timer++;
            if(stage==0)
            {
                check("configured_long_range",SeeleConfig.UMBILICAL_RANGE.get()==768);
                ticket(level,REEL);level.setBlock(REEL,ModBlocks.UMBILICAL_PYLON.get().defaultBlockState(),3);
                pilot=FakePlayerFactory.get(level,new GameProfile(UUID.fromString("2361a6c5-b538-48d8-822a-5eca40a49378"),"[R25 cable]"));
                pilot.getCapability(com.projectseele.capability.EvaPilotCapability.DATA).ifPresent(data->data.setSynchronization(100));
                fresh(level);stage=1;timer=0;
            }
            else if(stage==1&&timer>60)
            {
                var state=new JsonObject();state.addProperty("eva_ticks",eva.tickCount);state.addProperty("position",eva.position().toString());
                state.addProperty("plug_inserted",eva.isEntryPlugInserted());state.addProperty("pilot",String.valueOf(eva.getPilotEntity()));
                state.addProperty("reel",String.valueOf(level.getBlockEntity(REEL)));state.addProperty("nearest",String.valueOf(com.projectseele.world.UmbilicalPylonBlockEntity.findNearest(level,eva.position(),768)));
                state.addProperty("connected",eva.isUmbilicalConnected());state.addProperty("severed",eva.isUmbilicalSevered());state.addProperty("anchor",String.valueOf(eva.getUmbilicalAnchor()));checks.add("initial_state",state);
                check("native_reel_connection",eva.isUmbilicalConnected()&&REEL.equals(eva.getUmbilicalAnchor()));move(level,600.5);stage=2;timer=0;
            }
            else if(stage==2&&timer>180)
            {
                check("connected_600_blocks_away",eva.isUmbilicalConnected()&&!eva.isUmbilicalSevered());
                check("remote_reel_chunk_retained",level.hasChunkAt(REEL)&&level.getBlockEntity(REEL)!=null);
                saved=eva.saveWithoutId(new CompoundTag());check("anchor_saved",saved.contains("SeeleUmbilicalAnchor"));
                pilot.stopRiding();eva.discard();stage=3;timer=0;
            }
            else if(stage==3&&timer>3)
            {
                eva=ModEntities.EVA_UNIT01.get().create(level);eva.load(saved);
                check("anchor_restored_before_reboarding",REEL.equals(eva.getUmbilicalAnchor()));
                eva.setNoAi(true);eva.setNoGravity(true);check("restored_spawn",level.addFreshEntity(eva));
                pilot.setPos(eva.position());check("restored_board",eva.boardFromExternalPlug(pilot,100));stage=4;timer=0;
            }
            else if(stage==4&&timer>30)
            {
                check("connected_after_reload",eva.isUmbilicalConnected());
                if(eva.isAtFieldOn())eva.toggleAtField(pilot);
                eva.invulnerableTime=0;float hp=eva.getHealth();boolean accepted=eva.hurt(level.damageSources().generic(),4);
                check("hull_hit_severs_cable",accepted&&eva.getHealth()<hp&&!eva.isUmbilicalConnected()&&eva.isUmbilicalSevered());
                stage=5;timer=0;
            }
            else if(stage==5&&timer>35)
            {check("cut_cable_does_not_auto_reconnect",!eva.isUmbilicalConnected());fresh(level);stage=6;timer=0;}
            else if(stage==6&&timer>30)
            {check("second_reel_connection",eva.isUmbilicalConnected());move(level,780.5);stage=7;timer=0;}
            else if(stage==7&&timer>30)
            {
                check("out_of_range_disconnect",!eva.isUmbilicalConnected()&&eva.isUmbilicalSevered());
                check("internal_battery_remains",eva.getPowerTicks()>0);
                pilot.stopRiding();eva.discard();finish(server,world,"");
            }
        }
        catch(Exception failure){ProjectSeele.LOGGER.error("R25 cable fixture failed",failure);finish(server,world,failure.toString());}
    }
    private static void finish(net.minecraft.server.MinecraftServer server,Path world,String error)
    {
        finished=true;var report=new JsonObject();report.addProperty("passed",error.isEmpty());report.addProperty("error",error);report.add("checks",checks);
        try{Files.writeString(world.resolve("r25_power_review.json"),report.toString());}catch(Exception e){throw new IllegalStateException(e);}
        server.halt(false);
    }
    private PowerCableR25Review() {}
}
