package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.projectseele.ProjectSeele;
import com.projectseele.client.TreeOfLifeWallClient;
import com.projectseele.entity.NervArmamentStationEntity;
import com.projectseele.entity.EvaScale;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.client.renderer.texture.TextureAtlas;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import com.mojang.math.Axis;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.RenderType;
import org.joml.Matrix3f;
import org.joml.Matrix4f;

/** Smooth TV-style vertical Pallet Rifle armament building. */
public final class NervArmamentStationRenderer
        extends EntityRenderer<NervArmamentStationEntity>
{
    private static final double POD_TRAVEL = 43.0D;
    private static final float POD_HEIGHT = 42.0F;
    private static final ResourceLocation RIFLE_MESH = new ResourceLocation(
            ProjectSeele.MODID, "mesh/eva_pallet_smg.mesh.json");
    private static final ResourceLocation RIFLE_TEXTURE = new ResourceLocation(
            ProjectSeele.MODID, "textures/entity/eva_pallet_smg.png");
    private static final BlockState FRAME =
            Blocks.POLISHED_DEEPSLATE.defaultBlockState();
    private static final BlockState ARMOUR =
            Blocks.DEEPSLATE_TILES.defaultBlockState();
    private static final BlockState RAIL =
            Blocks.POLISHED_BLACKSTONE.defaultBlockState();
    private static final BlockState CRADLE =
            Blocks.IRON_BLOCK.defaultBlockState();
    private static final BlockState WARNING = Blocks.REDSTONE_LAMP
            .defaultBlockState().setValue(BlockStateProperties.LIT, true);

    public NervArmamentStationRenderer(EntityRendererProvider.Context context)
    {
        super(context);
        this.shadowRadius = 0.0F;
    }

    @Override
    public void render(NervArmamentStationEntity station, float yaw,
            float partialTick, PoseStack poses, MultiBufferSource buffers,
            int packedLight)
    {
        poses.pushPose();
        renderSurfaceFrame(poses, buffers, packedLight);
        renderHatch(poses, buffers, packedLight,
                station.getHatchProgress(partialTick));

        float lift = station.getLiftProgress(partialTick);
        if (lift > 0.001F || station.getStationState()
                != NervArmamentStationEntity.STOWED)
        {
            renderMovingRack(poses, buffers, packedLight, lift,
                    station.getDoorProgress(partialTick),
                    station.isStocked());
        }
        poses.popPose();
        super.render(station, yaw, partialTick, poses, buffers, packedLight);
    }

    private static void renderSurfaceFrame(PoseStack poses,
            MultiBufferSource buffers, int light)
    {
        for (int x = -5; x <= 5; x++)
        {
            for (int z = -5; z <= 5; z++)
            {
                if (Math.abs(x) == 5 || Math.abs(z) == 5)
                {
                    renderBlock(poses, buffers, light, FRAME, x, 0.0D, z);
                }
            }
        }
        renderBlock(poses, buffers, light, WARNING, -5, 1.0D, -5);
        renderBlock(poses, buffers, light, WARNING, 5, 1.0D, -5);
        renderBlock(poses, buffers, light, WARNING, -5, 1.0D, 5);
        renderBlock(poses, buffers, light, WARNING, 5, 1.0D, 5);
    }

    private static void renderHatch(PoseStack poses,
            MultiBufferSource buffers, int light, float progress)
    {
        double slide = progress * 5.25D;
        for (int x = -4; x <= 4; x++)
        {
            for (int z = -4; z <= 4; z++)
            {
                double shiftedX = x < 0 ? x - slide : x + slide;
                renderBlock(poses, buffers, light, ARMOUR,
                        shiftedX, 0.05D, z);
            }
        }
    }

    private static void renderMovingRack(PoseStack poses,
            MultiBufferSource buffers, int light, float progress,
            float doorProgress, boolean stocked)
    {
        double baseY = -POD_TRAVEL + progress * POD_TRAVEL;
        for (int x = -4; x <= 4; x++)
        {
            for (int z = -4; z <= 4; z++)
            {
                renderBlock(poses, buffers, light, ARMOUR,
                        x, baseY, z);
            }
        }

        // A complete sealed armour pod rises first. Large panels are scaled
        // block models rather than hundreds of individual world blocks, so
        // the motion remains cheap and visually continuous.
        renderPanel(poses, buffers, light, ARMOUR,
                -4.5D, baseY + 1.0D, -4.5D, 1.0F, POD_HEIGHT, 9.0F);
        renderPanel(poses, buffers, light, ARMOUR,
                3.5D, baseY + 1.0D, -4.5D, 1.0F, POD_HEIGHT, 9.0F);
        renderPanel(poses, buffers, light, ARMOUR,
                -3.5D, baseY + 1.0D, 3.5D, 7.0F, POD_HEIGHT, 1.0F);
        renderPanel(poses, buffers, light, FRAME,
                -3.5D, baseY + POD_HEIGHT, -3.5D,
                7.0F, 1.0F, 7.0F);

        // Two front armour leaves stay shut throughout the rise and slide
        // sideways only after the pod has stopped at full height.
        double doorSlide = doorProgress * 3.75D;
        renderPanel(poses, buffers, light, ARMOUR,
                -3.5D - doorSlide, baseY + 1.0D, -4.5D,
                3.5F, POD_HEIGHT - 1.0F, 1.0F);
        renderSplitDoorLogo(poses, buffers, baseY, doorSlide);
        renderPanel(poses, buffers, light, ARMOUR,
                doorSlide, baseY + 1.0D, -4.5D,
                3.5F, POD_HEIGHT - 1.0F, 1.0F);

        // Internal lift rails and rifle cradle become visible through the
        // opening; they never form the exterior silhouette during travel.
        for (int y = 2; y <= 40; y++)
        {
            renderBlock(poses, buffers, light, RAIL,
                    -3, baseY + y, 3);
            renderBlock(poses, buffers, light, RAIL,
                    3, baseY + y, 3);
        }
        for (int y = 3; y <= 39; y += 5)
        {
            renderBlock(poses, buffers, light, CRADLE,
                    -3, baseY + y, 0);
            renderBlock(poses, buffers, light, CRADLE,
                    3, baseY + y, 0);
        }

        if (stocked)
        {
            poses.pushPose();
            poses.translate(0.5D, baseY + 1.0D, 0.5D);
            // The payload stays upright; only its front/back heading changes.
            poses.mulPose(Axis.YP.rotationDegrees(180.0F));
            // Use the exact same world scale as the rifle in an EVA's hands;
            // the former 3.6 scale made the station payload only 72% size.
            poses.scale(EvaScale.RENDER_SCALE, EvaScale.RENDER_SCALE,
                    EvaScale.RENDER_SCALE);
            LocalTriangleMeshLayer.renderStandalone(poses, buffers,
                    RIFLE_MESH, RIFLE_TEXTURE, light,
                    OverlayTexture.NO_OVERLAY);
            poses.popPose();
        }
    }

    private static void renderSplitDoorLogo(PoseStack poses,
            MultiBufferSource buffers, double baseY, double doorSlide)
    {
        ResourceLocation logo = TreeOfLifeWallClient.nervLogoTexture(
                Minecraft.getInstance());
        if (logo == null)
        {
            return;
        }
        VertexConsumer consumer = buffers.getBuffer(
                RenderType.entityTranslucent(logo));
        renderLogoHalf(poses, consumer,
                -3.5D - doorSlide, 0.0D - doorSlide,
                baseY + 15.0D, baseY + 31.0D,
                -4.515D, 1.0F, 0.5F);
        renderLogoHalf(poses, consumer,
                0.0D + doorSlide, 3.5D + doorSlide,
                baseY + 15.0D, baseY + 31.0D,
                -4.515D, 0.5F, 0.0F);
    }

    private static void renderLogoHalf(PoseStack poses,
            VertexConsumer consumer, double x0, double x1,
            double y0, double y1, double z, float u0, float u1)
    {
        Matrix4f matrix = poses.last().pose();
        Matrix3f normal = poses.last().normal();
        logoVertex(consumer, matrix, normal, x0, y0, z, u0, 1.0F);
        logoVertex(consumer, matrix, normal, x1, y0, z, u1, 1.0F);
        logoVertex(consumer, matrix, normal, x1, y1, z, u1, 0.0F);
        logoVertex(consumer, matrix, normal, x0, y1, z, u0, 0.0F);
    }

    private static void logoVertex(VertexConsumer consumer, Matrix4f pose,
            Matrix3f normal, double x, double y, double z, float u, float v)
    {
        consumer.vertex(pose, (float)x, (float)y, (float)z)
                .color(255, 255, 255, 255).uv(u, v)
                .overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(0x00F000F0).normal(normal, 0.0F, 0.0F, -1.0F)
                .endVertex();
    }

    private static void renderBlock(PoseStack poses,
            MultiBufferSource buffers, int light, BlockState state,
            double x, double y, double z)
    {
        poses.pushPose();
        poses.translate(x - 0.5D, y, z - 0.5D);
        Minecraft.getInstance().getBlockRenderer().renderSingleBlock(
                state, poses, buffers, light, OverlayTexture.NO_OVERLAY);
        poses.popPose();
    }

    private static void renderPanel(PoseStack poses,
            MultiBufferSource buffers, int light, BlockState state,
            double x, double y, double z, float sizeX, float sizeY,
            float sizeZ)
    {
        poses.pushPose();
        poses.translate(x, y, z);
        poses.scale(sizeX, sizeY, sizeZ);
        Minecraft.getInstance().getBlockRenderer().renderSingleBlock(
                state, poses, buffers, light, OverlayTexture.NO_OVERLAY);
        poses.popPose();
    }

    @Override
    public ResourceLocation getTextureLocation(
            NervArmamentStationEntity entity)
    {
        return TextureAtlas.LOCATION_BLOCKS;
    }
}
