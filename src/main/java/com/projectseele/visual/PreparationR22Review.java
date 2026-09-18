package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.world.FacilitySchemaV2;
import net.minecraft.core.*;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.*;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.*;
import net.minecraft.world.item.context.*;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.*;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Only the named R22 copy: finish native terrain and exercise a real piano placement. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class PreparationR22Review
{
    public static final boolean ENABLED="r22-prepare".equals(System.getProperty("projectseele.regionalBuild",""));
    public static final BlockPos PIANO=new BlockPos(13,-389,355);
    public static volatile boolean ready,played,released,finished;
    private static int age,generated,stage,timer;private static JsonArray chunks;private static Path world;
    public static volatile String failure="";
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent e)
    {
        if(!ENABLED||finished||e.phase!=TickEvent.Phase.END)return;
        var server=e.getServer();if(server.getPlayerList().getPlayers().isEmpty()||++age<100)return;
        world=server.getWorldPath(LevelResource.ROOT).normalize();if(!world.getFileName().toString().equals("SEELE_R22_REVIEW"))throw new IllegalStateException("R22 review only");
        var level=server.getLevel(FacilitySchemaV2.DIMENSION);var player=server.getPlayerList().getPlayers().get(0);
        try
        {
            if(stage==0)
            {
                if(chunks==null)chunks=JsonParser.parseString(Files.readString(world.resolve("r22_generate_chunks.json"))).getAsJsonArray();
                for(int i=0;i<2&&generated<chunks.size();i++,generated++){var q=chunks.get(generated).getAsJsonArray();level.getChunk(q.get(0).getAsInt(),q.get(1).getAsInt());}
                if(generated<chunks.size())return;
                Files.writeString(world.resolve("r22_generated_chunks_result.json"),chunks.toString());
                player.setGameMode(GameType.CREATIVE);player.stopRiding();player.teleportTo(level,13.5,-389,352.5,0,10);player.setDeltaMovement(Vec3.ZERO);level.getChunkAt(PIANO);
                var block=BuiltInRegistries.BLOCK.get(new ResourceLocation("grandpianomod","grand_piano"));
                if(level.getBlockState(PIANO).getBlock()!=block)
                {
                    for(var p:BlockPos.betweenClosed(9,-389,350,17,-386,361))if(!level.getBlockState(p).isAir())throw new IllegalStateException("Piano installation footprint is occupied: "+p);
                    var item=BuiltInRegistries.ITEM.get(new ResourceLocation("grandpianomod","grand_piano"));if(!(item instanceof BlockItem piano))throw new IllegalStateException("Piano item absent");
                    player.setItemInHand(InteractionHand.MAIN_HAND,new ItemStack(item));
                    var context=new UseOnContext(player,InteractionHand.MAIN_HAND,new BlockHitResult(Vec3.atCenterOf(PIANO.below()).add(0,.5,0),Direction.UP,PIANO.below(),false));
                    if(!piano.place(new BlockPlaceContext(context)).consumesAction())throw new IllegalStateException("Native multi-block piano placement failed");
                }
                player.setItemInHand(InteractionHand.MAIN_HAND,ItemStack.EMPTY);
                var be=level.getBlockEntity(PIANO);if(be==null)throw new IllegalStateException("Missing piano master");
                be.getClass().getMethod("setCustomName",String.class).invoke(be,"NERV 接待厅 · 三角钢琴");
                be.getClass().getMethod("setLidOpen",boolean.class).invoke(be,true);
                // The original bench is independently placeable and remains optional
                // for keyboard play. Keep the foreground access lane open.
                var bench=BuiltInRegistries.BLOCK.get(new ResourceLocation("grandpianomod","piano_bench"));var seat=new BlockPos(13,-389,353);
                if(level.getBlockState(seat).isAir())level.setBlock(seat,bench.defaultBlockState(),3);
                ready=true;stage=1;timer=0;ProjectSeele.LOGGER.info("R22 piano master installed with native multiblock geometry; generated={}",generated);return;
            }
            if(++timer>600)throw new IllegalStateException("Piano GUI/note test timeout");
            var piano=level.getBlockEntity(PIANO);boolean active=false;
            for(boolean key:(boolean[])piano.getClass().getMethod("getActiveKeys").invoke(piano))active|=key;
            if(active)played=true;
            if(played&&released&&!active)
            {
                var result=new JsonObject();result.addProperty("passed",true);result.addProperty("generated_chunks",generated);result.addProperty("native_keyboard_press_and_release",true);result.addProperty("master",PIANO.toShortString());
                Files.writeString(world.resolve("r22_piano_review.json"),result.toString());finished=true;
            }
        }
        catch(Exception x)
        {
            failure=x.toString();ProjectSeele.LOGGER.error("R22 preparation failed",x);finished=true;
            try{Files.writeString(world.resolve("r22_preparation_failure.txt"),failure);}catch(Exception ignored){}
        }
    }
}
