package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.world.FacilitySchemaV2;
import com.projectseele.world.RegionalGatewayDirector;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.ChunkStatus;

/** Explicit regional construction stages; ordinary game sessions never enter this driver. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID)
public final class RegionalWorldBuildDriver
{
    private static final String MODE = System.getProperty("projectseele.regionalBuild", "");
    private static int age, sample;
    private static boolean done;
    private static final JsonArray HEIGHTS = new JsonArray();
    private static JsonArray chunks;
    private static int queued,completed;
    private static final Map<ChunkPos,CompletableFuture<?>> PENDING=new LinkedHashMap<>();
    private static boolean registryChecked, gateReady;
    private static final Map<String,Set<String>> VEHICLE_POSITIONS = new LinkedHashMap<>();

    @SubscribeEvent
    public static void tick(TickEvent.ServerTickEvent event)
    {
        if (MODE.isEmpty() || MODE.equals("passengers") || MODE.equals("transit-riding") || done || event.phase != TickEvent.Phase.END) return;
        MinecraftServer server=event.getServer();
        Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if (!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))
            throw new IllegalStateException("Regional construction refuses a different world");
        try
        {
            if (++age<100) return;
            if (Files.exists(world.resolve("regional_stop_requested")))
            {
                Files.delete(world.resolve("regional_stop_requested"));
                stop(server);
                return;
            }
            ServerLevel level=server.getLevel(FacilitySchemaV2.DIMENSION);
            if (MODE.equals("commission"))
            {
                if (!registryChecked)
                {
                    var states = JsonParser.parseString(Files.readString(world.resolve("regional_states.json"))).getAsJsonArray();
                    for (JsonElement value : states)
                    {
                        String full = value.getAsString();
                        String name = full.split("\\[")[0];
                        ResourceLocation id = new ResourceLocation(name);
                        if (!BuiltInRegistries.BLOCK.containsKey(id)) throw new IllegalStateException("Unknown authored block " + full);
                        var definition = BuiltInRegistries.BLOCK.get(id).getStateDefinition();
                        if (full.contains("[")) for (String property : full.substring(full.indexOf('[')+1,full.length()-1).split(","))
                        {
                            String[] pair = property.split("=");
                            var key = definition.getProperty(pair[0]);
                            if (key == null || key.getValue(pair[1]).isEmpty()) throw new IllegalStateException("Invalid authored state " + full);
                        }
                    }
                    registryChecked = true;
                    ProjectSeele.LOGGER.info("REGIONAL PALETTE PASS uniqueStates={}", states.size());
                }
                if (!gateReady)
                {
                    gateReady = RegionalGatewayDirector.commission(level);
                    if (!gateReady) { if (age>1000) throw new IllegalStateException("Gateway controller did not initialize"); return; }
                    var group = RegionalGatewayDirector.group(level);
                    int cars = 0;
                    for (int i=0;i<group.getFloorCount();i++) if (group.isCageAvailableAt(i,true,null)) cars++;
                    if (cars!=1) throw new IllegalStateException("Expected one complete regional car; found " + cars);
                }
                if (age%20!=0) return;
                JsonObject transit = RegionalNativeTransitInspection.snapshot();
                if (transit==null) { if(age>1000)throw new IllegalStateException("MTR world unavailable"); return; }
                if (transit.get("rails").getAsInt()!=98 || transit.get("routes").getAsInt()!=7)
                    throw new IllegalStateException("Incomplete installed MTR network " + transit);
                for (JsonElement entry : transit.getAsJsonArray("vehicles"))
                {
                    var v=entry.getAsJsonObject();
                    VEHICLE_POSITIONS.computeIfAbsent(v.get("siding").getAsString(),key->new HashSet<>())
                            .add(Math.round(v.get("x").getAsDouble())+","+Math.round(v.get("y").getAsDouble())+","+Math.round(v.get("z").getAsDouble()));
                }
                if(age%200==0)ProjectSeele.LOGGER.info("REGIONAL LIVE MTR vehicleSamples={}",VEHICLE_POSITIONS.entrySet().stream().map(e->e.getKey()+":"+e.getValue().size()).toList());
                if(VEHICLE_POSITIONS.size()>=7 && VEHICLE_POSITIONS.values().stream().allMatch(set->set.size()>=5))
                {
                    transit.addProperty("paletteValid",true);transit.addProperty("nativeGatewayCarCount",1);
                    Files.writeString(world.resolve("regional_commission_receipt.json"),new GsonBuilder().setPrettyPrinting().create().toJson(transit));
                    ProjectSeele.LOGGER.info("REGIONAL COMMISSION COMPLETE nativeLines=7 nativeLargeCar=1");stop(server);
                }
                else if(age>4800)throw new IllegalStateException("Not every installed MTR line produced moving vehicles");
                return;
            }
            if (MODE.equals("survey"))
            {
                int nx=61,nz=46,total=nx*nz;
                for(int n=0;n<12 && sample<total;n++,sample++)
                {
                    int x=-2400+(sample%nx)*64,z=-960+(sample/nx)*64;
                    int y=level.getChunkSource().getGenerator().getBaseHeight(x,z,Heightmap.Types.OCEAN_FLOOR_WG,
                            level,level.getChunkSource().randomState());
                    JsonArray point=new JsonArray();point.add(x);point.add(y);point.add(z);HEIGHTS.add(point);
                }
                if(sample%240==0)ProjectSeele.LOGGER.info("REGIONAL SURVEY {}/{}",sample,total);
                if(sample==total)
                {
                    JsonObject report=new JsonObject();report.addProperty("seed",level.getSeed());
                    report.add("native_heights",HEIGHTS);
                    Files.writeString(world.resolve("regional_surface_survey.json"),new Gson().toJson(report));
                    ProjectSeele.LOGGER.info("REGIONAL SURVEY COMPLETE samples={}",sample);
                    stop(server);
                }
                return;
            }
            if (MODE.equals("generate") || MODE.equals("generate-extra"))
            {
                if(chunks==null)
                {
                    chunks=JsonParser.parseString(Files.readString(world.resolve("regional_plan.json"))).getAsJsonObject()
                            .getAsJsonArray(MODE.equals("generate-extra")?"extra_chunks":"chunks");
                    ProjectSeele.LOGGER.info("REGIONAL GENERATION START chunks={}",chunks.size());
                }
                var iterator=PENDING.entrySet().iterator();
                while(iterator.hasNext())
                {
                    var item=iterator.next();if(!item.getValue().isDone())continue;
                    Object result=item.getValue().join();
                    if(result instanceof com.mojang.datafixers.util.Either<?,?> either && either.right().isPresent())
                        throw new IllegalStateException("Chunk failed "+item.getKey());
                    iterator.remove();completed++;
                    if(completed%256==0)ProjectSeele.LOGGER.info("REGIONAL GENERATION {}/{}",completed,chunks.size());
                }
                for(int n=0;n<4 && queued<chunks.size() && PENDING.size()<12;n++)
                {
                    JsonArray pair=chunks.get(queued++).getAsJsonArray();ChunkPos p=new ChunkPos(pair.get(0).getAsInt(),pair.get(1).getAsInt());
                    PENDING.put(p,level.getChunkSource().getChunkFuture(p.x,p.z,ChunkStatus.FULL,true));
                }
                if(completed==chunks.size())
                {
                    Files.writeString(world.resolve(MODE.equals("generate-extra")?"regional_extra_generation_complete.json":"regional_generation_complete.json"),"{\"chunks\":"+completed+"}");
                    ProjectSeele.LOGGER.info("REGIONAL GENERATION COMPLETE chunks={}",completed);stop(server);
                }
                return;
            }
            throw new IllegalStateException("Unknown regional stage "+MODE);
        }
        catch(Exception exception)
        {
            ProjectSeele.LOGGER.error("REGIONAL STAGE FAILED "+MODE,exception);
            try { Files.writeString(world.resolve("regional_"+MODE+"_failure.txt"),exception.toString()); }
            catch(Exception ignored) { }
            stop(server);
        }
    }

    private static void stop(MinecraftServer server)
    {
        done=true;
        if(server.isDedicatedServer())server.halt(false);
    }
}
