package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.UltramanAvatarEntity;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.culling.Frustum;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

/** Renders the user-supplied FBX mesh, never the vanilla player body. */
public final class UltramanAvatarRenderer
        extends GeoEntityRenderer<UltramanAvatarEntity>
{
    private static final ResourceLocation MESH = new ResourceLocation(
            ProjectSeele.MODID, "mesh/ultraman_avatar.mesh.json");
    private static final ResourceLocation TEXTURE = new ResourceLocation(
            ProjectSeele.MODID, "textures/entity/ultraman_avatar.png");

    public UltramanAvatarRenderer(EntityRendererProvider.Context context)
    {
        super(context, new UltramanAvatarGeoModel());
        this.addRenderLayer(new LocalTriangleMeshLayer<>(this,
                entity -> MESH, entity -> TEXTURE));
        this.shadowRadius = 0.0F;
    }

    @Override
    public boolean shouldRender(UltramanAvatarEntity entity,
            Frustum frustum, double cameraX, double cameraY, double cameraZ)
    {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.options.getCameraType().isFirstPerson()
                && minecraft.player != null
                && entity.getOwnerId() == minecraft.player.getId())
        {
            // The local first-person camera occupies the real head socket;
            // never render the owner's enclosing head shell into that view.
            return false;
        }
        return true;
    }

    @Override
    public void preRender(PoseStack poses, UltramanAvatarEntity entity,
            BakedGeoModel model, @Nullable MultiBufferSource buffers,
            @Nullable VertexConsumer buffer, boolean isReRender,
            float partialTick, int packedLight, int packedOverlay,
            float red, float green, float blue, float alpha)
    {
        super.preRender(poses, entity, model, buffers, buffer, isReRender,
                partialTick, packedLight, packedOverlay,
                red, green, blue, alpha);
        // Exported model height is exactly two blocks; 0.9 maps scale 1 to a
        // normal player's 1.8 blocks and scale 32 to 57.6 blocks.
        float scale = entity.getVisualScale(partialTick) * 0.9F;
        poses.scale(scale, scale, scale);
    }
}
