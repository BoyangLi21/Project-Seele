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
    private static int end,oldDistance;private static boolean saved,pause,oldGui;
    private static net.minecraft.client.CameraType oldCamera;
    private static net.minecraft.world.entity.Entity camera;
    private static java.io.BufferedWriter trace;
    private static java.nio.file.Path folder;
    private static int imageCase=-1;
    private static long previousFrame;
    private static long nextMovieFrame;
    private static int movieCase=-1,movieFrame;private static boolean jumpSent,lastCrouch;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!EvaTerrainR11Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        if(EvaTerrainR11Review.R30&&mc.screen instanceof net.minecraft.client.gui.screens.DeathScreen){if(mc.player.isDeadOrDying())mc.player.respawn();mc.setScreen(null);return;}
        if(!saved){saved=true;pause=mc.options.pauseOnLostFocus;oldGui=mc.options.hideGui;oldCamera=mc.options.getCameraType();mc.options.pauseOnLostFocus=false;oldDistance=mc.options.renderDistance().get();if(EvaTerrainR11Review.R19){mc.options.renderDistance().set(8);mc.options.broadcastOptions();}
            try{folder=mc.gameDirectory.toPath().resolve((EvaTerrainR11Review.R30?"../artifacts/facility_r30/terrain_":EvaTerrainR11Review.R25?"../artifacts/facility_r25/terrain_":EvaTerrainR11Review.R21?"../artifacts/un_models_r21/terrain_"+System.getProperty("projectseele.regionalBuild")+"_":EvaTerrainR11Review.R19?"../artifacts/world_repair_r19/un_terrain_":"../artifacts/world_motion_r11/terrain_visual_")+System.currentTimeMillis()).normalize();java.nio.file.Files.createDirectories(folder);trace=java.nio.file.Files.newBufferedWriter(folder.resolve("frames.jsonl"));}catch(Exception e){throw new IllegalStateException(e);}}
        EvaTerrainR11Review.tracked=mc.level.getEntity(EvaTerrainR11Review.actor)!=null;EvaTerrainR11Review.mounted=mc.player.getRootVehicle().getId()==EvaTerrainR11Review.actor;
        boolean driving=EvaTerrainR11Review.forward!=0;
        if(EvaTerrainR11Review.R30&&mc.level.getEntity(EvaTerrainR11Review.actor) instanceof com.projectseele.entity.EvaUnit01Entity endCheck&&endCheck.getZ()>=153)driving=false;
        mc.options.keyUp.setDown(driving);mc.options.keyJump.setDown(!EvaTerrainR11Review.R30&&EvaTerrainR11Review.jump);
        mc.options.keySprint.setDown(EvaTerrainR11Review.mounted&&(EvaTerrainR11Review.caseIndex==2||EvaTerrainR11Review.caseIndex==3));
        if(EvaTerrainR11Review.RIFLE||EvaTerrainR11Review.R30)mc.options.keyAttack.setDown(EvaTerrainR11Review.runningCase&&EvaTerrainR11Review.caseTick%60>=10&&EvaTerrainR11Review.caseTick%60<15);
        mc.options.keyShift.setDown(EvaTerrainR11Review.mounted&&EvaTerrainR11Review.crouchInput);
        if(EvaTerrainR11Review.R30)
        {
            // Forge's crouch binding polls GLFW directly; use its real network
            // command in the unattended fixture instead of pretending a raw key exists.
            boolean c=EvaTerrainR11Review.mounted&&EvaTerrainR11Review.crouchInput;
            if(c!=lastCrouch){lastCrouch=c;com.projectseele.network.SeeleNetwork.CHANNEL.sendToServer(new com.projectseele.network.ServerboundEvaControlPacket(c?com.projectseele.network.ServerboundEvaControlPacket.ACTION_CROUCH_START:com.projectseele.network.ServerboundEvaControlPacket.ACTION_CROUCH_STOP));}
            if(EvaTerrainR11Review.jump&&!jumpSent){jumpSent=true;com.projectseele.network.SeeleNetwork.CHANNEL.sendToServer(new com.projectseele.network.ServerboundEvaControlPacket(com.projectseele.network.ServerboundEvaControlPacket.ACTION_JUMP,9000+EvaTerrainR11Review.caseIndex));}
            if(!EvaTerrainR11Review.jump)jumpSent=false;
        }
        mc.player.input.up=driving;mc.player.input.down=false;mc.player.input.forwardImpulse=driving?1:0;mc.player.zza=driving?1:0;mc.player.xxa=0;mc.player.input.jumping=!EvaTerrainR11Review.R30&&EvaTerrainR11Review.jump;
        mc.player.setYRot(EvaTerrainR11Review.heading);
        mc.player.setXRot((EvaTerrainR11Review.R25||EvaTerrainR11Review.R30)&&(EvaTerrainR11Review.caseIndex==5||EvaTerrainR11Review.caseIndex==8)
                ?(float)(Math.sin(EvaTerrainR11Review.caseTick/32D)*60):0);
        if(EvaTerrainR11Review.finished&&++end>35){mc.options.keyUp.setDown(false);mc.options.keyJump.setDown(false);mc.options.keyShift.setDown(false);mc.options.keySprint.setDown(false);mc.options.keyAttack.setDown(false);if(EvaTerrainR11Review.R19){mc.options.renderDistance().set(oldDistance);mc.options.broadcastOptions();}mc.options.pauseOnLostFocus=pause;mc.options.hideGui=oldGui;mc.options.setCameraType(oldCamera);mc.setCameraEntity(mc.player);try{trace.close();}catch(Exception ignored){}mc.stop();}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!EvaTerrainR11Review.ENABLED||!saved||end>0)return;var mc=Minecraft.getInstance();if(mc.level==null||!(mc.level.getEntity(EvaTerrainR11Review.actor) instanceof com.projectseele.entity.EvaUnit01Entity eva))return;
        if(event.phase==TickEvent.Phase.START)
        {
            if(EvaTerrainR11Review.R30&&EvaTerrainR11Review.caseIndex==9){mc.setCameraEntity(mc.player);mc.options.hideGui=false;mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);return;}
            if(camera==null){camera=net.minecraft.world.entity.EntityType.ARMOR_STAND.create(mc.level);camera.setInvisible(true);}
            double low=Math.min(1,eva.rifleStanceLevel(event.renderTickTime)/3);var p=eva.getPosition(event.renderTickTime).add(EvaTerrainR11Review.caseIndex==5?0:65,EvaTerrainR11Review.caseIndex==5?18:32-18*low,EvaTerrainR11Review.caseIndex==5?72:48);var target=eva.getPosition(event.renderTickTime).add(0,25-18*low,0);var dir=target.subtract(p);
            camera.setPos(p.x,p.y-camera.getEyeHeight(),p.z);camera.xo=camera.xOld=camera.getX();camera.yo=camera.yOld=camera.getY();camera.zo=camera.zOld=camera.getZ();camera.setYRot((float)Math.toDegrees(Math.atan2(-dir.x,dir.z)));camera.setYHeadRot(camera.getYRot());if(camera instanceof net.minecraft.world.entity.LivingEntity living)living.yHeadRotO=living.yHeadRot;camera.setXRot((float)-Math.toDegrees(Math.atan2(dir.y,dir.horizontalDistance())));camera.yRotO=camera.getYRot();camera.xRotO=camera.getXRot();mc.options.hideGui=true;mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);mc.setCameraEntity(camera);return;
        }
        try
        {
            if(EvaTerrainR11Review.R30&&EvaTerrainR11Review.mounted&&!EvaTerrainR11Review.runningCase)EvaTerrainR11Review.warmedFrames++;
            long now=System.nanoTime();com.google.gson.JsonObject d=new com.google.gson.JsonObject();d.addProperty("case",EvaTerrainR11Review.caseIndex);d.addProperty("tick",EvaTerrainR11Review.caseTick);d.addProperty("frame_ms",previousFrame==0?0:(now-previousFrame)/1e6);previousFrame=now;var p=eva.getPosition(event.renderTickTime);d.addProperty("x",p.x);d.addProperty("y",p.y);d.addProperty("z",p.z);d.addProperty("stance",eva.rifleStanceLevel(event.renderTickTime));d.addProperty("gait",eva.rifleGaitPhase(event.renderTickTime));d.addProperty("run",eva.rifleRunBlend(event.renderTickTime));d.addProperty("air",eva.isVisuallyAirborneForRender());
            var support=com.projectseele.client.render.EvaFootPlacement.LAST.get(eva.getId());if(support!=null){var a=new com.google.gson.JsonArray();for(double v:support)a.add(Double.isFinite(v)?v:0);d.add("foot_support",a);}trace.write(d.toString());trace.newLine();
            if(EvaTerrainR11Review.runningCase&&EvaTerrainR11Review.caseTick>=(EvaTerrainR11Review.caseIndex==8&&!EvaTerrainR11Review.R25?350:100)&&Math.abs(eva.getX()-(EvaTerrainR11Review.caseIndex*96+.5))<30&&imageCase!=EvaTerrainR11Review.caseIndex)
            {imageCase=EvaTerrainR11Review.caseIndex;try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){image.writeToFile(folder.resolve("case_"+imageCase+".png"));}}
            if(EvaTerrainR11Review.R19&&EvaTerrainR11Review.runningCase)
            {
                int c=EvaTerrainR11Review.caseIndex,t=EvaTerrainR11Review.caseTick;
                int begin=c==6?30:c==8?280:c==9?20:80,finish=c==9?300:begin+130;
                if(t>=begin&&t<=finish&&now>=nextMovieFrame)
                {
                    if(movieCase!=c){movieCase=c;movieFrame=0;java.nio.file.Files.createDirectories(folder.resolve("clip_"+c));}
                    try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget()))
                    {NativeReviewFrames.writeJpeg(image,folder.resolve("clip_"+c).resolve(String.format(java.util.Locale.ROOT,"%05d.jpg",movieFrame++)));}
                    nextMovieFrame=now+50_000_000L;
                }
            }
        }
        catch(Exception e){throw new IllegalStateException("R11 visual telemetry",e);}
    }
}
