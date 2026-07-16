package com.projectseele.entity;

import com.projectseele.ProjectSeele;
import com.projectseele.config.SeeleConfig;
import com.projectseele.combat.AtFieldRules;
import com.projectseele.fx.AtFieldFX;
import com.projectseele.fx.StrategicExplosionDirector;
import com.projectseele.network.ClientboundCannonBeamPacket;
import com.projectseele.network.ClientboundNukeFxPacket;
import com.projectseele.network.ClientboundRifleTracerPacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.registry.ModSounds;
import com.projectseele.registry.ModEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.util.Mth;
import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityDimensions;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.Pose;
import net.minecraft.world.entity.SpawnGroupData;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.ProjectileUtil;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.ServerLevelAccessor;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.ForgeMod;
import net.minecraftforge.network.PacketDistributor;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * EVA Unit-01: rideable 30-block war machine and the pilot's body in every
 * Angel fight. Carries contact weapons, a positron cannon, automatic pallet
 * SMG and N2 self-destruct, plus an A.T. Field shield pool. All pilot input
 * arrives via {@code ServerboundEvaControlPacket}.
 */
public class EvaUnit01Entity extends PathfinderMob implements GeoEntity
{
    public static final int WEAPON_FISTS = 0;
    public static final int WEAPON_KNIFE = 1;
    public static final int WEAPON_CANNON = 2;
    public static final int WEAPON_LANCE = 3;
    public static final int WEAPON_RIFLE = 4;
    public static final int WEAPON_N2 = 5;
    public static final int UNIT_00 = 0;
    public static final int UNIT_01 = 1;
    public static final int UNIT_02 = 2;
    public static final int VISUAL_NORMAL = 0;
    public static final int VISUAL_IDLE = 1;
    public static final int VISUAL_WALK_CONTACT = 2;
    public static final int VISUAL_KNIFE_WINDUP = 3;
    public static final int VISUAL_KNIFE_CONTACT = 4;
    public static final int VISUAL_KNIFE_RECOVERY = 5;
    public static final int VISUAL_CROUCH = 6;
    public static final int VISUAL_PRONE = 7;
    public static final int VISUAL_LANCE_WINDUP = 8;
    public static final int VISUAL_LANCE_CONTACT = 9;
    public static final int VISUAL_LANCE_RECOVERY = 10;
    public static final int VISUAL_CANNON = 11;
    public static final int VISUAL_PRONE_CANNON = 12;
    public static final int VISUAL_RUN_CONTACT = 13;
    public static final int VISUAL_JUMP = 14;
    public static final int VISUAL_FALL = 15;
    public static final int VISUAL_CROUCH_WALK = 16;
    public static final int VISUAL_CRAWL = 17;
    public static final int VISUAL_KNIFE_READY = 18;
    public static final int VISUAL_LANCE_READY = 19;
    public static final int VISUAL_RIFLE = 20;
    public static final int VISUAL_CROUCH_KNIFE_CONTACT = 21;
    public static final int VISUAL_PRONE_KNIFE_CONTACT = 22;
    public static final int VISUAL_CROUCH_LANCE_CONTACT = 23;
    public static final int VISUAL_PRONE_LANCE_CONTACT = 24;
    public static final int VISUAL_N2_READY = 25;
    public static final int VISUAL_RIFLE_WALK_CONTACT = 26;
    public static final int VISUAL_CROUCH_RIFLE_CONTACT = 27;
    public static final int VISUAL_PRONE_RIFLE = 28;
    public static final int VISUAL_LIVE_MELEE = 29;
    public static final int VISUAL_LIVE_KNIFE = 30;
    public static final int VISUAL_LIVE_LANCE = 31;
    public static final int VISUAL_LIVE_RIFLE = 32;
    public static final int VISUAL_LIVE_KNIFE_HEAVY = 33;
    public static final int VISUAL_LIVE_JUMP = 34;
    public static final int LAUNCH_IDLE = 0;
    public static final int LAUNCH_LOCKED = 1;
    public static final int LAUNCH_ASCENT = 2;
    public static final int LAUNCH_CLEAR = 3;
    public static final float SILO_BAY_YAW = 180.0F;

    private static final float MELEE_FIST_DAMAGE = 20.0F;
    private static final float MELEE_KNIFE_DAMAGE = 60.0F;
    private static final float MELEE_LANCE_DAMAGE = 120.0F;
    private static final int MELEE_COOLDOWN_TICKS = 12;
    // Reach geometry for the 30-block frame.
    private static final double MELEE_REACH = 10.0D;
    private static final double MELEE_RADIUS = 7.5D;
    // Smash: crouch + attack. Slow, heavy, area knockdown.
    private static final float SMASH_FIST_DAMAGE = 35.0F;
    private static final float SMASH_KNIFE_DAMAGE = 80.0F;
    private static final float SMASH_LANCE_DAMAGE = 160.0F;
    private static final int SMASH_COOLDOWN_TICKS = 60;
    private static final double SMASH_RADIUS = 11.0D;
    private static final float STOMP_DAMAGE = 50.0F;
    private static final int STOMP_COOLDOWN_TICKS = 50;
    private static final double STOMP_RADIUS = 9.4D;
    private static final float AT_FIELD_MAX = 200.0F;
    private static final float AT_FIELD_REGEN = 0.4F;
    private static final int AT_FIELD_REGEN_DELAY = 100;
    private static final float AT_FIELD_MIN_TO_RAISE = 20.0F;
    private static final float NORMAL_WIDTH = 8.5F;
    private static final float NORMAL_HEIGHT = 30.0F;
    private static final float CROUCH_HEIGHT = 21.0F;
    // Z is a true belly-down crawl: wide and very low, distinct from the
    // Shift kneel / Unit-00 shield brace.
    private static final float PRONE_WIDTH = 24.0F;
    private static final float PRONE_HEIGHT = 8.5F;
    private static final float WALK_SPEED = 0.42F;
    private static final float CROUCH_SPEED = 0.18F;
    private static final float PRONE_SPEED = 0.10F;
    private static final float SPRINT_SPEED = 0.62F;
    private static final double JUMP_VELOCITY = 5.40D;
    private static final int JUMP_COOLDOWN_TICKS = 10;
    private static final int LAUNCH_ASCENT_TICKS = 34;
    private static final int LAUNCH_CLEAR_TICKS = 18;
    private static final double LAUNCH_TARGET_ABOVE_BED = 32.0D;
    private static final double SILO_ENTRY_MIN_HEIGHT = 24.0D;
    private static final double SILO_ENTRY_MAX_HEIGHT = 29.5D;
    private static final double SILO_ENTRY_MIN_REAR_DOT = 0.62D;
    private static final double SILO_ENTRY_MIN_DISTANCE = 0.75D;
    private static final double SILO_ENTRY_MAX_DISTANCE = 9.5D;
    private static final double ENTRY_PLUG_USE_REACH = 8.25D;
    private static final double ENTRY_PLUG_AIM_RADIUS = 2.0D;
    // Final entry-plug pivots in the reviewed 2.5x Tiger meshes. Keeping the
    // three sockets explicit makes interaction follow each airframe instead
    // of guessing from the entity AABB or a legacy cube body's chest.
    private static final double ENTRY_PLUG_HEIGHT_00 = 26.9164D;
    private static final double ENTRY_PLUG_HEIGHT_01 = 26.9170D;
    private static final double ENTRY_PLUG_HEIGHT_02 = 26.9178D;
    private static final double ENTRY_PLUG_REAR_OFFSET = 1.25D;
    private static final int LAUNCH_PASSENGER_RESTORE_GRACE_TICKS = 40;
    private static final int NO_LAUNCH_CARRIER = Integer.MIN_VALUE;
    /** Mechanical elevation envelope of the shared cannon/body aim rig. */
    public static final float MIN_CANNON_AIM_PITCH = -55.0F;
    public static final float MAX_CANNON_AIM_PITCH = 55.0F;
    // Muzzle sockets measured from the reviewed 2.5x Tiger rig and the
    // locally installed TV Pallet Rifle. The ray still starts at the pilot's
    // eye for fair aiming; tracers and sound start at the visible muzzle.
    private static final double RIFLE_STANDING_PIVOT_HEIGHT = 24.2201D;
    private static final double RIFLE_STANDING_PIVOT_FORWARD = 0.0D;
    private static final double RIFLE_STANDING_MUZZLE_FORWARD = 18.3308D;
    private static final double RIFLE_STANDING_MUZZLE_UP = 0.6153D;
    private static final double RIFLE_STANDING_MUZZLE_RIGHT = 1.2752D;
    private static final double RIFLE_PRONE_PIVOT_HEIGHT = 3.9523D;
    private static final double RIFLE_PRONE_PIVOT_FORWARD = 9.9317D;
    private static final double RIFLE_PRONE_MUZZLE_FORWARD = 19.9715D;
    private static final double RIFLE_PRONE_MUZZLE_UP = -0.4405D;
    private static final double RIFLE_PRONE_MUZZLE_RIGHT = 0.7458D;
    // Far-cap coordinates measured from the installed Kantrophe positron
    // cannon after the final two-hand pose. The old 12.5-block approximation
    // began the beam inside the receiver, visibly behind the barrel.
    private static final double CANNON_STANDING_PIVOT_HEIGHT = 24.2201D;
    private static final double CANNON_STANDING_PIVOT_FORWARD = 0.0D;
    private static final double CANNON_STANDING_MUZZLE_FORWARD = 22.4417D;
    private static final double CANNON_STANDING_MUZZLE_UP = 0.5960D;
    private static final double CANNON_STANDING_MUZZLE_RIGHT = 1.2263D;
    private static final double CANNON_PRONE_PIVOT_HEIGHT = 3.9523D;
    private static final double CANNON_PRONE_PIVOT_FORWARD = 9.9317D;
    private static final double CANNON_PRONE_MUZZLE_FORWARD = 23.9289D;
    private static final double CANNON_PRONE_MUZZLE_UP = -0.3676D;
    private static final double CANNON_PRONE_MUZZLE_RIGHT = 0.6284D;
    /** Starts the visible tracer just beyond the barrel cap instead of inside it. */
    private static final double MUZZLE_SURFACE_CLEARANCE = 0.25D;
    // Full-cycle travel measured from the real animated foot contacts after
    // the 2.5x model scale. Gecko's default 1x playback made the limbs cycle
    // several times faster than the chassis actually crossed the ground.
    private static final double WALK_STRIDE_BLOCKS = 25.8334D;
    private static final double RUN_STRIDE_BLOCKS = 31.3944D;
    private static final double CROUCH_STRIDE_BLOCKS = 9.2990D;
    private static final double CRAWL_STRIDE_BLOCKS = 5.0046D;
    private static final double WALK_CYCLE_SECONDS = 1.0D;
    private static final double RUN_CYCLE_SECONDS = 0.62D;
    // The mathematically exact contact stride reads like slow motion on a
    // thirty-block EVA. Preserve the foot-authored cycle while giving the
    // sprint a deliberate giant-humanoid cadence rather than a walking beat.
    private static final double WALK_CADENCE_GAIN = 1.45D;
    private static final double RUN_CADENCE_GAIN = 2.35D;
    private static final double CROUCH_CYCLE_SECONDS = 1.0D;
    private static final double CRAWL_CYCLE_SECONDS = 1.4D;

