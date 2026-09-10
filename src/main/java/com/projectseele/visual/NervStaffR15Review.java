package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.NervStaffEntity;
import com.projectseele.world.*;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.*;
import net.minecraft.server.level.*;
import net.minecraft.world.level.*;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Uses copied real rooms, native navigation/buttons, and a second cold server load. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class NervStaffR15Review
{
    public static final boolean CONTROLS_ONLY="r15-staff-controls".equals(System.getProperty("projectseele.regionalBuild",""));
    public static final boolean ENABLED=CONTROLS_ONLY||"r15-staff".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile boolean finished;
    public static volatile String photo="";
    public static final Set<String> captured=java.util.concurrent.ConcurrentHashMap.newKeySet();
    private static int age,phase,ticks,index,presses;
    private static ServerLevel level;private static ServerPlayer player;private static Path world;
    private static NervStaffEntity misato,ritsuko;private static boolean powered;
    private static List<NervStaffDirector.Station> roster;
    private static final JsonObject checks=new JsonObject(),identities=new JsonObject();
    private static final Set<String> visited=new HashSet<>();
    private static final TicketType<ChunkPos> TICKET=TicketType.create("r15_staff_review",Comparator.comparingLong(ChunkPos::toLong),240);
    private static void load(BlockPos pos)
    {
        var c=new ChunkPos(pos);for(int x=c.x-1;x<=c.x+1;x++)for(int z=c.z-1;z<=c.z+1;z++)
        {var chunk=new ChunkPos(x,z);level.getChunkSource().addRegionTicket(TICKET,chunk,2,chunk);level.getChunk(x,z);}
    }
    private static NervStaffEntity member(String id)
    {var uuid=NervStaffSavedData.get(level).identity(id);return uuid!=null&&level.getEntity(uuid) instanceof NervStaffEntity npc?npc:null;}
    private static void check(String key,boolean pass)
    {checks.addProperty(key,pass);if(!pass)throw new IllegalStateException(key);}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();if(++age<80)return;
        try
        {
            if(world==null)
            {
                world=server.getWorldPath(LevelResource.ROOT).normalize();
                if(!world.getFileName().toString().equals(CONTROLS_ONLY?"SEELE_STAFF_CONTROL_R15":"SEELE_STAFF_REVIEW_R15"))throw new IllegalStateException("R15 review requires isolated copy");
                level=server.getLevel(ResourceKey.create(Registries.DIMENSION,new ResourceLocation("projectseele","geofront")));roster=NervStaffDirector.roster(level);
                check("roster_loaded",roster.size()>200);check("surface_cities_empty",roster.stream().noneMatch(s->s.feet().getY()>=0&&s.feet().getX()<6000));
                if(CONTROLS_ONLY)check("migrated_layout_authority",RegionalFacilityLayout.migrated(server));
                if(server.isDedicatedServer())
                {
                    var previous=JsonParser.parseString(Files.readString(world.resolve("r15_staff_review.json"))).getAsJsonObject();
                    check("client_review_completed",previous.get("error").getAsString().isEmpty());
                    identities.asMap().putAll(previous.getAsJsonObject("identities").asMap());phase=20;index=0;ticks=0;return;
                }
            }
            if(server.isDedicatedServer()){reloadTick();return;}
            if(server.getPlayerList().getPlayers().isEmpty())return;player=server.getPlayerList().getPlayers().get(0);
            ticks++;
            if(phase==0)
            {
                player.setGameMode(GameType.CREATIVE);player.setInvisible(true);server.setFlightAllowed(true);player.getAbilities().flying=true;player.onUpdateAbilities();player.getInventory().add(new net.minecraft.world.item.ItemStack(com.projectseele.registry.ModItems.NERV_EMPLOYEE_CARD.get()));
                load(new BlockPos(28,-409,283));player.teleportTo(level,27.5,-407,282.5,0,0);phase=1;ticks=0;return;
            }
            if(phase==1)
            {
                if(ticks%60==0)load(new BlockPos(28,-409,283));misato=member("misato");ritsuko=member("ritsuko");
                if(misato==null||ritsuko==null){if(ticks>360)throw new IllegalStateException("Named operators not spawned");return;}
                if(Boolean.getBoolean("projectseele.staffPhotoOnly")){photo="command_staff";if(captured.contains(photo))finish("");return;}
                if(ticks<120){photo="command_staff";return;}
                check("ambiguous_unit_rejected",NervStaffDialogue.talk(player,"misato","整备 00 01")==0&&!misato.busy());
                check("negated_launch_rejected",NervStaffDialogue.talk(player,"misato","不要发射 01")==0&&!misato.busy());
                check("question_is_not_a_launch",NervStaffDialogue.talk(player,"misato","可以发射 01 吗？")==0&&!misato.busy());
                presses=misato.pressCount();check("prepare_requested",NervStaffDialogue.talk(player,"misato","整备 01")==1&&misato.busy());
                check("busy_request_rejected",NervStaffDialogue.talk(player,"misato","回收 01")==0);phase=2;ticks=0;photo="command_staff";return;
            }
            if(phase==2)
            {
                var button=NervOperationsConsole.staffControl(level,"prepare",1);var state=level.getBlockState(button);powered|=state.getBlock() instanceof ButtonBlock&&state.getValue(ButtonBlock.POWERED);
                if(misato.pressCount()>presses&&!misato.busy()&&ticks>60)
                {check("one_real_prepare_press",misato.pressCount()==presses+1&&powered);check("press_uses_local_path",misato.position().distanceTo(Vec3.atCenterOf(button))<5);if(CONTROLS_ONLY)check("remote_assigned_eva_loaded",EvaLogisticsDirector.status(level,1).loaded());phase=3;ticks=0;return;}
                if(ticks>380)throw new IllegalStateException("Prepare operation did not reach the real button");return;
            }
            if(phase==3)
            {
                if(ticks<180)return;check("returns_to_post",misato.position().distanceTo(Vec3.atBottomCenterOf(misato.station()))<1);
                player.teleportTo(level,27.5,-407,282.5,0,0);presses=ritsuko.pressCount();
                check("recover_requested",NervStaffDialogue.talk(player,"ritsuko","回收 01")==1&&ritsuko.busy());phase=4;ticks=0;powered=false;return;
            }
            if(phase==4)
            {
                var state=level.getBlockState(NervOperationsConsole.staffControl(level,"recover",1));powered|=state.getBlock() instanceof ButtonBlock&&state.getValue(ButtonBlock.POWERED);
                if(ritsuko.pressCount()>presses&&!ritsuko.busy()){check("one_real_recovery_press",ritsuko.pressCount()==presses+1&&powered);phase=5;ticks=0;return;}
                if(ticks>380)throw new IllegalStateException("Recovery operation did not reach the real button");return;
            }
            if(phase==5)
            {
                if(ticks<160)return;
                player.teleportTo(level,27.5,-407,282.5,0,0);presses=misato.pressCount();
                check("launch_can_be_cancelled",NervStaffDialogue.talk(player,"misato","发射 01")==1&&NervStaffDialogue.talk(player,"misato","停止操作")==1&&!misato.busy()&&misato.pressCount()==presses);
                if(CONTROLS_ONLY){finish("");return;}phase=6;index=0;ticks=0;return;
            }
            if(phase==6)
            {
                if(index>=roster.size()){check("all_posts_registered",NervStaffSavedData.get(level).identities().size()==roster.size());finish("");return;}
                var station=roster.get(index);
                if(ticks==1){load(station.feet());player.teleportTo(level,station.feet().getX()+.5,station.feet().getY()+2,station.feet().getZ()+.5,station.yaw(),20);}
                if(ticks%60==0)load(station.feet());
                var npc=member(station.id());
                if(npc!=null)
                {
                    checkPost(station,npc);identities.addProperty(station.id(),npc.getStringUUID());
                    if(station.id().equals("un/guard/0")){photo="un_personnel";if(ticks<140)return;}
                    if(!station.id().equals("misato")&&!station.id().equals("ritsuko"))
                    {var tag=new net.minecraft.nbt.CompoundTag();npc.saveWithoutId(tag);var copy=com.projectseele.registry.ModEntities.NERV_STAFF.get().create(level);copy.load(tag);check("serialization/"+station.id(),copy.memberId().equals(station.id())&&!copy.busy());}
                    index++;ticks=0;return;
                }
                if(ticks>400)throw new IllegalStateException("Post failed to populate: "+station.id());
            }
            if(age>20000)throw new IllegalStateException("Staff review timeout");
        }
        catch(Exception e){ProjectSeele.LOGGER.error("R15 STAFF REVIEW FAILED",e);finish(e.toString());}
    }
    private static void checkPost(NervStaffDirector.Station station,NervStaffEntity npc)
    {
        var matches=level.getEntitiesOfClass(NervStaffEntity.class,npc.getBoundingBox().inflate(32),n->n.memberId().equals(station.id()));
        check("unique/"+station.id(),matches.size()==1);
        check("supported/"+station.id(),!level.getBlockState(npc.blockPosition().below()).getCollisionShape(level,npc.blockPosition().below()).isEmpty());
        check("clear/"+station.id(),level.noCollision(npc));
    }
    private static void reloadTick()throws Exception
    {
        ticks++;
        if(index>=roster.size()){check("cold_registry_unchanged",NervStaffSavedData.get(level).identities().size()==roster.size());finish("");return;}
        var station=roster.get(index);if(ticks==1||ticks%60==0)load(station.feet());var npc=member(station.id());
        if(npc!=null)
        {
            checkPost(station,npc);check("cold_uuid/"+station.id(),identities.get(station.id()).getAsString().equals(npc.getStringUUID()));check("cold_no_task/"+station.id(),!npc.busy());index++;ticks=0;
        }
        else if(ticks>180)throw new IllegalStateException("Cold staff not restored: "+station.id());
    }
    private static void finish(String error)
    {
        finished=true;var report=new JsonObject();report.addProperty("error",error);report.add("checks",checks);report.add("identities",identities);report.addProperty("age",age);
        try{Files.writeString(world.resolve(Boolean.getBoolean("projectseele.staffPhotoOnly")?"r15_staff_photo.json":level.getServer().isDedicatedServer()?"r15_staff_dedicated.json":"r15_staff_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception e){ProjectSeele.LOGGER.error("Staff report failed",e);}
        ProjectSeele.LOGGER.info("R15 STAFF REVIEW FINISHED checks={} error={}",checks.size(),error);
        if(level!=null&&level.getServer().isDedicatedServer())level.getServer().halt(false);
    }
    private NervStaffR15Review(){}
}
