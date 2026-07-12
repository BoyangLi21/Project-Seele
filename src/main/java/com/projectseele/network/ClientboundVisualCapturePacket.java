package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Starts the deterministic client-side Visual Lab screenshot sequence. */
public class ClientboundVisualCapturePacket
{
    public final int entityId;
    public final int pose;

    public ClientboundVisualCapturePacket(int entityId, int pose)
    {
        this.entityId = entityId;
        this.pose = pose;
    }

    public ClientboundVisualCapturePacket(FriendlyByteBuf buffer)
    {
        this(buffer.readVarInt(), buffer.readVarInt());
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeVarInt(this.entityId);
        buffer.writeVarInt(this.pose);
    }

    public void handle(Supplier<NetworkEvent.Context> context)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.visual.VisualCaptureManager.start(this.entityId, this.pose));
        context.get().setPacketHandled(true);
    }
}
