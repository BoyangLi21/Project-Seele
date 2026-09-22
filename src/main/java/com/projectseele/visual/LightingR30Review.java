package com.projectseele.visual;

import com.google.gson.*;
import com.mojang.authlib.GameProfile;
import com.projectseele.registry.ModBlocks;
import com.projectseele.world.*;
import net.minecraft.core.*;
import net.minecraft.server.level.*;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.level.*;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.*;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Native light propagation and real commander-lever interaction on sampled public routes. */
@Mod.EventBusSubscriber(modid="projectseele")
public final class LightingR30Review
{
    private static final boolean ENABLED="r30-lighting".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final TicketType<ChunkPos> TICKET=TicketType.create("r30_lighting_review",Comparator.comparingLong(ChunkPos::toLong),100);
    private static int age,index,wait,circuitStage;private static boolean done;private static ChunkPos current;
    private static JsonArray samples,lamps;private static BlockPos lever;private static BlockState originalLever;
    private static final JsonArray results=new JsonArray();private static final JsonObject report=new JsonObject();
    private static BlockPos position(JsonArray a){return new BlockPos(a.get(0).getAsInt(),a.get(1).getAsInt(),a.get(2).getAsInt());}
    private static void retain(ServerLevel l,BlockPos p){var c=new ChunkPos(p);l.getChunkSource().addRegionTicket(TICKET,c,3,c);l.getChunk(p);}
    private static void check(String key,boolean value){report.addProperty(key,value);if(!value)throw new IllegalStateException(key);}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END)return;var server=event.getServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_FIELD_R30_REVIEW"))throw new IllegalStateException("Wrong lighting review world");var l=server.getLevel(FacilitySchemaV2.DIMENSION);if(l==null)return;l.resetEmptyTime();
        try
        {
            if(++age<60)return;
            if(samples==null)
            {
                samples=JsonParser.parseString(Files.readString(world.resolve("r30_lighting_samples.json"))).getAsJsonArray();var circuit=JsonParser.parseString(Files.readString(world.resolve("facility_lighting_r30.json"))).getAsJsonObject();lamps=circuit.getAsJsonArray("command_lamps");lever=position(circuit.getAsJsonArray("command_lever"));retain(l,lever);originalLever=l.getBlockState(lever);wait=30;return;
            }
            if(circuitStage<3)
            {
                retain(l,lever);for(var raw:lamps)retain(l,position(raw.getAsJsonArray()));if(wait-->0)return;
                boolean wantOn=circuitStage==1;
                if(circuitStage==0||circuitStage==2)
                {
                    boolean target=circuitStage==0;
                    if(l.getBlockState(lever).getValue(BlockStateProperties.POWERED)!=target)
                    {
                        var p=FakePlayerFactory.get(l,new GameProfile(UUID.fromString("fc4d64ed-66b6-41b1-8c9c-232071ce0e30"),"R30Lighting"));p.setPos(28.5,-406,275.5);
                        l.getBlockState(lever).use(l,p,InteractionHand.MAIN_HAND,new BlockHitResult(Vec3.atCenterOf(lever),Direction.UP,lever,false));
                    }
                    if(circuitStage==0){circuitStage=1;wait=20;return;}
                    circuitStage=3;wait=20;return;
                }
                boolean all=true;for(var raw:lamps){var p=position(raw.getAsJsonArray());var s=l.getBlockState(p);all&=s.is(ModBlocks.NERV_CEILING_LIGHT.get())&&s.getValue(BlockStateProperties.LIT);}
                check("commander_lever_switches_all_lamps_on",all);circuitStage=2;wait=2;return;
            }
            if(wait-->0)return;
            if(!report.has("commander_lamps_off"))
            {
                boolean off=true;for(var raw:lamps){var p=position(raw.getAsJsonArray());off&=!l.getBlockState(p).getValue(BlockStateProperties.LIT);}check("commander_lamps_off",off);l.setBlock(lever,originalLever,3);
            }
            for(int n=0;n<8&&index<samples.size();n++)
            {
                var sample=samples.get(index).getAsJsonObject();BlockPos feet=position(sample.getAsJsonArray("feet"));var chunk=new ChunkPos(feet);retain(l,feet);
                if(!chunk.equals(current)){current=chunk;wait=10;return;}
                if(!l.isPositionEntityTicking(feet)){wait=5;return;}
                var row=sample.deepCopy();int block=l.getBrightness(LightLayer.BLOCK,feet.above()),sky=l.getBrightness(LightLayer.SKY,feet.above());row.addProperty("block_light",block);row.addProperty("sky_light",sky);row.addProperty("visible_light",Math.max(block,sky));results.add(row);index++;
            }
            if(index==samples.size())
            {
                int dark=0;for(var raw:results)if(raw.getAsJsonObject().get("visible_light").getAsInt()<5)dark++;
                report.addProperty("sample_count",results.size());report.addProperty("dark_samples",dark);report.add("samples",results);report.addProperty("passed",dark==0);finish(l,world);
            }
        }
        catch(Exception e){report.addProperty("passed",false);report.addProperty("error",e.toString());com.projectseele.ProjectSeele.LOGGER.error("R30 lighting review failed",e);if(lever!=null&&originalLever!=null)l.setBlock(lever,originalLever,3);finish(l,world);}
    }
    private static void finish(ServerLevel l,Path world){done=true;try{Files.writeString(world.resolve("r30_lighting_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception e){throw new IllegalStateException(e);}l.getServer().halt(false);}
    private LightingR30Review(){}
}
