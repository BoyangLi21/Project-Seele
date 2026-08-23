package com.projectseele.network;

import java.util.function.Supplier;
import java.util.concurrent.atomic.AtomicInteger;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.network.PacketDistributor;

/** One authenticated cockpit frame relayed to command-room observers. */
public final class ClientboundEvaVideoFramePacket
{
    private static final AtomicInteger NEXT_FRAME_ID = new AtomicInteger();
    private final int variant;
    private final int frameId;
    private final int chunkIndex;
    private final int chunkCount;
    private final int totalBytes;
    private final byte[] chunk;

    public ClientboundEvaVideoFramePacket(int variant, int frameId,
                                          int chunkIndex, int chunkCount,
                                          int totalBytes, byte[] chunk)
    {
        this.variant = variant;
        this.frameId = frameId;
        this.chunkIndex = chunkIndex;
        this.chunkCount = chunkCount;
        this.totalBytes = totalBytes;
        this.chunk = chunk;
    }

    public ClientboundEvaVideoFramePacket(FriendlyByteBuf buffer)
    {
        this(buffer.readUnsignedByte(), buffer.readVarInt(),
                buffer.readVarInt(), buffer.readVarInt(), buffer.readVarInt(),
                buffer.readByteArray(
                        ServerboundEvaVideoFramePacket.MAX_CHUNK_BYTES));
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeByte(this.variant);
        buffer.writeVarInt(this.frameId);
        buffer.writeVarInt(this.chunkIndex);
        buffer.writeVarInt(this.chunkCount);
        buffer.writeVarInt(this.totalBytes);
        buffer.writeByteArray(this.chunk);
    }

    public void handle(Supplier<NetworkEvent.Context> contextSupplier)
    {
        NetworkEvent.Context context = contextSupplier.get();
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> context.enqueueWork(() ->
                        com.projectseele.client.EvaCommandFeedClient
                                .acceptFrameChunk(this.variant, this.frameId,
                                        this.chunkIndex, this.chunkCount,
                                        this.totalBytes, this.chunk)));
        context.setPacketHandled(true);
    }

    public static void send(ServerPlayer viewer, int variant, byte[] frame)
    {
        if (frame == null || frame.length <= 0
                || frame.length > EvaVideoFrameTransport.MAX_FRAME_BYTES)
        {
            return;
        }
        int frameId = NEXT_FRAME_ID.incrementAndGet();
        int chunks = EvaVideoFrameTransport.chunkCount(frame.length);
        for (int index = 0; index < chunks; index++)
        {
            SeeleNetwork.CHANNEL.send(
                    PacketDistributor.PLAYER.with(() -> viewer),
                    new ClientboundEvaVideoFramePacket(variant, frameId,
                            index, chunks, frame.length,
                            EvaVideoFrameTransport.chunk(frame, index)));
        }
    }
}
