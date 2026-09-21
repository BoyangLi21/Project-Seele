package com.projectseele.client.visual;

import com.projectseele.client.screen.StaffConversationScreen;
import com.projectseele.visual.TvCampaignR24Review;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class TvCampaignR24Client
{
    private static boolean started,oldPause,oldGui;private static int end,oldDistance;private static Path folder;
    // Bounded 0.5 s cushion for short disk/GC stalls; frames remain original
    // and timestamped. At 720p this holds at most about 60 MiB of raw images.
    private static final java.util.concurrent.ThreadPoolExecutor WRITER=new java.util.concurrent.ThreadPoolExecutor(1,1,0,java.util.concurrent.TimeUnit.SECONDS,new java.util.concurrent.ArrayBlockingQueue<>(16),r->{var t=new Thread(r,"tv-r24-frame-writer");t.setDaemon(true);return t;});
    private static final com.google.gson.JsonArray frames=new com.google.gson.JsonArray();
    private static long firstFrame,nextFrame;private static int serial,dropped;private static volatile String captureFailure="";
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!TvCampaignR24Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        if(!started)
        {
            started=true;oldPause=mc.options.pauseOnLostFocus;oldGui=mc.options.hideGui;oldDistance=mc.options.renderDistance().get();mc.options.pauseOnLostFocus=false;mc.options.renderDistance().set(TvCampaignR24Review.R29?20:12);mc.options.broadcastOptions();
            folder=mc.gameDirectory.toPath().resolve((TvCampaignR24Review.R29?"../artifacts/facility_r29/native_campaign_":"../artifacts/facility_r24/native_campaign_")+System.currentTimeMillis()).normalize();try{Files.createDirectories(folder);}catch(Exception e){throw new IllegalStateException(e);}TvCampaignR24Review.ready=true;
        }
        if(TvCampaignR24Review.finished)
        {
            if(++end==1)WRITER.shutdown();
            if(end>35&&WRITER.isTerminated())
            {
                var record=new com.google.gson.JsonObject();record.add("frames",frames);record.addProperty("dropped",dropped);record.addProperty("error",captureFailure);record.addProperty("source","Native Minecraft framebuffer; one real server-directed encounter, no interpolated frames");
                try{Files.writeString(folder.resolve("frames.json"),record.toString());}catch(Exception e){throw new IllegalStateException(e);}
                mc.setScreen(null);mc.options.pauseOnLostFocus=oldPause;mc.options.hideGui=oldGui;mc.options.renderDistance().set(oldDistance);mc.options.broadcastOptions();mc.stop();
            }return;
        }
        var controlled=com.projectseele.world.EvaPilotResolver.controlTarget(mc.player);
        TvCampaignR24Review.clientBattleActive=controlled!=null&&controlled.isFirstBattleActive();
        TvCampaignR24Review.clientEnemyTracked=mc.level.getEntity(TvCampaignR24Review.entityId) instanceof com.projectseele.entity.ShamshelEntity;
        if(mc.player.tickCount%20==0)TvCampaignR24Review.clientView="pilot="+mc.player.position()+" vehicle="+(controlled==null?"none":controlled.position())+" camera="+mc.gameRenderer.getMainCamera().getPosition();
        if(mc.screen==null&&mc.level.getEntity(TvCampaignR24Review.entityId) instanceof com.projectseele.entity.ShamshelEntity enemy)
        {
            var direction=enemy.position().add(0,enemy.getBbHeight()*.80,0).subtract(mc.player.getEyePosition());
            float yaw=(float)Math.toDegrees(Math.atan2(-direction.x,direction.z)),pitch=(float)-Math.toDegrees(Math.atan2(direction.y,direction.horizontalDistance()));
            mc.player.setYRot(yaw);mc.player.yRotO=yaw;mc.player.setXRot(pitch);mc.player.xRotO=pitch;
        }
        String request=TvCampaignR24Review.input;
        if(request.isEmpty()||TvCampaignR24Review.inputs.contains(request)||!(mc.screen instanceof StaffConversationScreen screen))return;
        if(request.equals("close")){screen.onClose();TvCampaignR24Review.inputs.add(request);return;}
        String label=request.equals("briefing")?"作战记录":"接受当前作战";
        for(var child:List.copyOf(screen.children()))if(child instanceof Button button&&button.getMessage().getString().equals(label))
        {screen.mouseClicked(button.getX()+3,button.getY()+3,0);screen.mouseReleased(button.getX()+3,button.getY()+3,0);TvCampaignR24Review.inputs.add(request);return;}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!TvCampaignR24Review.ENABLED||!started||event.phase!=TickEvent.Phase.END)return;
        var mc=Minecraft.getInstance();
        var eva=mc.player==null?null:com.projectseele.world.EvaPilotResolver.controlTarget(mc.player);
        if(!WRITER.isShutdown()&&eva!=null&&eva.isFirstBattleActive())
        {
            long now=System.nanoTime();
            if(now>=nextFrame&&(firstFrame==0||now-firstFrame<90_000_000_000L))
            {
                // Keep a 30 Hz deadline instead of resetting from each render
                // frame. Small rounding differences otherwise turn 60 Hz
                // rendering into an uneven 20–30 Hz recording.
                nextFrame=Math.max(nextFrame+33_333_333L,now+8_333_333L);if(firstFrame==0)firstFrame=now;
                if(WRITER.getQueue().remainingCapacity()==0)dropped++;
                else
                {
                    var frame=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget());String file=String.format("frame_%05d.jpg",serial++);
                    var row=new com.google.gson.JsonObject();row.addProperty("file",file);row.addProperty("seconds",(now-firstFrame)/1e9);row.addProperty("scene_seconds",eva.firstBattleSignals().time(eva,event.renderTickTime));row.addProperty("fps",mc.getFps());frames.add(row);
                    WRITER.execute(()->{try(frame){NativeReviewFrames.writeJpeg(frame,folder.resolve(file));}catch(Exception e){captureFailure=e.toString();}});
                }
            }
        }
        String name=TvCampaignR24Review.photo;if(name.isEmpty()||TvCampaignR24Review.photos.contains(name))return;
        try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){image.writeToFile(folder.resolve(name+".png"));TvCampaignR24Review.photos.add(name);}catch(Exception e){throw new IllegalStateException(e);}
    }
    private TvCampaignR24Client(){}
}
