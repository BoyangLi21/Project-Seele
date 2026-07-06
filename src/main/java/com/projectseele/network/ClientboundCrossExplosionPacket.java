package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Tells clients to play a cross explosion at a position. */
public class ClientboundCrossExplosionPacket
{
    public final double x;
    public final double y;
    public final double z;
    public final float scale;

    public ClientboundCrossExplosionPacket(double x, double y, double z, float scale)
    {
        this.x = x;
        this.y = y;
        this.z = z;
        this.scale = scale;
    }

    public ClientboundCrossExplosionPacket(FriendlyByteBuf buf)
    {
        this(buf.readDouble(), buf.readDouble(), buf.readDouble(), buf.readFloat());
    }

    public void encode(FriendlyByteBuf buf)
    {
        buf.writeDouble(this.x);
        buf.writeDouble(this.y);
        buf.writeDouble(this.z);
        buf.writeFloat(this.scale);
    }

    public void handle(Supplier<NetworkEvent.Context> ctx)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.fx.ClientFxManager.addCrossExplosion(this));
        ctx.get().setPacketHandled(true);
    }
}
