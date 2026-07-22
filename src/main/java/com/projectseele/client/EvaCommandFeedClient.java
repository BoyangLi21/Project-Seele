package com.projectseele.client;

import java.io.IOException;
import java.util.concurrent.atomic.AtomicBoolean;

import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.client.visual.VisualCaptureManager;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.network.ServerboundEvaVideoFramePacket;
import com.projectseele.visual.GeoFrontCommands;
import com.projectseele.world.IntegratedNervMapBuilder;
import net.minecraft.world.level.block.Blocks;
import com.projectseele.world.NervOperationsCentreBuilder;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.Util;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.client.gui.overlay.IGuiOverlay;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Matrix3f;
import org.joml.Matrix4f;

/**
 * Captures the final cockpit view at low resolution and renders authenticated
 * remote frames on three physical 16:9 screens in NERV operations.
 */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE,
        value = Dist.CLIENT)
public final class EvaCommandFeedClient
{
    public static final IGuiOverlay CAPTURE_OVERLAY =
            (gui, graphics, partialTick, width, height) -> captureIfDue();

    private static final int CAPTURE_INTERVAL_TICKS = 5;
    private static final long FRAME_STALE_NANOS = 3_000_000_000L;
    private static final double DISPLAY_RANGE_SQR = 150.0D * 150.0D;
    private static final float SCREEN_WIDTH = 10.5F;
    private static final float SCREEN_HEIGHT =
            SCREEN_WIDTH * ServerboundEvaVideoFramePacket.FRAME_HEIGHT
                    / ServerboundEvaVideoFramePacket.FRAME_WIDTH;
    private static final int[] SCREEN_X = {-12, 0, 12};
    private static final AtomicBoolean CAPTURE_IN_FLIGHT =
            new AtomicBoolean();
    private static final DynamicTexture[] TEXTURES =
            new DynamicTexture[3];
    private static final long[] LAST_FRAME_NANOS = new long[3];
    private static final ResourceLocation[] TEXTURE_IDS = {
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/eva_command_feed_00"),
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/eva_command_feed_01"),
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/eva_command_feed_02")
    };
    private static final DynamicTexture[] STANDBY_TEXTURES =
            new DynamicTexture[3];
    private static final ResourceLocation[] STANDBY_TEXTURE_IDS = {
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/eva_command_standby_00"),
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/eva_command_standby_01"),
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/eva_command_standby_02")
    };
    private static final int[][] UNIT_COLOURS = {
            {232, 143, 38}, {144, 62, 205}, {210, 45, 52}
    };

    private static int lastCaptureTick = -CAPTURE_INTERVAL_TICKS;
    private static ClientLevel captureLevel;
    private static int captureEvaId = Integer.MIN_VALUE;
    private static ClientLevel activeLevel;

    private EvaCommandFeedClient() {}

    private static void captureIfDue()
    {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.player == null || minecraft.level == null
                || minecraft.screen != null
                || VisualCaptureManager.isSuppressingGui()
                || !(minecraft.player.getVehicle()
                        instanceof EvaUnit01Entity eva)
                || eva.getFirstPassenger() != minecraft.player
                || !eva.isAlive())
        {
            return;
        }
        if (captureLevel != minecraft.level || captureEvaId != eva.getId())
        {
            captureLevel = minecraft.level;
            captureEvaId = eva.getId();
            lastCaptureTick = minecraft.player.tickCount
                    - CAPTURE_INTERVAL_TICKS;
        }
        int tick = minecraft.player.tickCount;
        if (tick - lastCaptureTick < CAPTURE_INTERVAL_TICKS
                || !CAPTURE_IN_FLIGHT.compareAndSet(false, true))
        {
            return;
        }
        lastCaptureTick = tick;

