package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Starts or stops the Angel-attack alarm state on the client. */
public class ClientboundAlarmPacket
{
    public final boolean active;

    public ClientboundAlarmPacket(boolean active)
    {
        this.active = active;
    }

    public ClientboundAlarmPacket(FriendlyByteBuf buf)
    {
        this(buf.readBoolean());
    }

    public void encode(FriendlyByteBuf buf)
    {
        buf.writeBoolean(this.active);
    }

    public void handle(Supplier<NetworkEvent.Context> ctx)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.ClientAlarmState.setActive(this.active));
        ctx.get().setPacketHandled(true);
    }
}
