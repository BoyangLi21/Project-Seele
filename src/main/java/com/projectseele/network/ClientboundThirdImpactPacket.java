package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Starts the client-side Kabbalah tree manifestation. */
public class ClientboundThirdImpactPacket
{
    public final double x;
    public final double y;
    public final double z;

    public ClientboundThirdImpactPacket(double x, double y, double z)
    {
        this.x = x;
        this.y = y;
        this.z = z;
    }

    public ClientboundThirdImpactPacket(FriendlyByteBuf buf)
    {
        this(buf.readDouble(), buf.readDouble(), buf.readDouble());
    }

    public void encode(FriendlyByteBuf buf)
    {
        buf.writeDouble(this.x);
        buf.writeDouble(this.y);
        buf.writeDouble(this.z);
    }

    public void handle(Supplier<NetworkEvent.Context> ctx)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.fx.ClientFxManager.addThirdImpact(this));
        ctx.get().setPacketHandled(true);
    }
}