        NativeImage full;
        try
        {
            full = Screenshot.takeScreenshot(
                    minecraft.getMainRenderTarget());
        }
        catch (RuntimeException exception)
        {
            CAPTURE_IN_FLIGHT.set(false);
            ProjectSeele.LOGGER.warn(
                    "Unable to capture EVA command feed", exception);
            return;
        }
        int variant = eva.getUnitVariant();
        Util.ioPool().execute(() -> encodeAndSend(
                minecraft, variant, full));
    }

    private static void encodeAndSend(Minecraft minecraft, int variant,
                                      NativeImage full)
    {
        try (full;
             NativeImage reduced = new NativeImage(
                     ServerboundEvaVideoFramePacket.FRAME_WIDTH,
                     ServerboundEvaVideoFramePacket.FRAME_HEIGHT, false))
        {
            full.resizeSubRectTo(0, 0, full.getWidth(), full.getHeight(),
                    reduced);
            byte[] png = reduced.asByteArray();
            if (png.length <= ServerboundEvaVideoFramePacket.MAX_FRAME_BYTES)
            {
                minecraft.execute(() -> SeeleNetwork.CHANNEL.sendToServer(
                        new ServerboundEvaVideoFramePacket(variant, png)));
            }
        }
        catch (IOException | RuntimeException exception)
        {
            ProjectSeele.LOGGER.warn(
                    "Unable to encode EVA command feed", exception);
        }
        finally
        {
            CAPTURE_IN_FLIGHT.set(false);
        }
    }

    public static void acceptFrame(int variant, byte[] png)
    {
        if (variant < EvaUnit01Entity.UNIT_00
                || variant > EvaUnit01Entity.UNIT_02)
        {
            return;
        }
        NativeImage image = null;
        try
        {
            image = NativeImage.read(png);
            if (image.getWidth()
                    != ServerboundEvaVideoFramePacket.FRAME_WIDTH
                    || image.getHeight()
                    != ServerboundEvaVideoFramePacket.FRAME_HEIGHT)
            {
                image.close();
                return;
            }

            Minecraft minecraft = Minecraft.getInstance();
            DynamicTexture texture = TEXTURES[variant];
            if (texture == null)
            {
                texture = new DynamicTexture(image);
                TEXTURES[variant] = texture;
                minecraft.getTextureManager().register(
                        TEXTURE_IDS[variant], texture);
            }
            else
            {
                NativeImage previous = texture.getPixels();
                texture.setPixels(image);
                if (previous != null)
                {
                    previous.close();
                }
            }
            texture.upload();
            LAST_FRAME_NANOS[variant] = System.nanoTime();
        }
        catch (IOException | RuntimeException exception)
        {
            if (image != null)
            {
                image.close();
            }
            ProjectSeele.LOGGER.warn(
                    "Rejected EVA command feed frame", exception);
        }
    }

    @SubscribeEvent
    public static void onRenderLevelStage(RenderLevelStageEvent event)
    {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_PARTICLES)
        {
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        ClientLevel level = minecraft.level;
        if (level == null || minecraft.player == null
                || !level.dimension().equals(GeoFrontCommands.GEOFRONT))
        {
            activeLevel = level;
            return;
        }
        if (activeLevel != level)
        {
            activeLevel = level;
            for (int index = 0; index < LAST_FRAME_NANOS.length; index++)
            {
                LAST_FRAME_NANOS[index] = 0L;
            }
        }

        var origin = IntegratedNervMapBuilder.GEOFRONT_ORIGIN;
        var importedAnchor = origin.offset(0, 17, 58);
        boolean importedVideoWall = level.getBlockState(
                importedAnchor.offset(0, 4, -1)).is(Blocks.BLACK_CONCRETE)
                && level.getBlockState(importedAnchor.offset(-18, 4, -1))
                .is(Blocks.POLISHED_DEEPSLATE);
        var anchor = importedVideoWall ? importedAnchor
                : origin.offset(0, 7,
                        NervOperationsCentreBuilder.DISPLAY_Z + 1);
        if (minecraft.player.position().distanceToSqr(
                Vec3.atCenterOf(anchor)) > DISPLAY_RANGE_SQR)
        {
            return;
        }

        ensureStandbyTextures(minecraft);
        long now = System.nanoTime();
        Vec3 camera = event.getCamera().getPosition();
        for (int variant = 0; variant < 3; variant++)
        {
            boolean live = TEXTURES[variant] != null
                    && now - LAST_FRAME_NANOS[variant]
                    <= FRAME_STALE_NANOS;
            ResourceLocation texture = live ? TEXTURE_IDS[variant]
                    : STANDBY_TEXTURE_IDS[variant];
            Vec3 centre = Vec3.atCenterOf(
                    anchor.offset(SCREEN_X[variant], 4, 0))
                    .add(0.0D, 0.0D, -0.48D);
            renderScreen(event.getPoseStack(), camera, centre,
                    texture, minecraft);
        }
    }

    private static void ensureStandbyTextures(Minecraft minecraft)
    {
        for (int variant = 0; variant < STANDBY_TEXTURES.length; variant++)
        {
            if (STANDBY_TEXTURES[variant] != null)
            {
                continue;
            }
            NativeImage image = new NativeImage(
                    ServerboundEvaVideoFramePacket.FRAME_WIDTH,
                    ServerboundEvaVideoFramePacket.FRAME_HEIGHT, false);
            paintStandby(image, variant);
            DynamicTexture texture = new DynamicTexture(image);
            STANDBY_TEXTURES[variant] = texture;
            minecraft.getTextureManager().register(
                    STANDBY_TEXTURE_IDS[variant], texture);
        }
    }

    private static void paintStandby(NativeImage image, int variant)
    {
        int width = image.getWidth();
        int height = image.getHeight();
        int[] colour = UNIT_COLOURS[variant];
        int accent = rgba(colour[0], colour[1], colour[2], 255);
        int dim = rgba(colour[0] / 4, colour[1] / 4, colour[2] / 4, 255);
        int background = rgba(5, 9, 12, 255);
        for (int y = 0; y < height; y++)
        {
            for (int x = 0; x < width; x++)
            {
                boolean scan = y % 8 == 0;
                boolean grid = x % 20 == 0 || y % 20 == 0;
                image.setPixelRGBA(x, y, scan || grid ? dim : background);
            }
        }
        fillRect(image, 0, 0, width, 3, accent);
        fillRect(image, 0, height - 3, width, 3, accent);
        fillRect(image, 0, 0, 3, height, accent);
        fillRect(image, width - 3, 0, 3, height, accent);
        fillRect(image, 8, 8, 36, 4, accent);
        fillRect(image, width - 44, 8, 36, 4, accent);
        drawDigit(image, 58, 27, 0, accent);
        drawDigit(image, 82, 27, variant, accent);
        for (int bar = 0; bar < 7; bar++)
        {
            fillRect(image, 24 + bar * 17, 72, 11, 3,
                    bar < 2 ? accent : dim);
        }
    }

    private static void drawDigit(NativeImage image, int x, int y,
                                  int digit, int colour)
    {
        int mask = switch (digit)
        {
            case 1 -> 0b0000110;
            case 2 -> 0b1011011;
            default -> 0b0111111;
        };
        if ((mask & 0b0000001) != 0)
        {
            fillRect(image, x + 3, y, 13, 3, colour);
        }
        if ((mask & 0b0000010) != 0)
        {
            fillRect(image, x + 16, y + 3, 3, 12, colour);
        }
        if ((mask & 0b0000100) != 0)
        {
            fillRect(image, x + 16, y + 18, 3, 12, colour);
        }
        if ((mask & 0b0001000) != 0)
        {
            fillRect(image, x + 3, y + 30, 13, 3, colour);
        }
        if ((mask & 0b0010000) != 0)
        {
            fillRect(image, x, y + 18, 3, 12, colour);
        }
        if ((mask & 0b0100000) != 0)
        {
            fillRect(image, x, y + 3, 3, 12, colour);
        }
        if ((mask & 0b1000000) != 0)
        {
            fillRect(image, x + 3, y + 15, 13, 3, colour);
        }
    }

    private static void fillRect(NativeImage image, int x, int y,
                                 int width, int height, int colour)
    {
        for (int py = y; py < y + height; py++)
        {
            for (int px = x; px < x + width; px++)
            {
                image.setPixelRGBA(px, py, colour);
            }
        }
    }

    private static int rgba(int red, int green, int blue, int alpha)
    {
        return alpha << 24 | blue << 16 | green << 8 | red;
    }

    private static void renderScreen(PoseStack poseStack, Vec3 camera,
                                     Vec3 centre,
                                     ResourceLocation texture,
                                     Minecraft minecraft)
    {
        poseStack.pushPose();
        poseStack.translate(centre.x - camera.x,
                centre.y - camera.y, centre.z - camera.z);
        MultiBufferSource.BufferSource buffers =
                minecraft.renderBuffers().bufferSource();
        RenderType renderType = RenderType.entityCutoutNoCull(texture);
        VertexConsumer consumer = buffers.getBuffer(renderType);
        Matrix4f pose = poseStack.last().pose();
        Matrix3f normal = poseStack.last().normal();
        float halfWidth = SCREEN_WIDTH * 0.5F;
        float halfHeight = SCREEN_HEIGHT * 0.5F;
        vertex(consumer, pose, normal,
                -halfWidth, -halfHeight, 0.0F, 0.0F, 1.0F);
        vertex(consumer, pose, normal,
                halfWidth, -halfHeight, 0.0F, 1.0F, 1.0F);
        vertex(consumer, pose, normal,
                halfWidth, halfHeight, 0.0F, 1.0F, 0.0F);
        vertex(consumer, pose, normal,
                -halfWidth, halfHeight, 0.0F, 0.0F, 0.0F);
        buffers.endBatch(renderType);
        poseStack.popPose();
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
