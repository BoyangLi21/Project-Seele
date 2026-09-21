package com.projectseele.client.visual;

import com.projectseele.visual.CombatR29Review;
import net.minecraft.client.Minecraft;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class CombatR29Client
{
    private static boolean started,oldPause,oldGui;private static int oldDistance,end,frame,warmup;private static Path folder;private static String last="";private static long next,firstFrame;
    private static final com.google.gson.JsonArray timestamps=new com.google.gson.JsonArray();
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent e)
    {
        if(!CombatR29Review.ENABLED||e.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null)return;
        if(!started)
        {
            started=true;oldPause=mc.options.pauseOnLostFocus;oldGui=mc.options.hideGui;oldDistance=mc.options.renderDistance().get();mc.options.pauseOnLostFocus=false;mc.options.hideGui=true;mc.options.renderDistance().set(18);mc.options.broadcastOptions();mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);
            folder=mc.gameDirectory.toPath().resolve("../artifacts/facility_r29/native_combat_"+System.currentTimeMillis()).normalize();try{Files.createDirectories(folder);}catch(Exception x){throw new IllegalStateException(x);}CombatR29Review.ready=true;
        }
        if(mc.level!=null&&mc.level.getEntity(CombatR29Review.evaId)!=null&&mc.levelRenderer.isChunkCompiled(new net.minecraft.core.BlockPos(32,80,217))&&++warmup>160)CombatR29Review.sceneReady=true;
        if(CombatR29Review.done&&++end>30){try{Files.writeString(folder.resolve("frames.json"),timestamps.toString());}catch(Exception x){throw new IllegalStateException(x);}mc.options.pauseOnLostFocus=oldPause;mc.options.hideGui=oldGui;mc.options.renderDistance().set(oldDistance);mc.options.broadcastOptions();mc.stop();}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent e)
    {
        if(!CombatR29Review.ENABLED||!started||CombatR29Review.evaId==0)return;var mc=Minecraft.getInstance();if(mc.player==null)return;
        if(e.phase==TickEvent.Phase.START)
        {
            Vec3 target=CombatR29Review.age<400?new Vec3(32.5,117,207.5):CombatR29Review.age<480?new Vec3(32.5,137,217.5):new Vec3(32.5,221,245.5);Vec3 d=target.subtract(mc.player.getEyePosition());float yaw=(float)Math.toDegrees(Math.atan2(-d.x,d.z)),pitch=(float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance()));mc.player.setYRot(yaw);mc.player.yRotO=yaw;mc.player.setXRot(pitch);mc.player.xRotO=pitch;return;
        }
        String photo=CombatR29Review.photo;
        if(!photo.isEmpty()&&!photo.equals(last))
        {try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){image.writeToFile(folder.resolve(photo+".png"));last=photo;}catch(Exception x){throw new IllegalStateException(x);}}
        long now=System.nanoTime();
        if(CombatR29Review.age>=90&&CombatR29Review.age<390&&now>=next)
        {
            next=now+100_000_000L;
            if(firstFrame==0)firstFrame=now;var t=new com.google.gson.JsonObject();t.addProperty("frame",frame);t.addProperty("seconds",(now-firstFrame)/1e9);t.addProperty("server_tick",CombatR29Review.age);timestamps.add(t);
            try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){NativeReviewFrames.writeJpeg(image,folder.resolve(String.format(Locale.ROOT,"frame_%05d.jpg",frame++)));}catch(Exception x){throw new IllegalStateException(x);}
        }
    }
    private CombatR29Client() {}
}
