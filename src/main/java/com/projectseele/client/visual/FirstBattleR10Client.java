package com.projectseele.client.visual;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.projectseele.ProjectSeele;
import com.projectseele.client.FirstBattleClient;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.network.ServerboundEvaControlPacket;
import com.projectseele.visual.FirstBattleR10Review;
import com.projectseele.world.EvaPilotResolver;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.concurrent.*;

/** Bounded asynchronous recording of the actual native framebuffer in the disposable review world. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class FirstBattleR10Client
{
    private static boolean initialized,closing;
    private static boolean warmedCamera;
    private static boolean oldPause,oldGui;
    private static int oldDistance,serial,closeTicks;
    private static CameraType oldCamera;
    private static long firstNanos,lastNanos;
    private static Path output;
    private static final JsonArray frames=new JsonArray();
    private static final ThreadPoolExecutor WRITER=new ThreadPoolExecutor(2,2,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(6),r->{Thread t=new Thread(r,"first-battle-native-frames");t.setDaemon(true);return t;});
    private static volatile String writeFailure="";

    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!FirstBattleR10Review.ENABLED||event.phase!=TickEvent.Phase.END)return;
        var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        try
        {
            if(!initialized)
            {
                initialized=true;oldPause=mc.options.pauseOnLostFocus;oldGui=mc.options.hideGui;oldDistance=mc.options.renderDistance().get();oldCamera=mc.options.getCameraType();
                mc.options.pauseOnLostFocus=false;mc.options.hideGui=false;mc.options.renderDistance().set(8);mc.options.setCameraType(CameraType.FIRST_PERSON);mc.options.broadcastOptions();
                output=mc.gameDirectory.toPath().resolve("../artifacts/first_battle_world_r10/native_movie_"+System.currentTimeMillis()).normalize();Files.createDirectories(output);
            }
            var entity=mc.level.getEntity(FirstBattleR10Review.heroId);
            FirstBattleR10Review.clientTracked=entity instanceof EvaUnit01Entity;
            FirstBattleR10Review.clientMounted=entity!=null&&EvaPilotResolver.controlTarget(mc.player)==entity;
            FirstBattleR10Review.clientCameraRestored=!FirstBattleClient.active()&&mc.options.getCameraType()==CameraType.FIRST_PERSON;
            if(FirstBattleR10Review.warming){warmedCamera=true;mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);}
            else if(warmedCamera){warmedCamera=false;mc.options.setCameraType(CameraType.FIRST_PERSON);}
            if(FirstBattleR10Review.actionSerial!=serial)
            {
                serial=FirstBattleR10Review.actionSerial;SeeleNetwork.CHANNEL.sendToServer(new ServerboundEvaControlPacket(FirstBattleR10Review.action));
            }
            mc.options.keyUp.setDown(FirstBattleR10Review.forward!=0);
            if(FirstBattleR10Review.finished||FirstBattleR10Review.reloadRequested)
            {
                mc.options.keyUp.setDown(false);
                if(!closing){closing=true;FirstBattleClient.releaseCamera();mc.options.pauseOnLostFocus=oldPause;mc.options.hideGui=oldGui;mc.options.renderDistance().set(oldDistance);mc.options.setCameraType(oldCamera);WRITER.shutdown();}
                if(++closeTicks>20&&WRITER.isTerminated())
                {
                    if(!frames.isEmpty())
                    {
                        JsonObject manifest=new JsonObject();manifest.addProperty("source","Native Minecraft framebuffer, timestamped at capture; no interpolated frames");manifest.add("frames",frames);manifest.addProperty("dropped",FirstBattleR10Review.droppedFrames);manifest.addProperty("write_failure",writeFailure);Files.writeString(output.resolve("frames.json"),manifest.toString());
                    }
                    mc.stop();
                }
            }
        }
        catch(Exception failure){ProjectSeele.LOGGER.error("R10 native client review failed",failure);FirstBattleClient.releaseCamera();mc.stop();}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!FirstBattleR10Review.ENABLED||!initialized||closing||event.phase!=TickEvent.Phase.END||!FirstBattleR10Review.captureMovie)return;
        long now=System.nanoTime();if(now-lastNanos<33_333_333L)return;lastNanos=now;
        if(WRITER.getQueue().remainingCapacity()==0){FirstBattleR10Review.droppedFrames++;return;}
        if(firstNanos==0)firstNanos=now;
        var mc=Minecraft.getInstance();var image=Screenshot.takeScreenshot(mc.getMainRenderTarget());
        int index=FirstBattleR10Review.clientFrames++;String name=String.format("frame_%05d.jpg",index);
        JsonObject frame=new JsonObject();frame.addProperty("file",name);frame.addProperty("seconds",(now-firstNanos)/1e9);
        frame.addProperty("fps",mc.getFps());
        var entity=mc.level.getEntity(FirstBattleR10Review.heroId);
        if(entity instanceof EvaUnit01Entity eva){frame.addProperty("scene_seconds",eva.firstBattleSignals().time(eva,event.renderTickTime));frame.addProperty("active",eva.isFirstBattleActive());frame.addProperty("hero_yaw",eva.yBodyRot);var other=mc.level.getEntity(eva.firstBattleSignals().partner(eva));if(other instanceof net.minecraft.world.entity.LivingEntity living)frame.addProperty("angel_yaw",living.yBodyRot);}
        frames.add(frame);
        WRITER.execute(()->{try(image){
            NativeReviewFrames.writeJpeg(image,output.resolve(name));
        }catch(Exception failure){writeFailure=failure.toString();ProjectSeele.LOGGER.error("R10 frame write failed",failure);}});
    }
    private FirstBattleR10Client() {}
}
