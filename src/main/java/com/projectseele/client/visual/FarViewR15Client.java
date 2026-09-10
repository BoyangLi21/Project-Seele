package com.projectseele.client.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.visual.FarViewR15Review;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class FarViewR15Client
{
    private static int view=-1,end;private static long previous,started;private static Path folder;
    private static final List<Double> times=new ArrayList<>();private static final JsonArray results=new JsonArray();
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!FarViewR15Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();mc.options.pauseOnLostFocus=false;
        if(FarViewR15Review.finished&&++end>40){mc.options.hideGui=false;mc.stop();}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!FarViewR15Review.ENABLED||event.phase!=TickEvent.Phase.END||FarViewR15Review.index<0||FarViewR15Review.finished||FarViewR15Review.next)return;
        var mc=Minecraft.getInstance();if(mc.level==null||mc.player==null)return;
        try
        {
            if(folder==null){folder=mc.gameDirectory.toPath().resolve("../artifacts/staff_world_r15/far_native_"+System.currentTimeMillis()).normalize();Files.createDirectories(folder);}
            long now=System.nanoTime();
            if(view!=FarViewR15Review.index){view=FarViewR15Review.index;times.clear();started=previous=now;}
            mc.options.hideGui=true;mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);
            double seconds=(now-started)/1e9;if(seconds>55&&previous>0)times.add((now-previous)/1e6);previous=now;
            // Allow fresh disk LODs to bake, then measure stationary rendering.
            if(seconds<85)return;
            var shot=FarViewR15Review.SHOTS[view];try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){image.writeToFile(folder.resolve(shot.name()+".png"));}
            var row=new JsonObject();row.addProperty("view",shot.name());row.addProperty("frames",times.size());Collections.sort(times);
            row.addProperty("median_ms",times.get(times.size()/2));row.addProperty("p95_ms",times.get((int)(times.size()*.95)));row.addProperty("p99_ms",times.get((int)(times.size()*.99)));
            row.addProperty("heap_used_mib",(Runtime.getRuntime().totalMemory()-Runtime.getRuntime().freeMemory())/1048576);row.addProperty("heap_max_mib",Runtime.getRuntime().maxMemory()/1048576);row.addProperty("render_chunks",mc.options.renderDistance().get());row.addProperty("simulation_chunks",mc.options.simulationDistance().get());
            row.addProperty("dh_loaded",net.minecraftforge.fml.ModList.get().isLoaded("distanthorizons"));row.addProperty("embeddium_loaded",net.minecraftforge.fml.ModList.get().isLoaded("embeddium"));row.addProperty("ferritecore_loaded",net.minecraftforge.fml.ModList.get().isLoaded("ferritecore"));results.add(row);
            Files.writeString(folder.resolve("measurements.json"),new GsonBuilder().setPrettyPrinting().create().toJson(results));FarViewR15Review.next=true;
        }
        catch(Exception e){ProjectSeele.LOGGER.error("R15 far-view capture failed",e);FarViewR15Review.finished=true;}
    }
    private FarViewR15Client(){}
}
