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
        this.setYRot(180.0F);
        this.yBodyRot = 180.0F;
        this.yHeadRot = 180.0F;
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
