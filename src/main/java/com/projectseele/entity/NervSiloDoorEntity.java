package com.projectseele.entity;

import com.projectseele.registry.ModEntities;
import java.util.Comparator;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.PushReaction;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.NetworkHooks;

/** Synchronized visual plus physical weather seal for one EVA surface hatch. */
public final class NervSiloDoorEntity extends Entity
{
    private static final int PHYSICAL_RADIUS = 15;
    // setBlock already updates collision and heightmaps.  Cascading neighbour
    // shape work over 2,883 hatch cells only creates a first-load stall.
    private static final int UPDATE = Block.UPDATE_CLIENTS;
    private static final BlockState PHYSICAL_HATCH =
            Blocks.BARRIER.defaultBlockState();
    private static final Map<ServerLevel,Set<Integer>> SEALED =
            Collections.synchronizedMap(new WeakHashMap<>());
    private static final EntityDataAccessor<Integer> DATA_VARIANT =
            SynchedEntityData.defineId(NervSiloDoorEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Float> DATA_OPEN =
            SynchedEntityData.defineId(NervSiloDoorEntity.class,
                    EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> DATA_TARGET =
            SynchedEntityData.defineId(NervSiloDoorEntity.class,
                    EntityDataSerializers.FLOAT);

    private float clientOpen;
    private float clientOpenO;

    public NervSiloDoorEntity(EntityType<? extends NervSiloDoorEntity> type,
                              Level level)
    {
        super(type, level);
        this.noPhysics = true;
        this.noCulling = true;
        this.setNoGravity(true);
        this.setInvulnerable(true);
    }

    @Override
    protected void defineSynchedData()
    {
        this.entityData.define(DATA_VARIANT, 0);
        this.entityData.define(DATA_OPEN, 0.0F);
        this.entityData.define(DATA_TARGET, 0.0F);
    }

    @Override
    protected void readAdditionalSaveData(CompoundTag tag)
    {
    }

    @Override
    protected void addAdditionalSaveData(CompoundTag tag)
    {
    }

    @Override
    public Packet<ClientGamePacketListener> getAddEntityPacket()
    {
        return NetworkHooks.getEntitySpawningPacket(this);
    }

    @Override
    public void tick()
    {
        super.tick();
        this.setDeltaMovement(Vec3.ZERO);
        if (this.level().isClientSide)
        {
            this.clientOpenO = this.clientOpen;
            this.clientOpen = this.entityData.get(DATA_OPEN);
            return;
        }
        float current = this.entityData.get(DATA_OPEN);
        float target = this.entityData.get(DATA_TARGET);
        float next = Mth.approach(current, target, 0.10F);
        if (Math.abs(next - current) > 1.0E-4F)
        {
            this.entityData.set(DATA_OPEN, next);
        }
    }

    public int getVariant()
    {
        return this.entityData.get(DATA_VARIANT);
    }

    public float getOpenProgress(float partialTick)
    {
        return Mth.lerp(partialTick, this.clientOpenO, this.clientOpen);
    }

    public void setTargetOpen(float target)
    {
        float clamped = Mth.clamp(target, 0.0F, 1.0F);
        if (Math.abs(this.entityData.get(DATA_TARGET) - clamped) > 1.0E-4F)
        {
            this.entityData.set(DATA_TARGET, clamped);
        }
    }

    public static void reconcile(ServerLevel level, int variant,
            BlockPos surfaceBed, float targetOpen)
    {
        Vec3 centre = new Vec3(surfaceBed.getX() + 0.5D,
                surfaceBed.getY() + 1.01D,
                surfaceBed.getZ() + 0.5D);
        AABB search = new AABB(centre, centre).inflate(3.0D, 3.0D, 3.0D);
        List<NervSiloDoorEntity> matches = level.getEntitiesOfClass(
                NervSiloDoorEntity.class, search,
                entity -> entity.getVariant() == variant);
        matches.sort(Comparator.comparingInt(Entity::getId));
        NervSiloDoorEntity door;
        if (matches.isEmpty())
        {
            door = ModEntities.NERV_SILO_DOOR.get().create(level);
            if (door == null)
            {
                return;
            }
            door.entityData.set(DATA_VARIANT, variant);
            door.setPos(centre);
            level.addFreshEntity(door);
        }
        else
        {
            door = matches.get(0);
            if (door.position().distanceToSqr(centre) > 1.0E-8D)
            {
                door.setPos(centre);
            }
            for (int index = 1; index < matches.size(); index++)
            {
                matches.get(index).discard();
            }
        }
        door.setTargetOpen(targetOpen);
        synchronizePhysicalHatch(level, variant, surfaceBed, door,
                targetOpen);
    }

    private static void synchronizePhysicalHatch(ServerLevel level,
            int variant, BlockPos surfaceBed, NervSiloDoorEntity door,
            float targetOpen)
    {
        Set<Integer> sealed = SEALED.computeIfAbsent(level,
                ignored -> new HashSet<>());
        BlockPos planeCentre = surfaceBed.above();
        boolean ownsPhysicalLayer = sealed.contains(variant)
                || level.getBlockState(planeCentre).is(PHYSICAL_HATCH.getBlock());

        if (targetOpen > 1.0E-3F)
        {
            if (!ownsPhysicalLayer)
            {
                return;
            }
            BlockPos.MutableBlockPos cursor = new BlockPos.MutableBlockPos();
            for (int dx = -PHYSICAL_RADIUS; dx <= PHYSICAL_RADIUS; dx++)
            {
                for (int dz = -PHYSICAL_RADIUS; dz <= PHYSICAL_RADIUS; dz++)
                {
                    cursor.set(planeCentre.getX() + dx,
                            planeCentre.getY(), planeCentre.getZ() + dz);
                    if (level.hasChunkAt(cursor)
                            && !level.getBlockState(cursor).isAir())
                    {
                        // An open launch mouth is an unconditional 31x31 air
                        // aperture. Older revisions only removed barriers and
                        // could leave individual trim blocks in the centre.
                        level.setBlock(cursor, Blocks.AIR.defaultBlockState(),
                                UPDATE);
                    }
                }
            }
            sealed.remove(variant);
            return;
        }

        // Do not pop a solid roof under an open animated leaf.  The physical
        // layer appears only once the synchronized visual is nearly closed.
        if (door.entityData.get(DATA_OPEN) > 0.05F || sealed.contains(variant))
        {
            return;
        }
        boolean complete = true;
        BlockPos.MutableBlockPos cursor = new BlockPos.MutableBlockPos();
        for (int dx = -PHYSICAL_RADIUS; dx <= PHYSICAL_RADIUS; dx++)
        {
            for (int dz = -PHYSICAL_RADIUS; dz <= PHYSICAL_RADIUS; dz++)
            {
                cursor.set(planeCentre.getX() + dx,
                        planeCentre.getY(), planeCentre.getZ() + dz);
                if (!level.hasChunkAt(cursor))
                {
                    complete = false;
                    continue;
                }
                if (!level.getBlockState(cursor).equals(PHYSICAL_HATCH))
                {
                    level.setBlock(cursor, PHYSICAL_HATCH, UPDATE);
                }
            }
        }
        if (complete)
        {
            sealed.add(variant);
        }
    }

    @Override
    public boolean isPickable()
    {
        return false;
    }

    @Override
    public boolean isPushable()
    {
        return false;
    }

    @Override
    public boolean hurt(DamageSource source, float amount)
    {
        return false;
    }

    @Override
    public PushReaction getPistonPushReaction()
    {
        return PushReaction.IGNORE;
    }
}
