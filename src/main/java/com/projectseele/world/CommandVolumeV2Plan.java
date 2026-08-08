package com.projectseele.world;

import java.util.List;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Civil reservation for the single imported NERV command bridge.
 *
 * <p>The private 1:1 NBT is the only visual author of this room. Earlier
 * revisions built a second command room, furniture, screens and side
 * circulation inside the same owner before the NBT post-pass. Those
 * structures survived outside the template envelope and caused the visible
 * overlapping galleries rejected in human review.</p>
 *
 * <p>This plan now does only two things: it preserves the load-bearing geology
 * around the exact imported envelope and opens declared reciprocal ports.
 * {@link FacilityV2CommandInteriorDirector} is the sole presentation
 * post-pass and may touch only measured masks and the measured empty rear
 * sleeve.</p>
 */
public final class CommandVolumeV2Plan implements FacilityZonePlan
{
    private static final String ZONE_ID = "COMMAND_VOLUME";
    private static final String STAGE = "S19_COMMAND_CIVIL_RESERVATION";
    private static final String PLAN_VERSION =
            "command-volume-s19-nbt-authority-a1";

    private static final BlockState AIR = Blocks.AIR.defaultBlockState();

    private final FacilitySchemaV2.IntBox owner;
    private final List<FacilitySchemaV2.PortSpec> ports;
    private final String buildPlanHash;

    public CommandVolumeV2Plan(
            FacilitySchemaV2.ResolvedManifest manifest)
    {
        this.owner = manifest.requireZone(ZONE_ID).owner();
        this.ports = manifest.ports().stream()
                .filter(port -> ZONE_ID.equals(port.zoneId()))
                .toList();
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
        if (isPortTunnel(position))
        {
            return AIR;
        }

        /*
         * null is deliberate. The bounded generator leaves this owner solid.
         * The private NBT loader clears only its exact transformed envelope,
         * then the measured presentation post-pass joins the legal ports.
         * No guessed furniture or shell may survive beside the authored room.
         */
        return null;
    }

    private boolean isPortTunnel(BlockPos position)
    {
        for (FacilitySchemaV2.PortSpec port : this.ports)
        {
            FacilitySchemaV2.IntBox aperture = port.aperture();
            FacilitySchemaV2.IntBox inner = aperture.offset(
                    -port.facing().getStepX(),
                    -port.facing().getStepY(),
                    -port.facing().getStepZ());
            if (contains(aperture, position) || contains(inner, position))
            {
                return true;
            }
        }
        return false;
    }

    private static boolean contains(FacilitySchemaV2.IntBox box,
                                    BlockPos position)
    {
        return position.getX() >= box.minX()
                && position.getX() < box.maxX()
                && position.getY() >= box.minY()
                && position.getY() < box.maxY()
                && position.getZ() >= box.minZ()
                && position.getZ() < box.maxZ();
    }
}
