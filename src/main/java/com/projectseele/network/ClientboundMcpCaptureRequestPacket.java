package com.projectseele.network;

import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Requests one world-only framebuffer capture from the active client. */
public final class ClientboundMcpCaptureRequestPacket
{
    private final String requestId;
    private final int width;
    private final int height;

    public ClientboundMcpCaptureRequestPacket(String requestId,
                                              int width, int height)
    {
        this.requestId = requestId;
        this.width = width;
        this.height = height;
    }

    public ClientboundMcpCaptureRequestPacket(FriendlyByteBuf buffer)
    {
        this(buffer.readUtf(64), buffer.readVarInt(), buffer.readVarInt());
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeUtf(this.requestId, 64);
        buffer.writeVarInt(this.width);
        buffer.writeVarInt(this.height);
    }

    public void handle(Supplier<NetworkEvent.Context> contextSupplier)
    {
        NetworkEvent.Context context = contextSupplier.get();
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> context.enqueueWork(() ->
                        com.projectseele.client.McpViewCaptureClient.request(
                                this.requestId, this.width, this.height)));
        context.setPacketHandled(true);
    }
}
