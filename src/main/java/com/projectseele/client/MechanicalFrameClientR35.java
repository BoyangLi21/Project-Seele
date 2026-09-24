package com.projectseele.client;

import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.util.ArrayList;

/** Keep a tracked rail assembly out of the unloaded-origin ticking deadlock. */
@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class MechanicalFrameClientR35
{
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.level==null||mc.isPaused())return;
        var moving=new ArrayList<EvaUnit01Entity>();
        for(var entity:mc.level.entitiesForRendering())if(entity instanceof EvaUnit01Entity eva&&!eva.isRemoved()&&eva.hasActiveCarrierMotion())moving.add(eva);
        for(var eva:moving)eva.syncClientCarrierFrameR35();
    }
    private MechanicalFrameClientR35(){}
}
