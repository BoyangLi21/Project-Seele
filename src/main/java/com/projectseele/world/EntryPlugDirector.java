package com.projectseele.world;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.projectseele.ProjectSeele;
import com.projectseele.config.SeeleConfig;
import com.projectseele.entity.EntryPlugCarrierEntity;
import com.projectseele.entity.EvaScale;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.TrainingPilotEntity;
import com.projectseele.registry.ModEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/** Owns the external entry plug from the overhead rack to the dorsal socket. */
public final class EntryPlugDirector
{
    public static final int INSERTION_TICKS = 120;

    /** Ticks the crane takes to draw a seated capsule back out to its cage. */
    public static final int EJECTION_TICKS = 105;
    /** Pyrotechnic extraction, ballistic clearance and landing. */
    public static final int FIELD_EJECTION_TICKS = 70;
    private static final Map<ResourceKey<Level>, Map<Integer, UUID>>
            CACHED_PLUGS = new HashMap<>();
    /** Last crane frame drawn per cage, so identical ticks cost nothing. */
    private static final Map<Integer, Long> CRANE_SIGNATURE = new HashMap<>();

    private EntryPlugDirector() {}

    /**
     * Signed Z offset of the dorsal socket from the bed for an airframe parked
     * at {@link EvaUnit01Entity#SILO_BAY_YAW}. The hangar geometry gate reads
     * this rather than hard-coding which side the back is on: an earlier
     * revision asserted -Z and so certified a bridge built at the EVA's face.
     */
    public static double socketZOffset()
    {
        double yaw = Math.toRadians(EvaUnit01Entity.SILO_BAY_YAW);
        return -Math.cos(yaw)
                * EntryPlugKinematics.SOCKET_REAR_BLOCKS;
    }

    public static EntryPlugCarrierEntity ensureSuspended(
            ServerLevel level, int variant, EvaUnit01Entity unit)
    {
        EntryPlugCarrierEntity plug = canonical(level, variant);
        if (plug == null)
        {
            UUID savedId = savedPlugId(level, variant);
            if (savedId != null)
            {
                ProjectSeele.LOGGER.error(
                        "NERV entry-plug authority fault: EVA-0{} saved capsule {} cannot be resolved; replacement inhibited",
                        variant, savedId);
                return null;
            }
            if (unit.isEntryPlugInserted())
            {
                ProjectSeele.LOGGER.error(
                        "NERV entry-plug authority fault: EVA-0{} reports a seated capsule but its UUID cannot be resolved; replacement inhibited",
                        variant);
                return null;
            }
            plug = ModEntities.ENTRY_PLUG_CARRIER.get().create(level);
            if (plug == null)
            {
                return null;
            }
            plug.assignVariant(variant);
            plug.setPersistenceRequired();
            positionSuspended(plug, unit);
            if (!level.addFreshEntity(plug))
            {
                return null;
            }
            remember(level, variant, plug);
            ProjectSeele.LOGGER.info(
                    "NERV external entry plug suspended: eva={} plug={} pos={}",
                    variant, plug.getStringUUID(), plug.blockPosition().toShortString());
        }
        int stage = plug.getInsertionStage();
        if (stage != EntryPlugCarrierEntity.STAGE_INSERTING
                && stage != EntryPlugCarrierEntity.STAGE_EJECTING
                && stage != EntryPlugCarrierEntity.STAGE_FIELD_EJECTING
                && stage != EntryPlugCarrierEntity.STAGE_FIELD_LANDED
                && stage != EntryPlugCarrierEntity.STAGE_LOCKED
                && stage != EntryPlugCarrierEntity.STAGE_ABORT_RETURNING
                && stage != EntryPlugCarrierEntity.STAGE_ABORT_DOCKED)
        {
            RigidTransform wanted = cageDockTransform(unit);
            // A suspended capsule is cage hardware, not a child of the EVA's
            // live look direction. Re-solving its quaternion from the unit on
            // every logistics tick made it visibly oscillate while parked.
            if (!plug.hasCanonicalPose()
                    || plug.position().distanceToSqr(wanted.translation())
                            > 1.0E-4D
                    || plug.getCanonicalTransform()
                            .rotationErrorDegrees(wanted) > 0.1D)
            {
                plug.setCanonicalTransform(wanted);
            }
            if (plug.getInsertionProgress() != 0)
            {
                plug.setInsertionProgress(0);
            }
            int wantedStage = plug.isVehicle()
                    ? EntryPlugCarrierEntity.STAGE_OCCUPIED
                    : EntryPlugCarrierEntity.STAGE_SUSPENDED;
            if (plug.getInsertionStage() != wantedStage)
            {
                if (!plug.transitionInsertionStage(stage,
                        plug.getInsertionEpoch(), wantedStage))
                {
                    ProjectSeele.LOGGER.error(
                            "NERV entry-plug dock reconciliation refused illegal stage edge: eva={} from={} to={} epoch={}",
                            variant, stage, wantedStage,
                            plug.getInsertionEpoch());
                    return plug;
                }
            }
            Vec3 craneEye = plug.transformPlugMarker(
                    EntryPlugKinematics.CRANE_ATTACHMENT_P);
            updateCables(level, variant, craneEye.y, craneEye.z, false);
        }
        return plug;
    }

