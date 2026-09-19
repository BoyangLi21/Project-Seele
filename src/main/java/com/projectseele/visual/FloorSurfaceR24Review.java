package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.world.FacilitySchemaV2;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.*;
import net.minecraft.world.entity.MoverType;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Whole passenger floor coverage, not just selected corridor centre lines. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class FloorSurfaceR24Review
{
    private static final boolean ENABLED="r24-floors".equals(System.getProperty("projectseele.regionalBuild",""));
    private static int age,index,supported,occupied,stepped;
    private static boolean done;private static JsonArray points;private static Path world;
    private static final JsonArray failures=new JsonArray();
    private static long lastChunk=Long.MIN_VALUE;
    private static net.minecraftforge.common.util.FakePlayer probe;
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END||++age<100)return;
        var server=event.getServer();var level=server.getLevel(FacilitySchemaV2.DIMENSION);if(level==null)return;
        try
        {
            if(points==null)
            {
                world=server.getWorldPath(LevelResource.ROOT).normalize();
                if(!world.getFileName().toString().equals("SEELE_R24_TV_REVIEW"))throw new IllegalStateException("Floor audit review boundary");
                points=JsonParser.parseString(Files.readString(world.resolve("r24_floor_grid.json"))).getAsJsonArray();
            }
            level.resetEmptyTime();
            if(probe==null){probe=FakePlayerFactory.get(level,new com.mojang.authlib.GameProfile(UUID.fromString("f3f6c231-62c0-4055-92e1-bfc310002424"),"R24 floor audit"));probe.setGameMode(GameType.SURVIVAL);probe.getAbilities().flying=false;probe.noPhysics=false;probe.setMaxUpStep(.6F);}
            var player=probe;
            for(int batch=0;batch<192&&index<points.size();batch++,index++)
            {
                var test=points.get(index).getAsJsonObject();var p=test.getAsJsonArray("feet");Vec3 start=new Vec3(p.get(0).getAsDouble(),p.get(1).getAsDouble(),p.get(2).getAsDouble());
                var block=BlockPos.containing(start);long chunk=net.minecraft.world.level.ChunkPos.asLong(block.getX()>>4,block.getZ()>>4);
                // A getChunk() read is not a persistent ticket. Distant audit
                // chunks can unload between ticks, including the cached last
                // chunk. Reload at every batch boundary before collision reads.
                if(batch==0||chunk!=lastChunk)
                {
                    int cx=block.getX()>>4,cz=block.getZ()>>4;
                    for(int x=cx-1;x<=cx+1;x++)for(int z=cz-1;z<=cz+1;z++)level.getChunk(x,z);
                    lastChunk=chunk;
                }
                player.setPos(start);player.setDeltaMovement(Vec3.ZERO);player.setOnGround(false);player.fallDistance=0;
                String initialBox=player.getBoundingBox().toString();double initialY=player.getY();
                boolean collision=level.getBlockCollisions(player,player.getBoundingBox().deflate(.02)).iterator().hasNext();
                if(collision)
                {
                    if(level.getBlockState(block).isAir()&&level.getBlockState(block.above()).isAir())
                    {var failure=test.deepCopy();failure.addProperty("reason","shape intrudes into nominal clear body cells");failures.add(failure);}
                    else occupied++;
                    continue;
                }
                for(int i=0;i<8;i++)player.move(MoverType.SELF,new Vec3(0,-.35,0));
                double drop=start.y-player.getY();
                if(drop<=.26){supported++;continue;}
                boolean shaped=false;
                for(int dy=0;dy<=2;dy++)
                {
                    var state=level.getBlockState(block.below(dy));
                    shaped|=state.getBlock() instanceof StairBlock||state.getBlock() instanceof SlabBlock
                            ||net.minecraft.core.registries.BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString().startsWith("mtr:escalator_step");
                }
                if(shaped&&drop<=.65){stepped++;continue;}
                var failure=test.deepCopy();failure.addProperty("reason","unexpected floor drop");failure.addProperty("actual_y",player.getY());failure.addProperty("drop",drop);
                failure.addProperty("batch_slot",batch);failure.addProperty("initial_y",initialY);failure.addProperty("initial_box",initialBox);failure.addProperty("end_box",player.getBoundingBox().toString());
                failure.addProperty("no_physics",player.noPhysics);failure.addProperty("below",level.getBlockState(block.below()).toString());failures.add(failure);
            }
            if(index%3840==0)ProjectSeele.LOGGER.info("R24 FLOOR COVERAGE {}/{} failures={}",index,points.size(),failures.size());
            if(index==points.size())
            {
                var report=new JsonObject();report.addProperty("passed",failures.isEmpty());report.addProperty("total",index);report.addProperty("supported",supported);report.addProperty("occupied",occupied);report.addProperty("shaped_steps",stepped);report.add("failures",failures);
                Files.writeString(world.resolve("r24_floor_coverage.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));done=true;server.halt(false);
            }
        }
        catch(Exception failure)
        {
            ProjectSeele.LOGGER.error("R24 full-floor audit failed",failure);
            try{Files.writeString(world.resolve("r24_floor_coverage_failure.txt"),failure.toString());}catch(Exception ignored){}
            done=true;server.halt(false);
        }
    }
    private FloorSurfaceR24Review(){}
}
