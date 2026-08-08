package com.projectseele.world;

import java.util.Comparator;
import java.util.UUID;

import javax.annotation.Nullable;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.EvaWeaponEntity;
import com.projectseele.entity.NervCarrierPlatformEntity;
import com.projectseele.registry.ModEntities;
import com.projectseele.world.EvaWeaponLiftSavedData.LiftEntry;
import com.projectseele.world.EvaWeaponLiftSavedData.State;
import com.projectseele.world.EvaArmamentRackBlockEntity.Reservation;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.TicketType;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/** Server authority for one real weapon identity riding one real lift cradle. */
public final class EvaWeaponLiftDirector
{
    private static final int EVA_SEARCH_RANGE = 56;
    private static final int LOAD_LOCK_TICKS = 20;
    private static final int TOP_DOCK_TICKS = 16;
    private static final int GRIP_VERIFY_TICKS = 12;
    private static final int RELEASE_HOLD_TICKS = 16;
    private static final int PRESENTATION_RISE = 25;
    private static final double MAX_SPEED = 0.42D;
    private static final double ACCELERATION = 0.018D;
    private static final double LEVEL_TOLERANCE = 0.015D;
    private static final double GRIP_ENVELOPE = 12.5D;
    private static final float GRIP_YAW_TOLERANCE = 28.0F;
    private static final int ENTITY_RECOVERY_GRACE_TICKS = 100;
    private static final TicketType<ChunkPos> RECOVERY_TICKET =
            TicketType.create("projectseele_weapon_lift_recovery",
                    Comparator.comparingLong(ChunkPos::toLong), 140);

    private EvaWeaponLiftDirector() {}

