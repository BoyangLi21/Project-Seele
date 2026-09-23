package com.projectseele.client.visual;

import com.projectseele.visual.SortieR32Review;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class SortieR32Client
{
    private static int finish;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent e)
    {
        if(!SortieR32Review.ENABLED||e.phase!=TickEvent.Phase.END)return;
        var mc=Minecraft.getInstance();if(mc.level==null||mc.player==null)return;
        mc.options.pauseOnLostFocus=false;SortieR32Review.ready=true;
        if(SortieR32Review.finished&&++finish>40)mc.stop();
    }
    private SortieR32Client(){}
}
