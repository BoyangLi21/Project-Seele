package com.projectseele.client;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.math.Axis;
import com.projectseele.ProjectSeele;
import com.projectseele.world.FacilitySchemaV2;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Matrix3f;
import org.joml.Matrix4f;

/**
 * Framed plate on the command-room wall at z=257.
 *
 * <p>The image is read from the game directory rather than the mod jar, so the
 * plate can be replaced without a rebuild and no third-party artwork is
 * committed to this repository.  Drop the file at
 * {@code projectseele-local-maps/tree_of_life.png}; if it is absent nothing is
 * drawn and the wall stays as authored.</p>
 */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID,
        bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class TreeOfLifeWallClient
{
    private static final Path SOURCE = Paths.get(
            "projectseele-local-maps", "tree_of_life.png");
    private static final ResourceLocation TEXTURE_ID = new ResourceLocation(
            ProjectSeele.MODID, "dynamic/tree_of_life_wall");

    /*
     * The authored face is x16..25 by y-419..-410 on the z=257 plane, so the
     * plate is centred on it and sized 3:4 to match the engraving rather than
     * stretched to the square wall.  z sits just proud of the blocks so it
     * never z-fights with them.
     */
    private static final Vec3 CENTRE = new Vec3(20.5D, -414.5D, 257.98D);
    private static final float WIDTH = 7.5F;
    private static final float HEIGHT = 10.0F;
    private static final float YAW = 0.0F;
    private static final double RANGE_SQR = 96.0D * 96.0D;

    private static DynamicTexture texture;
    private static boolean sourceChecked;

    private TreeOfLifeWallClient() {}

    @SubscribeEvent
    public static void onRenderLevel(RenderLevelStageEvent event)
    {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_TRANSLUCENT_BLOCKS)
        {
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null || minecraft.player == null
                || !minecraft.level.dimension().equals(
                        FacilitySchemaV2.DIMENSION))
        {
            return;
        }
        if (minecraft.player.position().distanceToSqr(CENTRE) > RANGE_SQR)
        {
            return;
        }
        if (!ensureTexture(minecraft))
        {
            return;
        }

        Vec3 camera = event.getCamera().getPosition();
        PoseStack poseStack = event.getPoseStack();
        poseStack.pushPose();
        poseStack.translate(CENTRE.x - camera.x, CENTRE.y - camera.y,
                CENTRE.z - camera.z);
        poseStack.mulPose(Axis.YP.rotationDegrees(YAW));
        MultiBufferSource.BufferSource buffers =
                minecraft.renderBuffers().bufferSource();
        RenderType renderType = RenderType.entityTranslucent(TEXTURE_ID);
        VertexConsumer consumer = buffers.getBuffer(renderType);
        Matrix4f pose = poseStack.last().pose();
        Matrix3f normal = poseStack.last().normal();
        float halfWidth = WIDTH * 0.5F;
        float halfHeight = HEIGHT * 0.5F;
        // Wound so the printed side faces +Z, which is the room.
        vertex(consumer, pose, normal, halfWidth, -halfHeight, 0.0F, 0.0F, 1.0F);
        vertex(consumer, pose, normal, -halfWidth, -halfHeight, 0.0F, 1.0F, 1.0F);
        vertex(consumer, pose, normal, -halfWidth, halfHeight, 0.0F, 1.0F, 0.0F);
        vertex(consumer, pose, normal, halfWidth, halfHeight, 0.0F, 0.0F, 0.0F);
        buffers.endBatch(renderType);
        poseStack.popPose();
    }

    private static boolean ensureTexture(Minecraft minecraft)
    {
        if (texture != null)
        {
            return true;
        }
        if (sourceChecked)
        {
            return false;
        }
        sourceChecked = true;
        if (!Files.isRegularFile(SOURCE))
        {
            ProjectSeele.LOGGER.info(
                    "Tree-of-life wall idle: no image at {}", SOURCE);
            return false;
        }
        try (InputStream stream = Files.newInputStream(SOURCE))
        {
            NativeImage image = NativeImage.read(stream);
            texture = new DynamicTexture(image);
            minecraft.getTextureManager().register(TEXTURE_ID, texture);
            ProjectSeele.LOGGER.info(
                    "Tree-of-life wall loaded {}x{} from {}",
                    image.getWidth(), image.getHeight(), SOURCE);
            return true;
        }
        catch (IOException | RuntimeException exception)
        {
            ProjectSeele.LOGGER.error(
                    "Tree-of-life wall image unreadable", exception);
            return false;
        }
    }

    /** Forces a re-read after the file on disk has been replaced. */
    public static void reload()
    {
        if (texture != null)
        {
            Minecraft.getInstance().getTextureManager().release(TEXTURE_ID);
            texture.close();
            texture = null;
        }
        sourceChecked = false;
    }

    private static void vertex(VertexConsumer consumer, Matrix4f pose,
                               Matrix3f normal, float x, float y, float z,
                               float u, float v)
    {
        consumer.vertex(pose, x, y, z)
                .color(255, 255, 255, 255)
                .uv(u, v)
                .overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(LightTexture.FULL_BRIGHT)
                .normal(normal, 0.0F, 0.0F, 1.0F)
                .endVertex();
    }
}