    /** Empty-hand rack use: request presentation, then authorize handoff. */
    public static boolean requestPresentation(ServerPlayer player,
                                              BlockPos rackPos,
                                              EvaArmamentRackBlockEntity rack)
    {
        ServerLevel level = player.serverLevel();
        EvaWeaponLiftSavedData data = EvaWeaponLiftSavedData.get(level);
        LiftEntry current = data.entry(rackPos).orElse(null);
        if (current == null)
        {
            rack.releaseOrphanReservation();
        }
        EvaUnit01Entity eva = findNearestEva(level, rackPos);
        if (current != null)
        {
            if (current.state() == State.PRESENTED_LOCKED)
            {
                if (eva == null || !gripEnvelope(eva,
                        resolvePlatform(level, current)))
                {
                    player.displayClientMessage(Component.literal(
                            "NERV ARMAMENT: align a stationary EVA with the presented cradle"),
                            true);
                    return false;
                }
                data.put(current.withEva(eva.getUUID()).withState(
                        State.GRIP_VERIFY, 0, 0.0D));
                player.displayClientMessage(Component.literal(
                        "NERV ARMAMENT: grip verification started"), true);
                return true;
            }
            if (current.state() != State.RACKED_UNDERGROUND)
            {
                player.displayClientMessage(Component.literal(
                        "NERV ARMAMENT: lift sequence already active / "
                                + current.state().name()), true);
                return false;
            }
        }
        if (eva == null || !eva.canReceiveRackArmament())
        {
            player.displayClientMessage(Component.literal(
                    "NERV ARMAMENT: no stationary receptive EVA within "
                            + EVA_SEARCH_RANGE + " blocks"), true);
            return false;
        }

        long transactionNonce = rack.nextTransactionNonce(
                current == null ? 0L : current.nonce());
        Reservation reservation = rack.reserveNextArmament(transactionNonce);
        if (reservation == null)
        {
            player.displayClientMessage(Component.translatable(
                    "msg.projectseele.armament_rack_empty"), true);
            return false;
        }
        ItemStack reserved = reservation.stack();
        int weapon = EvaArmamentRackBlockEntity.weaponFor(reserved);
        BlockPos bottomPos = rack.liftBottomOr(
                BlockPos.containing(bottom(rackPos)));
        BlockPos topPos = rack.liftTopOr(
                bottomPos.above(PRESENTATION_RISE));
        if (topPos.getY() <= bottomPos.getY())
        {
            rack.releaseOrphanReservation();
            player.displayClientMessage(Component.literal(
                    "NERV ARMAMENT: invalid physical lift stops"), true);
            return false;
        }
        NervCarrierPlatformEntity platform = current == null ? null
                : resolvePlatform(level, current);
        boolean spawnedPlatform = false;
        if (current != null && platform == null)
        {
            requestRecoveryTicket(level, current.platformLast());
            player.displayClientMessage(Component.literal(
                    "NERV ARMAMENT: recovering the persistent lift; retry shortly"),
                    true);
            return false;
        }
        if (platform == null)
        {
            platform = ModEntities.NERV_LIFT_CABIN.get().create(level);
            if (platform == null)
            {
                rack.releaseOrphanReservation();
                return false;
            }
            platform.configureArmamentLift(systemId(rackPos),
                    eva.getUnitVariant());
            Vec3 bottom = Vec3.atCenterOf(bottomPos);
            platform.setPos(bottom.x, bottom.y, bottom.z);
            platform.setYRot(eva.getYRot());
            if (!level.addFreshEntity(platform))
            {
                rack.releaseOrphanReservation();
                return false;
            }
            spawnedPlatform = true;
        }
        else
        {
            platform.configureArmamentLift(systemId(rackPos),
                    eva.getUnitVariant());
            platform.setYRot(eva.getYRot());
        }

        EvaWeaponEntity payload = null;
        boolean spawnedPayload = reservation.residentEntityId() == null;
        if (!spawnedPayload)
        {
            Entity resident = level.getEntity(reservation.residentEntityId());
            if (resident instanceof EvaWeaponEntity weaponEntity
                    && weaponEntity.getAttachmentMode()
                    == EvaWeaponEntity.ATTACHMENT_RACK)
            {
                payload = weaponEntity;
            }
        }
        else
        {
            payload = ModEntities.EVA_WEAPON.get().create(level);
        }
        if (payload == null)
        {
            if (spawnedPlatform)
            {
                platform.discard();
            }
            rack.releaseOrphanReservation();
            player.displayClientMessage(Component.literal(
                    "NERV ARMAMENT: resident payload identity unavailable; no replacement created"),
                    true);
            return false;
        }
        payload.configurePayload(weapon);
        payload.setCarrierStage(EvaWeaponEntity.STAGE_LOADING_LOCKED);
        platform.configureArmamentLift(systemId(rackPos),
                eva.getUnitVariant(), payload.getUUID());
        if ((spawnedPayload && !level.addFreshEntity(payload))
                || !payload.mountOnPlatform(platform,
                EvaWeaponEntity.STAGE_LOADING_LOCKED,
                presentationEpoch(transactionNonce)))
        {
            if (spawnedPayload)
            {
                payload.discard();
            }
            else
            {
                payload.markStored(Vec3.atCenterOf(bottomPos));
            }
            if (spawnedPlatform)
            {
                platform.discard();
            }
            rack.releaseOrphanReservation();
            return false;
        }
        LiftEntry started = new LiftEntry(rackPos.immutable(), bottomPos, topPos,
                eva.getUnitVariant(), weapon, State.LOADING_LOCKED, 0, 0.0D,
                platform.getUUID(), payload.getUUID(), eva.getUUID(),
                transactionNonce, platform.blockPosition(),
                payload.blockPosition(), 0, 0);
        data.put(started);
        if (!rack.commitReservation(transactionNonce, weapon))
        {
            data.remove(rackPos);
            if (spawnedPayload)
            {
                payload.discard();
            }
            else
            {
                payload.markStored(Vec3.atCenterOf(bottomPos));
            }
            if (spawnedPlatform)
            {
                platform.discard();
            }
            rack.releaseOrphanReservation();
            ProjectSeele.LOGGER.error(
                    "NERV armament reservation commit failed: rack={} nonce={} weapon={}",
                    rackPos, transactionNonce, weapon);
            return false;
        }
        level.playSound(null, rackPos, SoundEvents.PISTON_CONTRACT,
                SoundSource.BLOCKS, 1.2F, 0.62F);
        player.displayClientMessage(Component.literal(
                "NERV ARMAMENT: payload locked; underground lift rising"),
                true);
        ProjectSeele.LOGGER.info(
                "NERV armament lift reserved payload: rack={} weapon={} platform={} payload={} eva={}",
                rackPos, weapon, platform.getStringUUID(),
                payload.getStringUUID(), eva.getStringUUID());
        return true;
    }

