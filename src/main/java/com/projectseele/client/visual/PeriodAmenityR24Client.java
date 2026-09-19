package com.projectseele.client.visual;

import com.projectseele.client.screen.StaffConversationScreen;
import com.projectseele.visual.PeriodAmenityR24Review;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class PeriodAmenityR24Client
{
    private static boolean started,oldPause,oldGui;private static int oldDistance,end,settled;private static String pending="";private static Path folder;
    @SubscribeEvent public static void chat(net.minecraftforge.client.event.ClientChatReceivedEvent event)
    {if(PeriodAmenityR24Review.ENABLED&&event.getMessage().getString().contains("线路处于紧急管制"))PeriodAmenityR24Review.phoneReply=true;}
    @SubscribeEvent public static void sound(net.minecraftforge.client.event.sound.PlaySoundEvent event)
    {if(PeriodAmenityR24Review.ENABLED&&event.getSound()!=null&&event.getSound().getLocation().getPath().equals("period_phone_busy"))PeriodAmenityR24Review.phoneSound=true;}
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!PeriodAmenityR24Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        if(!started)
        {
            started=true;oldPause=mc.options.pauseOnLostFocus;oldGui=mc.options.hideGui;oldDistance=mc.options.renderDistance().get();mc.options.pauseOnLostFocus=false;mc.options.hideGui=false;mc.options.renderDistance().set(6);mc.options.broadcastOptions();
            folder=mc.gameDirectory.toPath().resolve("../artifacts/facility_r24/native_amenities_"+System.currentTimeMillis()).normalize();try{Files.createDirectories(folder);}catch(Exception e){throw new IllegalStateException(e);}PeriodAmenityR24Review.ready=true;
        }
        if(PeriodAmenityR24Review.finished)
        {
            if(++end>35){mc.setScreen(null);mc.options.pauseOnLostFocus=oldPause;mc.options.hideGui=oldGui;mc.options.renderDistance().set(oldDistance);mc.options.broadcastOptions();mc.stop();}return;
        }
        String input=PeriodAmenityR24Review.input;if(input.isEmpty()||PeriodAmenityR24Review.inputs.contains(input))return;
        if(input.equals("phone")||input.equals("sit"))
        {
            mc.gameMode.useItemOn(mc.player,net.minecraft.world.InteractionHand.MAIN_HAND,PeriodAmenityR24Review.hit);PeriodAmenityR24Review.inputs.add(input);return;
        }
        if(!(mc.screen instanceof StaffConversationScreen screen))return;
        if(input.equals("close")){screen.onClose();PeriodAmenityR24Review.inputs.add(input);return;}
        String title=input.equals("directions")?"道路指引":"机库";
        for(var child:List.copyOf(screen.children()))if(child instanceof Button b&&b.getMessage().getString().equals(title))
        {screen.mouseClicked(b.getX()+3,b.getY()+3,0);screen.mouseReleased(b.getX()+3,b.getY()+3,0);PeriodAmenityR24Review.inputs.add(input);return;}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!PeriodAmenityR24Review.ENABLED||!started||event.phase!=TickEvent.Phase.END)return;
        String name=PeriodAmenityR24Review.photo;if(name.isEmpty()||PeriodAmenityR24Review.photos.contains(name))return;
        settled=name.equals(pending)?settled+1:0;pending=name;if(settled<45)return;var mc=Minecraft.getInstance();
        try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){image.writeToFile(folder.resolve(name+".png"));PeriodAmenityR24Review.photos.add(name);}catch(Exception e){throw new IllegalStateException(e);}
    }
    private PeriodAmenityR24Client(){}
}
