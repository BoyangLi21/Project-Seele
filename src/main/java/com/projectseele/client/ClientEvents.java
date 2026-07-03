package com.projectseele.client;

import com.projectseele.ProjectSeele;
import com.projectseele.client.render.RamielRenderer;
import com.projectseele.registry.ModEntities;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public class ClientEvents
{
    @SubscribeEvent
    public static void onRegisterRenderers(EntityRenderersEvent.RegisterRenderers event)
    {
        event.registerEntityRenderer(ModEntities.RAMIEL.get(), RamielRenderer::new);
    }
}