    public static EntryPlugCarrierEntity canonical(ServerLevel level,
                                                    int variant)
    {
        Map<Integer, UUID> dimensionCache = CACHED_PLUGS.computeIfAbsent(
                level.dimension(), ignored -> new HashMap<>());
        UUID savedId = savedPlugId(level, variant);
        if (savedId != null)
        {
            Entity saved = level.getEntity(savedId);
            if (saved instanceof EntryPlugCarrierEntity plug
                    && plug.isAlive()
                    && plug.getAssignedVariant() == variant)
            {
                dimensionCache.put(variant, savedId);
                return plug;
            }
            /*
             * A persisted identity is stronger than a nearby cosmetic shell.
             * Its chunk is forced by an active logistics phase; until it is
             * available we fail closed instead of silently swapping capsules.
             */
            return null;
        }
        UUID cachedId = dimensionCache.get(variant);
        if (cachedId != null)
        {
            Entity cached = level.getEntity(cachedId);
            if (cached instanceof EntryPlugCarrierEntity plug
                    && plug.isAlive() && plug.getAssignedVariant() == variant)
            {
                return plug;
            }
            dimensionCache.remove(variant);
        }

        // Reload recovery: a seated plug may be hundreds of blocks from its
        // wet cage. Scan loaded entities only on a cache miss, then retain the
        // UUID so normal ticks return in O(1).
        for (Entity entity : level.getAllEntities())
        {
            if (entity instanceof EntryPlugCarrierEntity plug
                    && plug.isAlive()
                    && plug.getAssignedVariant() == variant
                    && plug.isLockedToEva())
            {
                remember(level, variant, plug);
                return plug;
            }
        }

        // A PARKED/INSERTING plug never leaves its assigned wet cage. A local
        // section query avoids scanning every entity in the 640-block cavern
        // three times per server tick.
        net.minecraft.core.BlockPos bed = hangarBed(level, variant);
        AABB search = new AABB(bed).inflate(32.0D, 64.0D, 48.0D);
        List<EntryPlugCarrierEntity> matches = new ArrayList<>(
                level.getEntitiesOfClass(EntryPlugCarrierEntity.class, search,
                        plug -> plug.isAlive()
                                && plug.getAssignedVariant() == variant));
        if (matches.isEmpty())
        {
            return null;
        }
        /*
         * Never let UUID ordering choose an empty cosmetic shell over the
         * capsule that already contains the pilot or is midway through the
         * mechanical sequence.  That old tie-break was the source of several
         * "prepare did nothing" reports after a reload.
         */
        matches.sort(Comparator
                .comparingInt(EntryPlugDirector::canonicalPriority)
                .thenComparingDouble(plug ->
                        plug.position().distanceToSqr(
                                plugRestPosition(level, variant)))
                .thenComparing(Entity::getUUID));
        EntryPlugCarrierEntity keep = matches.get(0);
        for (int index = 1; index < matches.size(); index++)
        {
            EntryPlugCarrierEntity duplicate = matches.get(index);
            for (Entity passenger : List.copyOf(duplicate.getPassengers()))
            {
                passenger.stopRiding();
                keep.boardPassenger(passenger);
            }
            duplicate.discard();
        }
        remember(level, variant, keep);
        return keep;
    }

    private static int canonicalPriority(EntryPlugCarrierEntity plug)
    {
        if (plug.isLockedToEva()
                || plug.getInsertionStage()
                        == EntryPlugCarrierEntity.STAGE_LOCKED)
        {
            return 0;
        }
        if (plug.isVehicle() || !plug.getPassengers().isEmpty())
        {
            return 1;
        }
        int stage = plug.getInsertionStage();
        if (stage == EntryPlugCarrierEntity.STAGE_INSERTING
                || stage == EntryPlugCarrierEntity.STAGE_EJECTING
                || stage == EntryPlugCarrierEntity.STAGE_FIELD_EJECTING
                || stage == EntryPlugCarrierEntity.STAGE_FIELD_LANDED)
        {
            return 2;
        }
        return 3;
    }

    public static void resetRuntime()
    {
        CACHED_PLUGS.clear();
        CRANE_SIGNATURE.clear();
        FacilityV2EvaRuntime.resetRuntime();
    }

    /**
     * Discards entry-plug carriers stranded away from their cage crane.
     *
     * <p>An earlier revision derived the suspended plug's rest point from the
     * airframe, so a deployed unit dragged a phantom capsule hundreds of blocks
     * up into the Tokyo-3 sky. Those persistent strays outlive the code fix;
     * this removes any empty carrier sitting far from its own wet cage, leaving
     * the single canonical plug {@link #canonical} maintains. A carrier that
     * still holds a pilot is left alone so nobody is discarded mid-flight.
     *
     * @return how many stray carriers were removed.
     */
    public static int sweepStrayPlugs(ServerLevel level)
    {
        int removed = 0;
        // Entry plugs are intentionally unique (one per EVA), so iterating the
        // already-loaded entity list is much cheaper and more reliable than a
        // huge AABB. It also reaches both the old phantom capsules above
        // Tokyo-3 and the same-position duplicates left in each wet cage.
        for (int variant = 0; variant < 3; variant++)
        {
            UUID savedId = savedPlugId(level, variant);
            List<EntryPlugCarrierEntity> candidates = new ArrayList<>();
            EntryPlugCarrierEntity saved = null;
            Vec3 rest = plugRestPosition(level, variant);
            for (Entity entity : level.getAllEntities())
            {
                if (!(entity instanceof EntryPlugCarrierEntity plug)
                        || !plug.isAlive()
                        || plug.getAssignedVariant() != variant)
                {
                    continue;
                }
                candidates.add(plug);
                if (plug.getUUID().equals(savedId))
                {
                    saved = plug;
                }
            }
            if (candidates.isEmpty())
            {
                continue;
            }
            /*
             * A saved identity that is merely in an unloaded chunk remains
             * authoritative.  Never replace it with a cosmetic cage shell.
             */
            if (savedId != null && saved == null)
            {
                continue;
            }
            candidates.sort(Comparator
                    .comparingInt(EntryPlugDirector::canonicalPriority)
                    .thenComparingInt(plug -> plug.getUUID().equals(savedId)
                            ? 0 : 1)
                    .thenComparingDouble(plug ->
                            plug.position().distanceToSqr(rest))
                    .thenComparing(Entity::getUUID));
            EntryPlugCarrierEntity keep = candidates.get(0);
            for (int index = 1; index < candidates.size(); index++)
            {
                EntryPlugCarrierEntity duplicate = candidates.get(index);
                for (Entity passenger
                        : List.copyOf(duplicate.getPassengers()))
                {
                    passenger.stopRiding();
                    keep.boardPassenger(passenger);
                }
                duplicate.discard();
                removed++;
            }
            remember(level, variant, keep);
        }
        if (removed > 0)
        {
            ProjectSeele.LOGGER.info(
                    "NERV swept {} stray entry-plug carrier(s) in {}",
                    removed, level.dimension().location());
        }
        return removed;
    }

    /** Seals the boarded capsule and starts its local PREPARE sequence. */
    public static void beginCabinPreparation(ServerLevel level, int variant,
                                             EvaUnit01Entity unit)
    {
        EntryPlugCarrierEntity plug = ensureSuspended(level, variant, unit);
        if (plug != null)
        {
            plug.beginCabinPreparation();
        }
    }

    /**
     * PREPARE starts while the split boarding bridge retracts. Run the first
     * thirty percent of the continuous sequence here so LCL is already rising
     * before the crane moves.
     */
    public static void tickCabinPreparation(ServerLevel level, int variant,
                                            EvaUnit01Entity unit, int ticks,
                                            int totalTicks)
    {
        // PREPARE owns the exact occupied capsule that requestPrepare
        // authenticated. Never manufacture a replacement midway through the
        // sealed-cabin sequence if that entity temporarily cannot be resolved.
        EntryPlugCarrierEntity plug = canonical(level, variant);
        if (plug == null || !plug.isVehicle())
        {
            return;
        }
        if (!plug.isHatchFullySealed())
        {
            plug.setCabinSequenceProgress(0);
            return;
        }
        int preparationTicks = Math.max(1,
                ticks - EntryPlugCarrierEntity.HATCH_SEAL_TICKS + 1);
        int preparationWindow = Math.max(1,
                totalTicks - EntryPlugCarrierEntity.HATCH_SEAL_TICKS + 1);
        int progress = Mth.clamp((int) Math.round(
                30.0D * preparationTicks / preparationWindow), 1, 30);
        plug.setCabinSequenceProgress(progress);
    }

