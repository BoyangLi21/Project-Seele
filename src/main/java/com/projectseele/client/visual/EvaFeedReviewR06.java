package com.projectseele.client.visual;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.projectseele.ProjectSeele;
import com.projectseele.client.EvaCommandFeedClient;
import com.projectseele.config.SeeleConfig;
import com.projectseele.world.EvaPilotResolver;
import net.minecraft.client.Minecraft;
import net.minecraft.client.CameraType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Real network roundtrip; only the dedicated disposable review save permits self-relay. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class EvaFeedReviewR06
{
    private static int wait,start=-1,stage=-1;
    private static long started,phaseStart;
    private static long[] previous;
    private static int width,fps,budget;
    private static double quality;
    private static CameraType originalCamera;
    private static boolean finished;
    private static final JsonArray results=new JsonArray();
    @SubscribeEvent
    public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!Boolean.getBoolean("projectseele.feedReviewR06")||finished||event.phase!=TickEvent.Phase.END)return;
        var mc=Minecraft.getInstance();var server=mc.getSingleplayerServer();
        if(mc.player==null||mc.level==null||server==null)return;
        if(!server.getWorldPath(LevelResource.ROOT).normalize().getFileName().toString().startsWith("SEELE_EVA_FEED_REVIEW"))throw new IllegalStateException("Feed review save boundary");
        mc.options.pauseOnLostFocus=false;mc.options.hideGui=false;
        if(++wait==80)
        {
            mc.player.connection.sendCommand("seele motionlab reset");mc.player.connection.sendCommand("seele motionlab enter unit01");
            mc.player.connection.sendCommand("seele motionlab weapon unit01 rifle");
            width=SeeleConfig.VIDEO_CAPTURE_WIDTH.get();fps=SeeleConfig.VIDEO_TARGET_FPS.get();budget=SeeleConfig.VIDEO_FRAME_BUDGET_KIB.get();quality=SeeleConfig.VIDEO_JPEG_QUALITY.get();
            originalCamera=mc.options.getCameraType();
        }
        if(wait<100)return;
        var eva=EvaPilotResolver.controlTarget(mc.player);if(eva==null||!eva.isPoweredOn()||eva.getActivationTicks()>0)return;
        if(start<0){start=server.getTickCount();started=System.nanoTime();}
        int tick=server.getTickCount()-start;int next=Math.min(3,tick/160);
        if(next!=stage)
        {
            if(stage>=0)savePhase();stage=next;previous=EvaCommandFeedClient.reviewCounts();phaseStart=System.nanoTime();
            SeeleConfig.VIDEO_CAPTURE_WIDTH.set(stage==0?1280:stage==1?1920:stage==2?640:1280);
            SeeleConfig.VIDEO_JPEG_QUALITY.set(stage==1?.94D:.86D);SeeleConfig.VIDEO_TARGET_FPS.set(15);SeeleConfig.VIDEO_FRAME_BUDGET_KIB.set(stage==1?128:384);
            mc.options.setCameraType(stage>=2?CameraType.THIRD_PERSON_BACK:CameraType.FIRST_PERSON);
        }
        EvaCommandFeedClient.setCaptureDemand(true);mc.player.setYRot((float)(Math.sin(tick/65D)*35));mc.player.setXRot((float)(Math.sin(tick/91D)*8));
        if(tick%160==120)EvaCommandFeedClient.saveReviewFeed(1,mc.gameDirectory.toPath().resolve("screenshots/projectseele_feed_r06/stage_"+stage+".png"));
        if(tick>=640)
        {
            savePhase();finished=true;SeeleConfig.VIDEO_CAPTURE_WIDTH.set(width);SeeleConfig.VIDEO_TARGET_FPS.set(fps);SeeleConfig.VIDEO_FRAME_BUDGET_KIB.set(budget);SeeleConfig.VIDEO_JPEG_QUALITY.set(quality);
            mc.options.setCameraType(originalCamera);
            try
            {
                Path path=mc.gameDirectory.toPath().resolve("screenshots/projectseele_feed_r06/report.json");Files.createDirectories(path.getParent());Files.writeString(path,results.toString());
            }
            catch(Exception failure){throw new IllegalStateException(failure);}
            ProjectSeele.LOGGER.info("R06 feed review complete: {} seconds {}",(System.nanoTime()-started)/1e9,results);mc.stop();
        }
    }
    private static void savePhase()
    {
        long[] now=EvaCommandFeedClient.reviewCounts();double seconds=(System.nanoTime()-phaseStart)/1e9;
        var row=new JsonObject();row.addProperty("stage",stage);row.addProperty("width",SeeleConfig.VIDEO_CAPTURE_WIDTH.get());row.addProperty("camera",stage>=2?"third-person optical pass":"first-person downsample");
        row.addProperty("seconds",seconds);row.addProperty("captured",now[0]-previous[0]);row.addProperty("encoded",now[1]-previous[1]);row.addProperty("displayed",now[2]-previous[2]);row.addProperty("displayFps",(now[2]-previous[2])/seconds);row.addProperty("maxFrameBytes",now[3]);results.add(row);
        if(now[2]-previous[2]<seconds*5||now[3]>=com.projectseele.network.EvaVideoFrameTransport.MAX_FRAME_BYTES)
            throw new IllegalStateException("Feed review did not sustain bounded playback: "+row);
    }
}