    /** Shift-use: reverse an unclaimed payload or retrieve a deployed one. */
    public static boolean requestReturn(ServerPlayer player, BlockPos rackPos)
    {
        ServerLevel level = player.serverLevel();
        EvaWeaponLiftSavedData data = EvaWeaponLiftSavedData.get(level);
        LiftEntry entry = data.entry(rackPos).orElse(null);
        if (entry == null || entry.state() == State.RACKED_UNDERGROUND)
        {
            return false;
        }
        switch (entry.state())
        {
            case LOADING_LOCKED, ASCENDING, TOP_DOCKING,
                    PRESENTED_LOCKED, GRIP_VERIFY ->
            {
                data.put(entry.withState(State.DESCENDING_WITH_WEAPON,
                        0, 0.0D));
                player.displayClientMessage(Component.literal(
                        "NERV ARMAMENT: presentation cancelled; payload returning"),
                        true);
                return true;
            }
            case DEPLOYED_TO_EVA ->
            {
                EvaUnit01Entity eva = resolveEva(level, entry);
                if (eva == null || !eva.canReceiveRackArmament())
                {
                    player.displayClientMessage(Component.literal(
                            "NERV ARMAMENT: EVA must be stationary for return"),
                            true);
                    return false;
                }
                data.put(entry.withState(
                        State.ASCENDING_EMPTY_FOR_RETURN, 0, 0.0D));
                player.displayClientMessage(Component.literal(
                        "NERV ARMAMENT: empty cradle rising for recovery"),
                        true);
                return true;
            }
            default ->
            {
                player.displayClientMessage(Component.literal(
                        "NERV ARMAMENT: return sequence busy / "
                                + entry.state().name()), true);
                return false;
            }
        }
    }

    public static boolean hasActiveSequence(ServerLevel level,
                                            BlockPos rackPos)
    {
        return EvaWeaponLiftSavedData.get(level).entry(rackPos)
                .map(entry -> entry.state() != State.RACKED_UNDERGROUND)
                .orElse(false);
    }

    public static void tick(ServerLevel level)
    {
        EvaWeaponLiftSavedData data = EvaWeaponLiftSavedData.get(level);
        for (LiftEntry entry : data.entries())
        {
            tick(level, data, entry);
        }
    }

