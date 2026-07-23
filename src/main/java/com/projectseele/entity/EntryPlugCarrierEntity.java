package com.projectseele.entity;

import com.projectseele.world.EntryPlugDirector;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * Physical, passenger-carrying entry plug suspended above an EVA wet cage.
 * It exists separately from the EVA so boarding and insertion are observable.
 */
public final class EntryPlugCarrierEntity extends PathfinderMob
        implements GeoEntity
{
    public static final int STAGE_SUSPENDED = 0;
    public static final int STAGE_OCCUPIED = 1;
    public static final int STAGE_INSERTING = 2;

    private static final EntityDataAccessor<Integer> DATA_VARIANT =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_STAGE =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_PROGRESS =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.INT);

    private final AnimatableInstanceCache geoCache =
            GeckoLibUtil.createInstanceCache(this);

    public EntryPlugCarrierEntity(
            EntityType<? extends EntryPlugCarrierEntity> type, Level level)
    {
        super(type, level);
        this.noPhysics = true;
        this.setNoGravity(true);
        this.setPersistenceRequired();
    }

    public static AttributeSupplier.Builder createAttributes()
    {
        return Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 40.0D)
                .add(Attributes.MOVEMENT_SPEED, 0.0D)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0D);
    }

    @Override
    protected void registerGoals()
    {
        // The overhead insertion crane is the sole movement authority.
    }

    @Override
    protected void defineSynchedData()
    {
        super.defineSynchedData();
        this.entityData.define(DATA_VARIANT, EvaUnit01Entity.UNIT_01);
        this.entityData.define(DATA_STAGE, STAGE_SUSPENDED);
        this.entityData.define(DATA_PROGRESS, 0);
    }

    public int getAssignedVariant()
    {
        return this.entityData.get(DATA_VARIANT);
    }

    public void assignVariant(int variant)
    {
        int safe = Math.max(EvaUnit01Entity.UNIT_00,
                Math.min(EvaUnit01Entity.UNIT_02, variant));
        this.entityData.set(DATA_VARIANT, safe);
        this.setCustomName(Component.literal(String.format(
                "NERV ENTRY PLUG / EVA-%02d", safe)));
        this.setCustomNameVisible(false);
    }

    public int getInsertionStage()
    {
        return this.entityData.get(DATA_STAGE);
    }

    public void setInsertionStage(int stage)
    {
        this.entityData.set(DATA_STAGE, stage);
    }

    public int getInsertionProgress()
    {
        return this.entityData.get(DATA_PROGRESS);
    }

    public void setInsertionProgress(int progress)
    {
        this.entityData.set(DATA_PROGRESS, Math.max(0, Math.min(100, progress)));
    }

    public boolean boardPassenger(Entity passenger)
    {
        if (this.level().isClientSide || this.getInsertionStage()
                == STAGE_INSERTING || this.isVehicle()
                || passenger.isPassenger())
        {
            return false;
        }
        if (!passenger.startRiding(this, true))
        {
            return false;
        }
        this.setInsertionStage(STAGE_OCCUPIED);
        this.level().playSound(null, this.blockPosition(),
                SoundEvents.IRON_TRAPDOOR_CLOSE, SoundSource.BLOCKS,
                1.2F, 0.72F);
        return true;
    }

    @Override
    public InteractionResult mobInteract(Player player, InteractionHand hand)
    {
        if (this.level().isClientSide)
        {
            return InteractionResult.SUCCESS;
        }
        if (this.getInsertionStage() == STAGE_INSERTING)
        {
            player.displayClientMessage(Component.literal(
                    "Entry plug is already under crane control."), true);
            return InteractionResult.CONSUME;
        }
        if (this.isVehicle())
        {
            player.displayClientMessage(Component.literal(
                    "Entry plug is already occupied."), true);
            return InteractionResult.CONSUME;
        }
        return this.boardPassenger(player)
                ? InteractionResult.CONSUME : InteractionResult.FAIL;
    }

    @Override
    protected boolean canAddPassenger(Entity passenger)
    {
        return this.getPassengers().isEmpty()
                && (passenger instanceof Player
                    || passenger instanceof TrainingPilotEntity);
    }

    @Override
    protected void positionRider(Entity passenger, Entity.MoveFunction move)
    {
        if (!this.hasPassenger(passenger))
        {
            return;
        }
        double seatY = this.getY() + 0.35D - passenger.getBbHeight() * 0.5D;
        move.accept(passenger, this.getX(), seatY, this.getZ());
        passenger.setYRot(this.getYRot());
        passenger.setXRot(this.getXRot());
    }

    @Override
    public Vec3 getDismountLocationForPassenger(
            net.minecraft.world.entity.LivingEntity passenger)
    {
        float radians = (float) Math.toRadians(this.getYRot());
        return this.position().add(Math.cos(radians) * 2.0D,
                -2.0D, Math.sin(radians) * 2.0D);
    }

    @Override
    public void tick()
    {
        super.tick();
        this.noPhysics = true;
        this.setNoGravity(true);
        this.setDeltaMovement(Vec3.ZERO);
        this.fallDistance = 0.0F;
        for (Entity passenger : this.getPassengers())
        {
            this.positionRider(passenger, Entity::setPos);
        }
        if (!this.level().isClientSide)
        {
            EntryPlugDirector.keepPassengerState(this);
        }
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
    public boolean removeWhenFarAway(double distanceToClosestPlayer)
    {
        return false;
    }

    @Override
    public void addAdditionalSaveData(CompoundTag tag)
    {
        super.addAdditionalSaveData(tag);
        tag.putInt("EvaVariant", this.getAssignedVariant());
        tag.putInt("InsertionStage", this.getInsertionStage());
        tag.putInt("InsertionProgress", this.getInsertionProgress());
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag)
    {
        super.readAdditionalSaveData(tag);
        if (tag.contains("EvaVariant"))
        {
            this.assignVariant(tag.getInt("EvaVariant"));
        }
        if (tag.contains("InsertionStage"))
        {
            this.setInsertionStage(tag.getInt("InsertionStage"));
        }
        if (tag.contains("InsertionProgress"))
        {
            this.setInsertionProgress(tag.getInt("InsertionProgress"));
        }
    }

    @Override
    public void registerControllers(
            AnimatableManager.ControllerRegistrar controllers)
    {
        // The logistics director supplies the physical transform.
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache()
    {
        return this.geoCache;
    }
}
