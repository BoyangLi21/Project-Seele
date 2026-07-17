package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/**
 * Corrects the locally controlled EVA at the physical Tokyo-3 shaft exit.
 * Vanilla entity teleport packets intentionally ignore a vehicle controlled by
 * the local client, so the launch rail needs one explicit authoritative snap.
 */
public final class ClientboundEvaArrivalSyncPacket
{
    private final int entityId;
    private final double x;
    private final double y;
    private final double z;
    private final float yaw;
    private final float pitch;

    public ClientboundEvaArrivalSyncPacket(int entityId, double x, double y, double z,
            float yaw, float pitch)
    {
        this.entityId = entityId;
        this.x = x;
        this.y = y;
        this.z = z;
        this.yaw = yaw;
        this.pitch = pitch;
    }

    public ClientboundEvaArrivalSyncPacket(FriendlyByteBuf buffer)
    {
        this(buffer.readVarInt(), buffer.readDouble(), buffer.readDouble(),
                buffer.readDouble(), buffer.readFloat(), buffer.readFloat());
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeVarInt(this.entityId);
        buffer.writeDouble(this.x);
        buffer.writeDouble(this.y);
        buffer.writeDouble(this.z);
        buffer.writeFloat(this.yaw);
        buffer.writeFloat(this.pitch);
    }

    public void handle(Supplier<NetworkEvent.Context> context)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.ClientEvaArrivalSync.apply(
                        this.entityId, this.x, this.y, this.z, this.yaw, this.pitch));
        context.get().setPacketHandled(true);
    }
}