    private static final EntityDataAccessor<Integer> DATA_WEAPON =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> DATA_AT_ON =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Float> DATA_AT_ENERGY =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Integer> DATA_CANNON_CHARGE =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_CANNON_COOLDOWN =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Float> DATA_CANNON_AIM_PITCH =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Integer> DATA_N2_ARM_TICKS =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> DATA_CROUCHING =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Boolean> DATA_SPRINTING =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Boolean> DATA_PRONE =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.BOOLEAN);
    // Nailed to Tiferet by the SEELE scenario: pose locked, gravity off.
    private static final EntityDataAccessor<Boolean> DATA_CRUCIFIED =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Boolean> DATA_MELEE_LEFT =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Integer> DATA_MELEE_SEQUENCE =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_SMASH_SEQUENCE =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_JUMP_SEQUENCE =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_ACTIVATION_TICKS =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> DATA_ENTRY_PLUG_INSERTED =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Integer> DATA_VISUAL_POSE =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_LAUNCH_PHASE =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_LAUNCH_TICKS =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);

    private static final RawAnimation ANIM_IDLE = RawAnimation.begin().thenLoop("animation.eva_unit01.idle");
    private static final RawAnimation ANIM_WALK = RawAnimation.begin().thenLoop("animation.eva_unit01.walk");
    private static final RawAnimation ANIM_RUN = RawAnimation.begin().thenLoop("animation.eva_unit01.run");
    private static final RawAnimation ANIM_CROUCH = RawAnimation.begin().thenLoop("animation.eva_unit01.crouch");
    private static final RawAnimation ANIM_CROUCH_WALK = RawAnimation.begin().thenLoop("animation.eva_unit01.crouch_walk");
    private static final RawAnimation ANIM_TAKEOFF = RawAnimation.begin().thenPlay("animation.eva_unit01.takeoff");
    private static final RawAnimation ANIM_JUMP = RawAnimation.begin().thenLoop("animation.eva_unit01.jump");
    private static final RawAnimation ANIM_FALL = RawAnimation.begin().thenLoop("animation.eva_unit01.fall");
    private static final RawAnimation ANIM_PRONE = RawAnimation.begin().thenLoop("animation.eva_unit01.prone");
    private static final RawAnimation ANIM_CRUCIFIED = RawAnimation.begin().thenLoop("animation.eva_unit01.crucified");
    private static final RawAnimation ANIM_CRAWL = RawAnimation.begin().thenLoop("animation.eva_unit01.crawl");
    private static final RawAnimation ANIM_AIM = RawAnimation.begin().thenLoop("animation.eva_unit01.aim");
    private static final RawAnimation ANIM_RIFLE_AIM = RawAnimation.begin().thenLoop("animation.eva_unit01.rifle_aim");
    private static final RawAnimation ANIM_PRONE_AIM = RawAnimation.begin().thenLoop("animation.eva_unit01.prone_aim");
    private static final RawAnimation ANIM_N2_READY = RawAnimation.begin().thenLoop("animation.eva_unit01.n2_ready");
    private static final RawAnimation ANIM_LANCE_READY = RawAnimation.begin().thenLoop("animation.eva_unit01.lance_ready");
    private static final RawAnimation ANIM_LANCE_CARRY = RawAnimation.begin().thenLoop("animation.eva_unit01.lance_carry");
    private static final RawAnimation ANIM_SHIELD_BRACE = RawAnimation.begin().thenLoop("animation.eva_unit01.shield_brace");
    private static final RawAnimation ANIM_MELEE = RawAnimation.begin().thenPlay("animation.eva_unit01.melee");
    private static final RawAnimation ANIM_MELEE_LEFT = RawAnimation.begin().thenPlay("animation.eva_unit01.melee_left");
    private static final RawAnimation ANIM_KNIFE_READY = RawAnimation.begin().thenLoop("animation.eva_unit01.knife_ready");
    private static final RawAnimation ANIM_KNIFE = RawAnimation.begin().thenPlay("animation.eva_unit01.knife");
    private static final RawAnimation ANIM_KNIFE_LEFT = RawAnimation.begin().thenPlay("animation.eva_unit01.knife_left");
    private static final RawAnimation ANIM_KNIFE_HEAVY = RawAnimation.begin().thenPlay("animation.eva_unit01.knife_heavy");
    private static final RawAnimation ANIM_LANCE_THRUST = RawAnimation.begin().thenPlay("animation.eva_unit01.lance_thrust");
    private static final RawAnimation ANIM_PRONE_MELEE = RawAnimation.begin().thenPlay("animation.eva_unit01.prone_melee");
    private static final RawAnimation ANIM_PRONE_MELEE_LEFT = RawAnimation.begin().thenPlay("animation.eva_unit01.prone_melee_left");
    private static final RawAnimation ANIM_PRONE_KNIFE = RawAnimation.begin().thenPlay("animation.eva_unit01.prone_knife");
    private static final RawAnimation ANIM_PRONE_KNIFE_HEAVY = RawAnimation.begin().thenPlay("animation.eva_unit01.prone_knife_heavy");
    private static final RawAnimation ANIM_PRONE_LANCE_THRUST = RawAnimation.begin().thenPlay("animation.eva_unit01.prone_lance_thrust");
    private static final RawAnimation ANIM_PRONE_SMASH = RawAnimation.begin().thenPlay("animation.eva_unit01.prone_smash");
    private static final RawAnimation ANIM_CROUCH_MELEE = RawAnimation.begin().thenPlay("animation.eva_unit01.crouch_melee");
    private static final RawAnimation ANIM_CROUCH_MELEE_LEFT = RawAnimation.begin().thenPlay("animation.eva_unit01.crouch_melee_left");
    private static final RawAnimation ANIM_CROUCH_KNIFE = RawAnimation.begin().thenPlay("animation.eva_unit01.crouch_knife");
    private static final RawAnimation ANIM_CROUCH_KNIFE_HEAVY = RawAnimation.begin().thenPlay("animation.eva_unit01.crouch_knife_heavy");
    private static final RawAnimation ANIM_CROUCH_LANCE_THRUST = RawAnimation.begin().thenPlay("animation.eva_unit01.crouch_lance_thrust");
    private static final RawAnimation ANIM_CROUCH_SMASH = RawAnimation.begin().thenPlay("animation.eva_unit01.crouch_smash");
    private static final RawAnimation ANIM_PRONE_KNIFE_READY = RawAnimation.begin().thenLoop("animation.eva_unit01.prone_knife_ready");
    private static final RawAnimation ANIM_PRONE_LANCE_READY = RawAnimation.begin().thenLoop("animation.eva_unit01.prone_lance_ready");
    private static final RawAnimation ANIM_SMASH = RawAnimation.begin().thenPlay("animation.eva_unit01.smash");
    private static final RawAnimation ANIM_CANNON_FIRE = RawAnimation.begin().thenPlay("animation.eva_unit01.cannon_fire");
    private static final RawAnimation ANIM_PRONE_CANNON_FIRE = RawAnimation.begin().thenPlay("animation.eva_unit01.prone_cannon_fire");
    private static final RawAnimation ANIM_RIFLE_FIRE = RawAnimation.begin().thenPlay("animation.eva_unit01.rifle_fire");
    private static final RawAnimation ANIM_PRONE_RIFLE_FIRE = RawAnimation.begin().thenPlay("animation.eva_unit01.prone_rifle_fire");
    private static final RawAnimation ANIM_LAND = RawAnimation.begin().thenPlay("animation.eva_unit01.land");
    private static final RawAnimation ANIM_STOMP = RawAnimation.begin().thenPlay("animation.eva_unit01.stomp");
    private static final RawAnimation ANIM_ACTIVATION = RawAnimation.begin().thenPlay("animation.eva_unit01.activation");
    private static final RawAnimation ANIM_VISUAL_IDLE = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_idle");
    private static final RawAnimation ANIM_VISUAL_WALK = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_walk_contact");
    private static final RawAnimation ANIM_VISUAL_RUN = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_run_contact");
    private static final RawAnimation ANIM_VISUAL_JUMP = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_jump");
    private static final RawAnimation ANIM_VISUAL_FALL = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_fall");
    private static final RawAnimation ANIM_VISUAL_CROUCH_WALK = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_crouch_walk");
    private static final RawAnimation ANIM_VISUAL_CRAWL = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_crawl");
    private static final RawAnimation ANIM_VISUAL_KNIFE_READY = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_knife_ready");
    private static final RawAnimation ANIM_VISUAL_LANCE_READY = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_lance_ready");
    private static final RawAnimation ANIM_VISUAL_KNIFE_WINDUP = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_knife_windup");
    private static final RawAnimation ANIM_VISUAL_KNIFE_CONTACT = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_knife_contact");
    private static final RawAnimation ANIM_VISUAL_KNIFE_RECOVERY = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_knife_recovery");
    private static final RawAnimation ANIM_VISUAL_KNIFE_HEAVY_CONTACT = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_knife_heavy_contact");
    private static final RawAnimation ANIM_VISUAL_LANCE_WINDUP = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_lance_windup");
    private static final RawAnimation ANIM_VISUAL_LANCE_CONTACT = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_lance_contact");
    private static final RawAnimation ANIM_VISUAL_LANCE_RECOVERY = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_lance_recovery");
    private static final RawAnimation ANIM_VISUAL_CANNON = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_cannon");
    private static final RawAnimation ANIM_VISUAL_RIFLE = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_rifle");
    private static final RawAnimation ANIM_VISUAL_CROUCH_KNIFE_CONTACT = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_crouch_knife_contact");
    private static final RawAnimation ANIM_VISUAL_PRONE_KNIFE_CONTACT = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_prone_knife_contact");
    private static final RawAnimation ANIM_VISUAL_CROUCH_LANCE_CONTACT = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_crouch_lance_contact");
    private static final RawAnimation ANIM_VISUAL_PRONE_LANCE_CONTACT = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_prone_lance_contact");
    private static final RawAnimation ANIM_VISUAL_N2_READY = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_n2_ready");
    private static final RawAnimation ANIM_VISUAL_RIFLE_WALK_CONTACT = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_rifle_walk_contact");
    private static final RawAnimation ANIM_VISUAL_CROUCH_RIFLE_CONTACT = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_crouch_rifle_contact");
    private static final RawAnimation ANIM_VISUAL_PRONE_RIFLE = RawAnimation.begin().thenLoop("animation.eva_unit01.visual_prone_rifle");

    private final AnimatableInstanceCache geoCache = GeckoLibUtil.createInstanceCache(this);

    private boolean chargingHeld;
    private int meleeCooldown;
    private int smashCooldown;
    private int stompCooldown;
    private int rifleCooldown;
    private boolean leftSwing;
    private int atRegenDelay;
    private int jumpCooldown;
    private boolean crouchingDimensions;
    private boolean proneDimensions;
    private boolean wasAirborne;
    private int clientMeleeSequence;
    private int clientMeleeStartTick = -1000;
    private boolean clientMeleeLeft;
    private int clientSmashSequence;
    private int clientSmashStartTick = -1000;
    private int clientJumpSequence;
    private boolean clientJumpImpulsePending;
    @Nullable
    private BlockPos launchBedPos;
    private int launchCarrierY = NO_LAUNCH_CARRIER;
    private boolean launchRecoveryPending;
    private int launchPassengerRestoreGraceTicks;
    private float launchLockedYaw;

    public EvaUnit01Entity(EntityType<? extends EvaUnit01Entity> type, Level level)
    {
        super(type, level);
        this.setMaxUpStep(2.6F);
    }

    public static AttributeSupplier.Builder createAttributes()
    {
        return PathfinderMob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 300.0D)
                .add(Attributes.MOVEMENT_SPEED, 0.42D)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0D)
                .add(Attributes.ATTACK_DAMAGE, 12.0D)
                .add(ForgeMod.STEP_HEIGHT_ADDITION.get(), 1.0D);
    }

    @Override
    protected void defineSynchedData()
    {
        super.defineSynchedData();
        this.entityData.define(DATA_WEAPON, WEAPON_FISTS);
        this.entityData.define(DATA_AT_ON, false);
        this.entityData.define(DATA_AT_ENERGY, AT_FIELD_MAX);
        this.entityData.define(DATA_CANNON_CHARGE, 0);
        this.entityData.define(DATA_CANNON_COOLDOWN, 0);
        this.entityData.define(DATA_CANNON_AIM_PITCH, 0.0F);
        this.entityData.define(DATA_N2_ARM_TICKS, 0);
        this.entityData.define(DATA_CROUCHING, false);
        this.entityData.define(DATA_SPRINTING, false);
        this.entityData.define(DATA_PRONE, false);
        this.entityData.define(DATA_CRUCIFIED, false);
        this.entityData.define(DATA_MELEE_LEFT, false);
        this.entityData.define(DATA_MELEE_SEQUENCE, 0);
        this.entityData.define(DATA_SMASH_SEQUENCE, 0);
        this.entityData.define(DATA_JUMP_SEQUENCE, 0);
        this.entityData.define(DATA_ACTIVATION_TICKS, 0);
        this.entityData.define(DATA_ENTRY_PLUG_INSERTED, false);
        this.entityData.define(DATA_VISUAL_POSE, VISUAL_NORMAL);
        this.entityData.define(DATA_LAUNCH_PHASE, LAUNCH_IDLE);
        this.entityData.define(DATA_LAUNCH_TICKS, 0);
    }

    @Override
    public SpawnGroupData finalizeSpawn(ServerLevelAccessor level, DifficultyInstance difficulty,
                                        MobSpawnType reason, @Nullable SpawnGroupData spawnData,
                                        @Nullable CompoundTag dataTag)
    {
        if (SeeleConfig.COMMON_SPEC.isLoaded())
        {
            this.getAttribute(Attributes.MAX_HEALTH).setBaseValue(SeeleConfig.EVA_MAX_HEALTH.get());
            this.setHealth(this.getMaxHealth());
        }
        this.entityData.set(DATA_AT_ENERGY, this.getAtFieldCapacity());
        return super.finalizeSpawn(level, difficulty, reason, spawnData, dataTag);
    }

    @Override
    public void addAdditionalSaveData(CompoundTag tag)
    {
        super.addAdditionalSaveData(tag);
        tag.putBoolean("SeeleCrucified", this.isCrucified());
        tag.putBoolean("SeeleEntryPlugInserted", this.isEntryPlugInserted());
        if (this.isLaunchSequenceActive() && this.launchBedPos != null)
        {
            tag.putInt("SeeleLaunchPhase", this.getLaunchPhase());
            tag.putInt("SeeleLaunchTicks", this.getLaunchTicks());
            tag.putInt("SeeleActivationTicks", this.getActivationTicks());
            tag.putLong("SeeleLaunchBed", this.launchBedPos.asLong());
            tag.putFloat("SeeleLaunchYaw", this.launchLockedYaw);
            if (this.launchCarrierY != NO_LAUNCH_CARRIER)
            {
                tag.putInt("SeeleLaunchCarrierY", this.launchCarrierY);
            }
        }
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag)
    {
        super.readAdditionalSaveData(tag);
        boolean crucified = tag.getBoolean("SeeleCrucified");
        this.entityData.set(DATA_CRUCIFIED, crucified);
        this.entityData.set(DATA_ENTRY_PLUG_INSERTED, tag.getBoolean("SeeleEntryPlugInserted"));
        int phase = tag.getInt("SeeleLaunchPhase");
        if (phase >= LAUNCH_LOCKED && phase <= LAUNCH_CLEAR && tag.contains("SeeleLaunchBed"))
        {
            this.launchBedPos = BlockPos.of(tag.getLong("SeeleLaunchBed"));
            this.entityData.set(DATA_LAUNCH_PHASE, phase);
            this.entityData.set(DATA_LAUNCH_TICKS, Math.max(0, tag.getInt("SeeleLaunchTicks")));
            this.entityData.set(DATA_ACTIVATION_TICKS, Math.max(0, tag.getInt("SeeleActivationTicks")));
            this.launchCarrierY = tag.contains("SeeleLaunchCarrierY")
                    ? tag.getInt("SeeleLaunchCarrierY")
                    : Mth.floor(this.getY()) - 1;
            this.launchRecoveryPending = phase == LAUNCH_ASCENT;
            this.launchPassengerRestoreGraceTicks = LAUNCH_PASSENGER_RESTORE_GRACE_TICKS;
            this.launchLockedYaw = tag.contains("SeeleLaunchYaw")
                    ? tag.getFloat("SeeleLaunchYaw") : this.getYRot();
            this.setNoGravity(true);
        }
        else
        {
            // No launch tag is the normal case. Do not call reset here: that
            // would erase a deliberate vanilla NoGravity flag on every EVA
            // simply because the world was reloaded.
            this.entityData.set(DATA_LAUNCH_PHASE, LAUNCH_IDLE);
            this.entityData.set(DATA_LAUNCH_TICKS, 0);
            this.launchBedPos = null;
            this.launchCarrierY = NO_LAUNCH_CARRIER;
            this.launchRecoveryPending = false;
            this.launchPassengerRestoreGraceTicks = 0;
            this.launchLockedYaw = this.getYRot();
            if (crucified)
            {
                this.setNoGravity(true);
            }
        }
    }

    // ----- state accessors -----

    public int getWeapon()
    {
        return this.entityData.get(DATA_WEAPON);
    }

    public int getUnitVariant()
    {
        if (this.getType() == ModEntities.EVA_UNIT00.get())
        {
            return UNIT_00;
        }
        if (this.getType() == ModEntities.EVA_UNIT02.get())
        {
            return UNIT_02;
        }
        return UNIT_01;
    }

    public boolean isAtFieldOn()
    {
        return this.entityData.get(DATA_AT_ON);
    }

    public float getAtFieldEnergy()
    {
        return this.entityData.get(DATA_AT_ENERGY);
    }

    public float getAtFieldCapacity()
    {
        return switch (this.getUnitVariant())
        {
            case UNIT_00 -> 300.0F;
            case UNIT_02 -> 160.0F;
            default -> AT_FIELD_MAX;
        };
    }

    /** Unit-00's kneeling shield posture, used to cover the firing Unit. */
    public boolean isShieldBraced()
    {
        return this.getUnitVariant() == UNIT_00 && this.isPilotCrouching() && this.isAtFieldOn();
    }

    public int getCannonCharge()
    {
        return this.entityData.get(DATA_CANNON_CHARGE);
    }

    public int getCannonCooldown()
    {
        return this.entityData.get(DATA_CANNON_COOLDOWN);
    }

    public int getN2ArmTicks()
    {
        return this.entityData.get(DATA_N2_ARM_TICKS);
    }

    public float n2ArmProgress()
    {
        return Mth.clamp(this.getN2ArmTicks() / (float) SeeleConfig.N2_ARM_TICKS.get(), 0.0F, 1.0F);
    }

    /**
     * Physical barrel elevation shared by the visible Gecko rig and the shot
     * ray. Positive pitch points down, matching {@link Player#getXRot()}.
     */
    public float getCannonAimPitch()
    {
        return this.entityData.get(DATA_CANNON_AIM_PITCH);
    }

    /** Contact weapons alone are allowed to neutralize an Angel A.T. Field. */
    public boolean isMeleeWeapon()
    {
        return this.getWeapon() == WEAPON_FISTS || this.getWeapon() == WEAPON_KNIFE
                || this.getWeapon() == WEAPON_LANCE;
    }

    public boolean isPilotCrouching()
    {
        return this.entityData.get(DATA_CROUCHING);
    }

    public boolean isPilotSprinting()
    {
        return this.entityData.get(DATA_SPRINTING);
    }

    public boolean isPilotProne()
    {
        return this.entityData.get(DATA_PRONE);
    }

    public boolean isCrucified()
    {
        return this.entityData.get(DATA_CRUCIFIED);
    }

    public int getActivationTicks()
    {
        return this.entityData.get(DATA_ACTIVATION_TICKS);
    }

    /** The physical plug remains seated after its insertion animation ends. */
    public boolean isEntryPlugInserted()
    {
        return this.entityData.get(DATA_ENTRY_PLUG_INSERTED);
    }

    /**
     * World-space centre of this variant's reviewed dorsal entry socket.
     * This is also the authoritative target for the extended right-click ray.
     */
    public Vec3 getEntryPlugSocketPosition()
    {
        double height = switch (this.getUnitVariant())
        {
            case UNIT_00 -> ENTRY_PLUG_HEIGHT_00;
            case UNIT_02 -> ENTRY_PLUG_HEIGHT_02;
            default -> ENTRY_PLUG_HEIGHT_01;
        };
        Vec3 rear = this.getForward().multiply(-1.0D, 0.0D, -1.0D).normalize();
        return this.position().add(rear.scale(ENTRY_PLUG_REAR_OFFSET)).add(0.0D, height, 0.0D);
    }

    /** Client/server-identical narrow ray test for the dorsal plug hardware. */
    public boolean isEntryPlugTargeted(Player player)
    {
        Vec3 eye = player.getEyePosition();
        Vec3 toSocket = this.getEntryPlugSocketPosition().subtract(eye);
        double distanceSqr = toSocket.lengthSqr();
        if (distanceSqr > ENTRY_PLUG_USE_REACH * ENTRY_PLUG_USE_REACH || distanceSqr < 1.0E-6D)
        {
            return false;
        }
        Vec3 look = player.getViewVector(1.0F).normalize();
        double alongRay = toSocket.dot(look);
        if (alongRay <= 0.0D)
        {
            return false;
        }
        double missDistanceSqr = Math.max(0.0D, distanceSqr - alongRay * alongRay);
        return missDistanceSqr <= ENTRY_PLUG_AIM_RADIUS * ENTRY_PLUG_AIM_RADIUS;
    }

    public int getLaunchPhase()
    {
        return this.entityData.get(DATA_LAUNCH_PHASE);
    }

    public int getLaunchTicks()
    {
        return this.entityData.get(DATA_LAUNCH_TICKS);
    }

    /** Current mag-lev carrier layer, or {@link Integer#MIN_VALUE} while parked. */
    public int getLaunchCarrierY()
    {
        return this.launchCarrierY;
    }

    /** The armed carrier bed remains known while the EVA is rising above scan range. */
    @Nullable
    public BlockPos getLaunchBedPosition()
    {
        return this.launchBedPos;
    }

    public boolean isLaunchSequenceActive()
    {
        return this.getLaunchPhase() != LAUNCH_IDLE;
    }

    /** A NERV launch bed is identified by the lodestone directly under the carrier. */
    @Nullable
    public BlockPos findLaunchBed()
    {
        BlockPos base = BlockPos.containing(this.getX(), this.getY() - 0.2D, this.getZ());
        BlockPos nearest = null;
        double nearestDistance = Double.MAX_VALUE;
        for (int depth = 0; depth <= 2; depth++)
        {
            for (int x = -5; x <= 5; x++)
            {
                for (int z = -5; z <= 5; z++)
                {
                    BlockPos candidate = base.offset(x, -depth, z);
                    if (!this.level().getBlockState(candidate).is(Blocks.LODESTONE))
                    {
                        continue;
                    }
                    double distance = this.distanceToSqr(candidate.getX() + 0.5D,
                            this.getY(), candidate.getZ() + 0.5D);
                    if (distance < nearestDistance)
                    {
                        nearest = candidate.immutable();
                        nearestDistance = distance;
                    }
                }
            }
        }
        return nearest;
    }

    private boolean launchBedClaimedByAnother(BlockPos bed)
    {
        if (!(this.level() instanceof ServerLevel serverLevel))
        {
            return false;
        }
        AABB area = new AABB(bed).inflate(16.0D, 64.0D, 16.0D);
        return !serverLevel.getEntitiesOfClass(EvaUnit01Entity.class, area,
                unit -> unit != this && unit.isAlive() && unit.isLaunchSequenceActive()
                        && bed.equals(unit.getLaunchBedPosition())).isEmpty();
    }

    public float getActivationProgress(float partialTick)
    {
        return Mth.clamp((120.0F - this.getActivationTicks() + partialTick) / 120.0F, 0.0F, 1.0F);
    }

    public int getVisualPose()
    {
        return this.entityData.get(DATA_VISUAL_POSE);
    }

    /** Development-only fixed pose used by the screenshot Visual Lab. */
    public void setVisualPose(int pose)
    {
        int safePose = Mth.clamp(pose, VISUAL_NORMAL, VISUAL_LIVE_JUMP);
        this.entityData.set(DATA_VISUAL_POSE, safePose);
        if (safePose == VISUAL_KNIFE_WINDUP || safePose == VISUAL_KNIFE_CONTACT
                || safePose == VISUAL_KNIFE_RECOVERY || safePose == VISUAL_KNIFE_READY
                || safePose == VISUAL_CROUCH_KNIFE_CONTACT
                || safePose == VISUAL_PRONE_KNIFE_CONTACT
                || safePose == VISUAL_LIVE_KNIFE
                || safePose == VISUAL_LIVE_KNIFE_HEAVY)
        {
            this.entityData.set(DATA_WEAPON, WEAPON_KNIFE);
        }
        else if (safePose == VISUAL_CANNON || safePose == VISUAL_PRONE_CANNON)
        {
            this.entityData.set(DATA_WEAPON, WEAPON_CANNON);
        }
        else if (safePose == VISUAL_RIFLE || safePose == VISUAL_RIFLE_WALK_CONTACT
                || safePose == VISUAL_CROUCH_RIFLE_CONTACT
                || safePose == VISUAL_PRONE_RIFLE
                || safePose == VISUAL_LIVE_RIFLE)
        {
            this.entityData.set(DATA_WEAPON, WEAPON_RIFLE);
        }
        else if (safePose == VISUAL_LANCE_WINDUP || safePose == VISUAL_LANCE_CONTACT
                || safePose == VISUAL_LANCE_RECOVERY || safePose == VISUAL_LANCE_READY
                || safePose == VISUAL_CROUCH_LANCE_CONTACT
                || safePose == VISUAL_PRONE_LANCE_CONTACT
                || safePose == VISUAL_LIVE_LANCE)
        {
            this.entityData.set(DATA_WEAPON, WEAPON_LANCE);
        }
        else if (safePose == VISUAL_N2_READY)
        {
            this.entityData.set(DATA_WEAPON, WEAPON_N2);
        }
        else if (safePose != VISUAL_NORMAL)
        {
            this.entityData.set(DATA_WEAPON, WEAPON_FISTS);
        }
        if (safePose != VISUAL_NORMAL)
        {
            this.setDeltaMovement(Vec3.ZERO);
        }
    }

    /** Cockpit synchronization readout derived from the live airframe state. */
    public float getSynchronizationRatio(float partialTick)
    {
        float nominal = switch (this.getUnitVariant())
        {
            case UNIT_00 -> 38.2F;
            case UNIT_02 -> 52.4F;
            default -> 41.3F;
        };
        if (this.getActivationTicks() > 0)
        {
            return nominal * getActivationProgress(partialTick);
        }
        float hullPenalty = (1.0F - this.getHealth() / this.getMaxHealth()) * 11.0F;
        float fieldGain = this.isAtFieldOn() ? 1.6F : 0.0F;
        float motion = this.getDeltaMovement().horizontalDistanceSqr() > 0.002D
                ? Mth.sin((this.tickCount + partialTick) * 0.38F) * 1.25F
                : Mth.sin((this.tickCount + partialTick) * 0.08F) * 0.45F;
        float cannonLoad = this.getCannonCharge() > 0 ? -1.8F * this.chargeProgress() : 0.0F;
        return Mth.clamp(nominal - hullPenalty + fieldGain + motion + cannonLoad, 0.0F, 99.9F);
    }

    /** Nail to / release from the Tree. Gravity and pose follow the flag. */
    public void setCrucified(boolean crucified)
    {
        this.entityData.set(DATA_CRUCIFIED, crucified);
        this.setNoGravity(crucified);
        if (crucified)
        {
            this.setDeltaMovement(Vec3.ZERO);
            // The cross silhouette is authoritative: held weapons and Visual
            // Lab poses must not layer an aim animation over the outstretched
            // arms during the Third-Impact ritual.
            this.entityData.set(DATA_WEAPON, WEAPON_FISTS);
            this.entityData.set(DATA_VISUAL_POSE, VISUAL_NORMAL);
            this.entityData.set(DATA_CANNON_CHARGE, 0);
            this.entityData.set(DATA_CANNON_AIM_PITCH, 0.0F);
            this.entityData.set(DATA_N2_ARM_TICKS, 0);
            this.entityData.set(DATA_CROUCHING, false);
            this.entityData.set(DATA_PRONE, false);
            this.entityData.set(DATA_SPRINTING, false);
        }
    }

    public boolean isSwingingLeftArm()
    {
        return this.swingingArm == InteractionHand.OFF_HAND;
    }

    /** Camera-rig attack state, driven by the same server command as GeckoLib. */
    public float getCockpitAttackAnim(float partialTick)
    {
        float elapsed = this.tickCount - this.clientMeleeStartTick + partialTick;
        return elapsed >= 0.0F && elapsed < 10.0F ? elapsed / 10.0F : 0.0F;
    }

    public boolean isCockpitSwingingLeft()
    {
        return this.clientMeleeLeft;
    }

    public float getCockpitSmashAnim(float partialTick)
    {
        float elapsed = this.tickCount - this.clientSmashStartTick + partialTick;
        return elapsed >= 0.0F && elapsed < 18.0F ? elapsed / 18.0F : 0.0F;
    }

    // ----- pilot commands (validated by the packet handler) -----

    public void cycleWeapon(ServerPlayer pilot)
    {
        if (this.isPilotControlLocked())
        {
            return;
        }
        int next = (this.getWeapon() + 1) % 6;
        this.entityData.set(DATA_WEAPON, next);
        this.entityData.set(DATA_CANNON_CHARGE, 0);
        this.entityData.set(DATA_N2_ARM_TICKS, 0);
        if (next != WEAPON_CANNON && next != WEAPON_RIFLE)
        {
            this.entityData.set(DATA_CANNON_AIM_PITCH, 0.0F);
        }
        this.chargingHeld = false;
        pilot.displayClientMessage(Component.translatable(this.getWeaponTranslationKey()), true);
        this.playSound(SoundEvents.IRON_GOLEM_STEP, 2.0F, 1.4F);
    }

    public String getWeaponTranslationKey()
    {
        return switch (this.getWeapon())
        {
            case WEAPON_KNIFE -> "msg.projectseele.weapon_knife";
            case WEAPON_CANNON -> "msg.projectseele.weapon_cannon";
            case WEAPON_LANCE -> this.getUnitVariant() == UNIT_02
                    ? "msg.projectseele.weapon_unit02_special"
                    : "msg.projectseele.weapon_lance";
            case WEAPON_RIFLE -> "msg.projectseele.weapon_rifle";
            case WEAPON_N2 -> "msg.projectseele.weapon_n2";
            default -> "msg.projectseele.weapon_fists";
        };
    }

    public void toggleAtField(ServerPlayer pilot)
    {
        if (this.isPilotControlLocked())
        {
            return;
        }
        if (!this.isAtFieldOn() && this.getAtFieldEnergy() < AT_FIELD_MIN_TO_RAISE)
        {
            pilot.displayClientMessage(Component.translatable("msg.projectseele.at_field_low"), true);
            return;
        }
        boolean on = !this.isAtFieldOn();
        this.entityData.set(DATA_AT_ON, on);
        pilot.displayClientMessage(Component.translatable(
                on ? "msg.projectseele.at_field_on" : "msg.projectseele.at_field_off"), true);
        this.playSound(ModSounds.CRYSTAL_HIT.get(), 2.0F, on ? 0.8F : 0.5F);
        if (on && this.level() instanceof ServerLevel serverLevel)
        {
            Vec3 front = this.position().add(this.getForward().scale(7.5D)).add(0.0D, 15.0D, 0.0D);
            AtFieldFX.ripple(serverLevel, front, this.getForward());
        }
    }

    public void setChargingHeld(boolean held)
    {
        this.chargingHeld = held && !this.isPilotControlLocked();
    }

    /** Left-click from the plug: alternating swings in front of the Unit. */
    public void meleeAttack(ServerPlayer pilot)
    {
        if (this.isPilotControlLocked() || this.meleeCooldown > 0 || !this.isMeleeWeapon())
        {
            return;
        }
        this.meleeCooldown = MELEE_COOLDOWN_TICKS;
        boolean lance = this.getWeapon() == WEAPON_LANCE;
        boolean knife = this.getWeapon() == WEAPON_KNIFE;
        boolean fixedRightHandWeapon = lance || knife;
        this.leftSwing = fixedRightHandWeapon ? false : !this.leftSwing;
        this.entityData.set(DATA_MELEE_LEFT, this.leftSwing);
        this.entityData.set(DATA_MELEE_SEQUENCE,
                (this.entityData.get(DATA_MELEE_SEQUENCE) + 1) & Integer.MAX_VALUE);
        this.swing(this.leftSwing ? InteractionHand.OFF_HAND : InteractionHand.MAIN_HAND, true);
        boolean prone = this.isPilotProne();
        boolean crouching = this.isPilotCrouching();
        String animation = prone
                ? lance ? "prone_lance_thrust"
                    : knife ? "prone_knife"
                    : (this.leftSwing ? "prone_melee_left" : "prone_melee")
                : crouching
                    ? lance ? "crouch_lance_thrust"
                        : knife ? "crouch_knife"
                        : (this.leftSwing ? "crouch_melee_left" : "crouch_melee")
                : lance ? "lance_thrust"
                    : knife ? "knife"
                    : (this.leftSwing ? "melee_left" : "melee");
        this.triggerAnim("strike", animation);
        float baseDamage = lance ? MELEE_LANCE_DAMAGE : knife ? MELEE_KNIFE_DAMAGE : MELEE_FIST_DAMAGE;
        float damage = baseDamage * this.getMeleeMultiplier();
        Vec3 forward = this.getForward().multiply(1.0D, 0.0D, 1.0D).normalize();
        double strikeHeight = prone ? 3.2D : this.isPilotCrouching() ? 8.0D : 14.0D;
        double verticalRadius = prone ? 3.2D : this.isPilotCrouching() ? 6.0D : 10.0D;
        Vec3 center = this.position().add(forward.scale(MELEE_REACH))
                .add(0.0D, strikeHeight, 0.0D);
        AABB zone = new AABB(center, center).inflate(MELEE_RADIUS, verticalRadius, MELEE_RADIUS);
        this.strikeZone(pilot, zone, damage, 1.1D, center);
        this.playSound(knife || lance ? SoundEvents.PLAYER_ATTACK_SWEEP : SoundEvents.IRON_GOLEM_ATTACK, 2.5F,
                lance ? 0.48F : knife ? 0.7F : 0.8F);
    }

    /** Crouch + attack: a slow two-handed slam that flattens the area ahead. */
    public void smashAttack(ServerPlayer pilot)
    {
        if (this.isPilotControlLocked() || this.smashCooldown > 0 || !this.isMeleeWeapon())
        {
            return;
        }
        this.smashCooldown = SMASH_COOLDOWN_TICKS;
        this.entityData.set(DATA_SMASH_SEQUENCE,
                (this.entityData.get(DATA_SMASH_SEQUENCE) + 1) & Integer.MAX_VALUE);

        boolean knife = this.getWeapon() == WEAPON_KNIFE;
        boolean lance = this.getWeapon() == WEAPON_LANCE;
        String animation = knife
                ? this.isPilotProne() ? "prone_knife_heavy"
                    : this.isPilotCrouching() ? "crouch_knife_heavy" : "knife_heavy"
                : this.isPilotProne() ? "prone_smash"
                    : this.isPilotCrouching() ? "crouch_smash" : "smash";
        this.triggerAnim("strike", animation);
        float baseDamage = lance ? SMASH_LANCE_DAMAGE : knife ? SMASH_KNIFE_DAMAGE : SMASH_FIST_DAMAGE;
        float damage = baseDamage * this.getMeleeMultiplier();
        Vec3 forward = this.getForward().multiply(1.0D, 0.0D, 1.0D).normalize();
        Vec3 center = this.position().add(forward.scale(MELEE_REACH + 1.0D)).add(0.0D, 4.0D, 0.0D);
        AABB zone = new AABB(center, center).inflate(SMASH_RADIUS, 8.5D, SMASH_RADIUS);
        this.strikeZone(pilot, zone, damage, 2.0D, center);
        if (this.level() instanceof ServerLevel serverLevel)
        {
            serverLevel.sendParticles(ParticleTypes.EXPLOSION,
                    center.x, center.y - 2.0D, center.z, 10, 3.5D, 0.6D, 3.5D, 0.0D);
        }
        this.playSound(knife ? SoundEvents.PLAYER_ATTACK_SWEEP : SoundEvents.IRON_GOLEM_DEATH,
                3.0F, knife ? 0.68F : 0.55F);
    }

    /** Heavy single-foot strike for targets beneath the Unit. */
    public void stompAttack(ServerPlayer pilot)
    {
        if (this.isPilotControlLocked() || this.isPilotProne()
                || this.stompCooldown > 0 || !this.isMeleeWeapon())
        {
            return;
        }
        this.stompCooldown = STOMP_COOLDOWN_TICKS;
        this.triggerAnim("strike", "stomp");

        Vec3 forward = this.getForward().multiply(1.0D, 0.0D, 1.0D).normalize();
        Vec3 center = this.position().add(forward.scale(2.8D)).add(0.0D, 1.0D, 0.0D);
        AABB zone = new AABB(center, center).inflate(STOMP_RADIUS, 3.5D, STOMP_RADIUS);
        this.strikeZone(pilot, zone, STOMP_DAMAGE * this.getMeleeMultiplier(), 2.4D, center);
        if (this.level() instanceof ServerLevel serverLevel)
        {
            serverLevel.sendParticles(ParticleTypes.CLOUD,
                    center.x, center.y, center.z, 34, 3.8D, 0.35D, 3.8D, 0.06D);
            serverLevel.sendParticles(ParticleTypes.EXPLOSION,
                    center.x, center.y, center.z, 8, 2.4D, 0.3D, 2.4D, 0.0D);
        }
        this.playSound(SoundEvents.GENERIC_EXPLODE, 3.2F, 0.58F);
    }

    private void strikeZone(ServerPlayer pilot, AABB zone, float damage, double knockback, Vec3 fxCenter)
    {
        if (!(this.level() instanceof ServerLevel serverLevel))
        {
            return;
        }
        boolean knife = this.getWeapon() == WEAPON_KNIFE;
        boolean lance = this.getWeapon() == WEAPON_LANCE;
        boolean anyHit = false;
        for (LivingEntity target : serverLevel.getEntitiesOfClass(LivingEntity.class, zone,
                e -> e != this && e != pilot && !this.hasPassenger(e) && e.isAlive()))
        {
            // Damage sourced directly from the Unit: Angel A.T. Fields
            // treat EVA contact as neutralized and let it through.
            target.hurt(this.damageSources().mobAttack(this), damage);
            target.knockback(knockback, this.getX() - target.getX(), this.getZ() - target.getZ());
            anyHit = true;
            // Impact burst on the body actually struck.
            Vec3 hit = target.position().add(0.0D, target.getBbHeight() * 0.55D, 0.0D);
            serverLevel.sendParticles(ParticleTypes.CRIT, hit.x, hit.y, hit.z, 26, 1.4D, 1.4D, 1.4D, 0.55D);
            serverLevel.sendParticles(knife || lance ? ParticleTypes.ENCHANTED_HIT : ParticleTypes.DAMAGE_INDICATOR,
                    hit.x, hit.y, hit.z, 14, 1.0D, 1.0D, 1.0D, 0.2D);
        }
        // The swing arc itself: a fan of sweep across the strike front.
        Vec3 side = this.getForward().yRot((float) Math.toRadians(90.0D));
        for (int i = -2; i <= 2; i++)
        {
            Vec3 p = fxCenter.add(side.scale(i * 1.6D));
            serverLevel.sendParticles(ParticleTypes.SWEEP_ATTACK, p.x, p.y, p.z, 1, 0.0D, 0.0D, 0.0D, 0.0D);
        }
        if (knife)
        {
            // High-vibration blade wake.
            serverLevel.sendParticles(ParticleTypes.ELECTRIC_SPARK,
                    fxCenter.x, fxCenter.y, fxCenter.z, 30, 2.0D, 1.4D, 2.0D, 0.35D);
        }
        if (lance)
        {
            serverLevel.sendParticles(ParticleTypes.END_ROD,
                    fxCenter.x, fxCenter.y, fxCenter.z, 44, 2.4D, 2.0D, 2.4D, 0.45D);
            serverLevel.sendParticles(ParticleTypes.ELECTRIC_SPARK,
                    fxCenter.x, fxCenter.y, fxCenter.z, 52, 2.8D, 2.2D, 2.8D, 0.55D);
        }
        if (!anyHit)
        {
            // Whiff: a little air displacement so empty swings still feel weighty.
            serverLevel.sendParticles(ParticleTypes.CLOUD, fxCenter.x, fxCenter.y, fxCenter.z,
                    6, 1.2D, 0.8D, 1.2D, 0.02D);
        }
    }

    private float getMeleeMultiplier()
    {
        return switch (this.getUnitVariant())
        {
            case UNIT_00 -> 0.85F;
            case UNIT_02 -> 1.20F;
            default -> 1.0F;
        };
    }

    /** Use-key released: fire if fully charged, otherwise just power down. */
    public void releaseCannon(ServerPlayer pilot)
    {
        this.chargingHeld = false;
        if (this.getWeapon() == WEAPON_N2)
        {
            this.entityData.set(DATA_N2_ARM_TICKS, 0);
            return;
        }
        boolean full = this.getCannonCharge() >= SeeleConfig.CANNON_CHARGE_TICKS.get();
        this.entityData.set(DATA_CANNON_CHARGE, 0);
        if (this.isPilotControlLocked() || !full || this.getWeapon() != WEAPON_CANNON
                || this.getCannonCooldown() > 0)
        {
            return;
        }
        this.entityData.set(DATA_CANNON_COOLDOWN, SeeleConfig.CANNON_COOLDOWN_TICKS.get());
        if (this.level() instanceof ServerLevel serverLevel)
        {
            this.fireCannon(serverLevel, pilot);
        }
    }

    public void setPilotCrouching(ServerPlayer pilot, boolean crouching)
    {
        if (this.getControllingPassenger() != pilot || this.isPilotControlLocked()
                || this.isPilotCrouching() == crouching)
        {
            return;
        }
        if (!crouching && !this.hasStandingRoom())
        {
            pilot.displayClientMessage(Component.translatable("msg.projectseele.cannot_stand"), true);
            return;
        }
        if (crouching)
        {
            this.entityData.set(DATA_PRONE, false);
        }
        this.entityData.set(DATA_CROUCHING, crouching);
        this.entityData.set(DATA_SPRINTING, false);
        this.updatePoseDimensions();
    }

    public void toggleProne(ServerPlayer pilot)
    {
        if (this.getControllingPassenger() != pilot || this.isPilotControlLocked())
        {
            return;
        }
        boolean prone = !this.isPilotProne();
        if (!prone && !this.hasStandingRoom())
        {
            pilot.displayClientMessage(Component.translatable("msg.projectseele.cannot_stand"), true);
            return;
        }
        this.entityData.set(DATA_PRONE, prone);
        this.entityData.set(DATA_CROUCHING, false);
        this.entityData.set(DATA_SPRINTING, false);
        this.updatePoseDimensions();
    }

    public void setPilotSprinting(ServerPlayer pilot, boolean sprinting)
    {
        if (this.getControllingPassenger() == pilot && !this.isPilotControlLocked())
        {
            this.entityData.set(DATA_SPRINTING, sprinting && !this.isPilotCrouching() && !this.isPilotProne()
                    && this.getCannonCharge() <= 0);
        }
    }

    public void pilotJump(ServerPlayer pilot)
    {
        // Visual Lab stands a 24-block entity on a one-block fixture.  During
        // an overloaded integrated-server screenshot tick the client can send
        // jump while the server still reports the fixture's tiny -0.078
        // settling velocity.  Permit that narrow development pose only; real
        // driving still requires Minecraft's authoritative onGround flag.
        boolean visualLabSettling = this.getVisualPose() == VISUAL_LIVE_JUMP
                && Math.abs(this.getDeltaMovement().y) < 0.12D;
        if (this.getControllingPassenger() != pilot || this.isPilotControlLocked()
                || !this.onGround() && !visualLabSettling
                || this.jumpCooldown > 0 || this.getCannonCharge() > 0)
        {
            if (this.getVisualPose() == VISUAL_LIVE_JUMP)
            {
                ProjectSeele.LOGGER.warn(
                        "Visual live jump rejected controlling={} locked={} onGround={} settling={} cooldown={} charge={}",
                        this.getControllingPassenger() == pilot, this.isPilotControlLocked(),
                        this.onGround(), visualLabSettling, this.jumpCooldown,
                        this.getCannonCharge());
            }
            return;
        }
        if (this.isPilotCrouching())
        {
            this.setPilotCrouching(pilot, false);
            if (this.isPilotCrouching())
            {
                return;
            }
        }
        if (this.isPilotProne())
        {
            this.toggleProne(pilot);
            if (this.isPilotProne())
            {
                return;
            }
        }
        Vec3 motion = this.getDeltaMovement();
        this.triggerAnim("strike", "takeoff");
        // A ridden living entity is movement-authoritative on the pilot's
        // client. Setting velocity only on the logical server is overwritten
        // by the next ServerboundMoveVehiclePacket, which previously reduced
        // every configured EVA jump to a one-block hop. The monotonically
        // increasing sequence authorizes the same impulse on that client.
        this.entityData.set(DATA_JUMP_SEQUENCE,
                this.entityData.get(DATA_JUMP_SEQUENCE) + 1);
        this.setDeltaMovement(motion.x, JUMP_VELOCITY, motion.z);
        if (this.getVisualPose() == VISUAL_LIVE_JUMP)
        {
            ProjectSeele.LOGGER.info("Visual live jump accepted velocityY={}", JUMP_VELOCITY);
        }
        this.hasImpulse = true;
        this.jumpCooldown = JUMP_COOLDOWN_TICKS;
        this.playSound(SoundEvents.IRON_GOLEM_STEP, 2.2F, 0.65F);
    }

    public void exitEva(ServerPlayer pilot)
    {
        if (this.getControllingPassenger() == pilot)
        {
            if (this.isLaunchSequenceActive())
            {
                pilot.displayClientMessage(Component.translatable("message.projectseele.launch_interlock"), true);
                return;
            }
            pilot.stopRiding();
            if (this.isCrucified())
            {
                // Stepping out of a cross hundreds of blocks up.
                pilot.addEffect(new net.minecraft.world.effect.MobEffectInstance(
                        net.minecraft.world.effect.MobEffects.SLOW_FALLING, 20 * 60, 0));
            }
        }
    }

    /** Automatic EVA pallet SMG: hitscan damage and a brief tracer, never an explosion. */
    public void fireRifle(ServerPlayer pilot)
    {
        if (this.isPilotControlLocked() || this.getWeapon() != WEAPON_RIFLE
                || this.rifleCooldown > 0 || this.getControllingPassenger() != pilot
                || !(this.level() instanceof ServerLevel level))
        {
            return;
        }
        this.rifleCooldown = SeeleConfig.EVA_RIFLE_INTERVAL_TICKS.get();
        this.triggerAnim("strike", this.isPilotProne()
                ? "prone_rifle_fire" : "rifle_fire");
        Vec3 dir = this.pilotAimDirection(pilot);
        Vec3 sight = pilot.getEyePosition();
        Vec3 farEnd = sight.add(dir.scale(SeeleConfig.EVA_RIFLE_RANGE.get()));
        BlockHitResult blockHit = level.clip(
                new ClipContext(sight, farEnd, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, this));
        Vec3 end = blockHit.getLocation();
        EntityHitResult entityHit = ProjectileUtil.getEntityHitResult(level, pilot, sight, end,
                new AABB(sight, end).inflate(1.25D),
                entity -> entity instanceof LivingEntity && entity != pilot && entity != this
                        && !entity.isSpectator() && entity.isAlive());
        if (entityHit != null)
        {
            end = entityHit.getLocation();
            entityHit.getEntity().hurt(pilot.damageSources().playerAttack(pilot),
                    SeeleConfig.EVA_RIFLE_DAMAGE.get().floatValue());
        }

        Vec3 muzzle = this.rifleMuzzlePosition(dir);
        SeeleNetwork.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> this),
                new ClientboundRifleTracerPacket(muzzle.x, muzzle.y, muzzle.z, end.x, end.y, end.z));
        level.sendParticles(ParticleTypes.CRIT, end.x, end.y, end.z,
                entityHit == null ? 2 : 9, 0.35D, 0.35D, 0.35D, 0.18D);
        level.playSound(null, muzzle.x, muzzle.y, muzzle.z, ModSounds.RIFLE_FIRE.get(),
                SoundSource.PLAYERS, 2.4F, 1.25F + this.random.nextFloat() * 0.12F);
    }

    private Vec3 rifleMuzzlePosition(Vec3 aimDirection)
    {
        Vec3 horizontal = aimDirection.multiply(1.0D, 0.0D, 1.0D).normalize();
        Vec3 right = new Vec3(horizontal.z, 0.0D, -horizontal.x);
        double horizontalLength = Math.sqrt(aimDirection.x * aimDirection.x
                + aimDirection.z * aimDirection.z);
        Vec3 pitchedUp = horizontal.scale(-aimDirection.y)
                .add(0.0D, horizontalLength, 0.0D).normalize();
        boolean prone = this.isPilotProne();
        double pivotHeight = prone ? RIFLE_PRONE_PIVOT_HEIGHT
                : RIFLE_STANDING_PIVOT_HEIGHT;
        double pivotForward = prone ? RIFLE_PRONE_PIVOT_FORWARD
                : RIFLE_STANDING_PIVOT_FORWARD;
        double muzzleForward = prone ? RIFLE_PRONE_MUZZLE_FORWARD
                : RIFLE_STANDING_MUZZLE_FORWARD;
        double muzzleUp = prone ? RIFLE_PRONE_MUZZLE_UP
                : RIFLE_STANDING_MUZZLE_UP;
        double muzzleRight = prone ? RIFLE_PRONE_MUZZLE_RIGHT
                : RIFLE_STANDING_MUZZLE_RIGHT;
        Vec3 pivot = this.position().add(0.0D, pivotHeight, 0.0D)
                .add(horizontal.scale(pivotForward));
        return pivot.add(aimDirection.scale(muzzleForward + MUZZLE_SURFACE_CLEARANCE))
                .add(pitchedUp.scale(muzzleUp)).add(right.scale(muzzleRight));
    }

    private Vec3 cannonMuzzlePosition(Vec3 aimDirection)
    {
        Vec3 horizontal = aimDirection.multiply(1.0D, 0.0D, 1.0D).normalize();
        Vec3 right = new Vec3(horizontal.z, 0.0D, -horizontal.x);
        double horizontalLength = Math.sqrt(aimDirection.x * aimDirection.x
                + aimDirection.z * aimDirection.z);
        Vec3 pitchedUp = horizontal.scale(-aimDirection.y)
                .add(0.0D, horizontalLength, 0.0D).normalize();
        boolean prone = this.isPilotProne();
        double pivotHeight = prone ? CANNON_PRONE_PIVOT_HEIGHT
                : CANNON_STANDING_PIVOT_HEIGHT;
        double pivotForward = prone ? CANNON_PRONE_PIVOT_FORWARD
                : CANNON_STANDING_PIVOT_FORWARD;
        double muzzleForward = prone ? CANNON_PRONE_MUZZLE_FORWARD
                : CANNON_STANDING_MUZZLE_FORWARD;
        double muzzleUp = prone ? CANNON_PRONE_MUZZLE_UP
                : CANNON_STANDING_MUZZLE_UP;
        double muzzleRight = prone ? CANNON_PRONE_MUZZLE_RIGHT
                : CANNON_STANDING_MUZZLE_RIGHT;
        Vec3 pivot = this.position().add(0.0D, pivotHeight, 0.0D)
                .add(horizontal.scale(pivotForward));
        return pivot.add(aimDirection.scale(muzzleForward + MUZZLE_SURFACE_CLEARANCE))
                .add(pitchedUp.scale(muzzleUp)).add(right.scale(muzzleRight));
    }

    private void detonateN2(ServerLevel level, ServerPlayer pilot)
    {
        this.chargingHeld = false;
        this.entityData.set(DATA_N2_ARM_TICKS, 0);
        Vec3 groundZero = this.position();
        Vec3 flash = groundZero.add(0.0D, 5.0D, 0.0D);
        StrategicExplosionDirector.startN2(level, groundZero, this);
        SeeleNetwork.CHANNEL.send(PacketDistributor.NEAR.with(() -> new PacketDistributor.TargetPoint(
                        flash.x, flash.y, flash.z, 1024.0D, level.dimension())),
                new ClientboundNukeFxPacket(flash.x, flash.y, flash.z, 10.8F, false));
        level.sendParticles(ParticleTypes.EXPLOSION_EMITTER,
                flash.x, flash.y, flash.z, 24, 12.0D, 7.0D, 12.0D, 0.0D);
        level.playSound(null, flash.x, flash.y, flash.z, SoundEvents.GENERIC_EXPLODE,
                SoundSource.PLAYERS, 12.0F, 0.38F);
        pilot.stopRiding();
        pilot.hurt(level.damageSources().genericKill(), Float.MAX_VALUE);
        this.hurt(level.damageSources().genericKill(), Float.MAX_VALUE);
    }

    private boolean isPilotControlLocked()
    {
        return this.getActivationTicks() > 20 || this.isLaunchSequenceActive();
    }

    private boolean hasStandingRoom()
    {
        double halfWidth = NORMAL_WIDTH * 0.5D;
        AABB standing = new AABB(this.getX() - halfWidth, this.getY(), this.getZ() - halfWidth,
                this.getX() + halfWidth, this.getY() + NORMAL_HEIGHT, this.getZ() + halfWidth);
        return this.level().noCollision(this, standing);
    }

    private void fireCannon(ServerLevel level, ServerPlayer pilot)
    {
        this.triggerAnim("strike", this.isPilotProne()
                ? "prone_cannon_fire" : "cannon_fire");
        // Sample the authoritative pilot rotation at the release packet, not
        // the previous entity-data frame. This removes the last one-tick yaw
        // or pitch discrepancy between the optical reticle and impact point.
        Vec3 dir = this.pilotAimDirection(pilot);
        // Match the reviewed hand/receiver pivots of the authored standing and
        // prone cannon stances. A fixed standing-height muzzle would otherwise
        // fire more than sixteen blocks above the visible prone weapon.
        Vec3 muzzle = this.cannonMuzzlePosition(dir);
        Vec3 from = muzzle;
        double range = SeeleConfig.CANNON_RANGE.get();
        Vec3 farEnd = from.add(dir.scale(range));
        BlockHitResult blockHit = level.clip(
                new ClipContext(from, farEnd, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, this));
        Vec3 end = blockHit.getLocation();

        EntityHitResult entityHit = ProjectileUtil.getEntityHitResult(level, pilot, from, end,
                new AABB(from, end).inflate(1.0D),
                e -> e instanceof LivingEntity && e != pilot && e != this && !e.isSpectator() && e.isAlive());

        if (entityHit != null)
        {
            end = entityHit.getLocation();
            if (entityHit.getEntity() instanceof RamielEntity ramiel && ramiel.isCoreShot(from, dir))
            {
                // The Yashima shot: two clean core hits end the Angel.
                ramiel.hurt(pilot.damageSources().playerAttack(pilot),
                        SeeleConfig.CANNON_CORE_DAMAGE.get().floatValue());
            }
            else
            {
                entityHit.getEntity().hurt(pilot.damageSources().playerAttack(pilot),
                        SeeleConfig.CANNON_MOB_DAMAGE.get().floatValue());
            }
        }

        // The shot itself detonates: damage is immediate, while the mountain-
        // scale crater is carved across later server ticks so one frame never
        // attempts millions of block updates.
        StrategicExplosionDirector.startCannon(level, end, this);
        final Vec3 impact = end;

        SeeleNetwork.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> this),
                new ClientboundCannonBeamPacket(muzzle.x, muzzle.y, muzzle.z, end.x, end.y, end.z));
        SeeleNetwork.CHANNEL.send(PacketDistributor.NEAR.with(() -> new PacketDistributor.TargetPoint(
                        impact.x, impact.y, impact.z, 320.0D, level.dimension())),
                new ClientboundNukeFxPacket(impact.x, impact.y, impact.z, 3.6F, false));
        level.sendParticles(ParticleTypes.END_ROD, impact.x, impact.y, impact.z, 54, 1.4D, 1.4D, 1.4D, 0.24D);
        level.sendParticles(ParticleTypes.EXPLOSION_EMITTER,
                impact.x, impact.y + 1.5D, impact.z, 6, 3.5D, 1.8D, 3.5D, 0.0D);
        for (int i = 2; i <= 24; i += 3)
        {
            level.sendParticles(ParticleTypes.LARGE_SMOKE,
                    impact.x, impact.y + i, impact.z, 8, 1.7D, 1.0D, 1.7D, 0.015D);
        }
        level.sendParticles(ParticleTypes.CAMPFIRE_COSY_SMOKE,
                impact.x, impact.y + 25.0D, impact.z, 70, 9.5D, 2.5D, 9.5D, 0.02D);
        level.playSound(null, this.getX(), this.getY(), this.getZ(),
                ModSounds.BEAM_FIRE.get(), SoundSource.PLAYERS, 4.0F, 1.25F);
    }

    /** Exact optical/fire ray shared by cannon and pallet SMG. */
    private Vec3 pilotAimDirection(Player pilot)
    {
        float pitch = Mth.clamp(pilot.getXRot(), MIN_CANNON_AIM_PITCH,
                MAX_CANNON_AIM_PITCH);
        this.entityData.set(DATA_CANNON_AIM_PITCH, pitch);
        return Vec3.directionFromRotation(pitch, pilot.getYRot()).normalize();
    }

    // ----- per-tick combat state -----

    @Override
    public void aiStep()
    {
        super.aiStep();
        if (this.level().isClientSide)
        {
            return;
        }
        if (this.meleeCooldown > 0)
        {
            this.meleeCooldown--;
        }
        if (this.smashCooldown > 0)
        {
            this.smashCooldown--;
        }
        if (this.stompCooldown > 0)
        {
            this.stompCooldown--;
        }
        if (this.rifleCooldown > 0)
        {
            this.rifleCooldown--;
        }
        if (this.jumpCooldown > 0)
        {
            this.jumpCooldown--;
        }
        if (this.getControllingPassenger() != null && !this.isEntryPlugInserted())
        {
            // Covers passenger restoration and development commands that use
            // startRiding directly instead of the normal plug interaction.
            this.entityData.set(DATA_ENTRY_PLUG_INSERTED, true);
        }
        if (this.getActivationTicks() > 0)
        {
            this.entityData.set(DATA_ACTIVATION_TICKS, this.getActivationTicks() - 1);
        }
        this.tickLaunchSequence();
        if (!this.onGround())
        {
            this.wasAirborne = true;
        }
        else if (this.wasAirborne)
        {
            this.wasAirborne = false;
            this.triggerAnim("strike", "land");
            if (this.level() instanceof ServerLevel serverLevel)
            {
                serverLevel.sendParticles(ParticleTypes.CLOUD, this.getX(), this.getY() + 0.4D, this.getZ(),
                        22, 3.2D, 0.25D, 3.2D, 0.04D);
            }
            this.playSound(SoundEvents.IRON_GOLEM_STEP, 2.8F, 0.52F);
        }
        int cooldown = this.getCannonCooldown();
        if (cooldown > 0)
        {
            this.entityData.set(DATA_CANNON_COOLDOWN, cooldown - 1);
        }

        int charge = this.getCannonCharge();
        boolean canCharge = this.chargingHeld && this.getWeapon() == WEAPON_CANNON
                && this.getCannonCooldown() <= 0 && this.getControllingPassenger() != null;
        if (canCharge)
        {
            if (charge < SeeleConfig.CANNON_CHARGE_TICKS.get())
            {
                this.entityData.set(DATA_CANNON_CHARGE, charge + 1);
            }
        }
        else if (charge > 0 && !this.chargingHeld)
        {
            this.entityData.set(DATA_CANNON_CHARGE, 0);
        }

        int n2Arm = this.getN2ArmTicks();
        boolean canArmN2 = this.chargingHeld && this.getWeapon() == WEAPON_N2
                && this.getControllingPassenger() instanceof ServerPlayer;
        if (canArmN2)
        {
            int next = Math.min(SeeleConfig.N2_ARM_TICKS.get(), n2Arm + 1);
            this.entityData.set(DATA_N2_ARM_TICKS, next);
            if (next >= SeeleConfig.N2_ARM_TICKS.get()
                    && this.getControllingPassenger() instanceof ServerPlayer pilot)
            {
                this.detonateN2((ServerLevel) this.level(), pilot);
            }
        }
        else if (n2Arm > 0)
        {
            this.entityData.set(DATA_N2_ARM_TICKS, 0);
        }

        if (this.atRegenDelay > 0)
        {
            this.atRegenDelay--;
        }
        else if (this.getAtFieldEnergy() < this.getAtFieldCapacity())
        {
            this.entityData.set(DATA_AT_ENERGY,
                    Math.min(this.getAtFieldCapacity(), this.getAtFieldEnergy() + AT_FIELD_REGEN));
        }
        if (this.isAtFieldOn() && this.getAtFieldEnergy() <= 0.0F)
        {
            this.entityData.set(DATA_AT_ON, false);
            this.playSound(ModSounds.CRYSTAL_BREAK.get(), 2.0F, 1.2F);
        }
        if (this.getControllingPassenger() == null)
        {
            this.clearPilotMotion();
        }
    }

    private void armLaunchBed(BlockPos bed)
    {
        this.launchBedPos = bed.immutable();
        this.launchLockedYaw = this.getYRot();
        this.entityData.set(DATA_LAUNCH_PHASE, LAUNCH_LOCKED);
        this.entityData.set(DATA_LAUNCH_TICKS, this.getActivationTicks());
        this.launchCarrierY = bed.getY();
        this.launchRecoveryPending = false;
        this.launchPassengerRestoreGraceTicks = 0;
        this.entityData.set(DATA_CROUCHING, false);
        this.entityData.set(DATA_PRONE, false);
        this.entityData.set(DATA_SPRINTING, false);
        this.updatePoseDimensions();
        this.setNoGravity(true);
        this.enforceLaunchLock();
        ProjectSeele.LOGGER.info("NERV launch locked: eva={} bed={} targetY={}",
                this.getStringUUID(), bed.toShortString(), bed.getY() + LAUNCH_TARGET_ABOVE_BED);
    }

    /** Hold the complete airframe on its audited bed until catapult release. */
    private void enforceLaunchLock()
    {
        if (this.launchBedPos == null)
        {
            return;
        }
        this.getNavigation().stop();
        this.setTarget(null);
        this.setPos(this.launchBedPos.getX() + 0.5D, this.launchBedPos.getY() + 1.0D,
                this.launchBedPos.getZ() + 0.5D);
        this.setDeltaMovement(Vec3.ZERO);
        this.setRot(this.launchLockedYaw, 0.0F);
        this.yRotO = this.yBodyRot = this.yHeadRot = this.launchLockedYaw;
        this.fallDistance = 0.0F;
        this.hasImpulse = true;
        for (Entity passenger : this.getPassengers())
        {
            this.positionRider(passenger, Entity::setPos);
        }
    }

    private void beginLaunchAscent()
    {
        if (this.launchBedPos == null || !this.level().getBlockState(this.launchBedPos).is(Blocks.LODESTONE))
        {
            this.resetLaunchSequence();
            return;
        }
        this.entityData.set(DATA_LAUNCH_PHASE, LAUNCH_ASCENT);
        this.entityData.set(DATA_LAUNCH_TICKS, LAUNCH_ASCENT_TICKS);
        this.setSurfaceCarrier(false);
        this.setNoGravity(true);
        this.setPos(this.launchBedPos.getX() + 0.5D, this.launchBedPos.getY() + 1.0D,
                this.launchBedPos.getZ() + 0.5D);
        this.setDeltaMovement(Vec3.ZERO);
        ProjectSeele.LOGGER.info("NERV launch ascent: eva={} ticks={}",
                this.getStringUUID(), LAUNCH_ASCENT_TICKS);
        this.playSound(SoundEvents.PISTON_EXTEND, 3.0F, 0.48F);
        if (this.level() instanceof ServerLevel serverLevel)
        {
            serverLevel.sendParticles(ParticleTypes.CLOUD, this.getX(), this.getY() + 0.4D, this.getZ(),
                    72, 4.2D, 0.7D, 4.2D, 0.16D);
            serverLevel.sendParticles(ParticleTypes.ELECTRIC_SPARK, this.getX(), this.getY() + 2.0D, this.getZ(),
                    36, 4.0D, 2.5D, 4.0D, 0.08D);
        }
    }

    private void tickLaunchSequence()
    {
        int phase = this.getLaunchPhase();
        if (phase == LAUNCH_IDLE)
        {
            return;
        }
        if (phase == LAUNCH_LOCKED)
        {
            if (this.getControllingPassenger() == null)
            {
                if (this.launchPassengerRestoreGraceTicks > 0)
                {
                    this.launchPassengerRestoreGraceTicks--;
                    this.enforceLaunchLock();
                    return;
                }
                this.resetLaunchSequence();
                return;
            }
            this.launchPassengerRestoreGraceTicks = 0;
            this.enforceLaunchLock();
            // A save made on the exact transition tick can restore with the
            // countdown already at or below 20. Resume instead of remaining
            // permanently mag-locked at the bottom of the shaft.
            if (this.getActivationTicks() <= 20)
            {
                this.beginLaunchAscent();
                return;
            }
            this.entityData.set(DATA_LAUNCH_TICKS, this.getActivationTicks());
            return;
        }
        if (phase == LAUNCH_ASCENT)
        {
            if (this.launchBedPos == null)
            {
                this.resetLaunchSequence();
                return;
            }
            if (this.launchRecoveryPending && !this.recoverMovingCarrier())
            {
                return;
            }
            if (this.getControllingPassenger() == null)
            {
                if (this.launchPassengerRestoreGraceTicks > 0)
                {
                    this.launchPassengerRestoreGraceTicks--;
                    this.setDeltaMovement(Vec3.ZERO);
                    return;
                }
                this.resetLaunchSequence();
                return;
            }
            this.launchPassengerRestoreGraceTicks = 0;
            double targetY = this.launchBedPos.getY() + LAUNCH_TARGET_ABOVE_BED;
            int remainingTicks = Math.max(0, this.getLaunchTicks() - 1);
            float progress = Mth.clamp((LAUNCH_ASCENT_TICKS - remainingTicks)
                    / (float) LAUNCH_ASCENT_TICKS, 0.0F, 1.0F);
            float easedProgress = progress * progress * (3.0F - 2.0F * progress);
            double startY = this.launchBedPos.getY() + 1.0D;
            double nextY = Mth.lerp(easedProgress, startY, targetY);
            this.setPos(this.launchBedPos.getX() + 0.5D, nextY,
                    this.launchBedPos.getZ() + 0.5D);
            this.setDeltaMovement(Vec3.ZERO);
            this.setRot(this.launchLockedYaw, 0.0F);
            this.yRotO = this.yBodyRot = this.yHeadRot = this.launchLockedYaw;
            this.fallDistance = 0.0F;
            this.hasImpulse = true;
            for (Entity passenger : this.getPassengers())
            {
                this.positionRider(passenger, Entity::setPos);
            }
            this.updateMovingCarrier();
            this.entityData.set(DATA_LAUNCH_TICKS, remainingTicks);
            if (remainingTicks <= 0)
            {
                this.clearMovingCarrierBelowSurface();
                this.launchCarrierY = this.launchBedPos.getY()
                        + (int) LAUNCH_TARGET_ABOVE_BED - 1;
                this.setPos(this.launchBedPos.getX() + 0.5D, targetY, this.launchBedPos.getZ() + 0.5D);
                for (Entity passenger : this.getPassengers())
                {
                    this.positionRider(passenger, Entity::setPos);
                }
                // Close only after the complete EVA/passenger assembly has
                // cleared the deck plane; otherwise a timeout could build
                // 121 solid blocks through a still-rising body.
                this.setSurfaceCarrier(true);
                this.setDeltaMovement(0.0D, 0.12D, 0.0D);
                this.setNoGravity(false);
                this.entityData.set(DATA_LAUNCH_PHASE, LAUNCH_CLEAR);
                this.entityData.set(DATA_LAUNCH_TICKS, LAUNCH_CLEAR_TICKS);
                ProjectSeele.LOGGER.info("NERV launch surface clear: eva={} y={}",
                        this.getStringUUID(), targetY);
                if (this.getControllingPassenger() instanceof ServerPlayer pilot)
                {
                    pilot.displayClientMessage(Component.translatable(
                            "message.projectseele.launch_surface_clear"), true);
                }
                this.playSound(SoundEvents.PISTON_CONTRACT, 2.8F, 0.72F);
                if (this.level() instanceof ServerLevel serverLevel)
                {
                    serverLevel.sendParticles(ParticleTypes.CLOUD, this.getX(), this.getY(), this.getZ(),
                            54, 5.0D, 0.4D, 5.0D, 0.09D);
                }
                return;
            }
            return;
        }
        int remainingTicks = this.getLaunchTicks() - 1;
        if (remainingTicks <= 0)
        {
            this.resetLaunchSequence();
        }
        else
        {
            this.entityData.set(DATA_LAUNCH_TICKS, remainingTicks);
            this.fallDistance = 0.0F;
        }
    }

    /** Move the visible 11x11 mag-lev carrier directly below the EVA's feet. */
    private void updateMovingCarrier()
    {
        if (this.launchBedPos == null || !(this.level() instanceof ServerLevel))
        {
            return;
        }
        int bedY = this.launchBedPos.getY();
        int deckY = bedY + (int) LAUNCH_TARGET_ABOVE_BED - 1;
        int desiredY = Mth.clamp(Mth.floor(this.getY()) - 1, bedY, deckY);
        if (desiredY == this.launchCarrierY)
        {
            return;
        }
        if (this.launchCarrierY > bedY && this.launchCarrierY < deckY)
        {
            this.setMovingCarrierLayer(this.launchCarrierY, false);
        }
        if (desiredY > bedY && desiredY < deckY)
        {
            this.setMovingCarrierLayer(desiredY, true);
        }
        this.launchCarrierY = desiredY;
        int travelled = desiredY - bedY;
        if (travelled == 1 || travelled == 16 || desiredY == deckY - 1)
        {
            ProjectSeele.LOGGER.info("NERV carrier progress: eva={} carrierY={} travelled={}/31",
                    this.getStringUUID(), desiredY, travelled);
        }
    }

    private void clearMovingCarrierBelowSurface()
    {
        if (this.launchBedPos == null)
        {
            return;
        }
        int bedY = this.launchBedPos.getY();
        int deckY = bedY + (int) LAUNCH_TARGET_ABOVE_BED - 1;
        if (this.launchCarrierY > bedY && this.launchCarrierY < deckY)
        {
            this.setMovingCarrierLayer(this.launchCarrierY, false);
        }
    }

    private boolean recoverMovingCarrier()
    {
        this.launchRecoveryPending = false;
        if (this.launchBedPos == null
                || !this.level().getBlockState(this.launchBedPos).is(Blocks.LODESTONE))
        {
            this.resetLaunchSequence();
            return false;
        }
        int bedY = this.launchBedPos.getY();
        int deckY = bedY + (int) LAUNCH_TARGET_ABOVE_BED - 1;
        int inferredY = Mth.clamp(Mth.floor(this.getY()) - 1, bedY, deckY);
        int savedY = this.launchCarrierY;
        // Entity and chunk saves are not atomic, so either the stored layer or
        // the layer immediately around the restored feet may survive. Only an
        // exact 11x11 carrier signature is eligible for removal; never sweep
        // an entire shaft merely because player blocks share its materials.
        for (int candidateY : new int[] {
                savedY, savedY - 1, savedY + 1,
                inferredY, inferredY - 1, inferredY + 1})
        {
            if (candidateY > bedY && candidateY < deckY
                    && this.hasMovingCarrierSignature(candidateY))
            {
                this.setMovingCarrierLayer(candidateY, false);
            }
        }
        this.launchCarrierY = NO_LAUNCH_CARRIER;
        this.updateMovingCarrier();
        ProjectSeele.LOGGER.info("NERV carrier recovered: eva={} bed={} carrierY={}",
                this.getStringUUID(), this.launchBedPos.toShortString(), this.launchCarrierY);
        return true;
    }

    private boolean hasMovingCarrierSignature(int y)
    {
        if (this.launchBedPos == null || !(this.level() instanceof ServerLevel serverLevel))
        {
            return false;
        }
        for (int x = -5; x <= 5; x++)
        {
            for (int z = -5; z <= 5; z++)
            {
                BlockPos block = new BlockPos(this.launchBedPos.getX() + x, y,
                        this.launchBedPos.getZ() + z);
                boolean rim = Math.abs(x) == 5 || Math.abs(z) == 5;
                if (rim ? !serverLevel.getBlockState(block).is(Blocks.IRON_BLOCK)
                        : !serverLevel.getBlockState(block).is(Blocks.LIGHT_GRAY_CONCRETE))
                {
                    return false;
                }
            }
        }
        return true;
    }

    private void setMovingCarrierLayer(int y, boolean present)
    {
        if (this.launchBedPos == null || !(this.level() instanceof ServerLevel serverLevel))
        {
            return;
        }
        for (int x = -5; x <= 5; x++)
        {
            for (int z = -5; z <= 5; z++)
            {
                BlockPos block = new BlockPos(this.launchBedPos.getX() + x, y,
                        this.launchBedPos.getZ() + z);
                boolean rim = Math.abs(x) == 5 || Math.abs(z) == 5;
                if (present)
                {
                    var desired = rim ? Blocks.IRON_BLOCK.defaultBlockState()
                            : Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState();
                    if (!serverLevel.getBlockState(block).equals(desired))
                    {
                        serverLevel.setBlock(block, desired, 2);
                    }
                }
                else if (serverLevel.getBlockState(block).is(Blocks.IRON_BLOCK)
                        || serverLevel.getBlockState(block).is(Blocks.LIGHT_GRAY_CONCRETE))
                {
                    serverLevel.setBlock(block, Blocks.AIR.defaultBlockState(), 2);
                }
            }
        }
    }

    /** Opens/closes the split surface carrier without touching unrelated player blocks. */
    private void setSurfaceCarrier(boolean closed)
    {
        if (this.launchBedPos == null || !(this.level() instanceof ServerLevel serverLevel))
        {
            return;
        }
        int deckY = this.launchBedPos.getY() + (int) LAUNCH_TARGET_ABOVE_BED - 1;
        for (int x = -5; x <= 5; x++)
        {
            for (int z = -5; z <= 5; z++)
            {
                BlockPos deck = new BlockPos(this.launchBedPos.getX() + x, deckY,
                        this.launchBedPos.getZ() + z);
                if (closed)
                {
                    var desired = (Math.abs(x) == 5 || Math.abs(z) == 5)
                            ? Blocks.IRON_BLOCK.defaultBlockState()
                            : Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState();
                    if (!serverLevel.getBlockState(deck).equals(desired))
                    {
                        serverLevel.setBlock(deck, desired, 2);
                    }
                }
                else if (serverLevel.getBlockState(deck).is(Blocks.IRON_BLOCK)
                        || serverLevel.getBlockState(deck).is(Blocks.LIGHT_GRAY_CONCRETE))
                {
                    serverLevel.setBlock(deck, Blocks.AIR.defaultBlockState(), 2);
                }
            }
        }
    }

    private void resetLaunchSequence()
    {
        boolean abandoned = this.getControllingPassenger() == null;
        if (this.getLaunchPhase() == LAUNCH_ASCENT)
        {
            this.clearMovingCarrierBelowSurface();
            if (this.launchBedPos != null)
            {
                this.setPos(this.launchBedPos.getX() + 0.5D, this.launchBedPos.getY() + 1.0D,
                        this.launchBedPos.getZ() + 0.5D);
                for (Entity passenger : this.getPassengers())
                {
                    this.positionRider(passenger, Entity::setPos);
                }
                this.setSurfaceCarrier(true);
            }
        }
        this.entityData.set(DATA_LAUNCH_PHASE, LAUNCH_IDLE);
        this.entityData.set(DATA_LAUNCH_TICKS, 0);
        this.launchBedPos = null;
        this.launchCarrierY = NO_LAUNCH_CARRIER;
        this.launchRecoveryPending = false;
        this.launchPassengerRestoreGraceTicks = 0;
        this.launchLockedYaw = this.getYRot();
        if (abandoned)
        {
            // A timed-out passenger restore is a real aborted insertion. Do
            // not leave the seated plug or activation overlay latched forever.
            this.entityData.set(DATA_ACTIVATION_TICKS, 0);
            this.entityData.set(DATA_ENTRY_PLUG_INSERTED, false);
        }
        if (!this.isCrucified())
        {
            this.setNoGravity(false);
        }
    }

    @Override
    public void die(DamageSource source)
    {
        // /kill or lethal combat during ascent must not strand a carrier
        // layer inside the shaft or leave the surface aperture open.
        if (this.isLaunchSequenceActive())
        {
            this.resetLaunchSequence();
        }
        super.die(source);
    }

    @Override
    public void remove(RemovalReason reason)
    {
        if (reason == RemovalReason.DISCARDED && this.isLaunchSequenceActive())
        {
            this.resetLaunchSequence();
        }
        super.remove(reason);
    }

    /**
     * The EVA A.T. Field: while raised it nullifies ordinary damage outright;
     * Angel attacks tear chunks out of the field energy instead, spilling
     * into hull damage only once the pool runs dry.
     */
    @Override
    public boolean hurt(DamageSource source, float amount)
    {
        if (source.is(DamageTypeTags.BYPASSES_INVULNERABILITY))
        {
            return super.hurt(source, amount);
        }
        if (AtFieldRules.bypassesAtField(source))
        {
            return super.hurt(source, amount);
        }
        if (this.isAtFieldOn() && amount > 0.0F)
        {
            this.atRegenDelay = AT_FIELD_REGEN_DELAY;
            boolean evaMelee = source.getEntity() instanceof EvaUnit01Entity attacker
                    && attacker.isMeleeWeapon() && !source.is(DamageTypeTags.IS_EXPLOSION);
            if (source.getEntity() instanceof Angel || evaMelee)
            {
                float energy = this.getAtFieldEnergy();
                // Unit-00 can physically interpose itself in Ramiel's ray.
                // Kneeling behind the shield doubles its already superior
                // field efficiency, making the Yashima cover role practical.
                float costMultiplier = this.getUnitVariant() == UNIT_00
                        ? (this.isShieldBraced() ? 0.30F : 0.60F) : 1.0F;
                float fieldCost = amount * costMultiplier;
                float absorbed = Math.min(energy, fieldCost);
                this.entityData.set(DATA_AT_ENERGY, energy - absorbed);
                this.rippleAt(source);
                float leftover = (fieldCost - absorbed) / costMultiplier;
                return leftover > 0.0F && super.hurt(source, leftover);
            }
            // Conventional weapons cannot even scratch the field.
            this.rippleAt(source);
            return false;
        }
        return super.hurt(source, amount);
    }

    private void rippleAt(DamageSource source)
    {
        if (!(this.level() instanceof ServerLevel serverLevel))
        {
            return;
        }
        Vec3 origin = source.getSourcePosition();
        Vec3 center = this.position().add(0.0D, this.getBbHeight() * 0.55D, 0.0D);
        Vec3 dir = origin != null && origin.distanceToSqr(center) > 1.0E-4D
                ? origin.subtract(center).normalize()
                : this.getForward();
        AtFieldFX.ripple(serverLevel, center.add(dir.scale(8.0D)), dir);
    }

    // ----- piloting -----

    @Override
    public InteractionResult mobInteract(Player player, InteractionHand hand)
    {
        if (!this.isVehicle() && !player.isSecondaryUseActive())
        {
            return this.level().isClientSide
                    ? InteractionResult.SUCCESS : this.tryEnterFromPlug(player, false);
        }
        return super.mobInteract(player, hand);
    }

    /**
     * Server-authoritative boarding entry used by the extended plug ray.
     * Vanilla entity interaction has already performed a hit test and calls
     * the overload that skips only the redundant narrow aim-cone check.
     */
    public InteractionResult tryEnterFromPlug(Player player)
    {
        return this.tryEnterFromPlug(player, true);
    }

    /** Command helpers may skip only the look cone after placing the pilot on an audited gantry. */
    public InteractionResult tryEnterFromPlug(Player player, boolean requireAim)
    {
        if (this.level().isClientSide)
        {
            return InteractionResult.SUCCESS;
        }
        if (this.isVehicle() || player.isPassenger())
        {
            return InteractionResult.FAIL;
        }
        if (this.isLaunchSequenceActive())
        {
            player.displayClientMessage(
                    Component.translatable("message.projectseele.launch_interlock"), true);
            return InteractionResult.CONSUME;
        }

        BlockPos launchBed = this.findLaunchBed();
        if (launchBed != null)
        {
            if (this.launchBedClaimedByAnother(launchBed))
            {
                player.displayClientMessage(
                        Component.translatable("message.projectseele.launch_bed_occupied"), true);
                return InteractionResult.CONSUME;
            }
        }

        // Everything below through line-of-sight is evaluated against the
        // transform the player can currently see. A rejected interaction must
        // never snap or rotate an EVA as a side effect.
        double relativeHeight = player.getY() - this.getY();
        Vec3 horizontal = new Vec3(player.getX() - this.getX(), 0.0D,
                player.getZ() - this.getZ());
        double distance = horizontal.length();
        Vec3 rear = this.getForward().multiply(-1.0D, 0.0D, -1.0D).normalize();
        double rearDot = distance > 1.0E-4D
                ? horizontal.scale(1.0D / distance).dot(rear) : -1.0D;
        if (relativeHeight < SILO_ENTRY_MIN_HEIGHT || relativeHeight > SILO_ENTRY_MAX_HEIGHT
                || distance < SILO_ENTRY_MIN_DISTANCE || distance > SILO_ENTRY_MAX_DISTANCE
                || rearDot < SILO_ENTRY_MIN_REAR_DOT)
        {
            player.displayClientMessage(
                    Component.translatable("message.projectseele.use_entry_gantry"), true);
            return InteractionResult.CONSUME;
        }
        if ((requireAim && !this.isEntryPlugTargeted(player)) || !this.hasClearEntryPlugPath(player))
        {
            player.displayClientMessage(
                    Component.translatable("message.projectseele.aim_entry_plug"), true);
            return InteractionResult.CONSUME;
        }

        if (launchBed != null)
        {
            // Authorization succeeded. Only now may the launch fixture pull a
            // slightly displaced caged airframe onto its audited bed/yaw.
            this.alignForSiloBoarding(launchBed);
        }
        this.entityData.set(DATA_ACTIVATION_TICKS, 120);
        this.entityData.set(DATA_ENTRY_PLUG_INSERTED, true);
        if (!player.startRiding(this, true))
        {
            this.entityData.set(DATA_ACTIVATION_TICKS, 0);
            this.entityData.set(DATA_ENTRY_PLUG_INSERTED, false);
            return InteractionResult.FAIL;
        }
        if (launchBed != null)
        {
            this.armLaunchBed(launchBed);
            player.displayClientMessage(Component.translatable("message.projectseele.launch_locked"), true);
        }
        return InteractionResult.CONSUME;
    }

    private void alignForSiloBoarding(BlockPos bed)
    {
        this.setPos(bed.getX() + 0.5D, bed.getY() + 1.0D, bed.getZ() + 0.5D);
        this.setDeltaMovement(Vec3.ZERO);
        this.setRot(SILO_BAY_YAW, 0.0F);
        this.yRotO = this.yBodyRot = this.yHeadRot = SILO_BAY_YAW;
        this.fallDistance = 0.0F;
    }

    private boolean hasClearEntryPlugPath(Player player)
    {
        Vec3 eye = player.getEyePosition();
        Vec3 socket = this.getEntryPlugSocketPosition();
        BlockHitResult hit = this.level().clip(new ClipContext(
                eye, socket, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, player));
        return hit.getType() == net.minecraft.world.phys.HitResult.Type.MISS
                || hit.getLocation().distanceToSqr(socket) <= 0.75D * 0.75D;
    }

    @Nullable
    @Override
    public LivingEntity getControllingPassenger()
    {
        return this.getFirstPassenger() instanceof Player player ? player : super.getControllingPassenger();
    }

    @Override
    protected void tickRidden(Player player, Vec3 input)
    {
        if (!this.level().isClientSide)
        {
            float aimPitch = !this.isCrucified()
                    && !this.isPilotControlLocked()
                    && (this.getWeapon() == WEAPON_CANNON || this.getWeapon() == WEAPON_RIFLE)
                    ? Mth.clamp(player.getXRot(), MIN_CANNON_AIM_PITCH, MAX_CANNON_AIM_PITCH)
                    : 0.0F;
            if (Math.abs(this.getCannonAimPitch() - aimPitch) > 0.01F)
            {
                this.entityData.set(DATA_CANNON_AIM_PITCH, aimPitch);
            }
        }
        if (this.isCrucified() || this.isPilotControlLocked())
        {
            // Activation interlocks, launch rails and ritual restraints all
            // own the chassis transform. Pilot view input must not rotate it.
            this.setDeltaMovement(Vec3.ZERO);
            return;
        }
        super.tickRidden(player, input);
        // Yaw steers the chassis; camera pitch remains pilot-only input. Cannon
        // elevation is synchronized separately and applied to the one world
        // skeleton, so the entire EVA never pitches with the camera.
        this.setRot(player.getYRot(), 0.0F);
        this.yRotO = this.yBodyRot = this.yHeadRot = this.getYRot();
        // The player renderer is cancelled client-side while mounted. Do not
        // leave the pilot invisibility flag set after an older cockpit pass.
        if (player.isInvisible())
        {
            player.setInvisible(false);
        }
    }

    @Override
    protected void removePassenger(Entity passenger)
    {
        super.removePassenger(passenger);
        this.chargingHeld = false;
        this.entityData.set(DATA_CANNON_CHARGE, 0);
        this.entityData.set(DATA_N2_ARM_TICKS, 0);
        this.entityData.set(DATA_CANNON_AIM_PITCH, 0.0F);
        this.entityData.set(DATA_ACTIVATION_TICKS, 0);
        this.entityData.set(DATA_ENTRY_PLUG_INSERTED, false);
        if (this.isLaunchSequenceActive())
        {
            this.resetLaunchSequence();
        }
        this.clearPilotMotion();
    }

    private void setPilotMovementState(boolean crouching, boolean sprinting)
    {
        this.entityData.set(DATA_CROUCHING, crouching);
        this.entityData.set(DATA_SPRINTING, sprinting);
        this.entityData.set(DATA_PRONE, false);
        this.updatePoseDimensions();
    }

    /** Stop input-driven motion without making a prone Unit pop upright. */
    private void clearPilotMotion()
    {
        this.entityData.set(DATA_CROUCHING, false);
        this.entityData.set(DATA_SPRINTING, false);
        this.updatePoseDimensions();
    }

    private void updatePoseDimensions()
    {
        boolean crouching = this.isPilotCrouching();
        boolean prone = this.isPilotProne();
        if (this.crouchingDimensions != crouching || this.proneDimensions != prone)
        {
            this.crouchingDimensions = crouching;
            this.proneDimensions = prone;
            this.refreshDimensions();
        }
    }

    @Override
    public boolean isImmobile()
    {
        return super.isImmobile() || this.isCrucified() || this.isPilotControlLocked();
    }

    @Override
    public boolean isPushable()
    {
        return !this.isCrucified() && !this.isPilotControlLocked() && super.isPushable();
    }

    @Override
    public void travel(Vec3 input)
    {
        if (this.isCrucified() || this.isPilotControlLocked())
        {
            this.setDeltaMovement(Vec3.ZERO);
            return;
        }
        super.travel(input);
        // LivingEntity calls this only after it has selected the local pilot
        // as vehicle authority. Applying the synchronized impulse here avoids
        // both the pre-travel friction pass and the non-authoritative branch
        // that zeros remote ridden entities.
        if (this.level().isClientSide && this.clientJumpImpulsePending)
        {
            Vec3 motion = this.getDeltaMovement();
            this.setDeltaMovement(motion.x, JUMP_VELOCITY, motion.z);
            this.hasImpulse = true;
            this.clientJumpImpulsePending = false;
            if (this.getVisualPose() == VISUAL_LIVE_JUMP)
            {
                ProjectSeele.LOGGER.info(
                        "Visual live jump client travel impulse applied velocityY={} localAuthority={}",
                        this.getDeltaMovement().y, this.isControlledByLocalInstance());
            }
        }
    }

    @Override
    protected Vec3 getRiddenInput(Player player, Vec3 input)
    {
        if (this.getActivationTicks() > 20 || this.isLaunchSequenceActive())
        {
            return Vec3.ZERO;
        }
        double strafe = this.isPilotProne() ? 0.28D : this.isPilotCrouching() ? 0.45D : 0.7D;
        return new Vec3(player.xxa * strafe, 0.0D, player.zza >= 0.0F ? player.zza : player.zza * 0.6D);
    }

    @Override
    protected float getRiddenSpeed(Player player)
    {
        if (this.getActivationTicks() > 20 || this.isLaunchSequenceActive())
        {
            return 0.0F;
        }
        // Sniper stance: charging the cannon roots the Unit.
        if (this.getCannonCharge() > 0 || this.getN2ArmTicks() > 0)
        {
            return 0.02F;
        }
        if (this.isPilotCrouching())
        {
            return CROUCH_SPEED;
        }
        if (this.isPilotProne())
        {
            return PRONE_SPEED;
        }
        float variantSpeed = switch (this.getUnitVariant())
        {
            case UNIT_00 -> this.isPilotSprinting() ? 0.52F : 0.36F;
            case UNIT_02 -> this.isPilotSprinting() ? 0.72F : 0.48F;
            default -> this.isPilotSprinting() ? SPRINT_SPEED : WALK_SPEED;
        };
        return variantSpeed;
    }

    @Override
    public EntityDimensions getDimensions(Pose pose)
    {
        EntityDimensions dimensions = super.getDimensions(pose);
        if (this.proneDimensions)
        {
            return EntityDimensions.scalable(PRONE_WIDTH, PRONE_HEIGHT);
        }
        return this.crouchingDimensions ? EntityDimensions.scalable(NORMAL_WIDTH, CROUCH_HEIGHT) : dimensions;
    }

    @Override
    public void onSyncedDataUpdated(EntityDataAccessor<?> key)
    {
        super.onSyncedDataUpdated(key);
        if (DATA_CROUCHING.equals(key) || DATA_PRONE.equals(key))
        {
            this.updatePoseDimensions();
        }
        if (DATA_MELEE_SEQUENCE.equals(key))
        {
            int sequence = this.entityData.get(DATA_MELEE_SEQUENCE);
            if (sequence != this.clientMeleeSequence)
            {
                this.clientMeleeSequence = sequence;
                this.clientMeleeLeft = this.entityData.get(DATA_MELEE_LEFT);
                this.clientMeleeStartTick = this.tickCount;
            }
        }
        if (DATA_SMASH_SEQUENCE.equals(key))
        {
            int sequence = this.entityData.get(DATA_SMASH_SEQUENCE);
            if (sequence != this.clientSmashSequence)
            {
                this.clientSmashSequence = sequence;
                this.clientSmashStartTick = this.tickCount;
            }
        }
        if (DATA_JUMP_SEQUENCE.equals(key) && this.level().isClientSide)
        {
            int sequence = this.entityData.get(DATA_JUMP_SEQUENCE);
            if (sequence != this.clientJumpSequence)
            {
                this.clientJumpSequence = sequence;
                this.clientJumpImpulsePending = true;
                if (this.getVisualPose() == VISUAL_LIVE_JUMP)
                {
                    ProjectSeele.LOGGER.info("Visual live jump client sequence received sequence={}",
                            sequence);
                }
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
        // The pilot rides at the animated rig's head socket. First person sees
        // the same world entity and the same evaluated bones as third person.
        float rad = (float) Math.toRadians(this.yBodyRot);
        // All three reviewed Tiger bodies share the same 192-pixel height and
        // semantic rig contract. Keep one eye-socket calculation so Unit-00
        // and Unit-02 cannot fall back to the former SmOd seat coordinates.
        boolean proneView = this.isPilotProne() || this.getVisualPose() == VISUAL_PRONE
                || this.getVisualPose() == VISUAL_CRAWL
                || this.getVisualPose() == VISUAL_PRONE_CANNON
                || this.getVisualPose() == VISUAL_PRONE_KNIFE_CONTACT
                || this.getVisualPose() == VISUAL_PRONE_LANCE_CONTACT
                || this.getVisualPose() == VISUAL_PRONE_RIFLE;
        boolean crouchView = this.isPilotCrouching() || this.getVisualPose() == VISUAL_CROUCH
                || this.getVisualPose() == VISUAL_CROUCH_WALK
                || this.getVisualPose() == VISUAL_CROUCH_KNIFE_CONTACT
                || this.getVisualPose() == VISUAL_CROUCH_LANCE_CONTACT
                || this.getVisualPose() == VISUAL_CROUCH_RIFLE_CONTACT;
        // These coordinates place the camera on the visible face plane rather
        // than at the neck pivot inside the chest shell. Tiger/SmOd's local
        // -Z face direction is entity-forward after rendering, so every stance
        // uses the same positive forward socket convention. Express Y as the
        // desired eye position because Camera adds the player's own eye height
        // after positionRider.
        double targetEyeHeight = proneView ? 7.00D : crouchView ? 19.70D : 24.63D;
        double forward = proneView ? 12.00D : crouchView ? 0.80D : 1.00D;
        // A right-shouldered rifle puts its receiver immediately beside the
        // EVA's face. Offset the optical eye toward the left eye by less than
        // one block so the stock sits at the screen edge like a human sight
        // picture instead of covering half the display. This moves only the
        // rider socket; weapon and arms remain the shared world skeleton.
        double lateral = this.getWeapon() == WEAPON_RIFLE ? 0.90D : 0.0D;
        double seatHeight = targetEyeHeight - passenger.getEyeHeight();
        move.accept(passenger,
                this.getX() - Math.sin(rad) * forward + Math.cos(rad) * lateral,
                this.getY() + seatHeight,
                this.getZ() + Math.cos(rad) * forward + Math.sin(rad) * lateral);
    }

    @Override
    public Vec3 getDismountLocationForPassenger(LivingEntity passenger)
    {
        // Step out at the Unit's feet instead of dropping from plug height.
        float rad = (float) Math.toRadians(this.yBodyRot);
        return new Vec3(this.getX() + Math.sin(rad) * 5.5D, this.getY(), this.getZ() - Math.cos(rad) * 5.5D);
    }

    // ----- durability -----

    @Override
    public boolean causeFallDamage(float distance, float multiplier, DamageSource source)
    {
        // A 40-metre war machine does not stub its toe.
        return distance > 18.0F && super.causeFallDamage(distance - 18.0F, multiplier * 0.5F, source);
    }

    @Override
    public boolean fireImmune()
    {
        return true;
    }

    @Override
    public boolean removeWhenFarAway(double distance)
    {
        return false;
    }

    @Override
    protected SoundEvent getHurtSound(DamageSource source)
    {
        return SoundEvents.IRON_GOLEM_DAMAGE;
    }

    @Override
    protected SoundEvent getDeathSound()
    {
        return SoundEvents.IRON_GOLEM_DEATH;
    }

    @Override
    protected float getSoundVolume()
    {
        return 2.5F;
    }

    // ----- GeckoLib -----

    private double locomotionAnimationSpeed()
    {
        if (this.getVisualPose() != VISUAL_NORMAL || this.getActivationTicks() > 0
                || this.isCrucified() || !this.onGround())
        {
            return 1.0D;
        }
        Vec3 motion = this.getDeltaMovement();
        double blocksPerSecond = Math.sqrt(
                motion.x * motion.x + motion.z * motion.z) * 20.0D;
        if (blocksPerSecond < 0.05D)
        {
            return 1.0D;
        }
        double speed;
        if (this.isPilotProne())
        {
            speed = blocksPerSecond * CRAWL_CYCLE_SECONDS / CRAWL_STRIDE_BLOCKS;
        }
        else if (this.isPilotCrouching())
        {
            speed = blocksPerSecond * CROUCH_CYCLE_SECONDS / CROUCH_STRIDE_BLOCKS;
        }
        else if (this.isPilotSprinting())
        {
            speed = blocksPerSecond * RUN_CYCLE_SECONDS / RUN_STRIDE_BLOCKS
                    * RUN_CADENCE_GAIN;
        }
        else
        {
            speed = blocksPerSecond * WALK_CYCLE_SECONDS / WALK_STRIDE_BLOCKS
                    * WALK_CADENCE_GAIN;
        }
        return Mth.clamp(speed, 0.18D, 1.6D);
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers)
    {
        controllers.add(new AnimationController<>(this, "base", 6, state ->
        {
            if (this.isCrucified())
            {
                return state.setAndContinue(ANIM_CRUCIFIED);
            }
            switch (this.getVisualPose())
            {
                case VISUAL_IDLE -> { return state.setAndContinue(ANIM_VISUAL_IDLE); }
                case VISUAL_WALK_CONTACT -> { return state.setAndContinue(ANIM_VISUAL_WALK); }
                case VISUAL_RUN_CONTACT -> { return state.setAndContinue(ANIM_VISUAL_RUN); }
                case VISUAL_JUMP -> { return state.setAndContinue(ANIM_VISUAL_JUMP); }
                case VISUAL_FALL -> { return state.setAndContinue(ANIM_VISUAL_FALL); }
                case VISUAL_CROUCH_WALK -> { return state.setAndContinue(ANIM_VISUAL_CROUCH_WALK); }
                case VISUAL_CRAWL -> { return state.setAndContinue(ANIM_VISUAL_CRAWL); }
                case VISUAL_KNIFE_READY -> { return state.setAndContinue(ANIM_VISUAL_KNIFE_READY); }
                case VISUAL_LANCE_READY -> { return state.setAndContinue(ANIM_VISUAL_LANCE_READY); }
                case VISUAL_KNIFE_WINDUP -> { return state.setAndContinue(ANIM_VISUAL_KNIFE_WINDUP); }
                case VISUAL_KNIFE_CONTACT -> { return state.setAndContinue(ANIM_VISUAL_KNIFE_CONTACT); }
                case VISUAL_KNIFE_RECOVERY -> { return state.setAndContinue(ANIM_VISUAL_KNIFE_RECOVERY); }
                case VISUAL_CROUCH -> { return state.setAndContinue(ANIM_CROUCH); }
                case VISUAL_PRONE -> { return state.setAndContinue(ANIM_PRONE); }
                case VISUAL_LANCE_WINDUP -> { return state.setAndContinue(ANIM_VISUAL_LANCE_WINDUP); }
                case VISUAL_LANCE_CONTACT -> { return state.setAndContinue(ANIM_VISUAL_LANCE_CONTACT); }
                case VISUAL_LANCE_RECOVERY -> { return state.setAndContinue(ANIM_VISUAL_LANCE_RECOVERY); }
                case VISUAL_CANNON -> { return state.setAndContinue(ANIM_VISUAL_CANNON); }
                case VISUAL_PRONE_CANNON -> { return state.setAndContinue(ANIM_PRONE); }
                case VISUAL_RIFLE -> { return state.setAndContinue(ANIM_VISUAL_RIFLE); }
                case VISUAL_CROUCH_KNIFE_CONTACT -> { return state.setAndContinue(ANIM_VISUAL_CROUCH_KNIFE_CONTACT); }
                case VISUAL_PRONE_KNIFE_CONTACT -> { return state.setAndContinue(ANIM_VISUAL_PRONE_KNIFE_CONTACT); }
                case VISUAL_CROUCH_LANCE_CONTACT -> { return state.setAndContinue(ANIM_VISUAL_CROUCH_LANCE_CONTACT); }
                case VISUAL_PRONE_LANCE_CONTACT -> { return state.setAndContinue(ANIM_VISUAL_PRONE_LANCE_CONTACT); }
                case VISUAL_N2_READY -> { return state.setAndContinue(ANIM_VISUAL_N2_READY); }
                case VISUAL_RIFLE_WALK_CONTACT -> { return state.setAndContinue(ANIM_VISUAL_RIFLE_WALK_CONTACT); }
                case VISUAL_CROUCH_RIFLE_CONTACT -> { return state.setAndContinue(ANIM_VISUAL_CROUCH_RIFLE_CONTACT); }
                case VISUAL_PRONE_RIFLE -> { return state.setAndContinue(ANIM_VISUAL_PRONE_RIFLE); }
                case VISUAL_LIVE_MELEE -> { return state.setAndContinue(ANIM_VISUAL_IDLE); }
                case VISUAL_LIVE_KNIFE -> { return state.setAndContinue(ANIM_VISUAL_KNIFE_READY); }
                case VISUAL_LIVE_LANCE -> { return state.setAndContinue(ANIM_VISUAL_LANCE_READY); }
                case VISUAL_LIVE_RIFLE -> { return state.setAndContinue(ANIM_VISUAL_RIFLE); }
                case VISUAL_LIVE_KNIFE_HEAVY -> { return state.setAndContinue(ANIM_VISUAL_KNIFE_READY); }
                case VISUAL_LIVE_JUMP -> { return state.setAndContinue(ANIM_JUMP); }
                default -> { }
            }
            if (this.getActivationTicks() > 0)
            {
                return state.setAndContinue(ANIM_ACTIVATION);
            }
            // Stance changes resize the hitbox and can leave the Unit one
            // frame off the ground. Keep the requested pose authoritative so
            // PRONE never flashes back to an upright jump/fall animation.
            if (this.isPilotProne())
            {
                return state.setAndContinue(state.isMoving() ? ANIM_CRAWL : ANIM_PRONE);
            }
            if (this.isPilotCrouching())
            {
                return state.setAndContinue(state.isMoving() ? ANIM_CROUCH_WALK : ANIM_CROUCH);
            }
            if (!this.onGround())
            {
                return state.setAndContinue(this.getDeltaMovement().y > 0.02D ? ANIM_JUMP : ANIM_FALL);
            }
            if (state.isMoving())
            {
                return state.setAndContinue(this.isPilotSprinting() ? ANIM_RUN : ANIM_WALK);
            }
            return state.setAndContinue(ANIM_IDLE);
        }).setAnimationSpeedHandler(entity -> entity.locomotionAnimationSpeed()));
        controllers.add(new AnimationController<>(this, "arms", 3, state ->
        {
            if (this.isCrucified())
            {
                return PlayState.STOP;
            }
            if (this.isShieldBraced())
            {
                return state.setAndContinue(ANIM_SHIELD_BRACE);
            }
            if (this.getWeapon() == WEAPON_N2
                    && !this.isPilotProne()
                    && this.getVisualPose() == VISUAL_NORMAL)
            {
                return state.setAndContinue(ANIM_N2_READY);
            }
            if (this.getWeapon() == WEAPON_KNIFE
                    && this.getVisualPose() == VISUAL_NORMAL)
            {
                return state.setAndContinue(this.isPilotProne()
                        ? ANIM_PRONE_KNIFE_READY : ANIM_KNIFE_READY);
            }
            if ((this.getWeapon() == WEAPON_CANNON || this.getWeapon() == WEAPON_RIFLE)
                    && (this.isPilotProne() || this.getVisualPose() == VISUAL_PRONE_CANNON))
            {
                return state.setAndContinue(ANIM_PRONE_AIM);
            }
            if (this.getWeapon() == WEAPON_LANCE
                    && this.getVisualPose() == VISUAL_NORMAL)
            {
                return state.setAndContinue(this.isPilotProne()
                        ? ANIM_PRONE_LANCE_READY : ANIM_LANCE_CARRY);
            }
            if ((this.getWeapon() == WEAPON_CANNON || this.getWeapon() == WEAPON_RIFLE)
                    && !this.isPilotProne()
                    && this.getVisualPose() == VISUAL_NORMAL)
            {
                return state.setAndContinue(this.getWeapon() == WEAPON_RIFLE
                        ? ANIM_RIFLE_AIM : ANIM_AIM);
            }
            return PlayState.STOP;
        }));
        controllers.add(new AnimationController<>(this, "strike", 3, state ->
        {
            if (this.isCrucified())
            {
                state.getController().stop();
                return PlayState.STOP;
            }
            // receiveTriggeredAnimations asks GeckoLib to consult this
            // predicate during a trigger. Returning STOP unconditionally
            // cancelled every melee/knife/lance clip on its first frame.
            return state.getController().isPlayingTriggeredAnimation()
                    ? PlayState.CONTINUE : PlayState.STOP;
        })
                .triggerableAnim("melee", ANIM_MELEE)
                .triggerableAnim("melee_left", ANIM_MELEE_LEFT)
                .triggerableAnim("knife", ANIM_KNIFE)
                .triggerableAnim("knife_left", ANIM_KNIFE_LEFT)
                .triggerableAnim("knife_heavy", ANIM_KNIFE_HEAVY)
                .triggerableAnim("lance_thrust", ANIM_LANCE_THRUST)
                .triggerableAnim("prone_melee", ANIM_PRONE_MELEE)
                .triggerableAnim("prone_melee_left", ANIM_PRONE_MELEE_LEFT)
                .triggerableAnim("prone_knife", ANIM_PRONE_KNIFE)
                .triggerableAnim("prone_knife_heavy", ANIM_PRONE_KNIFE_HEAVY)
                .triggerableAnim("prone_lance_thrust", ANIM_PRONE_LANCE_THRUST)
                .triggerableAnim("prone_smash", ANIM_PRONE_SMASH)
                .triggerableAnim("crouch_melee", ANIM_CROUCH_MELEE)
                .triggerableAnim("crouch_melee_left", ANIM_CROUCH_MELEE_LEFT)
                .triggerableAnim("crouch_knife", ANIM_CROUCH_KNIFE)
                .triggerableAnim("crouch_knife_heavy", ANIM_CROUCH_KNIFE_HEAVY)
                .triggerableAnim("crouch_lance_thrust", ANIM_CROUCH_LANCE_THRUST)
                .triggerableAnim("crouch_smash", ANIM_CROUCH_SMASH)
                .triggerableAnim("smash", ANIM_SMASH)
                .triggerableAnim("cannon_fire", ANIM_CANNON_FIRE)
                .triggerableAnim("prone_cannon_fire", ANIM_PRONE_CANNON_FIRE)
                .triggerableAnim("rifle_fire", ANIM_RIFLE_FIRE)
                .triggerableAnim("prone_rifle_fire", ANIM_PRONE_RIFLE_FIRE)
                .triggerableAnim("takeoff", ANIM_TAKEOFF)
                .triggerableAnim("land", ANIM_LAND)
                .triggerableAnim("stomp", ANIM_STOMP)
                .receiveTriggeredAnimations());
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache()
    {
        return this.geoCache;
    }

    /** Client helper for smooth HUD/FOV: 0..1 charge with partial ticks. */
    public float chargeProgress()
    {
        return Mth.clamp(this.getCannonCharge() / (float) SeeleConfig.CANNON_CHARGE_TICKS.get(), 0.0F, 1.0F);
    }
}
