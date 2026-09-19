package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.SachielEntity;
import com.projectseele.event.FirstBattleMission;
import com.projectseele.registry.ModEntities;
import com.projectseele.world.*;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.GameRules;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Native fallback completion and false-credit checks, without replacing actors. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class NaturalResolutionR24Review
{
    private static final boolean ENABLED="r24-natural-resolution".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final UUID OWNER=UUID.fromString("24000000-0000-4000-8000-000000000024");
    private static boolean done;private static int age;private static final JsonObject checks=new JsonObject();
    private static void check(String name,boolean value){checks.addProperty(name,value);if(!value)throw new IllegalStateException(name);}
    private static void bind(ServerLevel level,SachielEntity angel,boolean campaign)
    {
        var first=new FirstBattleSavedData();first.missionOwner=OWNER;first.missionAngel=angel.getUUID();
        level.getDataStorage().set("projectseele_first_battle_r10",first);
        var tv=new TvCampaignSavedData();if(campaign){tv.active="sachiel";tv.phase="combat";tv.owner=OWNER;tv.angel=angel.getUUID();}
        level.getDataStorage().set("projectseele_tv_campaign_r24",tv);
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END||++age<60)return;
        var server=event.getServer();Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_R24_TV_REVIEW"))throw new IllegalStateException("Wrong native fallback test world");
        var level=server.getLevel(FacilitySchemaV2.DIMENSION);if(level==null)return;
        var first=FirstBattleSavedData.get(level);var tv=TvCampaignSavedData.get(level);
        if(first.active!=null||first.missionOwner!=null||!tv.active.isEmpty())throw new IllegalStateException("Existing campaign must be idle");
        CompoundTag firstBefore=first.save(new CompoundTag()),tvBefore=tv.save(new CompoundTag());
        boolean grief=level.getGameRules().getBoolean(GameRules.RULE_MOBGRIEFING);String error="";
        SachielEntity angel=null,other=null;
        try
        {
            angel=ModEntities.SACHIEL.get().create(level);other=ModEntities.SACHIEL.get().create(level);
            if(angel==null||other==null)throw new IllegalStateException("Native entity factory failed");
            bind(level,angel,true);FirstBattleMission.naturalResolution(other);
            check("different_target_no_credit",TvCampaignSavedData.get(level).completed.isEmpty()&&FirstBattleSavedData.get(level).missionAngel.equals(angel.getUUID()));
            bind(level,angel,true);FirstBattleSavedData.get(level).missionCancelRequested=true;FirstBattleMission.naturalResolution(angel);
            check("cancelled_no_credit",TvCampaignSavedData.get(level).completed.isEmpty());
            bind(level,angel,true);FirstBattleSavedData.get(level).active=new FirstBattleSavedData.Encounter();FirstBattleMission.naturalResolution(angel);
            check("director_owns_active_encounter",TvCampaignSavedData.get(level).completed.isEmpty());
            bind(level,angel,false);FirstBattleMission.naturalResolution(angel);
            check("independent_replay_does_not_advance_tv",TvCampaignSavedData.get(level).chapter==0&&TvCampaignSavedData.get(level).completed.isEmpty());
            bind(level,angel,true);
            // Run the real one-tick fuse and explosion entirely above the
            // existing world's build height, with block griefing disabled.
            level.getGameRules().getRule(GameRules.RULE_MOBGRIEFING).set(false,server);
            var tag=angel.saveWithoutId(new CompoundTag());tag.putInt("SachielSelfDestruct",1);tag.putBoolean("FirstBattleUsed",true);tag.putFloat("Health",1);
            angel.readAdditionalSaveData(tag);angel.setNoAi(true);angel.setNoGravity(true);angel.moveTo(30,level.getMaxBuildHeight()+128,310,0,0);
            check("fixture_not_inserted_into_world",level.getEntity(angel.getUUID())==null);
            angel.tick();var completed=TvCampaignSavedData.get(level);
            check("real_fuse_discarded_target",angel.isRemoved());
            check("real_fuse_advanced_exact_chapter",completed.chapter==1&&completed.completed.equals(List.of("sachiel"))&&completed.active.isEmpty());
            check("mission_binding_released",FirstBattleSavedData.get(level).missionOwner==null&&FirstBattleSavedData.get(level).missionAngel==null);
            FirstBattleMission.naturalResolution(angel);check("duplicate_callback_no_double_credit",completed.completed.size()==1&&completed.chapter==1);
        }
        catch(Exception failure){error=failure.toString();ProjectSeele.LOGGER.error("R24 natural resolution review failed",failure);}
        finally
        {
            if(angel!=null)angel.discard();if(other!=null)other.discard();
            level.getDataStorage().set("projectseele_first_battle_r10",first);level.getDataStorage().set("projectseele_tv_campaign_r24",tv);
            level.getGameRules().getRule(GameRules.RULE_MOBGRIEFING).set(grief,server);
            boolean preserved=firstBefore.equals(FirstBattleSavedData.get(level).save(new CompoundTag()))&&tvBefore.equals(TvCampaignSavedData.get(level).save(new CompoundTag()));
            checks.addProperty("original_campaign_state_preserved",preserved);if(!preserved)error+=" Original campaign state changed";
            var report=new JsonObject();report.addProperty("passed",error.isEmpty());report.addProperty("error",error);report.add("checks",checks);report.addProperty("existing_actor_changes",0);report.addProperty("existing_block_changes",0);
            try{Files.writeString(world.resolve("r24_natural_resolution_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception failure){ProjectSeele.LOGGER.error("Could not save review report",failure);}
            done=true;server.halt(false);
        }
    }
    private NaturalResolutionR24Review(){}
}
