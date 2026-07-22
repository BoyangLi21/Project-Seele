package com.projectseele.client;

import com.projectseele.ProjectSeele;
import com.projectseele.client.render.EvaUnit01Renderer;
import com.projectseele.client.render.LocalTriangleMeshLayer;
import com.projectseele.client.render.LocalVisualAssetFingerprint;
import com.projectseele.client.render.RamielRenderer;
import com.projectseele.client.render.LilithRenderer;
import com.projectseele.client.render.ColossalHumanoidRenderer;
import com.projectseele.client.render.HybridAddonRenderer;
import com.projectseele.registry.ModEntities;
import com.projectseele.registry.ModFluids;
import net.minecraft.client.renderer.ItemBlockRenderTypes;
import net.minecraft.client.renderer.RenderType;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.client.event.RegisterGuiOverlaysEvent;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.client.event.RegisterClientReloadListenersEvent;
import net.minecraft.server.packs.resources.ResourceManagerReloadListener;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;

@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public class ClientEvents
{
    @SubscribeEvent
    public static void onClientSetup(FMLClientSetupEvent event)
    {
        event.enqueueWork(() ->
        {
            ItemBlockRenderTypes.setRenderLayer(ModFluids.LCL_SOURCE.get(),
                    RenderType.translucent());
            ItemBlockRenderTypes.setRenderLayer(ModFluids.FLOWING_LCL.get(),
                    RenderType.translucent());
        });
    }

    @SubscribeEvent
    public static void onRegisterRenderers(EntityRenderersEvent.RegisterRenderers event)
    {
        event.registerEntityRenderer(ModEntities.RAMIEL.get(), RamielRenderer::new);
        event.registerEntityRenderer(ModEntities.EVA_UNIT01.get(), EvaUnit01Renderer::new);
        event.registerEntityRenderer(ModEntities.EVA_UNIT00.get(), EvaUnit01Renderer::new);
        event.registerEntityRenderer(ModEntities.EVA_UNIT02.get(), EvaUnit01Renderer::new);
        event.registerEntityRenderer(ModEntities.SACHIEL.get(), context -> new HybridAddonRenderer<>(context,
                ColossalHumanoidRenderer.Style.SACHIEL, "sachiel", 8.0F));
        event.registerEntityRenderer(ModEntities.SHAMSHEL.get(),
                context -> new ColossalHumanoidRenderer<>(context, ColossalHumanoidRenderer.Style.SHAMSHEL));
        event.registerEntityRenderer(ModEntities.ZERUEL.get(),
                context -> new ColossalHumanoidRenderer<>(context, ColossalHumanoidRenderer.Style.ZERUEL));
        event.registerEntityRenderer(ModEntities.ISRAFEL.get(), context -> new HybridAddonRenderer<>(context,
                ColossalHumanoidRenderer.Style.SACHIEL, "israfel", 9.0F));
        event.registerEntityRenderer(ModEntities.LILITH.get(), LilithRenderer::new);
        event.registerEntityRenderer(ModEntities.MASS_PRODUCTION_EVA.get(), context -> new HybridAddonRenderer<>(context,
                ColossalHumanoidRenderer.Style.MASS_PRODUCTION, "mass_production_eva", 6.5F));
    }

    @SubscribeEvent
    public static void onRegisterGuiOverlays(RegisterGuiOverlaysEvent event)
    {
        event.registerAboveAll("angel_alarm", AlarmOverlay.INSTANCE);
        event.registerAboveAll("eva_cockpit", EvaHud.COCKPIT);
        event.registerAboveAll("sniper_scope", EvaHud.SCOPE);
        event.registerAboveAll("plug_insertion", EvaHud.INSERTION);
        event.registerAboveAll("nuclear_flash", EvaHud.NUCLEAR_FLASH);
        event.registerAboveAll("eva_command_feed_capture", EvaCommandFeedClient.CAPTURE_OVERLAY);
    }

    @SubscribeEvent
    public static void onRegisterKeyMappings(RegisterKeyMappingsEvent event)
    {
        event.register(Keybinds.CYCLE_WEAPON);
        event.register(Keybinds.TOGGLE_AT_FIELD);
        event.register(Keybinds.EXIT_EVA);
        event.register(Keybinds.STOMP);
        event.register(Keybinds.TOGGLE_PRONE);
    }

    @SubscribeEvent
    public static void onRegisterReloadListeners(RegisterClientReloadListenersEvent event)
    {
        event.registerReloadListener((ResourceManagerReloadListener) resourceManager ->
        {
            LocalTriangleMeshLayer.clearCache();
            LocalVisualAssetFingerprint.clearCache();
        });
    }
}
