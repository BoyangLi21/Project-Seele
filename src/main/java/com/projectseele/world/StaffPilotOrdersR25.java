package com.projectseele.world;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.NervStaffEntity;
import com.projectseele.entity.TrainingPilotEntity;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.util.*;

/** Dispatch waits for the existing remote airframe; it never replaces a pilot. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID)
public final class StaffPilotOrdersR25
{
    private record Order(UUID caller, UUID officer, int unit, long deadline) {}
    private static final Map<ServerLevel, Map<Integer,Order>> ORDERS = new WeakHashMap<>();
    public static String request(ServerPlayer player, NervStaffEntity npc, int unit)
    {
        if (unit<0 || unit>2 || !NervStaffDialogue.authorized(player) || !StaffAuthorityR25.allows(npc,"board"))
            return "本岗位无权调遣驾驶员，请联络美里、律子或冬月。";
        var jobs=ORDERS.computeIfAbsent(player.serverLevel(),l->new HashMap<>());
        var command=StaffCommandBookR24.unitOrder(player.serverLevel(),unit);
        if(command!=null&&!command.owner.equals(player.getUUID()))return "这台机体已有其他指挥员的待执行指令，请先联系下令人。";
        if(jobs.containsKey(unit))return "该驾驶员已有登机指令，正在执行。";
        jobs.put(unit,new Order(player.getUUID(),npc.getUUID(),unit,player.server.getTickCount()+300));
        EvaLogisticsDirector.loadControlTarget(player.serverLevel(),unit);
        return "正在呼叫"+TrainingPilotEntity.pilotName(unit)+"，确认对应机库后开始登机。";
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(event.phase!=TickEvent.Phase.END || event.getServer().getTickCount()%5!=0)return;
        for(var level:event.getServer().getAllLevels())
        {
            var jobs=ORDERS.get(level);if(jobs==null)continue;
            for(var job:List.copyOf(jobs.values()))
            {
                var player=event.getServer().getPlayerList().getPlayer(job.caller());
                var actor=level.getEntity(job.officer());
                if(player==null || player.level()!=level || !(actor instanceof NervStaffEntity npc)
                        || !NervStaffDialogue.authorized(player) || !StaffAuthorityR25.allows(npc,"board"))
                {jobs.remove(job.unit());continue;}
                if(event.getServer().getTickCount()>job.deadline())
                {jobs.remove(job.unit());NervStaffDialogue.reply(player,npc,"机库信号超时，登机指令未执行。");continue;}
                EvaLogisticsDirector.loadControlTarget(level,job.unit());
                if(EvaLogisticsDirector.canonicalUnit(level,job.unit())==null)continue;
                jobs.remove(job.unit());var result=TrainingPilotDirector.start(level,job.unit());
                NervStaffDialogue.reply(player,npc,TrainingPilotEntity.pilotName(job.unit())+"："
                        +(result.accepted()?"收到，前往插入栓登机。":result.message()));
            }
        }
    }
    private StaffPilotOrdersR25() {}
}