    private static void tick(ServerLevel level,
                             EvaWeaponLiftSavedData data, LiftEntry entry)
    {
        requestRecoveryTicket(level, entry.platformLast());
        NervCarrierPlatformEntity platform = resolvePlatform(level, entry);
        if (platform == null)
        {
            awaitMissingPlatform(level, data, entry);
            return;
        }
        if (entry.platformUnresolvedTicks() > 0)
        {
            platform.resetInterpolationFrame();
        }
        if (entry.platformUnresolvedTicks() > 0
                || !entry.platformLast().equals(platform.blockPosition()))
        {
            entry = entry.observedPlatform(platform.blockPosition());
            data.put(entry);
        }
        platform.configureArmamentLift(systemId(entry.rack()),
                entry.variant(), entry.weaponEntityId());
        updateSurfaceFacade(level, entry, platform);
        if (!reconcileReservation(level, entry))
        {
            fault(data, entry, "rack reservation could not be reconciled");
            return;
        }
        EvaWeaponEntity weapon = resolveWeapon(level, entry);
        if (requiresPayload(entry.state()) && weapon == null)
        {
            requestRecoveryTicket(level, entry.weaponLast() == null
                    ? entry.rack() : entry.weaponLast());
            awaitMissingWeapon(level, data, entry);
            return;
        }
        if (weapon != null && (entry.weaponUnresolvedTicks() > 0
                || entry.weaponLast() == null
                || !entry.weaponLast().equals(weapon.blockPosition())))
        {
            if (entry.weaponUnresolvedTicks() > 0)
            {
                weapon.resetInterpolationFrame();
            }
            entry = entry.observedWeapon(weapon.blockPosition());
            data.put(entry);
        }
        if (weapon != null && requiresPayload(entry.state())
                && !weapon.hasExclusiveTransportOwner(entry.platformId(),
                entry.evaId()))
        {
            weapon.setCarrierStage(EvaWeaponEntity.STAGE_FAULT);
            weapon.setTransportLocked(true);
            fault(data, entry,
                    "payload has zero, duplicate, or foreign physical owners");
            return;
        }

        switch (entry.state())
        {
            case RACKED_UNDERGROUND -> holdAt(platform, entry.bottom());
            case LOADING_LOCKED ->
            {
                holdAt(platform, entry.bottom());
                if (!keepMounted(weapon, platform,
                        EvaWeaponEntity.STAGE_LOADING_LOCKED,
                        presentationEpoch(entry.nonce())))
                {
                    fault(data, entry, "payload failed bottom cradle lock");
                    return;
                }
                int ticks = entry.ticks() + 1;
                data.put(ticks >= LOAD_LOCK_TICKS
                        ? entry.withState(State.ASCENDING, 0, 0.0D)
                        : entry.moving(State.LOADING_LOCKED, ticks, 0.0D));
            }
            case ASCENDING ->
            {
                if (!keepMounted(weapon, platform,
                        EvaWeaponEntity.STAGE_ASCENDING,
                        presentationEpoch(entry.nonce())))
                {
                    fault(data, entry, "payload left ascending cradle");
                    return;
                }
                Motion motion = move(platform, entry.top().getY() + 0.5D,
                        entry.velocity());
                data.put(motion.arrived()
                        ? entry.withState(State.TOP_DOCKING, 0, 0.0D)
                        : entry.moving(State.ASCENDING,
                        entry.ticks() + 1, motion.velocity()));
            }
            case TOP_DOCKING ->
            {
                holdAt(platform, entry.top());
                if (!keepMounted(weapon, platform,
                        EvaWeaponEntity.STAGE_TOP_DOCKING,
                        presentationEpoch(entry.nonce())))
                {
                    fault(data, entry, "payload failed top docking lock");
                    return;
                }
                int ticks = entry.ticks() + 1;
                data.put(ticks >= TOP_DOCK_TICKS
                        ? entry.withState(State.PRESENTED_LOCKED, 0, 0.0D)
                        : entry.moving(State.TOP_DOCKING, ticks, 0.0D));
            }
            case PRESENTED_LOCKED ->
            {
                holdAt(platform, entry.top());
                if (!keepMounted(weapon, platform,
                        EvaWeaponEntity.STAGE_PRESENTED_LOCKED,
                        presentationEpoch(entry.nonce())))
                {
                    fault(data, entry, "presented payload is not locked");
                }
            }
            case GRIP_VERIFY -> tickGripVerify(level, data, entry,
                    platform, weapon);
            case HANDOFF_TO_EVA -> tickHandoffToEva(level, data, entry,
                    platform, weapon);
            case RELEASED_TO_EVA ->
            {
                holdAt(platform, entry.top());
                if (!verifyEvaAttachment(level, data, entry, weapon))
                {
                    return;
                }
                int ticks = entry.ticks() + 1;
                data.put(ticks >= RELEASE_HOLD_TICKS
                        ? entry.withState(State.RETURNING_EMPTY, 0, 0.0D)
                        : entry.moving(State.RELEASED_TO_EVA, ticks, 0.0D));
            }
            case RETURNING_EMPTY ->
            {
                if (!verifyEvaAttachment(level, data, entry, weapon))
                {
                    return;
                }
                Motion motion = move(platform,
                        entry.bottom().getY() + 0.5D, entry.velocity());
                data.put(motion.arrived()
                        ? entry.withState(State.DEPLOYED_TO_EVA, 0, 0.0D)
                        : entry.moving(State.RETURNING_EMPTY,
                        entry.ticks() + 1, motion.velocity()));
            }
            case DEPLOYED_TO_EVA ->
            {
                holdAt(platform, entry.bottom());
                verifyEvaAttachment(level, data, entry, weapon);
            }
            case ASCENDING_EMPTY_FOR_RETURN ->
            {
                if (!verifyEvaAttachment(level, data, entry, weapon))
                {
                    return;
                }
                Motion motion = move(platform, entry.top().getY() + 0.5D,
                        entry.velocity());
                data.put(motion.arrived()
                        ? entry.withState(State.RETURN_DOCKING, 0, 0.0D)
                        : entry.moving(State.ASCENDING_EMPTY_FOR_RETURN,
                        entry.ticks() + 1, motion.velocity()));
            }
            case RETURN_DOCKING -> tickReturnDocking(level, data, entry,
                    platform, weapon);
            case HANDOFF_TO_PLATFORM -> tickHandoffToPlatform(level, data,
                    entry, platform, weapon);
            case DESCENDING_WITH_WEAPON -> tickPayloadReturn(level, data,
                    entry, platform, weapon);
            case EMERGENCY_STOP, FAULT ->
            {
                platform.moveControlled(platform.getX(), platform.getY(),
                        platform.getZ());
                if (weapon != null)
                {
                    weapon.setTransportLocked(true);
                }
            }
        }
    }

