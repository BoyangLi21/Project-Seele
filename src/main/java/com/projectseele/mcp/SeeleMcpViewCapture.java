package com.projectseele.mcp;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.projectseele.network.ClientboundMcpCaptureRequestPacket;
import com.projectseele.network.SeeleNetwork;
import java.util.Base64;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.PacketDistributor;

/** Coordinates a one-shot, read-only rendered-view capture for MCP. */
public final class SeeleMcpViewCapture
{
    public static final int DEFAULT_WIDTH = 640;
    public static final int DEFAULT_HEIGHT = 360;
    public static final int MIN_WIDTH = 160;
    public static final int MIN_HEIGHT = 90;
    public static final int MAX_WIDTH = 960;
    public static final int MAX_HEIGHT = 540;
    public static final int MAX_IMAGE_BYTES = 1024 * 1024;

    private static final byte[] PNG_SIGNATURE = {
            (byte) 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A
    };
    private static PendingCapture activeCapture;

    private SeeleMcpViewCapture() {}

    static synchronized CaptureTicket begin(MinecraftServer server,
                                            JsonObject body)
    {
        if (activeCapture != null)
        {
            return CaptureTicket.completed(error("CAPTURE_BUSY",
                    "Another rendered-view capture is already running."));
        }
        ServerPlayer player = server.getPlayerList().getPlayers().stream()
                .findFirst().orElse(null);
        if (player == null)
        {
            return CaptureTicket.completed(error("NO_ACTIVE_PLAYER",
                    "Join a local world before capturing a rendered view."));
        }
        int width = clamp(intOr(body, "width", DEFAULT_WIDTH),
                MIN_WIDTH, MAX_WIDTH);
        int height = clamp(intOr(body, "height", DEFAULT_HEIGHT),
                MIN_HEIGHT, MAX_HEIGHT);
        String label = stringOr(body, "viewLabel", "current-view").trim();
        if (label.isEmpty())
        {
            label = "current-view";
        }
        if (label.length() > 96)
        {
            label = label.substring(0, 96);
        }
        String id = "seele-capture-" + UUID.randomUUID();
        PendingCapture pending = new PendingCapture(id, player, width, height,
                label);
        activeCapture = pending;
        SeeleNetwork.CHANNEL.send(
                PacketDistributor.PLAYER.with(() -> player),
                new ClientboundMcpCaptureRequestPacket(id, width, height));
        return new CaptureTicket(id, pending.future);
    }

    public static synchronized void acceptFrame(ServerPlayer sender,
                                                String requestId,
                                                int width, int height,
                                                byte[] png, String clientError)
    {
        PendingCapture pending = activeCapture;
        if (pending == null || !pending.id.equals(requestId))
        {
            return;
        }
        if (!pending.playerId.equals(sender.getUUID()))
        {
            finish(pending, error("CAPTURE_PLAYER_MISMATCH",
                    "The rendered view came from an unexpected player."));
            return;
        }
        if (clientError != null && !clientError.isBlank())
        {
            finish(pending, error("CAPTURE_CLIENT_ERROR", clientError));
            return;
        }
        if (!validPng(png, width, height)
                || width != pending.width || height != pending.height)
        {
            finish(pending, error("INVALID_CAPTURE",
                    "The client returned an invalid PNG or unexpected dimensions."));
            return;
        }

        JsonObject result = new JsonObject();
        result.addProperty("success", true);
        result.addProperty("requestId", pending.id);
        result.addProperty("viewLabel", pending.label);
        result.addProperty("mimeType", "image/png");
        result.addProperty("width", width);
        result.addProperty("height", height);
        result.addProperty("byteCount", png.length);
        result.addProperty("player", pending.playerName);
        result.addProperty("dimension", pending.dimension);
        result.add("position", vector(pending.position));
        result.addProperty("yaw", pending.yaw);
        result.addProperty("pitch", pending.pitch);
        result.addProperty("imageBase64",
                Base64.getEncoder().encodeToString(png));
        finish(pending, result);
    }

