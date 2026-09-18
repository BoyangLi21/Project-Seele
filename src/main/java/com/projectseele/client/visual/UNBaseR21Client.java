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
    private static Path folder;private static int end;private static net.minecraft.world.entity.LivingEntity camera;private static String view="";private static long viewSince;private static int settled,oldDistance;private static boolean saved,oldPause,oldGui;private static net.minecraft.client.CameraType oldCamera;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!UNBaseR21Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null)return;
        if(!saved){saved=true;oldPause=mc.options.pauseOnLostFocus;oldGui=mc.options.hideGui;oldCamera=mc.options.getCameraType();oldDistance=mc.options.renderDistance().get();mc.options.renderDistance().set(12);mc.options.broadcastOptions();}
        mc.options.pauseOnLostFocus=false;int move=UNBaseR21Review.forward;mc.options.keyUp.setDown(move>0);mc.options.keyDown.setDown(move<0);mc.options.keySprint.setDown(false);mc.options.keyJump.setDown(false);mc.options.keyShift.setDown(false);
        if(mc.player.getRootVehicle() instanceof EvaPrototypeEntity){mc.player.setYRot(0);mc.player.setXRot(0);mc.player.input.forwardImpulse=move;mc.player.zza=move;}
        if(UNBaseR21Review.finished&&++end>40){mc.options.keyUp.setDown(false);mc.options.keyDown.setDown(false);mc.options.hideGui=oldGui;mc.options.pauseOnLostFocus=oldPause;mc.options.setCameraType(oldCamera);mc.options.renderDistance().set(oldDistance);mc.options.broadcastOptions();mc.setCameraEntity(mc.player);mc.stop();}
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
                var origin=eva.getPosition(event.renderTickTime);var eye=origin.add(34,65,60);var target=origin.add(0,32,0);var d=target.subtract(eye);
                camera.setPos(eye.x,eye.y-camera.getEyeHeight(),eye.z);camera.xo=camera.xOld=camera.getX();camera.yo=camera.yOld=camera.getY();camera.zo=camera.zOld=camera.getZ();camera.setYRot((float)Math.toDegrees(Math.atan2(-d.x,d.z)));camera.yRotO=camera.yHeadRot=camera.yHeadRotO=camera.getYRot();camera.setXRot((float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance())));camera.xRotO=camera.getXRot();mc.setCameraEntity(camera);
            }
            if(!shot.equals(view))viewSince=System.nanoTime();settled=shot.equals(view)?settled+1:0;view=shot;return;
        }
        if(shot.isEmpty()||!shot.equals(view)||settled<40||System.nanoTime()-viewSince<10_000_000_000L||UNBaseR21Review.captured.contains(shot))return;
        try(var pixels=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget()))
        {if(folder==null){folder=mc.gameDirectory.toPath().resolve("../artifacts/un_models_r21/base_native_"+System.currentTimeMillis()).normalize();Files.createDirectories(folder);}pixels.writeToFile(folder.resolve(shot+".png"));UNBaseR21Review.captured.add(shot);}
        catch(Exception failure){throw new IllegalStateException(failure);}
    }
    private UNBaseR21Client(){}
}
