package com.projectseele.client.visual;
import com.projectseele.visual.UNR29ResumeReview;
import com.projectseele.client.Keybinds;
import net.minecraft.client.Minecraft;
import net.minecraft.client.KeyMapping;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class UNR29ResumeClient
{
    private static boolean started,oldPause;private static int end,oldDistance;private static Path folder;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!UNR29ResumeReview.ENABLED)return;var mc=Minecraft.getInstance();if(mc.player==null)return;
        if(event.phase==TickEvent.Phase.START){mc.options.keyJump.setDown(UNR29ResumeReview.keys.equals("up"));mc.options.keyUp.setDown(UNR29ResumeReview.keys.equals("forward"));mc.options.keySprint.setDown(UNR29ResumeReview.keys.equals("forward"));return;}
        if(!started){started=true;oldPause=mc.options.pauseOnLostFocus;mc.options.pauseOnLostFocus=false;oldDistance=mc.options.renderDistance().get();mc.options.renderDistance().set(16);mc.options.broadcastOptions();folder=mc.gameDirectory.toPath().resolve("../artifacts/facility_r29/native_un_resume_"+System.currentTimeMillis()).normalize();try{Files.createDirectories(folder);}catch(Exception e){throw new IllegalStateException(e);}UNR29ResumeReview.ready=true;}
        if(UNR29ResumeReview.finished&&++end>3){mc.options.keyJump.setDown(false);mc.options.keyUp.setDown(false);mc.options.keySprint.setDown(false);mc.options.pauseOnLostFocus=oldPause;mc.options.renderDistance().set(oldDistance);mc.options.broadcastOptions();mc.stop();return;}
        String input=UNR29ResumeReview.input;if(!input.isEmpty()&&UNR29ResumeReview.inputs.add(input))KeyMapping.click(Keybinds.UN_FLIGHT.getKey());
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!UNR29ResumeReview.ENABLED||!started||event.phase!=TickEvent.Phase.END)return;String name=UNR29ResumeReview.photo;if(name.isEmpty()||UNR29ResumeReview.photos.contains(name))return;
        try(var image=net.minecraft.client.Screenshot.takeScreenshot(Minecraft.getInstance().getMainRenderTarget())){image.writeToFile(folder.resolve(name+".png"));UNR29ResumeReview.photos.add(name);}catch(Exception e){throw new IllegalStateException(e);}
    }
    private UNR29ResumeClient() {}
}
