package com.projectseele.client.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.client.SkySourceScanR24;
import com.projectseele.registry.ModBlocks;
import net.minecraft.client.Minecraft;
import net.minecraft.core.*;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.chunk.*;
import net.minecraft.world.level.lighting.ChunkSkyLightSources;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Compare the injected initializer with the untouched vanilla method on real client chunks. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class SkySourceR24Review
{
    private static final boolean ENABLED="r24-skylight".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final int[][] SITES={{-120,96,-172},{30,-420,320},{44,-566,270},{6400,76,-6650},{1184,96,472},{-2752,96,-960}};
    private static final JsonArray results=new JsonArray();private static final List<ChunkAccess> pending=new ArrayList<>();
    private static final Set<Long> visited=new HashSet<>();private static int age,site=-1,timer,index,end,oldDistance;private static boolean initialized,requested,done,oldPause;
    private static long baselineNanos,fastNanos;private static int columns;private static Path output;
    private static void compare(ChunkAccess chunk,String name)
    {
        var mc=Minecraft.getInstance();var vanilla=new ChunkSkyLightSources(mc.level);var fast=new ChunkSkyLightSources(mc.level);
        SkySourceScanR24.VANILLA.set(true);vanilla.fillFrom(chunk);SkySourceScanR24.VANILLA.set(false);fast.fillFrom(chunk);
        int different=0;
        for(int x=0;x<16;x++)for(int z=0;z<16;z++)if(vanilla.getLowestSourceY(x,z)!=fast.getLowestSourceY(x,z))different++;
        long a=0,b=0;
        for(int repeat=0;repeat<4;repeat++)
        {
            for(boolean base:repeat%2==0?new boolean[]{true,false}:new boolean[]{false,true})
            {
                SkySourceScanR24.VANILLA.set(base);long start=System.nanoTime();(base?vanilla:fast).fillFrom(chunk);long elapsed=System.nanoTime()-start;
                if(base)a+=elapsed;else b+=elapsed;
            }
        }
        SkySourceScanR24.VANILLA.remove();baselineNanos+=a;fastNanos+=b;columns+=256;
        var row=new JsonObject();row.addProperty("case",name);row.addProperty("x",chunk.getPos().x);row.addProperty("z",chunk.getPos().z);row.addProperty("different_columns",different);row.addProperty("baseline_ns",a);row.addProperty("fast_ns",b);results.add(row);
        if(different!=0)throw new IllegalStateException("Skylight columns changed: "+name+" "+chunk.getPos()+" count="+different);
    }
    private static ProtoChunk synthetic(String type)
    {
        var mc=Minecraft.getInstance();var chunk=new ProtoChunk(new ChunkPos(0,0),UpgradeData.EMPTY,mc.level,mc.level.registryAccess().registryOrThrow(Registries.BIOME),null);
        int min=mc.level.getMinBuildHeight(),max=mc.level.getMaxBuildHeight();var pos=new BlockPos.MutableBlockPos();var random=new Random(19950919);
        if(type.equals("empty"))return chunk;
        if(type.equals("transparent_shells"))
        {
            for(int y=min+8;y<max;y+=23)for(int x=0;x<16;x++)for(int z=0;z<16;z++)
                chunk.setBlockState(pos.set(x,y,z),(x+z)%2==0?ModBlocks.GEOFRONT_SKYWEAVE.get().defaultBlockState():Blocks.LIGHT.defaultBlockState(),false);
            return chunk;
        }
        var states=List.of(Blocks.GLASS.defaultBlockState(),ModBlocks.GEOFRONT_SKYWEAVE.get().defaultBlockState(),Blocks.STONE.defaultBlockState(),
                Blocks.TINTED_GLASS.defaultBlockState(),Blocks.OAK_SLAB.defaultBlockState(),Blocks.OAK_SLAB.defaultBlockState().setValue(net.minecraft.world.level.block.state.properties.BlockStateProperties.SLAB_TYPE,net.minecraft.world.level.block.state.properties.SlabType.TOP),
                Blocks.OAK_STAIRS.defaultBlockState(),Blocks.OAK_TRAPDOOR.defaultBlockState(),Blocks.WATER.defaultBlockState(),Blocks.LIGHT.defaultBlockState(),
                Blocks.LIGHT.defaultBlockState().setValue(net.minecraft.world.level.block.state.properties.BlockStateProperties.WATERLOGGED,true),Blocks.GLASS_PANE.defaultBlockState(),
                Blocks.CAVE_AIR.defaultBlockState(),Blocks.VOID_AIR.defaultBlockState());
        for(int i=0;i<9000;i++)chunk.setBlockState(pos.set(random.nextInt(16),min+random.nextInt(max-min),random.nextInt(16)),states.get(random.nextInt(states.size())),false);
        return chunk;
    }
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.level==null||mc.player==null||mc.getSingleplayerServer()==null)return;
        try
        {
            if(!initialized)
            {
                var world=mc.getSingleplayerServer().getWorldPath(LevelResource.ROOT).normalize();if(!world.getFileName().toString().equals("SEELE_R24_TV_REVIEW"))throw new IllegalStateException("Wrong light review world");
                initialized=true;oldPause=mc.options.pauseOnLostFocus;oldDistance=mc.options.renderDistance().get();mc.options.pauseOnLostFocus=false;mc.options.renderDistance().set(6);mc.options.broadcastOptions();
                output=mc.gameDirectory.toPath().resolve("../artifacts/facility_r24/validation/skylight_native.json").normalize();mc.player.connection.sendCommand("gamemode spectator");
            }
            if(done){if(++end>30){mc.options.pauseOnLostFocus=oldPause;mc.options.renderDistance().set(oldDistance);mc.options.broadcastOptions();mc.stop();}return;}
            if(++age<100)return;if(age>4500)throw new IllegalStateException("Light review timeout");
            if(site<0)
            {
                for(String kind:List.of("empty","transparent_shells","mixed_boundaries"))compare(synthetic(kind),kind);
                site=0;
            }
            if(site==SITES.length){finish("");return;}
            int[] location=SITES[site];
            if(!requested)
            {
                mc.player.connection.sendCommand("execute in projectseele:geofront run tp @s "+location[0]+" "+location[1]+" "+location[2]);timer=0;requested=true;pending.clear();index=0;return;
            }
            if(!mc.level.dimension().location().toString().equals("projectseele:geofront")||mc.player.position().distanceToSqr(location[0],location[1],location[2])>4)return;
            if(++timer<180)return;
            if(pending.isEmpty())
            {
                for(int dx=-3;dx<=3;dx++)for(int dz=-3;dz<=3;dz++)
                {
                    int x=(location[0]>>4)+dx,z=(location[2]>>4)+dz;
                    var chunk=mc.level.getChunkSource().getChunk(x,z,ChunkStatus.FULL,false);if(chunk==null)return;
                }
                for(int dx=-3;dx<=3;dx++)for(int dz=-3;dz<=3;dz++)
                {
                    int x=(location[0]>>4)+dx,z=(location[2]>>4)+dz;
                    if(visited.add(ChunkPos.asLong(x,z)))pending.add(mc.level.getChunkSource().getChunk(x,z,ChunkStatus.FULL,false));
                }
            }
            for(int n=0;n<4&&index<pending.size();n++,index++)compare(pending.get(index),"real_site_"+site);
            if(index==pending.size()){ProjectSeele.LOGGER.info("R24 SKY COMPARE site={} columns={} speedup={}",site,columns,baselineNanos/(double)Math.max(1,fastNanos));site++;requested=false;}
        }
        catch(Exception error){ProjectSeele.LOGGER.error("R24 sky-source verification failed",error);finish(error.toString());}
    }
    private static void finish(String error)
    {
        SkySourceScanR24.VANILLA.remove();var report=new JsonObject();report.addProperty("passed",error.isEmpty());report.addProperty("error",error);report.addProperty("columns",columns);report.addProperty("baseline_ns",baselineNanos);report.addProperty("fast_ns",fastNanos);report.addProperty("initializer_speedup",baselineNanos/(double)Math.max(1,fastNanos));report.add("cases",results);
        try{Files.writeString(output,new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception ignored){}done=true;
    }
    private SkySourceR24Review(){}
}
