package com.projectseele.world;

import com.projectseele.entity.*;
import com.projectseele.event.TvCampaignDirector;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.*;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.ChunkPos;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import java.util.*;

/** A single encounter, with independent original airframes and original riding chains. */
@Mod.EventBusSubscriber(modid="projectseele")
public final class TvSortiesR32
{
    private static final TicketType<ChunkPos> TICKET=TicketType.create("tv_sorties_r32",Comparator.comparingLong(ChunkPos::toLong),100);
    public static int slot(EvaUnit01Entity e){return e instanceof EvaPrototypeEntity un?3+un.getUNSerial():e.getUnitVariant();}
    public static String name(int slot){return slot<3?NervStaffDialogue.unitName(slot):"EVA-UN-0"+(slot-3);}
    public static EvaUnit01Entity unit(ServerLevel l,int slot)
    {
        if(slot<3)return EvaLogisticsDirector.canonicalUnit(l,slot);
        var id=UNRecoveryR22.identity(l,slot-3);return id!=null&&l.getEntity(id) instanceof EvaUnit01Entity e?e:null;
    }
    public static boolean ready(EvaUnit01Entity e)
    {return e!=null&&e.getPilotEntity()!=null&&e.isPoweredOn()&&!EvaShutdownR30.disabled(e)&&!e.isNervLogisticsLocked()&&!e.isLaunchSequenceActive()&&!EvaAirTransportR31.active(e);}
    public static int reinforce(ServerPlayer caller,int unit,boolean npc,boolean rifle)
    {
        var l=TvCampaignDirector.level(caller);
        if(l==null||l!=caller.level()||!NervStaffDialogue.authorized(caller)||unit<0||unit>4||npc&&unit>2)return 0;
        var d=TvCampaignSavedData.get(l);if(d.active.isEmpty()||d.phase.equals("cancel"))return 0;
        var current=d.sorties.get(unit);
        if(current!=null){caller.sendSystemMessage(Component.literal(name(unit)+"已经在出击编成中。"));return 1;}
        var e=unit(l,unit);
        if(e!=null&&e.getPilotEntity()!=null&&(npc?!(e.getPilotEntity() instanceof TrainingPilotEntity):e.getPilotEntity()!=caller))
        {caller.sendSystemMessage(Component.literal("这台机体已有其他驾驶员，不能接管。"));return 0;}
        d.assign(unit,caller.getUUID(),npc,rifle&&npc);
        NervStaffDialogue.say(caller,"葛城美里 · 作战通信",name(unit)+"加入迎击。正在交战的机体继续牵制，支援机到达后从侧面接应。");
        return 1;
    }
    public static String roster(TvCampaignSavedData data)
    {return "出击编成："+String.join("、",data.sorties.values().stream().map(s->name(s.unit)+"（"+(s.npc?TrainingPilotEntity.pilotName(s.unit):"玩家")+"）").toList());}
    public static void updateTarget(ServerLevel l,TvCampaignSavedData d)
    {
        if(d.angel==null||!(l.getEntity(d.angel) instanceof Mob enemy))return;
        if(enemy instanceof FirstBattleSignals.Actor actor&&actor.firstBattleSignals().active(enemy))return;
        var choices=d.sorties.values().stream().map(s->unit(l,s.unit)).filter(TvSortiesR32::ready).filter(e->!e.isFirstBattleActive()).toList();
        var nearest=choices.stream().min(Comparator.comparingDouble(enemy::distanceToSqr)).orElse(null);
        var present=enemy.getTarget();
        // Retain an engaged target; switch only after it leaves combat or a much closer support intervenes.
        if(present==null||!choices.contains(present)||nearest!=null&&nearest.distanceToSqr(enemy)<present.distanceToSqr(enemy)*.45)
            enemy.setTarget(nearest);
    }
    public static void continuity(ServerLevel l,TvCampaignSavedData d)
    {
        if(d.active.isEmpty()||d.phase.equals("cancel"))return;
        for(var player:l.players())
        {
            var eva=EvaPilotResolver.controlTarget(player);if(eva==null||!NervStaffDialogue.authorized(player))continue;
            int unit=slot(eva);var assigned=d.sorties.get(unit);
            if(unit(l,unit)==eva&&(assigned==null||assigned.npc||!player.getUUID().equals(assigned.commander)))
                d.assign(unit,player.getUUID(),false,false);
        }
        for(var s:d.sorties.values())
        {
            var eva=unit(l,s.unit);
            if(eva!=null&&!eva.blockPosition().equals(s.position)){s.position=eva.blockPosition();d.setDirty();}
            if(s.npc)continue;
            var player=l.getServer().getPlayerList().getPlayer(s.commander);if(player==null)continue;
            if(player.level()!=l){s.resumePending=s.wasRiding=false;d.setDirty();continue;}
            if(s.resumePending)
            {
                if(++s.resumeTicks>200){s.resumePending=s.wasRiding=false;d.setDirty();continue;}
                if(s.position!=null&&s.resumeTicks%10==1){var chunk=new ChunkPos(s.position);l.getChunkSource().addRegionTicket(TICKET,chunk,3,chunk);l.getChunk(s.position);}
                if(eva==null||s.eva==null||!eva.getUUID().equals(s.eva)||!(l.getEntity(s.plug) instanceof EntryPlugCarrierEntity plug))continue;
                if(player.isPassenger()){s.resumePending=false;s.wasRiding=EvaPilotResolver.controlTarget(player)==eva;d.setDirty();continue;}
                if(plug.getLinkedEva()!=eva||plug.getVehicle()!=eva||!plug.isLockedToEva()||!plug.isHatchFullySealed()||eva.getPilotEntity()!=null||plug.isVehicle()||player.distanceToSqr(eva)>128*128||!NervStaffDialogue.authorized(player))
                {s.resumePending=s.wasRiding=false;d.setDirty();continue;}
                if(player.startRiding(plug,true))
                {
                    player.fallDistance=0;plug.syncPilotPositionNow();l.getChunkSource().move(player);
                    var packet=new net.minecraft.network.protocol.game.ClientboundSetPassengersPacket(plug);l.getChunkSource().broadcastAndSend(plug,packet);player.connection.send(packet);
                    s.resumePending=false;s.wasRiding=true;d.setDirty();
                }
                continue;
            }
            boolean riding=eva!=null&&EvaPilotResolver.controlTarget(player)==eva&&player.getVehicle() instanceof EntryPlugCarrierEntity;
            if(riding){s.eva=eva.getUUID();s.plug=player.getVehicle().getUUID();}
            if(s.wasRiding!=riding){s.wasRiding=riding;d.setDirty();}
        }
    }
    @SubscribeEvent public static void commands(RegisterCommandsEvent event)
    {
        event.getDispatcher().register(Commands.literal("seele").then(Commands.literal("tv")
            .then(Commands.literal("support").then(Commands.argument("unit",IntegerArgumentType.integer(0,4))
                .then(Commands.literal("player").executes(c->TvCampaignDirector.beginAssigned(c.getSource().getPlayerOrException(),IntegerArgumentType.getInteger(c,"unit"),false,false)))
                .then(Commands.literal("npc").executes(c->TvCampaignDirector.beginAssigned(c.getSource().getPlayerOrException(),IntegerArgumentType.getInteger(c,"unit"),true,true)))))));
    }
    private TvSortiesR32(){}
}
