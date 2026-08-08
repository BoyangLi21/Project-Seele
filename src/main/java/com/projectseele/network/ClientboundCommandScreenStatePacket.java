package com.projectseele.network;

import java.util.function.Supplier;

import com.projectseele.world.NervCommandDisplayState;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Synchronizes the four physical S20 command-screen power switches. */
public final class ClientboundCommandScreenStatePacket
{
    private final int visibleMask;

    public ClientboundCommandScreenStatePacket(int visibleMask)
    {
        this.visibleMask = visibleMask
                & NervCommandDisplayState.ALL_VISIBLE_MASK;
    }

    public ClientboundCommandScreenStatePacket(FriendlyByteBuf buffer)
    {
        this(buffer.readByte());
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeByte(this.visibleMask);
    }

    public void handle(Supplier<NetworkEvent.Context> contextSupplier)
    {
        NetworkEvent.Context context = contextSupplier.get();
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.EvaCommandFeedClient
                        .setCommandScreenMask(this.visibleMask));
        context.setPacketHandled(true);
    }
}
