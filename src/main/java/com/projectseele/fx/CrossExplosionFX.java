package com.projectseele.fx;

import com.projectseele.network.ClientboundCrossExplosionPacket;
import com.projectseele.network.SeeleNetwork;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.PacketDistributor;

/**
 * Server-side entry point for the signature EVA cross explosion. Angels play
 * it on death by default; N2 mines, self-destructs and Third Impact reuse it.
 */
public final class CrossExplosionFX
{
    private CrossExplosionFX() {}

    /**
     * Broadcasts a cross explosion to every player tracking the chunk. The
     * visual plants itself on the ground below {@code center} so the cross
     * rises out of the terrain no matter where the source died.
     */
    public static void spawn(ServerLevel level, Vec3 center, float scale)
    {
        double groundY = center.y;
        BlockPos.MutableBlockPos probe = BlockPos.containing(center).mutable();
        for (int i = 0; i < 48 && probe.getY() > level.getMinBuildHeight(); i++)
        {
            if (!level.getBlockState(probe).getCollisionShape(level, probe).isEmpty())
            {
                groundY = probe.getY() + 1.0D;
                break;
            }
            probe.move(0, -1, 0);
        }

        ClientboundCrossExplosionPacket packet =
                new ClientboundCrossExplosionPacket(center.x, groundY, center.z, scale);
        SeeleNetwork.CHANNEL.send(
                PacketDistributor.TRACKING_CHUNK.with(() -> level.getChunkAt(BlockPos.containing(center))),
                packet);
    }
}
