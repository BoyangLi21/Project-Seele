package com.projectseele.world;

import net.minecraft.server.MinecraftServer;

/**
 * Compatibility shim for the retired one-off performance sampler.
 *
 * <p>The one-off diagnosis established the client/GPU profile and is no
 * longer part of normal gameplay. Existing call sites can be removed as
 * their owning systems are rebuilt; until then these methods deliberately
 * perform no work, allocate nothing and never display test instructions.</p>
 */
public final class PerformanceCounters
{
    private PerformanceCounters() {}

    public static void beginServerTick(MinecraftServer server) {}

    public static void markServerEndPhase(MinecraftServer server) {}

    public static void beginProjectTickWork(MinecraftServer server) {}

    public static void endServerTick(MinecraftServer server) {}

    public static void recordWorldBlockWrites(long count) {}

    public static void recordSyncChunkLoads(long count) {}

    public static void recordGlobalEntityScan() {}

    public static void recordRaycasts(long count) {}

    public static void recordFramebufferCapture() {}

    public static void recordPngEncode() {}

    public static void recordVideoFrame(long bytes) {}

    public static void recordBuilderCall() {}

    public static void recordRepairCall() {}

    public static void recordForcedChunkDelta(int delta) {}

    public static void recordForcedChunkSnapshot(int current) {}

    public static void recordClientFrame() {}

    public static void leaveClientScenario() {}

    public static void reset() {}
}
