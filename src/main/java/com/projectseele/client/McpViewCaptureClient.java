package com.projectseele.client;

import com.mojang.blaze3d.platform.NativeImage;
import com.projectseele.ProjectSeele;
import com.projectseele.mcp.SeeleMcpViewCapture;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.network.ServerboundMcpCaptureResponsePacket;
import java.io.IOException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import net.minecraft.Util;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Captures the completed level render without moving the player or camera. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID,
        bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class McpViewCaptureClient
{
    private static final AtomicReference<CaptureRequest> PENDING =
            new AtomicReference<>();
    private static final AtomicBoolean CAPTURE_IN_FLIGHT =
            new AtomicBoolean();

    private McpViewCaptureClient() {}

    public static void request(String requestId, int width, int height)
    {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null || minecraft.player == null)
        {
            sendFailure(requestId, "No rendered world is active on the client.");
            return;
        }
        PENDING.set(new CaptureRequest(requestId, width, height));
    }

    @SubscribeEvent
    public static void onRenderLevelStage(RenderLevelStageEvent event)
    {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_LEVEL
                || CAPTURE_IN_FLIGHT.get())
        {
            return;
        }
        CaptureRequest request = PENDING.getAndSet(null);
        if (request == null || !CAPTURE_IN_FLIGHT.compareAndSet(false, true))
        {
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        NativeImage full;
        try
        {
            full = Screenshot.takeScreenshot(minecraft.getMainRenderTarget());
        }
        catch (RuntimeException exception)
        {
            CAPTURE_IN_FLIGHT.set(false);
            sendFailure(request.id, "Framebuffer capture failed: "
                    + safeMessage(exception));
            return;
        }
        Util.ioPool().execute(() -> encodeAndSend(minecraft, request, full));
    }

    private static void encodeAndSend(Minecraft minecraft,
                                      CaptureRequest request,
                                      NativeImage full)
    {
        try (full;
             NativeImage reduced = new NativeImage(
                     request.width, request.height, false))
        {
            full.resizeSubRectTo(0, 0, full.getWidth(), full.getHeight(),
                    reduced);
            byte[] png = reduced.asByteArray();
            if (png.length > SeeleMcpViewCapture.MAX_IMAGE_BYTES)
            {
                sendFailure(request.id,
                        "Encoded capture exceeded the 1 MiB safety limit.");
                return;
            }
            minecraft.execute(() -> SeeleNetwork.CHANNEL.sendToServer(
                    new ServerboundMcpCaptureResponsePacket(request.id,
                            request.width, request.height, png, "")));
        }
        catch (IOException | RuntimeException exception)
        {
            sendFailure(request.id, "PNG encoding failed: "
                    + safeMessage(exception));
        }
        finally
        {
            CAPTURE_IN_FLIGHT.set(false);
        }
    }

    private static void sendFailure(String requestId, String message)
    {
        Minecraft minecraft = Minecraft.getInstance();
        minecraft.execute(() ->
        {
            if (minecraft.getConnection() != null)
            {
                SeeleNetwork.CHANNEL.sendToServer(
                        new ServerboundMcpCaptureResponsePacket(requestId,
                                0, 0, new byte[0], message));
            }
        });
    }

    private static String safeMessage(Throwable throwable)
    {
        String message = throwable.getMessage();
        return message == null || message.isBlank()
                ? throwable.getClass().getSimpleName() : message;
    }

    private record CaptureRequest(String id, int width, int height) {}
}
