package com.projectseele.client.render;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.GeoModel;

/** Resource wiring for the Unit-01 GeckoLib model. */
public class EvaUnit01GeoModel extends GeoModel<EvaUnit01Entity>
{
    private static final ResourceLocation MODEL =
            new ResourceLocation(ProjectSeele.MODID, "geo/eva_unit01.geo.json");
    private static final ResourceLocation TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva_unit01.png");
    private static final ResourceLocation ANIMATIONS =
            new ResourceLocation(ProjectSeele.MODID, "animations/eva_unit01.animation.json");

    @Override
    public ResourceLocation getModelResource(EvaUnit01Entity animatable)
    {
        return MODEL;
    }

    @Override
    public ResourceLocation getTextureResource(EvaUnit01Entity animatable)
    {
        return TEXTURE;
    }

    @Override
    public ResourceLocation getAnimationResource(EvaUnit01Entity animatable)
    {
        return ANIMATIONS;
    }
}
