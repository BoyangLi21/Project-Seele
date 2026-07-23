package com.projectseele.client.render;

import com.projectseele.entity.TrainingPilotEntity;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.client.model.geom.ModelLayers;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.client.resources.DefaultPlayerSkin;
import net.minecraft.resources.ResourceLocation;

/** Human-scale visual proxy for the automated NERV training pilot. */
public final class TrainingPilotRenderer
        extends MobRenderer<TrainingPilotEntity, PlayerModel<TrainingPilotEntity>>
{
    public TrainingPilotRenderer(EntityRendererProvider.Context context)
    {
        super(context, new PlayerModel<>(
                context.bakeLayer(ModelLayers.PLAYER), false), 0.5F);
    }

    @Override
    public ResourceLocation getTextureLocation(TrainingPilotEntity entity)
    {
        return DefaultPlayerSkin.getDefaultSkin(entity.getUUID());
    }
}
