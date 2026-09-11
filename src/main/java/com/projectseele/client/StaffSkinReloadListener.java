package com.projectseele.client;

import com.projectseele.ProjectSeele;
import com.projectseele.client.render.NervStaffSkins;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterClientReloadListenersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT,bus=Mod.EventBusSubscriber.Bus.MOD)
public final class StaffSkinReloadListener
{
    @SubscribeEvent public static void register(RegisterClientReloadListenersEvent event)
    {
        event.registerReloadListener((net.minecraft.server.packs.resources.ResourceManagerReloadListener)manager->{
            NervStaffSkins.reset();
            com.projectseele.client.render.TvFacilityMeshes.clearCache();
        });
    }
    private StaffSkinReloadListener() {}
}
