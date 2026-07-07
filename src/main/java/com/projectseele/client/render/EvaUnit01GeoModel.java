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
    private static final ResourceLocation MODEL_00 =
            new ResourceLocation(ProjectSeele.MODID, "geo/eva_unit00.geo.json");
    private static final ResourceLocation MODEL_02 =
            new ResourceLocation(ProjectSeele.MODID, "geo/eva_unit02.geo.json");
    private static final ResourceLocation TEXTURE_00 =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva_unit00.png");
    private static final ResourceLocation TEXTURE_02 =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva_unit02.png");
    private static final ResourceLocation ANIMATIONS_00 =
            new ResourceLocation(ProjectSeele.MODID, "animations/eva_unit00.animation.json");
    private static final ResourceLocation ANIMATIONS_02 =
            new ResourceLocation(ProjectSeele.MODID, "animations/eva_unit02.animation.json");

    @Override
    public ResourceLocation getModelResource(EvaUnit01Entity animatable)
    {
        return switch (animatable.getUnitVariant())
        {
            case EvaUnit01Entity.UNIT_00 -> MODEL_00;
            case EvaUnit01Entity.UNIT_02 -> MODEL_02;
            default -> MODEL;
        };
    }

    @Override
    public ResourceLocation getTextureResource(EvaUnit01Entity animatable)
    {
        return switch (animatable.getUnitVariant())
        {
            case EvaUnit01Entity.UNIT_00 -> TEXTURE_00;
            case EvaUnit01Entity.UNIT_02 -> TEXTURE_02;
            default -> TEXTURE;
        };
    }

    @Override
    public ResourceLocation getAnimationResource(EvaUnit01Entity animatable)
    {
        return switch (animatable.getUnitVariant())
        {
            case EvaUnit01Entity.UNIT_00 -> ANIMATIONS_00;
            case EvaUnit01Entity.UNIT_02 -> ANIMATIONS_02;
            default -> ANIMATIONS;
        };
    }
}
