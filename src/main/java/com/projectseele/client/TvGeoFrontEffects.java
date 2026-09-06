package com.projectseele.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.projectseele.ProjectSeele;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.DimensionSpecialEffects;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.material.FogType;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterDimensionSpecialEffectsEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Matrix4f;

/** Selected by the preview save's dimension-type datapack, including multiplayer clients. */
public final class TvGeoFrontEffects extends DimensionSpecialEffects
{
    private static final OverworldEffects SURFACE = new OverworldEffects();

    public TvGeoFrontEffects()
    {
        super(256, true, SkyType.NORMAL, false, false);
    }

    @Override
    public Vec3 getBrightnessDependentFogColor(Vec3 colour, float brightness)
    {
        return SURFACE.getBrightnessDependentFogColor(colour, brightness);
    }

    @Override
    public boolean isFoggyAt(int x, int z)
    {
        return false;
    }

    @Override
    public boolean renderSky(ClientLevel level, int ticks, float partialTick,
                             PoseStack poseStack, Camera camera, Matrix4f projection,
                             boolean foggy, Runnable setupFog)
    {
        // Distant unloaded sections should fade into cavern haze, never a
        // blue daytime sky below hundreds of metres of rock and armour.
        return camera.getPosition().y < -128;
    }

    @Mod.EventBusSubscriber(modid = ProjectSeele.MODID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.MOD)
    public static final class Registration
    {
        @SubscribeEvent
        public static void register(RegisterDimensionSpecialEffectsEvent event)
        {
            event.register(new ResourceLocation(ProjectSeele.MODID, "tv_geofront"), new TvGeoFrontEffects());
        }
    }

    @Mod.EventBusSubscriber(modid = ProjectSeele.MODID, value = Dist.CLIENT)
    public static final class Atmosphere
    {
        @SubscribeEvent
        public static void ceilingVisibility(ViewportEvent.RenderFog event)
        {
            ClientLevel level = Minecraft.getInstance().level;
            if (level == null || !(level.effects() instanceof TvGeoFrontEffects)
                    || event.getCamera().getPosition().y >= -128
                    || event.getCamera().getXRot() >= -35
                    || event.getType() != FogType.NONE) return;
            // Keep the real ceiling visible vertically without demanding a
            // forty-chunk horizontal view distance from the player's machine.
            event.setNearPlaneDistance(Math.max(event.getNearPlaneDistance(), 320));
            event.setFarPlaneDistance(Math.max(event.getFarPlaneDistance(), 640));
            event.setCanceled(true);
        }

        @SubscribeEvent
        public static void colour(ViewportEvent.ComputeFogColor event)
        {
            ClientLevel level = Minecraft.getInstance().level;
            if (level == null || !(level.effects() instanceof TvGeoFrontEffects)
                    || event.getCamera().getPosition().y >= -128
                    || event.getCamera().getFluidInCamera() != FogType.NONE) return;
            event.setRed(0.34F);
            event.setGreen(0.42F);
            event.setBlue(0.43F);
        }
    }
}
