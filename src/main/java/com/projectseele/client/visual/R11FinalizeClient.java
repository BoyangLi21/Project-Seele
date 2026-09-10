package com.projectseele.client.visual;
import com.projectseele.ProjectSeele;
import com.projectseele.visual.R11MainFinalize;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class R11FinalizeClient
{
    private static boolean saved,pause;private static int end;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!R11MainFinalize.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();
        if(!saved){pause=mc.options.pauseOnLostFocus;mc.options.pauseOnLostFocus=false;saved=true;}
        if(R11MainFinalize.finished&&++end>35){mc.options.pauseOnLostFocus=pause;mc.stop();}
    }
}
