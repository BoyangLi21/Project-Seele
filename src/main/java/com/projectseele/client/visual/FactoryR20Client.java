package com.projectseele.client.visual;

import com.projectseele.visual.FactoryR20Review;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.*;
import net.minecraft.client.gui.screens.PauseScreen;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.concurrent.*;
import com.google.gson.*;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class FactoryR20Client
{
    private static int distance=-1,exit,age,lastStill=-1,dropped,phaseTicks;private static String previous="",inputPhase="";private static Path folder;
    private static final JsonArray frames=new JsonArray();private static long began,lastFrame;private static boolean closing;
    private static volatile String frameError="";private static boolean oldGui;
    private static final ThreadPoolExecutor writer=new ThreadPoolExecutor(2,2,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(8),r->{Thread t=new Thread(r,"r20-factory-frames");t.setDaemon(true);return t;});
    public record CameraView(net.minecraft.world.phys.Vec3 position,net.minecraft.world.phys.Vec3 target){}
    public static CameraView cameraView()
    {
        if(!FactoryR20Review.ENABLED||!Boolean.getBoolean("projectseele.factoryCinematic")||!FactoryR20Review.phase.equals("prepare_transfer"))return null;
        var mc=Minecraft.getInstance();if(mc.level==null)return null;
        var units=mc.level.getEntitiesOfClass(EvaUnit01Entity.class,new net.minecraft.world.phys.AABB(-30,-470,-290,96,-330,-180),e->e.getUnitVariant()==1&&!e.isExperimentalUnit());
        if(units.isEmpty()||units.get(0).hasActiveCarrierMotion())return null;
        var root=units.get(0).getPosition(mc.getFrameTime());return new CameraView(root.add(18,68,15),root.add(0,53.3,4.8));
    }
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent e)
    {
        if(!FactoryR20Review.ENABLED||e.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();mc.options.pauseOnLostFocus=false;if(mc.screen instanceof PauseScreen)mc.setScreen(null);
        if(FactoryR20Review.finished){if(distance>=0){mc.options.renderDistance().set(distance);mc.options.broadcastOptions();mc.options.hideGui=oldGui;distance=-1;}if(!closing){writer.shutdown();closing=true;}if(writer.isTerminated()&&++exit==1&&folder!=null){try{JsonObject report=new JsonObject();report.addProperty("source","Unmodified native framebuffer; real F5 pilot camera and carrier motion");report.addProperty("dropped",dropped);report.addProperty("write_failure",frameError);report.add("frames",frames);Files.writeString(folder.resolve("frames.json"),report.toString());}catch(Exception x){throw new IllegalStateException(x);}}if(exit>30)mc.stop();return;}
        if(mc.player==null||mc.level==null||mc.screen!=null)return;
        if(distance<0){distance=mc.options.renderDistance().get();oldGui=mc.options.hideGui;mc.options.hideGui=true;mc.options.renderDistance().set(10);mc.options.broadcastOptions();mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);folder=mc.gameDirectory.toPath().resolve(("r21-factory".equals(System.getProperty("projectseele.regionalBuild",""))?"../artifacts/world_repair_r21/factory/native_cycle_":"../artifacts/world_rebuild_r20/factory/native_cycle_")+System.currentTimeMillis());try{Files.createDirectories(folder);}catch(Exception x){throw new IllegalStateException(x);}}
        FactoryR20Review.ready=true;age++;
        if(!inputPhase.equals(FactoryR20Review.phase)){inputPhase=FactoryR20Review.phase;phaseTicks=0;}else phaseTicks++;
        if("r21-factory".equals(System.getProperty("projectseele.regionalBuild","")))
        {
            boolean free=FactoryR20Review.phase.equals("free_surface_hold");
            mc.options.keyUp.setDown(free&&phaseTicks>=30&&phaseTicks<44);
            mc.options.keyDown.setDown(free&&phaseTicks>=55&&phaseTicks<69);
            mc.options.keyAttack.setDown(free&&phaseTicks>=90&&phaseTicks<120);
            mc.options.keyUse.setDown(free&&phaseTicks>=135&&phaseTicks<140);
            if(free&&phaseTicks==90)KeyMapping.click(mc.options.keyAttack.getKey());
            if(free&&phaseTicks==135)KeyMapping.click(mc.options.keyUse.getKey());
        }
        if(!FactoryR20Review.phase.equals("setup")&&!FactoryR20Review.phase.equals("board"))
        {mc.player.setYRot(180);mc.player.yRotO=180;mc.player.setXRot(12);mc.player.xRotO=12;}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent e)
    {
        if(!FactoryR20Review.ENABLED||closing||e.phase!=TickEvent.Phase.END||folder==null)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.screen!=null)return;
        String phase=FactoryR20Review.phase;
        if(!phase.equals(previous)||age%160==0&&age>0&&lastStill!=age)
        {
            try(var im=Screenshot.takeScreenshot(mc.getMainRenderTarget())){im.writeToFile(folder.resolve(String.format("%06d_%s.png",age,phase)));}catch(Exception x){throw new IllegalStateException(x);}previous=phase;lastStill=age;
        }
        long now=System.nanoTime();if(phase.equals("setup")||now-lastFrame<50_000_000L)return;lastFrame=now;
        if(writer.getQueue().remainingCapacity()==0){dropped++;return;}if(began==0)began=now;
        JsonObject f=new JsonObject();String name=String.format("frame_%05d.jpg",frames.size());f.addProperty("file",name);f.addProperty("seconds",(now-began)/1e9);f.addProperty("phase",phase);f.addProperty("fps",mc.getFps());f.addProperty("mechanical_closeup",cameraView()!=null);
        var camera=mc.gameRenderer.getMainCamera().getPosition();f.addProperty("camera_x",camera.x);f.addProperty("camera_y",camera.y);f.addProperty("camera_z",camera.z);
        var eva=com.projectseele.world.EvaPilotResolver.controlTarget(mc.player);
        if(eva!=null){var p=eva.carrierRenderPosition(mc.getFrameTime());f.addProperty("carrier",eva.hasActiveCarrierMotion());f.addProperty("eva_x",p.x);f.addProperty("eva_y",p.y);f.addProperty("eva_z",p.z);}
        var im=Screenshot.takeScreenshot(mc.getMainRenderTarget());frames.add(f);writer.execute(()->{try(im){NativeReviewFrames.writeJpeg(im,folder.resolve(name));}catch(Exception x){frameError=x.toString();}});
    }
}
