package com.projectseele.entity;

import java.util.UUID;

import com.projectseele.world.EntryPlugDirector;
import com.projectseele.world.EntryPlugKinematics;
import com.projectseele.world.RigidTransform;
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
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import org.joml.Quaternionf;
import org.jetbrains.annotations.Nullable;
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
    /** Crane is drawing the capsule back out of the airframe with its pilot. */
    public static final int STAGE_EJECTING = 3;
    /** Emergency pyrotechnics are throwing the occupied capsule clear. */
    public static final int STAGE_FIELD_EJECTING = 4;
    /** Emergency capsule has landed and is no longer owned by a cage crane. */
    public static final int STAGE_FIELD_LANDED = 5;
    /**
     * The same physical capsule is seated inside its EVA. It remains the
     * player's vehicle and rides the airframe as a hidden nested passenger.
     */
    public static final int STAGE_LOCKED = 6;
    /** A failed PREPARE is braking and retracing the authored insertion path. */
    public static final int STAGE_ABORT_RETURNING = 7;
    public static final int STAGE_ABORT_DOCKED = 8;

    /** Hatch open at the boarding bridge; the capsule is safe to enter. */
    public static final int CABIN_OPEN = 0;
    /** Pilot seated, hatch sealed, optical feed still completely disconnected. */
    public static final int CABIN_SEALED_DARK = 1;
    /** PREPARE accepted and the local capsule is filling with LCL. */
    public static final int CABIN_LCL_FILLING = 2;
    /** A10 nerve connection and external optical synchronization are running. */
    public static final int CABIN_SYNCHRONIZING = 3;
    /** Optical feed is live; ownership is about to transfer to the airframe. */
    public static final int CABIN_ONLINE = 4;
    /** Percent reached outside the EVA before the seated plug takes over. */
    public static final int CABIN_TRANSFER_PERCENT = 70;
    /** Door animation is eight percentage points per server tick. */
    public static final int HATCH_SEAL_TICKS = 13;

    private int ejectionTicks;
    private Vec3 fieldEjectionStart = Vec3.ZERO;
    private Vec3 fieldEjectionEscape = Vec3.ZERO;
    private Vec3 fieldEjectionLanding = Vec3.ZERO;

    private static final EntityDataAccessor<Integer> DATA_VARIANT =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_STAGE =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.INT);
    /**
     * Monotonic mechanical-generation counter.  Stage changes and their epoch
     * are published together on the server thread, allowing directors and
     * clients to reject a stale insertion/rollback decision after a reload or
     * an abort request.
     */
    private static final EntityDataAccessor<Integer> DATA_STAGE_EPOCH =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_PROGRESS =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_CABIN_STAGE =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_CABIN_PROGRESS =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.INT);
    /**
     * Visual hatch travel, 0 = pressure shell closed and 100 = fully open.
     * This is separate from {@link #DATA_CABIN_STAGE}: boarding must lock
     * immediately, while the two physical door leaves still need several
     * frames to close rather than vanishing between clicks.
     */
    private static final EntityDataAccessor<Integer> DATA_HATCH_OPEN =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> DATA_CANONICAL_POSE =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Float> DATA_POSE_QX =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> DATA_POSE_QY =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> DATA_POSE_QZ =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> DATA_POSE_QW =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Integer> DATA_POSE_SEQUENCE =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_HOST_EVA_ID =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> DATA_SHELL_VISIBLE =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.BOOLEAN);
    /** Pilot/entity code may request a rollback, but only the director may
     * advance the mechanical insertion stage. */
    private static final EntityDataAccessor<Boolean> DATA_ABORT_REQUESTED =
            SynchedEntityData.defineId(EntryPlugCarrierEntity.class,
                    EntityDataSerializers.BOOLEAN);

    private final AnimatableInstanceCache geoCache =
            GeckoLibUtil.createInstanceCache(this);
    private RigidTransform clientPreviousRotation = RigidTransform.identity();
    private RigidTransform clientCurrentRotation = RigidTransform.identity();
    private int clientRotationUpdateTick = Integer.MIN_VALUE;
    @Nullable
    private UUID hostEvaUuid;
    private int nextBoardingDiagnosticTick;
    private RigidTransform lockedSocketToPlug = new RigidTransform(
            new Vec3(0.0D, 0.0D, -EntryPlugKinematics.LOCK_DEPTH_BLOCKS),
            0.0F, 0.0F, 0.0F, 1.0F);

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
        this.entityData.define(DATA_STAGE_EPOCH, 0);
        this.entityData.define(DATA_PROGRESS, 0);
        this.entityData.define(DATA_CABIN_STAGE, CABIN_OPEN);
        this.entityData.define(DATA_CABIN_PROGRESS, 0);
        this.entityData.define(DATA_HATCH_OPEN, 100);
        this.entityData.define(DATA_CANONICAL_POSE, false);
        this.entityData.define(DATA_POSE_QX, 0.0F);
        this.entityData.define(DATA_POSE_QY, 0.0F);
        this.entityData.define(DATA_POSE_QZ, 0.0F);
        this.entityData.define(DATA_POSE_QW, 1.0F);
        this.entityData.define(DATA_POSE_SEQUENCE, 0);
        this.entityData.define(DATA_HOST_EVA_ID, -1);
        this.entityData.define(DATA_SHELL_VISIBLE, true);
        this.entityData.define(DATA_ABORT_REQUESTED, false);
    }

    public boolean hasCanonicalPose()
    {
        return this.entityData.get(DATA_CANONICAL_POSE);
    }

    public RigidTransform getCanonicalTransform()
    {
        return new RigidTransform(this.position(),
                this.entityData.get(DATA_POSE_QX),
                this.entityData.get(DATA_POSE_QY),
                this.entityData.get(DATA_POSE_QZ),
                this.entityData.get(DATA_POSE_QW));
    }

    public Quaternionf getCanonicalRotation(float partialTick)
    {
        if (!this.level().isClientSide)
        {
            return this.getCanonicalTransform().rotation();
        }
        if (this.tickCount != this.clientRotationUpdateTick)
        {
            return this.clientCurrentRotation.rotation();
        }
        return this.clientPreviousRotation.interpolate(
                this.clientCurrentRotation, partialTick).rotation();
    }

    /**
     * The crane/director publishes one translation + quaternion pose. Renderer,
     * hatch, seat and interaction markers all derive from this state.
     */
    public void setCanonicalTransform(RigidTransform transform)
    {
        this.setPos(transform.translation());
        this.entityData.set(DATA_POSE_QX, transform.qx());
        this.entityData.set(DATA_POSE_QY, transform.qy());
        this.entityData.set(DATA_POSE_QZ, transform.qz());
        this.entityData.set(DATA_POSE_QW, transform.qw());
        this.entityData.set(DATA_CANONICAL_POSE, true);
        this.entityData.set(DATA_POSE_SEQUENCE,
                this.entityData.get(DATA_POSE_SEQUENCE) + 1);
    }

    public Vec3 transformPlugMarker(Vec3 marker)
    {
        return this.getCanonicalTransform().transformPoint(marker);
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

    private void setInsertionStage(int stage)
    {
        int safe = Math.max(STAGE_SUSPENDED,
                Math.min(STAGE_ABORT_DOCKED, stage));
        if (this.entityData.get(DATA_STAGE) == safe)
        {
            return;
        }
        this.entityData.set(DATA_STAGE, safe);
        advanceInsertionEpoch();
    }

    public int getInsertionEpoch()
    {
        return this.entityData.get(DATA_STAGE_EPOCH);
    }

    /**
     * Server-thread compare-and-set used by the mechanical director.  A stale
     * callback may not advance or rewind a capsule that has already entered a
     * different phase.
     */
    public boolean transitionInsertionStage(int expectedStage, int nextStage)
    {
        return this.transitionInsertionStage(expectedStage,
                this.getInsertionEpoch(), nextStage);
    }

    public boolean transitionInsertionStage(
            int expectedStage, int expectedEpoch, int nextStage)
    {
        if (this.level().isClientSide
                || this.getInsertionStage() != expectedStage
                || this.getInsertionEpoch() != expectedEpoch
                || !allowedInsertionTransition(expectedStage, nextStage))
        {
            return false;
        }
        this.setInsertionStage(nextStage);
        return this.getInsertionStage() == Math.max(STAGE_SUSPENDED,
                Math.min(STAGE_ABORT_DOCKED, nextStage));
    }

    private static boolean allowedInsertionTransition(int from, int to)
    {
        return switch (from)
        {
            case STAGE_SUSPENDED -> to == STAGE_OCCUPIED;
            case STAGE_OCCUPIED -> to == STAGE_SUSPENDED
                    || to == STAGE_INSERTING;
            case STAGE_INSERTING -> to == STAGE_LOCKED
                    || to == STAGE_ABORT_RETURNING;
            case STAGE_LOCKED -> to == STAGE_INSERTING
                    || to == STAGE_EJECTING
                    || to == STAGE_FIELD_EJECTING
                    || to == STAGE_ABORT_RETURNING;
            case STAGE_EJECTING -> to == STAGE_OCCUPIED
                    || to == STAGE_SUSPENDED;
            case STAGE_FIELD_EJECTING -> to == STAGE_FIELD_LANDED;
            case STAGE_FIELD_LANDED -> to == STAGE_OCCUPIED;
            case STAGE_ABORT_RETURNING -> to == STAGE_ABORT_DOCKED;
            case STAGE_ABORT_DOCKED -> to == STAGE_OCCUPIED
                    || to == STAGE_SUSPENDED;
            default -> false;
        };
    }

    private void advanceInsertionEpoch()
    {
        int current = this.entityData.get(DATA_STAGE_EPOCH);
        this.entityData.set(DATA_STAGE_EPOCH,
                current == Integer.MAX_VALUE ? 1 : current + 1);
    }

    public int getInsertionProgress()
    {
        return this.entityData.get(DATA_PROGRESS);
    }

    public void setInsertionProgress(int progress)
    {
        this.entityData.set(DATA_PROGRESS, Math.max(0, Math.min(100, progress)));
    }

    public boolean isLockedToEva()
    {
        return this.getInsertionStage() == STAGE_LOCKED
                && (this.hostEvaUuid != null
                    || this.entityData.get(DATA_HOST_EVA_ID) >= 0
                    || this.getVehicle() instanceof EvaUnit01Entity);
    }

    public boolean isShellVisible()
    {
        return this.entityData.get(DATA_SHELL_VISIBLE);
    }

    public boolean isInsertionAbortRequested()
    {
        return this.entityData.get(DATA_ABORT_REQUESTED);
    }

    public void requestInsertionAbort()
    {
        if (this.getInsertionStage() == STAGE_INSERTING)
        {
            this.entityData.set(DATA_ABORT_REQUESTED, true);
            this.sealCabin();
        }
    }

    public void clearInsertionAbortRequest()
    {
        this.entityData.set(DATA_ABORT_REQUESTED, false);
    }

    @Nullable
    public UUID getHostEvaUuid()
    {
        return this.hostEvaUuid;
    }

    /**
     * Resolves the airframe without forcing a chunk load. The direct nested
     * vehicle is authoritative; synchronized IDs cover the client, and UUIDs
     * restore the link after a server reload.
     */
    @Nullable
    public EvaUnit01Entity getLinkedEva()
    {
        if (this.getVehicle() instanceof EvaUnit01Entity direct)
        {
            return direct;
        }
        int entityId = this.entityData.get(DATA_HOST_EVA_ID);
        Entity byId = entityId >= 0 ? this.level().getEntity(entityId) : null;
        if (byId instanceof EvaUnit01Entity eva)
        {
            return eva;
        }
        if (!this.level().isClientSide && this.hostEvaUuid != null
                && this.level() instanceof net.minecraft.server.level.ServerLevel server)
        {
            Entity byUuid = server.getEntity(this.hostEvaUuid);
            if (byUuid instanceof EvaUnit01Entity eva)
            {
                return eva;
            }
        }
        return null;
    }

    /**
     * Seats this exact entity in the dorsal socket. The pilot is deliberately
     * not transferred: EVA -> plug -> pilot remains one persistent ride chain.
     */
    public boolean lockToEva(EvaUnit01Entity unit)
    {
        if (this.level().isClientSide || unit.level() != this.level()
                || !this.isVehicle())
        {
            return false;
        }
        RigidTransform socket = unit.getEntryPlugSocketTransform();
        RigidTransform seated = EntryPlugKinematics.lockedTransform(unit);
        this.lockedSocketToPlug = socket.inverse().compose(seated);
        this.hostEvaUuid = unit.getUUID();
        this.entityData.set(DATA_HOST_EVA_ID, unit.getId());
        this.entityData.set(DATA_SHELL_VISIBLE, false);
        this.clearInsertionAbortRequest();
        this.setCanonicalTransform(seated);
        if (!this.startRiding(unit, true))
        {
            this.hostEvaUuid = null;
            this.entityData.set(DATA_HOST_EVA_ID, -1);
            this.entityData.set(DATA_SHELL_VISIBLE, true);
            return false;
        }
        if (!this.transitionInsertionStage(STAGE_INSERTING, STAGE_LOCKED))
        {
            this.stopRiding();
            this.hostEvaUuid = null;
            this.entityData.set(DATA_HOST_EVA_ID, -1);
            this.entityData.set(DATA_SHELL_VISIBLE, true);
            return false;
        }
        this.setInsertionProgress(100);
        this.setCabinSequenceProgress(CABIN_TRANSFER_PERCENT);
        return true;
    }

    /** Detaches the same capsule for hangar extraction or field ejection. */
    public void unlockFromEva()
    {
        if (this.getVehicle() instanceof EvaUnit01Entity)
        {
            this.stopRiding();
        }
        this.hostEvaUuid = null;
        this.entityData.set(DATA_HOST_EVA_ID, -1);
        this.entityData.set(DATA_SHELL_VISIBLE, true);
    }

    public boolean beginFieldEjection(Vec3 start, Vec3 escape, Vec3 landing)
    {
        int stage = this.getInsertionStage();
        int epoch = this.getInsertionEpoch();
        if (!this.transitionInsertionStage(stage, epoch,
                STAGE_FIELD_EJECTING))
        {
            return false;
        }
        this.fieldEjectionStart = start;
        this.fieldEjectionEscape = escape;
        this.fieldEjectionLanding = landing;
        this.ejectionTicks = 0;
        this.setInsertionProgress(100);
        return true;
    }

    public Vec3 getFieldEjectionStart()
    {
        return this.fieldEjectionStart;
    }

    public Vec3 getFieldEjectionEscape()
    {
        return this.fieldEjectionEscape;
    }

    public Vec3 getFieldEjectionLanding()
    {
        return this.fieldEjectionLanding;
    }

    public int getCabinStage()
    {
        return this.entityData.get(DATA_CABIN_STAGE);
    }

    public int getCabinProgress()
    {
        return this.entityData.get(DATA_CABIN_PROGRESS);
    }

    public boolean isHatchOpen()
    {
        return this.getCabinStage() == CABIN_OPEN && !this.isVehicle();
    }

    public float getHatchOpenAmount()
    {
        return this.entityData.get(DATA_HATCH_OPEN) / 100.0F;
    }

    public boolean isHatchFullySealed()
    {
        return this.getCabinStage() != CABIN_OPEN
                && this.entityData.get(DATA_HATCH_OPEN) == 0;
    }

    public void sealCabin()
    {
        this.entityData.set(DATA_CABIN_STAGE, CABIN_SEALED_DARK);
        this.entityData.set(DATA_CABIN_PROGRESS, 0);
    }

    public void beginCabinPreparation()
    {
        if (this.isVehicle() && this.getCabinStage() <= CABIN_SEALED_DARK)
        {
            /*
             * PREPARE may be pressed immediately after boarding, while the two
             * pressure-door leaves are still travelling.  Keep the capsule
             * optically black until the hatch is physically shut; the
             * logistics director starts LCL only after the zero-travel
             * interlock is true.
             */
            this.entityData.set(DATA_CABIN_STAGE, CABIN_SEALED_DARK);
            this.entityData.set(DATA_CABIN_PROGRESS, 0);
        }
    }

    /**
     * Advances the continuous cockpit sequence. The visual stage is derived
     * here so server logistics cannot publish a percentage and a contradictory
     * label on separate ticks.
     */
    public void setCabinSequenceProgress(int progress)
    {
        int safe = Math.max(0, Math.min(CABIN_TRANSFER_PERCENT, progress));
        this.entityData.set(DATA_CABIN_PROGRESS, safe);
        if (safe <= 0)
        {
            this.entityData.set(DATA_CABIN_STAGE, CABIN_SEALED_DARK);
        }
        else if (safe < 45)
        {
            this.entityData.set(DATA_CABIN_STAGE, CABIN_LCL_FILLING);
        }
        else if (safe < CABIN_TRANSFER_PERCENT)
        {
            this.entityData.set(DATA_CABIN_STAGE, CABIN_SYNCHRONIZING);
        }
        else
        {
            this.entityData.set(DATA_CABIN_STAGE, CABIN_ONLINE);
        }
    }

    public void openCabin()
    {
        if (!this.isVehicle()
                && (this.getInsertionStage() == STAGE_SUSPENDED
                    || this.getInsertionStage() == STAGE_FIELD_LANDED))
        {
            this.entityData.set(DATA_CABIN_STAGE, CABIN_OPEN);
            this.entityData.set(DATA_CABIN_PROGRESS, 0);
        }
    }

    public boolean boardPassenger(Entity passenger)
    {
        int stage = this.getInsertionStage();
        if (this.level().isClientSide
                || (stage != STAGE_SUSPENDED
                    && stage != STAGE_FIELD_LANDED)
                || this.isVehicle()
                || passenger.isPassenger())
        {
            return false;
        }
        int epoch = this.getInsertionEpoch();
        // Publish OCCUPIED before the vanilla ride callback runs.  Passenger
        // callbacks may query the capsule immediately; leaving it SUSPENDED
        // during startRiding made both real and dummy pilots intermittently
        // reject an otherwise valid docked plug.
        if (!this.transitionInsertionStage(stage, epoch, STAGE_OCCUPIED))
        {
            return false;
        }
        if (!passenger.startRiding(this, true))
        {
            this.transitionInsertionStage(STAGE_OCCUPIED,
                    this.getInsertionEpoch(), stage);
            if (this.tickCount >= this.nextBoardingDiagnosticTick)
            {
                this.nextBoardingDiagnosticTick = this.tickCount + 20;
                com.projectseele.ProjectSeele.LOGGER.warn(
                        "NERV entry-plug boarding rejected by ride graph: eva={} plug={} pilot={} stage={} pilotVehicle={}",
                        this.getAssignedVariant(), this.getStringUUID(),
                        passenger.getStringUUID(), stage,
                        passenger.getVehicle() == null ? "none"
                                : passenger.getVehicle().getStringUUID());
            }
            return false;
        }
        if (this.level() instanceof net.minecraft.server.level.ServerLevel
                serverLevel)
        {
            EntryPlugDirector.claimBoardedPlug(serverLevel, this);
        }
        this.sealCabin();
        this.level().playSound(null, this.blockPosition(),
                SoundEvents.IRON_TRAPDOOR_CLOSE, SoundSource.BLOCKS,
                1.2F, 0.72F);
        return true;
    }

    @Override
    public float getPickRadius()
    {
        // The imported shell and its open hatch are wider than the entity's
        // slim insertion collision body.  This only extends selection; the
        // server still validates hatch state, range and line of sight.
        return 3.5F;
    }

    /**
     * Server-authoritative hatch interaction for the physical capsule.
     *
     * <p>The client extends the use ray because the imported shell is much
     * larger than a vanilla interaction target. This method repeats every
     * meaningful gate so a packet cannot board a sealed or remote plug.
     */
    public InteractionResult tryBoardFromHatch(Player player)
    {
        if (this.level().isClientSide)
        {
            return InteractionResult.SUCCESS;
        }
        if (!this.isHatchOpen() || this.getInsertionStage() != STAGE_SUSPENDED
                || this.isVehicle() || player.isPassenger())
        {
            player.displayClientMessage(Component.literal(
                    "Entry-plug hatch is sealed or under crane control."), true);
            return InteractionResult.CONSUME;
        }
        Vec3 eye = player.getEyePosition();
        Vec3 hatch = this.hasCanonicalPose()
                ? this.transformPlugMarker(
                        EntryPlugKinematics.HATCH_PORTAL_CENTRE_P)
                : this.getBoundingBox().getCenter();
        Vec3 direction = hatch.subtract(eye);
        double interactionRange = EvaScale.ENTRY_PLUG_INTERACTION_RANGE;
        if (direction.lengthSqr() > interactionRange * interactionRange
                || direction.lengthSqr() < 1.0E-4D
                || direction.normalize().dot(player.getViewVector(1.0F))
                        < 0.35D)
        {
            player.displayClientMessage(Component.literal(
                    "Stand on the boarding bridge and face the entry-plug hatch."),
                    true);
            return InteractionResult.CONSUME;
        }
        net.minecraft.world.phys.BlockHitResult hit = this.level().clip(
                new ClipContext(eye, hatch, ClipContext.Block.COLLIDER,
                        ClipContext.Fluid.NONE, player));
        if (hit.getType() != HitResult.Type.MISS
                && hit.getLocation().distanceToSqr(hatch) > 3.0D * 3.0D)
        {
            player.displayClientMessage(Component.literal(
                    "Entry-plug hatch is obstructed."), true);
            return InteractionResult.CONSUME;
        }
        return this.boardPassenger(player)
                ? InteractionResult.CONSUME : InteractionResult.FAIL;
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
        Entity occupant = this.getFirstPassenger();
        if (occupant != null)
        {
            // A seated pilot is invisible — they are inside the capsule — so
            // naming the occupant is the only way to tell a boarded plug from
            // one that is wrongly reporting itself full.
            player.displayClientMessage(Component.literal(
                    "Entry plug is already occupied by "
                            + occupant.getName().getString()
                            + " (/seele eva dummy stop to clear)."), true);
            return InteractionResult.CONSUME;
        }
        return this.tryBoardFromHatch(player);
    }

    @Override
    protected boolean canAddPassenger(Entity passenger)
    {
        return this.getPassengers().isEmpty()
                && (passenger instanceof Player
                    || passenger instanceof TrainingPilotEntity);
    }

    @Override
    protected void removePassenger(Entity passenger)
    {
        super.removePassenger(passenger);
        if (this.getInsertionStage() == STAGE_INSERTING)
        {
            // Losing the pilot is an abort request, not permission to open a
            // pressure hatch halfway through the EVA/bridge sweep volume.
            this.requestInsertionAbort();
        }
        else if (this.getInsertionStage() == STAGE_OCCUPIED)
        {
            // A pilot may climb back out while the same capsule is safely at
            // its dock.  Publish SUSPENDED before opening so openCabin cannot
            // accidentally authorize an OCCUPIED capsule elsewhere.
            this.transitionInsertionStage(STAGE_OCCUPIED,
                    this.getInsertionEpoch(), STAGE_SUSPENDED);
            this.openCabin();
        }
        else
        {
            this.openCabin();
        }
        if (passenger instanceof Player player)
        {
            // Reveal the pilot when they climb out of the plug. A plug->EVA
            // insertion transfer shows the body for a single tick before the
            // airframe hides it again, which is imperceptible.
            player.setInvisible(false);
            // The plug can sit high on the airframe's back after an ejection, so
            // glide the pilot down instead of dropping them to their death.
            if (!this.level().isClientSide)
            {
                player.addEffect(new MobEffectInstance(
                        MobEffects.SLOW_FALLING, 20 * 12, 0));
            }
        }
    }

    @Override
    protected void positionRider(Entity passenger, Entity.MoveFunction move)
    {
        if (!this.hasPassenger(passenger))
        {
            return;
        }
        Vec3 seat = this.hasCanonicalPose()
                ? this.transformPlugMarker(EntryPlugKinematics.PILOT_SEAT_P)
                : this.position().add(0.0D, 0.35D, 0.0D);
        EvaUnit01Entity linkedEva = this.getLinkedEva();
        if (this.isLockedToEva() && linkedEva != null)
        {
            seat = linkedEva.getPilotCameraSeatPosition(passenger);
        }
        move.accept(passenger, seat.x,
                this.isLockedToEva() && linkedEva != null
                        ? seat.y : seat.y - passenger.getBbHeight() * 0.5D,
                seat.z);
        if (this.isLockedToEva())
        {
            // Once optical synchronization is live, mouse look belongs to the
            // EVA. During crane motion the capsule frame still owns yaw/pitch.
            return;
        }
        Vec3 view = this.hasCanonicalPose()
                ? this.getCanonicalTransform().transformVector(
                        EntryPlugKinematics.PILOT_VIEW_FORWARD_P)
                : this.getLookAngle();
        float yaw = (float) Math.toDegrees(
                Math.atan2(-view.x, view.z));
        float pitch = (float) Math.toDegrees(
                Math.asin(-Math.max(-1.0D, Math.min(1.0D, view.y))));
        passenger.setYRot(yaw);
        passenger.setXRot(pitch);
    }

    /** Immediately reconciles the nested pilot after the host EVA teleports. */
    public void syncPilotPositionNow()
    {
        for (Entity passenger : this.getPassengers())
        {
            this.positionRider(passenger,
                    (entity, x, y, z) ->
                    {
                        entity.setPos(x, y, z);
                        entity.xo = x;
                        entity.yo = y;
                        entity.zo = z;
                        entity.setDeltaMovement(Vec3.ZERO);
                        entity.fallDistance = 0.0F;
                    });
        }
    }

    @Override
    public Vec3 getDismountLocationForPassenger(
            net.minecraft.world.entity.LivingEntity passenger)
    {
        if (!this.hasCanonicalPose())
        {
            float radians = (float) Math.toRadians(this.getYRot());
            return this.position().add(Math.cos(radians) * 2.0D,
                    -2.0D, Math.sin(radians) * 2.0D);
        }
        Vec3 left = this.transformPlugMarker(
                EntryPlugKinematics.PILOT_DISMOUNT_LEFT_P);
        Vec3 right = this.transformPlugMarker(
                EntryPlugKinematics.PILOT_DISMOUNT_RIGHT_P);
        return this.level().noCollision(passenger,
                passenger.getBoundingBox().move(
                        left.subtract(passenger.position())))
                ? left : right;
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
            if (this.getInsertionStage() == STAGE_LOCKED)
            {
                EvaUnit01Entity host = this.getLinkedEva();
                if (host != null)
                {
                    this.hostEvaUuid = host.getUUID();
                    this.entityData.set(DATA_HOST_EVA_ID, host.getId());
                    this.entityData.set(DATA_SHELL_VISIBLE, false);
                    RigidTransform wanted =
                            host.getEntryPlugSocketTransform()
                                    .compose(this.lockedSocketToPlug);
                    RigidTransform current = this.getCanonicalTransform();
                    if (current.translation().distanceToSqr(
                            wanted.translation()) > 1.0E-6D
                            || current.rotationErrorDegrees(wanted)
                            > 0.01D)
                    {
                        this.setCanonicalTransform(wanted);
                    }
                    if (this.getVehicle() != host && !this.startRiding(host, true))
                    {
                        host.markEntryPlugLinkFault(this);
                    }
                }
            }
            int hatch = this.entityData.get(DATA_HATCH_OPEN);
            int target = this.getCabinStage() == CABIN_OPEN
                    && !this.isVehicle() ? 100 : 0;
            if (hatch != target)
            {
                boolean closingObstructed = target == 0 && hatch > 0
                        && this.hatchClosingObstructed();
                if (!closingObstructed)
                {
                    int step = target > hatch ? 8 : -8;
                    this.entityData.set(DATA_HATCH_OPEN,
                            Math.max(0, Math.min(100, hatch + step)));
                }
            }
            if (this.getInsertionStage() == STAGE_EJECTING)
            {
                // Driven from the capsule itself: the logistics tick calls
                // ensureSuspended every tick while an EVA is parked, which would
                // otherwise snap the plug — pilot aboard — straight back to its
                // cage instead of letting the crane withdraw it.
                this.ejectionTicks++;
                EntryPlugDirector.tickEjection(this, this.ejectionTicks);
            }
            else if (this.getInsertionStage() == STAGE_FIELD_EJECTING)
            {
                this.ejectionTicks++;
                EntryPlugDirector.tickFieldEjection(this, this.ejectionTicks);
            }
            else
            {
                this.ejectionTicks = 0;
            }
            EntryPlugDirector.keepPassengerState(this);
        }
    }

    /** Holds the physical door open while any foreign collision occupies the
     * complete left/right leaf sweep. The seated pilot and host airframe are
     * authored occupants, not obstructions. */
    private boolean hatchClosingObstructed()
    {
        if (!this.hasCanonicalPose())
        {
            return false;
        }
        net.minecraft.world.phys.AABB sweep =
                EntryPlugKinematics.hatchClosingSweep(
                        this.getCanonicalTransform()).deflate(0.025D);
        if (this.level().getBlockCollisions(this, sweep).iterator().hasNext())
        {
            return true;
        }
        EvaUnit01Entity host = this.getLinkedEva();
        return !this.level().getEntities(this, sweep, entity ->
                entity.isAlive() && entity != host
                        && !this.hasPassenger(entity)
                        && entity.isPickable()).isEmpty();
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
        tag.putInt("InsertionEpoch", this.getInsertionEpoch());
        tag.putInt("InsertionProgress", this.getInsertionProgress());
        tag.putInt("CabinStage", this.getCabinStage());
        tag.putInt("CabinProgress", this.getCabinProgress());
        tag.putInt("HatchOpen", this.entityData.get(DATA_HATCH_OPEN));
        tag.putBoolean("CanonicalPose", this.hasCanonicalPose());
        tag.putFloat("PoseQX", this.entityData.get(DATA_POSE_QX));
        tag.putFloat("PoseQY", this.entityData.get(DATA_POSE_QY));
        tag.putFloat("PoseQZ", this.entityData.get(DATA_POSE_QZ));
        tag.putFloat("PoseQW", this.entityData.get(DATA_POSE_QW));
        if (this.hostEvaUuid != null)
        {
            tag.putUUID("HostEva", this.hostEvaUuid);
        }
        tag.putBoolean("ShellVisible", this.isShellVisible());
        tag.putBoolean("InsertionAbortRequested",
                this.isInsertionAbortRequested());
        putTransform(tag, "LockedSocketToPlug", this.lockedSocketToPlug);
        tag.putInt("EjectionTicks", this.ejectionTicks);
        putVector(tag, "FieldStart", this.fieldEjectionStart);
        putVector(tag, "FieldEscape", this.fieldEjectionEscape);
        putVector(tag, "FieldLanding", this.fieldEjectionLanding);
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
            this.entityData.set(DATA_STAGE, Math.max(STAGE_SUSPENDED,
                    Math.min(STAGE_ABORT_DOCKED,
                            tag.getInt("InsertionStage"))));
        }
        this.entityData.set(DATA_STAGE_EPOCH, Math.max(0,
                tag.getInt("InsertionEpoch")));
        if (tag.contains("InsertionProgress"))
        {
            this.setInsertionProgress(tag.getInt("InsertionProgress"));
        }
        if (tag.contains("CabinStage"))
        {
            this.entityData.set(DATA_CABIN_STAGE, Math.max(CABIN_OPEN,
                    Math.min(CABIN_ONLINE, tag.getInt("CabinStage"))));
            this.entityData.set(DATA_CABIN_PROGRESS, Math.max(0,
                    Math.min(CABIN_TRANSFER_PERCENT,
                            tag.getInt("CabinProgress"))));
        }
        else if (this.isVehicle())
        {
            this.sealCabin();
        }
        if (tag.contains("HatchOpen"))
        {
            this.entityData.set(DATA_HATCH_OPEN, Math.max(0,
                    Math.min(100, tag.getInt("HatchOpen"))));
        }
        else
        {
            this.entityData.set(DATA_HATCH_OPEN,
                    this.getCabinStage() == CABIN_OPEN ? 100 : 0);
        }
        if (tag.getBoolean("CanonicalPose"))
        {
            RigidTransform saved = new RigidTransform(this.position(),
                    tag.getFloat("PoseQX"), tag.getFloat("PoseQY"),
                    tag.getFloat("PoseQZ"), tag.getFloat("PoseQW"));
            this.setCanonicalTransform(saved);
            this.clientPreviousRotation = new RigidTransform(Vec3.ZERO,
                    saved.qx(), saved.qy(), saved.qz(), saved.qw());
            this.clientCurrentRotation = this.clientPreviousRotation;
        }
        this.hostEvaUuid = tag.hasUUID("HostEva")
                ? tag.getUUID("HostEva") : null;
        this.entityData.set(DATA_HOST_EVA_ID, -1);
        this.entityData.set(DATA_SHELL_VISIBLE,
                tag.contains("ShellVisible")
                        ? tag.getBoolean("ShellVisible")
                        : this.getInsertionStage() != STAGE_LOCKED);
        this.entityData.set(DATA_ABORT_REQUESTED,
                tag.getBoolean("InsertionAbortRequested"));
        this.lockedSocketToPlug = getTransform(tag,
                "LockedSocketToPlug", this.lockedSocketToPlug);
        this.ejectionTicks = Math.max(0, tag.getInt("EjectionTicks"));
        this.fieldEjectionStart = getVector(tag, "FieldStart", this.position());
        this.fieldEjectionEscape = getVector(tag, "FieldEscape", this.position());
        this.fieldEjectionLanding = getVector(tag, "FieldLanding", this.position());
    }

    private static void putVector(CompoundTag tag, String key, Vec3 value)
    {
        tag.putDouble(key + "X", value.x);
        tag.putDouble(key + "Y", value.y);
        tag.putDouble(key + "Z", value.z);
    }

    private static Vec3 getVector(CompoundTag tag, String key, Vec3 fallback)
    {
        if (!tag.contains(key + "X") || !tag.contains(key + "Y")
                || !tag.contains(key + "Z"))
        {
            return fallback;
        }
        return new Vec3(tag.getDouble(key + "X"), tag.getDouble(key + "Y"),
                tag.getDouble(key + "Z"));
    }

    private static void putTransform(CompoundTag tag, String key,
                                     RigidTransform transform)
    {
        putVector(tag, key + "T", transform.translation());
        tag.putFloat(key + "QX", transform.qx());
        tag.putFloat(key + "QY", transform.qy());
        tag.putFloat(key + "QZ", transform.qz());
        tag.putFloat(key + "QW", transform.qw());
    }

    private static RigidTransform getTransform(CompoundTag tag, String key,
                                               RigidTransform fallback)
    {
        if (!tag.contains(key + "QW"))
        {
            return fallback;
        }
        return new RigidTransform(getVector(tag, key + "T",
                fallback.translation()), tag.getFloat(key + "QX"),
                tag.getFloat(key + "QY"), tag.getFloat(key + "QZ"),
                tag.getFloat(key + "QW"));
    }

    @Override
    public void onSyncedDataUpdated(EntityDataAccessor<?> key)
    {
        super.onSyncedDataUpdated(key);
        if (DATA_STAGE_EPOCH.equals(key))
        {
            /*
             * A stage epoch is a hard mechanical boundary (dock, insertion,
             * lock or rollback), not another animation sample.  Blending a
             * newly loaded/reattached plug from the final quaternion of the
             * previous stage is what produced the visible reverse sweep and
             * occasional full turn after reload.  Collapse the interpolation
             * frame here; ordinary pose-sequence updates still blend below.
             */
            RigidTransform current = this.getCanonicalTransform();
            RigidTransform rotation = new RigidTransform(Vec3.ZERO,
                    current.qx(), current.qy(), current.qz(), current.qw());
            this.clientPreviousRotation = rotation;
            this.clientCurrentRotation = rotation;
            this.clientRotationUpdateTick = Integer.MIN_VALUE;
            this.xo = this.getX();
            this.yo = this.getY();
            this.zo = this.getZ();
            return;
        }
        if (DATA_POSE_SEQUENCE.equals(key))
        {
            this.clientPreviousRotation = this.clientCurrentRotation;
            RigidTransform current = this.getCanonicalTransform();
            this.clientCurrentRotation = new RigidTransform(Vec3.ZERO,
                    current.qx(), current.qy(), current.qz(), current.qw());
            this.clientRotationUpdateTick = this.tickCount;
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
