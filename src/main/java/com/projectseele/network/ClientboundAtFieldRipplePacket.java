package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/**
 * Plays an A.T. Field ripple: concentric orange hexagons expanding in the
 * plane whose normal is (nx, ny, nz), centred at (x, y, z).
 */
public class ClientboundAtFieldRipplePacket
{
    public final double x;
    public final double y;
    public final double z;
    public final float nx;
    public final float ny;
    public final float nz;

    public ClientboundAtFieldRipplePacket(double x, double y, double z, float nx, float ny, float nz)
    {
        this.x = x;
        this.y = y;
        this.z = z;
        this.nx = nx;
        this.ny = ny;
        this.nz = nz;
    }

    public ClientboundAtFieldRipplePacket(FriendlyByteBuf buf)
    {
        this(buf.readDouble(), buf.readDouble(), buf.readDouble(),
                buf.readFloat(), buf.readFloat(), buf.readFloat());
    }

    public void encode(FriendlyByteBuf buf)
    {
        buf.writeDouble(this.x);
        buf.writeDouble(this.y);
        buf.writeDouble(this.z);
        buf.writeFloat(this.nx);
        buf.writeFloat(this.ny);
        buf.writeFloat(this.nz);
    }

    public void handle(Supplier<NetworkEvent.Context> ctx)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.fx.ClientFxManager.addAtFieldRipple(this));
        ctx.get().setPacketHandled(true);
    }
}