    private static void tickGripVerify(ServerLevel level,
                                       EvaWeaponLiftSavedData data,
                                       LiftEntry entry,
                                       NervCarrierPlatformEntity platform,
                                       EvaWeaponEntity weapon)
    {
        holdAt(platform, entry.top());
        if (!keepMounted(weapon, platform,
                EvaWeaponEntity.STAGE_GRIP_VERIFY,
                presentationEpoch(entry.nonce())))
        {
            fault(data, entry, "payload left cradle during grip verification");
            return;
        }
        EvaUnit01Entity eva = resolveEva(level, entry);
        if (eva == null || !gripEnvelope(eva, platform))
        {
            data.put(entry.withState(State.PRESENTED_LOCKED, 0, 0.0D));
            return;
        }
        int ticks = entry.ticks() + 1;
        if (ticks < GRIP_VERIFY_TICKS)
        {
            data.put(entry.moving(State.GRIP_VERIFY, ticks, 0.0D));
            return;
        }
        data.put(entry.withState(State.HANDOFF_TO_EVA, 0, 0.0D));
    }

    private static void tickHandoffToEva(ServerLevel level,
                                         EvaWeaponLiftSavedData data,
                                         LiftEntry entry,
                                         NervCarrierPlatformEntity platform,
                                         EvaWeaponEntity weapon)
    {
        holdAt(platform, entry.top());
        EvaUnit01Entity eva = resolveEva(level, entry);
        long epoch = evaEpoch(entry.nonce());
        if (eva == null)
        {
            requestRecoveryTicket(level, entry.weaponLast() == null
                    ? entry.rack() : entry.weaponLast());
            return;
        }
        if (weapon == null || !gripEnvelope(eva, platform))
        {
            fault(data, entry, "EVA handoff target unavailable");
            return;
        }
        if (weapon.isAttachedToEva(eva, epoch))
        {
            data.put(entry.withState(State.RELEASED_TO_EVA, 0, 0.0D));
            return;
        }
        if (weapon.isAttachedToPlatform(platform,
                presentationEpoch(entry.nonce())))
        {
            if (!weapon.beginHandoff(eva, epoch))
            {
                fault(data, entry, "payload EVA handoff intent failed");
                return;
            }
            data.put(entry.moving(State.HANDOFF_TO_EVA,
                    entry.ticks() + 1, 0.0D));
            return;
        }
        if (!weapon.isHandoffTo(eva, epoch)
                || !weapon.commitToEva(eva, epoch))
        {
            fault(data, entry, "payload EVA parent commit failed");
            return;
        }
        data.put(entry.withState(State.RELEASED_TO_EVA, 0, 0.0D));
        level.playSound(null, platform.blockPosition(),
                SoundEvents.IRON_TRAPDOOR_OPEN, SoundSource.BLOCKS,
                1.3F, 0.72F);
    }

    private static void tickReturnDocking(ServerLevel level,
                                          EvaWeaponLiftSavedData data,
                                          LiftEntry entry,
                                          NervCarrierPlatformEntity platform,
                                          EvaWeaponEntity weapon)
    {
        holdAt(platform, entry.top());
        EvaUnit01Entity eva = resolveEva(level, entry);
        if (eva == null)
        {
            requestRecoveryTicket(level, entry.weaponLast() == null
                    ? entry.rack() : entry.weaponLast());
            return;
        }
        if (weapon == null || !gripEnvelope(eva, platform)
                || !weapon.isAttachedToEva(eva,
                evaEpoch(entry.nonce())))
        {
            fault(data, entry, "EVA/weapon return socket unavailable");
            return;
        }
        int ticks = entry.ticks() + 1;
        if (ticks < TOP_DOCK_TICKS)
        {
            data.put(entry.moving(State.RETURN_DOCKING, ticks, 0.0D));
            return;
        }
        data.put(entry.withState(State.HANDOFF_TO_PLATFORM, 0, 0.0D));
    }