    public static boolean hasBoardedPilot(ServerLevel level, int variant,
                                          EvaUnit01Entity unit)
    {
        if (isSupportedPilot(unit.getPilotEntity()))
        {
            return true;
        }
        EntryPlugCarrierEntity plug = canonical(level, variant);
        if (plug != null && isSupportedPilot(plug.getFirstPassenger()))
        {
            return true;
        }
        // Save-upgrade recovery: a player may already be riding the visible
        // capsule from before boarding began claiming fleet authority. Adopt
        // that exact occupied entity instead of asking the player to dismount
        // and repeat the interaction.
        for (Entity entity : level.getAllEntities())
        {
            if (entity instanceof EntryPlugCarrierEntity occupied
                    && occupied.isAlive()
                    && occupied.getAssignedVariant() == variant
                    && isSupportedPilot(occupied.getFirstPassenger()))
            {
                claimBoardedPlug(level, occupied);
                return true;
            }
        }
        return false;
    }

    /**
     * Makes the capsule a real player just boarded the fleet authority.
     *
     * <p>Old saves can retain an empty duplicate whose UUID still sits in
     * fleet data.  Rendering and interaction then target the visible capsule,
     * while PREPARE resolves the stale empty one and reports no pilot.  The
     * successful server-side ride operation is the strongest possible proof
     * of identity, so claim it immediately and remove only an empty, idle
     * duplicate of the same EVA.</p>
     */
    public static void claimBoardedPlug(ServerLevel level,
                                        EntryPlugCarrierEntity boarded)
    {
        int variant = boarded.getAssignedVariant();
        EntryPlugCarrierEntity former = canonical(level, variant);
        if (former != null && former != boarded
                && !former.isVehicle()
                && former.getInsertionStage()
                        == EntryPlugCarrierEntity.STAGE_SUSPENDED)
        {
            former.discard();
        }
        remember(level, variant, boarded);
        ProjectSeele.LOGGER.info(
                "NERV entry-plug pilot authority claimed: eva={} plug={} pilot={}",
                variant, boarded.getStringUUID(),
                boarded.getFirstPassenger() == null ? "none"
                        : boarded.getFirstPassenger().getStringUUID());
    }

    public static boolean beginInsertion(ServerLevel level, int variant,
                                         EvaUnit01Entity unit)
    {
        EntryPlugCarrierEntity plug = canonical(level, variant);
        if (plug == null || !plug.isVehicle()
                || !plug.isHatchFullySealed()
                || plug.getCabinProgress() < 30
                || plug.getCabinStage()
                        < EntryPlugCarrierEntity.CABIN_LCL_FILLING)
        {
            return false;
        }
        RigidTransform dock = cageDockTransform(unit);
        RigidTransform actual = plug.getCanonicalTransform();
        if (actual.translation().distanceToSqr(dock.translation())
                > 1.0D / (1024.0D * 1024.0D)
                || actual.rotationErrorDegrees(dock) > 0.1D)
        {
            ProjectSeele.LOGGER.error(
                    "NERV entry-plug dock-pose interlock refused EVA-0{} insertion",
                    variant);
            return false;
        }
        if (!insertionRouteClear(level, unit, plug, dock))
        {
            ProjectSeele.LOGGER.error(
                    "NERV entry-plug full-route interlock refused EVA-0{} insertion",
                    variant);
            return false;
        }
        if (!plug.transitionInsertionStage(
                EntryPlugCarrierEntity.STAGE_OCCUPIED,
                EntryPlugCarrierEntity.STAGE_INSERTING))
        {
            ProjectSeele.LOGGER.error(
                    "NERV entry-plug insertion authority refused stale EVA-0{} stage={} epoch={}",
                    variant, plug.getInsertionStage(),
                    plug.getInsertionEpoch());
            return false;
        }
        plug.clearInsertionAbortRequest();
        plug.setInsertionProgress(0);
        plug.setCabinSequenceProgress(Math.max(30,
                plug.getCabinProgress()));
        return true;
    }

    /** Returns true only after the same occupied capsule is locked in the EVA. */
    public static boolean tickInsertion(ServerLevel level, int variant,
                                        EvaUnit01Entity unit, int ticks)
    {
        EntryPlugCarrierEntity plug = canonical(level, variant);
        if (plug == null)
        {
            ProjectSeele.LOGGER.error(
                    "NERV entry-plug insertion authority fault: EVA-0{} capsule vanished at tick {}; replacement inhibited",
                    variant, ticks);
            return false;
        }
        if (plug.getInsertionStage()
                != EntryPlugCarrierEntity.STAGE_INSERTING
                || plug.isInsertionAbortRequested()
                || !isSupportedPilot(plug.getFirstPassenger()))
        {
            return false;
        }
        double linear = Mth.clamp(ticks / (double) INSERTION_TICKS,
                0.0D, 1.0D);
        RigidTransform pose = EntryPlugKinematics.insertionTransform(
                unit, cageDockTransform(unit), linear);
        RigidTransform previous = plug.getCanonicalTransform();
        if (!insertionSweepClear(level, unit, plug, previous, pose))
        {
            if (!plug.transitionInsertionStage(
                    EntryPlugCarrierEntity.STAGE_INSERTING,
                    EntryPlugCarrierEntity.STAGE_ABORT_RETURNING))
            {
                return false;
            }
            plug.sealCabin();
            ProjectSeele.LOGGER.error(
                    "NERV entry-plug swept-clearance interlock: EVA-0{} halted at {}% and will return to dock",
                    variant, plug.getInsertionProgress());
            return false;
        }
        plug.setCanonicalTransform(pose);
        plug.setInsertionProgress((int) Math.round(linear * 100.0D));
        plug.setCabinSequenceProgress(30 + (int) Math.round(linear
                * (EntryPlugCarrierEntity.CABIN_TRANSFER_PERCENT - 30)));
        Vec3 craneEye = pose.transformPoint(
                EntryPlugKinematics.CRANE_ATTACHMENT_P);
        updateCables(level, variant, craneEye.y,
                craneEye.z, true);
        if (ticks < INSERTION_TICKS)
        {
            return false;
        }

        Entity passenger = plug.getFirstPassenger();
        if (!isSupportedPilot(passenger))
        {
            ProjectSeele.LOGGER.warn(
                    "NERV entry plug insertion aborted without pilot: eva={} plug={}",
                    variant, plug.getStringUUID());
            return false;
        }
        int cabinProgress = plug.getCabinProgress();
        if (!plug.lockToEva(unit))
        {
            ProjectSeele.LOGGER.error(
                    "NERV entry plug could not establish nested ride chain: eva={} plug={}",
                    variant, plug.getStringUUID());
            return false;
        }
        if (!unit.bindEntryPlug(plug, cabinProgress))
        {
            plug.unlockFromEva();
            plug.transitionInsertionStage(
                    EntryPlugCarrierEntity.STAGE_LOCKED,
                    EntryPlugCarrierEntity.STAGE_INSERTING);
            ProjectSeele.LOGGER.error(
                    "NERV EVA rejected persistent entry-plug link: eva={} plug={}",
                    variant, plug.getStringUUID());
            return false;
        }
        ProjectSeele.LOGGER.info(
                "NERV entry plug seated: eva={} plug={} passenger={}",
                variant, plug.getStringUUID(), passenger.getStringUUID());
        remember(level, variant, plug);
        stowCrane(level, variant);
        return true;
    }

