package com.projectseele.network;

import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Synchronizes a seated player's visible Commander Ikari pose. */
public final class ClientboundCommandSeatPosePacket
{
    private final int entityId;
    private final boolean active;

    public ClientboundCommandSeatPosePacket(int entityId, boolean active)
    {
        this.entityId = entityId;
        this.active = active;
    }

    public ClientboundCommandSeatPosePacket(FriendlyByteBuf buffer)
    {
        this(buffer.readVarInt(), buffer.readBoolean());
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeVarInt(this.entityId);
        buffer.writeBoolean(this.active);
    }

    public void handle(Supplier<NetworkEvent.Context> contextSupplier)
    {
        NetworkEvent.Context context = contextSupplier.get();
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.CommanderPoseClient
                        .setActive(this.entityId, this.active));
        context.setPacketHandled(true);
    }
}
