package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.core.BlockPos;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Starts the deterministic Tokyo-3 full-scene capture on the integrated client. */
public final class ClientboundTokyo3CapturePacket
{
    private final BlockPos origin;

    public ClientboundTokyo3CapturePacket(BlockPos origin)
    {
        this.origin = origin;
    }

    public ClientboundTokyo3CapturePacket(FriendlyByteBuf buffer)
    {
        this(buffer.readBlockPos());
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeBlockPos(this.origin);
    }

    public void handle(Supplier<NetworkEvent.Context> context)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.visual.VisualCaptureManager.startTokyo3(
                        this.origin));
        context.get().setPacketHandled(true);
    }
}
