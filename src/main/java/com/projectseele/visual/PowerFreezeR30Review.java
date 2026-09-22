package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.entity.*;
import com.projectseele.registry.ModEntities;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.*;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Real first-person power loss, with a temporary actor in the disposable motion lab. */
@Mod.EventBusSubscriber(modid="projectseele")
public final class PowerFreezeR30Review
{
    public static final boolean ENABLED="r30-power-client".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile int actor,clock,frames;
    public static volatile boolean tracked,mounted,finished,move,stable=true,firstPerson;
    private static int age,phase;private static EvaUnit01Entity eva;private static ServerPlayer pilot;
    private static CompoundTag savedPose;private static final JsonObject report=new JsonObject();
    private static void check(String name,boolean value){report.addProperty(name,value);if(!value)throw new IllegalStateException(name);}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();if(server.getPlayerList().getPlayers().isEmpty()||++age<70)return;
        Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_TERRAIN_R30_REVIEW"))throw new IllegalStateException("Wrong power lab world");
        var level=server.overworld();
        try
        {
            if(phase==0)
            {
                pilot=server.getPlayerList().getPlayers().get(0);if(!pilot.isAlive())pilot=server.getPlayerList().respawn(pilot,false);pilot.stopRiding();pilot.setGameMode(GameType.SURVIVAL);pilot.setHealth(pilot.getMaxHealth());
                var old=new java.util.ArrayList<net.minecraft.world.entity.Entity>();for(var e:level.getAllEntities())if(e instanceof EvaUnit01Entity)old.add(e);old.forEach(net.minecraft.world.entity.Entity::discard);
                eva=ModEntities.EVA_UNIT01.get().create(level);eva.prepareForMotionLab();eva.moveTo(.5,-60,-36.5,0,0);level.addFreshEntity(eva);
                pilot.teleportTo(level,.5,-59,-49,0,0);actor=eva.getId();clock=0;phase=1;return;
            }
            if(++clock>1000)throw new IllegalStateException("Power review timed out phase="+phase);
            if(phase==1&&tracked&&clock>25){check("human_boarded",eva.boardFromExternalPlug(pilot,100));phase=2;clock=0;return;}
            if(phase==2&&mounted&&clock>70)
            {
                var tag=eva.saveWithoutId(new CompoundTag());tag.putInt("SeelePowerTicks",90);tag.putBoolean("SeeleBatterySession",true);tag.putBoolean("SeeleUmbilicalSevered",true);eva.load(tag);
                eva.selectMotionLabWeapon(EvaUnit01Entity.WEAPON_RIFLE);move=true;phase=3;clock=0;return;
            }
            if(phase==3&&EvaShutdownR30.mode(eva)==EvaShutdownR30.POWER_LOCK)
            {check("actual_battery_depleted",eva.getPowerTicks()==0);move=false;phase=4;clock=0;return;}
            if(phase==4)
            {
                if(clock==80){check("pilot_composed_pose_received",eva.getPersistentData().getBoolean("R30FrozenPoseConfirmed"));savedPose=EvaShutdownR30.pose(eva).copy();}
                if(clock>=140&&frames>=100)
                {
                    check("real_first_person_camera",firstPerson);check("rendered_bones_remain_frozen",stable);
                    check("server_snapshot_stable",savedPose.equals(EvaShutdownR30.pose(eva)));report.addProperty("frozen_render_frames",frames);
                    var restored=ModEntities.EVA_UNIT01.get().create(level);restored.load(eva.saveWithoutId(new CompoundTag()));
                    check("save_reload_keeps_client_pose",EvaShutdownR30.mode(restored)==EvaShutdownR30.POWER_LOCK&&savedPose.equals(EvaShutdownR30.pose(restored)));
                    report.addProperty("passed",true);finish(world);
                }
            }
        }
        catch(Exception e){report.addProperty("passed",false);report.addProperty("error",e.toString());com.projectseele.ProjectSeele.LOGGER.error("R30 first person freeze failed",e);finish(world);}
    }
    private static void finish(Path world)
    {
        move=false;finished=true;
        if(pilot!=null){pilot.stopRiding();pilot.setGameMode(GameType.CREATIVE);pilot.teleportTo(pilot.serverLevel(),.5,-60,-45.5,0,0);}
        if(eva!=null)eva.discard();
        try{Files.writeString(world.resolve("r30_power_client_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception e){throw new IllegalStateException(e);}
    }
    private PowerFreezeR30Review(){}
}
