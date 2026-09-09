package com.projectseele.visual;

import com.google.gson.JsonObject;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.SachielEntity;
import com.projectseele.event.FirstBattleMission;
import com.projectseele.registry.ModBlocks;
import com.projectseele.registry.ModEntities;
import com.projectseele.world.FirstBattleSavedData;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.UUID;

/** Actual block-use packet -> mission queue -> mounted approach -> unique Angel -> cancellation. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class FirstBattleMissionR10Review
{
    public static final boolean ENABLED="r10-mission".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile boolean click,finished;
    private static int age,stage,ticks;
    private static EvaUnit01Entity eva;
    private static UUID angel;
    private static ServerPlayer pilot;
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;var server=event.getServer();if(server.getPlayerList().getPlayers().isEmpty()||++age<80)return;
        var world=server.getWorldPath(LevelResource.ROOT).normalize();if(!world.getFileName().toString().equals("SEELE_FIRST_BATTLE_REVIEW_R10"))throw new IllegalStateException("Mission review is lab-only");
        var level=server.overworld();var data=FirstBattleSavedData.get(level);
        try
        {
            ticks++;
            if(age>700)throw new IllegalStateException("Mission dispatch deadline, stage="+stage);
            if(stage==0)
            {
                pilot=server.getPlayerList().getPlayers().get(0);pilot.stopRiding();FirstBattleMission.cancel(pilot);
                var old=new java.util.ArrayList<net.minecraft.world.entity.Entity>();for(var e:level.getAllEntities())if(e instanceof EvaUnit01Entity)old.add(e);for(var e:old)e.discard();
                level.setBlock(new BlockPos(-8,-60,-18),Blocks.SMOOTH_QUARTZ.defaultBlockState(),3);level.setBlock(new BlockPos(-8,-59,-18),ModBlocks.NERV_WORKSTATION.get().defaultBlockState(),3);
                pilot.teleportTo(level,-8.5,-60,-14.5,180,0);eva=ModEntities.EVA_UNIT01.get().create(level);eva.prepareForMotionLab();eva.moveTo(0,-60,-55,0,0);level.addFreshEntity(eva);click=true;stage=1;ticks=0;
            }
            else if(stage==1&&data.missionOwner!=null)
            {
                if(!data.missionOwner.equals(pilot.getUUID())||data.missionAngel!=null)throw new IllegalStateException("Dispatch ownership or premature spawn");
                ProjectSeele.LOGGER.info("R10 MISSION REVIEW PASS real_block_dispatch");stage=2;ticks=0;
            }
            else if(stage==2&&ticks>30)
            {
                if(data.missionAngel!=null)throw new IllegalStateException("Angel spawned before pilot mounted");
                if(!eva.boardFromExternalPlug(pilot,100))throw new IllegalStateException("Mission boarding failed");stage=3;ticks=0;
            }
            else if(stage==3&&data.missionAngel!=null)
            {
                angel=data.missionAngel;if(!(level.getEntity(angel) instanceof SachielEntity s)||s.getHealth()!=s.getMaxHealth()||s.getAtField()!=900)throw new IllegalStateException("Mission Angel initial state");
                ProjectSeele.LOGGER.info("R10 MISSION REVIEW PASS mounted_approach full_HP_AT actor={}",angel);stage=4;ticks=0;
            }
            else if(stage==4&&ticks>40)
            {
                if(!angel.equals(data.missionAngel))throw new IllegalStateException("Mission duplicated Angel");
                if(!FirstBattleMission.cancel(pilot)||data.missionOwner!=null||data.missionAngel!=null||level.getEntity(angel)!=null)throw new IllegalStateException("Mission cancellation cleanup failed");
                JsonObject result=new JsonObject();result.addProperty("passed",true);result.addProperty("real_block_packet",true);result.addProperty("spawn_requires_mounted_approach",true);result.addProperty("unique_angel",angel.toString());result.addProperty("cancel_cleanup",true);Files.writeString(world.resolve("r10_mission_review.json"),result.toString());finished=true;
            }
        }
        catch(Exception failure)
        {
            ProjectSeele.LOGGER.error("R10 MISSION REVIEW FAILED",failure);try{JsonObject d=new JsonObject();d.addProperty("passed",false);d.addProperty("failure",failure.toString());Files.writeString(world.resolve("r10_mission_review.json"),d.toString());}catch(Exception ignored){}finished=true;
        }
    }
    private FirstBattleMissionR10Review() {}
}
