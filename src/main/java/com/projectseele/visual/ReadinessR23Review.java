package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.world.*;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Explicit installation review: never runs during ordinary play. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class ReadinessR23Review
{
    private static final boolean ENABLED="r23-readiness".equals(System.getProperty("projectseele.regionalBuild",""));
    private static int age,stage;private static boolean done;private static JsonArray specs;private static JsonObject installed;
    private static Map<String,UUID> original;
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END||++age<100)return;
        var server=event.getServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_R22_REVIEW"))throw new IllegalStateException("Readiness review is copy-only");
        var level=server.getLevel(FacilitySchemaV2.DIMENSION);if(level==null)return;
        level.resetEmptyTime();
        try
        {
            if(stage==0)
            {
                specs=JsonParser.parseString(Files.readString(world.resolve("military_readiness_r23.json"))).getAsJsonObject().getAsJsonArray("vehicles");
                for(var value:specs)
                {
                    var p=value.getAsJsonObject().getAsJsonArray("position");var pos=new BlockPos(p.get(0).getAsInt(),p.get(1).getAsInt(),p.get(2).getAsInt());var chunk=new net.minecraft.world.level.ChunkPos(pos);
                    level.getChunkSource().addRegionTicket(net.minecraft.server.level.TicketType.PORTAL,chunk,2,pos);
                }
                original=new LinkedHashMap<>(MilitaryR07Director.state(level).entities);
                installed=MilitaryR07Director.reinforce(level,specs);stage=1;age=0;
            }
            else if(age>=160)
            {
                var state=MilitaryR07Director.state(level);for(var entry:original.entrySet())if(!entry.getValue().equals(state.entities.get(entry.getKey())))throw new IllegalStateException("Original military UUID changed");
                JsonArray rows=new JsonArray();int verified=0;
                for(var value:specs)
                {
                    var spec=value.getAsJsonObject();var p=spec.getAsJsonArray("position");var point=new BlockPos(p.get(0).getAsInt(),p.get(1).getAsInt(),p.get(2).getAsInt());level.getChunkAt(point);
                    var id=state.entities.get(spec.get("key").getAsString());var entity=level.getEntity(id);
                    if(entity==null){age=140;return;}
                    if(!entity.isAlive()||entity.getY()<p.get(1).getAsDouble()-1)throw new IllegalStateException("Vehicle not supported: "+spec.get("key"));
                    if(!entity.getTags().contains("seele_r23_readiness"))throw new IllegalStateException("Wrong readiness vehicle identity");
                    JsonObject row=new JsonObject();row.addProperty("key",spec.get("key").getAsString());row.addProperty("uuid",entity.getStringUUID());row.addProperty("type",spec.get("id").getAsString());row.addProperty("energy",((Number)entity.getClass().getMethod("getEnergy").invoke(entity)).intValue());row.addProperty("floor_y",entity.getY());rows.add(row);verified++;
                }
                if(verified!=144)throw new IllegalStateException("Incomplete reinforcement count: "+verified);
                JsonObject result=new JsonObject();result.addProperty("passed",true);result.addProperty("additional_vehicles",verified);result.addProperty("original_identities_retained",original.size());result.add("vehicles",rows);result.add("commission",installed);
                Files.writeString(world.resolve("readiness_r23_pass.json"),new GsonBuilder().setPrettyPrinting().create().toJson(result));done=true;server.halt(false);
            }
        }
        catch(Exception error)
        {
            try{Files.writeString(world.resolve("readiness_r23_failure.txt"),error.toString());}catch(Exception ignored){}
            ProjectSeele.LOGGER.error("R23 readiness review failed",error);done=true;server.halt(false);
        }
    }
}
