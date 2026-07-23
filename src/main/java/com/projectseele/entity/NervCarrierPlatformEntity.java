package com.projectseele.entity;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.material.PushReaction;
import net.minecraft.world.phys.Vec3;

/**
 * Ephemeral visual mag-lev deck. It replaces thousands of moving block
 * updates while the EVA itself remains the authoritative physical vehicle.
 */
public final class NervCarrierPlatformEntity extends Entity
{
    private static final EntityDataAccessor<Integer> DATA_VARIANT =
            SynchedEntityData.defineId(NervCarrierPlatformEntity.class,
                    EntityDataSerializers.INT);
    private static final int CONTROL_TIMEOUT_TICKS = 10;

    private int ticksWithoutControl;

    public NervCarrierPlatformEntity(
            EntityType<? extends NervCarrierPlatformEntity> type, Level level)
    {
        super(type, level);
        this.noPhysics = true;
        this.setNoGravity(true);
    }

    @Override
    protected void defineSynchedData()
    {
        this.entityData.define(DATA_VARIANT, EvaUnit01Entity.UNIT_01);
    }

    public int getUnitVariant()
    {
        return this.entityData.get(DATA_VARIANT);
    }

    public void assignVariant(int variant)
    {
        this.entityData.set(DATA_VARIANT, Math.max(EvaUnit01Entity.UNIT_00,
                Math.min(EvaUnit01Entity.UNIT_02, variant)));
    }

    public void moveControlled(double x, double y, double z)
    {
        this.ticksWithoutControl = 0;
        this.setPos(x, y, z);
        this.setDeltaMovement(Vec3.ZERO);
        this.hasImpulse = true;
    }

    @Override
    public void tick()
    {
        super.tick();
        this.noPhysics = true;
        this.setNoGravity(true);
        this.setDeltaMovement(Vec3.ZERO);
        if (!this.level().isClientSide
                && ++this.ticksWithoutControl > CONTROL_TIMEOUT_TICKS)
        {
            this.discard();
        }
    }

    @Override
    protected void readAdditionalSaveData(CompoundTag tag)
    {
        if (tag.contains("EvaVariant"))
        {
            this.assignVariant(tag.getInt("EvaVariant"));
        }
    }

    @Override
    protected void addAdditionalSaveData(CompoundTag tag)
    {
        tag.putInt("EvaVariant", this.getUnitVariant());
    }

    @Override
    public boolean hurt(DamageSource source, float amount)
    {
        return false;
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
    public PushReaction getPistonPushReaction()
    {
        return PushReaction.IGNORE;
    }
}