    static synchronized void cancel(String requestId)
    {
        if (activeCapture != null && activeCapture.id.equals(requestId))
        {
            PendingCapture pending = activeCapture;
            activeCapture = null;
            pending.future.complete(error("CAPTURE_CANCELLED",
                    "The rendered-view capture was cancelled."));
        }
    }

    static synchronized void shutdown()
    {
        if (activeCapture != null)
        {
            PendingCapture pending = activeCapture;
            activeCapture = null;
            pending.future.complete(error("SERVER_STOPPED",
                    "The Minecraft server stopped during capture."));
        }
    }

    private static void finish(PendingCapture pending, JsonObject result)
    {
        if (activeCapture == pending)
        {
            activeCapture = null;
        }
        pending.future.complete(result);
    }

    private static boolean validPng(byte[] data, int width, int height)
    {
        if (data == null || data.length < 24
                || data.length > MAX_IMAGE_BYTES
                || width < MIN_WIDTH || width > MAX_WIDTH
                || height < MIN_HEIGHT || height > MAX_HEIGHT)
        {
            return false;
        }
        for (int index = 0; index < PNG_SIGNATURE.length; index++)
        {
            if (data[index] != PNG_SIGNATURE[index])
            {
                return false;
            }
        }
        return readBigEndianInt(data, 16) == width
                && readBigEndianInt(data, 20) == height;
    }

    private static int readBigEndianInt(byte[] data, int offset)
    {
        return (data[offset] & 0xFF) << 24
                | (data[offset + 1] & 0xFF) << 16
                | (data[offset + 2] & 0xFF) << 8
                | data[offset + 3] & 0xFF;
    }

    private static int intOr(JsonObject object, String key, int fallback)
    {
        try
        {
            return object != null && object.has(key)
                    ? object.get(key).getAsInt() : fallback;
        }
        catch (RuntimeException ignored)
        {
            return fallback;
        }
    }

    private static String stringOr(JsonObject object, String key,
                                   String fallback)
    {
        try
        {
            return object != null && object.has(key)
                    ? object.get(key).getAsString() : fallback;
        }
        catch (RuntimeException ignored)
        {
            return fallback;
        }
    }

    private static int clamp(int value, int min, int max)
    {
        return Math.max(min, Math.min(max, value));
    }

    private static JsonArray vector(BlockPos position)
    {
        JsonArray vector = new JsonArray();
        vector.add(position.getX());
        vector.add(position.getY());
        vector.add(position.getZ());
        return vector;
    }

    private static JsonObject error(String code, String message)
    {
        JsonObject root = new JsonObject();
        JsonObject error = new JsonObject();
        error.addProperty("code", code);
        error.addProperty("message", message);
        root.add("error", error);
        return root;
    }

    static final class CaptureTicket
    {
        final String id;
        final CompletableFuture<JsonObject> future;

        private CaptureTicket(String id, CompletableFuture<JsonObject> future)
        {
            this.id = id;
            this.future = future;
        }

        private static CaptureTicket completed(JsonObject result)
        {
            return new CaptureTicket("", CompletableFuture.completedFuture(result));
        }
    }

    private static final class PendingCapture
    {
        private final String id;
        private final UUID playerId;
        private final String playerName;
        private final String dimension;
        private final BlockPos position;
        private final float yaw;
        private final float pitch;
        private final int width;
        private final int height;
        private final String label;
        private final CompletableFuture<JsonObject> future =
                new CompletableFuture<>();

        private PendingCapture(String id, ServerPlayer player,
                               int width, int height, String label)
        {
            this.id = id;
            this.playerId = player.getUUID();
            this.playerName = player.getGameProfile().getName();
            this.dimension = player.serverLevel().dimension().location()
                    .toString();
            this.position = player.blockPosition().immutable();
            this.yaw = player.getYRot();
            this.pitch = player.getXRot();
            this.width = width;
            this.height = height;
            this.label = label;
        }
    }
}
