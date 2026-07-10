package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Plays a nuke-grade beam impact; only Angel attacks request a cross. */
public class ClientboundNukeFxPacket
{
    public final double x;
    public final double y;
    public final double z;
    public final float scale;
    public final boolean angelCross;

    public ClientboundNukeFxPacket(double x, double y, double z, float scale, boolean angelCross)
    {
        this.x = x;
        this.y = y;
        this.z = z;
        this.scale = scale;
        this.angelCross = angelCross;
    }

    public ClientboundNukeFxPacket(FriendlyByteBuf buf)
    {
        this(buf.readDouble(), buf.readDouble(), buf.readDouble(), buf.readFloat(), buf.readBoolean());
    }

    public void encode(FriendlyByteBuf buf)
    {
        buf.writeDouble(this.x);
        buf.writeDouble(this.y);
        buf.writeDouble(this.z);
        buf.writeFloat(this.scale);
        buf.writeBoolean(this.angelCross);
    }

    public void handle(Supplier<NetworkEvent.Context> ctx)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.fx.ClientFxManager.addNukeFx(this));
        ctx.get().setPacketHandled(true);
    }
}