    /**
     * The capsule is no-physics for deterministic crane motion, therefore the
     * director must explicitly perform the collision interlock before moving
     * it. The host EVA and seated pilot are the only authored overlaps.
     */
    private static boolean insertionSweepClear(ServerLevel level,
                                                EvaUnit01Entity unit,
                                                EntryPlugCarrierEntity plug,
                                                RigidTransform previous,
                                                RigidTransform next)
    {
        /*
         * The suspended capsule legitimately overlaps its fixed dock collar.
         * Testing the union of the old and new bounds therefore rejected every
         * insertion forever: the union still contained the collar even while
         * the plug was moving away from it. Sample the actual motion instead
         * and reject only collision volume that increases. Existing dock
         * overlap may shrink, but the capsule may never enter a new solid.
         */
        AABB priorBounds = EntryPlugKinematics.worldBounds(previous,
                EntryPlugKinematics.BODY_OBB_CENTRE_P,
                EntryPlugKinematics.BODY_OBB_HALF_EXTENTS).deflate(0.04D);
        for (int sample = 1; sample <= 4; sample++)
        {
            RigidTransform pose = previous.interpolate(next,
                    sample / 4.0D);
            AABB currentBounds = EntryPlugKinematics.worldBounds(pose,
                    EntryPlugKinematics.BODY_OBB_CENTRE_P,
                    EntryPlugKinematics.BODY_OBB_HALF_EXTENTS).deflate(0.04D);
            if (!blockMotionClear(level, plug.getAssignedVariant(),
                    priorBounds, currentBounds))
            {
                return false;
            }
            if (!level.getEntities(plug, currentBounds, entity ->
                    entity.isAlive() && entity != unit
                            && !plug.hasPassenger(entity)
                            && entity.isPickable()).isEmpty())
            {
                return false;
            }
            priorBounds = currentBounds;
        }
        return true;
    }

    private static boolean blockMotionClear(ServerLevel level, int variant,
                                            AABB previous,
                                            AABB current)
    {
        BlockPos min = BlockPos.containing(current.minX, current.minY,
                current.minZ);
        BlockPos max = BlockPos.containing(current.maxX, current.maxY,
                current.maxZ);
        for (BlockPos position : BlockPos.betweenClosed(min, max))
        {
            // The active trolley/yoke/collar is the mechanism carrying this
            // capsule and is repositioned immediately after the accepted
            // motion step. It must not interlock against itself.
            if (EvaHangarBuilder.isActivePlugCraneCell(variant, position))
            {
                continue;
            }
            BlockState state = level.getBlockState(position);
            if (state.getCollisionShape(level, position).isEmpty())
            {
                continue;
            }
            for (AABB local : state.getCollisionShape(level, position)
                    .toAabbs())
            {
                AABB solid = local.move(position);
                double before = intersectionVolume(previous, solid);
                double after = intersectionVolume(current, solid);
                if (after > before + 1.0E-4D)
                {
                    ProjectSeele.LOGGER.error(
                            "NERV entry-plug route obstruction at {} block={} overlap {} -> {}",
                            position.toShortString(), state.getBlock(),
                            before, after);
                    return false;
                }
            }
        }
        return true;
    }

    private static double intersectionVolume(AABB first, AABB second)
    {
        double x = Math.max(0.0D,
                Math.min(first.maxX, second.maxX)
                        - Math.max(first.minX, second.minX));
        double y = Math.max(0.0D,
                Math.min(first.maxY, second.maxY)
                        - Math.max(first.minY, second.minY));
        double z = Math.max(0.0D,
                Math.min(first.maxZ, second.maxZ)
                        - Math.max(first.minZ, second.minZ));
        return x * y * z;
    }

    /**
     * Checks the complete authored route before the crane leaves its brake.
     * Per-tick swept checks remain active as a second interlock for entities
     * entering the volume after PREPARE.
     */
    private static boolean insertionRouteClear(ServerLevel level,
                                                EvaUnit01Entity unit,
                                                EntryPlugCarrierEntity plug,
                                                RigidTransform dock)
    {
        RigidTransform previous = dock;
        for (int sample = 1; sample <= 24; sample++)
        {
            RigidTransform next = EntryPlugKinematics.insertionTransform(
                    unit, dock, sample / 24.0D);
            if (!insertionSweepClear(level, unit, plug, previous, next))
            {
                return false;
            }
            previous = next;
        }
        return true;
    }

    /**
     * True only while the SavedData-authoritative occupied capsule owns the
     * complete EVA -> plug -> pilot launch chain at the reviewed socket pose.
     *
     * <p>The mechanical lock pause is not merely a timer. A reload, passenger
     * dismount or rejected nested ride during that pause must stop the cage
     * drain instead of sending an empty airframe to the launch silo.</p>
     */
    public static boolean hasLaunchLock(ServerLevel level, int variant,
                                        EvaUnit01Entity unit)
    {
        EntryPlugCarrierEntity plug = canonical(level, variant);
        UUID saved = savedPlugId(level, variant);
        if (plug == null || saved == null || !saved.equals(plug.getUUID())
                || plug.getAssignedVariant() != variant
                || plug.getInsertionStage()
                        != EntryPlugCarrierEntity.STAGE_LOCKED
                || plug.getInsertionProgress() != 100
                || plug.getVehicle() != unit
                || plug.getLinkedEva() != unit
                || !unit.getUUID().equals(plug.getHostEvaUuid())
                || unit.getLockedEntryPlug() != plug
                || !unit.isEntryPlugInserted()
                || !isSupportedPilot(plug.getFirstPassenger())
                || !plug.isHatchFullySealed())
        {
            return false;
        }
        RigidTransform expected = EntryPlugKinematics.lockedTransform(unit);
        RigidTransform actual = plug.getCanonicalTransform();
        return actual.translation().distanceToSqr(expected.translation())
                <= 0.04D
                && actual.rotationErrorDegrees(expected) <= 0.5D;
    }

