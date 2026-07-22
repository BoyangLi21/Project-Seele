package com.projectseele.entity;

import net.minecraft.core.BlockPos;

/** Angel that can resume a persistent NERV-beacon assault after a reload. */
public interface SiegeAnchorAware
{
    void setSiegeBeacon(BlockPos beacon);
}