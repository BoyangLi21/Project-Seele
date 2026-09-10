package com.projectseele.client.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.visual.NervStaffR15Review;
import net.minecraft.client.Minecraft;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class NervStaffR15Client
{
    @SubscribeEvent(priority=net.minecraftforge.eventbus.api.EventPriority.HIGHEST)
    public static void hideCameraOperator(net.minecraftforge.client.event.RenderPlayerEvent.Pre event)
    {
        if(NervStaffR15Review.ENABLED&&event.getEntity()==Minecraft.getInstance().player)event.setCanceled(true);
    }
    private static boolean saved,pause,gui;private static int oldDistance,end,settled;private static String view="";
    private static net.minecraft.client.CameraType oldCamera;
    private static net.minecraft.world.entity.LivingEntity camera;private static Path folder;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!NervStaffR15Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        if(!saved)
        {
            saved=true;pause=mc.options.pauseOnLostFocus;gui=mc.options.hideGui;oldCamera=mc.options.getCameraType();oldDistance=mc.options.renderDistance().get();mc.options.pauseOnLostFocus=false;mc.options.renderDistance().set(6);mc.options.broadcastOptions();mc.levelRenderer.allChanged();
            folder=mc.gameDirectory.toPath().resolve("../artifacts/staff_world_r15/native_"+System.currentTimeMillis()).normalize();try{Files.createDirectories(folder);}catch(Exception e){throw new IllegalStateException(e);}
        }
        if(NervStaffR15Review.finished&&++end>35){mc.options.renderDistance().set(oldDistance);mc.options.broadcastOptions();mc.options.pauseOnLostFocus=pause;mc.options.hideGui=gui;mc.options.setCameraType(oldCamera);mc.setCameraEntity(mc.player);mc.stop();}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!NervStaffR15Review.ENABLED||!saved||end>0)return;var mc=Minecraft.getInstance();if(mc.level==null||mc.player==null)return;String name=NervStaffR15Review.photo;
        if(name.isEmpty()||NervStaffR15Review.captured.contains(name)){mc.setCameraEntity(mc.player);mc.options.hideGui=false;return;}
        if(event.phase==TickEvent.Phase.START)
        {
            if(camera==null||camera.level()!=mc.level){camera=net.minecraft.world.entity.EntityType.ARMOR_STAND.create(mc.level);camera.setInvisible(true);}
            settled=name.equals(view)?settled+1:0;view=name;
            Vec3 p=name.equals("command_staff")?new Vec3(27.5,-407.3,279.5):mc.player.position().add(9,2,-9);
            Vec3 target=name.equals("command_staff")?new Vec3(29,-407.8,283):mc.player.position().add(0,-.7,0);
            Vec3 d=target.subtract(p);camera.setPos(p.x,p.y-camera.getEyeHeight(),p.z);camera.xo=camera.xOld=camera.getX();camera.yo=camera.yOld=camera.getY();camera.zo=camera.zOld=camera.getZ();
            camera.setYRot((float)Math.toDegrees(Math.atan2(-d.x,d.z)));camera.yRotO=camera.yHeadRot=camera.yHeadRotO=camera.getYRot();camera.setXRot((float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance())));camera.xRotO=camera.getXRot();mc.options.hideGui=true;mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);mc.setCameraEntity(camera);
        }
        else if(settled>120)
        {try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){image.writeToFile(folder.resolve(name+".png"));NervStaffR15Review.captured.add(name);}catch(Exception e){throw new IllegalStateException(e);}}
    }
    private NervStaffR15Client(){}
}
