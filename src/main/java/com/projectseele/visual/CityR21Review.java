package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.world.*;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Native city movement precedes any claim about a clear battle surface. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class CityR21Review
{
    private static final String MODE=System.getProperty("projectseele.regionalBuild","");
    private static final boolean ENABLED=MODE.equals("r21-city-retract")||MODE.equals("r21-city-restore");
    private static int age;private static boolean requested,finished;
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent e)
    {
        if(!ENABLED||finished||e.phase!=TickEvent.Phase.END)return;
        var server=e.getServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_R21_REVIEW"))throw new IllegalStateException("R21 city review boundary");
        var level=server.getLevel(FacilitySchemaV2.DIMENSION);if(level==null||++age<160)return;
        try
        {
            var origin=IntegratedNervMapBuilder.tokyo3Origin(level);boolean retract=MODE.endsWith("retract");
            if(!requested)
            {
                var footprints=new JsonArray();for(var t:ThirdTokyoSurfaceBuilder.movableBuildings(level)){var a=new JsonArray();for(int n:new int[]{origin.getX()+t.x()-t.halfSize(),origin.getZ()+t.z()-t.halfSize(),origin.getX()+t.x()+t.halfSize(),origin.getZ()+t.z()+t.halfSize(),t.height()})a.add(n);footprints.add(a);}
                Files.writeString(world.resolve("r21_moving_city_footprints.json"),footprints.toString());
                var result=Tokyo3RetractionDirector.request(level,origin,retract);ProjectSeele.LOGGER.info("R21 CITY requested {}",result);requested=true;
            }
            int depth=Tokyo3RetractionDirector.depth(level,origin),target=retract?ThirdTokyoSurfaceBuilder.maximumRetractionDepth(origin):0;
            if(age%200==0)ProjectSeele.LOGGER.info("R21 CITY progress {}/{}",depth,target);
            if(depth==target)
            {
                var proof=new JsonObject();proof.addProperty("native_movement_complete",true);proof.addProperty("depth",depth);proof.addProperty("target",target);proof.addProperty("ticks",age);Files.writeString(world.resolve(MODE+".json"),proof.toString());finished=true;server.halt(false);
            }
            if(age>18000)throw new IllegalStateException("City movement timed out at "+depth+"/"+target);
        }
        catch(Exception x){try{Files.writeString(world.resolve(MODE+"_failure.txt"),x.toString());}catch(Exception ignored){}finished=true;ProjectSeele.LOGGER.error("R21 native city test failed",x);server.halt(false);}
    }
    private CityR21Review(){}
}
