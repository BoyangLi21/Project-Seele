package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.world.*;
import net.minecraft.server.level.*;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Load existing identities and commission the UN capsule through its ordinary runtime. No test actors or teleports. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class R11MainFinalize
{
    public static final boolean ENABLED="r11-finalize".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile boolean finished;
    private static int age;private static final Set<ChunkPos> chunks=new HashSet<>();private static Map<String,UUID> military;
    private static JsonArray industrial;private static Path world;
    private static final TicketType<ChunkPos> TICKET=TicketType.create("r11_final_identity",Comparator.comparingLong(ChunkPos::toLong),100);
    private static JsonObject read(String name)throws Exception{return JsonParser.parseString(Files.readString(world.resolve(name))).getAsJsonObject();}
    private static void select(JsonArray rows,String point)
    {for(var row:rows){var p=row.getAsJsonObject().getAsJsonArray(point);chunks.add(new ChunkPos(BlockPos.containing(p.get(0).getAsDouble(),p.get(1).getAsDouble(),p.get(2).getAsDouble())));}}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;var server=event.getServer();if(server.getPlayerList().getPlayers().isEmpty()||++age<100)return;
        world=server.getWorldPath(LevelResource.ROOT).normalize();if(!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))throw new IllegalStateException("R11 finalization requires the actual TV world");
        try
        {
            var level=server.getLevel(FacilitySchemaV2.DIMENSION);var data=MilitaryR07Director.state(level);
            if(military==null)
            {
                if(!data.commissioned||data.entities.size()!=31)throw new IllegalStateException("Original military receipt changed");military=new LinkedHashMap<>(data.entities);
                select(read("r07_installations.json").getAsJsonArray("entities"),"position");select(read("r08_equipment_relocation.json").getAsJsonArray("moves"),"to");select(read("r08_native_details.json").getAsJsonArray("members"),"position");industrial=read("r08_detail_review.json").getAsJsonArray("identities");
            }
            if(age%20==0)
            {
                for(ChunkPos c:chunks){level.getChunkSource().addRegionTicket(TICKET,c,2,c);level.getChunk(c.x,c.z);}
                if(age<160)for(int i=0;i<3;i++)EvaLogisticsDirector.loadControlTarget(level,i);
            }
            if(age<230)return;
            List<String> missing=new ArrayList<>();for(var e:military.entrySet())if(!e.getValue().equals(data.entities.get(e.getKey()))||level.getEntity(e.getValue())==null)missing.add(e.getKey());
            for(var row:industrial){var r=row.getAsJsonObject();if(level.getEntity(UUID.fromString(r.get("uuid").getAsString()))==null)missing.add(r.get("key").getAsString());}
            if(!missing.isEmpty()){if(age>650)throw new IllegalStateException("Identity load failed: "+missing);return;}
            JsonArray fleet=new JsonArray();for(int i=0;i<3;i++)
            {
                var status=EvaLogisticsDirector.status(level,i);var eva=EvaLogisticsDirector.canonicalUnit(level,i);if(eva==null||!status.phase().equals("PARKED")||eva.isExperimentalUnit())throw new IllegalStateException("Canonical fleet not parked: "+status);
                JsonObject r=new JsonObject();r.addProperty("variant",i);r.addProperty("uuid",eva.getUUID().toString());r.addProperty("phase",status.phase());fleet.add(r);
            }
            if(data.phase!=MilitaryR07Director.Phase.WET)throw new IllegalStateException("UN cell state differs from the WET baseline: "+data.phase);
            var un=(EvaPrototypeEntity)level.getEntity(military.get("prototype"));var plug=UNPlugDirector.capsule(un);
            if(plug==null||!plug.isIndependentUNPlug()||plug.getLinkedEva()!=un||plug.getInsertionStage()!=EntryPlugCarrierEntity.STAGE_SUSPENDED)throw new IllegalStateException("UN capsule ownership or parked stage failed");
            JsonObject report=new JsonObject();report.addProperty("passed",true);report.add("canonical_fleet",fleet);report.addProperty("military_original_identities",military.size());report.addProperty("industrial_members",industrial.size());report.addProperty("un_uuid",un.getUUID().toString());report.addProperty("un_capsule_uuid",plug.getUUID().toString());report.addProperty("un_cell","WET");report.addProperty("player_teleported_by_finalize",false);report.addProperty("time_ticks",age);write(report);finished=true;
            for(ChunkPos c:chunks)level.getChunkSource().removeRegionTicket(TICKET,c,2,c);ProjectSeele.LOGGER.info("R11 MAIN FINAL PASS {}",report);
        }
        catch(Exception error)
        {JsonObject r=new JsonObject();r.addProperty("passed",false);r.addProperty("error",error.toString());try{write(r);}catch(Exception ignored){}ProjectSeele.LOGGER.error("R11 MAIN FINAL FAILED",error);finished=true;}
    }
    private static void write(JsonObject report)throws Exception
    {Files.writeString(world.resolve("r11_final_identities.json"),report.toString());}
}
