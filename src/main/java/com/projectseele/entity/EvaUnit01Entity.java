package com.projectseele.entity;

import com.projectseele.config.SeeleConfig;
import com.projectseele.combat.AtFieldRules;
import com.projectseele.fx.AtFieldFX;
import com.projectseele.network.ClientboundCannonBeamPacket;
import com.projectseele.network.ClientboundNukeFxPacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.registry.ModSounds;
import com.projectseele.registry.ModEntities;
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
 * Angel fight. Carries its own weapon state (fists / prog knife / positron
 * sniper cannon), an A.T. Field shield pool, and survives exactly two Ramiel
 * beams. All pilot input arrives via {@code ServerboundEvaControlPacket}.
 */
public class EvaUnit01Entity extends PathfinderMob implements GeoEntity
{
    public static final int WEAPON_FISTS = 0;
    public static final int WEAPON_KNIFE = 1;
    public static final int WEAPON_CANNON = 2;
    public static final int WEAPON_LANCE = 3;
    public static final int UNIT_00 = 0;
    public static final int UNIT_01 = 1;
    public static final int UNIT_02 = 2;

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
    private static final double JUMP_VELOCITY = 1.05D;
    private static final int JUMP_COOLDOWN_TICKS = 10;

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

    private static final RawAnimation ANIM_IDLE = RawAnimation.begin().thenLoop("animation.eva_unit01.idle");
    private static final RawAnimation ANIM_WALK = RawAnimation.begin().thenLoop("animation.eva_unit01.walk");
    private static final RawAnimation ANIM_RUN = RawAnimation.begin().thenLoop("animation.eva_unit01.run");
    private static final RawAnimation ANIM_CROUCH = RawAnimation.begin().thenLoop("animation.eva_unit01.crouch");
    private static final RawAnimation ANIM_CROUCH_WALK = RawAnimation.begin().thenLoop("animation.eva_unit01.crouch_walk");
    private static final RawAnimation ANIM_JUMP = RawAnimation.begin().thenLoop("animation.eva_unit01.jump");
    private static final RawAnimation ANIM_FALL = RawAnimation.begin().thenLoop("animation.eva_unit01.fall");
    private static final RawAnimation ANIM_PRONE = RawAnimation.begin().thenLoop("animation.eva_unit01.prone");
    private static final RawAnimation ANIM_CRUCIFIED = RawAnimation.begin().thenLoop("animation.eva_unit01.crucified");
    private static final RawAnimation ANIM_CRAWL = RawAnimation.begin().thenLoop("animation.eva_unit01.crawl");
    private static final RawAnimation ANIM_AIM = RawAnimation.begin().thenLoop("animation.eva_unit01.aim");
    private static final RawAnimation ANIM_MELEE = RawAnimation.begin().thenPlay("animation.eva_unit01.melee");
    private static final RawAnimation ANIM_MELEE_LEFT = RawAnimation.begin().thenPlay("animation.eva_unit01.melee_left");
    private static final RawAnimation ANIM_KNIFE = RawAnimation.begin().thenPlay("animation.eva_unit01.knife");
    private static final RawAnimation ANIM_KNIFE_LEFT = RawAnimation.begin().thenPlay("animation.eva_unit01.knife_left");
    private static final RawAnimation ANIM_SMASH = RawAnimation.begin().thenPlay("animation.eva_unit01.smash");
    private static final RawAnimation ANIM_CANNON_FIRE = RawAnimation.begin().thenPlay("animation.eva_unit01.cannon_fire");
    private static final RawAnimation ANIM_LAND = RawAnimation.begin().thenPlay("animation.eva_unit01.land");
    private static final RawAnimation ANIM_STOMP = RawAnimation.begin().thenPlay("animation.eva_unit01.stomp");

    private final AnimatableInstanceCache geoCache = GeckoLibUtil.createInstanceCache(this);

