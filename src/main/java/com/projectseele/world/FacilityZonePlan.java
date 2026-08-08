package com.projectseele.world;

import javax.annotation.Nullable;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Deterministic, side-effect-free block plan for one FacilitySchema owner.
 *
 * <p>A {@code null} result preserves fingerprinted geology. Non-null results
 * are the complete intended state for that position. Runtime machinery state
 * is deliberately excluded from construction plans.</p>
 */
public interface FacilityZonePlan
{
    String zoneId();

    String stage();

    String buildPlanHash();

    FacilitySchemaV2.IntBox owner();

    @Nullable
    BlockState blockAt(BlockPos position);
}
