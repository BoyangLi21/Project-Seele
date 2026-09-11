package com.projectseele.client.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.visual.TvFacilityR16Review;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.*;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** Captures the actual rendered mechanical cycle; no synthesized motion frames. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class TvFacilityR16Client
{
    private static boolean initialized,closing,oldPause,oldGui;
    private static int oldDistance,oldFov,closeTicks,dropped;
    private static CameraType oldCamera;
    private static net.minecraft.world.entity.LivingEntity camera;
    private static Path folder;
    private static long lastNanos;
    private static final Map<String,JsonArray> FRAMES=new LinkedHashMap<>();
    private static final Map<String,Long> STARTS=new HashMap<>();
    private static final ThreadPoolExecutor WRITER=new ThreadPoolExecutor(2,2,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(8),r->{Thread t=new Thread(r,"tv-facility-frame-writer");t.setDaemon(true);return t;});
    private static volatile String writeFailure="";
    @SubscribeEvent(priority=net.minecraftforge.eventbus.api.EventPriority.HIGHEST)
    public static void hideOperator(net.minecraftforge.client.event.RenderPlayerEvent.Pre event)
    {if(TvFacilityR16Review.ENABLED&&event.getEntity()==Minecraft.getInstance().player)event.setCanceled(true);}
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!TvFacilityR16Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        try
        {
            if(!initialized)
            {
                initialized=true;oldPause=mc.options.pauseOnLostFocus;oldGui=mc.options.hideGui;oldDistance=mc.options.renderDistance().get();oldCamera=mc.options.getCameraType();oldFov=mc.options.fov().get();
                mc.options.pauseOnLostFocus=false;mc.options.hideGui=true;mc.options.renderDistance().set(8);mc.options.fov().set(76);mc.options.broadcastOptions();
                folder=mc.gameDirectory.toPath().resolve("../artifacts/tv_facilities_r16/native_cycle_"+System.currentTimeMillis()).normalize();Files.createDirectories(folder);
            }
            TvFacilityR16Review.clientReady=mc.level.getEntity(TvFacilityR16Review.heroId) instanceof EvaUnit01Entity&&mc.levelRenderer.countRenderedChunks()>50;
            if(TvFacilityR16Review.finished)
            {
                if(!closing)
                {
                    closing=true;mc.setCameraEntity(mc.player);mc.options.pauseOnLostFocus=oldPause;mc.options.hideGui=oldGui;mc.options.renderDistance().set(oldDistance);mc.options.fov().set(oldFov);mc.options.setCameraType(oldCamera);mc.options.broadcastOptions();WRITER.shutdown();
                }
                if(++closeTicks>40&&WRITER.isTerminated())
                {
                    for(var entry:FRAMES.entrySet())
                    {
                        var json=new JsonObject();json.addProperty("source","Actual native Minecraft framebuffer with capture timestamps");json.addProperty("dropped",dropped);json.addProperty("rigid_capsule_gpu_draw_calls",com.projectseele.client.render.RigidCapsuleGpu.drawCalls);json.addProperty("write_failure",writeFailure);json.add("frames",entry.getValue());Files.writeString(folder.resolve(entry.getKey()).resolve("frames.json"),json.toString());
                    }
                    mc.stop();
                }
            }
        }
        catch(Exception e){ProjectSeele.LOGGER.error("R16 camera setup failed",e);mc.stop();}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!TvFacilityR16Review.ENABLED||!initialized||closing)return;var mc=Minecraft.getInstance();if(mc.level==null||mc.player==null)return;
        if(TvFacilityR16Review.photographing)
        {
            if(event.phase==TickEvent.Phase.START)placeCamera(mc,TvFacilityR16Review.photoEye,TvFacilityR16Review.photoTarget);
            else if(!TvFacilityR16Review.photo.isEmpty()&&!TvFacilityR16Review.capturedPhotos.contains(TvFacilityR16Review.photo)
                    &&mc.level.getEntitiesOfClass(com.projectseele.entity.NervStaffEntity.class,new net.minecraft.world.phys.AABB(TvFacilityR16Review.photoTarget,TvFacilityR16Review.photoTarget).inflate(12)).size()>0)
            {
                String file=TvFacilityR16Review.photo;
                try(var image=Screenshot.takeScreenshot(mc.getMainRenderTarget())){Path out=folder.resolve("npc");Files.createDirectories(out);image.writeToFile(out.resolve(file));TvFacilityR16Review.capturedPhotos.add(file);}
                catch(Exception e){ProjectSeele.LOGGER.error("NPC photograph failed",e);}
            }
            return;
        }
        var entity=mc.level.getEntity(TvFacilityR16Review.heroId);if(!(entity instanceof EvaUnit01Entity eva))return;
        if(event.phase==TickEvent.Phase.START)
        {
            if(camera==null||camera.level()!=mc.level){camera=net.minecraft.world.entity.EntityType.ARMOR_STAND.create(mc.level);camera.setInvisible(true);}
            float partial=event.renderTickTime;
            Vec3 base=new Vec3(net.minecraft.util.Mth.lerp((double)partial,eva.xOld,eva.getX()),net.minecraft.util.Mth.lerp((double)partial,eva.yOld,eva.getY()),net.minecraft.util.Mth.lerp((double)partial,eva.zOld,eva.getZ()))
                    .add(mc.getEntityRenderDispatcher().getRenderer(eva).getRenderOffset(eva,partial)),p,target;
            switch(TvFacilityR16Review.shot)
            {
                case 1 -> {p=new Vec3(42,-379,-75);target=new Vec3(30,-391,-89);}
                case 2 -> {p=new Vec3(44,-383,-116);target=new Vec3(30,-413,-96);}
                case 3 -> {p=new Vec3(40,-369,base.z-13);target=base.add(0,34,0);}
                case 4 -> {p=new Vec3(30,-363,-44);target=new Vec3(30,-294,-36);}
                case 5 -> {p=base.add(11,55,-13);target=base.add(0,40,0);}
                case 6,7 -> {p=new Vec3(72,123,-100);target=new Vec3(30,114,-36);}
                case 8 -> {p=new Vec3(30,155,-85);target=new Vec3(30,80,-36);}
                default -> {p=new Vec3(32,-388,-121);target=new Vec3(30,-395,-96);}
            }
            Vec3 d=target.subtract(p);camera.setPos(p.x,p.y-camera.getEyeHeight(),p.z);camera.xo=camera.xOld=camera.getX();camera.yo=camera.yOld=camera.getY();camera.zo=camera.zOld=camera.getZ();
            camera.setYRot((float)Math.toDegrees(Math.atan2(-d.x,d.z)));camera.yRotO=camera.yHeadRot=camera.yHeadRotO=camera.getYRot();camera.setXRot((float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance())));camera.xRotO=camera.getXRot();mc.options.hideGui=true;mc.options.setCameraType(CameraType.FIRST_PERSON);mc.setCameraEntity(camera);
            return;
        }
        String hatchPhoto=TvFacilityR16Review.hatchPhoto;
        if(!hatchPhoto.isEmpty()&&!TvFacilityR16Review.capturedPhotos.contains(hatchPhoto))
        {
            try(var image=Screenshot.takeScreenshot(mc.getMainRenderTarget()))
            {
                Path out=folder.resolve("hatches");Files.createDirectories(out);image.writeToFile(out.resolve(hatchPhoto));TvFacilityR16Review.capturedPhotos.add(hatchPhoto);
            }
            catch(Exception e){ProjectSeele.LOGGER.error("Hatch photograph failed",e);}
        }
        String clip=TvFacilityR16Review.capture;if(clip.isEmpty())return;long now=System.nanoTime();if(now-lastNanos<33_333_333L)return;lastNanos=now;
        if(WRITER.getQueue().remainingCapacity()==0){dropped++;return;}
        try
        {
            Path out=folder.resolve(clip);Files.createDirectories(out);var rows=FRAMES.computeIfAbsent(clip,k->new JsonArray());long start=STARTS.computeIfAbsent(clip,k->now);
            String name=String.format("frame_%05d.jpg",rows.size());var frame=new JsonObject();frame.addProperty("file",name);frame.addProperty("seconds",(now-start)/1e9);frame.addProperty("tick",TvFacilityR16Review.tick);frame.addProperty("phase",TvFacilityR16Review.phase);frame.addProperty("phase_tick",TvFacilityR16Review.phaseTick);frame.addProperty("shot",TvFacilityR16Review.shot);frame.addProperty("eva_y",eva.getY());frame.addProperty("fps",mc.getFps());frame.addProperty("active",true);
            var image=Screenshot.takeScreenshot(mc.getMainRenderTarget());rows.add(frame);
            WRITER.execute(()->{try(image){NativeReviewFrames.writeJpeg(image,out.resolve(name));}catch(Exception e){writeFailure=e.toString();ProjectSeele.LOGGER.error("R16 native frame failed",e);}});
        }
        catch(Exception e){writeFailure=e.toString();ProjectSeele.LOGGER.error("R16 framebuffer failed",e);}
    }
    private static void placeCamera(Minecraft mc,Vec3 p,Vec3 target)
    {
        if(p==null||target==null)return;if(camera==null||camera.level()!=mc.level){camera=net.minecraft.world.entity.EntityType.ARMOR_STAND.create(mc.level);camera.setInvisible(true);}
        Vec3 d=target.subtract(p);camera.setPos(p.x,p.y-camera.getEyeHeight(),p.z);camera.xo=camera.xOld=camera.getX();camera.yo=camera.yOld=camera.getY();camera.zo=camera.zOld=camera.getZ();camera.setYRot((float)Math.toDegrees(Math.atan2(-d.x,d.z)));camera.yRotO=camera.yHeadRot=camera.yHeadRotO=camera.getYRot();camera.setXRot((float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance())));camera.xRotO=camera.getXRot();mc.options.hideGui=true;mc.options.setCameraType(CameraType.FIRST_PERSON);mc.setCameraEntity(camera);
    }
    private TvFacilityR16Client() {}
}