    private static void tickHandoffToPlatform(ServerLevel level,
                                              EvaWeaponLiftSavedData data,
                                              LiftEntry entry,
                                              NervCarrierPlatformEntity platform,
                                              EvaWeaponEntity weapon)
    {
        holdAt(platform, entry.top());
        EvaUnit01Entity eva = resolveEva(level, entry);
        long epoch = returnEpoch(entry.nonce());
        if (eva == null)
        {
            requestRecoveryTicket(level, entry.weaponLast() == null
                    ? entry.rack() : entry.weaponLast());
            return;
        }
        if (weapon == null || !gripEnvelope(eva, platform))
        {
            fault(data, entry, "return handoff target unavailable");
            return;
        }
        if (weapon.isAttachedToPlatform(platform, epoch))
        {
            eva.unloadRackArmament();
            data.put(entry.withState(State.DESCENDING_WITH_WEAPON,
                    0, 0.0D));
            return;
        }
        if (weapon.isAttachedToEva(eva, evaEpoch(entry.nonce())))
        {
            if (!weapon.beginHandoff(platform, epoch))
            {
                fault(data, entry, "payload return handoff intent failed");
                return;
            }
            data.put(entry.moving(State.HANDOFF_TO_PLATFORM,
                    entry.ticks() + 1, 0.0D));
            return;
        }
        if (!weapon.isHandoffTo(platform, epoch)
                || !weapon.commitToPlatform(platform,
                EvaWeaponEntity.STAGE_RETURNING, epoch))
        {
            fault(data, entry, "payload platform parent commit failed");
            return;
        }
        eva.unloadRackArmament();
        data.put(entry.withState(State.DESCENDING_WITH_WEAPON, 0, 0.0D));
    }

    private static void tickPayloadReturn(ServerLevel level,
                                          EvaWeaponLiftSavedData data,
                                          LiftEntry entry,
                                          NervCarrierPlatformEntity platform,
                                          EvaWeaponEntity weapon)
    {
        if (level.getBlockEntity(entry.rack())
                instanceof EvaArmamentRackBlockEntity receivedRack
                && receivedRack.hasReturnedEntity(entry.nonce(),
                weapon.getUUID(), weapon.getWeapon()))
        {
            finishStoredReturn(data, entry, platform, weapon);
            return;
        }
        if (!keepMounted(weapon, platform, EvaWeaponEntity.STAGE_RETURNING,
                returnEpoch(entry.nonce())))
        {
            fault(data, entry, "returning payload left cradle");
            return;
        }
        Motion motion = move(platform, entry.bottom().getY() + 0.5D,
                entry.velocity());
        if (!motion.arrived())
        {
            data.put(entry.moving(State.DESCENDING_WITH_WEAPON,
                    entry.ticks() + 1, motion.velocity()));
            return;
        }
        if (!(level.getBlockEntity(entry.rack())
                instanceof EvaArmamentRackBlockEntity rack)
                || !rack.acceptReturnedArmament(entry.nonce(),
                weapon.getUUID(), weapon.getWeapon()))
        {
            fault(data, entry, "rack missing or full at bottom docking");
            return;
        }
        finishStoredReturn(data, entry, platform, weapon);
        level.playSound(null, entry.rack(), SoundEvents.IRON_DOOR_CLOSE,
                SoundSource.BLOCKS, 1.0F, 0.72F);
    }

    private static void finishStoredReturn(EvaWeaponLiftSavedData data,
                                           LiftEntry entry,
                                           NervCarrierPlatformEntity platform,
                                           EvaWeaponEntity weapon)
    {
        weapon.markStored(Vec3.atCenterOf(entry.bottom()));
        platform.configureArmamentLift(systemId(entry.rack()),
                entry.variant(), null);
        data.put(new LiftEntry(entry.rack(), entry.bottom(), entry.top(),
                entry.variant(), EvaUnit01Entity.WEAPON_FISTS,
                State.RACKED_UNDERGROUND, 0, 0.0D,
                entry.platformId(), null, null, entry.nonce(),
                platform.blockPosition(), null, 0, 0));
    }

    private static boolean keepMounted(@Nullable EvaWeaponEntity weapon,
                                       NervCarrierPlatformEntity platform,
                                       int stage, long epoch)
    {
        if (weapon == null)
        {
            return false;
        }
        weapon.setCarrierStage(stage);
        weapon.setTransportLocked(true);
        weapon.setPayloadVisible(true);
        return weapon.isAttachedToPlatform(platform, epoch);
    }

    private static Motion move(NervCarrierPlatformEntity platform,
                               double targetY, double velocity)
    {
        double remaining = Math.abs(targetY - platform.getY());
        if (remaining <= LEVEL_TOLERANCE)
        {
            platform.moveControlled(platform.getX(), targetY,
                    platform.getZ());
            return new Motion(0.0D, true);
        }
        double targetSpeed = Math.min(MAX_SPEED,
                Math.sqrt(2.0D * ACCELERATION * remaining));
        double nextVelocity = velocity < targetSpeed
                ? Math.min(targetSpeed, velocity + ACCELERATION)
                : Math.max(targetSpeed, velocity - ACCELERATION);
        double step = Math.min(remaining,
                Math.max(LEVEL_TOLERANCE, nextVelocity));
        platform.moveControlled(platform.getX(),
                platform.getY() + Math.copySign(step,
                        targetY - platform.getY()), platform.getZ());
        return new Motion(nextVelocity,
                Math.abs(targetY - platform.getY()) <= LEVEL_TOLERANCE);
    }

