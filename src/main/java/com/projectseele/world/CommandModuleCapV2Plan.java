package com.projectseele.world;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Legal owner for the thirteen authored crown layers above CommandVolume.
 *
 * <p>The imported local command asset is installed only after this owner and
 * {@code COMMAND_VOLUME} are complete.  Keeping the cap separate avoids
 * silently expanding the command owner across the secure lift and office
 * contracts.</p>
 */
public final class CommandModuleCapV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "COMMAND_MODULE_CAP";
    private static final String STAGE = "S12_COMMAND_MODULE_CAP";
    private static final String PLAN_VERSION = "command-module-cap-v1";

    private final FacilitySchemaV2.IntBox owner;
    private final String buildPlanHash;

    public CommandModuleCapV2Plan(
            FacilitySchemaV2.ResolvedManifest manifest)
    {
        this.owner = manifest.requireZone(ZONE_ID).owner();
        this.buildPlanHash = FacilityV2Hashing.buildPlanHash(
                ZONE_ID, STAGE, PLAN_VERSION, this.owner);
    }

    @Override
    public String zoneId()
    {
        return ZONE_ID;
    }

    @Override
    public String stage()
    {
        return STAGE;
    }

    @Override
    public String buildPlanHash()
    {
        return this.buildPlanHash;
    }

    @Override
    public FacilitySchemaV2.IntBox owner()
    {
        return this.owner;
    }

    @Override
    public BlockState blockAt(BlockPos position)
    {
        return Blocks.AIR.defaultBlockState();
    }
}
