package com.projectseele.entity;

import java.util.UUID;
import java.util.Optional;

import javax.annotation.Nullable;

import com.projectseele.world.EvaArmamentRackBlockEntity;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.material.PushReaction;
import net.minecraft.world.phys.Vec3;

/** One persistent full-scale armament from underground rack to EVA handoff. */
public final class EvaWeaponEntity extends Entity
{
    public static final int STAGE_RACKED = 0;
    public static final int STAGE_LOADING_LOCKED = 1;
    public static final int STAGE_ASCENDING = 2;
    public static final int STAGE_TOP_DOCKING = 3;
    public static final int STAGE_PRESENTED_LOCKED = 4;
    public static final int STAGE_GRIP_VERIFY = 5;
    public static final int STAGE_RELEASED_TO_EVA = 6;
    public static final int STAGE_RETURNING = 7;
    public static final int STAGE_EMERGENCY_STOP = 8;
    public static final int STAGE_FAULT = 9;

    public static final int ATTACHMENT_RACK = 0;
    public static final int ATTACHMENT_PLATFORM = 1;
    public static final int ATTACHMENT_EVA = 2;
    public static final int ATTACHMENT_HANDOFF = 3;
    public static final int ATTACHMENT_FAULT = 4;

    private static final EntityDataAccessor<Integer> DATA_WEAPON =
            SynchedEntityData.defineId(EvaWeaponEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_STAGE =
            SynchedEntityData.defineId(EvaWeaponEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> DATA_VISIBLE =
            SynchedEntityData.defineId(EvaWeaponEntity.class,
                    EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Boolean> DATA_LOCKED =
            SynchedEntityData.defineId(EvaWeaponEntity.class,
                    EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Integer> DATA_ATTACHMENT =
            SynchedEntityData.defineId(EvaWeaponEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Optional<UUID>>
            DATA_ATTACHMENT_OWNER = SynchedEntityData.defineId(
                    EvaWeaponEntity.class,
                    EntityDataSerializers.OPTIONAL_UUID);
    private static final EntityDataAccessor<Long> DATA_ATTACHMENT_EPOCH =
            SynchedEntityData.defineId(EvaWeaponEntity.class,
                    EntityDataSerializers.LONG);

    @Nullable
    private UUID boundEvaUuid;

    public EvaWeaponEntity(EntityType<? extends EvaWeaponEntity> type,
                           Level level)
    {
        super(type, level);
        this.noPhysics = true;
        this.setNoGravity(true);
    }

    @Override
    protected void defineSynchedData()
    {
        this.entityData.define(DATA_WEAPON, EvaUnit01Entity.WEAPON_KNIFE);
        this.entityData.define(DATA_STAGE, STAGE_RACKED);
        this.entityData.define(DATA_VISIBLE, true);
        this.entityData.define(DATA_LOCKED, true);
        this.entityData.define(DATA_ATTACHMENT, ATTACHMENT_RACK);
        this.entityData.define(DATA_ATTACHMENT_OWNER, Optional.empty());
        this.entityData.define(DATA_ATTACHMENT_EPOCH, 0L);
    }

    public void configurePayload(int weapon)
    {
        int safe = Math.max(EvaUnit01Entity.WEAPON_KNIFE,
                Math.min(EvaUnit01Entity.WEAPON_N2, weapon));
        this.entityData.set(DATA_WEAPON, safe);
        this.setCustomName(Component.literal("NERV EVA ARMAMENT / " + safe));
        this.setCustomNameVisible(false);
    }

    public int getWeapon()
    {
        return this.entityData.get(DATA_WEAPON);
    }

    public ItemStack getPayloadStack()
    {
        return EvaArmamentRackBlockEntity.stackForWeapon(this.getWeapon());
    }

    public int getCarrierStage()
    {
        return this.entityData.get(DATA_STAGE);
    }

    public void setCarrierStage(int stage)
    {
        this.entityData.set(DATA_STAGE, Math.max(STAGE_RACKED,
                Math.min(STAGE_FAULT, stage)));
    }

    public boolean isPayloadVisible()
    {
        return this.entityData.get(DATA_VISIBLE);
    }

    public boolean isTransportLocked()
    {
        return this.entityData.get(DATA_LOCKED);
    }

    public void setTransportLocked(boolean locked)
    {
        this.entityData.set(DATA_LOCKED, locked);
    }

    public void setPayloadVisible(boolean visible)
    {
        this.entityData.set(DATA_VISIBLE, visible);
    }

    public int getAttachmentMode()
    {
        return this.entityData.get(DATA_ATTACHMENT);
    }

    public Optional<UUID> getAttachmentOwnerId()
    {
        return this.entityData.get(DATA_ATTACHMENT_OWNER);
    }

    public long getAttachmentEpoch()
    {
        return this.entityData.get(DATA_ATTACHMENT_EPOCH);
    }

    private void setAttachment(int mode, @Nullable UUID owner, long epoch)
    {
        this.entityData.set(DATA_ATTACHMENT, Math.max(ATTACHMENT_RACK,
                Math.min(ATTACHMENT_FAULT, mode)));
        this.entityData.set(DATA_ATTACHMENT_OWNER,
                Optional.ofNullable(owner));
        this.entityData.set(DATA_ATTACHMENT_EPOCH, Math.max(0L, epoch));
    }

    /** Attach this exact payload identity to the locked mechanical cradle. */
    public boolean mountOnPlatform(NervCarrierPlatformEntity platform,
                                   int stage)
    {
        return this.mountOnPlatform(platform, stage,
                Math.max(1L, this.getAttachmentEpoch()));
    }

    public boolean mountOnPlatform(NervCarrierPlatformEntity platform,
                                   int stage, long epoch)
    {
        if (this.level().isClientSide || platform.level() != this.level()
                || !platform.isArmamentLift()
                || !platform.getPassengers().isEmpty())
        {
            return false;
        }
        this.stopRiding();
        this.boundEvaUuid = null;
        this.entityData.set(DATA_VISIBLE, true);
        this.entityData.set(DATA_LOCKED, true);
        this.setCarrierStage(stage);
        this.setPos(platform.getX(), platform.getY() + 0.34D,
                platform.getZ());
        this.setYRot(platform.getYRot());
        if (!this.startRiding(platform, true))
        {
            return false;
        }
        this.setAttachment(ATTACHMENT_PLATFORM, platform.getUUID(), epoch);
        return true;
    }

    @Nullable
    public UUID getBoundEvaUuid()
    {
        return this.boundEvaUuid;
    }

    /**
     * The payload may be physically parented to the cradle or logically
     * parented to one EVA, never both and never neither while a lift
     * transaction is active.  Handoff intent deliberately does not change
     * this physical ownership until the matching commit succeeds.
     */
    public boolean hasExclusiveTransportOwner(UUID platformId,
                                               @Nullable UUID evaId)
    {
        Entity vehicle = this.getVehicle();
        boolean platformOwned = vehicle instanceof NervCarrierPlatformEntity
                && vehicle.getUUID().equals(platformId);
        boolean evaOwned = vehicle == null && evaId != null
                && this.boundEvaUuid != null
                && this.boundEvaUuid.equals(evaId);
        return platformOwned != evaOwned;
    }

    public boolean isAttachedToPlatform(NervCarrierPlatformEntity platform,
                                        long epoch)
    {
        return this.getAttachmentMode() == ATTACHMENT_PLATFORM
                && this.getAttachmentEpoch() == epoch
                && this.getAttachmentOwnerId().filter(
                        platform.getUUID()::equals).isPresent()
                && this.getVehicle() == platform
                && platform.isExpectedArmamentPayload(this);
    }

    public boolean isAttachedToEva(EvaUnit01Entity eva, long epoch)
    {
        return this.getAttachmentMode() == ATTACHMENT_EVA
                && this.getAttachmentEpoch() == epoch
                && this.getAttachmentOwnerId().filter(
                        eva.getUUID()::equals).isPresent()
                && this.boundEvaUuid != null
                && this.boundEvaUuid.equals(eva.getUUID())
                && this.getVehicle() == null;
    }

    public boolean isHandoffTo(Entity target, long epoch)
    {
        return this.getAttachmentMode() == ATTACHMENT_HANDOFF
                && this.getAttachmentEpoch() == epoch
                && this.getAttachmentOwnerId().filter(
                        target.getUUID()::equals).isPresent();
    }

    /** Persist the intended new parent before changing any ride relation. */
    public boolean beginHandoff(Entity target, long epoch)
    {
        if (this.isHandoffTo(target, epoch))
        {
            return true;
        }
        if (this.level().isClientSide || target.level() != this.level()
                || epoch <= this.getAttachmentEpoch()
                || (!(target instanceof EvaUnit01Entity)
                    && !(target instanceof NervCarrierPlatformEntity)))
        {
            return false;
        }
        this.setAttachment(ATTACHMENT_HANDOFF, target.getUUID(), epoch);
        this.entityData.set(DATA_LOCKED, true);
        return true;
    }

    /** Preserve this UUID while the EVA renderer owns the visible hand mesh. */
    public boolean bindToEva(EvaUnit01Entity eva)
    {
        long epoch = Math.max(1L, this.getAttachmentEpoch() + 1L);
        if (!this.beginHandoff(eva, epoch))
        {
            return false;
        }
        return this.commitToEva(eva, epoch);
    }

    public boolean commitToEva(EvaUnit01Entity eva, long epoch)
    {
        if (this.level().isClientSide || eva.level() != this.level())
        {
            return false;
        }
        if (this.isAttachedToEva(eva, epoch))
        {
            return true;
        }
        if (!this.isHandoffTo(eva, epoch)
                || !eva.equipRackArmament(this.getWeapon()))
        {
            return false;
        }
        this.stopRiding();
        this.boundEvaUuid = eva.getUUID();
        this.entityData.set(DATA_VISIBLE, false);
        this.entityData.set(DATA_LOCKED, false);
        this.setCarrierStage(STAGE_RELEASED_TO_EVA);
        this.setAttachment(ATTACHMENT_EVA, eva.getUUID(), epoch);
        this.followBoundEva(eva);
        return true;
    }

    public boolean commitToPlatform(NervCarrierPlatformEntity platform,
                                    int stage, long epoch)
    {
        if (this.level().isClientSide || platform.level() != this.level())
        {
            return false;
        }
        if (this.isAttachedToPlatform(platform, epoch))
        {
            return true;
        }
        if (!this.isHandoffTo(platform, epoch)
                || !platform.isArmamentLift()
                || !platform.getPassengers().isEmpty())
        {
            return false;
        }
        this.stopRiding();
        this.boundEvaUuid = null;
        this.entityData.set(DATA_VISIBLE, true);
        this.entityData.set(DATA_LOCKED, true);
        this.setCarrierStage(stage);
        this.setPos(platform.getX(), platform.getY() + 0.34D,
                platform.getZ());
        this.setYRot(platform.getYRot());
        if (!this.startRiding(platform, true))
        {
            return false;
        }
        this.setAttachment(ATTACHMENT_PLATFORM, platform.getUUID(), epoch);
        return true;
    }

    public void releaseFromEva(Vec3 position)
    {
        this.boundEvaUuid = null;
        this.entityData.set(DATA_VISIBLE, true);
        this.entityData.set(DATA_LOCKED, false);
        this.setCarrierStage(STAGE_RACKED);
        this.setAttachment(ATTACHMENT_RACK, null,
                this.getAttachmentEpoch());
        this.setPos(position);
    }

    /** The rack accepts the payload only after the lift is level at bottom. */
    public void markStored()
    {
        this.markStored(this.position());
    }

    public void markStored(Vec3 position)
    {
        this.boundEvaUuid = null;
        this.entityData.set(DATA_VISIBLE, false);
        this.entityData.set(DATA_LOCKED, true);
        this.setCarrierStage(STAGE_RACKED);
        this.stopRiding();
        this.setAttachment(ATTACHMENT_RACK, null,
                this.getAttachmentEpoch());
        this.setPos(position);
    }

    @Override
    public void tick()
    {
        super.tick();
        this.noPhysics = true;
        this.setNoGravity(true);
        this.setDeltaMovement(Vec3.ZERO);
        if (!this.level().isClientSide
                && this.getAttachmentMode() == ATTACHMENT_EVA
                && this.boundEvaUuid != null
                && this.level() instanceof ServerLevel serverLevel)
        {
            Entity entity = serverLevel.getEntity(this.boundEvaUuid);
            if (entity instanceof EvaUnit01Entity eva && eva.isAlive())
            {
                this.followBoundEva(eva);
            }
            else if (entity != null)
            {
                this.setCarrierStage(STAGE_FAULT);
                this.setAttachment(ATTACHMENT_FAULT, null,
                        this.getAttachmentEpoch());
            }
        }
    }

    private void followBoundEva(EvaUnit01Entity eva)
    {
        this.setPos(eva.getX(), eva.getY() + EvaScale.NORMAL_HEIGHT * 0.55D,
                eva.getZ());
    }

    /** Prevents one-frame interpolation from an obsolete pre-unload pose. */
    public void resetInterpolationFrame()
    {
        this.xo = this.getX();
        this.yo = this.getY();
        this.zo = this.getZ();
        this.yRotO = this.getYRot();
        this.xRotO = this.getXRot();
    }

    @Override
    protected void addAdditionalSaveData(CompoundTag tag)
    {
        tag.putInt("Weapon", this.getWeapon());
        tag.putInt("CarrierStage", this.getCarrierStage());
        tag.putBoolean("PayloadVisible", this.isPayloadVisible());
        tag.putBoolean("TransportLocked", this.isTransportLocked());
        tag.putInt("Attachment", this.getAttachmentMode());
        this.getAttachmentOwnerId().ifPresent(
                owner -> tag.putUUID("AttachmentOwner", owner));
        tag.putLong("AttachmentEpoch", this.getAttachmentEpoch());
        if (this.boundEvaUuid != null)
        {
            tag.putUUID("BoundEva", this.boundEvaUuid);
        }
    }

    @Override
    protected void readAdditionalSaveData(CompoundTag tag)
    {
        this.configurePayload(tag.getInt("Weapon"));
        this.setCarrierStage(tag.getInt("CarrierStage"));
        this.entityData.set(DATA_VISIBLE,
                !tag.contains("PayloadVisible")
                        || tag.getBoolean("PayloadVisible"));
        this.entityData.set(DATA_LOCKED,
                !tag.contains("TransportLocked")
                        || tag.getBoolean("TransportLocked"));
        this.boundEvaUuid = tag.hasUUID("BoundEva")
                ? tag.getUUID("BoundEva") : null;
        if (tag.contains("Attachment"))
        {
            this.setAttachment(tag.getInt("Attachment"),
                    tag.hasUUID("AttachmentOwner")
                            ? tag.getUUID("AttachmentOwner") : null,
                    tag.getLong("AttachmentEpoch"));
        }
        else if (this.boundEvaUuid != null)
        {
            this.setAttachment(ATTACHMENT_EVA, this.boundEvaUuid, 1L);
        }
        else
        {
            this.setAttachment(this.getCarrierStage() == STAGE_RACKED
                            ? ATTACHMENT_RACK : ATTACHMENT_PLATFORM,
                    null, 1L);
        }
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
