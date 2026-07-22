package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** One authenticated cockpit frame relayed to command-room observers. */
public final class ClientboundEvaVideoFramePacket
{
    private final int variant;
    private final byte[] png;

    public ClientboundEvaVideoFramePacket(int variant, byte[] png)
    {
        this.variant = variant;
        this.png = png;
    }

    public ClientboundEvaVideoFramePacket(FriendlyByteBuf buffer)
    {
        this(buffer.readUnsignedByte(),
                buffer.readByteArray(
                        ServerboundEvaVideoFramePacket.MAX_FRAME_BYTES));
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeByte(this.variant);
        buffer.writeByteArray(this.png);
    }

    public void handle(Supplier<NetworkEvent.Context> contextSupplier)
    {
        NetworkEvent.Context context = contextSupplier.get();
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> context.enqueueWork(() ->
                        com.projectseele.client.EvaCommandFeedClient
                                .acceptFrame(this.variant, this.png)));
        context.setPacketHandled(true);
    }
}
