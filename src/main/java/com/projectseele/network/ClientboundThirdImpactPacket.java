package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/**
 * Manifests the Tree of Life. Carries the facing yaw so the client light
 * geometry and the server-parked Mass-Production Evas share one layout.
 */
public class ClientboundThirdImpactPacket
{
    public final double x;
    public final double y;
    public final double z;
    public final float yaw;
    /** True when a real Unit-01 was nailed to Tiferet (skip the silhouette). */
    public final boolean hasUnit;

    public ClientboundThirdImpactPacket(double x, double y, double z, float yaw, boolean hasUnit)
    {
        this.x = x;
        this.y = y;
        this.z = z;
        this.yaw = yaw;
        this.hasUnit = hasUnit;
    }

    public ClientboundThirdImpactPacket(FriendlyByteBuf buf)
    {
        this(buf.readDouble(), buf.readDouble(), buf.readDouble(), buf.readFloat(), buf.readBoolean());
    }

    public void encode(FriendlyByteBuf buf)
    {
        buf.writeDouble(this.x);
        buf.writeDouble(this.y);
        buf.writeDouble(this.z);
        buf.writeFloat(this.yaw);
        buf.writeBoolean(this.hasUnit);
    }

    public void handle(Supplier<NetworkEvent.Context> ctx)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.fx.ClientFxManager.addThirdImpact(this));
        ctx.get().setPacketHandled(true);
    }
}
