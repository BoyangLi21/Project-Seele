package com.projectseele.world;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.level.ChunkPos;
import java.util.Comparator;

/** A connected reel remains simulated even after its pilot leaves the chunk. */
public final class EvaPowerLinkR25
{
    private static final TicketType<ChunkPos> TICKET = TicketType.create(
            "eva_umbilical_reel", Comparator.comparingLong(ChunkPos::toLong), 60);

    public static void retain(ServerLevel level, BlockPos anchor)
    {
        ChunkPos chunk = new ChunkPos(anchor);
        level.getChunkSource().addRegionTicket(TICKET, chunk, 2, chunk);
        // Only the already connected, range-checked reel may load a chunk.
        level.getChunk(chunk.x, chunk.z);
    }

    private EvaPowerLinkR25() {}
}
