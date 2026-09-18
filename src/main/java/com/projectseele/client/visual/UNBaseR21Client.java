package com.projectseele.client.visual;
import com.projectseele.ProjectSeele;
import com.projectseele.visual.UNBaseR21Review;
import com.projectseele.entity.EvaPrototypeEntity;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class UNBaseR21Client
{
    private static final java.util.Set<String> pending=java.util.concurrent.ConcurrentHashMap.newKeySet();
    private static final java.util.concurrent.ExecutorService writer=java.util.concurrent.Executors.newSingleThreadExecutor(r->{var t=new Thread(r,"seele-un-review-images");t.setDaemon(true);return t;});
    private static final com.google.gson.JsonArray captureManifest=new com.google.gson.JsonArray();
    private static Path folder;private static int end;private static net.minecraft.world.entity.LivingEntity camera;private static String view="";private static long viewSince;private static int settled,oldDistance;private static boolean saved,oldPause,oldGui;private static net.minecraft.client.CameraType oldCamera;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!UNBaseR21Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null)return;
        if(!saved){saved=true;oldPause=mc.options.pauseOnLostFocus;oldGui=mc.options.hideGui;oldCamera=mc.options.getCameraType();oldDistance=mc.options.renderDistance().get();mc.options.renderDistance().set(12);mc.options.broadcastOptions();}
        mc.options.pauseOnLostFocus=false;int move=UNBaseR21Review.forward;mc.options.keyUp.setDown(move>0);mc.options.keyDown.setDown(move<0);mc.options.keySprint.setDown(false);mc.options.keyJump.setDown(false);mc.options.keyShift.setDown(false);
        if(mc.player.getRootVehicle() instanceof EvaPrototypeEntity){mc.player.setYRot(0);mc.player.setXRot(0);mc.player.input.forwardImpulse=move;mc.player.zza=move;}
        if(UNBaseR21Review.finished)
        {
            if(++end==1)writer.shutdown();
            if(end>40&&writer.isTerminated()){mc.options.keyUp.setDown(false);mc.options.keyDown.setDown(false);mc.options.hideGui=oldGui;mc.options.pauseOnLostFocus=oldPause;mc.options.setCameraType(oldCamera);mc.options.renderDistance().set(oldDistance);mc.options.broadcastOptions();mc.setCameraEntity(mc.player);mc.stop();}
        }
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!UNBaseR21Review.ENABLED||UNBaseR21Review.finished)return;var mc=Minecraft.getInstance();if(mc.level==null||!(mc.level.getEntity(UNBaseR21Review.actor) instanceof EvaPrototypeEntity eva))return;
        String shot=UNBaseR21Review.shot;
        if(event.phase==TickEvent.Phase.START)
        {
            mc.options.hideGui=!shot.endsWith("pilot_view");mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);
            if(shot.endsWith("pilot_view"))mc.setCameraEntity(mc.player);
            else
            {
                if(camera==null){camera=net.minecraft.world.entity.EntityType.ARMOR_STAND.create(mc.level);camera.setInvisible(true);}
                var origin=eva.getPosition(event.renderTickTime);var eye=origin.add(34,65,60);var target=origin.add(0,32,0);
                if(shot.endsWith("head_detail")){target=com.projectseele.entity.EvaUNOptics.eye(eva,event.renderTickTime);eye=target.add(0,1,12);}
                if(shot.endsWith("hand_detail"))
                {
                    var pose=com.projectseele.entity.EvaBodyPose.sample(eva,event.renderTickTime);var bone=pose.rig.get("hand_r");
                    var hand=new org.joml.Matrix4f(com.projectseele.entity.EvaRifleKinematics.world(eva,event.renderTickTime)).mul(pose.matrix("hand_r")).transformPosition(new org.joml.Vector3f(bone.pivot()));
                    target=new net.minecraft.world.phys.Vec3(hand.x,hand.y-1.3,hand.z);eye=target.add(Math.signum(hand.x-origin.x)*7,2,8);
                }
                var d=target.subtract(eye);
                camera.setPos(eye.x,eye.y-camera.getEyeHeight(),eye.z);camera.xo=camera.xOld=camera.getX();camera.yo=camera.yOld=camera.getY();camera.zo=camera.zOld=camera.getZ();camera.setYRot((float)Math.toDegrees(Math.atan2(-d.x,d.z)));camera.yRotO=camera.yHeadRot=camera.yHeadRotO=camera.getYRot();camera.setXRot((float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance())));camera.xRotO=camera.getXRot();mc.setCameraEntity(camera);
            }
            if(!shot.equals(view))viewSince=System.nanoTime();settled=shot.equals(view)?settled+1:0;view=shot;return;
        }
        boolean attack=shot.contains("_attack_");
        if(shot.isEmpty()||!shot.equals(view)||settled<(attack?0:40)||System.nanoTime()-viewSince<(attack?0L:10_000_000_000L)||UNBaseR21Review.captured.contains(shot))return;
        if(!pending.add(shot))return;
        try
        {
            if(folder==null){folder=mc.gameDirectory.toPath().resolve((UNBaseR21Review.R22?"../artifacts/access_r22/models/base_native_":"../artifacts/un_models_r21/base_native_")+System.currentTimeMillis()).normalize();Files.createDirectories(folder);}
            var pixels=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget());var file=folder.resolve(shot+".png");var manifest=folder.resolve("capture_manifest.json");int cycle=UNBaseR21Review.attackCycle;long tick=mc.level.getGameTime();
            writer.submit(()->{try(pixels){pixels.writeToFile(file);var row=new com.google.gson.JsonObject();row.addProperty("shot",shot);row.addProperty("game_tick",tick);row.addProperty("native_attack_cycle",attack?cycle:0);captureManifest.add(row);Files.writeString(manifest,captureManifest.toString());UNBaseR21Review.captured.add(shot);}catch(Exception error){ProjectSeele.LOGGER.error("Native UN review image failed",error);pending.remove(shot);}});
        }
        catch(Exception failure){throw new IllegalStateException(failure);}
    }
    private UNBaseR21Client(){}
}
