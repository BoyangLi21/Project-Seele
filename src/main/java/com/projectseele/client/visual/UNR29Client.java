package com.projectseele.client.visual;

import com.projectseele.visual.UNR29Review;
import com.projectseele.client.Keybinds;
import com.projectseele.client.screen.UNPhoneScreen;
import net.minecraft.client.Minecraft;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.gui.components.*;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class UNR29Client
{
    private static boolean started,oldPause;private static int end,oldDistance;private static Path folder;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!UNR29Review.ENABLED)return;var mc=Minecraft.getInstance();if(mc.player==null)return;
        if(event.phase==TickEvent.Phase.START)
        {
            mc.options.keyJump.setDown(UNR29Review.flightKeys.equals("up"));mc.options.keyUp.setDown(UNR29Review.flightKeys.equals("forward"));mc.options.keySprint.setDown(UNR29Review.flightKeys.equals("forward"));return;
        }
        if(!started)
        {
            started=true;oldPause=mc.options.pauseOnLostFocus;mc.options.pauseOnLostFocus=false;oldDistance=mc.options.renderDistance().get();mc.options.renderDistance().set(16);mc.options.broadcastOptions();folder=mc.gameDirectory.toPath().resolve("../artifacts/facility_r29/native_un_"+System.currentTimeMillis()).normalize();
            try{Files.createDirectories(folder);}catch(Exception e){throw new IllegalStateException(e);}UNR29Review.ready=true;
        }
        if(UNR29Review.finished)
        {if(++end>30){mc.options.keyJump.setDown(false);mc.options.keyUp.setDown(false);mc.options.keySprint.setDown(false);mc.options.pauseOnLostFocus=oldPause;mc.options.renderDistance().set(oldDistance);mc.options.broadcastOptions();mc.setScreen(null);mc.stop();}return;}
        String command=UNR29Review.input;
        if(command.equals("close")){if(mc.screen!=null)mc.setScreen(null);return;}
        if(command.isEmpty()||UNR29Review.inputs.contains(command))return;
        if(command.startsWith("flight")||command.equals("land"))
        {KeyMapping.click(Keybinds.UN_FLIGHT.getKey());UNR29Review.inputs.add(command);return;}
        if(command.startsWith("deliver")&&mc.screen instanceof UNPhoneScreen screen)
        {
            if(!UNR29Review.photos.contains("un_phone")){UNR29Review.photo="un_phone";return;}
            int serial=command.endsWith("1")?1:0;
            for(var child:List.copyOf(screen.children()))if(child instanceof Button b&&b.getMessage().getString().equals("EVA-UN-0"+serial)){screen.mouseClicked(b.getX()+3,b.getY()+3,0);screen.mouseReleased(b.getX()+3,b.getY()+3,0);}
            var boxes=screen.children().stream().filter(x->x instanceof EditBox).map(x->(EditBox)x).toList();if(boxes.size()!=2)return;
            boxes.get(0).setValue(serial==0?"6400":"6260");boxes.get(1).setValue("-5820");
            for(var child:List.copyOf(screen.children()))if(child instanceof Button b&&b.getMessage().getString().equals("投放到指定 X / Z"))
            {screen.mouseClicked(b.getX()+3,b.getY()+3,0);screen.mouseReleased(b.getX()+3,b.getY()+3,0);UNR29Review.inputs.add(command);break;}
        }
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!UNR29Review.ENABLED||!started)return;
        var mc=Minecraft.getInstance();
        if(event.phase==TickEvent.Phase.START&&mc.player!=null&&UNR29Review.lookTarget!=null)
        {
            var d=UNR29Review.lookTarget.subtract(mc.player.getEyePosition());float yaw=(float)Math.toDegrees(Math.atan2(-d.x,d.z)),pitch=(float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance()));mc.player.setYRot(yaw);mc.player.yRotO=yaw;mc.player.setXRot(pitch);mc.player.xRotO=pitch;
        }
        if(event.phase!=TickEvent.Phase.END)return;
        String name=UNR29Review.photo;if(name.isEmpty()||UNR29Review.photos.contains(name))return;
        try(var frame=net.minecraft.client.Screenshot.takeScreenshot(Minecraft.getInstance().getMainRenderTarget())){frame.writeToFile(folder.resolve(name+".png"));UNR29Review.photos.add(name);}catch(Exception e){throw new IllegalStateException(e);}
    }
    private UNR29Client() {}
}
