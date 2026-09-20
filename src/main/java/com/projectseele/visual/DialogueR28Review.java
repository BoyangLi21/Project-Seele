package com.projectseele.visual;

import com.google.gson.JsonObject;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.registry.ModEntities;
import com.projectseele.world.*;
import net.minecraft.server.level.*;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Unspawned actors exercise dialogue without replacing any saved NPC or fleet. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class DialogueR28Review
{
    public static final boolean ENABLED=System.getProperty("projectseele.regionalBuild", "").equals("r28-dialogue");
    public static volatile boolean ready, finished;
    public static final Set<String> received=java.util.concurrent.ConcurrentHashMap.newKeySet();
    public static final List<Integer> radioTicks=new java.util.concurrent.CopyOnWriteArrayList<>();
    private static int age;
    private static final TrainingPilotEntity[] pilots=new TrainingPilotEntity[3];
    private static final EvaUnit01Entity[] units=new EvaUnit01Entity[3];
    private static final JsonObject checks=new JsonObject();
    private static void check(String key,boolean value){checks.addProperty(key,value);if(!value)throw new IllegalStateException(key);}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||!ready||finished||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        try
        {
            check("isolated_world",world.getFileName().toString().equals("SEELE_FIELD_R28_REVIEW"));
            var player=server.getPlayerList().getPlayers().get(0);var level=server.getLevel(FacilitySchemaV2.DIMENSION);age++;
            if(age==1)
            {
                player.stopRiding();player.teleportTo(level,27.5,-406,283.5,180,0);
                for(int v=0;v<3;v++)
                {
                    pilots[v]=ModEntities.TRAINING_PILOT.get().create(level);pilots[v].assignVariant(v);pilots[v].setPos(player.position());
                    pilots[v].setTrainingStage(TrainingPilotEntity.STAGE_STANDBY);
                    units[v]=ModEntities.EVA_UNIT01.get().create(level);
                    for(String topic:List.of("standby","boarding","plug","link","transfer","ready","launch","field","hit","low_power","return","fault"))
                    {
                        Set<String> prose=new HashSet<>();for(int i=0;i<3;i++)prose.add(StaffDialogueCatalogR24.line(PilotRadioR28.profile(v),"technician",topic,i));
                        check("profile_"+v+"_"+topic,prose.size()==3&&!prose.contains("我在岗位上。你需要了解哪一项情况？"));
                    }
                    var lines=new HashSet<String>();for(int i=0;i<6;i++)lines.add(PilotRadioR28.response(player,pilots[v],true));
                    check("six_distinct_standby_"+v,lines.size()==6);
                    check("no_false_occupancy_"+v,PilotRadioR28.occupiedUnit(pilots[v])==null);
                    NervStaffDialogue.pilot(player,pilots[v]);
                }
                check("transfer_state",PilotRadioR28.phaseTopic("TO_SILO",false).equals("transfer"));
                check("return_state",PilotRadioR28.phaseTopic("TO_HANGAR",false).equals("return"));
                check("launch_state",PilotRadioR28.phaseTopic("DEPLOYED",true).equals("launch"));
                check("field_state",PilotRadioR28.phaseTopic("DEPLOYED",false).equals("field"));
                check("guard_not_commander",!StaffAuthorityR25.allows("guard","guard","launch"));
                check("ritsuko_no_launch",!StaffAuthorityR25.allows("scientist","ritsuko","launch"));
                check("misato_launch",StaffAuthorityR25.allows("commander","misato","launch"));
            }
            for(int v=0;v<3;v++)
            {
                int start=40+v*220;
                if(age==start)pilots[v].setTrainingStage(TrainingPilotEntity.STAGE_WALKING);
                if(age==start+180)
                {
                    check("mounted_actor_"+v,pilots[v].startRiding(units[v],true));
                    check("real_occupant_"+v,PilotRadioR28.occupiedUnit(pilots[v])==units[v]);
                    NervStaffDialogue.pilot(player,pilots[v]);
                }
                if(age>=start&&age<start+200&&age%20==0){pilots[v].tickCount=age;PilotRadioR28.tick(pilots[v]);}
            }
            if(age==750)
            {
                for(int v=0;v<3;v++){int variant=v;check("native_chat_"+v,received.stream().anyMatch(s->s.contains(TrainingPilotEntity.pilotName(variant))));}
                check("native_radio",radioTicks.size()>=3);
                for(int i=1;i<radioTicks.size();i++)check("radio_spacing_"+i,radioTicks.get(i)-radioTicks.get(i-1)>=175);
                for(var pilot:pilots)pilot.stopRiding();
                checks.addProperty("passed",true);checks.addProperty("radio_messages",radioTicks.size());checks.addProperty("client_messages",received.size());
                Files.writeString(world.resolve("r28_dialogue_pass.json"),checks.toString());ProjectSeele.LOGGER.info("R28 DIALOGUE PASS {}",checks);finished=true;
            }
        }
        catch(Exception error)
        {
            ProjectSeele.LOGGER.error("R28 DIALOGUE FAILED",error);finished=true;
            try{Files.writeString(world.resolve("r28_dialogue_failure.txt"),error.toString());}catch(Exception ignored){}
        }
    }
    private DialogueR28Review() {}
}
