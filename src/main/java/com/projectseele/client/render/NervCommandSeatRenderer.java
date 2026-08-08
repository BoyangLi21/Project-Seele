package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.NervCommandSeatEntity;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;

/** The command chair is rendered by blocks; its riding anchor stays invisible. */
public final class NervCommandSeatRenderer
        extends EntityRenderer<NervCommandSeatEntity>
{
    private static final ResourceLocation TEXTURE = new ResourceLocation(
            ProjectSeele.MODID, "textures/entity/ramiel.png");

    public NervCommandSeatRenderer(EntityRendererProvider.Context context)
    {
        super(context);
    }

    @Override
    public void render(NervCommandSeatEntity entity, float yaw,
                       float partialTick, PoseStack poseStack,
                       MultiBufferSource buffer, int packedLight)
    {
    }

    @Override
    public ResourceLocation getTextureLocation(NervCommandSeatEntity entity)
    {
        return TEXTURE;
    }
}
