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
    private static int view=-1,end,lastProgress=-1;private static long previous,started;private static Path folder;
    private static final List<Double> times=new ArrayList<>();private static final JsonArray results=new JsonArray();
    private static jdk.jfr.Recording profile;
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
            if(folder==null){folder=mc.gameDirectory.toPath().resolve((FarViewR15Review.CURRENT?"../artifacts/rendering_r17/far_native_":"../artifacts/staff_world_r15/far_native_")+System.currentTimeMillis()).normalize();Files.createDirectories(folder);}
            long now=System.nanoTime();
            if(view!=FarViewR15Review.index){view=FarViewR15Review.index;times.clear();started=previous=now;}
            mc.options.hideGui=true;mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);
            double seconds=(now-started)/1e9;if(seconds>(FarViewR15Review.CURRENT?60:55)&&previous>0)times.add((now-previous)/1e6);previous=now;
            int progress=(int)seconds/10;
            if(progress!=lastProgress){lastProgress=progress;ProjectSeele.LOGGER.info("FAR WARMUP {} seconds={} fps={} chunks={}",FarViewR15Review.SHOTS[view].name(),(int)seconds,mc.getFps(),mc.levelRenderer.getChunkStatistics());}
            if(Boolean.getBoolean("projectseele.profileFarView")&&FarViewR15Review.CURRENT&&FarViewR15Review.SHOTS[view].name().equals("geofront_pyramid")&&seconds>=60&&profile==null)
            {
                profile=new jdk.jfr.Recording();
                profile.enable("jdk.ExecutionSample").withPeriod(java.time.Duration.ofMillis(10));
                profile.enable("jdk.NativeMethodSample").withPeriod(java.time.Duration.ofMillis(10));
                profile.start();
            }
            // Allow fresh disk LODs to bake, then measure stationary rendering.
            if(seconds<(FarViewR15Review.CURRENT?90:85))return;
            if(profile!=null&&profile.getState()==jdk.jfr.RecordingState.RUNNING)
            {profile.stop();profile.dump(folder.resolve("pyramid_render_profile.jfr"));profile.close();}
            var shot=FarViewR15Review.SHOTS[view];try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){image.writeToFile(folder.resolve(shot.name()+".png"));}
            var row=new JsonObject();row.addProperty("view",shot.name());row.addProperty("frames",times.size());Collections.sort(times);
            row.addProperty("median_ms",times.get(times.size()/2));row.addProperty("p95_ms",times.get((int)(times.size()*.95)));row.addProperty("p99_ms",times.get((int)(times.size()*.99)));
            row.addProperty("heap_used_mib",(Runtime.getRuntime().totalMemory()-Runtime.getRuntime().freeMemory())/1048576);row.addProperty("heap_max_mib",Runtime.getRuntime().maxMemory()/1048576);row.addProperty("render_chunks",mc.options.renderDistance().get());row.addProperty("simulation_chunks",mc.options.simulationDistance().get());
            row.addProperty("dh_loaded",net.minecraftforge.fml.ModList.get().isLoaded("distanthorizons"));row.addProperty("embeddium_loaded",net.minecraftforge.fml.ModList.get().isLoaded("embeddium"));row.addProperty("ferritecore_loaded",net.minecraftforge.fml.ModList.get().isLoaded("ferritecore"));results.add(row);
            row.addProperty("opengl_renderer",org.lwjgl.opengl.GL11.glGetString(org.lwjgl.opengl.GL11.GL_RENDERER));
            row.addProperty("modernfix_loaded",net.minecraftforge.fml.ModList.get().isLoaded("modernfix"));
            Files.writeString(folder.resolve("measurements.json"),new GsonBuilder().setPrettyPrinting().create().toJson(results));FarViewR15Review.next=true;
        }
        catch(Exception e){ProjectSeele.LOGGER.error("R15 far-view capture failed",e);FarViewR15Review.finished=true;}
    }
    private FarViewR15Client(){}
}
