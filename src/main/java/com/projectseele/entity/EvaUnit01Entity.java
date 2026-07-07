package com.projectseele.entity;

import com.projectseele.config.SeeleConfig;
import com.projectseele.fx.AtFieldFX;
import com.projectseele.network.ClientboundCannonBeamPacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.registry.ModSounds;
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
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.PathfinderMob;
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
 * EVA Unit-01: rideable 12-block war machine and the pilot's body in every
 * Angel fight. Carries its own weapon state (fists / prog knife / positron
 * sniper cannon), an A.T. Field shield pool, and survives exactly two Ramiel
 * beams. All pilot input arrives via {@code ServerboundEvaControlPacket}.
 */
public class EvaUnit01Entity extends PathfinderMob implements GeoEntity
{
    public static final int WEAPON_FISTS = 0;
    public static final int WEAPON_KNIFE = 1;
    public static final int WEAPON_CANNON = 2;

    private static final float MELEE_FIST_DAMAGE = 20.0F;
    private static final float MELEE_KNIFE_DAMAGE = 60.0F;
    private static final int MELEE_COOLDOWN_TICKS = 12;
    // Reach geometry for the doubled 24-block frame.
    private static final double MELEE_REACH = 8.0D;
    private static final double MELEE_RADIUS = 6.0D;
    // Smash: crouch + attack. Slow, heavy, area knockdown.
    private static final float SMASH_FIST_DAMAGE = 35.0F;
    private static final float SMASH_KNIFE_DAMAGE = 80.0F;
    private static final int SMASH_COOLDOWN_TICKS = 60;
    private static final double SMASH_RADIUS = 9.0D;
    private static final float AT_FIELD_MAX = 200.0F;
    private static final float AT_FIELD_REGEN = 0.4F;
    private static final int AT_FIELD_REGEN_DELAY = 100;
    private static final float AT_FIELD_MIN_TO_RAISE = 20.0F;

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

    private static final RawAnimation ANIM_IDLE = RawAnimation.begin().thenLoop("animation.eva_unit01.idle");
    private static final RawAnimation ANIM_WALK = RawAnimation.begin().thenLoop("animation.eva_unit01.walk");
    private static final RawAnimation ANIM_AIM = RawAnimation.begin().thenLoop("animation.eva_unit01.aim");
    private static final RawAnimation ANIM_MELEE = RawAnimation.begin().thenPlay("animation.eva_unit01.melee");
    private static final RawAnimation ANIM_MELEE_LEFT = RawAnimation.begin().thenPlay("animation.eva_unit01.melee_left");
    private static final RawAnimation ANIM_SMASH = RawAnimation.begin().thenPlay("animation.eva_unit01.smash");

    private final AnimatableInstanceCache geoCache = GeckoLibUtil.createInstanceCache(this);

