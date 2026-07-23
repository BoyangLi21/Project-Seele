package com.projectseele.world;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EntryPlugCarrierEntity;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.TrainingPilotEntity;
import com.projectseele.registry.ModEntities;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/** Owns the external entry plug from the overhead rack to the dorsal socket. */
public final class EntryPlugDirector
{
    public static final int INSERTION_TICKS = 80;

    private static final double START_REAR_OFFSET = 6.25D;
    private static final double START_HEIGHT_OFFSET = 3.5D;
    private static final float START_TILT = -10.0F;
    private static final float SEATED_TILT = -48.0F;
    private static final Map<ResourceKey<Level>, Map<Integer, UUID>>
            CACHED_PLUGS = new HashMap<>();

    private EntryPlugDirector() {}

    public static EntryPlugCarrierEntity ensureSuspended(
            ServerLevel level, int variant, EvaUnit01Entity unit)
    {
        EntryPlugCarrierEntity plug = canonical(level, variant);
        if (plug == null)
        {
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
        if (plug.getInsertionStage()
                != EntryPlugCarrierEntity.STAGE_INSERTING)
        {
            Vec3 wanted = suspendedPosition(unit);
            if (plug.position().distanceToSqr(wanted) > 1.0E-4D
                    || Math.abs(plug.getYRot() - unit.getYRot()) > 0.01F
                    || Math.abs(plug.getXRot() - START_TILT) > 0.01F)
            {
                plug.moveTo(wanted.x, wanted.y, wanted.z,
                        unit.getYRot(), START_TILT);
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
                plug.setInsertionStage(wantedStage);
            }
        }
        return plug;
    }

    public static EntryPlugCarrierEntity canonical(ServerLevel level,
                                                    int variant)
    {
        Map<Integer, UUID> dimensionCache = CACHED_PLUGS.computeIfAbsent(
                level.dimension(), ignored -> new HashMap<>());
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

        // A PARKED/INSERTING plug never leaves its assigned wet cage. A local
        // section query avoids scanning every entity in the 640-block cavern
        // three times per server tick.
        net.minecraft.core.BlockPos bed = EvaHangarBuilder.hangarBed(
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant);
        AABB search = new AABB(bed).inflate(32.0D, 64.0D, 48.0D);
        List<EntryPlugCarrierEntity> matches = new ArrayList<>(
                level.getEntitiesOfClass(EntryPlugCarrierEntity.class, search,
                        plug -> plug.isAlive()
                                && plug.getAssignedVariant() == variant));
        if (matches.isEmpty())
        {
            return null;
        }
        matches.sort(Comparator.comparing(Entity::getUUID));
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

    public static void resetRuntime()
    {
        CACHED_PLUGS.clear();
    }

    public static boolean hasBoardedPilot(ServerLevel level, int variant,
                                          EvaUnit01Entity unit)
    {
        if (isSupportedPilot(unit.getFirstPassenger()))
        {
            return true;
        }
        EntryPlugCarrierEntity plug = canonical(level, variant);
        return plug != null && isSupportedPilot(plug.getFirstPassenger());
    }

    public static void beginInsertion(ServerLevel level, int variant,
                                      EvaUnit01Entity unit)
    {
        EntryPlugCarrierEntity plug = ensureSuspended(level, variant, unit);
        if (plug != null)
        {
            plug.setInsertionStage(EntryPlugCarrierEntity.STAGE_INSERTING);
            plug.setInsertionProgress(0);
        }
    }

    /** Returns true only after the passenger is physically transferred. */
    public static boolean tickInsertion(ServerLevel level, int variant,
                                        EvaUnit01Entity unit, int ticks)
    {
        EntryPlugCarrierEntity plug = canonical(level, variant);
        if (plug == null)
        {
            plug = ensureSuspended(level, variant, unit);
            if (plug == null)
            {
                return false;
            }
            plug.setInsertionStage(EntryPlugCarrierEntity.STAGE_INSERTING);
        }
        double linear = Mth.clamp(ticks / (double) INSERTION_TICKS,
                0.0D, 1.0D);
        double progress = linear * linear * (3.0D - 2.0D * linear);
        Vec3 start = suspendedPosition(unit);
        Vec3 target = unit.getEntryPlugSocketPosition();
        Vec3 position = start.lerp(target, progress);
        float tilt = (float) Mth.lerp(progress, START_TILT, SEATED_TILT);
        plug.moveTo(position.x, position.y, position.z,
                unit.getYRot(), tilt);
        plug.setInsertionProgress((int) Math.round(linear * 100.0D));
        plug.setInsertionStage(EntryPlugCarrierEntity.STAGE_INSERTING);
        if (ticks < INSERTION_TICKS)
        {
            return false;
        }

        Entity passenger = plug.getFirstPassenger();
        if (passenger == null && !isSupportedPilot(unit.getFirstPassenger()))
        {
            ProjectSeele.LOGGER.warn(
                    "NERV entry plug insertion aborted without pilot: eva={} plug={}",
                    variant, plug.getStringUUID());
            return false;
        }
        if (passenger != null)
        {
            passenger.stopRiding();
            if (!unit.boardFromExternalPlug(passenger))
            {
                plug.boardPassenger(passenger);
                return false;
            }
        }
        ProjectSeele.LOGGER.info(
                "NERV entry plug seated: eva={} plug={} passenger={}",
                variant, plug.getStringUUID(), passenger == null
                        ? "already-in-unit" : passenger.getStringUUID());
        plug.discard();
        return true;
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
    }

    public static void keepPassengerState(EntryPlugCarrierEntity plug)
    {
        Entity passenger = plug.getFirstPassenger();
        if (passenger instanceof TrainingPilotEntity pilot)
        {
            pilot.setInvisible(true);
            pilot.setTrainingStage(TrainingPilotEntity.STAGE_IN_PLUG);
        }
        if (passenger == null && plug.getInsertionStage()
                == EntryPlugCarrierEntity.STAGE_OCCUPIED)
        {
            plug.setInsertionStage(EntryPlugCarrierEntity.STAGE_SUSPENDED);
        }
    }

    private static void positionSuspended(EntryPlugCarrierEntity plug,
                                          EvaUnit01Entity unit)
    {
        Vec3 position = suspendedPosition(unit);
        plug.moveTo(position.x, position.y, position.z,
                unit.getYRot(), START_TILT);
    }

    private static Vec3 suspendedPosition(EvaUnit01Entity unit)
    {
        Vec3 rear = unit.getForward().multiply(-1.0D, 0.0D, -1.0D)
                .normalize();
        return unit.getEntryPlugSocketPosition()
                .add(rear.scale(START_REAR_OFFSET))
                .add(0.0D, START_HEIGHT_OFFSET, 0.0D);
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
    }

    private static void forget(ServerLevel level, int variant)
    {
        Map<Integer, UUID> dimension = CACHED_PLUGS.get(level.dimension());
        if (dimension != null)
        {
            dimension.remove(variant);
        }
    }
}
