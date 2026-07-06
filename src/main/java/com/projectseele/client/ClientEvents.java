package com.projectseele.client;

import com.projectseele.ProjectSeele;
import com.projectseele.client.render.EvaUnit01Renderer;
import com.projectseele.client.render.RamielRenderer;
import com.projectseele.registry.ModEntities;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.client.event.RegisterGuiOverlaysEvent;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public class ClientEvents
{
    @SubscribeEvent
    public static void onRegisterRenderers(EntityRenderersEvent.RegisterRenderers event)
    {
        event.registerEntityRenderer(ModEntities.RAMIEL.get(), RamielRenderer::new);
        event.registerEntityRenderer(ModEntities.EVA_UNIT01.get(), EvaUnit01Renderer::new);
    }

    @SubscribeEvent
    public static void onRegisterGuiOverlays(RegisterGuiOverlaysEvent event)
    {
        event.registerAboveAll("angel_alarm", AlarmOverlay.INSTANCE);
        event.registerAboveAll("eva_cockpit", EvaHud.COCKPIT);
        event.registerAboveAll("sniper_scope", EvaHud.SCOPE);
        event.registerAboveAll("plug_insertion", EvaHud.INSERTION);
    }

    @SubscribeEvent
    public static void onRegisterKeyMappings(RegisterKeyMappingsEvent event)
    {
        event.register(Keybinds.CYCLE_WEAPON);
        event.register(Keybinds.TOGGLE_AT_FIELD);
    }
}