    private static void holdAt(NervCarrierPlatformEntity platform,
                               BlockPos position)
    {
        platform.moveControlled(position.getX() + 0.5D,
                position.getY() + 0.5D, position.getZ() + 0.5D);
    }

    private static boolean gripEnvelope(EvaUnit01Entity eva,
                                        @Nullable NervCarrierPlatformEntity platform)
    {
        if (platform == null || !eva.canReceiveRackArmament())
        {
            return false;
        }
        double distance = eva.getNearestArmamentServiceHandProxy(
                platform.position()).distanceTo(platform.position());
        float yawError = Math.abs(Mth.wrapDegrees(
                eva.getYRot() - platform.getYRot()));
        return distance <= GRIP_ENVELOPE
                && yawError <= GRIP_YAW_TOLERANCE;
    }

    private static boolean reconcileReservation(ServerLevel level,
                                                 LiftEntry entry)
    {
        if (entry.state() == State.RACKED_UNDERGROUND)
        {
            return true;
        }
        if (!(level.getBlockEntity(entry.rack())
                instanceof EvaArmamentRackBlockEntity rack))
        {
            return false;
        }
        return rack.reconcileReservationCommit(entry.nonce(),
                entry.weapon());
    }

    private static void updateSurfaceFacade(ServerLevel level,
                                            LiftEntry entry,
                                            NervCarrierPlatformEntity platform)
    {
        if (!(level.getBlockEntity(entry.rack())
                instanceof EvaArmamentRackBlockEntity rack)
                || rack.surfaceFacadeOrigin() == null)
        {
            return;
        }
        double bottomY = entry.bottom().getY() + 0.5D;
        double topY = entry.top().getY() + 0.5D;
        double openness = topY <= bottomY ? 0.0D
                : Math.max(0.0D, Math.min(1.0D,
                (platform.getY() - bottomY) / (topY - bottomY)));
        boolean active = switch (entry.state())
        {
            case RACKED_UNDERGROUND, DEPLOYED_TO_EVA,
                    EMERGENCY_STOP, FAULT -> false;
            default -> true;
        };
        ThirdTokyoSurfaceBuilder.updateWeaponLiftFacade(level,
                rack.surfaceFacadeOrigin(), openness, active);
    }

    private static boolean requiresPayload(State state)
    {
        return switch (state)
        {
            case LOADING_LOCKED, ASCENDING, TOP_DOCKING,
                    PRESENTED_LOCKED, GRIP_VERIFY, HANDOFF_TO_EVA,
                    RELEASED_TO_EVA, RETURNING_EMPTY, DEPLOYED_TO_EVA,
                    ASCENDING_EMPTY_FOR_RETURN, RETURN_DOCKING,
                    HANDOFF_TO_PLATFORM, DESCENDING_WITH_WEAPON -> true;
            default -> false;
        };
    }

    private static boolean verifyEvaAttachment(ServerLevel level,
                                               EvaWeaponLiftSavedData data,
                                               LiftEntry entry,
                                               @Nullable EvaWeaponEntity weapon)
    {
        EvaUnit01Entity eva = resolveEva(level, entry);
        if (eva == null)
        {
            requestRecoveryTicket(level, entry.weaponLast() == null
                    ? entry.rack() : entry.weaponLast());
            return false;
        }
        if (weapon == null || !weapon.isAttachedToEva(eva,
                evaEpoch(entry.nonce())))
        {
            fault(data, entry, "payload/EVA attachment receipt mismatch");
            return false;
        }
        return true;
    }

    private static void awaitMissingPlatform(ServerLevel level,
                                             EvaWeaponLiftSavedData data,
                                             LiftEntry entry)
    {
        requestRecoveryTicket(level, entry.platformLast());
        if (!chunkFullyLoaded(level, entry.platformLast()))
        {
            return;
        }
        LiftEntry waiting = entry.missingPlatformTick();
        if (waiting.platformUnresolvedTicks()
                >= ENTITY_RECOVERY_GRACE_TICKS)
        {
            fault(data, waiting,
                    "persistent platform absent after loaded-chunk recovery barrier");
        }
        else
        {
            data.put(waiting);
        }
    }

