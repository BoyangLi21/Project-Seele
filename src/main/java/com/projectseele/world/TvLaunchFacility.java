package com.projectseele.world;

import java.nio.file.Files;
import java.util.Map;
import java.util.WeakHashMap;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;

/** Commissioned geometry, never inferred from air in an arbitrary world. */
public final class TvLaunchFacility
{
    private static final Map<ServerLevel,Boolean> ENABLED=new WeakHashMap<>();
    public static boolean enabled(ServerLevel level)
    {
        return ENABLED.computeIfAbsent(level,l->l.dimension().location().toString().equals("projectseele:geofront")
                &&Files.isRegularFile(l.getServer().getWorldPath(LevelResource.ROOT).resolve("tv_facilities_r16.json")));
    }
    /** Pressure bulkheads spaced farther apart than a complete EVA and pallet. */
    public static final int[] BULKHEAD_BELOW_SURFACE={412,272,132};
    private TvLaunchFacility() {}
}
