package com.projectseele.network;

import java.util.function.Supplier;

import com.projectseele.client.EvaCommandFeedClient;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.network.NetworkEvent;

/** Server-side subscription for the expensive real-pilot cockpit capture. */
public final class ClientboundEvaVideoDemandPacket
{
    private final boolean demanded;

    public ClientboundEvaVideoDemandPacket(boolean demanded)
    {
        this.demanded = demanded;
    }

    public ClientboundEvaVideoDemandPacket(FriendlyByteBuf buffer)
    {
        this(buffer.readBoolean());
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeBoolean(this.demanded);
    }

    public void handle(Supplier<NetworkEvent.Context> contextSupplier)
    {
        NetworkEvent.Context context = contextSupplier.get();
        context.enqueueWork(() ->
                EvaCommandFeedClient.setCaptureDemand(this.demanded));
        context.setPacketHandled(true);
    }
}
