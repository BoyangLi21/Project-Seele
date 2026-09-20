package com.projectseele.client.visual;

import com.projectseele.visual.DialogueR28Review;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ClientChatReceivedEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class DialogueR28Client
{
    private static int ticks,end;private static boolean started,oldPause;
    @SubscribeEvent public static void chat(ClientChatReceivedEvent event)
    {
        if(!DialogueR28Review.ENABLED)return;
        String text=event.getMessage().getString();DialogueR28Review.received.add(text);
        if(text.contains(" · 通信」"))DialogueR28Review.radioTicks.add(Minecraft.getInstance().getSingleplayerServer().getTickCount());
    }
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!DialogueR28Review.ENABLED||event.phase!=TickEvent.Phase.END)return;
        var mc=Minecraft.getInstance();if(mc.player==null)return;ticks++;
        if(!started){started=true;oldPause=mc.options.pauseOnLostFocus;mc.options.pauseOnLostFocus=false;DialogueR28Review.ready=true;}
        if(DialogueR28Review.finished&&++end>30){mc.options.pauseOnLostFocus=oldPause;mc.stop();}
    }
    private DialogueR28Client() {}
}
