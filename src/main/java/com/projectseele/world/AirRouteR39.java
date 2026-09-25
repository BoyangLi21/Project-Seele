package com.projectseele.world;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.*;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.phys.Vec3;
import java.util.Comparator;

/** Bounded, nonblocking look-ahead; a streaming pause never restarts a flight leg. */
public final class AirRouteR39
{
    private static final TicketType<ChunkPos> TICKET = TicketType.create("seele_air_route_r39", Comparator.comparingLong(ChunkPos::toLong), 40);
    public static int duration(Vec3 from, Vec3 to)
    { return Math.max(80, (int)Math.ceil(from.distanceTo(to) / 60)); }
    public static double progress(double ticks, int duration)
    {
        double t = Math.max(0, Math.min(1, ticks / Math.max(1, duration)));
        return t*t*t*(t*(t*6-15)+10);
    }
    public static void prefetch(ServerLevel level, Vec3 from, Vec3 to, int age, int duration)
    {
        if (level.getGameTime()%5 != 0 && age != 0) return;
        Vec3 at = from.lerp(to, progress(age, duration));
        Vec3 direction = to.subtract(at); double distance = Math.min(384, direction.length());
        direction = direction.normalize();
        for (double d=0; d<=distance+32; d+=32)
        {
            var chunk = new ChunkPos(BlockPos.containing(at.add(direction.scale(Math.min(d,distance)))));
            level.getChunkSource().addRegionTicket(TICKET,chunk,2,chunk);
        }
    }
    private AirRouteR39() {}
}