    /**
     * Rewinds a failed PREPARE to the crane dock without changing capsule
     * identity. An occupied capsule remains sealed and keeps its pilot; an
     * empty capsule reopens for boarding.
     */
    public static boolean abortInsertionToDock(ServerLevel level, int variant,
                                               EvaUnit01Entity unit)
    {
        EntryPlugCarrierEntity plug = canonical(level, variant);
        if (plug == null)
        {
            ProjectSeele.LOGGER.error(
                    "NERV entry-plug rollback inhibited: EVA-0{} canonical capsule is unavailable",
                    variant);
            return false;
        }
        int stage = plug.getInsertionStage();
        if (stage == EntryPlugCarrierEntity.STAGE_ABORT_RETURNING)
        {
            return true;
        }
        if (stage != EntryPlugCarrierEntity.STAGE_INSERTING
                && stage != EntryPlugCarrierEntity.STAGE_LOCKED)
        {
            return false;
        }
        if (!plug.transitionInsertionStage(stage,
                EntryPlugCarrierEntity.STAGE_ABORT_RETURNING))
        {
            return false;
        }
        if (plug.getLinkedEva() == unit
                || plug.getVehicle() instanceof EvaUnit01Entity)
        {
            plug.unlockFromEva();
        }
        plug.clearInsertionAbortRequest();
        plug.sealCabin();
        remember(level, variant, plug);
        return true;
    }

    /**
     * Brakes a failed insertion and returns the same capsule along the exact
     * authored curve.  No teleport, replacement capsule or open hatch is
     * permitted inside the crane/EVA sweep volume.
     */
    public static boolean tickAbortReturn(ServerLevel level, int variant,
                                          EvaUnit01Entity unit,
                                          int abortTicks)
    {
        EntryPlugCarrierEntity plug = canonical(level, variant);
        if (plug == null)
        {
            return false;
        }
        if (plug.getInsertionStage()
                != EntryPlugCarrierEntity.STAGE_ABORT_RETURNING)
        {
            return false;
        }
        // Six ticks of physical braking prevent an insertion moving at +1%
        // per tick from reversing direction discontinuously on the first
        // abort frame.  The same persistent transform is held meanwhile.
        int progress = plug.getInsertionProgress();
        if (abortTicks > 6)
        {
            progress = Math.max(0, progress - 1);
        }
        double linear = progress / 100.0D;
        RigidTransform pose = EntryPlugKinematics.insertionTransform(
                unit, cageDockTransform(unit), linear);
        plug.setCanonicalTransform(pose);
        plug.setInsertionProgress(progress);
        Vec3 craneEye = pose.transformPoint(
                EntryPlugKinematics.CRANE_ATTACHMENT_P);
        updateCables(level, variant, craneEye.y, craneEye.z, true);
        if (progress > 0)
        {
            return false;
        }

        positionSuspended(plug, unit);
        plug.setCabinSequenceProgress(0);
        // The capsule is physically home, but the access bridge still occupies
        // its retracted state.  Keep a distinct sealed docking state until the
        // logistics authority proves the bridge fully extended.
        if (!plug.transitionInsertionStage(
                EntryPlugCarrierEntity.STAGE_ABORT_RETURNING,
                EntryPlugCarrierEntity.STAGE_ABORT_DOCKED))
        {
            return false;
        }
        plug.sealCabin();
        remember(level, variant, plug);
        return true;
    }

    /** Releases a returned capsule only after the boarding bridge is safe. */
    public static boolean completeAbortDocking(ServerLevel level, int variant,
                                               EvaUnit01Entity unit)
    {
        EntryPlugCarrierEntity plug = canonical(level, variant);
        if (plug == null || plug.getInsertionStage()
                != EntryPlugCarrierEntity.STAGE_ABORT_DOCKED
                || plug.getInsertionProgress() != 0)
        {
            return false;
        }
        RigidTransform expected = cageDockTransform(unit);
        RigidTransform actual = plug.getCanonicalTransform();
        if (actual.translation().distanceToSqr(expected.translation())
                > 1.0D / (1024.0D * 1024.0D)
                || actual.rotationErrorDegrees(expected) > 0.1D)
        {
            return false;
        }
        plug.setCabinSequenceProgress(0);
        plug.clearInsertionAbortRequest();
        if (plug.isVehicle())
        {
            if (!plug.transitionInsertionStage(
                    EntryPlugCarrierEntity.STAGE_ABORT_DOCKED,
                    EntryPlugCarrierEntity.STAGE_OCCUPIED))
            {
                return false;
            }
            plug.sealCabin();
        }
        else
        {
            if (!plug.transitionInsertionStage(
                    EntryPlugCarrierEntity.STAGE_ABORT_DOCKED,
                    EntryPlugCarrierEntity.STAGE_SUSPENDED))
            {
                return false;
            }
            plug.openCabin();
        }
        remember(level, variant, plug);
        return true;
    }

