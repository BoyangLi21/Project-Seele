package com.projectseele.entity;

import java.util.Optional;
import java.util.UUID;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.core.Direction;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.material.PushReaction;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import com.projectseele.world.S20PhysicalElevatorDirector;

/**
 * Ephemeral visual mag-lev deck. It replaces thousands of moving block
 * updates while the EVA itself remains the authoritative physical vehicle.
 */
public final class NervCarrierPlatformEntity extends Entity
{
    private static final EntityDataAccessor<Integer> DATA_VARIANT =
            SynchedEntityData.defineId(NervCarrierPlatformEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> DATA_PERSONNEL_LIFT =
            SynchedEntityData.defineId(NervCarrierPlatformEntity.class,
                    EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Integer> DATA_LIFT_ACCENT =
            SynchedEntityData.defineId(NervCarrierPlatformEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> DATA_LIFT_DOOR_OPEN =
            SynchedEntityData.defineId(NervCarrierPlatformEntity.class,
                    EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Boolean> DATA_PERSISTENT_LIFT =
            SynchedEntityData.defineId(NervCarrierPlatformEntity.class,
                    EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<String> DATA_LIFT_ID =
            SynchedEntityData.defineId(NervCarrierPlatformEntity.class,
                    EntityDataSerializers.STRING);
    private static final EntityDataAccessor<Integer> DATA_LIFT_EXIT =
            SynchedEntityData.defineId(NervCarrierPlatformEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> DATA_ARMAMENT_LIFT =
            SynchedEntityData.defineId(NervCarrierPlatformEntity.class,
                    EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<String> DATA_ARMAMENT_SYSTEM_ID =
            SynchedEntityData.defineId(NervCarrierPlatformEntity.class,
                    EntityDataSerializers.STRING);
    private static final EntityDataAccessor<Optional<UUID>>
            DATA_ARMAMENT_PAYLOAD_ID = SynchedEntityData.defineId(
                    NervCarrierPlatformEntity.class,
                    EntityDataSerializers.OPTIONAL_UUID);
    private static final int CONTROL_TIMEOUT_TICKS = 10;
    public static final int LIFT_IDLE_OPEN = 0;
    public static final int LIFT_DOOR_CLOSING = 1;
    public static final int LIFT_STARTING = 2;
    public static final int LIFT_MOVING = 3;
    public static final int LIFT_BRAKING = 4;
    public static final int LIFT_LEVELING = 5;
    public static final int LIFT_DOOR_OPENING = 6;
    public static final int LIFT_FAULT = 7;
    public static final int LIFT_RECOVERY_HOLD = 8;
    private static final int DOOR_CLOSE_TICKS = 60;
    private static final int DOOR_OPEN_TICKS = 20;
    private static final int DOOR_SLIDE_TICKS = 20;
    private static final int MAX_LIFT_PASSENGERS = 9;
    private static final int CONTROL_DEBOUNCE_TICKS = 6;
    private static final double LIFT_MAX_SPEED = 1.6D;
    private static final double LIFT_ACCELERATION = 0.04D;
    private static final double LIFT_LEVELING_SPEED = 0.15D;
    private static final double LIFT_ARRIVAL_TOLERANCE = 0.03D;
    /** Even the 523-block surface shaft completes well inside this window. */
    private static final int LIFT_TRAVEL_WATCHDOG_TICKS = 1200;

    private int ticksWithoutControl;
    private int persistentLiftState = LIFT_IDLE_OPEN;
    private int persistentLiftPhaseTicks;
    private double persistentLiftTargetY;
    private double persistentLiftVelocity;
    private int persistentLiftStateRevision;
    private long persistentLiftLastMotionEpoch;
    private long persistentLiftPendingMotionEpoch;
    private long persistentLiftActiveMotionEpoch;
    private double persistentLiftLowerY = Double.NaN;
    private double persistentLiftUpperY = Double.NaN;
    private long lastPersistentLiftControlTick = Long.MIN_VALUE;

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
        this.entityData.define(DATA_PERSONNEL_LIFT, false);
        this.entityData.define(DATA_LIFT_ACCENT, 0);
        this.entityData.define(DATA_LIFT_DOOR_OPEN, false);
        this.entityData.define(DATA_PERSISTENT_LIFT, false);
        this.entityData.define(DATA_LIFT_ID, "");
        this.entityData.define(DATA_LIFT_EXIT,
                Direction.NORTH.get2DDataValue());
        this.entityData.define(DATA_ARMAMENT_LIFT, false);
        this.entityData.define(DATA_ARMAMENT_SYSTEM_ID, "");
        this.entityData.define(DATA_ARMAMENT_PAYLOAD_ID, Optional.empty());
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

    /**
     * Reuses the tracked, non-saving carrier entity as a human-scale lift
     * cabin. The server still owns passenger motion; this flag only changes
     * the client silhouette and door state.
     */
    public void configurePersonnelLift(int accent)
    {
        this.entityData.set(DATA_PERSONNEL_LIFT, true);
        this.entityData.set(DATA_LIFT_ACCENT, Math.max(0,
                Math.min(4, accent)));
    }

    /**
     * Configures a saved, continuously present lift cabin. This mode is
     * intentionally separate from the short-lived EVA carrier silhouette.
     */
    public void configurePersistentLift(String liftId, int accent)
    {
        this.configurePersistentLift(liftId, accent,
                Double.NaN, Double.NaN);
    }

    public void configurePersistentLift(String liftId, int accent,
                                        double lowerY, double upperY)
    {
        this.configurePersonnelLift(accent);
        this.entityData.set(DATA_PERSISTENT_LIFT, true);
        this.entityData.set(DATA_LIFT_ID, liftId == null ? "" : liftId);
        this.persistentLiftState = LIFT_IDLE_OPEN;
        this.persistentLiftPhaseTicks = 0;
        this.persistentLiftTargetY = this.getY();
        this.persistentLiftLowerY = lowerY;
        this.persistentLiftUpperY = upperY;
        this.persistentLiftVelocity = 0.0D;
        this.persistentLiftPendingMotionEpoch = 0L;
        this.persistentLiftActiveMotionEpoch = 0L;
        this.persistentLiftStateRevision++;
        this.setLiftDoorOpen(true);
        this.ticksWithoutControl = 0;
    }

    /**
     * Configures a saved payload-only lift. It deliberately does not enable
     * personnel-lift state or its autonomous door/motion controller: one
     * {@link EvaWeaponEntity} is the only legal passenger and the armament
     * director owns every transform.
     */
    public void configureArmamentLift(String systemId, int variant)
    {
        this.configureArmamentLift(systemId, variant, null);
    }

    public void configureArmamentLift(String systemId, int variant,
                                      UUID payloadId)
    {
        this.assignVariant(variant);
        this.entityData.set(DATA_PERSONNEL_LIFT, false);
        this.entityData.set(DATA_PERSISTENT_LIFT, false);
        this.entityData.set(DATA_ARMAMENT_LIFT, true);
        this.entityData.set(DATA_ARMAMENT_SYSTEM_ID,
                systemId == null ? "" : systemId);
        this.entityData.set(DATA_ARMAMENT_PAYLOAD_ID,
                Optional.ofNullable(payloadId));
        this.setLiftDoorOpen(false);
        this.ticksWithoutControl = 0;
    }

    public boolean isArmamentLift()
    {
        return this.entityData.get(DATA_ARMAMENT_LIFT);
    }

    public String getArmamentSystemId()
    {
        return this.entityData.get(DATA_ARMAMENT_SYSTEM_ID);
    }

    public Optional<UUID> getArmamentPayloadId()
    {
        return this.entityData.get(DATA_ARMAMENT_PAYLOAD_ID);
    }

    public boolean isExpectedArmamentPayload(Entity entity)
    {
        return this.isArmamentLift()
                && entity instanceof EvaWeaponEntity
                && this.getArmamentPayloadId().filter(
                        id -> id.equals(entity.getUUID())).isPresent();
    }

    public boolean isPersistentLift()
    {
        return this.entityData.get(DATA_PERSISTENT_LIFT);
    }

    public String getLiftId()
    {
        return this.entityData.get(DATA_LIFT_ID);
    }

    public int getPersistentLiftState()
    {
        return this.persistentLiftState;
    }

    public boolean isPersistentLiftIdle()
    {
        return this.isPersistentLift()
                && this.persistentLiftState == LIFT_IDLE_OPEN;
    }

    public boolean isPersistentLiftRecoveryHold()
    {
        return this.isPersistentLift()
                && this.persistentLiftState == LIFT_RECOVERY_HOLD;
    }

    public int getPersistentLiftStateRevision()
    {
        return this.persistentLiftStateRevision;
    }

    public double getPersistentLiftTargetY()
    {
        return this.persistentLiftTargetY;
    }

    public void setLiftExit(Direction exit)
    {
        if (exit != null && exit.getAxis() != Direction.Axis.Y)
        {
            this.entityData.set(DATA_LIFT_EXIT, exit.get2DDataValue());
        }
    }

    public Direction getLiftExit()
    {
        return Direction.from2DDataValue(
                this.entityData.get(DATA_LIFT_EXIT));
    }

    /**
     * Arms one already-recorded trip after the fixed landing doors have
     * actually closed.  Unlike the old two-tick heartbeat, this lease cannot
     * expire merely because entity and server-event ticks run in a different
     * order.  The epoch is minted once by the shaft authority for one trip.
     */
    public boolean activatePersistentLiftMotion(long motionEpoch)
    {
        if (!this.isPersistentLift()
                || motionEpoch <= 0L
                || motionEpoch != this.persistentLiftPendingMotionEpoch
                || motionEpoch < this.persistentLiftLastMotionEpoch)
        {
            return false;
        }
        this.persistentLiftActiveMotionEpoch = motionEpoch;
        return true;
    }

    /** Compatibility bridge for the quarantined pre-S20 lift director. */
    @Deprecated
    public void authorizePersistentLiftMotion(boolean allowed)
    {
        if (allowed && this.persistentLiftPendingMotionEpoch > 0L)
        {
            this.activatePersistentLiftMotion(
                    this.persistentLiftPendingMotionEpoch);
        }
        else if (!allowed && this.isPersistentLiftTranslating())
        {
            this.revokePersistentLiftMotion();
        }
    }

    public void revokePersistentLiftMotion()
    {
        this.persistentLiftActiveMotionEpoch = 0L;
        if (this.isPersistentLiftTranslating())
        {
            this.persistentLiftState = LIFT_RECOVERY_HOLD;
            this.persistentLiftVelocity = 0.0D;
            this.persistentLiftPhaseTicks = 0;
            this.persistentLiftStateRevision++;
            this.setLiftDoorOpen(false);
        }
    }

    public long getPersistentLiftLastMotionEpoch()
    {
        return this.persistentLiftLastMotionEpoch;
    }

    public long getPersistentLiftPendingMotionEpoch()
    {
        return this.persistentLiftPendingMotionEpoch;
    }

    public boolean isPersistentLiftTranslating()
    {
        return this.persistentLiftState == LIFT_STARTING
                || this.persistentLiftState == LIFT_MOVING
                || this.persistentLiftState == LIFT_BRAKING
                || this.persistentLiftState == LIFT_LEVELING;
    }

    /**
     * Crash recovery always restarts from rest toward one audited landing.
     * It never resumes a serialized velocity.
     */
    public boolean recoverPersistentLiftTo(double stableFloorY,
                                           long motionEpoch)
    {
        if (!this.isPersistentLiftRecoveryHold()
                || motionEpoch <= this.persistentLiftLastMotionEpoch
                || !this.isValidPersistentLiftTarget(stableFloorY))
        {
            return false;
        }
        this.persistentLiftLastMotionEpoch = motionEpoch;
        this.persistentLiftPendingMotionEpoch = motionEpoch;
        this.persistentLiftActiveMotionEpoch = motionEpoch;
        this.persistentLiftTargetY = stableFloorY;
        this.persistentLiftVelocity = 0.0D;
        this.persistentLiftPhaseTicks = 0;
        this.persistentLiftStateRevision++;
        this.setLiftDoorOpen(false);
        if (Math.abs(this.getY() - stableFloorY)
                <= LIFT_ARRIVAL_TOLERANCE)
        {
            this.finishPersistentLiftTravel();
        }
        else
        {
            this.persistentLiftState = LIFT_STARTING;
        }
        return true;
    }

    /** Compatibility bridge for the quarantined pre-S20 lift director. */
    @Deprecated
    public boolean recoverPersistentLiftTo(double stableFloorY)
    {
        return this.recoverPersistentLiftTo(stableFloorY,
                this.persistentLiftLastMotionEpoch + 1L);
    }

    public void forcePersistentLiftFault()
    {
        if (!this.isPersistentLift())
        {
            return;
        }
        this.persistentLiftState = LIFT_FAULT;
        this.persistentLiftVelocity = 0.0D;
        this.persistentLiftPendingMotionEpoch = 0L;
        this.persistentLiftActiveMotionEpoch = 0L;
        this.persistentLiftStateRevision++;
        this.setLiftDoorOpen(false);
    }

    public boolean isAtLiftY(double y)
    {
        return Math.abs(this.getY() - y) <= 0.08D;
    }

    /**
     * The fixed landing door may mirror the cabin door only while the cabin
     * is level with that landing. During the boarding delay both remain open;
     * once either leaf starts closing every landing is locked.
     */
    public boolean canOpenLandingDoorAt(double y)
    {
        return this.isPersistentLift()
                && this.isLiftDoorOpen()
                && this.isAtLiftY(y)
                && (this.persistentLiftState == LIFT_IDLE_OPEN
                || this.persistentLiftState == LIFT_DOOR_CLOSING);
    }

    public boolean beginPersistentLiftTravel(double targetY,
                                             long motionEpoch)
    {
        if (!this.isPersistentLiftIdle()
                || !this.isValidPersistentLiftTarget(targetY)
                || motionEpoch <= this.persistentLiftLastMotionEpoch
                || Math.abs(this.getY() - targetY)
                <= LIFT_ARRIVAL_TOLERANCE)
        {
            return false;
        }
        this.persistentLiftLastMotionEpoch = motionEpoch;
        this.persistentLiftPendingMotionEpoch = motionEpoch;
        this.persistentLiftActiveMotionEpoch = 0L;
        this.persistentLiftTargetY = targetY;
        this.persistentLiftState = LIFT_DOOR_CLOSING;
        this.persistentLiftPhaseTicks = 0;
        this.persistentLiftStateRevision++;
        // Leave the physical and rendered door open for the first two
        // seconds so the caller can step into the already-present cabin.
        this.setLiftDoorOpen(true);
        return true;
    }

    /** Compatibility bridge for the quarantined pre-S20 lift director. */
    @Deprecated
    public boolean beginPersistentLiftTravel(double targetY)
    {
        return this.beginPersistentLiftTravel(targetY,
                this.persistentLiftLastMotionEpoch + 1L);
    }

    public boolean isPersonnelLift()
    {
        return this.entityData.get(DATA_PERSONNEL_LIFT);
    }

    public int getLiftAccent()
    {
        return this.entityData.get(DATA_LIFT_ACCENT);
    }

    public void setLiftDoorOpen(boolean open)
    {
        this.entityData.set(DATA_LIFT_DOOR_OPEN, open);
    }

    public boolean isLiftDoorOpen()
    {
        return this.entityData.get(DATA_LIFT_DOOR_OPEN);
    }

    public void moveControlled(double x, double y, double z)
    {
        this.ticksWithoutControl = 0;
        this.setPos(x, y, z);
        this.setDeltaMovement(Vec3.ZERO);
        this.hasImpulse = true;
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
    public void tick()
    {
        super.tick();
        this.noPhysics = true;
        this.setNoGravity(true);
        this.setDeltaMovement(Vec3.ZERO);
        if (!this.level().isClientSide
                && !this.isPersistentLift() && !this.isArmamentLift()
                && ++this.ticksWithoutControl > CONTROL_TIMEOUT_TICKS)
        {
            this.discard();
        }
        if (!this.level().isClientSide && this.isPersistentLift())
        {
            this.tickPersistentLift();
        }
    }

    @Override
    protected void readAdditionalSaveData(CompoundTag tag)
    {
        if (tag.contains("EvaVariant"))
        {
            this.assignVariant(tag.getInt("EvaVariant"));
        }
        if (tag.getBoolean("PersonnelLift"))
        {
            this.configurePersonnelLift(tag.getInt("LiftAccent"));
            this.setLiftDoorOpen(tag.getBoolean("LiftDoorOpen"));
        }
        if (tag.getBoolean("PersistentLift"))
        {
            this.entityData.set(DATA_PERSISTENT_LIFT, true);
            this.entityData.set(DATA_LIFT_ID, tag.getString("LiftId"));
            if (tag.contains("LiftExit"))
            {
                this.entityData.set(DATA_LIFT_EXIT,
                        tag.getInt("LiftExit"));
            }
            int savedState = tag.getInt("LiftState");
            this.persistentLiftState = isMotionState(savedState)
                    ? LIFT_RECOVERY_HOLD : savedState;
            this.persistentLiftPhaseTicks = tag.getInt("LiftPhaseTicks");
            this.persistentLiftTargetY = tag.getDouble("LiftTargetY");
            this.persistentLiftLowerY = tag.contains("LiftLowerY")
                    ? tag.getDouble("LiftLowerY") : Double.NaN;
            this.persistentLiftUpperY = tag.contains("LiftUpperY")
                    ? tag.getDouble("LiftUpperY") : Double.NaN;
            this.persistentLiftVelocity = 0.0D;
            this.persistentLiftStateRevision =
                    Math.max(0, tag.getInt("LiftStateRevision")) + 1;
            this.persistentLiftLastMotionEpoch = Math.max(0L,
                    tag.getLong("LiftLastMotionEpoch"));
            this.persistentLiftPendingMotionEpoch = 0L;
            this.persistentLiftActiveMotionEpoch = 0L;
            if (this.persistentLiftState == LIFT_RECOVERY_HOLD)
            {
                this.setLiftDoorOpen(false);
            }
        }
        if (tag.getBoolean("ArmamentLift"))
        {
            this.configureArmamentLift(tag.getString("ArmamentSystemId"),
                    tag.getInt("EvaVariant"),
                    tag.hasUUID("ArmamentPayloadId")
                            ? tag.getUUID("ArmamentPayloadId") : null);
        }
    }

    @Override
    protected void addAdditionalSaveData(CompoundTag tag)
    {
        tag.putInt("EvaVariant", this.getUnitVariant());
        tag.putBoolean("PersonnelLift", this.isPersonnelLift());
        tag.putInt("LiftAccent", this.getLiftAccent());
        tag.putBoolean("LiftDoorOpen", this.isLiftDoorOpen());
        tag.putBoolean("PersistentLift", this.isPersistentLift());
        tag.putString("LiftId", this.getLiftId());
        tag.putInt("LiftExit",
                this.entityData.get(DATA_LIFT_EXIT));
        tag.putInt("LiftState", this.persistentLiftState);
        tag.putInt("LiftPhaseTicks", this.persistentLiftPhaseTicks);
        tag.putDouble("LiftTargetY", this.persistentLiftTargetY);
        if (Double.isFinite(this.persistentLiftLowerY)
                && Double.isFinite(this.persistentLiftUpperY))
        {
            tag.putDouble("LiftLowerY", this.persistentLiftLowerY);
            tag.putDouble("LiftUpperY", this.persistentLiftUpperY);
        }
        tag.putDouble("LiftVelocity", this.persistentLiftVelocity);
        tag.putInt("LiftStateRevision", this.persistentLiftStateRevision);
        tag.putLong("LiftLastMotionEpoch",
                this.persistentLiftLastMotionEpoch);
        tag.putBoolean("ArmamentLift", this.isArmamentLift());
        tag.putString("ArmamentSystemId", this.getArmamentSystemId());
        this.getArmamentPayloadId().ifPresent(id ->
                tag.putUUID("ArmamentPayloadId", id));
    }

    @Override
    public boolean hurt(DamageSource source, float amount)
    {
        return false;
    }

    @Override
    public boolean isPickable()
    {
        return this.isPersistentLift() || this.isArmamentLift();
    }

    @Override
    public boolean isPushable()
    {
        return false;
    }

    @Override
    public InteractionResult interact(Player player, InteractionHand hand)
    {
        if (this.isArmamentLift() || !this.isPersistentLift()
                || !this.isPersistentLiftIdle()
                || !this.isLiftDoorOpen())
        {
            return InteractionResult.PASS;
        }
        if (!this.level().isClientSide)
        {
            player.startRiding(this, true);
        }
        return InteractionResult.sidedSuccess(this.level().isClientSide);
    }

    @Override
    public InteractionResult interactAt(Player player, Vec3 hit,
                                        InteractionHand hand)
    {
        if (!this.isPersistentLift()
                || !this.hasConfiguredLiftLandings()
                || !this.isInsidePersistentLiftCabin(player))
        {
            return super.interactAt(player, hit, hand);
        }

        double yaw = Math.toRadians(-this.getYRot());
        double localX = hit.x * Math.cos(yaw) - hit.z * Math.sin(yaw);
        double localZ = hit.x * Math.sin(yaw) + hit.z * Math.cos(yaw);
        boolean onPanel = localX >= 1.85D && localX <= 2.45D
                && localZ >= 0.45D && localZ <= 1.55D
                && hit.y >= 1.00D && hit.y <= 2.15D;
        if (!onPanel)
        {
            return super.interactAt(player, hit, hand);
        }
        if (!this.level().isClientSide)
        {
            if (player instanceof ServerPlayer serverPlayer)
            {
                S20PhysicalElevatorDirector.handleCabinControl(
                        serverPlayer, this, hit.y >= 1.55D);
            }
        }
        return InteractionResult.sidedSuccess(this.level().isClientSide);
    }

    @Override
    public PushReaction getPistonPushReaction()
    {
        return PushReaction.IGNORE;
    }

    @Override
    protected boolean canAddPassenger(Entity passenger)
    {
        if (this.isArmamentLift())
        {
            return this.isExpectedArmamentPayload(passenger)
                    && this.getPassengers().isEmpty();
        }
        return this.isPersistentLift()
                && passenger instanceof Player
                && this.getPassengers().size() < MAX_LIFT_PASSENGERS;
    }

    @Override
    protected void positionRider(Entity passenger, Entity.MoveFunction move)
    {
        if (!this.hasPassenger(passenger))
        {
            return;
        }
        if (this.isArmamentLift())
        {
            if (!this.isExpectedArmamentPayload(passenger))
            {
                passenger.stopRiding();
                return;
            }
            move.accept(passenger, this.getX(), this.getY() + 0.34D,
                    this.getZ());
            passenger.setYRot(this.getYRot());
            passenger.setXRot(0.0F);
            return;
        }
        int index = Math.max(0, this.getPassengers().indexOf(passenger));
        double offsetX = (index % 3 - 1) * 1.15D;
        double offsetZ = (index / 3 - 1) * 0.95D;
        move.accept(passenger, this.getX() + offsetX,
                this.getY() + 0.18D, this.getZ() + offsetZ);
    }

    @Override
    public Vec3 getDismountLocationForPassenger(LivingEntity passenger)
    {
        // Never place a rider outside the car while the shaft is open below
        // them.  Sneak-dismounts and transient client remounts can otherwise
        // eject a player 3.4 blocks into an empty shaft during travel.
        if (this.isPersistentLift()
                && (!this.isPersistentLiftIdle()
                || !this.isLiftDoorOpen()))
        {
            return this.position().add(0.0D, 0.2D, 0.0D);
        }
        Direction exit = this.getLiftExit();
        return this.position().add(exit.getStepX() * 3.4D,
                0.2D, exit.getStepZ() * 3.4D);
    }

    private void tickPersistentLift()
    {
        switch (this.persistentLiftState)
        {
            case LIFT_DOOR_CLOSING ->
            {
                this.persistentLiftPhaseTicks++;
                if (this.persistentLiftPhaseTicks
                        >= DOOR_CLOSE_TICKS - DOOR_SLIDE_TICKS)
                {
                    this.setLiftDoorOpen(false);
                }
                if (this.persistentLiftPhaseTicks >= DOOR_CLOSE_TICKS)
                {
                    if (!this.boardWaitingPassengers())
                    {
                        this.persistentLiftState = LIFT_IDLE_OPEN;
                        this.persistentLiftPhaseTicks = 0;
                        this.persistentLiftVelocity = 0.0D;
                        this.persistentLiftStateRevision++;
                        this.setLiftDoorOpen(true);
                        break;
                    }
                    this.persistentLiftState = LIFT_STARTING;
                    this.persistentLiftPhaseTicks = 0;
                    this.persistentLiftVelocity = 0.0D;
                }
            }
            case LIFT_STARTING, LIFT_MOVING, LIFT_BRAKING,
                    LIFT_LEVELING ->
            {
                if (this.persistentLiftActiveMotionEpoch <= 0L
                        || this.isLiftDoorOpen())
                {
                    this.persistentLiftState = LIFT_RECOVERY_HOLD;
                    this.persistentLiftVelocity = 0.0D;
                    this.persistentLiftStateRevision++;
                    this.setLiftDoorOpen(false);
                }
                else
                {
                    this.tickPersistentLiftMotion();
                }
            }
            case LIFT_DOOR_OPENING ->
            {
                this.persistentLiftPhaseTicks++;
                if (this.persistentLiftPhaseTicks >= DOOR_OPEN_TICKS)
                {
                    this.persistentLiftState = LIFT_IDLE_OPEN;
                    this.persistentLiftPhaseTicks = 0;
                    this.setLiftDoorOpen(true);
                }
            }
            case LIFT_FAULT ->
            {
                this.persistentLiftVelocity = 0.0D;
                this.setLiftDoorOpen(false);
            }
            case LIFT_RECOVERY_HOLD ->
            {
                this.persistentLiftVelocity = 0.0D;
                this.setLiftDoorOpen(false);
            }
            default ->
            {
                this.persistentLiftState = LIFT_IDLE_OPEN;
                this.persistentLiftPhaseTicks = 0;
                this.persistentLiftVelocity = 0.0D;
                this.setLiftDoorOpen(true);
            }
        }
    }

    private void tickPersistentLiftMotion()
    {
        // A rider who briefly dismounted inside the closed car (for example
        // because of an input packet arriving on the same tick as departure)
        // must remain attached to the one authoritative moving transform.
        if (!this.boardWaitingPassengers())
        {
            this.persistentLiftState = LIFT_RECOVERY_HOLD;
            this.persistentLiftVelocity = 0.0D;
            this.persistentLiftPhaseTicks = 0;
            this.persistentLiftStateRevision++;
            this.setLiftDoorOpen(false);
            return;
        }
        this.persistentLiftPhaseTicks++;
        if (this.persistentLiftPhaseTicks > LIFT_TRAVEL_WATCHDOG_TICKS)
        {
            /*
             * Never leave a cabin permanently reporting IN TRANSIT.  The
             * shaft authority will recover this stopped car to the nearest
             * audited landing on its next heartbeat.
             */
            this.persistentLiftState = LIFT_RECOVERY_HOLD;
            this.persistentLiftVelocity = 0.0D;
            this.persistentLiftPhaseTicks = 0;
            this.persistentLiftStateRevision++;
            this.setLiftDoorOpen(false);
            return;
        }
        double delta = this.persistentLiftTargetY - this.getY();
        double remaining = Math.abs(delta);
        if (remaining <= LIFT_ARRIVAL_TOLERANCE)
        {
            this.finishPersistentLiftTravel();
            return;
        }

        double brakingSpeed = Math.sqrt(
                2.0D * LIFT_ACCELERATION * remaining);
        double desiredSpeed = Math.min(LIFT_MAX_SPEED, brakingSpeed);
        if (remaining <= 0.75D)
        {
            desiredSpeed = Math.min(desiredSpeed, LIFT_LEVELING_SPEED);
            this.persistentLiftState = LIFT_LEVELING;
        }
        else if (desiredSpeed + 0.01D
                < this.persistentLiftVelocity)
        {
            this.persistentLiftState = LIFT_BRAKING;
        }
        else if (this.persistentLiftVelocity
                < LIFT_MAX_SPEED - 0.01D)
        {
            this.persistentLiftState = LIFT_STARTING;
        }
        else
        {
            this.persistentLiftState = LIFT_MOVING;
        }

        if (this.persistentLiftVelocity < desiredSpeed)
        {
            this.persistentLiftVelocity = Math.min(desiredSpeed,
                    this.persistentLiftVelocity + LIFT_ACCELERATION);
        }
        else
        {
            this.persistentLiftVelocity = Math.max(desiredSpeed,
                    this.persistentLiftVelocity - LIFT_ACCELERATION);
        }
        double step = Math.min(remaining,
                Math.max(LIFT_ARRIVAL_TOLERANCE,
                        this.persistentLiftVelocity));
        this.moveControlled(this.getX(),
                this.getY() + Math.copySign(step, delta), this.getZ());
        for (Entity passenger : this.getPassengers())
        {
            this.positionRider(passenger, Entity::setPos);
            passenger.resetFallDistance();
        }
        if (Math.abs(this.persistentLiftTargetY - this.getY())
                <= LIFT_ARRIVAL_TOLERANCE)
        {
            this.finishPersistentLiftTravel();
        }
    }

    private void finishPersistentLiftTravel()
    {
        this.moveControlled(this.getX(),
                this.persistentLiftTargetY, this.getZ());
        this.persistentLiftVelocity = 0.0D;
        this.persistentLiftPendingMotionEpoch = 0L;
        this.persistentLiftActiveMotionEpoch = 0L;
        this.persistentLiftState = LIFT_DOOR_OPENING;
        this.persistentLiftPhaseTicks = 0;
        this.persistentLiftStateRevision++;
    }

    private boolean isValidPersistentLiftTarget(double targetY)
    {
        return Double.isFinite(targetY)
                && targetY >= this.level().getMinBuildHeight()
                && targetY <= this.level().getMaxBuildHeight() - 5.0D;
    }

    private static boolean isMotionState(int state)
    {
        return state == LIFT_DOOR_CLOSING
                || state == LIFT_STARTING
                || state == LIFT_MOVING
                || state == LIFT_BRAKING
                || state == LIFT_LEVELING
                || state == LIFT_DOOR_OPENING;
    }

    private boolean boardWaitingPassengers()
    {
        AABB cabinInterior = new AABB(
                this.getX() - 2.15D, this.getY() - 0.4D,
                this.getZ() - 2.15D,
                this.getX() + 2.15D, this.getY() + 3.5D,
                this.getZ() + 2.15D);
        for (Player player : this.level().getEntitiesOfClass(
                Player.class, cabinInterior, candidate ->
                        !candidate.isPassenger()))
        {
            if (this.getPassengers().size() >= MAX_LIFT_PASSENGERS)
            {
                return false;
            }
            if (!player.startRiding(this, true))
            {
                return false;
            }
        }
        return this.level().getEntitiesOfClass(
                Player.class, cabinInterior, candidate ->
                        !candidate.isPassenger()
                                && !candidate.isSpectator()).isEmpty();
    }

    private boolean hasConfiguredLiftLandings()
    {
        return Double.isFinite(this.persistentLiftLowerY)
                && Double.isFinite(this.persistentLiftUpperY)
                && this.persistentLiftLowerY < this.persistentLiftUpperY;
    }

    private boolean isInsidePersistentLiftCabin(Player player)
    {
        if (this.hasPassenger(player))
        {
            return true;
        }
        return player.getBoundingBox().intersects(new AABB(
                this.getX() - 2.2D, this.getY() - 0.25D,
                this.getZ() - 2.2D,
                this.getX() + 2.2D, this.getY() + 3.45D,
                this.getZ() + 2.2D));
    }

    public boolean consumePersistentLiftControlDebounce()
    {
        long now = this.level().getGameTime();
        if (now - this.lastPersistentLiftControlTick
                < CONTROL_DEBOUNCE_TICKS)
        {
            return false;
        }
        this.lastPersistentLiftControlTick = now;
        return true;
    }
}
