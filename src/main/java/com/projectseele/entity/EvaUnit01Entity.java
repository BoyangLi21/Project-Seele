package com.projectseele.entity;

import java.util.List;
import java.util.function.Function;

import com.projectseele.ProjectSeele;
import com.projectseele.capability.EvaPilotCapability;
import com.projectseele.capability.EvaPilotData;
import com.projectseele.config.SeeleConfig;
import com.projectseele.combat.AtFieldRules;
import com.projectseele.fx.AtFieldFX;
import com.projectseele.fx.StrategicExplosionDirector;
import com.projectseele.network.ClientboundCannonBeamPacket;
import com.projectseele.network.ClientboundEvaArrivalSyncPacket;
import com.projectseele.network.ClientboundNukeFxPacket;
import com.projectseele.network.ClientboundRifleTracerPacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.registry.ModSounds;
import com.projectseele.registry.ModEntities;
import com.projectseele.world.IntegratedNervMapBuilder;
import com.projectseele.world.UmbilicalPylonBlockEntity;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ClientboundTeleportEntityPacket;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
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
import net.minecraft.world.level.portal.PortalInfo;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.ForgeMod;
import net.minecraftforge.common.util.ITeleporter;
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
    public static final int ARMAMENT_MASK_FISTS = 1 << WEAPON_FISTS;
    private static final int ALL_ARMAMENT_MASK = (1 << (WEAPON_N2 + 1)) - 1;
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
    private static final int JUMP_BUFFER_TICKS = 20;
    private static final int JUMP_COYOTE_TICKS = 5;
    private static final int LAUNCH_ASCENT_TICKS = 34;
    private static final int LAUNCH_CLEAR_TICKS = 18;
    private static final double LAUNCH_TARGET_ABOVE_BED = 32.0D;
    private static final double CONTINUOUS_ASCENT_BLOCKS_PER_TICK = 2.0D;
    private static final int CONTINUOUS_EXIT_HEADROOM = 40;
    // Keep exactly one authoritative surface tick for the locally controlled
    // vehicle. Longer holds are visible as a carrier snag after the EVA has
    // already cleared the street aperture.
    private static final int CONTINUOUS_SURFACE_SYNC_TICKS = 1;
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
    private static final EntityDataAccessor<Integer> DATA_ARMAMENT_MASK =
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
    private static final EntityDataAccessor<Integer> DATA_POWER_TICKS =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> DATA_POWER_CONNECTED =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Integer> DATA_POWER_ANCHOR_X =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_POWER_ANCHOR_Y =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> DATA_POWER_ANCHOR_Z =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Float> DATA_PILOT_SYNCHRONIZATION =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Boolean> DATA_BERSERK =
            SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Integer> DATA_BERSERK_TICKS =
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
    private static final RawAnimation ANIM_BERSERK_ROAR = RawAnimation.begin().thenPlay("animation.eva_unit01.berserk_roar");

    private final AnimatableInstanceCache geoCache = GeckoLibUtil.createInstanceCache(this);

    private boolean chargingHeld;
    private int meleeCooldown;
    private int smashCooldown;
    private int stompCooldown;
    private int rifleCooldown;
    private boolean leftSwing;
    private int atRegenDelay;
    private int jumpCooldown;
    private int jumpBufferTicks;
    private int groundedGraceTicks;
    private int lastJumpRequestId = Integer.MIN_VALUE;
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
    private boolean launchContinuousRoute;
    private boolean launchRecoveryPending;
    private int launchPassengerRestoreGraceTicks;
    private float launchLockedYaw;
    @Nullable
    private ResourceKey<Level> sortieDestinationDimension;
    @Nullable
    private BlockPos sortieDestinationBed;
    @Nullable
    private BlockPos sortieParkingBed;
    private int powerCheckCooldown;
    private int berserkRecoveryTicks;
    private int berserkAttackCooldown;
    private int berserkTargetSearchCooldown;

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
        this.entityData.define(DATA_ARMAMENT_MASK, ARMAMENT_MASK_FISTS);
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
        this.entityData.define(DATA_POWER_TICKS, 6000);
        this.entityData.define(DATA_POWER_CONNECTED, false);
        this.entityData.define(DATA_POWER_ANCHOR_X, 0);
        this.entityData.define(DATA_POWER_ANCHOR_Y, 0);
        this.entityData.define(DATA_POWER_ANCHOR_Z, 0);
        this.entityData.define(DATA_PILOT_SYNCHRONIZATION, 40.0F);
        this.entityData.define(DATA_BERSERK, false);
        this.entityData.define(DATA_BERSERK_TICKS, 0);
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
        this.entityData.set(DATA_POWER_TICKS, this.getPowerCapacityTicks());
        return super.finalizeSpawn(level, difficulty, reason, spawnData, dataTag);
    }

    @Override
    public void addAdditionalSaveData(CompoundTag tag)
    {
        super.addAdditionalSaveData(tag);
        tag.putInt("SeeleWeapon", this.getWeapon());
        tag.putInt("SeeleArmamentMask", this.getArmamentMask());
        tag.putBoolean("SeeleCrucified", this.isCrucified());
        tag.putBoolean("SeeleEntryPlugInserted", this.isEntryPlugInserted());
        tag.putInt("SeelePowerTicks", this.getPowerTicks());
        tag.putFloat("SeelePilotSynchronization", this.getPilotSynchronization());
        tag.putBoolean("SeeleBerserk", this.isBerserk());
        tag.putInt("SeeleBerserkTicks", this.getBerserkTicks());
        tag.putInt("SeeleBerserkRecoveryTicks", this.berserkRecoveryTicks);
        if (this.sortieDestinationDimension != null && this.sortieDestinationBed != null)
        {
            tag.putString("SeeleSortieDimension",
                    this.sortieDestinationDimension.location().toString());
            tag.putLong("SeeleSortieBed", this.sortieDestinationBed.asLong());
            if (this.sortieParkingBed != null)
            {
                tag.putLong("SeeleSortieParkingBed", this.sortieParkingBed.asLong());
            }
        }
        if (this.isLaunchSequenceActive() && this.launchBedPos != null)
        {
            tag.putInt("SeeleLaunchPhase", this.getLaunchPhase());
            tag.putInt("SeeleLaunchTicks", this.getLaunchTicks());
            tag.putInt("SeeleActivationTicks", this.getActivationTicks());
            tag.putLong("SeeleLaunchBed", this.launchBedPos.asLong());
            tag.putFloat("SeeleLaunchYaw", this.launchLockedYaw);
            tag.putBoolean("SeeleLaunchContinuous", this.launchContinuousRoute);
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
        int savedMask = tag.contains("SeeleArmamentMask")
                ? tag.getInt("SeeleArmamentMask") : ARMAMENT_MASK_FISTS;
        savedMask = (savedMask & ALL_ARMAMENT_MASK) | ARMAMENT_MASK_FISTS;
        int savedWeapon = tag.contains("SeeleWeapon")
                ? Mth.clamp(tag.getInt("SeeleWeapon"), WEAPON_FISTS, WEAPON_N2)
                : WEAPON_FISTS;
        if (rackLoadoutEnforced() && (savedMask & (1 << savedWeapon)) == 0)
        {
            savedWeapon = WEAPON_FISTS;
        }
        this.entityData.set(DATA_ARMAMENT_MASK, savedMask);
        this.entityData.set(DATA_WEAPON, savedWeapon);
        boolean crucified = tag.getBoolean("SeeleCrucified");
        this.entityData.set(DATA_CRUCIFIED, crucified);
        this.entityData.set(DATA_ENTRY_PLUG_INSERTED, tag.getBoolean("SeeleEntryPlugInserted"));
        this.entityData.set(DATA_POWER_TICKS, tag.contains("SeelePowerTicks")
                ? Mth.clamp(tag.getInt("SeelePowerTicks"), 0, this.getPowerCapacityTicks())
                : this.getPowerCapacityTicks());
        this.entityData.set(DATA_PILOT_SYNCHRONIZATION,
                tag.contains("SeelePilotSynchronization")
                        ? Mth.clamp(tag.getFloat("SeelePilotSynchronization"), 0.0F,
                                EvaPilotData.maxSynchronization())
                        : EvaPilotData.initialSynchronization());
        boolean savedBerserk = tag.getBoolean("SeeleBerserk")
                && this.getUnitVariant() == UNIT_01;
        this.entityData.set(DATA_BERSERK, savedBerserk);
        this.entityData.set(DATA_BERSERK_TICKS, savedBerserk
                ? Math.max(1, tag.getInt("SeeleBerserkTicks")) : 0);
        this.berserkRecoveryTicks = Math.max(0,
                tag.getInt("SeeleBerserkRecoveryTicks"));
        this.setUmbilicalAnchor(null);
        ResourceLocation sortieLocation = tag.contains("SeeleSortieDimension")
                ? ResourceLocation.tryParse(tag.getString("SeeleSortieDimension")) : null;
        this.sortieDestinationDimension = sortieLocation == null ? null
                : ResourceKey.create(Registries.DIMENSION, sortieLocation);
        this.sortieDestinationBed = this.sortieDestinationDimension != null
                && tag.contains("SeeleSortieBed")
                ? BlockPos.of(tag.getLong("SeeleSortieBed")) : null;
        this.sortieParkingBed = this.sortieDestinationDimension != null
                && tag.contains("SeeleSortieParkingBed")
                ? BlockPos.of(tag.getLong("SeeleSortieParkingBed")) : null;
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
            this.launchContinuousRoute = tag.getBoolean("SeeleLaunchContinuous");
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
            this.launchContinuousRoute = false;
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

    public int getArmamentMask()
    {
        return this.entityData.get(DATA_ARMAMENT_MASK);
    }

    private static boolean rackLoadoutEnforced()
    {
        return SeeleConfig.COMMON_SPEC.isLoaded()
                && SeeleConfig.EVA_ARMAMENT_RACK_ENFORCES_LOADOUT.get();
    }

    private boolean armamentAvailable(int weapon)
    {
        int mask = rackLoadoutEnforced()
                ? this.getArmamentMask() : ALL_ARMAMENT_MASK;
        return weapon >= WEAPON_FISTS && weapon <= WEAPON_N2
                && (mask & (1 << weapon)) != 0;
    }

    private void selectWeapon(int weapon)
    {
        int safeWeapon = Mth.clamp(weapon, WEAPON_FISTS, WEAPON_N2);
        this.entityData.set(DATA_WEAPON, safeWeapon);
        this.entityData.set(DATA_CANNON_CHARGE, 0);
        this.entityData.set(DATA_N2_ARM_TICKS, 0);
        if (safeWeapon != WEAPON_CANNON && safeWeapon != WEAPON_RIFLE)
        {
            this.entityData.set(DATA_CANNON_AIM_PITCH, 0.0F);
        }
        this.chargingHeld = false;
    }

    public boolean canReceiveRackArmament()
    {
        return !this.isPilotControlLocked() && !this.isCrucified()
                && this.getDeltaMovement().horizontalDistanceSqr() < 0.01D;
    }

    public boolean equipRackArmament(int weapon)
    {
        if (!this.canReceiveRackArmament()
                || weapon <= WEAPON_FISTS || weapon > WEAPON_N2)
        {
            return false;
        }
        this.entityData.set(DATA_ARMAMENT_MASK,
                ARMAMENT_MASK_FISTS | (1 << weapon));
        this.selectWeapon(weapon);
        return true;
    }

    public void unloadRackArmament()
    {
        this.entityData.set(DATA_ARMAMENT_MASK, ARMAMENT_MASK_FISTS);
        this.selectWeapon(WEAPON_FISTS);
    }

    public int getPowerTicks()
    {
        return this.entityData.get(DATA_POWER_TICKS);
    }

    public float getPilotSynchronization()
    {
        return this.entityData.get(DATA_PILOT_SYNCHRONIZATION);
    }

    public boolean isBerserk()
    {
        return this.entityData.get(DATA_BERSERK);
    }

    public int getBerserkTicks()
    {
        return this.entityData.get(DATA_BERSERK_TICKS);
    }

    public int getBerserkRecoveryTicks()
    {
        return this.berserkRecoveryTicks;
    }

    public int getPowerCapacityTicks()
    {
        return SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.EVA_POWER_CAPACITY_TICKS.get() : 6000;
    }

    public boolean isUmbilicalConnected()
    {
        return this.entityData.get(DATA_POWER_CONNECTED);
    }

    public boolean isPowerDepleted()
    {
        return !this.isUmbilicalConnected() && this.getPowerTicks() <= 0;
    }

    @Nullable
    public BlockPos getUmbilicalAnchor()
    {
        if (!this.isUmbilicalConnected())
        {
            return null;
        }
        return new BlockPos(this.entityData.get(DATA_POWER_ANCHOR_X),
                this.entityData.get(DATA_POWER_ANCHOR_Y),
                this.entityData.get(DATA_POWER_ANCHOR_Z));
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

    /** Client acknowledgement for one accepted, authoritative jump impulse. */
    public int getJumpSequence()
    {
        return this.entityData.get(DATA_JUMP_SEQUENCE);
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

    /**
     * Releases an occupied, launch-locked EVA from the remote NERV console.
     * All normal passenger, bed and physical-shaft checks still run inside the
     * launch state machine on the following server tick.
     */
    public boolean releaseLaunchFromCommand()
    {
        if (this.level().isClientSide
                || this.getLaunchPhase() != LAUNCH_LOCKED
                || !(this.getControllingPassenger() instanceof ServerPlayer pilot)
                || this.launchBedPos == null)
        {
            return false;
        }
        int releaseTicks = Math.min(20, Math.max(0,
                this.getActivationTicks()));
        this.entityData.set(DATA_ACTIVATION_TICKS, releaseTicks);
        this.entityData.set(DATA_LAUNCH_TICKS, releaseTicks);
        this.enforceLaunchLock();
        pilot.displayClientMessage(Component.literal(
                "NERV command has authorized catapult release."), true);
        ProjectSeele.LOGGER.info(
                "NERV remote launch release: eva={} pilot={} bed={}",
                this.getStringUUID(), pilot.getGameProfile().getName(),
                this.launchBedPos.toShortString());
        return true;
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

    public boolean hasSortieDestination()
    {
        return this.sortieDestinationDimension != null && this.sortieDestinationBed != null;
    }

    @Nullable
    public ResourceKey<Level> getSortieDestinationDimension()
    {
        return this.sortieDestinationDimension;
    }

    @Nullable
    public BlockPos getSortieDestinationBed()
    {
        return this.sortieDestinationBed;
    }

    /** Arms one exact surface shaft for the next completed launch. */
    public void setSortieDestination(ResourceKey<Level> dimension, BlockPos bed)
    {
        this.sortieDestinationDimension = dimension;
        this.sortieDestinationBed = bed.immutable();
    }

    /** Keeps an unpiloted linked EVA frozen on its assigned underground carrier. */
    public void setSortieParkingBed(BlockPos bed)
    {
        this.sortieParkingBed = bed.immutable();
    }

    public void clearSortieDestination()
    {
        this.sortieDestinationDimension = null;
        this.sortieDestinationBed = null;
        this.sortieParkingBed = null;
    }

    /** Moves an unoccupied parked EVA between audited launch facilities. */
    @Nullable
    public EvaUnit01Entity transferUnpilotedTo(ServerLevel destination, Vec3 position,
                                                float yaw)
    {
        if (this.isVehicle() || this.isPassenger() || this.isLaunchSequenceActive()
                || this.level() == destination)
        {
            return null;
        }
        Entity moved = this.changeDimension(destination,
                directTeleporter(position, Vec3.ZERO, yaw, 0.0F));
        if (!(moved instanceof EvaUnit01Entity relocated))
        {
            return null;
        }
        relocated.setRot(yaw, 0.0F);
        relocated.yRotO = relocated.yBodyRot = relocated.yHeadRot = yaw;
        relocated.setYBodyRot(yaw);
        relocated.setYHeadRot(yaw);
        relocated.setDeltaMovement(Vec3.ZERO);
        relocated.setNoGravity(false);
        return relocated;
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

    /** Cockpit readout uses the persistent pilot value plus live airframe load. */
    public float getSynchronizationRatio(float partialTick)
    {
        float pilotValue = this.getPilotSynchronization();
        if (this.getActivationTicks() > 0)
        {
            return pilotValue * getActivationProgress(partialTick);
        }
        float hullPenalty = (1.0F - this.getHealth() / this.getMaxHealth()) * 11.0F;
        float fieldGain = this.isAtFieldOn() ? 1.6F : 0.0F;
        float motion = this.getDeltaMovement().horizontalDistanceSqr() > 0.002D
                ? Mth.sin((this.tickCount + partialTick) * 0.38F) * 1.25F
                : Mth.sin((this.tickCount + partialTick) * 0.08F) * 0.45F;
        float cannonLoad = this.getCannonCharge() > 0 ? -1.8F * this.chargeProgress() : 0.0F;
        return Mth.clamp(pilotValue - hullPenalty + fieldGain + motion + cannonLoad,
                0.0F, EvaPilotData.maxSynchronization());
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
        int next = this.getWeapon();
        for (int offset = 1; offset <= WEAPON_N2 + 1; offset++)
        {
            int candidate = Math.floorMod(this.getWeapon() + offset,
                    WEAPON_N2 + 1);
            if (this.armamentAvailable(candidate))
            {
                next = candidate;
                break;
            }
        }
        this.selectWeapon(next);
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
        this.meleeCooldown = this.synchronizedCooldown(MELEE_COOLDOWN_TICKS);
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
        this.smashCooldown = this.synchronizedCooldown(SMASH_COOLDOWN_TICKS);
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
        this.stompCooldown = this.synchronizedCooldown(STOMP_COOLDOWN_TICKS);
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

    private int synchronizedCooldown(int baseTicks)
    {
        float speed = EvaPilotCapability.attackSpeedMultiplier(
                this.getPilotSynchronization());
        return Math.max(1, Mth.ceil(baseTicks / speed));
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
        if (this.getControllingPassenger() != pilot)
        {
            return;
        }

        this.jumpBufferTicks = JUMP_BUFFER_TICKS;
        this.tryConsumeBufferedJump(pilot);
    }

    public void pilotJump(ServerPlayer pilot, int requestId)
    {
        if (requestId == this.lastJumpRequestId)
        {
            return;
        }
        this.lastJumpRequestId = requestId;
        this.pilotJump(pilot);
    }

    private boolean tryConsumeBufferedJump(ServerPlayer pilot)
    {
        if (this.jumpBufferTicks <= 0 || this.getControllingPassenger() != pilot
                || this.isPilotControlLocked() || this.jumpCooldown > 0
                || this.getCannonCharge() > 0
                || !this.onGround() && this.groundedGraceTicks <= 0)
        {
            return false;
        }
        if ((this.isPilotCrouching() || this.isPilotProne())
                && !this.hasStandingRoom())
        {
            this.jumpBufferTicks = 0;
            pilot.displayClientMessage(Component.translatable(
                    "msg.projectseele.cannot_stand"), true);
            return false;
        }
        if (this.isPilotCrouching())
        {
            this.setPilotCrouching(pilot, false);
            if (this.isPilotCrouching())
            {
                return false;
            }
        }
        if (this.isPilotProne())
        {
            this.toggleProne(pilot);
            if (this.isPilotProne())
            {
                return false;
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
        this.jumpBufferTicks = 0;
        this.groundedGraceTicks = 0;
        this.playSound(SoundEvents.IRON_GOLEM_STEP, 2.2F, 0.65F);
        return true;
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
        this.rifleCooldown = this.synchronizedCooldown(SeeleConfig.EVA_RIFLE_INTERVAL_TICKS.get());
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

    private void tickPowerSystem()
    {
        if (!(this.level() instanceof ServerLevel server))
        {
            return;
        }
        if (this.isBerserk())
        {
            this.setUmbilicalAnchor(null);
            this.entityData.set(DATA_POWER_TICKS, 0);
            this.entityData.set(DATA_AT_ON, false);
            return;
        }

        int range = SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.UMBILICAL_RANGE.get() : 32;
        BlockPos anchor = this.getUmbilicalAnchor();
        boolean anchorValid = anchor != null
                && server.hasChunkAt(anchor)
                && server.getBlockEntity(anchor) instanceof UmbilicalPylonBlockEntity
                && this.position().distanceToSqr(Vec3.atCenterOf(anchor))
                <= (double) range * range;
        if (!anchorValid)
        {
            anchor = null;
        }
        if (--this.powerCheckCooldown <= 0)
        {
            anchor = UmbilicalPylonBlockEntity.findNearest(
                    server, this.position(), range);
            this.powerCheckCooldown = 20;
        }

        boolean wasConnected = this.isUmbilicalConnected();
        int oldPower = this.getPowerTicks();
        this.setUmbilicalAnchor(anchor);
        if (anchor != null)
        {
            this.entityData.set(DATA_POWER_TICKS, this.getPowerCapacityTicks());
            if (this.tickCount % 20 == 0 && this.getHealth() < this.getMaxHealth())
            {
                double repair = SeeleConfig.COMMON_SPEC.isLoaded()
                        ? SeeleConfig.UMBILICAL_REPAIR_PER_SECOND.get() : 1.0D;
                if (repair > 0.0D)
                {
                    this.heal((float) repair);
                }
            }
            if (!wasConnected && this.getControllingPassenger() instanceof ServerPlayer pilot)
            {
                pilot.displayClientMessage(Component.translatable(
                        "msg.projectseele.power_connected"), true);
            }
            return;
        }

        if (wasConnected && this.getControllingPassenger() instanceof ServerPlayer pilot)
        {
            pilot.displayClientMessage(Component.translatable(
                    "msg.projectseele.power_disconnected"), true);
        }
        boolean active = this.getControllingPassenger() != null || this.isAtFieldOn();
        if (active && oldPower > 0)
        {
            int nextPower = oldPower - 1;
            this.entityData.set(DATA_POWER_TICKS, nextPower);
            if (nextPower == 0)
            {
                this.entityData.set(DATA_AT_ON, false);
                this.entityData.set(DATA_SPRINTING, false);
                this.entityData.set(DATA_CANNON_CHARGE, 0);
                this.entityData.set(DATA_N2_ARM_TICKS, 0);
                this.chargingHeld = false;
                this.setDeltaMovement(Vec3.ZERO);
                if (this.getControllingPassenger() instanceof ServerPlayer pilot)
                {
                    pilot.displayClientMessage(Component.translatable(
                            "msg.projectseele.power_depleted"), true);
                }
                this.playSound(SoundEvents.REDSTONE_TORCH_BURNOUT, 2.5F, 0.55F);
            }
        }
    }

    private void tickPilotSynchronization()
    {
        if (!(this.getControllingPassenger() instanceof ServerPlayer pilot))
        {
            return;
        }
        if (this.getActivationTicks() <= 20 && !this.isLaunchSequenceActive()
                && !this.isPowerDepleted() && !this.isCrucified())
        {
            EvaPilotCapability.tickActiveDriving(pilot);
        }
        float synchronization = EvaPilotCapability.synchronization(pilot);
        if (Math.abs(this.getPilotSynchronization() - synchronization) > 0.001F)
        {
            this.entityData.set(DATA_PILOT_SYNCHRONIZATION, synchronization);
        }
    }

    private void tickBerserkState()
    {
        if (this.berserkRecoveryTicks > 0 && !this.isBerserk())
        {
            this.berserkRecoveryTicks--;
        }
        if (!this.isBerserk())
        {
            if (this.canEnterBerserk())
            {
                this.beginBerserk();
            }
            return;
        }
        if (!(this.level() instanceof ServerLevel server)
                || this.getUnitVariant() != UNIT_01 || this.isCrucified()
                || this.isLaunchSequenceActive())
        {
            this.finishBerserk();
            return;
        }

        for (Entity passenger : List.copyOf(this.getPassengers()))
        {
            if (passenger instanceof ServerPlayer pilot)
            {
                pilot.stopRiding();
                pilot.addEffect(new net.minecraft.world.effect.MobEffectInstance(
                        net.minecraft.world.effect.MobEffects.DAMAGE_RESISTANCE, 100, 1));
                pilot.addEffect(new net.minecraft.world.effect.MobEffectInstance(
                        net.minecraft.world.effect.MobEffects.SLOW_FALLING, 200, 0));
            }
            else
            {
                passenger.stopRiding();
            }
        }

        int remaining = this.getBerserkTicks() - 1;
        this.entityData.set(DATA_BERSERK_TICKS, Math.max(0, remaining));
        if (this.berserkAttackCooldown > 0)
        {
            this.berserkAttackCooldown--;
        }
        if (--this.berserkTargetSearchCooldown <= 0
                || !(this.getTarget() instanceof Angel) || !this.getTarget().isAlive())
        {
            this.setTarget(this.findNearestBerserkTarget(server));
            this.berserkTargetSearchCooldown = 20;
        }

        LivingEntity target = this.getTarget();
        if (target != null && target.isAlive())
        {
            this.getLookControl().setLookAt(target, 30.0F, 30.0F);
            this.getNavigation().moveTo(target, 1.45D);
            double distance = this.distanceTo(target);
            if (distance <= 14.0D && Math.abs(target.getY() - this.getY()) <= 16.0D
                    && this.berserkAttackCooldown <= 0)
            {
                this.berserkClaw(target, server);
            }
        }
        else
        {
            this.getNavigation().stop();
        }

        if (this.tickCount % 3 == 0)
        {
            this.emitBerserkEyes(server);
        }
        if (remaining <= 0)
        {
            this.finishBerserk();
        }
    }

    private boolean canEnterBerserk()
    {
        if (this.getUnitVariant() != UNIT_01 || this.berserkRecoveryTicks > 0
                || this.isCrucified() || this.isLaunchSequenceActive()
                || this.getPowerTicks() > 0
                || !(this.getControllingPassenger() instanceof ServerPlayer))
        {
            return false;
        }
        double healthThreshold = SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.EVA_BERSERK_HEALTH_THRESHOLD.get() : 0.15D;
        double syncThreshold = SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.EVA_BERSERK_SYNC_THRESHOLD.get() : 60.0D;
        return this.getHealth() > 0.0F
                && this.getHealth() <= this.getMaxHealth() * healthThreshold
                && this.getPilotSynchronization() >= syncThreshold;
    }

    private void beginBerserk()
    {
        int duration = SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.EVA_BERSERK_DURATION_TICKS.get() : 900;
        ServerPlayer pilot = this.getControllingPassenger() instanceof ServerPlayer player
                ? player : null;
        this.entityData.set(DATA_BERSERK, true);
        this.entityData.set(DATA_BERSERK_TICKS, duration);
        this.entityData.set(DATA_AT_ON, false);
        this.entityData.set(DATA_WEAPON, WEAPON_FISTS);
        this.entityData.set(DATA_CROUCHING, false);
        this.entityData.set(DATA_PRONE, false);
        this.entityData.set(DATA_SPRINTING, false);
        this.entityData.set(DATA_CANNON_CHARGE, 0);
        this.entityData.set(DATA_N2_ARM_TICKS, 0);
        this.chargingHeld = false;
        this.updatePoseDimensions();
        this.setNoGravity(false);
        this.berserkAttackCooldown = 0;
        this.berserkTargetSearchCooldown = 0;
        this.triggerAnim("strike", "berserk_roar");
        this.playSound(SoundEvents.RAVAGER_ROAR, 5.0F, 0.62F);
        if (pilot != null)
        {
            pilot.displayClientMessage(Component.translatable(
                    "msg.projectseele.berserk_triggered"), false);
            pilot.stopRiding();
            pilot.addEffect(new net.minecraft.world.effect.MobEffectInstance(
                    net.minecraft.world.effect.MobEffects.DAMAGE_RESISTANCE, 100, 1));
            pilot.addEffect(new net.minecraft.world.effect.MobEffectInstance(
                    net.minecraft.world.effect.MobEffects.SLOW_FALLING, 200, 0));
        }
        ProjectSeele.LOGGER.warn(
                "EVA Unit-01 berserk: eva={} synchronization={} durationTicks={}",
                this.getStringUUID(), this.getPilotSynchronization(), duration);
    }

    @Nullable
    private LivingEntity findNearestBerserkTarget(ServerLevel server)
    {
        int range = SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.EVA_BERSERK_TARGET_RANGE.get() : 128;
        LivingEntity nearest = null;
        double nearestDistance = Double.MAX_VALUE;
        for (LivingEntity candidate : server.getEntitiesOfClass(LivingEntity.class,
                this.getBoundingBox().inflate(range),
                entity -> entity instanceof Angel && entity.isAlive()))
        {
            double distance = this.distanceToSqr(candidate);
            if (distance < nearestDistance)
            {
                nearest = candidate;
                nearestDistance = distance;
            }
        }
        return nearest;
    }

    private void berserkClaw(LivingEntity target, ServerLevel server)
    {
        this.leftSwing = !this.leftSwing;
        this.entityData.set(DATA_MELEE_LEFT, this.leftSwing);
        this.entityData.set(DATA_MELEE_SEQUENCE,
                (this.entityData.get(DATA_MELEE_SEQUENCE) + 1) & Integer.MAX_VALUE);
        this.triggerAnim("strike", this.leftSwing ? "melee_left" : "melee");
        this.swing(this.leftSwing ? InteractionHand.OFF_HAND : InteractionHand.MAIN_HAND, true);
        float multiplier = SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.EVA_BERSERK_DAMAGE_MULTIPLIER.get().floatValue() : 2.5F;
        float damage = MELEE_FIST_DAMAGE * multiplier;
        if (target.hurt(this.damageSources().mobAttack(this), damage))
        {
            Vec3 away = target.position().subtract(this.position())
                    .multiply(1.0D, 0.0D, 1.0D).normalize();
            target.push(away.x * 1.7D, 0.55D, away.z * 1.7D);
            server.sendParticles(ParticleTypes.SWEEP_ATTACK,
                    target.getX(), target.getY() + target.getBbHeight() * 0.55D,
                    target.getZ(), 4, 1.8D, 1.8D, 1.8D, 0.0D);
        }
        this.berserkAttackCooldown = 10;
        this.playSound(SoundEvents.RAVAGER_ATTACK, 3.5F, 0.72F);
    }

    private void emitBerserkEyes(ServerLevel server)
    {
        Vec3 forward = this.getForward().multiply(1.0D, 0.0D, 1.0D).normalize();
        Vec3 right = new Vec3(forward.z, 0.0D, -forward.x);
        Vec3 eye = this.position().add(0.0D, this.getBbHeight() * 0.88D, 0.0D)
                .add(forward.scale(2.2D));
        for (double side : new double[] {-0.42D, 0.42D})
        {
            Vec3 point = eye.add(right.scale(side));
            server.sendParticles(DustParticleOptions.REDSTONE,
                    point.x, point.y, point.z, 2, 0.05D, 0.05D, 0.05D, 0.0D);
        }
    }

    private void finishBerserk()
    {
        if (!this.isBerserk())
        {
            return;
        }
        this.entityData.set(DATA_BERSERK, false);
        this.entityData.set(DATA_BERSERK_TICKS, 0);
        this.berserkRecoveryTicks = SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.EVA_BERSERK_RECOVERY_TICKS.get() : 6000;
        this.getNavigation().stop();
        this.setTarget(null);
        this.setDeltaMovement(Vec3.ZERO);
        this.entityData.set(DATA_WEAPON, WEAPON_FISTS);
        this.playSound(SoundEvents.REDSTONE_TORCH_BURNOUT, 3.0F, 0.42F);
        ProjectSeele.LOGGER.warn(
                "EVA Unit-01 berserk ended: eva={} recoveryTicks={}",
                this.getStringUUID(), this.berserkRecoveryTicks);
    }

    private void setUmbilicalAnchor(@Nullable BlockPos anchor)
    {
        boolean connected = anchor != null;
        this.entityData.set(DATA_POWER_CONNECTED, connected);
        if (connected)
        {
            this.entityData.set(DATA_POWER_ANCHOR_X, anchor.getX());
            this.entityData.set(DATA_POWER_ANCHOR_Y, anchor.getY());
            this.entityData.set(DATA_POWER_ANCHOR_Z, anchor.getZ());
        }
    }

    private boolean isPilotControlLocked()
    {
        return this.getActivationTicks() > 20 || this.isLaunchSequenceActive()
                || this.isPowerDepleted() || this.isBerserk()
                || this.berserkRecoveryTicks > 0;
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
        if (this.onGround())
        {
            this.groundedGraceTicks = JUMP_COYOTE_TICKS;
        }
        if (this.jumpBufferTicks > 0)
        {
            boolean consumed = this.getControllingPassenger() instanceof ServerPlayer pilot
                    && this.tryConsumeBufferedJump(pilot);
            if (!consumed)
            {
                this.jumpBufferTicks--;
            }
        }
        if (!this.onGround() && this.groundedGraceTicks > 0)
        {
            // Consume after the buffered attempt so the first three airborne
            // ticks all retain their intended coyote-time opportunity.
            this.groundedGraceTicks--;
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
        this.tickPilotSynchronization();
        this.tickPowerSystem();
        this.tickBerserkState();
        this.tickSortieParkingLock();
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
        boolean canCharge = !this.isPilotControlLocked()
                && this.chargingHeld && this.getWeapon() == WEAPON_CANNON
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
        boolean canArmN2 = !this.isPilotControlLocked()
                && this.chargingHeld && this.getWeapon() == WEAPON_N2
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
            this.clearJumpRequestState();
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
        this.launchContinuousRoute = this.isContinuousSortie();
        this.launchRecoveryPending = false;
        this.launchPassengerRestoreGraceTicks = 0;
        this.entityData.set(DATA_CROUCHING, false);
        this.entityData.set(DATA_PRONE, false);
        this.entityData.set(DATA_SPRINTING, false);
        this.updatePoseDimensions();
        this.setNoGravity(true);
        this.enforceLaunchLock();
        ProjectSeele.LOGGER.info("NERV launch locked: eva={} bed={} targetY={}",
                this.getStringUUID(), bed.toShortString(), this.launchTargetY());
    }

    /**
     * A same-dimension destination lodestone is the real surface carrier.
     * Legacy external launch complexes retain their original 32-block travel,
     * while an integrated NERV shaft derives its complete height from the two
     * physical station markers.
     */
    private boolean isContinuousSortie()
    {
        return this.launchBedPos != null
                && this.sortieDestinationDimension != null
                && this.sortieDestinationDimension.equals(this.level().dimension())
                && this.sortieDestinationBed != null
                && this.sortieDestinationBed.getY() > this.launchBedPos.getY()
                && this.sortieDestinationBed.getX() == this.launchBedPos.getX()
                && this.sortieDestinationBed.getZ() == this.launchBedPos.getZ()
                && this.level().getBlockState(this.sortieDestinationBed).is(Blocks.LODESTONE);
    }

    private double launchTargetY()
    {
        if (this.launchContinuousRoute && this.sortieDestinationBed != null)
        {
            return this.sortieDestinationBed.getY() + 1.0D;
        }
        return this.launchBedPos == null ? this.getY()
                : this.launchBedPos.getY() + LAUNCH_TARGET_ABOVE_BED;
    }

    private int launchDeckY()
    {
        if (this.launchContinuousRoute && this.sortieDestinationBed != null)
        {
            return this.sortieDestinationBed.getY();
        }
        return this.launchBedPos == null ? Mth.floor(this.getY()) - 1
                : this.launchBedPos.getY() + (int) LAUNCH_TARGET_ABOVE_BED - 1;
    }

    private int launchAscentTicks()
    {
        if (this.launchBedPos == null)
        {
            return LAUNCH_ASCENT_TICKS;
        }
        double distance = Math.max(0.0D,
                this.launchTargetY() - (this.launchBedPos.getY() + 1.0D));
        return Math.max(LAUNCH_ASCENT_TICKS,
                Mth.ceil(distance / CONTINUOUS_ASCENT_BLOCKS_PER_TICK));
    }

    private void tickSortieParkingLock()
    {
        if (this.sortieParkingBed == null || !this.hasSortieDestination()
                || this.isLaunchSequenceActive() || this.getControllingPassenger() != null)
        {
            return;
        }
        if (!this.level().getBlockState(this.sortieParkingBed).is(Blocks.LODESTONE))
        {
            ProjectSeele.LOGGER.error(
                    "NERV sortie parking lock lost its bed: eva={} bed={}",
                    this.getStringUUID(), this.sortieParkingBed.toShortString());
            this.clearSortieDestination();
            this.setNoGravity(false);
            return;
        }
        this.getNavigation().stop();
        this.setTarget(null);
        this.setPos(this.sortieParkingBed.getX() + 0.5D,
                this.sortieParkingBed.getY() + 1.0D,
                this.sortieParkingBed.getZ() + 0.5D);
        this.setDeltaMovement(Vec3.ZERO);
        this.setRot(SILO_BAY_YAW, 0.0F);
        this.yRotO = this.yBodyRot = this.yHeadRot = SILO_BAY_YAW;
        this.fallDistance = 0.0F;
        this.setNoGravity(true);
        this.hasImpulse = true;
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
        if (this.launchContinuousRoute
                && (!(this.level() instanceof ServerLevel serverLevel)
                    || !this.isContinuousSortie()
                    || !isContinuousSortieRouteClear(serverLevel,
                            this.launchBedPos, this.sortieDestinationBed)))
        {
            if (this.getControllingPassenger() instanceof ServerPlayer pilot)
            {
                pilot.displayClientMessage(Component.literal(
                        "NERV launch inhibited: the physical shaft or surface exit is obstructed."),
                        true);
            }
            ProjectSeele.LOGGER.error(
                    "NERV continuous sortie preflight failed: eva={} lower={} upper={}",
                    this.getStringUUID(), this.launchBedPos.toShortString(),
                    this.sortieDestinationBed == null ? "missing"
                            : this.sortieDestinationBed.toShortString());
            this.resetLaunchSequence();
            return;
        }
        int ascentTicks = this.launchAscentTicks();
        this.entityData.set(DATA_LAUNCH_PHASE, LAUNCH_ASCENT);
        this.entityData.set(DATA_LAUNCH_TICKS, ascentTicks);
        this.setSurfaceCarrier(false);
        this.setNoGravity(true);
        this.setPos(this.launchBedPos.getX() + 0.5D, this.launchBedPos.getY() + 1.0D,
                this.launchBedPos.getZ() + 0.5D);
        this.setDeltaMovement(Vec3.ZERO);
        ProjectSeele.LOGGER.info("NERV launch ascent: eva={} ticks={}",
                this.getStringUUID(), ascentTicks);
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
            double targetY = this.launchTargetY();
            int ascentTicks = this.launchAscentTicks();
            int remainingTicks = Math.max(0, this.getLaunchTicks() - 1);
            float progress = Mth.clamp((ascentTicks - remainingTicks)
                    / (float) ascentTicks, 0.0F, 1.0F);
            // A launch carrier must keep accelerating through the aperture.
            // Smoothstep decelerates to zero at progress=1 and made the EVA
            // visibly hesitate at street level. This curve starts controlled
            // but retains positive velocity all the way through the exit.
            float easedProgress = progress * (0.35F + 0.65F * progress);
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
            if (!this.updateMovingCarrier())
            {
                if (this.getControllingPassenger() instanceof ServerPlayer pilot)
                {
                    pilot.displayClientMessage(Component.literal(
                            "NERV emergency stop: an obstruction entered the launch shaft."),
                            true);
                }
                ProjectSeele.LOGGER.error(
                        "NERV carrier obstruction during ascent: eva={} y={}",
                        this.getStringUUID(), Mth.floor(this.getY()) - 1);
                this.resetLaunchSequence();
                return;
            }
            this.entityData.set(DATA_LAUNCH_TICKS, remainingTicks);
            if (remainingTicks <= 0)
            {
                this.clearMovingCarrierBelowSurface();
                boolean continuousRoute = this.launchContinuousRoute;
                if (this.completeLinkedSortie())
                {
                    return;
                }
                if (continuousRoute)
                {
                    this.resetLaunchSequence();
                    return;
                }
                this.launchCarrierY = this.launchDeckY();
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
        if (phase == LAUNCH_CLEAR && this.launchContinuousRoute
                && this.sortieDestinationBed != null)
        {
            this.enforceContinuousSurfaceArrival();
            int remainingTicks = this.getLaunchTicks() - 1;
            if (remainingTicks <= 0)
            {
                this.finishTransferredSortie(this.launchLockedYaw);
            }
            else
            {
                this.entityData.set(DATA_LAUNCH_TICKS, remainingTicks);
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
    private boolean updateMovingCarrier()
    {
        if (this.launchBedPos == null || !(this.level() instanceof ServerLevel))
        {
            return false;
        }
        int bedY = this.launchBedPos.getY();
        int deckY = this.launchDeckY();
        int desiredY = Mth.clamp(Mth.floor(this.getY()) - 1, bedY, deckY);
        if (desiredY == this.launchCarrierY)
        {
            return true;
        }
        if (desiredY > bedY && desiredY < deckY
                && !this.canPlaceMovingCarrierLayer(desiredY))
        {
            return false;
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
            ProjectSeele.LOGGER.info(
                    "NERV carrier progress: eva={} carrierY={} travelled={}/{}",
                    this.getStringUUID(), desiredY, travelled, deckY - bedY);
        }
        return true;
    }

    private void clearMovingCarrierBelowSurface()
    {
        if (this.launchBedPos == null)
        {
            return;
        }
        int bedY = this.launchBedPos.getY();
        int deckY = this.launchDeckY();
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
        int deckY = this.launchDeckY();
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
        if (!this.updateMovingCarrier())
        {
            this.resetLaunchSequence();
            return false;
        }
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

    private boolean canPlaceMovingCarrierLayer(int y)
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
                if (!serverLevel.getBlockState(block).isAir())
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
        setSurfaceCarrierAt(serverLevel, this.launchBedPos,
                this.launchDeckY(), closed);
    }

    private static void setSurfaceCarrierAt(ServerLevel level, BlockPos bed,
                                            int deckY, boolean closed)
    {
        boolean flushTokyo3Door = IntegratedNervMapBuilder.isSurfaceStation(bed);
        for (int x = -5; x <= 5; x++)
        {
            for (int z = -5; z <= 5; z++)
            {
                BlockPos deck = new BlockPos(bed.getX() + x, deckY, bed.getZ() + z);
                if (closed)
                {
                    var desired = x == 0 && z == 0
                            && level.getBlockState(deck).is(Blocks.LODESTONE)
                            ? Blocks.LODESTONE.defaultBlockState()
                            : flushTokyo3Door
                            ? Blocks.SMOOTH_STONE.defaultBlockState()
                            : (Math.abs(x) == 5 || Math.abs(z) == 5)
                            ? Blocks.IRON_BLOCK.defaultBlockState()
                            : Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState();
                    if (!level.getBlockState(deck).equals(desired))
                    {
                        level.setBlock(deck, desired, 2);
                    }
                }
                else if (level.getBlockState(deck).is(Blocks.IRON_BLOCK)
                        || level.getBlockState(deck).is(Blocks.LIGHT_GRAY_CONCRETE))
                {
                    level.setBlock(deck, Blocks.AIR.defaultBlockState(), 2);
                }
            }
        }
    }

    /** Completes a linked launch; integrated maps keep the same entity and dimension. */
    private boolean completeLinkedSortie()
    {
        if (this.sortieDestinationDimension == null || this.sortieDestinationBed == null
                || !(this.level() instanceof ServerLevel sourceLevel)
                || !(this.getControllingPassenger() instanceof ServerPlayer pilot))
        {
            return false;
        }
        ServerLevel destination = sourceLevel.getServer().getLevel(
                this.sortieDestinationDimension);
        BlockPos destinationBed = this.sortieDestinationBed;
        if (destination == null
                || !destination.getBlockState(destinationBed).is(Blocks.LODESTONE))
        {
            pilot.displayClientMessage(Component.literal(
                    "NERV sortie link unavailable; completing launch inside GeoFront."), true);
            ProjectSeele.LOGGER.error(
                    "NERV cross-dimension sortie refused: eva={} dimension={} bed={}",
                    this.getStringUUID(), this.sortieDestinationDimension.location(),
                    destinationBed.toShortString());
            return false;
        }

        if (destination == sourceLevel)
        {
            if (this.launchBedPos == null
                    || !isContinuousSortieRouteClear(sourceLevel,
                            this.launchBedPos, destinationBed))
            {
                pilot.displayClientMessage(Component.literal(
                        "NERV physical shaft obstruction detected; launch held at the emergency deck."),
                        true);
                ProjectSeele.LOGGER.error(
                        "NERV continuous sortie shaft blocked: eva={} lower={} upper={}",
                        this.getStringUUID(),
                        this.launchBedPos == null ? "missing"
                                : this.launchBedPos.toShortString(),
                        destinationBed.toShortString());
                return false;
            }

            BlockPos lowerBed = this.launchBedPos;
            int rise = destinationBed.getY() - lowerBed.getY();
            float arrivalYaw = this.launchLockedYaw;
            Vec3 arrival = new Vec3(destinationBed.getX() + 0.5D,
                    destinationBed.getY() + 1.0D,
                    destinationBed.getZ() + 0.5D);
            this.setPos(arrival.x, arrival.y, arrival.z);
            for (Entity passenger : this.getPassengers())
            {
                this.positionRider(passenger, Entity::setPos);
            }
            setSurfaceCarrierAt(sourceLevel, destinationBed,
                    destinationBed.getY(), true);
            this.beginContinuousSurfaceArrival(arrivalYaw);
            pilot.displayClientMessage(Component.literal(
                    "TOKYO-3 SURFACE CLEAR - physical shaft sortie complete"), true);
            sourceLevel.sendParticles(ParticleTypes.CLOUD,
                    arrival.x, arrival.y, arrival.z,
                    90, 5.0D, 0.8D, 5.0D, 0.14D);
            sourceLevel.sendParticles(ParticleTypes.ELECTRIC_SPARK,
                    arrival.x, arrival.y + 3.0D, arrival.z,
                    48, 4.0D, 4.0D, 4.0D, 0.08D);
            ProjectSeele.LOGGER.info(
                    "NERV continuous sortie complete: eva={} dimension={} lower={} upper={} rise={}",
                    this.getStringUUID(), sourceLevel.dimension().location(),
                    lowerBed.toShortString(), destinationBed.toShortString(), rise);
            return true;
        }

        if (!isSortieShaftClear(destination, destinationBed))
        {
            pilot.displayClientMessage(Component.literal(
                    "Legacy destination shaft is obstructed; using the local emergency deck."), true);
            return false;
        }

        destination.getChunkAt(destinationBed);
        Vec3 arrival = new Vec3(destinationBed.getX() + 0.5D,
                destinationBed.getY() + LAUNCH_TARGET_ABOVE_BED,
                destinationBed.getZ() + 0.5D);
        float arrivalYaw = this.launchLockedYaw;
        pilot.stopRiding();
        Entity moved = this.changeDimension(destination,
                directTeleporter(arrival, new Vec3(0.0D, 0.12D, 0.0D),
                        arrivalYaw, 0.0F));
        if (!(moved instanceof EvaUnit01Entity relocated))
        {
            if (!this.isRemoved())
            {
                pilot.startRiding(this, true);
            }
            ProjectSeele.LOGGER.error(
                    "NERV cross-dimension sortie transfer failed: eva={} destination={}",
                    this.getStringUUID(), destination.dimension().location());
            return false;
        }

        relocated.finishTransferredSortie(arrivalYaw);
        setSurfaceCarrierAt(destination, destinationBed,
                destinationBed.getY() + (int) LAUNCH_TARGET_ABOVE_BED - 1, true);
        pilot.teleportTo(destination, arrival.x, arrival.y + 1.0D, arrival.z,
                arrivalYaw, 0.0F);
        if (!pilot.startRiding(relocated, true))
        {
            ProjectSeele.LOGGER.error(
                    "NERV sortie arrived but pilot remount failed: eva={} pilot={}",
                    relocated.getStringUUID(), pilot.getGameProfile().getName());
        }
        pilot.displayClientMessage(Component.literal(
                "TOKYO-3 SURFACE CLEAR — EVA sortie complete"), true);
        destination.sendParticles(ParticleTypes.CLOUD, arrival.x, arrival.y, arrival.z,
                90, 5.0D, 0.8D, 5.0D, 0.14D);
        destination.sendParticles(ParticleTypes.ELECTRIC_SPARK,
                arrival.x, arrival.y + 3.0D, arrival.z,
                48, 4.0D, 4.0D, 4.0D, 0.08D);
        ProjectSeele.LOGGER.info(
                "NERV cross-dimension sortie complete: eva={} source={} destination={} bed={}",
                relocated.getStringUUID(), sourceLevel.dimension().location(),
                destination.dimension().location(), destinationBed.toShortString());
        return true;
    }

    private void finishTransferredSortie(float yaw)
    {
        this.entityData.set(DATA_LAUNCH_PHASE, LAUNCH_IDLE);
        this.entityData.set(DATA_LAUNCH_TICKS, 0);
        this.entityData.set(DATA_ACTIVATION_TICKS, 0);
        this.launchBedPos = null;
        this.launchCarrierY = NO_LAUNCH_CARRIER;
        this.launchContinuousRoute = false;
        this.launchRecoveryPending = false;
        this.launchPassengerRestoreGraceTicks = 0;
        this.launchLockedYaw = yaw;
        this.clearSortieDestination();
        this.setNoGravity(false);
        this.setDeltaMovement(Vec3.ZERO);
        this.setOnGround(true);
        this.fallDistance = 0.0F;
        this.setRot(yaw, 0.0F);
        this.yRotO = this.yBodyRot = this.yHeadRot = yaw;
    }

    private void beginContinuousSurfaceArrival(float yaw)
    {
        this.entityData.set(DATA_LAUNCH_PHASE, LAUNCH_CLEAR);
        this.entityData.set(DATA_LAUNCH_TICKS, CONTINUOUS_SURFACE_SYNC_TICKS);
        this.entityData.set(DATA_ACTIVATION_TICKS, 0);
        this.launchCarrierY = NO_LAUNCH_CARRIER;
        this.launchRecoveryPending = false;
        this.launchPassengerRestoreGraceTicks = 0;
        this.launchLockedYaw = yaw;
        this.setNoGravity(true);
        this.enforceContinuousSurfaceArrival();
    }

    private void enforceContinuousSurfaceArrival()
    {
        if (this.sortieDestinationBed == null)
        {
            return;
        }
        BlockPos bed = this.sortieDestinationBed;
        this.setPos(bed.getX() + 0.5D, bed.getY() + 1.0D,
                bed.getZ() + 0.5D);
        this.setDeltaMovement(Vec3.ZERO);
        this.setRot(this.launchLockedYaw, 0.0F);
        this.yRotO = this.yBodyRot = this.yHeadRot = this.launchLockedYaw;
        this.fallDistance = 0.0F;
        this.hasImpulse = true;
        for (Entity passenger : this.getPassengers())
        {
            this.positionRider(passenger, Entity::setPos);
        }
        if (this.level() instanceof ServerLevel serverLevel
                && (this.getLaunchTicks() == CONTINUOUS_SURFACE_SYNC_TICKS
                    || this.getLaunchTicks() % 4 == 0))
        {
            serverLevel.getChunkSource().broadcastAndSend(this,
                    new ClientboundTeleportEntityPacket(this));
            if (this.getControllingPassenger() instanceof ServerPlayer pilot)
            {
                SeeleNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> pilot),
                        new ClientboundEvaArrivalSyncPacket(this.getId(),
                                this.getX(), this.getY(), this.getZ(),
                                this.launchLockedYaw, 0.0F));
            }
        }
    }

    /**
     * Applies the server's physical shaft-exit position on the locally driven
     * vehicle. The normal teleport packet is ignored for local vehicle
     * authority, which otherwise leaves the pilot visually inside the shaft.
     */
    public void applyClientArrivalSync(double x, double y, double z,
            float yaw, float pitch)
    {
        if (!this.level().isClientSide)
        {
            return;
        }
        this.syncPacketPositionCodec(x, y, z);
        this.setPos(x, y, z);
        this.xo = x;
        this.yo = y;
        this.zo = z;
        this.setDeltaMovement(Vec3.ZERO);
        this.setRot(yaw, pitch);
        this.yRotO = yaw;
        this.xRotO = pitch;
        this.yBodyRot = yaw;
        this.yBodyRotO = yaw;
        this.yHeadRot = yaw;
        this.yHeadRotO = yaw;
        this.fallDistance = 0.0F;
        this.setOnGround(true);
        this.hasImpulse = true;
        this.clientJumpImpulsePending = false;
        for (Entity passenger : this.getPassengers())
        {
            this.positionRider(passenger, (entity, riderX, riderY, riderZ) ->
            {
                entity.setPos(riderX, riderY, riderZ);
                entity.xo = riderX;
                entity.yo = riderY;
                entity.zo = riderZ;
                entity.setDeltaMovement(Vec3.ZERO);
                entity.fallDistance = 0.0F;
            });
        }
    }

    private static boolean isSortieShaftClear(ServerLevel level, BlockPos bed)
    {
        for (int y = 1; y <= (int) LAUNCH_TARGET_ABOVE_BED - 1; y++)
        {
            for (int x = -5; x <= 5; x++)
            {
                for (int z = -5; z <= 5; z++)
                {
                    if (!level.getBlockState(bed.offset(x, y, z)).isAir())
                    {
                        return false;
                    }
                }
            }
        }
        return true;
    }

    /** Full 11x11 block audit between the two station markers. */
    private static boolean isContinuousSortieShaftClear(ServerLevel level,
                                                         BlockPos lowerBed,
                                                         BlockPos upperBed)
    {
        if (lowerBed.getX() != upperBed.getX()
                || lowerBed.getZ() != upperBed.getZ()
                || upperBed.getY() <= lowerBed.getY())
        {
            return false;
        }
        for (int y = lowerBed.getY() + 1; y < upperBed.getY(); y++)
        {
            for (int x = -5; x <= 5; x++)
            {
                for (int z = -5; z <= 5; z++)
                {
                    BlockPos position = new BlockPos(lowerBed.getX() + x, y,
                            lowerBed.getZ() + z);
                    if (!level.getBlockState(position).isAir())
                    {
                        return false;
                    }
                }
            }
        }
        return true;
    }

    private static boolean isContinuousSortieRouteClear(ServerLevel level,
                                                         BlockPos lowerBed,
                                                         BlockPos upperBed)
    {
        if (!isContinuousSortieShaftClear(level, lowerBed, upperBed))
        {
            return false;
        }
        for (int y = upperBed.getY() + 1;
             y <= upperBed.getY() + CONTINUOUS_EXIT_HEADROOM; y++)
        {
            for (int x = -5; x <= 5; x++)
            {
                for (int z = -5; z <= 5; z++)
                {
                    if (!level.getBlockState(new BlockPos(upperBed.getX() + x,
                            y, upperBed.getZ() + z)).isAir())
                    {
                        return false;
                    }
                }
            }
        }
        return true;
    }

    private static ITeleporter directTeleporter(Vec3 position, Vec3 velocity,
                                                 float yaw, float pitch)
    {
        return new ITeleporter()
        {
            @Override
            public PortalInfo getPortalInfo(Entity entity, ServerLevel destination,
                                            Function<ServerLevel, PortalInfo> defaultPortalInfo)
            {
                return new PortalInfo(position, velocity, yaw, pitch);
            }
        };
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
        this.launchContinuousRoute = false;
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
        this.clearJumpRequestState();
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
            return this.applyHullDamageWithFeedback(source, amount);
        }
        if (AtFieldRules.bypassesAtField(source))
        {
            return this.applyHullDamageWithFeedback(source, amount);
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
                return leftover > 0.0F && this.applyHullDamageWithFeedback(source, leftover);
            }
            // Conventional weapons cannot even scratch the field.
            this.rippleAt(source);
            return false;
        }
        return this.applyHullDamageWithFeedback(source, amount);
    }

    private boolean applyHullDamageWithFeedback(DamageSource source, float amount)
    {
        float healthBefore = this.getHealth();
        boolean accepted = super.hurt(source, amount);
        float actualHullDamage = Math.max(0.0F, healthBefore - this.getHealth());
        if (accepted && actualHullDamage > 0.0F
                && this.getControllingPassenger() instanceof ServerPlayer pilot)
        {
            float synchronization = EvaPilotCapability.synchronization(pilot);
            float feedback = actualHullDamage
                    * EvaPilotCapability.neuralFeedbackFraction(synchronization);
            if (feedback >= 0.05F)
            {
                pilot.hurt(source, feedback);
                pilot.displayClientMessage(Component.translatable(
                        "msg.projectseele.sync_feedback",
                        String.format("%.1f", feedback),
                        String.format("%.1f", synchronization)), true);
            }
        }
        return accepted;
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
        if (this.isBerserk() || this.berserkRecoveryTicks > 0)
        {
            player.displayClientMessage(Component.translatable(
                    this.isBerserk() ? "msg.projectseele.berserk_active"
                            : "msg.projectseele.berserk_recovery",
                    Math.max(0, (this.isBerserk() ? this.getBerserkTicks() : this.berserkRecoveryTicks) / 20)), true);
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
        this.clearJumpRequestState();
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

    private void clearJumpRequestState()
    {
        this.jumpBufferTicks = 0;
        this.groundedGraceTicks = 0;
        this.lastJumpRequestId = Integer.MIN_VALUE;
        this.clientJumpImpulsePending = false;
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
        return super.isImmobile() || this.isCrucified() || (!this.isBerserk() && this.isPilotControlLocked());
    }

    @Override
    public boolean isPushable()
    {
        return !this.isCrucified() && (this.isBerserk() || !this.isPilotControlLocked()) && super.isPushable();
    }

    @Override
    public void travel(Vec3 input)
    {
        if (this.isCrucified() || (!this.isBerserk() && this.isPilotControlLocked()))
        {
            this.setDeltaMovement(Vec3.ZERO);
            return;
        }
        super.travel(input);
        // LivingEntity calls this only after it has selected the local pilot
        // as vehicle authority. Applying the synchronized impulse here avoids
        // both the pre-travel friction pass and the non-authoritative branch
        // that zeros remote ridden entities.
        if (this.level().isClientSide && this.clientJumpImpulsePending
                && this.isControlledByLocalInstance())
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
        float synchronizationSpeed = EvaPilotCapability.mobilityMultiplier(
                this.getPilotSynchronization());
        if (this.isPilotCrouching())
        {
            return CROUCH_SPEED * synchronizationSpeed;
        }
        if (this.isPilotProne())
        {
            return PRONE_SPEED * synchronizationSpeed;
        }
        float variantSpeed = switch (this.getUnitVariant())
        {
            case UNIT_00 -> this.isPilotSprinting() ? 0.52F : 0.36F;
            case UNIT_02 -> this.isPilotSprinting() ? 0.72F : 0.48F;
            default -> this.isPilotSprinting() ? SPRINT_SPEED : WALK_SPEED;
        };
        return variantSpeed * synchronizationSpeed;
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
                this.clientJumpImpulsePending = this.isControlledByLocalInstance();
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
        else if (this.isBerserk() || this.isPilotSprinting())
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
            if (this.isBerserk())
            {
                return state.setAndContinue(state.isMoving() ? ANIM_RUN : ANIM_IDLE);
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
            if (this.isCrucified() || this.isBerserk())
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
                .triggerableAnim("berserk_roar", ANIM_BERSERK_ROAR)
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