    /**
     * On exit, extracts the same persistent capsule from the dorsal socket, so
     * the pilot remains inside one physical entry plug for the full sortie.
     * The suspended plug was consumed on insertion, so a fresh one is spawned
     * for the ejection — this is not the "don't spawn a second plug for
     * insertion" case.
     */
    public static boolean ejectPilotToPlug(ServerLevel level, int variant,
                                           EvaUnit01Entity unit,
                                           LivingEntity pilot)
    {
        if (level.isClientSide)
        {
            return false;
        }
        boolean inHangar = isInsideAssignedCage(level, unit, variant);
        Vec3 socket = unit.getEntryPlugSocketPosition();
        Vec3 outward = unit.getForward()
                .multiply(-1.0D, 0.0D, -1.0D).normalize();
        if (outward.lengthSqr() < 1.0E-4D)
        {
            outward = new Vec3(0.0D, 0.0D, 1.0D);
        }
        RigidTransform seated = EntryPlugKinematics.lockedTransform(unit);
        // Reuse this cage's plug. The logistics tick re-suspends a capsule as
        // soon as the previous one is consumed, so spawning a second here left
        // two plugs in the cage — and made canonical() pick the one the pilot
        // was not in, which is why a later prepare refused to start.
        EntryPlugCarrierEntity plug =
                pilot.getVehicle() instanceof EntryPlugCarrierEntity ridden
                        && ridden.getLinkedEva() == unit
                        ? ridden : unit.getLockedEntryPlug();
        if (plug == null)
        {
            plug = canonical(level, variant);
        }
        if (plug == null)
        {
            ProjectSeele.LOGGER.error(
                    "NERV entry-plug ejection inhibited: EVA-0{} has no resolvable canonical capsule; replacement inhibited",
                    variant);
            return false;
        }
        if (plug.getLinkedEva() == unit)
        {
            plug.unlockFromEva();
        }
        plug.setCanonicalTransform(seated);
        if (pilot.getVehicle() != plug)
        {
            pilot.stopRiding();
            if (plug.isVehicle() || !plug.boardPassenger(pilot))
            {
                ProjectSeele.LOGGER.error(
                        "NERV entry-plug extraction refused occupied capsule: eva={} plug={}",
                        unit.getStringUUID(), plug.getStringUUID());
                return false;
            }
        }
        if (inHangar)
        {
            // Play the insertion path backwards under the wet-cage hoist.
            if (!plug.transitionInsertionStage(
                    EntryPlugCarrierEntity.STAGE_LOCKED,
                    plug.getInsertionEpoch(),
                    EntryPlugCarrierEntity.STAGE_EJECTING))
            {
                ProjectSeele.LOGGER.error(
                        "NERV wet-cage extraction rejected stale plug stage: eva={} plug={} stage={} epoch={}",
                        variant, plug.getStringUUID(),
                        plug.getInsertionStage(), plug.getInsertionEpoch());
                return false;
            }
            plug.setInsertionProgress(100);
            remember(level, variant, plug);
            level.playSound(null, plug.blockPosition(),
                    SoundEvents.PISTON_EXTEND, SoundSource.BLOCKS,
                    2.4F, 0.58F);
            ProjectSeele.LOGGER.info(
                    "NERV wet-cage entry plug extraction started: eva={} plug={} pilot={}",
                    variant, plug.getStringUUID(), pilot.getStringUUID());
        }
        else
        {
            Vec3 mouth = socket.add(outward.scale(
                            EvaScale.ENTRY_PLUG_LENGTH * 0.54D))
                    .add(0.0D, EvaScale.ENTRY_PLUG_LENGTH * 0.12D, 0.0D);
            Vec3 escape = mouth.add(outward.scale(12.0D))
                    .add(0.0D, 9.0D, 0.0D);
            Vec3 landingProbe = unit.position().add(outward.scale(
                    EvaScale.ENTRY_PLUG_LENGTH + 12.0D));
            Vec3 landing = findFieldLanding(level, landingProbe, unit.getY());
            if (!plug.beginFieldEjection(
                    seated.translation(), escape, landing))
            {
                ProjectSeele.LOGGER.error(
                        "NERV field ejection rejected stale plug stage: eva={} plug={} stage={} epoch={}",
                        variant, plug.getStringUUID(),
                        plug.getInsertionStage(), plug.getInsertionEpoch());
                return false;
            }
            level.playSound(null, plug.blockPosition(),
                    SoundEvents.GENERIC_EXPLODE, SoundSource.BLOCKS,
                    3.4F, 1.28F);
            level.sendParticles(ParticleTypes.EXPLOSION,
                    socket.x, socket.y, socket.z, 8,
                    1.4D, 1.4D, 1.4D, 0.08D);
            ProjectSeele.LOGGER.info(
                    "NERV field entry plug emergency ejection started: eva={} plug={} pilot={} landing={}",
                    variant, plug.getStringUUID(), pilot.getStringUUID(),
                    BlockPos.containing(landing).toShortString());
        }
        return true;
    }

    /**
     * Withdraws a seated capsule to its cage: the insertion path played back.
     * The pilot rides it out, so they leave inside the plug and then climb down
     * from it at the boarding deck instead of being dropped at the EVA's feet.
     */
    public static void tickEjection(EntryPlugCarrierEntity plug, int ticks)
    {
        if (!(plug.level() instanceof ServerLevel level))
        {
            return;
        }
        int variant = plug.getAssignedVariant();
        EvaUnit01Entity unit = EvaLogisticsDirector.canonicalUnit(level, variant);
        Vec3 rest = plugRestPosition(level, variant);
        double linear = Mth.clamp(ticks / (double) EJECTION_TICKS, 0.0D, 1.0D);
        if (unit == null)
        {
            return;
        }
        RigidTransform pose = EntryPlugKinematics.insertionTransform(
                unit, EntryPlugKinematics.cageDockTransform(rest),
                1.0D - linear);
        plug.setCanonicalTransform(pose);
        plug.setInsertionProgress((int) Math.round((1.0D - linear) * 100.0D));
        Vec3 craneEye = pose.transformPoint(
                EntryPlugKinematics.CRANE_ATTACHMENT_P);
        updateCables(level, variant, craneEye.y, craneEye.z, true);
        if (linear >= 1.0D)
        {
            int nextStage = plug.isVehicle()
                    ? EntryPlugCarrierEntity.STAGE_OCCUPIED
                    : EntryPlugCarrierEntity.STAGE_SUSPENDED;
            if (!plug.transitionInsertionStage(
                    EntryPlugCarrierEntity.STAGE_EJECTING,
                    plug.getInsertionEpoch(), nextStage))
            {
                ProjectSeele.LOGGER.error(
                        "NERV wet-cage extraction completion rejected stale plug stage: eva={} plug={} stage={} epoch={}",
                        variant, plug.getStringUUID(),
                        plug.getInsertionStage(), plug.getInsertionEpoch());
                return;
            }
            plug.setInsertionProgress(0);
            level.playSound(null, plug.blockPosition(),
                    SoundEvents.IRON_TRAPDOOR_OPEN, SoundSource.BLOCKS,
                    1.6F, 0.7F);
        }
    }