    private boolean chargingHeld;
    private int meleeCooldown;
    private int smashCooldown;
    private int stompCooldown;
    private boolean leftSwing;
    private int atRegenDelay;
    private int jumpCooldown;
    private boolean crouchingDimensions;
    private boolean proneDimensions;
    private boolean wasAirborne;
    private int activationTicks;
    private int clientMeleeSequence;
    private int clientMeleeStartTick = -1000;
    private boolean clientMeleeLeft;
    private int clientSmashSequence;
    private int clientSmashStartTick = -1000;

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
        this.entityData.define(DATA_CROUCHING, false);
        this.entityData.define(DATA_SPRINTING, false);
        this.entityData.define(DATA_PRONE, false);
        this.entityData.define(DATA_CRUCIFIED, false);
        this.entityData.define(DATA_MELEE_LEFT, false);
        this.entityData.define(DATA_MELEE_SEQUENCE, 0);
        this.entityData.define(DATA_SMASH_SEQUENCE, 0);
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

    /** Nail to / release from the Tree. Gravity and pose follow the flag. */
    public void setCrucified(boolean crucified)
    {
        this.entityData.set(DATA_CRUCIFIED, crucified);
        this.setNoGravity(crucified);
        if (crucified)
        {
            this.setDeltaMovement(Vec3.ZERO);
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
        int next = (this.getWeapon() + 1) % 4;
        this.entityData.set(DATA_WEAPON, next);
        this.entityData.set(DATA_CANNON_CHARGE, 0);
        this.chargingHeld = false;
        String key = switch (next)
        {
            case WEAPON_KNIFE -> "msg.projectseele.weapon_knife";
            case WEAPON_CANNON -> "msg.projectseele.weapon_cannon";
            case WEAPON_LANCE -> "msg.projectseele.weapon_lance";
            default -> "msg.projectseele.weapon_fists";
        };
        pilot.displayClientMessage(Component.translatable(key), true);
        this.playSound(SoundEvents.IRON_GOLEM_STEP, 2.0F, 1.4F);
    }

    public void toggleAtField(ServerPlayer pilot)
    {
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
        this.chargingHeld = held;
    }

    /** Left-click from the plug: alternating swings in front of the Unit. */
    public void meleeAttack(ServerPlayer pilot)
    {
        if (this.activationTicks > 20 || this.meleeCooldown > 0 || this.getWeapon() == WEAPON_CANNON)
        {
            return;
        }
        this.meleeCooldown = MELEE_COOLDOWN_TICKS;
        this.leftSwing = !this.leftSwing;
        this.entityData.set(DATA_MELEE_LEFT, this.leftSwing);
        this.entityData.set(DATA_MELEE_SEQUENCE,
                (this.entityData.get(DATA_MELEE_SEQUENCE) + 1) & Integer.MAX_VALUE);
        this.swing(this.leftSwing ? InteractionHand.OFF_HAND : InteractionHand.MAIN_HAND, true);
        boolean knife = this.getWeapon() == WEAPON_KNIFE;
        boolean lance = this.getWeapon() == WEAPON_LANCE;
        String animation = knife || lance
                ? (this.leftSwing ? "knife_left" : "knife")
                : (this.leftSwing ? "melee_left" : "melee");
        this.triggerAnim("strike", animation);
        float baseDamage = lance ? MELEE_LANCE_DAMAGE : knife ? MELEE_KNIFE_DAMAGE : MELEE_FIST_DAMAGE;
        float damage = baseDamage * this.getMeleeMultiplier();
        Vec3 forward = this.getForward().multiply(1.0D, 0.0D, 1.0D).normalize();
        Vec3 center = this.position().add(forward.scale(MELEE_REACH)).add(0.0D, 14.0D, 0.0D);
        AABB zone = new AABB(center, center).inflate(MELEE_RADIUS, 10.0D, MELEE_RADIUS);
        this.strikeZone(pilot, zone, damage, 1.1D, center);
        this.playSound(knife || lance ? SoundEvents.PLAYER_ATTACK_SWEEP : SoundEvents.IRON_GOLEM_ATTACK, 2.5F,
                lance ? 0.48F : knife ? 0.7F : 0.8F);
    }

    /** Crouch + attack: a slow two-handed slam that flattens the area ahead. */
    public void smashAttack(ServerPlayer pilot)
    {
        if (this.activationTicks > 20 || this.smashCooldown > 0 || this.getWeapon() == WEAPON_CANNON)
        {
            return;
        }
        this.smashCooldown = SMASH_COOLDOWN_TICKS;
        this.entityData.set(DATA_SMASH_SEQUENCE,
                (this.entityData.get(DATA_SMASH_SEQUENCE) + 1) & Integer.MAX_VALUE);
        this.triggerAnim("strike", "smash");

        boolean knife = this.getWeapon() == WEAPON_KNIFE;
        boolean lance = this.getWeapon() == WEAPON_LANCE;
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
        this.playSound(SoundEvents.IRON_GOLEM_DEATH, 3.0F, 0.55F);
    }

    /** Heavy single-foot strike for targets beneath the Unit. */
    public void stompAttack(ServerPlayer pilot)
    {
        if (this.activationTicks > 20 || this.stompCooldown > 0 || this.getWeapon() == WEAPON_CANNON)
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
        boolean full = this.getCannonCharge() >= SeeleConfig.CANNON_CHARGE_TICKS.get();
        this.entityData.set(DATA_CANNON_CHARGE, 0);
        if (this.activationTicks > 20 || !full || this.getWeapon() != WEAPON_CANNON || this.getCannonCooldown() > 0)
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
        if (this.getControllingPassenger() != pilot || this.isPilotCrouching() == crouching)
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
        if (this.getControllingPassenger() != pilot)
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
        if (this.getControllingPassenger() == pilot)
        {
            this.entityData.set(DATA_SPRINTING, sprinting && !this.isPilotCrouching() && !this.isPilotProne()
                    && this.getCannonCharge() <= 0);
        }
    }

    public void pilotJump(ServerPlayer pilot)
    {
        if (this.getControllingPassenger() != pilot || !this.onGround() || this.jumpCooldown > 0
                || this.getCannonCharge() > 0)
        {
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
        this.setDeltaMovement(motion.x, JUMP_VELOCITY, motion.z);
        this.hasImpulse = true;
        this.jumpCooldown = JUMP_COOLDOWN_TICKS;
        this.playSound(SoundEvents.IRON_GOLEM_STEP, 2.2F, 0.65F);
    }

    public void exitEva(ServerPlayer pilot)
    {
        if (this.getControllingPassenger() == pilot)
        {
            pilot.stopRiding();
            if (this.isCrucified())
            {
                // Stepping out of a cross hundreds of blocks up.
                pilot.addEffect(new net.minecraft.world.effect.MobEffectInstance(
                        net.minecraft.world.effect.MobEffects.SLOW_FALLING, 20 * 60, 0));
            }
        }
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
        this.triggerAnim("strike", "cannon_fire");
        Vec3 from = pilot.getEyePosition();
        Vec3 dir = pilot.getLookAngle();
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

        // The shot itself detonates: positron rounds do not leave neat holes.
        level.explode(this, end.x, end.y, end.z,
                SeeleConfig.CANNON_EXPLOSION_RADIUS.get().floatValue(), Level.ExplosionInteraction.MOB);
        final Vec3 impact = end;

        // Muzzle roughly at the cannon barrel, right hand height.
        Vec3 muzzle = this.position()
                .add(this.getForward().scale(8.75D))
                .add(0.0D, 18.75D, 0.0D);
        SeeleNetwork.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> this),
                new ClientboundCannonBeamPacket(muzzle.x, muzzle.y, muzzle.z, end.x, end.y, end.z));
        SeeleNetwork.CHANNEL.send(PacketDistributor.NEAR.with(() -> new PacketDistributor.TargetPoint(
                        impact.x, impact.y, impact.z, 320.0D, level.dimension())),
                new ClientboundNukeFxPacket(impact.x, impact.y, impact.z, 5.4F, false));
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
        if (this.jumpCooldown > 0)
        {
            this.jumpCooldown--;
        }
        if (this.activationTicks > 0)
        {
            this.activationTicks--;
        }
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
            boolean evaMelee = source.getEntity() instanceof EvaUnit01Entity
                    && !source.is(DamageTypeTags.IS_EXPLOSION);
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
            if (!this.level().isClientSide)
            {
                player.startRiding(this);
                this.activationTicks = 120;
            }
            return InteractionResult.sidedSuccess(this.level().isClientSide);
        }
        return super.mobInteract(player, hand);
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
        if (this.isCrucified())
        {
            // Nailed to the Tree: no steering, no movement; V still ejects.
            return;
        }
        super.tickRidden(player, input);
        // The Unit turns with the pilot's view, horse-style.
        this.setRot(player.getYRot(), player.getXRot() * 0.5F);
        this.yRotO = this.yBodyRot = this.yHeadRot = this.getYRot();
        // The player renderer is cancelled client-side while mounted. Keep
        // the entity itself visible so Forge still fires first-person hand
        // rendering events for the dedicated cockpit arms.
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
    protected Vec3 getRiddenInput(Player player, Vec3 input)
    {
        if (this.activationTicks > 20)
        {
            return Vec3.ZERO;
        }
        double strafe = this.isPilotProne() ? 0.28D : this.isPilotCrouching() ? 0.45D : 0.7D;
        return new Vec3(player.xxa * strafe, 0.0D, player.zza >= 0.0F ? player.zza : player.zza * 0.6D);
    }

