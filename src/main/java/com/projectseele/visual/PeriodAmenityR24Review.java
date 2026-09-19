package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.world.*;
import net.minecraft.core.*;
import net.minecraft.server.level.*;
import net.minecraft.world.level.*;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.*;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class PeriodAmenityR24Review
{
    public static final boolean ENABLED="r24-amenities".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile boolean ready,finished,phoneReply,phoneSound;
    public static volatile String input="",photo="";
    public static volatile BlockHitResult hit;
    public static final Set<String> inputs=java.util.concurrent.ConcurrentHashMap.newKeySet(),photos=java.util.concurrent.ConcurrentHashMap.newKeySet();
    private static Path world;private static ServerLevel level;private static ServerPlayer player;private static int stage,timer,age;
    private static final JsonObject checks=new JsonObject();
    private static void check(String name,boolean value){checks.addProperty(name,value);if(!value)throw new IllegalStateException(name);}
    private static void next(int s){stage=s;timer=0;input="";photo="";ProjectSeele.LOGGER.info("R24 AMENITY REVIEW stage={}",s);}
    private static void teleport(double x,double y,double z,float yaw,float pitch){player.teleportTo(level,x,y,z,yaw,pitch);}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||!ready||finished||event.phase!=TickEvent.Phase.END)return;
        try
        {
            var server=event.getServer();if(server.getPlayerList().getPlayers().isEmpty())return;
            if(world==null)
            {
                world=server.getWorldPath(LevelResource.ROOT).normalize();check("isolated_world",world.getFileName().toString().equals("SEELE_R24_TV_REVIEW"));
                level=server.getLevel(FacilitySchemaV2.DIMENSION);player=server.getPlayerList().getPlayers().get(0);player.stopRiding();player.setGameMode(GameType.SURVIVAL);player.getFoodData().setFoodLevel(20);
                teleport(32.5,-466,470.5,0,0);level.getChunk(new BlockPos(32,-466,473));
            }
            age++;timer++;level.resetEmptyTime();check("bounded_review",age<1400);
            if(stage==0&&timer>100)
            {
                UUID id=NervStaffSavedData.get(level).identity("guard/hq_station");if(id==null||!(level.getEntity(id) instanceof NervStaffEntity npc))return;
                check("headquarters_station_on_graph",NervWayfindingR24.guide(player,"hangars").isPresent());
                NervStaffDialogue.open(player,npc);next(1);input="directions";return;
            }
            if(stage==1)
            {
                if(!inputs.contains("directions"))return;photo="directions_dialogue";
                if(photos.contains(photo)){next(2);input="hangars";}return;
            }
            if(stage==2)
            {
                if(!inputs.contains("hangars")||timer<40)return;photo="walking_guide_enabled";
                if(photos.contains(photo)){next(3);input="close";}return;
            }
            if(stage==3)
            {
                if(!inputs.contains("close")||timer<25)return;
                var first=NervWayfindingR24.guide(player,"hangars").orElseThrow();check("next_step_adjacent",first.here().distSqr(first.next())<=2);
                var points=new Object[][]{{"command",new BlockPos(28,-406,269)},{"hangars",new BlockPos(90,-394,-255)},{"station",new BlockPos(30,-466,451)},
                        {"pyramid_station",new BlockPos(30,-466,519)},{"launch_station",new BlockPos(150,-442,-28)},{"observation",new BlockPos(90,-367,-221)},{"dogma",new BlockPos(30,-566,280)}};
                for(var point:points)
                {
                    String goal=(String)point[0];BlockPos p=(BlockPos)point[1];level.getChunk(p);player.setPos(p.getX()+.5,p.getY(),p.getZ()+.5);
                    var guide=NervWayfindingR24.guide(player,goal);check("arrival_"+goal,guide.isPresent()&&guide.get().arrived());
                }
                player.setPos(32.5,-300,470.5);check("different_floor_does_not_attach",NervWayfindingR24.guide(player,"hangars").isEmpty());NervWayfindingR24.start(player,"stop");
                teleport(-147.5,95,-158,0,10);next(4);return;
            }
            if(stage==4&&timer>65)
            {
                BlockPos phone=new BlockPos(-148,95,-156);Vec3 target=new Vec3(-147.5,96.15,-155.50);
                hit=level.clip(new ClipContext(player.getEyePosition(),target,ClipContext.Block.OUTLINE,ClipContext.Fluid.NONE,player));
                check("phone_upper_cell_pick",hit.getType()==HitResult.Type.BLOCK&&hit.getBlockPos().equals(phone.above()));
                var clock=(PeriodFixtureBlockEntity)level.getBlockEntity(new BlockPos(-124,97,-156));
                check("server_clock_current",clock!=null&&Math.abs(clock.clockMillis()-System.currentTimeMillis())<2500);
                next(5);input="phone";return;
            }
            if(stage==5)
            {
                if(!inputs.contains("phone")||timer<30)return;check("phone_reply_from_upper_part",phoneReply);check("phone_busy_sound_packet",phoneSound);
                photo="working_public_phone";if(!photos.contains(photo))return;
                teleport(-123.5,81,-185.5,90,30);next(6);return;
            }
            if(stage==6&&timer>60)
            {
                var stool=new BlockPos(-125,81,-185);var target=new Vec3(-124.5,81.52,-184.5);
                hit=level.clip(new ClipContext(player.getEyePosition(),target,ClipContext.Block.OUTLINE,ClipContext.Fluid.NONE,player));
                check("stool_actual_outline_pick",hit.getType()==HitResult.Type.BLOCK&&hit.getBlockPos().equals(stool));next(7);input="sit";return;
            }
            if(stage==7)
            {
                if(!inputs.contains("sit")||timer<35)return;check("stool_stays_mounted",player.getVehicle() instanceof NervCommandSeatEntity&&player.getVehicle().isAlive());
                photo="cafe_seating";if(!photos.contains(photo))return;
                player.stopRiding();next(8);return;
            }
            if(stage==8&&timer>15)
            {check("stool_safe_dismount",!player.isPassenger()&&level.noCollision(player,player.getBoundingBox().deflate(.01))&&player.getY()>80.9);finish("");}
        }
        catch(Exception failure){ProjectSeele.LOGGER.error("R24 amenity review failed",failure);finish(failure.toString());}
    }
    private static void finish(String error)
    {
        if(player!=null){player.stopRiding();NervWayfindingR24.start(player,"stop");teleport(27.5,-407,282.5,0,0);}
        var report=new JsonObject();report.addProperty("passed",error.isEmpty());report.addProperty("error",error);report.addProperty("stage",stage);report.add("checks",checks);
        try{Files.writeString(world.resolve("r24_amenity_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception ignored){}
        finished=true;
    }
    private PeriodAmenityR24Review(){}
}
