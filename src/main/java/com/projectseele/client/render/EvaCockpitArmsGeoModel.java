package com.projectseele.client.render;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.GeoModel;

/** A camera-space rig; it deliberately has no torso or shoulder bones. */
public class EvaCockpitArmsGeoModel extends GeoModel<EvaUnit01Entity>
{
    private static final ResourceLocation MODEL =
            new ResourceLocation(ProjectSeele.MODID, "geo/eva_cockpit_arms.geo.json");
    private static final ResourceLocation ANIMATIONS =
            new ResourceLocation(ProjectSeele.MODID, "animations/eva_cockpit_arms.animation.json");
    private static final ResourceLocation TEXTURE_01 =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva_unit01.png");
    private static final ResourceLocation TEXTURE_00 =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva_unit00.png");
    private static final ResourceLocation TEXTURE_02 =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva_unit02.png");

    @Override
    public ResourceLocation getModelResource(EvaUnit01Entity animatable)
    {
        return MODEL;
    }

    @Override
    public ResourceLocation getTextureResource(EvaUnit01Entity animatable)
    {
        return switch (animatable.getUnitVariant())
        {
            case EvaUnit01Entity.UNIT_00 -> TEXTURE_00;
            case EvaUnit01Entity.UNIT_02 -> TEXTURE_02;
            default -> TEXTURE_01;
        };
    }

    @Override
    public ResourceLocation getAnimationResource(EvaUnit01Entity animatable)
    {
        return ANIMATIONS;
    }
}
