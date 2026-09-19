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
    private static final List<Double> loadingTimes=new ArrayList<>();
    private static boolean settingsSaved,oldPause,oldGui;private static int oldDistance;private static net.minecraft.client.CameraType oldCamera;
    private static jdk.jfr.Recording profile;
    private static int abPhase=-1;private static final List<Double> abFrames=new ArrayList<>();private static final JsonArray abRows=new JsonArray();
    private static void occlusionAB(Minecraft mc,double seconds,double elapsed) throws Exception
    {
        if(seconds<60)return;int phase=Math.min(4,(int)((seconds-60)/30));
        if(phase!=abPhase)
        {
            if(abPhase>=0&&!abFrames.isEmpty())
            {
                Collections.sort(abFrames);var row=new JsonObject();row.addProperty("phase",abPhase);row.addProperty("enabled",abPhase%2==1);row.addProperty("frames",abFrames.size());
                row.addProperty("median_ms",abFrames.get(abFrames.size()/2));row.addProperty("p95_ms",abFrames.get((int)(abFrames.size()*.95)));
                row.add("occlusion",new Gson().toJsonTree(com.projectseele.client.ClientOcclusionR24.diagnostics()));abRows.add(row);
                try(var shot=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){shot.writeToFile(folder.resolve("occlusion_phase_"+abPhase+".png"));}
            }
            abPhase=phase;abFrames.clear();com.projectseele.client.ClientOcclusionR24.enabled(phase%2==1||phase==4);
            ProjectSeele.LOGGER.info("R24 fixed-view occlusion A/B phase={} enabled={}",phase,phase%2==1||phase==4);
        }
        if(phase<4&&seconds-60-phase*30>3)abFrames.add(elapsed);
    }
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!FarViewR15Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();
        if(!settingsSaved)
        {
            settingsSaved=true;oldPause=mc.options.pauseOnLostFocus;oldGui=mc.options.hideGui;oldDistance=mc.options.renderDistance().get();oldCamera=mc.options.getCameraType();
            mc.options.pauseOnLostFocus=false;
            if(FarViewR15Review.TV24){mc.options.renderDistance().set(24);mc.options.broadcastOptions();}
        }
        if(FarViewR15Review.finished&&++end>40)
        {mc.options.hideGui=oldGui;mc.options.pauseOnLostFocus=oldPause;mc.options.renderDistance().set(oldDistance);mc.options.setCameraType(oldCamera);mc.options.broadcastOptions();mc.stop();}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!FarViewR15Review.ENABLED||event.phase!=TickEvent.Phase.END||FarViewR15Review.index<0||FarViewR15Review.finished||FarViewR15Review.next)return;
        var mc=Minecraft.getInstance();if(mc.level==null||mc.player==null)return;
        try
        {
            if(folder==null){folder=mc.gameDirectory.toPath().resolve((FarViewR15Review.TV24?"../artifacts/facility_r24/far_native_":FarViewR15Review.CURRENT?"../artifacts/rendering_r17/far_native_":"../artifacts/staff_world_r15/far_native_")+System.currentTimeMillis()).normalize();Files.createDirectories(folder);}
            long now=System.nanoTime();
            if(view!=FarViewR15Review.index){view=FarViewR15Review.index;times.clear();loadingTimes.clear();started=previous=now;}
            mc.options.hideGui=true;mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);
            double seconds=(now-started)/1e9;
            if(FarViewR15Review.OCCLUSION_AB)occlusionAB(mc,seconds,(now-previous)/1e6);
            if(previous>0&&now>previous){if(seconds>(FarViewR15Review.CURRENT?60:55))times.add((now-previous)/1e6);else loadingTimes.add((now-previous)/1e6);}
            previous=now;
            int progress=(int)seconds/10;
            if(progress!=lastProgress){lastProgress=progress;ProjectSeele.LOGGER.info("FAR WARMUP {} seconds={} fps={} chunks={}",FarViewR15Review.SHOTS[view].name(),(int)seconds,mc.getFps(),mc.levelRenderer.getChunkStatistics());}
            if(Boolean.getBoolean("projectseele.profileFarView")&&seconds>=60&&profile==null)
            {
                profile=new jdk.jfr.Recording();
                profile.enable("jdk.ExecutionSample").withPeriod(java.time.Duration.ofMillis(10));
                profile.enable("jdk.NativeMethodSample").withPeriod(java.time.Duration.ofMillis(10));
                profile.start();
            }
            // Allow fresh disk LODs to bake, then measure stationary rendering.
            if(seconds<(FarViewR15Review.OCCLUSION_AB?180:FarViewR15Review.CURRENT?90:85))return;
            if(profile!=null&&profile.getState()==jdk.jfr.RecordingState.RUNNING)
            {profile.stop();profile.dump(folder.resolve(FarViewR15Review.TV24?"un_render_profile.jfr":"pyramid_render_profile.jfr"));profile.close();}
            var shot=FarViewR15Review.SHOTS[view];try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){image.writeToFile(folder.resolve(shot.name()+".png"));}
            var row=new JsonObject();row.addProperty("view",shot.name());row.addProperty("frames",times.size());Collections.sort(times);
            row.addProperty("median_ms",times.get(times.size()/2));row.addProperty("p95_ms",times.get((int)(times.size()*.95)));row.addProperty("p99_ms",times.get((int)(times.size()*.99)));
            row.addProperty("heap_used_mib",(Runtime.getRuntime().totalMemory()-Runtime.getRuntime().freeMemory())/1048576);row.addProperty("heap_max_mib",Runtime.getRuntime().maxMemory()/1048576);row.addProperty("render_chunks",mc.options.renderDistance().get());row.addProperty("simulation_chunks",mc.options.simulationDistance().get());
            row.addProperty("dh_loaded",net.minecraftforge.fml.ModList.get().isLoaded("distanthorizons"));row.addProperty("embeddium_loaded",net.minecraftforge.fml.ModList.get().isLoaded("embeddium"));row.addProperty("ferritecore_loaded",net.minecraftforge.fml.ModList.get().isLoaded("ferritecore"));results.add(row);
            row.addProperty("opengl_renderer",org.lwjgl.opengl.GL11.glGetString(org.lwjgl.opengl.GL11.GL_RENDERER));
            row.addProperty("modernfix_loaded",net.minecraftforge.fml.ModList.get().isLoaded("modernfix"));
            row.addProperty("entityculling_loaded",net.minecraftforge.fml.ModList.get().isLoaded("entityculling"));
            row.add("occlusion",new Gson().toJsonTree(com.projectseele.client.ClientOcclusionR24.diagnostics()));
            if(FarViewR15Review.OCCLUSION_AB)row.add("same_jvm_occlusion_ab",abRows);
            if(!loadingTimes.isEmpty())
            {
                Collections.sort(loadingTimes);row.addProperty("initial_loading_frames",loadingTimes.size());
                row.addProperty("initial_loading_p99_ms",loadingTimes.get((int)(loadingTimes.size()*.99)));
                row.addProperty("initial_loading_max_ms",loadingTimes.get(loadingTimes.size()-1));
                row.addProperty("initial_loading_over_100ms",loadingTimes.stream().filter(t->t>100).count());
            }
            row.addProperty("test_scope","Native fixed-view loading and steady rendering; not an A/B FPS claim or a flight-route benchmark");
            row.addProperty("sampling_profiler_enabled",Boolean.getBoolean("projectseele.profileFarView"));
            row.addProperty("vehicle_static_shape_hits",com.projectseele.entity.SbwStaticShapesR24.hits.sum());
            row.addProperty("vehicle_rest_reuses",com.projectseele.entity.SbwRestCollisionR24.reused.sum());
            row.addProperty("vehicle_rest_verified",com.projectseele.entity.SbwRestCollisionR24.verified.sum());
            row.addProperty("vehicle_rest_max_error",com.projectseele.entity.SbwRestCollisionR24.maximumError);
            row.addProperty("vehicle_rest_rejected",com.projectseele.entity.SbwRestCollisionR24.rejected);
            row.add("vehicle_rest_diagnostics",new Gson().toJsonTree(com.projectseele.entity.SbwRestCollisionR24.diagnostics()));
            row.add("vehicle_phantom_diagnostics",new Gson().toJsonTree(com.projectseele.client.SbwPhantomLoadR24.diagnostics()));
            Files.writeString(folder.resolve("measurements.json"),new GsonBuilder().setPrettyPrinting().create().toJson(results));FarViewR15Review.next=true;
        }
        catch(Exception e){ProjectSeele.LOGGER.error("R15 far-view capture failed",e);FarViewR15Review.finished=true;}
    }
    private FarViewR15Client(){}
}
