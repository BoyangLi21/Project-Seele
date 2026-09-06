package com.projectseele.client.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.visual.TvWorldPreviewPreparation;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Client shutdown bridge; preparation also runs on a dedicated local server. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, value = Dist.CLIENT)
public final class TvWorldPreviewReview
{
    private static final String MODE = System.getProperty("projectseele.tvWorldPreviewReview", "");
    private TvWorldPreviewReview() {}

    @SubscribeEvent
    public static void tick(TickEvent.ClientTickEvent event)
    {
        if (MODE.isEmpty() || event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        mc.options.pauseOnLostFocus = false;
        if (!MODE.equals("review")) mc.options.renderDistance().set(6);
        if (TvWorldPreviewPreparation.isFinished()) mc.stop();
    }
}
