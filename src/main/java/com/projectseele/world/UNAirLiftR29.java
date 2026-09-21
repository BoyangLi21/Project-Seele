package com.projectseele.world;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.registry.ModEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.*;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.*;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.ChunkStatus;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.phys.*;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.util.*;
import java.util.concurrent.CompletableFuture;

/** Persistent physical transport of the original UN EVA and its original capsule. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class UNAirLiftR29
{
    private enum Phase { PREPARE, GROUND_LIFT, ROLL_OUT, FERRY, APPROACH, CLAMP, ASCEND, CRUISE, DESCEND, RELEASE, ROLL_IN, GROUND_LOWER, RETREAT, RETURN_FLIGHT, HOLD }
    private static final double OFFSET=84,DECK=1.6;
    private static final TicketType<ChunkPos> TICKET=TicketType.create("seele_un_airlift",Comparator.comparingLong(ChunkPos::toLong),120);
    public static final class State extends SavedData
    {
        final Map<Integer,Job> jobs=new HashMap<>();final Map<Integer,UUID> carts=new HashMap<>();final Map<Integer,BlockPos> cartPositions=new HashMap<>();final Map<Integer,String> last=new HashMap<>();
        static State load(CompoundTag tag)
        {
            State s=new State();
            for(var raw:tag.getList("Jobs",Tag.TAG_COMPOUND))
            {
                var t=(CompoundTag)raw;Job j=new Job();j.serial=t.getInt("Serial");j.owner=t.getUUID("Owner");j.unit=t.getUUID("Unit");j.plug=t.hasUUID("Plug")?t.getUUID("Plug"):null;j.plane=t.hasUUID("Plane")?t.getUUID("Plane"):null;
                j.phase=Phase.valueOf(t.getString("Phase"));j.from=read(t,"From");j.to=read(t,"To");j.destination=read(t,"Destination");j.pickup=read(t,"Pickup");j.planePosition=read(t,"PlanePosition");j.age=t.getInt("Age");j.duration=t.getInt("Duration");j.total=t.getInt("Total");j.homebound=t.getBoolean("Homebound");j.crew=t.getBoolean("Crew");j.cancel=t.getBoolean("Cancel");j.carrying=t.getBoolean("Carrying");j.note=t.getString("Note");j.rebase=true;s.jobs.put(j.serial,j);
            }
            for(int i=0;i<2;i++){if(tag.hasUUID("Cart"+i))s.carts.put(i,tag.getUUID("Cart"+i));if(tag.contains("CartPos"+i))s.cartPositions.put(i,BlockPos.of(tag.getLong("CartPos"+i)));s.last.put(i,tag.getString("Last"+i));}return s;
        }
        @Override public CompoundTag save(CompoundTag tag)
        {
            ListTag list=new ListTag();for(var j:jobs.values())
            {
                CompoundTag t=new CompoundTag();t.putInt("Serial",j.serial);t.putUUID("Owner",j.owner);t.putUUID("Unit",j.unit);if(j.plug!=null)t.putUUID("Plug",j.plug);if(j.plane!=null)t.putUUID("Plane",j.plane);t.putString("Phase",j.phase.name());put(t,"From",j.from);put(t,"To",j.to);put(t,"Destination",j.destination);put(t,"Pickup",j.pickup);put(t,"PlanePosition",j.planePosition);t.putInt("Age",j.age);t.putInt("Duration",j.duration);t.putInt("Total",j.total);t.putBoolean("Homebound",j.homebound);t.putBoolean("Crew",j.crew);t.putBoolean("Cancel",j.cancel);t.putBoolean("Carrying",j.carrying);t.putString("Note",j.note);list.add(t);
            }
            tag.put("Jobs",list);for(int i=0;i<2;i++){if(carts.containsKey(i))tag.putUUID("Cart"+i,carts.get(i));if(cartPositions.containsKey(i))tag.putLong("CartPos"+i,cartPositions.get(i).asLong());tag.putString("Last"+i,last.getOrDefault(i,"待命"));}return tag;
        }
    }
    private static final class Job
    {
        int serial,age,duration,total,loadCursor,missing,planeMissing;UUID owner,unit,plug,plane;Phase phase=Phase.PREPARE;
        Vec3 from=Vec3.ZERO,to=Vec3.ZERO,destination=Vec3.ZERO,pickup=Vec3.ZERO,planePosition=Vec3.ZERO;
        boolean homebound,crew,cancel,carrying,rebase,paused,siteReady;String note="正在定位原机体";CompletableFuture<?> loading;Vec3 waitAt;
    }
    private static void put(CompoundTag tag,String key,Vec3 v){tag.putDouble(key+"X",v.x);tag.putDouble(key+"Y",v.y);tag.putDouble(key+"Z",v.z);}
    private static Vec3 read(CompoundTag tag,String key){return new Vec3(tag.getDouble(key+"X"),tag.getDouble(key+"Y"),tag.getDouble(key+"Z"));}
    public static State state(ServerLevel level){return level.getDataStorage().computeIfAbsent(State::load,State::new,"projectseele_un_airlift_r29");}
    public static boolean active(ServerLevel l,int serial){return state(l).jobs.containsKey(serial);}
    public static boolean ownsAircraft(ServerLevel l,UUID id){return state(l).jobs.values().stream().anyMatch(j->id.equals(j.plane));}
    public static void abortForMaintenance(ServerLevel l,int serial)
    {
        var s=state(l);var job=s.jobs.remove(serial);if(job==null)return;
        if(job.plane!=null&&l.getEntity(job.plane) instanceof UNTransportEntity plane)plane.discard();
        if(l.getEntity(job.unit) instanceof EvaPrototypeEntity eva){eva.endNervCarrierMotion();eva.getPersistentData().putBoolean("UNTransportAutoload",false);}
        s.last.put(serial,"运输已由管理员维护复位接管");s.setDirty();
    }
    public static String phaseName(ServerLevel l,int serial){var j=state(l).jobs.get(serial);return j==null?"IDLE":j.phase.name();}
    public static void resumeReview(ServerLevel level,int serial,ServerPlayer owner)
    {
        if(!"r29-un".equals(System.getProperty("projectseele.regionalBuild","")))throw new IllegalStateException("Review only");
        var j=state(level).jobs.get(serial);if(j==null||j.phase!=Phase.HOLD||j.carrying||!j.owner.equals(owner.getUUID()))return;
        if(level.getEntity(j.unit) instanceof EvaPrototypeEntity eva&&eva.position().distanceTo(UNRecoveryR22.home(serial))<8)
        {begin(level,j,Phase.ROLL_OUT,eva.position(),apron(serial),240,eva);state(level).setDirty();}
    }
    public static boolean ownsMotion(ServerLevel l,int serial)
    {var j=state(l).jobs.get(serial);return j!=null&&j.phase!=Phase.PREPARE&&j.phase!=Phase.RETREAT&&j.phase!=Phase.RETURN_FLIGHT;}
    public static boolean emptyLoading(EvaPrototypeEntity eva)
    {return eva.level() instanceof ServerLevel l&&active(l,eva.getUNSerial())&&eva.getPersistentData().getBoolean("UNTransportAutoload")&&eva.getUUID().equals(UNRecoveryR22.identity(l,eva.getUNSerial()));}
    public static String status(ServerLevel l,int serial)
    {
        var j=state(l).jobs.get(serial);if(j==null)return state(l).last.getOrDefault(serial,"运输机待命");
        return j.note+" · "+(j.homebound?"返回联合国基地":"目的地 "+Math.round(j.destination.x)+" / "+Math.round(j.destination.z));
    }
    public static String request(ServerPlayer player,int serial,boolean homebound,int x,int z)
    {
        ServerLevel l=player.serverLevel();var s=state(l);if(s.jobs.containsKey(serial))return "这台机体已有运输任务，请先查看状态。";
        UUID unit=UNRecoveryR22.identity(l,serial);if(unit==null)return "没有这台 UN 机体的原始登记，未创建替代机。";
        if(x< -29999000||x>29999000||z< -29999000||z>29999000||!l.getWorldBorder().isWithinBounds(new BlockPos(x,80,z)))return "目标超出世界边界。";
        var j=new Job();j.serial=serial;j.owner=player.getUUID();j.unit=unit;j.homebound=homebound;j.destination=homebound?apron(serial):new Vec3(x+.5,0,z+.5);
        if(s.jobs.values().stream().anyMatch(other->other.destination.distanceToSqr(j.destination)<70*70))return "另一架运输机正在使用附近空域，请选择稍远的投放点。";
        var eva=l.getEntity(unit);j.crew=eva instanceof EvaPrototypeEntity e&&e.getPilotEntity()==player;
        if(eva instanceof EvaPrototypeEntity e&&e.getPilotEntity()!=null&&e.getPilotEntity()!=player)return "该机体由另一名驾驶员控制，请由驾驶员本人呼叫运输。";
        s.jobs.put(serial,j);s.setDirty();return "运输指令已接受。正在加载原机体与目的地，随后检查落点和机库联锁。";
    }
    public static String cancel(ServerPlayer player,int serial)
    {
        var s=state(player.serverLevel());var j=s.jobs.get(serial);if(j==null)return "没有正在执行的运输。";
        if(!j.owner.equals(player.getUUID())&&!player.hasPermissions(2))return "只有下达指令的人或管理员可以取消这次运输。";
        if(j.phase==Phase.PREPARE){if(player.serverLevel().getEntity(j.unit) instanceof EvaPrototypeEntity eva)eva.getPersistentData().putBoolean("UNTransportAutoload",false);s.jobs.remove(serial);s.last.put(serial,"已取消；已启动的机库机械按原流程完成");s.setDirty();return s.last.get(serial);}
        if(j.phase==Phase.RETREAT||j.phase==Phase.RETURN_FLIGHT)return "机体已安全卸载，运输机正在返航。";
        j.cancel=true;s.setDirty();return "已收到取消指令，将先安全返回基地，不会在空中释放机体。";
    }
    private static Vec3 apron(int serial){var home=UNRecoveryR22.home(serial);return new Vec3(home.x,home.y+DECK,-6045.5);}
    private static double cruise(ServerLevel l){return l.getMaxBuildHeight()+128;}
    private static void retain(ServerLevel l,BlockPos p,int radius)
    {var c=new ChunkPos(p);l.getChunkSource().addRegionTicket(TICKET,c,radius,c);l.getChunkSource().getChunkFuture(c.x,c.z,ChunkStatus.FULL,true);}
    private static boolean readyAt(ServerLevel l,Vec3 point)
    {
        var c=new ChunkPos(BlockPos.containing(point));retain(l,BlockPos.containing(point),3);boolean ready=true;
        for(int x=c.x-1;x<=c.x+1;x++)for(int z=c.z-1;z<=c.z+1;z++)
            if(!l.getChunkSource().hasChunk(x,z)){l.getChunkSource().getChunkFuture(x,z,ChunkStatus.FULL,true);ready=false;}
        return ready;
    }
    private static boolean loadLanding(ServerLevel l,Job j)
    {
        var centre=new ChunkPos(BlockPos.containing(j.destination));retain(l,BlockPos.containing(j.destination),7);
        if(j.loading!=null&&!j.loading.isDone())return false;
        if(j.loading!=null&&j.loading.isCompletedExceptionally())throw new IllegalStateException("目标区块加载失败");
        if(j.loadCursor>=169)return true;
        int x=centre.x+j.loadCursor%13-6,z=centre.z+j.loadCursor/13-6;j.loading=l.getChunkSource().getChunkFuture(x,z,ChunkStatus.FULL,true);j.loadCursor++;return false;
    }
    private static Vec3 landing(ServerLevel l,Vec3 requested,EvaPrototypeEntity eva)
    {
        for(int radius:new int[]{0,16,32,48})for(int n=0;n<(radius==0?1:8);n++)
        {
            int x=Mth.floor(requested.x+radius*Math.cos(n*Math.PI/4)),z=Mth.floor(requested.z+radius*Math.sin(n*Math.PI/4));
            int y=l.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,x,z);
            while(y>l.getMinBuildHeight()+2&&l.getBlockState(new BlockPos(x,y-1,z)).getCollisionShape(l,new BlockPos(x,y-1,z)).isEmpty())y--;
            Vec3 p=new Vec3(x+.5,y,z+.5);if(!supported(l,p))continue;
            if(!l.noCollision(eva,new AABB(p.x-11,p.y+.08,p.z-11,p.x+11,p.y+63,p.z+11)))continue;
            if(l.getBlockCollisions(eva,new AABB(p.x-72,p.y+69,p.z-60,p.x+72,p.y+106,p.z+60)).iterator().hasNext())continue;
            if(!l.getEntities(eva,new AABB(p.x-14,p.y,p.z-14,p.x+14,p.y+65,p.z+14),e->e instanceof EvaUnit01Entity&&e.isAlive()).isEmpty())continue;
            return p;
        }
        return null;
    }
    private static boolean supported(ServerLevel l,Vec3 p)
    {
        for(int[] o:new int[][]{{0,0},{-5,-3},{5,-3},{-5,3},{5,3}})
        {
            boolean ground=false;for(int dy=1;dy<=2;dy++){BlockPos q=BlockPos.containing(p.add(o[0],-dy,o[1]));if(!l.getBlockState(q).getCollisionShape(l,q).isEmpty()){ground=true;break;}}if(!ground)return false;
        }
        return true;
    }
    private static boolean openBase(ServerLevel l,int serial)
    {
        var phase=serial==0?MilitaryR07Director.state(l).phase:UNAnnexR20.state(l).phase;
        String action=phase==MilitaryR07Director.Phase.WET||phase==MilitaryR07Director.Phase.FILLING?"drain":phase==MilitaryR07Director.Phase.DRY?"door":"";
        if(!action.isEmpty()){if(serial==0)MilitaryR07Director.request(l,action,null);else UNAnnexR20.request(l,action,null);}
        return phase==MilitaryR07Director.Phase.OPEN;
    }
    private static UNTransportEntity cart(ServerLevel l,State s,Job j,EvaPrototypeEntity eva)
    {
        UUID id=s.carts.get(j.serial);
        if(id!=null){retain(l,s.cartPositions.getOrDefault(j.serial,BlockPos.containing(UNRecoveryR22.home(j.serial))),3);return l.getEntity(id) instanceof UNTransportEntity e?e:null;}
        var e=ModEntities.UN_TRANSPORT.get().create(l);if(e==null)return null;e.configure(j.serial,false);e.setGroundCart();Vec3 at=eva.position().distanceTo(UNRecoveryR22.home(j.serial))<5?eva.position():apron(j.serial);e.setPos(at);if(!l.addFreshEntity(e))return null;s.carts.put(j.serial,e.getUUID());s.cartPositions.put(j.serial,e.blockPosition());s.setDirty();return e;
    }
    private static void note(ServerLevel l,Job j,String text)
    {
        if(text.equals(j.note))return;j.note=text;var p=l.getServer().getPlayerList().getPlayer(j.owner);if(p!=null)p.sendSystemMessage(Component.literal("[UN 运输管制] "+text));
    }
    private static void begin(ServerLevel l,Job j,Phase phase,Vec3 from,Vec3 to,int duration,EvaPrototypeEntity eva)
    {
        j.phase=phase;j.from=from;j.to=to;j.age=0;j.duration=Math.max(1,duration);j.rebase=false;
        if(movesEva(phase)){eva.setNervLogisticsLocked(true);eva.setNoGravity(true);eva.beginNervCarrierMotion(from,to,j.duration);}
        note(l,j,switch(phase){case GROUND_LIFT->"自行载台升起";case ROLL_OUT->"机体正在移至库外吊装点";case FERRY->"运输机前往接载点";case APPROACH->"运输机下降，展开吊装架";case CLAMP->"正在锁紧机体夹具";case ASCEND->"吊装完成，垂直爬升";case CRUISE->"重型运输机巡航中";case DESCEND->"抵达目标，开始垂直投放";case RELEASE->"接地，解除夹具";case ROLL_IN->"自行载台将机体送回库位";case GROUND_LOWER->"机体落座原机库";case RETREAT,RETURN_FLIGHT->"机体已交付，运输机返航";default->"运输准备中";});
    }
    private static boolean movesEva(Phase p){return switch(p){case GROUND_LIFT,ROLL_OUT,ASCEND,CRUISE,DESCEND,ROLL_IN,GROUND_LOWER->true;default->false;};}
    private static int duration(Vec3 a,Vec3 b){return Math.max(80,Mth.ceil(a.distanceTo(b)/5));}
    private static double smooth(double x){return x*x*x*(x*(x*6-15)+10);}
    private static void lock(EvaPrototypeEntity eva){eva.stopUNFlight();eva.setNervLogisticsLocked(true);eva.setNoGravity(true);eva.setDeltaMovement(Vec3.ZERO);}
    private static void release(EvaPrototypeEntity eva)
    {
        eva.endNervCarrierMotion();eva.setNervLogisticsLocked(false);eva.setNoGravity(false);eva.setDeltaMovement(Vec3.ZERO);eva.setOnGround(true);eva.getPersistentData().putBoolean("UNTransportAutoload",false);
        if(eva.level() instanceof ServerLevel level&&eva.getPilotEntity() instanceof ServerPlayer player)
        {
            var values=eva.getEntityData().packDirty();
            if(values!=null){var packet=new net.minecraft.network.protocol.game.ClientboundSetEntityDataPacket(eva.getId(),values);level.getChunkSource().broadcastAndSend(eva,packet);player.connection.send(packet);}
            level.getChunkSource().move(player);
            com.projectseele.network.SeeleNetwork.CHANNEL.send(net.minecraftforge.network.PacketDistributor.PLAYER.with(()->player),new com.projectseele.network.ClientboundEvaArrivalSyncPacket(eva.getId(),eva.getX(),eva.getY(),eva.getZ(),eva.getYRot(),0));
        }
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(event.phase!=TickEvent.Phase.END)return;var l=event.getServer().getLevel(FacilitySchemaV2.DIMENSION);if(l==null)return;var s=state(l);if(s.jobs.isEmpty())return;l.resetEmptyTime();
        for(var j:new ArrayList<>(s.jobs.values()))try{advance(l,s,j);}catch(Exception error){j.phase=Phase.HOLD;j.note="运输暂停："+error.getMessage();s.setDirty();ProjectSeele.LOGGER.error("UN airlift held serial={}",j.serial,error);}
    }
    private static void advance(ServerLevel l,State s,Job j)
    {
        BlockPos last=UNRecoveryR22.lastKnownPosition(l,j.unit);retain(l,last==null?BlockPos.containing(UNRecoveryR22.home(j.serial)):last,3);retain(l,BlockPos.containing(UNRecoveryR22.home(j.serial)),6);
        if(!(l.getEntity(j.unit) instanceof EvaPrototypeEntity eva))
        {if(++j.missing>600){j.phase=Phase.HOLD;note(l,j,"原机体未能加载，请由管理员检查登记或执行维护复位");s.setDirty();}return;}
        if(j.plug==null&&eva.getPersistentData().hasUUID("UNPlug"))j.plug=eva.getPersistentData().getUUID("UNPlug");
        if(j.plug==null)return;var plugPos=UNRecoveryR22.lastKnownPosition(l,j.plug);if(plugPos!=null)retain(l,plugPos,3);
        if(!(l.getEntity(j.plug) instanceof EntryPlugCarrierEntity plug))
        {if(++j.missing>600){j.phase=Phase.HOLD;note(l,j,"原插入栓未能加载，请由管理员检查登记或执行维护复位");s.setDirty();}return;}
        j.missing=0;
        var owner=l.getServer().getPlayerList().getPlayer(j.owner);
        if(j.phase==Phase.RETREAT||j.phase==Phase.RETURN_FLIGHT)j.crew=false;
        if(eva.getPilotEntity()!=null&&(owner==null||eva.getPilotEntity()!=owner)){if(!j.crew)throw new IllegalStateException("原机体已由其他驾驶员占用");}
        if(j.crew&&owner==null){eva.endNervCarrierMotion();eva.setDeltaMovement(Vec3.ZERO);j.paused=true;note(l,j,"驾驶员离线，保持位置等待通信恢复");s.setDirty();return;}
        if(j.crew&&owner!=null&&eva.getPilotEntity()!=owner)
        {
            if(owner.level()!=l||owner.isPassenger()||owner.distanceToSqr(eva)>128*128)j.crew=false;
            else if(plug.isLockedToEva()&&!plug.isVehicle()){owner.startRiding(plug,true);plug.syncPilotPositionNow();l.getChunkSource().move(owner);}
            else if(!plug.isVehicle())plug.boardPassenger(owner);
        }
        if(j.paused){j.paused=false;j.rebase=true;}
        if(j.total++>24000&&j.phase!=Phase.HOLD)throw new IllegalStateException("运输超时，机体保持锁定等待处置");
        if(j.phase==Phase.PREPARE)
        {
            if(j.homebound&&eva.position().distanceTo(UNRecoveryR22.home(j.serial))<4)
            {s.jobs.remove(j.serial);s.last.put(j.serial,"机体已在原机库，无需运输回收");s.setDirty();return;}
            if(!loadLanding(l,j)){note(l,j,"正在逐批加载目标空域");return;}
            if(!j.siteReady)
            {
                Vec3 at=j.homebound?apron(j.serial):landing(l,j.destination,eva);
                if(at==null){s.jobs.remove(j.serial);s.last.put(j.serial,"落点及邻近地面没有足够净空，请选择开阔位置");note(l,j,s.last.get(j.serial));s.setDirty();return;}
                j.destination=at;j.siteReady=true;note(l,j,"落点确认："+BlockPos.containing(at).toShortString());
            }
            if(!openBase(l,j.serial)){note(l,j,"等待机库排液与舱门开启");return;}
            if(eva.isUNFlying()){eva.landUNFlight();note(l,j,"等待 UN-01 降落后接载");return;}
            if(!plug.isLockedToEva())
            {
                if(UNPlugDirector.atDock(eva)&&!plug.isVehicle()){UNPlugDirector.prepareEmptyForTransport(eva);note(l,j,"吊机正在接入原插入栓");return;}
                if(plug.isVehicle()){note(l,j,"等待驾驶员完成插入栓接入");return;}
                throw new IllegalStateException("原插入栓尚未锁定，请归位后再呼叫运输");
            }
            if(UNPlugDirector.atDock(eva)&&eva.getPersistentData().getInt("UNSequenceTicks")<60)return;
            var cart=cart(l,s,j,eva);if(cart==null)return;
            if(j.plane==null)
            {
                var plane=ModEntities.UN_TRANSPORT.get().create(l);if(plane==null)return;
                Vec3 h=UNRecoveryR22.home(j.serial);plane.configure(j.serial,false);plane.addTag("seele_un_airlift");plane.setPos(h.x,cruise(l),h.z+500);if(!l.addFreshEntity(plane))return;j.plane=plane.getUUID();j.planePosition=plane.position();
            }
            j.pickup=eva.position();eva.getPersistentData().putBoolean("UNTransportAutoload",false);lock(eva);
            if(eva.position().distanceTo(UNRecoveryR22.home(j.serial))<4&&!j.homebound)
                begin(l,j,Phase.GROUND_LIFT,eva.position(),eva.position().add(0,DECK,0),30,eva);
            else begin(l,j,Phase.FERRY,j.planePosition,new Vec3(eva.getX(),cruise(l),eva.getZ()),duration(j.planePosition,new Vec3(eva.getX(),cruise(l),eva.getZ())),eva);
            s.setDirty();return;
        }
        retain(l,BlockPos.containing(j.planePosition),3);var plane=l.getEntity(j.plane) instanceof UNTransportEntity e?e:null;
        if(plane==null)
        {
            if(++j.planeMissing>600){j.phase=Phase.HOLD;eva.endNervCarrierMotion();lock(eva);note(l,j,"运输机信号丢失，保持机体位置；请管理员检查或维护复位");s.setDirty();}
            return;
        }
        j.planeMissing=0;
        var cart=cart(l,s,j,eva);if(cart==null)return;
        if(j.phase==Phase.HOLD)
        {
            lock(eva);if(!j.cancel)return;j.homebound=true;j.cancel=false;j.destination=apron(j.serial);
            if(!j.carrying&&eva.isInsideTestHangar())begin(l,j,Phase.ROLL_IN,eva.position(),UNRecoveryR22.home(j.serial).add(0,DECK,0),120,eva);
            else if(!j.carrying)begin(l,j,Phase.FERRY,plane.position(),new Vec3(eva.getX(),cruise(l),eva.getZ()),duration(plane.position(),new Vec3(eva.getX(),cruise(l),eva.getZ())),eva);
            else begin(l,j,Phase.ASCEND,eva.position(),new Vec3(eva.getX(),cruise(l)-OFFSET,eva.getZ()),120,eva);
        }
        if(j.rebase)
        {
            if(j.waitAt!=null&&!readyAt(l,j.waitAt))return;j.waitAt=null;
            Vec3 from=movesEva(j.phase)?eva.position():plane.position();begin(l,j,j.phase,from,j.to,Math.max(30,j.duration-j.age),eva);
        }
        if(j.cancel&&(j.phase==Phase.CRUISE||j.phase==Phase.ASCEND||j.phase==Phase.DESCEND))
        {j.homebound=true;j.cancel=false;j.destination=apron(j.serial);begin(l,j,Phase.ASCEND,eva.position(),new Vec3(eva.getX(),cruise(l)-OFFSET,eva.getZ()),120,eva);}
        else if(j.cancel&&j.phase==Phase.RELEASE)
        {
            j.cancel=false;
            if(!j.homebound){j.homebound=true;j.destination=apron(j.serial);begin(l,j,Phase.CLAMP,plane.position(),plane.position(),40,eva);}
        }
        else if(j.cancel&&(j.phase==Phase.GROUND_LIFT||j.phase==Phase.ROLL_OUT))
        {j.cancel=false;j.homebound=true;j.destination=apron(j.serial);begin(l,j,Phase.ROLL_IN,eva.position(),UNRecoveryR22.home(j.serial).add(0,DECK,0),120,eva);}
        if(j.homebound)
        {
            Vec3 target=apron(j.serial);Vec3 delta=target.subtract(cart.position());if(delta.length()>.1)cart.setPos(cart.position().add(delta.normalize().scale(Math.min(.8,delta.length()))));
            openBase(l,j.serial);
        }
        j.age++;double t=smooth(Mth.clamp((double)j.age/Math.max(1,j.duration),0,1));Vec3 point=j.from.lerp(j.to,t);
        if(j.phase==Phase.CRUISE||j.phase==Phase.FERRY||j.phase==Phase.RETURN_FLIGHT)
            readyAt(l,j.from.lerp(j.to,smooth(Mth.clamp((j.age+30D)/Math.max(1,j.duration),0,1))));
        if(!readyAt(l,point))
        {j.age--;j.waitAt=point;j.rebase=true;eva.endNervCarrierMotion();note(l,j,"前方区块正在加载，保持位置");s.setDirty();return;}
        if(movesEva(j.phase))
        {
            lock(eva);
            Vec3 wanted=point.subtract(eva.position());
            Vec3 allowed=Entity.collideBoundingBox(eva,wanted,eva.getBoundingBox().deflate(.08),l,List.of());
            // The standing body's broad box already touches the dorsal access
            // gantry. Vanilla's swept solver correctly permits movement away
            // from that contact, while still stopping new leading-face hits.
            if(allowed.subtract(wanted).lengthSqr()>1e-6)throw new IllegalStateException("运输路径受阻，停在 "+eva.blockPosition().toShortString());
            float yaw=eva.getYRot();if(j.phase==Phase.CRUISE){Vec3 d=j.to.subtract(j.from);float target=(float)Math.toDegrees(Math.atan2(-d.x,d.z));yaw=Mth.approachDegrees(yaw,target,2.5F);}else if(j.phase==Phase.ROLL_IN||j.phase==Phase.ROLL_OUT)yaw=Mth.approachDegrees(yaw,0,2.5F);
            eva.moveOnNervCarrier(point.x,point.y,point.z,yaw);
            if(j.carrying){plane.setPos(point.x,point.y+OFFSET,point.z);plane.setYRot(yaw);plane.cargo(eva.getId(),true,1);}
            else {cart.setPos(point);cart.setYRot(yaw);}
        }
        else if(j.phase==Phase.FERRY||j.phase==Phase.APPROACH||j.phase==Phase.RETREAT||j.phase==Phase.RETURN_FLIGHT)
        {
            plane.setPos(point);Vec3 d=j.to.subtract(j.from);if(d.horizontalDistanceSqr()>1)plane.setYRot(Mth.approachDegrees(plane.getYRot(),(float)Math.toDegrees(Math.atan2(-d.x,d.z)),2.5F));
            plane.cargo(eva.getId(),false,j.phase==Phase.APPROACH?(float)t:0);
        }
        else if(j.phase==Phase.CLAMP){lock(eva);plane.cargo(eva.getId(),true,1);}
        else if(j.phase==Phase.RELEASE){lock(eva);plane.cargo(eva.getId(),false,1);}
        j.planePosition=plane.position();s.cartPositions.put(j.serial,cart.blockPosition());UNRecoveryR22.remember(eva);UNRecoveryR22.remember(plug);s.setDirty();
        if(j.age<j.duration)return;
        switch(j.phase)
        {
            case GROUND_LIFT -> begin(l,j,Phase.ROLL_OUT,eva.position(),apron(j.serial),240,eva);
            case ROLL_OUT -> {eva.endNervCarrierMotion();j.pickup=eva.position();begin(l,j,Phase.FERRY,plane.position(),new Vec3(eva.getX(),cruise(l),eva.getZ()),duration(plane.position(),new Vec3(eva.getX(),cruise(l),eva.getZ())),eva);}
            case FERRY -> begin(l,j,Phase.APPROACH,plane.position(),eva.position().add(0,OFFSET,0),120,eva);
            case APPROACH -> {plane.setYRot(eva.getYRot());begin(l,j,Phase.CLAMP,plane.position(),plane.position(),40,eva);}
            case CLAMP -> {j.carrying=true;begin(l,j,Phase.ASCEND,eva.position(),new Vec3(eva.getX(),cruise(l)-OFFSET,eva.getZ()),120,eva);}
            case ASCEND -> {Vec3 dest=new Vec3(j.destination.x,cruise(l)-OFFSET,j.destination.z);begin(l,j,Phase.CRUISE,eva.position(),dest,duration(eva.position(),dest),eva);}
            case CRUISE -> begin(l,j,Phase.DESCEND,eva.position(),j.destination,160,eva);
            case DESCEND -> {eva.endNervCarrierMotion();begin(l,j,Phase.RELEASE,plane.position(),plane.position(),40,eva);}
            case RELEASE ->
            {
                j.carrying=false;
                if(j.homebound){if(!openBase(l,j.serial)){j.age=j.duration-1;return;}begin(l,j,Phase.ROLL_IN,eva.position(),UNRecoveryR22.home(j.serial).add(0,DECK,0),240,eva);}
                else {release(eva);begin(l,j,Phase.RETREAT,plane.position(),new Vec3(plane.getX(),cruise(l),plane.getZ()),120,eva);}
            }
            case ROLL_IN -> begin(l,j,Phase.GROUND_LOWER,eva.position(),UNRecoveryR22.home(j.serial),30,eva);
            case GROUND_LOWER ->
            {
                var occupant=eva.getPilotEntity();release(eva);
                if(occupant==null){plug.resetIndependentAtDock(eva);eva.enterHangarStandby();}
                else if(!EntryPlugDirector.ejectPilotToPlug(l,-1,eva,occupant))throw new IllegalStateException("退出原插入栓请求未被接受");
                begin(l,j,Phase.RETREAT,plane.position(),new Vec3(plane.getX(),cruise(l),plane.getZ()),120,eva);
            }
            case RETREAT -> {Vec3 home=UNRecoveryR22.home(j.serial);Vec3 end=new Vec3(home.x,cruise(l),home.z+500);begin(l,j,Phase.RETURN_FLIGHT,plane.position(),end,duration(plane.position(),end),eva);}
            case RETURN_FLIGHT ->
            {
                if(j.homebound&&plug.getInsertionStage()==EntryPlugCarrierEntity.STAGE_EJECTING){j.age=j.duration-1;note(l,j,"机体已固定，等待退出原插入栓");return;}
                plane.discard();s.jobs.remove(j.serial);s.last.put(j.serial,j.homebound?"机体已回到原机库，运输机待命":"机体已安全投放，运输机待命");note(l,j,s.last.get(j.serial));s.setDirty();ProjectSeele.LOGGER.info("UN AIRLIFT COMPLETE unit={} plug={} serial={} homebound={}",j.unit,j.plug,j.serial,j.homebound);
            }
            default -> {}
        }
    }
    private UNAirLiftR29() {}
}
