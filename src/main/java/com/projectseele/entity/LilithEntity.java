package com.projectseele.entity;

import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.util.GeckoLibUtil;

/** Immobile, invulnerable Terminal Dogma specimen and local mesh anchor. */
public class LilithEntity extends PathfinderMob implements GeoEntity
{
    private static final net.minecraft.network.syncher.EntityDataAccessor<Float> CONTAINMENT_SCALE=net.minecraft.network.syncher.SynchedEntityData.defineId(LilithEntity.class,net.minecraft.network.syncher.EntityDataSerializers.FLOAT);
    @Override protected void defineSynchedData(){super.defineSynchedData();this.entityData.define(CONTAINMENT_SCALE,1F);}
    public float getContainmentScale(){return this.entityData.get(CONTAINMENT_SCALE);}
    public void setContainmentScale(float value){this.entityData.set(CONTAINMENT_SCALE,net.minecraft.util.Mth.clamp(value,.5F,2F));}
    @Override public void addAdditionalSaveData(net.minecraft.nbt.CompoundTag tag){super.addAdditionalSaveData(tag);tag.putFloat("ContainmentScale",getContainmentScale());}
    @Override public void readAdditionalSaveData(net.minecraft.nbt.CompoundTag tag){super.readAdditionalSaveData(tag);setContainmentScale(tag.contains("ContainmentScale")?tag.getFloat("ContainmentScale"):1F);}
    private final AnimatableInstanceCache geoCache =
            GeckoLibUtil.createInstanceCache(this);

    public LilithEntity(EntityType<? extends LilithEntity> type, Level level)
    {
        super(type, level);
        this.noPhysics = true;
        this.setNoGravity(true);
        this.setPersistenceRequired();
    }

    public static AttributeSupplier.Builder createAttributes()
    {
        return Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 1000.0D)
                .add(Attributes.MOVEMENT_SPEED, 0.0D)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0D);
    }

    @Override
    protected void registerGoals()
    {
        // Lilith is an architectural containment specimen, not an AI actor.
    }

    @Override
    public void tick()
    {
        super.tick();
        this.noPhysics = true;
        this.setNoGravity(true);
        this.setDeltaMovement(Vec3.ZERO);
        this.fallDistance = 0.0F;
        // The imported south-wall mesh faces arrivals at zero yaw.
        this.setYRot(0.0F);
        this.yBodyRot = 0.0F;
        this.yHeadRot = 0.0F;
    }

    @Override
    public boolean hurt(DamageSource source, float amount)
    {
        return false;
    }

    @Override
    public boolean isPushable()
    {
        return false;
    }

    @Override
    public boolean canBeCollidedWith()
    {
        return false;
    }

    @Override
    public boolean removeWhenFarAway(double distanceToClosestPlayer)
    {
        return false;
    }

    @Override
    public void registerControllers(
            AnimatableManager.ControllerRegistrar controllers)
    {
        // The reviewed model is intentionally static on the crucifix.
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache()
    {
        return this.geoCache;
    }
}