    @Override
    protected float getRiddenSpeed(Player player)
    {
        if (this.activationTicks > 20)
        {
            return 0.0F;
        }
        // Sniper stance: charging the cannon roots the Unit.
        if (this.getCannonCharge() > 0)
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
    }

    @Override
    protected void positionRider(Entity passenger, Entity.MoveFunction move)
    {
        if (!this.hasPassenger(passenger))
        {
            return;
        }
        // The pilot rides at head height: in first person the plug view IS
        // the Unit's own eyes (the airframe hides itself from its pilot).
        float rad = (float) Math.toRadians(this.yBodyRot);
        double behind = 0.35D;
        // The eye must clear the shoulder pylons: at 25.0 it sat level with
        // the chest rim and first person stared into the Unit's own back.
        // SmOd's head tops out higher than the placeholder skeleton's, so the
        // standing height is per-family.
        double standing = this.getUnitVariant() == UNIT_00 ? 25.4D : 27.2D;
        double plugHeight = this.isPilotProne() ? 10.5D : this.isPilotCrouching() ? 17.7D : standing;
        move.accept(passenger,
                this.getX() + Math.sin(rad) * behind,
                this.getY() + plugHeight,
                this.getZ() - Math.cos(rad) * behind);
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

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers)
    {
        controllers.add(new AnimationController<>(this, "base", 6, state ->
        {
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
        }));
        controllers.add(new AnimationController<>(this, "arms", 8, state ->
        {
            if (this.getWeapon() == WEAPON_CANNON
                    && !this.isPilotCrouching() && !this.isPilotProne())
            {
                return state.setAndContinue(ANIM_AIM);
            }
            return PlayState.STOP;
        }));
        controllers.add(new AnimationController<>(this, "strike", 3, state -> PlayState.STOP)
                .triggerableAnim("melee", ANIM_MELEE)
                .triggerableAnim("melee_left", ANIM_MELEE_LEFT)
                .triggerableAnim("knife", ANIM_KNIFE)
                .triggerableAnim("knife_left", ANIM_KNIFE_LEFT)
                .triggerableAnim("smash", ANIM_SMASH)
                .triggerableAnim("cannon_fire", ANIM_CANNON_FIRE)
                .triggerableAnim("land", ANIM_LAND)
                .triggerableAnim("stomp", ANIM_STOMP));
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
