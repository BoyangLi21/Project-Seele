package com.projectseele.client;

import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Keep the optional piano's fixed 420x270 panel within the current window. */
@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class PianoScreenCompatibilityR22
{
    private static int previous=-1;
    public static boolean piano(Object screen){return screen!=null&&screen.getClass().getName().equals("com.solvane.grandpiano.client.gui.PianoPlayScreen");}
    public static boolean playTab(Object screen)
    {
        if(!piano(screen))return false;
        try{var f=screen.getClass().getDeclaredField("activeTab");f.setAccessible(true);return String.valueOf(f.get(screen)).equals("PLAY");}
        catch(ReflectiveOperationException e){return false;}
    }
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent e)
    {
        if(e.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();
        if(piano(mc.screen)&&previous<0)
        {
            previous=mc.options.guiScale().get();int fit=Math.max(1,Math.min(mc.getWindow().getWidth()/444,mc.getWindow().getHeight()/294));
            if(mc.getWindow().getGuiScaledWidth()<444||mc.getWindow().getGuiScaledHeight()<294)
            {mc.options.guiScale().set(fit);mc.resizeDisplay();}
        }
        else if(!piano(mc.screen)&&previous>=0)
        {int restore=previous;previous=-1;mc.options.guiScale().set(restore);mc.resizeDisplay();}
    }
    private PianoScreenCompatibilityR22(){}
}