    /**
     * Throws an occupied emergency capsule clear of the airframe and down a
     * deterministic landing arc. The landed capsule remains in the world and
     * is never registered as the wet cage's canonical spare.
     */
    public static void tickFieldEjection(EntryPlugCarrierEntity plug, int ticks)
    {
        if (!(plug.level() instanceof ServerLevel level))
        {
            return;
        }
        double linear = Mth.clamp(
                ticks / (double) FIELD_EJECTION_TICKS, 0.0D, 1.0D);
        Vec3 start = plug.getFieldEjectionStart();
        Vec3 escape = plug.getFieldEjectionEscape();
        Vec3 landing = plug.getFieldEjectionLanding();
        Vec3 position;
        if (linear <= 0.38D)
        {
            double phase = smoothstep(linear / 0.38D);
            position = start.lerp(escape, phase);
        }
        else
        {
            double phase = smoothstep((linear - 0.38D) / 0.62D);
            position = escape.lerp(landing, phase)
                    .add(0.0D, Math.sin(Math.PI * phase) * 8.0D, 0.0D);
        }
        RigidTransform current = plug.getCanonicalTransform();
        plug.setCanonicalTransform(new RigidTransform(position,
                current.qx(), current.qy(), current.qz(), current.qw()));
        plug.setInsertionProgress(
                (int) Math.round((1.0D - linear) * 100.0D));
        if (ticks % 3 == 0)
        {
            level.sendParticles(ParticleTypes.CLOUD,
                    position.x, position.y, position.z, 4,
                    0.55D, 0.35D, 0.55D, 0.02D);
            level.sendParticles(ParticleTypes.ELECTRIC_SPARK,
                    position.x, position.y, position.z, 3,
                    0.45D, 0.25D, 0.45D, 0.08D);
        }
        if (linear < 1.0D)
        {
            return;
        }

        RigidTransform landedRotation = plug.getCanonicalTransform();
        plug.setCanonicalTransform(new RigidTransform(landing,
                landedRotation.qx(), landedRotation.qy(),
                landedRotation.qz(), landedRotation.qw()));
        plug.setInsertionProgress(0);
        if (!plug.transitionInsertionStage(
                EntryPlugCarrierEntity.STAGE_FIELD_EJECTING,
                plug.getInsertionEpoch(),
                EntryPlugCarrierEntity.STAGE_FIELD_LANDED))
        {
            ProjectSeele.LOGGER.error(
                    "NERV field ejection landing rejected stale plug stage: eva={} plug={} stage={} epoch={}",
                    plug.getAssignedVariant(), plug.getStringUUID(),
                    plug.getInsertionStage(), plug.getInsertionEpoch());
            return;
        }
        Entity passenger = plug.getFirstPassenger();
        if (passenger instanceof Player pilot)
        {
            pilot.stopRiding();
            pilot.setHealth(Math.max(1.0F,
                    pilot.getHealth() - pilot.getMaxHealth() * 0.5F));
            pilot.displayClientMessage(Component.translatable(
                    "message.projectseele.field_ejection_landed"), true);
        }
        level.playSound(null, plug.blockPosition(),
                SoundEvents.GENERIC_EXPLODE, SoundSource.BLOCKS,
                2.8F, 0.72F);
        level.sendParticles(ParticleTypes.CLOUD,
                landing.x, landing.y, landing.z, 28,
                2.6D, 0.6D, 2.6D, 0.12D);
        ProjectSeele.LOGGER.info(
                "NERV field entry plug landed: eva={} plug={} pilot={} remainingHealth={}",
                plug.getAssignedVariant(), plug.getStringUUID(),
                passenger == null ? "none" : passenger.getStringUUID(),
                passenger instanceof Player player
                        ? String.format("%.1f", player.getHealth()) : "n/a");
    }

    public static void reset(ServerLevel level, int variant,
                             EvaUnit01Entity unit)
    {
        EntryPlugCarrierEntity plug = canonical(level, variant);
        if (plug != null)
        {
            for (Entity passenger : List.copyOf(plug.getPassengers()))
            {
                passenger.stopRiding();
            }
            plug.discard();
        }
        forget(level, variant);
        clearSavedPlug(level, variant);
        ensureSuspended(level, variant, unit);
    }

    public static void remove(ServerLevel level, int variant)
    {
        EntryPlugCarrierEntity plug = canonical(level, variant);
        if (plug != null)
        {
            plug.discard();
        }
        forget(level, variant);
        clearSavedPlug(level, variant);
    }

    public static void keepPassengerState(EntryPlugCarrierEntity plug)
    {
        Entity passenger = plug.getFirstPassenger();
        if (passenger != null
                && plug.getCabinStage() == EntryPlugCarrierEntity.CABIN_OPEN)
        {
            plug.sealCabin();
        }
        if (passenger instanceof TrainingPilotEntity pilot)
        {
            pilot.setInvisible(true);
            pilot.setTrainingStage(TrainingPilotEntity.STAGE_IN_PLUG);
        }
        else if (passenger instanceof Player player)
        {
            // Once aboard the capsule the pilot is inside it — hide the body so
            // the view reads as the plug's own first person, not a player
            // sitting on a floating model.
            player.setInvisible(true);
        }
        if (passenger == null && (plug.getInsertionStage()
                == EntryPlugCarrierEntity.STAGE_OCCUPIED
                || plug.getInsertionStage()
                == EntryPlugCarrierEntity.STAGE_SUSPENDED))
        {
            if (plug.getInsertionStage()
                    == EntryPlugCarrierEntity.STAGE_OCCUPIED)
            {
                plug.transitionInsertionStage(
                        EntryPlugCarrierEntity.STAGE_OCCUPIED,
                        plug.getInsertionEpoch(),
                        EntryPlugCarrierEntity.STAGE_SUSPENDED);
            }
            plug.openCabin();
        }
    }

    private static void positionSuspended(EntryPlugCarrierEntity plug,
                                          EvaUnit01Entity unit)
    {
        plug.setCanonicalTransform(cageDockTransform(unit));
    }

    private static RigidTransform cageDockTransform(EvaUnit01Entity unit)
    {
        return EntryPlugKinematics.cageDockTransform(suspendedPosition(unit));
    }

    /**
     * Resting point of the suspended plug — always its cage crane.
     *
     * <p>The plug is hangar hardware and never leaves the wet cage. An earlier
     * version derived the rest point from the airframe's own position, so once
     * a unit deployed to the surface the crane drew a stray capsule hundreds of
     * blocks up in the Tokyo-3 sky. It is anchored to the cage regardless of
     * where the airframe is.
     */
    private static Vec3 suspendedPosition(EvaUnit01Entity unit)
    {
        if (unit.level() instanceof ServerLevel level
                && FacilityV2EvaRuntime.ready(level,
                        unit.getUnitVariant()))
        {
            return FacilityV2EvaRuntime.plugRestPosition(
                    level, unit.getUnitVariant());
        }
        return EvaHangarBuilder.plugRestPosition(
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, unit.getUnitVariant());
    }

