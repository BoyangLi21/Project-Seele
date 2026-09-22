package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.entity.*;
import com.projectseele.registry.ModEntities;
import com.projectseele.world.*;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.level.ChunkPos;
import net.minecraftforge.common.util.FakePlayer;
import net.minecraftforge.common.util.FakePlayerFactory;
import com.mojang.authlib.GameProfile;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Native lifecycle regression; temporary actors only, guarded to the disposable review world. */
@Mod.EventBusSubscriber(modid="projectseele")
public final class ShutdownR30Review
{
    private static final boolean ENABLED="r30-shutdown".equals(System.getProperty("projectseele.regionalBuild",""));
    private static int age;private static boolean done;private static EvaPrototypeEntity hull;private static FakePlayer pilot;
    private static EvaUnit01Entity power;private static FakePlayer benchPilot;
    private static final JsonObject report=new JsonObject();
    private static final TicketType<ChunkPos> TICKET=TicketType.create("r30_shutdown_review",java.util.Comparator.comparingLong(ChunkPos::toLong),300);
    private static void check(String label,boolean value){report.addProperty(label,value);if(!value)throw new IllegalStateException(label);}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END)return;var server=event.getServer();
        Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_FIELD_R30_REVIEW"))throw new IllegalStateException("Wrong shutdown review world");
        ServerLevel level=server.getLevel(FacilitySchemaV2.DIMENSION);if(level==null)return;level.resetEmptyTime();
        var chunk=new ChunkPos(22,13);level.getChunkSource().addRegionTicket(TICKET,chunk,3,chunk);
        try
        {
            if(++age<60)return;
            if(age==60)
            {
                level.getChunk(22,13);hull=ModEntities.EVA_PROTOTYPE.get().create(level);hull.prepareForMotionLab();hull.setNoAi(true);hull.moveTo(356.5,81,217.5,0,0);level.addFreshEntity(hull);
                pilot=FakePlayerFactory.get(level,new GameProfile(java.util.UUID.fromString("96084dc2-2b4a-4d28-8bf6-7aacc4070e30"),"R30ReviewPilot"));pilot.moveTo(hull.position());check("pilot_boarded",pilot.startRiding(hull,true));
            }
            if(age==64){if(hull.tickCount<4){age--;return;}check("pilot_remains_seated",hull.getPilotEntity()==pilot);check("initially_powered",hull.isPoweredOn());pilot.stopRiding();}
            if(age==86){report.addProperty("native_hull_ticks",hull.tickCount);report.addProperty("empty_mode",EvaShutdownR30.mode(hull));check("empty_kneeling",EvaShutdownR30.mode(hull)==EvaShutdownR30.EMPTY&&hull.isPilotCrouching()&&!hull.isPoweredOn());check("kneel_pose_finite",EvaShutdownR30.valid(EvaShutdownR30.pose(hull)));}
            if(age==88){hull.hurt(level.damageSources().fellOutOfWorld(),100000);}
            if(age==89){hull.setPos(hull.getX(),155,hull.getZ());hull.setOnGround(false);hull.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);}
            if(age==120)
            {
                check("wreck_persists_at_zero_health",!hull.isRemoved()&&hull.isAlive()&&hull.getHealth()==0&&EvaShutdownR30.wreck(hull));
                report.addProperty("wreck_height_after_air_drop",hull.getY());check("disabled_hull_actually_falls",hull.getY()<145);
                check("wreck_prone_and_unpowered",hull.isPilotProne()&&!hull.isPoweredOn());
                var saved=hull.saveWithoutId(new CompoundTag());var clone=ModEntities.EVA_PROTOTYPE.get().create(level);clone.load(saved);
                check("wreck_reload_preserves_pose",EvaShutdownR30.wreck(clone)&&clone.getHealth()==0&&EvaShutdownR30.pose(clone).equals(EvaShutdownR30.pose(hull)));
                clone.setHealth(clone.getMaxHealth());EvaShutdownR30.tick(clone);check("repair_clears_wreck",!EvaShutdownR30.disabled(clone));
                hull.kill();
                // This unregistered NERV object is deliberately not added to the fleet.
                // It still runs the real native entity/power ticks in this ServerLevel.
                power=ModEntities.EVA_UNIT01.get().create(level);power.prepareForMotionLab();power.moveTo(356.5,100,217.5,0,0);power.setNoAi(true);
                var nbt=power.saveWithoutId(new CompoundTag());nbt.putInt("SeelePowerTicks",3);nbt.putBoolean("SeeleBatterySession",true);nbt.putBoolean("SeeleUmbilicalSevered",true);power.load(nbt);
                benchPilot=FakePlayerFactory.get(level,new GameProfile(java.util.UUID.fromString("6bc83596-2246-4135-a83e-38fa354abe30"),"R30BenchPilot"));benchPilot.startRiding(power,true);
            }
            if(age>120&&age<150)power.tick();
            if(age==150)
            {
                check("admin_kill_removes_wreck",hull.isRemoved());
                check("battery_empty_locks_pose",EvaShutdownR30.mode(power)==EvaShutdownR30.POWER_LOCK&&power.getPowerTicks()==0);
                check("frozen_pose_finite",EvaShutdownR30.valid(EvaShutdownR30.pose(power)));
                check("shutdown_gravity_retained",!power.isNoGravity());
                check("rifle_issued",(power.getArmamentMask()&(1<<EvaUnit01Entity.WEAPON_RIFLE))!=0);benchPilot.stopRiding();power.enterHangarStandby();
                check("recovery_removes_rifle",(power.getArmamentMask()&(1<<EvaUnit01Entity.WEAPON_RIFLE))==0);
                report.addProperty("passed",true);finish(level,world);
            }
        }
        catch(Exception error)
        {
            report.addProperty("passed",false);report.addProperty("error",error.toString());com.projectseele.ProjectSeele.LOGGER.error("R30 shutdown regression failed",error);finish(level,world);
        }
    }
    private static void finish(ServerLevel level,Path world)
    {
        done=true;if(hull!=null&&!hull.isRemoved())hull.discard();if(pilot!=null)pilot.discard();if(benchPilot!=null)benchPilot.stopRiding();
        try{Files.writeString(world.resolve("r30_shutdown_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception e){throw new IllegalStateException(e);}
        level.getServer().halt(false);
    }
    private ShutdownR30Review(){}
}
