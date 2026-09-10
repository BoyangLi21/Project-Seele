package com.projectseele.client.visual;
import com.projectseele.ProjectSeele;
import com.projectseele.visual.EvaTerrainR11Review;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class EvaTerrainR11Client
{
    private static int end;private static boolean saved,pause,oldGui;
    private static net.minecraft.client.CameraType oldCamera;
    private static net.minecraft.world.entity.Entity camera;
    private static java.io.BufferedWriter trace;
    private static java.nio.file.Path folder;
    private static int imageCase=-1;
    private static long previousFrame;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!EvaTerrainR11Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        if(!saved){saved=true;pause=mc.options.pauseOnLostFocus;oldGui=mc.options.hideGui;oldCamera=mc.options.getCameraType();mc.options.pauseOnLostFocus=false;
            try{folder=mc.gameDirectory.toPath().resolve("../artifacts/world_motion_r11/terrain_visual_"+System.currentTimeMillis()).normalize();java.nio.file.Files.createDirectories(folder);trace=java.nio.file.Files.newBufferedWriter(folder.resolve("frames.jsonl"));}catch(Exception e){throw new IllegalStateException(e);}}
        EvaTerrainR11Review.tracked=mc.level.getEntity(EvaTerrainR11Review.actor)!=null;EvaTerrainR11Review.mounted=mc.player.getRootVehicle().getId()==EvaTerrainR11Review.actor;
        mc.options.keyUp.setDown(EvaTerrainR11Review.forward!=0);mc.options.keyJump.setDown(EvaTerrainR11Review.jump);
        mc.options.keySprint.setDown(EvaTerrainR11Review.mounted&&(EvaTerrainR11Review.caseIndex==2||EvaTerrainR11Review.caseIndex==3));
        mc.options.keyShift.setDown(EvaTerrainR11Review.mounted&&EvaTerrainR11Review.crouchInput);
        mc.player.input.up=EvaTerrainR11Review.forward!=0;mc.player.input.down=false;mc.player.input.forwardImpulse=EvaTerrainR11Review.forward;mc.player.zza=EvaTerrainR11Review.forward;mc.player.xxa=0;mc.player.input.jumping=EvaTerrainR11Review.jump;
        mc.player.setYRot(EvaTerrainR11Review.heading);mc.player.setXRot(0);
        if(EvaTerrainR11Review.finished&&++end>35){mc.options.keyUp.setDown(false);mc.options.keyJump.setDown(false);mc.options.keyShift.setDown(false);mc.options.keySprint.setDown(false);mc.options.pauseOnLostFocus=pause;mc.options.hideGui=oldGui;mc.options.setCameraType(oldCamera);mc.setCameraEntity(mc.player);try{trace.close();}catch(Exception ignored){}mc.stop();}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!EvaTerrainR11Review.ENABLED||!saved||end>0)return;var mc=Minecraft.getInstance();if(mc.level==null||!(mc.level.getEntity(EvaTerrainR11Review.actor) instanceof com.projectseele.entity.EvaUnit01Entity eva))return;
        if(event.phase==TickEvent.Phase.START)
        {
            if(camera==null){camera=net.minecraft.world.entity.EntityType.ARMOR_STAND.create(mc.level);camera.setInvisible(true);}
            double low=Math.min(1,eva.rifleStanceLevel(event.renderTickTime)/3);var p=eva.getPosition(event.renderTickTime).add(EvaTerrainR11Review.caseIndex==5?0:65,EvaTerrainR11Review.caseIndex==5?18:32-18*low,EvaTerrainR11Review.caseIndex==5?72:48);var target=eva.getPosition(event.renderTickTime).add(0,25-18*low,0);var dir=target.subtract(p);
            camera.setPos(p.x,p.y-camera.getEyeHeight(),p.z);camera.xo=camera.xOld=camera.getX();camera.yo=camera.yOld=camera.getY();camera.zo=camera.zOld=camera.getZ();camera.setYRot((float)Math.toDegrees(Math.atan2(-dir.x,dir.z)));camera.setYHeadRot(camera.getYRot());if(camera instanceof net.minecraft.world.entity.LivingEntity living)living.yHeadRotO=living.yHeadRot;camera.setXRot((float)-Math.toDegrees(Math.atan2(dir.y,dir.horizontalDistance())));camera.yRotO=camera.getYRot();camera.xRotO=camera.getXRot();mc.options.hideGui=true;mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);mc.setCameraEntity(camera);return;
        }
        try
        {
            long now=System.nanoTime();com.google.gson.JsonObject d=new com.google.gson.JsonObject();d.addProperty("case",EvaTerrainR11Review.caseIndex);d.addProperty("tick",EvaTerrainR11Review.caseTick);d.addProperty("frame_ms",previousFrame==0?0:(now-previousFrame)/1e6);previousFrame=now;var p=eva.getPosition(event.renderTickTime);d.addProperty("x",p.x);d.addProperty("y",p.y);d.addProperty("z",p.z);d.addProperty("stance",eva.rifleStanceLevel(event.renderTickTime));d.addProperty("gait",eva.rifleGaitPhase(event.renderTickTime));d.addProperty("run",eva.rifleRunBlend(event.renderTickTime));d.addProperty("air",eva.isVisuallyAirborneForRender());
            var support=com.projectseele.client.render.EvaFootPlacement.LAST.get(eva.getId());if(support!=null){var a=new com.google.gson.JsonArray();for(double v:support)a.add(Double.isFinite(v)?v:0);d.add("foot_support",a);}trace.write(d.toString());trace.newLine();
            if(EvaTerrainR11Review.runningCase&&EvaTerrainR11Review.caseTick>=(EvaTerrainR11Review.caseIndex==8?350:100)&&Math.abs(eva.getX()-(EvaTerrainR11Review.caseIndex*96+.5))<30&&imageCase!=EvaTerrainR11Review.caseIndex)
            {imageCase=EvaTerrainR11Review.caseIndex;try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){image.writeToFile(folder.resolve("case_"+imageCase+".png"));}}
        }
        catch(Exception e){throw new IllegalStateException("R11 visual telemetry",e);}
    }
}
