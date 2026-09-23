package com.projectseele.client.visual;

import com.projectseele.visual.NpcCombatR30Review;
import com.projectseele.client.screen.StaffConversationScreen;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class NpcCombatR30Client
{
    private static boolean started,oldPause;private static int end,ui,oldDistance,captureWait;private static Path folder;private static String candidate="";
    private static boolean click(StaffConversationScreen screen,String text)
    {
        for(var child:List.copyOf(screen.children()))if(child instanceof Button b&&b.active&&b.getMessage().getString().contains(text))
        {screen.mouseClicked(b.getX()+3,b.getY()+3,0);screen.mouseReleased(b.getX()+3,b.getY()+3,0);return true;}return false;
    }
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!NpcCombatR30Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        if(!started)
        {
            started=true;oldPause=mc.options.pauseOnLostFocus;mc.options.pauseOnLostFocus=false;oldDistance=mc.options.renderDistance().get();mc.options.renderDistance().set(10);mc.options.broadcastOptions();
            folder=mc.gameDirectory.toPath().resolve("../artifacts/facility_r30/native_npc_"+System.currentTimeMillis()).normalize();try{Files.createDirectories(folder);}catch(Exception e){throw new IllegalStateException(e);}NpcCombatR30Review.ready=true;
        }
        if(NpcCombatR30Review.finished){if(++end>40){mc.options.pauseOnLostFocus=oldPause;mc.options.renderDistance().set(oldDistance);mc.setScreen(null);mc.stop();}return;}
        if(!candidate.equals(NpcCombatR30Review.photo)){candidate=NpcCombatR30Review.photo;captureWait=candidate.equals("mission_selection")?2:30;}else if(captureWait>0)captureWait--;
        if(NpcCombatR30Review.input.equals("close")){if(mc.screen!=null)mc.setScreen(null);return;}
        if(NpcCombatR30Review.input.equals("start_mission")&&mc.screen instanceof StaffConversationScreen screen)
        {
            if(ui==0&&click(screen,"作战记录"))ui=1;
            else if(ui==1){if(!NpcCombatR30Review.ASUKA||click(screen,"夏姆榭尔"))ui=2;}
            else if(ui==2){if(!NpcCombatR30Review.ASUKA||click(screen,"二号机"))ui=3;}
            else if(ui==3&&click(screen,NpcCombatR30Review.ASUKA?"明日香·兰格雷出战":"碇真嗣出战")){ui=4;NpcCombatR30Review.photo="mission_selection";}
            else if(ui==4&&NpcCombatR30Review.photos.contains("mission_selection")&&click(screen,"出击 / 加入增援"))ui=5;
        }
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!NpcCombatR30Review.ENABLED||!started)return;var mc=Minecraft.getInstance();
        if(event.phase==TickEvent.Phase.START&&mc.player!=null&&NpcCombatR30Review.lookTarget!=null)
        {var d=NpcCombatR30Review.lookTarget.subtract(mc.player.getEyePosition());float yaw=(float)Math.toDegrees(Math.atan2(-d.x,d.z)),pitch=(float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance()));mc.player.setYRot(yaw);mc.player.yRotO=yaw;mc.player.setXRot(pitch);mc.player.xRotO=pitch;}
        if(event.phase!=TickEvent.Phase.END)return;String name=NpcCombatR30Review.photo;if(name.isEmpty()||NpcCombatR30Review.photos.contains(name))return;
        if(captureWait>0||!candidate.equals(name)||!name.equals("mission_selection")&&mc.screen!=null)return;
        try(var frame=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){NativeReviewFrames.writeJpeg(frame,folder.resolve(name+".jpg"));NpcCombatR30Review.photos.add(name);}catch(Exception e){throw new IllegalStateException(e);}
    }
    private NpcCombatR30Client(){}
}