    private static void awaitMissingWeapon(ServerLevel level,
                                           EvaWeaponLiftSavedData data,
                                           LiftEntry entry)
    {
        BlockPos position = entry.weaponLast() == null
                ? entry.rack() : entry.weaponLast();
        requestRecoveryTicket(level, position);
        if (!chunkFullyLoaded(level, position))
        {
            return;
        }
        LiftEntry waiting = entry.missingWeaponTick();
        if (waiting.weaponUnresolvedTicks()
                >= ENTITY_RECOVERY_GRACE_TICKS)
        {
            fault(data, waiting,
                    "persistent payload absent after loaded-chunk recovery barrier");
        }
        else
        {
            data.put(waiting);
        }
    }

    private static void requestRecoveryTicket(ServerLevel level,
                                              BlockPos position)
    {
        ChunkPos chunk = new ChunkPos(position);
        level.getChunkSource().addRegionTicket(RECOVERY_TICKET,
                chunk, 0, chunk);
    }

    private static boolean chunkFullyLoaded(ServerLevel level,
                                            BlockPos position)
    {
        return level.getChunkSource().getChunkNow(
                position.getX() >> 4, position.getZ() >> 4) != null;
    }

    private static long presentationEpoch(long nonce)
    {
        return transactionEpoch(nonce, 0L);
    }

    private static long evaEpoch(long nonce)
    {
        return transactionEpoch(nonce, 1L);
    }

    private static long returnEpoch(long nonce)
    {
        return transactionEpoch(nonce, 2L);
    }

    private static long transactionEpoch(long nonce, long phase)
    {
        long safe = Math.max(1L, nonce);
        if (safe > (Long.MAX_VALUE - phase) / 4L)
        {
            return Long.MAX_VALUE - (2L - phase);
        }
        return safe * 4L + phase;
    }

    private static void fault(EvaWeaponLiftSavedData data, LiftEntry entry,
                              String reason)
    {
        if (entry.state() != State.FAULT)
        {
            ProjectSeele.LOGGER.error(
                    "NERV armament lift fault: rack={} state={} reason={}",
                    entry.rack(), entry.state(), reason);
            data.put(entry.withState(State.FAULT, 0, 0.0D));
        }
    }

    @Nullable
    private static NervCarrierPlatformEntity resolvePlatform(
            ServerLevel level, LiftEntry entry)
    {
        Entity entity = level.getEntity(entry.platformId());
        return entity instanceof NervCarrierPlatformEntity platform
                && platform.isArmamentLift()
                && systemId(entry.rack()).equals(
                        platform.getArmamentSystemId()) ? platform : null;
    }

    @Nullable
    private static EvaWeaponEntity resolveWeapon(ServerLevel level,
                                                 LiftEntry entry)
    {
        if (entry.weaponEntityId() == null)
        {
            return null;
        }
        Entity entity = level.getEntity(entry.weaponEntityId());
        return entity instanceof EvaWeaponEntity weapon ? weapon : null;
    }

    @Nullable
    private static EvaUnit01Entity resolveEva(ServerLevel level,
                                              LiftEntry entry)
    {
        if (entry.evaId() == null)
        {
            return null;
        }
        Entity entity = level.getEntity(entry.evaId());
        return entity instanceof EvaUnit01Entity eva ? eva : null;
    }

    @Nullable
    public static EvaUnit01Entity findNearestEva(ServerLevel level,
                                                 BlockPos rackPos)
    {
        Vec3 centre = Vec3.atCenterOf(rackPos);
        return level.getEntitiesOfClass(EvaUnit01Entity.class,
                        new AABB(rackPos).inflate(EVA_SEARCH_RANGE),
                        eva -> eva.isAlive() && !eva.isRemoved())
                .stream().min(Comparator.comparingDouble(
                        eva -> eva.distanceToSqr(centre))).orElse(null);
    }

    private static Vec3 bottom(BlockPos rackPos)
    {
        return Vec3.atCenterOf(rackPos.below(3));
    }

    private static String systemId(BlockPos rackPos)
    {
        return "weapon-" + rackPos.getX() + "-" + rackPos.getY()
                + "-" + rackPos.getZ();
    }

    private record Motion(double velocity, boolean arrived) {}
}
