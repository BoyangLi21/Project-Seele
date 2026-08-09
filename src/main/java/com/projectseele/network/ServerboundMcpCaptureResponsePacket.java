package com.projectseele.network;

import com.projectseele.mcp.SeeleMcpViewCapture;
import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.NetworkEvent;

/** Returns one bounded PNG capture to its pending MCP request. */
public final class ServerboundMcpCaptureResponsePacket
{
    private final String requestId;
    private final int width;
    private final int height;
    private final byte[] png;
    private final String error;

    public ServerboundMcpCaptureResponsePacket(String requestId,
                                               int width, int height,
                                               byte[] png, String error)
    {
        this.requestId = requestId;
        this.width = width;
        this.height = height;
        this.png = png == null ? new byte[0] : png;
        this.error = boundedError(error);
    }

    public ServerboundMcpCaptureResponsePacket(FriendlyByteBuf buffer)
    {
        this(buffer.readUtf(64), buffer.readVarInt(), buffer.readVarInt(),
                buffer.readByteArray(SeeleMcpViewCapture.MAX_IMAGE_BYTES),
                buffer.readUtf(512));
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeUtf(this.requestId, 64);
        buffer.writeVarInt(this.width);
        buffer.writeVarInt(this.height);
        buffer.writeByteArray(this.png);
        buffer.writeUtf(this.error, 512);
    }

    public void handle(Supplier<NetworkEvent.Context> contextSupplier)
    {
        NetworkEvent.Context context = contextSupplier.get();
        ServerPlayer sender = context.getSender();
        if (sender != null)
        {
            context.enqueueWork(() -> SeeleMcpViewCapture.acceptFrame(sender,
                    this.requestId, this.width, this.height,
                    this.png, this.error));
        }
        context.setPacketHandled(true);
    }

    private static String boundedError(String error)
    {
        if (error == null)
        {
            return "";
        }
        return error.length() <= 512 ? error : error.substring(0, 512);
    }
}
