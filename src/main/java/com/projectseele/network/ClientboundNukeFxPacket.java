package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Plays the nuke-grade beam impact: flash, fireball, cross light, shockwave. */
public class ClientboundNukeFxPacket
{
    public final double x;
    public final double y;
    public final double z;
    public final float scale;

    public ClientboundNukeFxPacket(double x, double y, double z, float scale)
    {
        this.x = x;
        this.y = y;
        this.z = z;
        this.scale = scale;
    }

    public ClientboundNukeFxPacket(FriendlyByteBuf buf)
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
                () -> () -> com.projectseele.client.fx.ClientFxManager.addNukeFx(this));
        ctx.get().setPacketHandled(true);
    }
}
