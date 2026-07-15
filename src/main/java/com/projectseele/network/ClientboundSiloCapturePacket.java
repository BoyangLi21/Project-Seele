package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Starts the deterministic launch-silo scene capture on the integrated client. */
public final class ClientboundSiloCapturePacket
{
    private final int entityId;

    public ClientboundSiloCapturePacket(int entityId)
    {
        this.entityId = entityId;
    }

    public ClientboundSiloCapturePacket(FriendlyByteBuf buffer)
    {
        this(buffer.readVarInt());
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeVarInt(this.entityId);
    }

    public void handle(Supplier<NetworkEvent.Context> context)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.visual.VisualCaptureManager.startSilo(
                        this.entityId));
        context.get().setPacketHandled(true);
    }
}
