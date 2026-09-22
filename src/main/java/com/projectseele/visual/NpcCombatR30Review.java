package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.entity.*;
import com.projectseele.registry.ModItems;
import com.projectseele.world.*;
import net.minecraft.server.level.*;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Real UI order, original Shinji/capsule/EVA, native walking and damage, then the natural TV finale. */
@Mod.EventBusSubscriber(modid="projectseele")
public final class NpcCombatR30Review
{
    private static final String MODE=System.getProperty("projectseele.regionalBuild","");
    public static final boolean ASUKA=MODE.equals("r30-npc-asuka");
    public static final int VARIANT=ASUKA?2:1;
    public static final String MISSION=ASUKA?"shamshel":"sachiel";
    public static final boolean ENABLED=ASUKA||MODE.equals("r30-npc-combat");
    public static volatile boolean ready,finished;
    public static volatile String input="",photo="";
    public static volatile Vec3 lookTarget;
    public static volatile int evaId=-1,tracerPackets;
    public static final Set<String> photos=java.util.concurrent.ConcurrentHashMap.newKeySet();
    private static int age,stage,timer,hits;private static double walked;private static boolean cinematic,rifle;
    private static Vec3 lastFeet;private static String lastPhase="";private static UUID evaUuid,plugUuid,pilotUuid,angelUuid;
    private static ServerPlayer player;private static ServerLevel level;private static Path world;private static int originalChapter;
    private static final JsonObject report=new JsonObject();private static final Set<String> phases=new TreeSet<>();
    private static void check(String key,boolean value){report.addProperty(key,value);if(!value)throw new IllegalStateException(key);}
    @SubscribeEvent public static void hit(LivingHurtEvent event)
    {
        if(!ENABLED||finished||angelUuid==null||!event.getEntity().getUUID().equals(angelUuid))return;
        if(event.getSource().getEntity() instanceof EvaUnit01Entity e&&e.getUUID().equals(evaUuid))hits++;
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||!ready||finished||event.phase!=TickEvent.Phase.END||event.getServer().getPlayerList().getPlayers().isEmpty())return;
        try
        {
            if(world==null)
            {
                world=event.getServer().getWorldPath(LevelResource.ROOT).normalize();check("isolated_review",world.getFileName().toString().equals("SEELE_FIELD_R30_REVIEW"));
                level=event.getServer().getLevel(FacilitySchemaV2.DIMENSION);player=event.getServer().getPlayerList().getPlayers().get(0);player.stopRiding();player.setGameMode(GameType.CREATIVE);player.setInvulnerable(true);
                player.getInventory().add(new ItemStack(ModItems.NERV_EMPLOYEE_CARD.get()));player.getInventory().add(new ItemStack(ModItems.SATELLITE_PHONE.get()));
                player.teleportTo(level,28.5,-406,275.5,0,0);originalChapter=TvCampaignSavedData.get(level).chapter;check("idle_campaign",TvCampaignSavedData.get(level).active.isEmpty());
            }
            age++;timer++;level.resetEmptyTime();check("bounded_run",age<18000);
            if(Files.deleteIfExists(world.resolve("regional_stop_requested")))throw new IllegalStateException("Review stopped for diagnosis");
            if(age%100==0)com.projectseele.ProjectSeele.LOGGER.info("R30 NPC REVIEW stage={} age={} phase={} mission={} notice={}",stage,age,EvaLogisticsDirector.status(level,VARIANT).phase(),TvCampaignSavedData.get(level).phase,TvCampaignSavedData.get(level).notice);
            EvaLogisticsDirector.loadControlTarget(level,VARIANT);var eva=EvaLogisticsDirector.canonicalUnit(level,VARIANT);if(eva==null)return;
            if(stage==0)
            {
                String logistics=EvaLogisticsDirector.status(level,VARIANT).phase();
                if(logistics.equals("DEPLOYED"))
                {
                    if(timer%100==0&&NervAirLiftR30.phaseName(level).equals("IDLE"))
                    {
                        if(NervAirLiftR30.waitingAtHead(eva))EvaLogisticsDirector.requestRecovery(level,VARIANT);
                        else NervAirLiftR30.request(player,VARIANT,true,0,0);
                    }
                    return;
                }
                if(logistics.equals("SILO_READY")){if(timer%100==0)EvaLogisticsDirector.requestCancel(level,VARIANT);return;}
                if(!logistics.equals("PARKED"))return;
                var plug=EntryPlugDirector.canonical(level,VARIANT);if(plug==null)return;
                check("parked_fixture",EvaLogisticsDirector.status(level,VARIANT).phase().equals("PARKED"));
                eva.setHealth(eva.getMaxHealth());EvaShutdownR30.clear(eva);eva.normalizeAfterTransportR30(true);eva.enterHangarStandby();
                evaUuid=eva.getUUID();plugUuid=plug.getUUID();evaId=eva.getId();
                var pilot=TrainingPilotDirector.pilots(level).stream().filter(p->p.getAssignedVariant()==VARIANT).findFirst().orElse(null);if(pilot==null)return;pilotUuid=pilot.getUUID();
                StaffConversationR24.contact(player,"美里");input="start_mission";stage=1;timer=0;return;
            }
            var data=TvCampaignSavedData.get(level);
            if(stage==1)
            {
                if(timer>1200)throw new IllegalStateException("Mission UI did not submit the NPC order");
                if(!data.active.equals(MISSION))return;
                check("real_ui_chose_shinji",data.npcPilot&&data.assignedVariant==VARIANT&&data.autoArmament);input="close";stage=2;timer=0;
            }
            check("same_eva",eva.getUUID().equals(evaUuid));check("same_plug",EntryPlugDirector.canonical(level,VARIANT)!=null&&EntryPlugDirector.canonical(level,VARIANT).getUUID().equals(plugUuid));
            String phase=EvaLogisticsDirector.status(level,VARIANT).phase();phases.add(phase);
            if(eva.getPilotEntity()!=null)check("real_original_pilot",eva.getPilotEntity() instanceof TrainingPilotEntity&&eva.getPilotEntity().getUUID().equals(pilotUuid));
            if(EvaShutdownR30.wreck(eva))throw new IllegalStateException("NPC was defeated before resolving the mission");
            if(!phase.equals(lastPhase))
            {
                lastPhase=phase;Vec3 at=eva.position().add(phase.equals("DEPLOYED")?76:0,58,phase.equals("DEPLOYED")?-78:-30);player.teleportTo(level,at.x,at.y,at.z,0,0);player.getAbilities().flying=true;player.onUpdateAbilities();player.setNoGravity(true);lookTarget=eva.position().add(0,phase.equals("DEPLOYED")?31:46,0);
                photo="npc_"+phase.toLowerCase(Locale.ROOT);
            }
            if(phase.equals("DEPLOYED")&&!eva.isLaunchSequenceActive()&&!eva.isFirstBattleActive()&&!eva.hasActiveCarrierMotion())
            {
                if(lastFeet!=null){double step=eva.position().distanceTo(lastFeet);if(step<6)walked+=step;}lastFeet=eva.position();
                rifle|=(eva.getArmamentMask()&(1<<EvaUnit01Entity.WEAPON_RIFLE))!=0;
                if(age%40==0){Vec3 at=eva.position().add(76,58,-78);player.teleportTo(level,at.x,at.y,at.z,0,0);}
            }
            else lastFeet=null;
            lookTarget=eva.position().add(0,phase.equals("DEPLOYED")?31:46,0);if(data.angel!=null)angelUuid=data.angel;
            if(phase.equals("DEPLOYED")&&tracerPackets>0&&!photos.contains("npc_rifle_fire"))photo="npc_rifle_fire";
            if(eva.isFirstBattleActive()){cinematic=true;photo="npc_tv_finale";}
            if(stage==2&&data.active.isEmpty())
            {
                check("walked_to_battle",walked>100);check("took_real_weapon",rifle);check("received_real_rifle_tracers",tracerPackets>0);check("real_melee_damage",hits>0);check("appropriate_finale",ASUKA?!cinematic:cinematic);
                check("replay_preserves_progress",data.chapter==originalChapter);check("commander_not_put_in_cockpit",!player.isPassenger());
                report.addProperty("walked_metres",walked);report.addProperty("melee_hits",hits);report.addProperty("tracer_packets",tracerPackets);report.addProperty("passed",true);finish();
            }
        }
        catch(Exception error)
        {report.addProperty("passed",false);report.addProperty("error",error.toString());com.projectseele.ProjectSeele.LOGGER.error("R30 NPC review failed",error);finish();}
    }
    private static void finish()
    {
        report.addProperty("walked_metres",walked);report.addProperty("melee_hits",hits);report.addProperty("tracer_packets",tracerPackets);report.addProperty("observed_cinematic",cinematic);
        if(level!=null&&player!=null&&report.has("passed")&&!report.get("passed").getAsBoolean())
        {com.projectseele.event.TvCampaignDirector.cancel(player);TrainingPilotDirector.stop(level,VARIANT);}
        report.add("phases",new Gson().toJsonTree(phases));report.addProperty("age",age);input="close";finished=true;
        try{if(world!=null)Files.writeString(world.resolve(ASUKA?"r30_npc_asuka_review.json":"r30_npc_combat_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception e){throw new IllegalStateException(e);}
    }
    private NpcCombatR30Review(){}
}
