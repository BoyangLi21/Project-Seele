package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import com.projectseele.entity.NervSlidingDoorEntity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.culling.Frustum;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.client.renderer.texture.TextureAtlas;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/** Two silver leaves that retract completely into the authored wall pockets. */
public final class NervSlidingDoorRenderer
        extends EntityRenderer<NervSlidingDoorEntity>
{
    private static final BlockState SILVER =
            Blocks.IRON_BLOCK.defaultBlockState();

    public NervSlidingDoorRenderer(EntityRendererProvider.Context context)
    {
        super(context);
        this.shadowRadius = 0.0F;
    }

    @Override
    public boolean shouldRender(NervSlidingDoorEntity entity,
            Frustum frustum, double cameraX, double cameraY, double cameraZ)
    {
        return true;
    }

    @Override
    public void render(NervSlidingDoorEntity door, float yaw,
            float partialTick, PoseStack poses, MultiBufferSource buffers,
            int packedLight)
    {
        double slide = door.getOpenProgress(partialTick) * 1.5D;
        poses.pushPose();
        if (!door.isAxisX())
        {
            poses.mulPose(Axis.YP.rotationDegrees(90.0F));
        }
        panel(poses, buffers, packedLight,
                -1.5D - slide, 0.0D, -0.09375D,
                1.48F, 2.0F, 0.1875F);
        panel(poses, buffers, packedLight,
                0.02D + slide, 0.0D, -0.09375D,
                1.48F, 2.0F, 0.1875F);
        poses.popPose();
        super.render(door, yaw, partialTick, poses, buffers, packedLight);
    }

    private static void panel(PoseStack poses, MultiBufferSource buffers,
            int light, double x, double y, double z,
            float sx, float sy, float sz)
    {
        poses.pushPose();
        poses.translate(x, y, z);
        poses.scale(sx, sy, sz);
        Minecraft.getInstance().getBlockRenderer().renderSingleBlock(
                SILVER, poses, buffers, light,
                OverlayTexture.NO_OVERLAY);
        poses.popPose();
    }

    @Override
    public ResourceLocation getTextureLocation(NervSlidingDoorEntity entity)
    {
        return TextureAtlas.LOCATION_BLOCKS;
    }
}