    private boolean chargingHeld;
    private int meleeCooldown;
    private int smashCooldown;
    private boolean leftSwing;
    private int atRegenDelay;

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
        return super.finalizeSpawn(level, difficulty, reason, spawnData, dataTag);
    }

    // ----- state accessors -----

    public int getWeapon()
    {
        return this.entityData.get(DATA_WEAPON);
    }

    public boolean isAtFieldOn()
    {
        return this.entityData.get(DATA_AT_ON);
    }

    public float getAtFieldEnergy()
    {
        return this.entityData.get(DATA_AT_ENERGY);
    }

    public static float getAtFieldMax()
    {
        return AT_FIELD_MAX;
    }

    public int getCannonCharge()
    {
        return this.entityData.get(DATA_CANNON_CHARGE);
    }

    public int getCannonCooldown()
    {
        return this.entityData.get(DATA_CANNON_COOLDOWN);
    }

    // ----- pilot commands (validated by the packet handler) -----

    public void cycleWeapon(ServerPlayer pilot)
    {
        int next = (this.getWeapon() + 1) % 3;
        this.entityData.set(DATA_WEAPON, next);
        this.entityData.set(DATA_CANNON_CHARGE, 0);
        this.chargingHeld = false;
        String key = switch (next)
        {
            case WEAPON_KNIFE -> "msg.projectseele.weapon_knife";
            case WEAPON_CANNON -> "msg.projectseele.weapon_cannon";
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
            Vec3 front = this.position().add(this.getForward().scale(6.0D)).add(0.0D, 12.0D, 0.0D);
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
        if (this.meleeCooldown > 0 || this.getWeapon() == WEAPON_CANNON)
        {
            return;
        }
        this.meleeCooldown = MELEE_COOLDOWN_TICKS;
        this.leftSwing = !this.leftSwing;
        this.triggerAnim("strike", this.leftSwing ? "melee_left" : "melee");

        boolean knife = this.getWeapon() == WEAPON_KNIFE;
        float damage = knife ? MELEE_KNIFE_DAMAGE : MELEE_FIST_DAMAGE;
        Vec3 forward = this.getForward().multiply(1.0D, 0.0D, 1.0D).normalize();
        Vec3 center = this.position().add(forward.scale(MELEE_REACH)).add(0.0D, 11.0D, 0.0D);
        AABB zone = new AABB(center, center).inflate(MELEE_RADIUS, 8.0D, MELEE_RADIUS);
        this.strikeZone(pilot, zone, damage, 1.1D, center);
        this.playSound(knife ? SoundEvents.PLAYER_ATTACK_SWEEP : SoundEvents.IRON_GOLEM_ATTACK, 2.5F,
                knife ? 0.7F : 0.8F);
    }

    /** Crouch + attack: a slow two-handed slam that flattens the area ahead. */
    public void smashAttack(ServerPlayer pilot)
    {
        if (this.smashCooldown > 0 || this.getWeapon() == WEAPON_CANNON)
        {
            return;
        }
        this.smashCooldown = SMASH_COOLDOWN_TICKS;
        this.triggerAnim("strike", "smash");

        boolean knife = this.getWeapon() == WEAPON_KNIFE;
        float damage = knife ? SMASH_KNIFE_DAMAGE : SMASH_FIST_DAMAGE;
        Vec3 forward = this.getForward().multiply(1.0D, 0.0D, 1.0D).normalize();
        Vec3 center = this.position().add(forward.scale(MELEE_REACH + 1.0D)).add(0.0D, 4.0D, 0.0D);
        AABB zone = new AABB(center, center).inflate(SMASH_RADIUS, 7.0D, SMASH_RADIUS);
        this.strikeZone(pilot, zone, damage, 2.0D, center);
        if (this.level() instanceof ServerLevel serverLevel)
        {
            serverLevel.sendParticles(ParticleTypes.EXPLOSION,
                    center.x, center.y - 2.0D, center.z, 10, 3.5D, 0.6D, 3.5D, 0.0D);
        }
        this.playSound(SoundEvents.IRON_GOLEM_DEATH, 3.0F, 0.55F);
    }

    private void strikeZone(ServerPlayer pilot, AABB zone, float damage, double knockback, Vec3 fxCenter)
    {
        if (!(this.level() instanceof ServerLevel serverLevel))
        {
            return;
        }
        for (LivingEntity target : serverLevel.getEntitiesOfClass(LivingEntity.class, zone,
                e -> e != this && e != pilot && !this.hasPassenger(e) && e.isAlive()))
        {
            // Damage sourced directly from the Unit: Angel A.T. Fields
            // treat EVA contact as neutralized and let it through.
            target.hurt(this.damageSources().mobAttack(this), damage);
            target.knockback(knockback, this.getX() - target.getX(), this.getZ() - target.getZ());
        }
        serverLevel.sendParticles(ParticleTypes.SWEEP_ATTACK,
                fxCenter.x, fxCenter.y, fxCenter.z, 6, 1.6D, 1.2D, 1.6D, 0.0D);
    }

    /** Use-key released: fire if fully charged, otherwise just power down. */
    public void releaseCannon(ServerPlayer pilot)
    {
        this.chargingHeld = false;
        boolean full = this.getCannonCharge() >= SeeleConfig.CANNON_CHARGE_TICKS.get();
        this.entityData.set(DATA_CANNON_CHARGE, 0);
        if (!full || this.getWeapon() != WEAPON_CANNON || this.getCannonCooldown() > 0)
        {
            return;
        }
        this.entityData.set(DATA_CANNON_COOLDOWN, SeeleConfig.CANNON_COOLDOWN_TICKS.get());
        if (this.level() instanceof ServerLevel serverLevel)
        {
            this.fireCannon(serverLevel, pilot);
        }
    }

    private void fireCannon(ServerLevel level, ServerPlayer pilot)
    {
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

        // Muzzle roughly at the cannon barrel, right hand height.
        Vec3 muzzle = this.position()
                .add(this.getForward().scale(7.0D))
                .add(0.0D, 15.0D, 0.0D);
        SeeleNetwork.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> this),
                new ClientboundCannonBeamPacket(muzzle.x, muzzle.y, muzzle.z, end.x, end.y, end.z));
        level.sendParticles(ParticleTypes.END_ROD, end.x, end.y, end.z, 30, 0.5D, 0.5D, 0.5D, 0.2D);
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
        else if (this.getAtFieldEnergy() < AT_FIELD_MAX)
        {
            this.entityData.set(DATA_AT_ENERGY,
                    Math.min(AT_FIELD_MAX, this.getAtFieldEnergy() + AT_FIELD_REGEN));
        }
        if (this.isAtFieldOn() && this.getAtFieldEnergy() <= 0.0F)
        {
            this.entityData.set(DATA_AT_ON, false);
            this.playSound(ModSounds.CRYSTAL_BREAK.get(), 2.0F, 1.2F);
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
        if (this.isAtFieldOn() && amount > 0.0F)
        {
            this.atRegenDelay = AT_FIELD_REGEN_DELAY;
            if (source.getEntity() instanceof Angel)
            {
                float energy = this.getAtFieldEnergy();
                float absorbed = Math.min(energy, amount);
                this.entityData.set(DATA_AT_ENERGY, energy - absorbed);
                this.rippleAt(source);
                float leftover = amount - absorbed;
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
        AtFieldFX.ripple(serverLevel, center.add(dir.scale(6.4D)), dir);
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
        super.tickRidden(player, input);
        // The Unit turns with the pilot's view, horse-style.
        this.setRot(player.getYRot(), player.getXRot() * 0.5F);
        this.yRotO = this.yBodyRot = this.yHeadRot = this.getYRot();
        // The pilot is sealed inside the entry plug — nobody sees them.
        if (!player.isInvisible())
        {
            player.setInvisible(true);
        }
    }

    @Override
    protected void removePassenger(Entity passenger)
    {
        super.removePassenger(passenger);
        if (passenger instanceof Player player)
        {
            player.setInvisible(false);
        }
    }

    @Override
    protected Vec3 getRiddenInput(Player player, Vec3 input)
    {
        return new Vec3(player.xxa * 0.7D, 0.0D, player.zza >= 0.0F ? player.zza : player.zza * 0.6D);
    }

    @Override
    protected float getRiddenSpeed(Player player)
    {
        // Sniper stance: charging the cannon roots the Unit.
        if (this.getCannonCharge() > 0)
        {
            return 0.02F;
        }
        return (float) this.getAttributeValue(Attributes.MOVEMENT_SPEED);
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
        move.accept(passenger,
                this.getX() + Math.sin(rad) * behind,
                this.getY() + 20.0D,
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
                state.setAndContinue(state.isMoving() ? ANIM_WALK : ANIM_IDLE)));
        controllers.add(new AnimationController<>(this, "arms", 8, state ->
        {
            if (this.getWeapon() == WEAPON_CANNON)
            {
                return state.setAndContinue(ANIM_AIM);
            }
            return PlayState.STOP;
        }));
        controllers.add(new AnimationController<>(this, "strike", 3, state -> PlayState.STOP)
                .triggerableAnim("melee", ANIM_MELEE)
                .triggerableAnim("melee_left", ANIM_MELEE_LEFT)
                .triggerableAnim("smash", ANIM_SMASH));
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
