package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.projectseele.ProjectSeele;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.LivingEntity;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

/** Uses a local high-detail Gecko model when installed, otherwise the original fallback renderer. */
public class HybridAddonRenderer<T extends LivingEntity & GeoEntity> extends EntityRenderer<T>
{
    private final ColossalHumanoidRenderer<T> fallback;
    private final GeoEntityRenderer<T> detailed;
    private final ResourceLocation geometry;
    private final ResourceLocation texture;
    private final ResourceLocation animation;

    public HybridAddonRenderer(EntityRendererProvider.Context context,
                               ColossalHumanoidRenderer.Style fallbackStyle,
                               String assetName, float scale)
    {
        super(context);
        this.geometry = new ResourceLocation(ProjectSeele.MODID, "geo/" + assetName + ".geo.json");
        this.texture = new ResourceLocation(ProjectSeele.MODID, "textures/entity/" + assetName + ".png");
        this.animation = new ResourceLocation(ProjectSeele.MODID, "animations/" + assetName + ".animation.json");
        this.fallback = new ColossalHumanoidRenderer<>(context, fallbackStyle);
        this.detailed = new GeoEntityRenderer<>(context,
                new LocalAddonGeoModel<>(this.geometry, this.texture, this.animation));
        this.detailed.withScale(scale);
        this.shadowRadius = fallbackStyle == ColossalHumanoidRenderer.Style.SACHIEL ? 3.8F : 4.5F;
    }

    private boolean hasDetailedResources()
    {
        var resources = Minecraft.getInstance().getResourceManager();
        return resources.getResource(this.geometry).isPresent()
                && resources.getResource(this.texture).isPresent()
                && resources.getResource(this.animation).isPresent();
    }

    @Override
    public void render(T entity, float yaw, float partialTick, PoseStack poseStack,
                       MultiBufferSource buffers, int packedLight)
    {
        if (hasDetailedResources())
        {
            this.detailed.render(entity, yaw, partialTick, poseStack, buffers, packedLight);
        }
        else
        {
            this.fallback.render(entity, yaw, partialTick, poseStack, buffers, packedLight);
        }
    }

    @Override
    public ResourceLocation getTextureLocation(T entity)
    {
        return hasDetailedResources() ? this.texture : this.fallback.getTextureLocation(entity);
    }
}
