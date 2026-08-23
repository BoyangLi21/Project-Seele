package com.projectseele.client.render;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.UltramanAvatarEntity;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.model.GeoModel;

/** Local-only FBX-derived Ultraman skeleton resources. */
public final class UltramanAvatarGeoModel extends GeoModel<UltramanAvatarEntity>
{
    private static final ResourceLocation GEO = new ResourceLocation(
            ProjectSeele.MODID, "geo/ultraman_avatar.geo.json");
    private static final ResourceLocation TEXTURE = new ResourceLocation(
            ProjectSeele.MODID, "textures/entity/ultraman_avatar.png");
    private static final ResourceLocation ANIMATION = new ResourceLocation(
            ProjectSeele.MODID, "animations/ultraman_avatar.animation.json");

    @Override
    public ResourceLocation getModelResource(UltramanAvatarEntity entity)
    {
        return GEO;
    }

    @Override
    public ResourceLocation getTextureResource(UltramanAvatarEntity entity)
    {
        return TEXTURE;
    }

    @Override
    public ResourceLocation getAnimationResource(UltramanAvatarEntity entity)
    {
        return ANIMATION;
    }
}
