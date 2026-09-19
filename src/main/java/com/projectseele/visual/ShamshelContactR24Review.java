package com.projectseele.visual;

import com.google.gson.*;
import com.mojang.authlib.GameProfile;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.registry.ModEntities;
import com.projectseele.world.FacilitySchemaV2;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Difficulty;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.vehicle.Boat;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Calls the real server attack on a registered player; restores every fixture. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class ShamshelContactR24Review
{
    private static final boolean ENABLED="r24-whip".equals(System.getProperty("projectseele.regionalBuild",""));
    private static int age;private static boolean done;
    private static final Vec3 ORIGIN=new Vec3(2048,180,2048);
    private static final JsonObject checks=new JsonObject();
    private static final Map<BlockPos,BlockState> restore=new LinkedHashMap<>();
    private static ShamshelEntity actor;private static ServerPlayer victim;private static Boat seat;
    private static void check(String name,boolean value){checks.addProperty(name,value);if(!value)throw new IllegalStateException(name);}
    private static ShamshelEntity fresh(ServerLevel level,int side)
    {
        var mob=ModEntities.SHAMSHEL.get().create(level);mob.setNoAi(true);mob.setNoGravity(true);mob.moveTo(ORIGIN.x,ORIGIN.y,ORIGIN.z,0,0);
        CompoundTag tag=new CompoundTag();mob.saveWithoutId(tag);tag.putInt("SweepAge",0);tag.putInt("SweepSide",side);tag.putFloat("SweepYaw",0);mob.load(tag);
        mob.setDeltaMovement(Vec3.ZERO);return mob;
    }
    private static Vec3 hitPosition(ShamshelEntity mob)
    {
        var points=ShamshelWhipMotion.points(mob,17,1);
        return points.get(3).lerp(points.get(4),.5).add(0,-.9,0);
    }
    private static float run(ServerLevel level,String name,int side,boolean evade,boolean wall,boolean passenger,boolean reload)
    {
        actor=fresh(level,side);check(name+"_registered",level.addFreshEntity(actor));
        Vec3 target=hitPosition(actor);victim.stopRiding();victim.setPos(evade?target.add(70,0,0):target);victim.setDeltaMovement(Vec3.ZERO);
        victim.setHealth(200);victim.invulnerableTime=0;victim.setInvulnerable(false);
        if(passenger)
        {
            seat=new Boat(level,target.x,target.y,target.z);seat.setNoGravity(true);check(name+"_seat",level.addFreshEntity(seat));
            check(name+"_passenger",victim.startRiding(seat,true));
        }
        if(wall)
        {
            var centre=BlockPos.containing(target.add(0,.9,0));
            for(int dx=-3;dx<=3;dx++)for(int dy=-3;dy<=3;dy++)for(int dz=-3;dz<=3;dz++)
            {
                if(Math.max(Math.max(Math.abs(dx),Math.abs(dy)),Math.abs(dz))!=3)continue;
                var q=centre.offset(dx,dy,dz);var old=level.getBlockState(q);
                if(!old.isAir())throw new IllegalStateException("Wall fixture would replace existing block at "+q);
                restore.put(q,old);level.setBlock(q,Blocks.STONE.defaultBlockState(),3);
            }
        }
        for(int i=0;i<ShamshelWhipMotion.CYCLE;i++)
        {
            actor.tick();
            if(reload&&i==18)
            {
                var tag=new CompoundTag();actor.saveWithoutId(tag);
                check(name+"_saved_hit",tag.getList("SweepHits",8).size()==1);
                actor.discard();actor=ModEntities.SHAMSHEL.get().create(level);actor.load(tag);
                // A full disk restore retains this UUID; synchronous fixture
                // uses a new ID to avoid the entity manager's deferred removal.
                actor.setUUID(UUID.randomUUID());check(name+"_reloaded",level.addFreshEntity(actor));victim.invulnerableTime=0;
            }
        }
        float damage=200-victim.getHealth();checks.addProperty(name+"_damage",damage);
        var tag=new CompoundTag();actor.saveWithoutId(tag);checks.addProperty(name+"_unique_hits",tag.getList("SweepHits",8).size());
        if(evade||wall||passenger)check(name+"_no_hit",damage==0&&tag.getList("SweepHits",8).isEmpty());
        else check(name+"_one_hit",damage>0&&damage<=45&&tag.getList("SweepHits",8).size()==1);
        victim.stopRiding();if(seat!=null){seat.discard();seat=null;}actor.discard();actor=null;
        for(var entry:restore.entrySet())level.setBlock(entry.getKey(),entry.getValue(),3);
        for(var entry:restore.entrySet())check(name+"_wall_restored",level.getBlockState(entry.getKey()).equals(entry.getValue()));
        restore.clear();return damage;
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END||++age<100)return;
        var server=event.getServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_R24_TV_REVIEW"))throw new IllegalStateException("Wrong whip review world");
        var level=server.getLevel(FacilitySchemaV2.DIMENSION);if(level==null)return;
        Difficulty difficulty=level.getDifficulty();String failure="";
        try
        {
            server.setDifficulty(Difficulty.NORMAL,true);
            for(int x=124;x<=132;x++)for(int z=124;z<=132;z++)level.getChunk(x,z);
            var profile=new GameProfile(UUID.fromString("24191919-0600-4000-9000-000000000024"),"R24 whip probe");
            victim=new ServerPlayer(server,level,profile);
            // Forge FakePlayer deliberately rejects every damage source.
            // Borrow only its no-network connection; use the real player
            // damage implementation and let native spawn grace expire.
            victim.connection=FakePlayerFactory.get(level,profile).connection;
            victim.setGameMode(GameType.SURVIVAL);victim.setNoGravity(true);victim.getAttribute(Attributes.MAX_HEALTH).setBaseValue(200);victim.setHealth(200);
            for(int n=0;n<80;n++)victim.tick();
            level.addNewPlayer(victim);
            for(int side:new int[]{-1,1})
            {
                String s=side<0?"left":"right";
                run(level,s+"_contact",side,false,false,false,false);
                run(level,s+"_evaded",side,true,false,false,false);
                run(level,s+"_wall",side,false,true,false,false);
                run(level,s+"_passenger",side,false,false,true,false);
                run(level,s+"_restore",side,false,false,false,true);
            }
        }
        catch(Exception error){failure=error.toString();ProjectSeele.LOGGER.error("R24 native whip contact review",error);}
        finally
        {
            if(actor!=null)actor.discard();if(seat!=null)seat.discard();
            if(victim!=null){victim.stopRiding();victim.discard();}
            restore.forEach((p,s)->level.setBlock(p,s,3));server.setDifficulty(difficulty,true);
            var report=new JsonObject();report.addProperty("passed",failure.isEmpty());report.addProperty("error",failure);report.add("checks",checks);
            report.addProperty("method","real Shamshel.tick and native query/clip/hurt against a registered headless ServerPlayer with a dummy connection; native spawn grace expired; synchronous controlled sweep; temporary air-only wall restored");
            try{Files.writeString(world.resolve("r24_whip_contact_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception error){ProjectSeele.LOGGER.error("Whip report write failed",error);}
            done=true;server.halt(false);
        }
    }
    private ShamshelContactR24Review(){}
}
