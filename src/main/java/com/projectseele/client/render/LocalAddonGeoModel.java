package com.projectseele.client.render;

import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.model.GeoModel;

/** Resource-pack-overridable model descriptor for local licensed/test assets. */
public class LocalAddonGeoModel<T extends GeoEntity> extends GeoModel<T>
{
    private final ResourceLocation geometry;
    private final ResourceLocation texture;
    private final ResourceLocation animation;

    public LocalAddonGeoModel(ResourceLocation geometry, ResourceLocation texture,
                              ResourceLocation animation)
    {
        this.geometry = geometry;
        this.texture = texture;
        this.animation = animation;
    }

    @Override
    public ResourceLocation getModelResource(T animatable)
    {
        return this.geometry;
    }

    @Override
    public ResourceLocation getTextureResource(T animatable)
    {
        return this.texture;
    }

    @Override
    public ResourceLocation getAnimationResource(T animatable)
    {
        return this.animation;
    }
}