    /**
     * Finds solid ground near the EVA instead of using the dimension heightmap.
     * In GeoFront the heightmap points at the cavern roof, not the floor.
     */
    private static Vec3 findFieldLanding(ServerLevel level, Vec3 probe,
                                         double unitY)
    {
        int x = Mth.floor(probe.x);
        int z = Mth.floor(probe.z);
        int top = Math.min(level.getMaxBuildHeight() - 3,
                Mth.floor(unitY) + 18);
        int bottom = Math.max(level.getMinBuildHeight() + 1,
                Mth.floor(unitY) - 128);
        BlockPos.MutableBlockPos floor = new BlockPos.MutableBlockPos();
        for (int y = top; y >= bottom; y--)
        {
            floor.set(x, y, z);
            if (!level.getBlockState(floor)
                    .isFaceSturdy(level, floor, Direction.UP))
            {
                continue;
            }
            BlockPos above = floor.above();
            BlockPos head = above.above();
            if (!level.getFluidState(above).isEmpty()
                    || !level.getFluidState(head).isEmpty()
                    || !level.getBlockState(above)
                            .getCollisionShape(level, above).isEmpty()
                    || !level.getBlockState(head)
                            .getCollisionShape(level, head).isEmpty())
            {
                continue;
            }
            return new Vec3(x + 0.5D, y + 2.4D, z + 0.5D);
        }
        return new Vec3(probe.x, Math.max(level.getMinBuildHeight() + 2.4D,
                unitY + 1.0D), probe.z);
    }

    private static double smoothstep(double value)
    {
        double clamped = Mth.clamp(value, 0.0D, 1.0D);
        return clamped * clamped * (3.0D - 2.0D * clamped);
    }

    /** Keeps the visible suspension in step with the capsule it carries. */
    private static void updateCables(ServerLevel level, int variant, double plugY)
    {
        updateCables(level, variant, plugY, Double.NaN, false);
    }

    /**
     * @param travelling true while the crane is driving the plug, which is when
     *                   the telescoping arm is extended behind it.
     */
    private static void updateCables(ServerLevel level, int variant,
                                     double plugY, double plugZ,
                                     boolean travelling)
    {
        BlockPos bed = hangarBed(level, variant);
        if (!level.hasChunkAt(bed))
        {
            return;
        }
        // Skip identical frames: the parked logistics tick asks for this every
        // tick for all three cages, and repainting the crane each time is what
        // put the server seconds behind.
        long signature = craneSignature(plugY, plugZ, travelling);
        if (CRANE_SIGNATURE.get(variant) != null
                && CRANE_SIGNATURE.get(variant) == signature)
        {
            return;
        }
        CRANE_SIGNATURE.put(variant, signature);
        if (FacilityV2EvaRuntime.ready(level, variant))
        {
            FacilityV2EvaRuntime.setPlugCrane(level, variant,
                    plugY, plugZ, travelling);
            return;
        }
        BlockPos origin = IntegratedNervMapBuilder.GEOFRONT_ORIGIN;
        EvaHangarBuilder.setPlugCrane(level, origin, variant, plugY, plugZ,
                travelling && SeeleConfig.PLUG_MECHANICAL_ARM.get());
    }

    private static long craneSignature(double plugY, double plugZ,
                                       boolean travelling)
    {
        long y = Math.round(plugY * 4.0D);
        long z = Double.isNaN(plugZ) ? Long.MIN_VALUE / 4L
                : Math.round(plugZ * 4.0D);
        return (y * 1_000_003L + z) * 2L + (travelling ? 1L : 0L);
    }

    /** Retracts the crane once the capsule is no longer in the cage's hands. */
    private static void stowCrane(ServerLevel level, int variant)
    {
        BlockPos bed = hangarBed(level, variant);
        if (FacilityV2EvaRuntime.ready(level, variant))
        {
            CRANE_SIGNATURE.remove(variant);
            FacilityV2EvaRuntime.stowPlugCrane(level, variant);
            return;
        }
        BlockPos origin = IntegratedNervMapBuilder.GEOFRONT_ORIGIN;
        if (level.hasChunkAt(bed))
        {
            CRANE_SIGNATURE.remove(variant);
            EvaHangarBuilder.stowPlugCrane(level, origin, variant);
        }
    }

    private static BlockPos hangarBed(ServerLevel level, int variant)
    {
        if (FacilityV2EvaRuntime.ready(level, variant))
        {
            return FacilityV2EvaRuntime.hangarBed(level, variant);
        }
        return EvaHangarBuilder.hangarBed(
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant);
    }

    private static Vec3 plugRestPosition(ServerLevel level, int variant)
    {
        if (FacilityV2EvaRuntime.ready(level, variant))
        {
            return FacilityV2EvaRuntime.plugRestPosition(level, variant);
        }
        return EvaHangarBuilder.plugRestPosition(
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant);
    }

    private static boolean isInsideAssignedCage(
            ServerLevel level, EvaUnit01Entity unit, int variant)
    {
        if (FacilityV2EvaRuntime.ready(level, variant))
        {
            return unit.getUnitVariant() == variant
                    && FacilityV2EvaRuntime.isInsideAssignedCage(
                            level, unit.position(), variant);
        }
        return EvaHangarBuilder.isInsideAssignedCage(
                level, unit, variant);
    }

    private static boolean isSupportedPilot(Entity entity)
    {
        return entity instanceof Player || entity instanceof TrainingPilotEntity;
    }

    private static void remember(ServerLevel level, int variant,
                                 EntryPlugCarrierEntity plug)
    {
        CACHED_PLUGS.computeIfAbsent(level.dimension(), ignored -> new HashMap<>())
                .put(variant, plug.getUUID());
        EvaFleetSavedData data = EvaFleetSavedData.get(level.getServer());
        EvaFleetSavedData.FleetEntry entry = data.entry(variant).orElse(null);
        if (entry != null && !plug.getUUID().equals(entry.entryPlugId()))
        {
            data.put(variant, entry.withEntryPlug(plug.getUUID()));
        }
    }

    private static void forget(ServerLevel level, int variant)
    {
        Map<Integer, UUID> dimension = CACHED_PLUGS.get(level.dimension());
        if (dimension != null)
        {
            dimension.remove(variant);
        }
    }

    private static UUID savedPlugId(ServerLevel level, int variant)
    {
        EvaFleetSavedData.FleetEntry entry =
                EvaFleetSavedData.get(level.getServer())
                        .entry(variant).orElse(null);
        return entry == null ? null : entry.entryPlugId();
    }

    private static void clearSavedPlug(ServerLevel level, int variant)
    {
        EvaFleetSavedData data = EvaFleetSavedData.get(level.getServer());
        EvaFleetSavedData.FleetEntry entry = data.entry(variant).orElse(null);
        if (entry != null && entry.entryPlugId() != null)
        {
            data.put(variant, entry.withEntryPlug(null));
        }
    }
}
