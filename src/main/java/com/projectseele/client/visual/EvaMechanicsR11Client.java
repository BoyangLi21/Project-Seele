package com.projectseele.client.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.visual.EvaMechanicsR11Review;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.Set;
import java.util.HashSet;

@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class EvaMechanicsR11Client
{
    private static boolean saved,pause,gui;private static int end,oldDistance;private static net.minecraft.client.CameraType cameraType;private static net.minecraft.world.entity.LivingEntity camera;private static Path folder;private static final Set<String> shots=new HashSet<>();
    private static String framedView="";private static int settledFrames;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!(EvaMechanicsR11Review.ENABLED||com.projectseele.visual.EvaCanonicalR11Review.ENABLED)||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        if(!saved){saved=true;pause=mc.options.pauseOnLostFocus;gui=mc.options.hideGui;cameraType=mc.options.getCameraType();mc.options.pauseOnLostFocus=false;oldDistance=mc.options.renderDistance().get();mc.options.renderDistance().set(16);mc.options.broadcastOptions();mc.levelRenderer.allChanged();folder=mc.gameDirectory.toPath().resolve("../artifacts/world_motion_r11/mechanics_native_"+System.currentTimeMillis()).normalize();try{Files.createDirectories(folder);NativeVertexR11Audit.run(folder.resolve("vertex_equivalence.json"));}catch(Exception e){throw new IllegalStateException(e);}}
        EvaMechanicsR11Review.tracked=mc.level.getEntity(EvaMechanicsR11Review.actor)!=null;mc.options.keyUp.setDown(false);mc.options.keyJump.setDown(false);mc.options.keyShift.setDown(false);mc.options.keySprint.setDown(false);mc.player.setYRot(0);mc.player.setXRot(0);
        if(EvaMechanicsR11Review.finished&&++end>30){mc.options.renderDistance().set(oldDistance);mc.options.broadcastOptions();mc.options.pauseOnLostFocus=pause;mc.options.hideGui=gui;mc.options.setCameraType(cameraType);mc.setCameraEntity(mc.player);mc.stop();}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!(EvaMechanicsR11Review.ENABLED||com.projectseele.visual.EvaCanonicalR11Review.ENABLED)||!saved||end>0)return;var mc=Minecraft.getInstance();if(mc.level==null||!(mc.level.getEntity(EvaMechanicsR11Review.actor) instanceof com.projectseele.entity.EvaUnit01Entity eva))return;
        if(event.phase==TickEvent.Phase.START)
        {
            if(camera==null){camera=net.minecraft.world.entity.EntityType.ARMOR_STAND.create(mc.level);camera.setInvisible(true);}
            String view=EvaMechanicsR11Review.view;var origin=eva.getPosition(event.renderTickTime);var p=origin.add(view.equals("dorsal")?22:view.equals("combat")?70:45,view.equals("dorsal")?66:39,view.equals("dorsal")?-30:view.equals("combat")?30:48);if(view.equals("dorsal"))p=origin.add(new net.minecraft.world.phys.Vec3(22,63,-25).yRot((float)-Math.toRadians(eva.getYRot())));var target=origin.add(0,view.equals("dorsal")?54:view.equals("laser")?49:32,view.equals("combat")?24:0);
            if(view.equals("dorsal"))
            {
                var socket=com.projectseele.world.EntryPlugKinematics.socketTransform(eva).translation();
                p=socket.add(new net.minecraft.world.phys.Vec3(12,14,-17).yRot((float)-Math.toRadians(eva.getYRot())));target=socket.add(0,2,0);
            }
            settledFrames=view.equals(framedView)?settledFrames+1:0;framedView=view;
            if(view.startsWith("crane"))
            {
                var cranes=mc.level.getEntitiesOfClass(com.projectseele.entity.NervCarrierPlatformEntity.class,eva.getBoundingBox().inflate(150),c->c.isPlugCrane()&&c.getCranePlug()!=null);
                if(!cranes.isEmpty())
                {
                    var hoist=cranes.get(0).getPosition(event.renderTickTime);boolean detail=view.equals("crane_detail");
                    p=hoist.add(detail?12:20,detail?6:8,detail?13:25);target=hoist.add(0,detail?0:-9,0);
                }
            }
            var obstruction=mc.level.clip(new net.minecraft.world.level.ClipContext(target,p,net.minecraft.world.level.ClipContext.Block.COLLIDER,net.minecraft.world.level.ClipContext.Fluid.NONE,mc.player));
            if(obstruction.getType()!=net.minecraft.world.phys.HitResult.Type.MISS)p=obstruction.getLocation().subtract(p.subtract(target).normalize().scale(.65));
            var d=target.subtract(p);
            camera.setPos(p.x,p.y-camera.getEyeHeight(),p.z);camera.xo=camera.xOld=camera.getX();camera.yo=camera.yOld=camera.getY();camera.zo=camera.zOld=camera.getZ();camera.setYRot((float)Math.toDegrees(Math.atan2(-d.x,d.z)));camera.yRotO=camera.yHeadRot=camera.yHeadRotO=camera.getYRot();camera.setXRot((float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance())));camera.xRotO=camera.getXRot();mc.options.hideGui=true;mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);mc.setCameraEntity(camera);
        }
        else if(settledFrames>=2&&framedView.equals(EvaMechanicsR11Review.view)&&!EvaMechanicsR11Review.shot.isEmpty()&&(!(EvaMechanicsR11Review.shot.equals("eye_laser_contact")||EvaMechanicsR11Review.shot.equals("at_field_deflection"))||eva instanceof com.projectseele.entity.EvaPrototypeEntity un&&un.isEyeLaserActive()&&un.eyeLaserAge(event.renderTickTime)>=8.8F)&&shots.add(EvaMechanicsR11Review.shot))
        {try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){image.writeToFile(folder.resolve(EvaMechanicsR11Review.shot+".png"));EvaMechanicsR11Review.captured.add(EvaMechanicsR11Review.shot);}catch(Exception e){throw new IllegalStateException(e);}}
    }
}
