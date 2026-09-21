package com.projectseele.world;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import net.minecraft.commands.*;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.*;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.*;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.*;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.util.*;

/** Recall the recorded UN actors; absent/unloaded UUIDs never authorize respawning. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class UNRecoveryR22
{
    public static final class Locations extends SavedData
    {
        final Map<UUID,BlockPos> positions=new HashMap<>();
        static Locations load(CompoundTag t){var s=new Locations();for(String k:t.getAllKeys())try{s.positions.put(UUID.fromString(k),BlockPos.of(t.getLong(k)));}catch(IllegalArgumentException ignored){}return s;}
        @Override public CompoundTag save(CompoundTag t){positions.forEach((id,p)->t.putLong(id.toString(),p.asLong()));return t;}
    }
    private record Job(int serial,boolean reset,CommandSourceStack source,int started) {}
    private static final Map<ServerLevel,Map<Integer,Job>> JOBS=new WeakHashMap<>();
    private static final TicketType<ChunkPos> TICKET=TicketType.create("seele_un_recovery",Comparator.comparingLong(ChunkPos::toLong),240);
    private static Locations locations(ServerLevel l){return l.getDataStorage().computeIfAbsent(Locations::load,Locations::new,"projectseele_un_locations_r22");}
    public static void remember(net.minecraft.world.entity.Entity eva)
    {
        if(!(eva.level() instanceof ServerLevel l)||!l.dimension().equals(FacilitySchemaV2.DIMENSION))return;
        if(!(eva instanceof EvaPrototypeEntity)&&!(eva instanceof EntryPlugCarrierEntity p&&p.isIndependentUNPlug()))return;
        var s=locations(l);BlockPos p=eva.blockPosition();
        if(!p.equals(s.positions.get(eva.getUUID()))){s.positions.put(eva.getUUID(),p);s.setDirty();}
    }
    public static UUID identity(ServerLevel l,int serial){return serial==0?MilitaryR07Director.state(l).entities.get("prototype"):UNAnnexR20.state(l).unitId;}
    public static Vec3 home(int serial){return serial==0?new Vec3(6442.5,77,-6205.5):UNAnnexR20.HOME;}
    public static BlockPos lastKnownPosition(ServerLevel level,UUID id){return locations(level).positions.get(id);}
    private static void load(ServerLevel l,BlockPos p)
    {
        for(int x=(p.getX()>>4)-1;x<=(p.getX()>>4)+1;x++)for(int z=(p.getZ()>>4)-1;z<=(p.getZ()>>4)+1;z++)
        {var c=new ChunkPos(x,z);l.getChunkSource().addRegionTicket(TICKET,c,2,c);l.getChunk(x,z);}
    }
    public static int request(CommandSourceStack source,int serial,boolean reset)
    {
        var l=source.getServer().getLevel(FacilitySchemaV2.DIMENSION);if(l==null||identity(l,serial)==null){source.sendFailure(Component.literal("没有该 UN 机体的已登记身份，未生成替代机"));return 0;}
        if(UNAirLiftR29.active(l,serial))
        {
            if(reset)UNAirLiftR29.abortForMaintenance(l,serial);
            else {source.sendFailure(Component.literal("运输任务仍在执行，请先取消运输并等待安全返回；管理员可用 reset 紧急复位。"));return 0;}
        }
        JOBS.computeIfAbsent(l,k->new HashMap<>()).put(serial,new Job(serial,reset,source,source.getServer().getTickCount()));
        source.sendSuccess(()->Component.literal("EVA-UN-0"+serial+"：正在定位原机体与插入栓"),false);return 1;
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(event.phase!=TickEvent.Phase.END)return;var l=event.getServer().getLevel(FacilitySchemaV2.DIMENSION);if(l==null)return;
        var jobs=JOBS.get(l);if(jobs==null)return;
        for(var it=jobs.values().iterator();it.hasNext();)
        {
            var job=it.next();UUID id=identity(l,job.serial());Vec3 home=home(job.serial());
            load(l,locations(l).positions.getOrDefault(id,BlockPos.containing(home)));load(l,BlockPos.containing(home));
            if(event.getServer().getTickCount()-job.started()>200){job.source().sendFailure(Component.literal("原机体或插入栓仍未加载，未删除或复制实体"));it.remove();continue;}
            if(!(l.getEntity(id) instanceof EvaPrototypeEntity eva))continue;
            eva.stopUNFlight();
            load(l,eva.blockPosition());var data=eva.getPersistentData();
            if(data.hasUUID("UNPlug"))
            {
                BlockPos parked=locations(l).positions.get(data.getUUID("UNPlug"));if(parked!=null)load(l,parked);
            }
            var plug=UNPlugDirector.capsule(eva);if(plug==null)continue;
            var pilot=eva.getPilotEntity();var passengers=new ArrayList<net.minecraft.world.entity.Entity>();passengers.addAll(plug.getPassengers());passengers.addAll(eva.getPassengers());
            eva.setNervLogisticsLocked(true);eva.setNoGravity(true);eva.setDeltaMovement(Vec3.ZERO);
            eva.teleportTo(home.x,home.y,home.z);eva.setYRot(0);eva.setYBodyRot(0);eva.setYHeadRot(0);eva.setXRot(0);eva.resetFallDistance();
            eva.setNervLogisticsLocked(false);eva.setNervLogisticsLocked(true);
            data.putDouble("UNHomeX",home.x);data.putDouble("UNHomeY",home.y);data.putDouble("UNHomeZ",home.z);data.putFloat("UNHomeYaw",0);
            boolean extracting=!job.reset()&&pilot!=null&&plug.getInsertionStage()==EntryPlugCarrierEntity.STAGE_LOCKED;
            if(extracting)
            {
                plug.setCanonicalTransform(EntryPlugKinematics.lockedTransform(eva));
                if(!EntryPlugDirector.ejectPilotToPlug(l,-1,eva,pilot))throw new IllegalStateException("UN extraction failed after identity-safe recall");
            }
            else
            {
                for(var person:passengers)if(person instanceof ServerPlayer p){p.stopRiding();p.teleportTo(l,home.x+4,127,home.z-12,90,0);p.setDeltaMovement(Vec3.ZERO);p.resetFallDistance();}
                plug.resetIndependentAtDock(eva);eva.enterHangarStandby();EvaDorsalMechanism.set(eva,0,0);
                if(job.reset())eva.setHealth(eva.getMaxHealth());
            }
            remember(eva);remember(plug);job.source().sendSuccess(()->Component.literal("EVA-UN-0"+job.serial()+" 已回到原机库；"+(extracting?"正在退出原插入栓":"原机体与原插入栓已复位")+"。UUID 保持不变。"),false);
            ProjectSeele.LOGGER.info("UN R22 {} serial={} eva={} plug={}",job.reset()?"reset":"recover",job.serial(),id,plug.getUUID());it.remove();
        }
    }
    @SubscribeEvent public static void commands(RegisterCommandsEvent e)
    {
        var military=Commands.literal("military");
        for(String action:new String[]{"recover","reset"})
        {
            var branch=Commands.literal(action);
            for(int serial=0;serial<2;serial++){final int s=serial;branch.then(Commands.literal("0"+s).executes(c->request(c.getSource(),s,action.equals("reset"))));}
            military.then(branch);
            for(int serial=0;serial<2;serial++){final int s=serial;military.then(Commands.literal("un0"+s).then(Commands.literal(action).executes(c->request(c.getSource(),s,action.equals("reset")))));}
        }
        e.getDispatcher().register(Commands.literal("seele").requires(s->s.hasPermission(2)).then(military));
    }
    private UNRecoveryR22(){}
}
