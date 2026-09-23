package com.projectseele.world;

import com.projectseele.entity.*;
import net.minecraft.server.level.*;
import net.minecraft.world.level.ChunkPos;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.util.*;

/** Boarding arms a persistent job on that original EVA. Operators still press real interlocked controls. */
@Mod.EventBusSubscriber(modid="projectseele")
public final class AutoSortieR32
{
    private static final TicketType<ChunkPos> TICKET=TicketType.create("auto_sortie_r32",Comparator.comparingLong(ChunkPos::toLong),100);
    public static void assignCommander(EvaUnit01Entity eva,ServerPlayer player)
    {if(eva!=null)eva.getPersistentData().putUUID("R32SortieCommander",player.getUUID());}
    public static void cancel(ServerPlayer player,int unit)
    {
        var level=player.serverLevel();
        for(int i=0;i<3;i++)if(unit<0||i==unit)
        {
            var e=EvaLogisticsDirector.canonicalUnit(level,i);if(e==null)continue;var tag=e.getPersistentData();
            if(player.hasPermissions(2)||tag.hasUUID("R32SortieCommander")&&player.getUUID().equals(tag.getUUID("R32SortieCommander")))
                tag.putBoolean("R32AutoCancelled",true);
        }
    }
    private static NervStaffEntity officer(ServerLevel level,String skin)
    {
        var post=NervStaffDirector.roster(level).stream().filter(p->p.skin().equals(skin)).findFirst().orElse(null);if(post==null)return null;
        var c=new ChunkPos(post.feet());level.getChunkSource().addRegionTicket(TICKET,c,3,c);level.getChunk(post.feet());
        var id=NervStaffSavedData.get(level).identity(post.id());return id!=null&&level.getEntity(id) instanceof NervStaffEntity npc?npc:null;
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(event.phase!=TickEvent.Phase.END||event.getServer().getTickCount()%5!=0)return;
        var level=event.getServer().getLevel(FacilitySchemaV2.DIMENSION);if(level==null)return;
        for(int unit=0;unit<3;unit++)
        {
            var eva=EvaLogisticsDirector.canonicalUnit(level,unit);if(eva==null)continue;
            var tag=eva.getPersistentData();var plug=EntryPlugDirector.canonical(level,unit);
            var pilot=plug==null?null:plug.getFirstPassenger();if(pilot==null)pilot=eva.getPilotEntity();
            String phase=EvaLogisticsDirector.status(level,unit).phase();
            if(pilot==null)
            {
                if(phase.equals("PARKED")){tag.remove("R32BoardingPilot");tag.remove("R32AutoCancelled");tag.remove("R32AutoStep");}
                continue;
            }
            if(phase.equals("PARKED")&&(!tag.hasUUID("R32BoardingPilot")||!tag.getUUID("R32BoardingPilot").equals(pilot.getUUID())))
            {
                tag.putUUID("R32BoardingPilot",pilot.getUUID());tag.putString("R32AutoStep","prepare");tag.remove("R32AutoCancelled");tag.remove("R32AutoNext");
                if(pilot instanceof ServerPlayer player)assignCommander(eva,player);
                else if(!tag.hasUUID("R32SortieCommander"))
                {
                    var commander=level.players().stream().filter(NervStaffDialogue::authorized).min(Comparator.comparingDouble(p->p.distanceToSqr(eva))).orElse(null);
                    if(commander!=null)assignCommander(eva,commander);
                }
            }
            if(!tag.contains("R32AutoStep")||tag.getBoolean("R32AutoCancelled")||!tag.hasUUID("R32SortieCommander"))continue;
            if(EvaShutdownR30.wreck(eva)||eva.getHealth()<=0)
            {
                tag.putBoolean("R32AutoCancelled",true);
                var commander=level.getServer().getPlayerList().getPlayer(tag.getUUID("R32SortieCommander"));
                if(commander!=null)NervStaffDialogue.say(commander,"赤木律子 · 整备通信",NervStaffDialogue.unitName(unit)+"还有损伤，不能接入。先修复机体，再重新登机。");
                continue;
            }
            if(phase.equals("DEPLOYED")){tag.remove("R32AutoStep");continue;}
            if(tag.getString("R32AutoStep").equals("launch_accepted"))continue;
            if(phase.equals("PLUG_FAULT")||phase.contains("ABORT")||Set.of("DESCENDING","TO_HANGAR","FILLING").contains(phase))
            {tag.putBoolean("R32AutoCancelled",true);continue;}
            if(!Set.of("PARKED","SILO_READY").contains(phase)||level.getGameTime()<tag.getLong("R32AutoNext"))continue;
            var caller=level.getServer().getPlayerList().getPlayer(tag.getUUID("R32SortieCommander"));
            if(caller==null||caller.level()!=level||!NervStaffDialogue.authorized(caller))continue;
            if(StaffCommandBookR24.unitOrder(level,unit)!=null)continue;
            String operation=phase.equals("PARKED")?"prepare":"launch";
            var actor=officer(level,operation.equals("prepare")?"ritsuko":"misato");
            if(actor==null||actor.busy()||StaffCommandBookR24.order(actor)!=null)continue;
            tag.putLong("R32AutoNext",level.getGameTime()+100);
            if(StaffCommandBookR24.request(caller,actor,operation,unit)>0)
            {
                var order=StaffCommandBookR24.unitOrder(level,unit);if(order!=null)order.automatic=true;
                tag.putString("R32AutoStep",operation);
                com.projectseele.ProjectSeele.LOGGER.info("AUTO SORTIE unit={} pilot={} operator={} operation={}",unit,pilot.getUUID(),actor.skin(),operation);
            }
        }
    }
    private AutoSortieR32(){}
}
