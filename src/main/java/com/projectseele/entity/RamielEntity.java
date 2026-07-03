package com.projectseele.entity;

import java.util.EnumSet;
import java.util.Optional;

import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerBossEvent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.util.Mth;
import net.minecraft.world.BossEvent;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.FlyingMob;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.control.MoveControl;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;

/**
 * Ramiel, the Fifth Angel: a hovering crystalline octahedron that snipes its
 * target with a devastating energy beam after a telegraphed charge-up.
 */
public class RamielEntity extends FlyingMob implements Enemy
{
    private static final EntityDataAccessor<Boolean> DATA_CHARGING =
            SynchedEntityData.defineId(RamielEntity.class, EntityDataSerializers.BOOLEAN);

    private static final int CHARGE_TICKS = 50;
    private static final int BEAM_COOLDOWN_TICKS = 90;
    private static final double BEAM_RANGE = 64.0D;
    private static final float BEAM_DAMAGE = 18.0F;
    private static final DustParticleOptions CHARGE_DUST =
            new DustParticleOptions(new Vector3f(1.0F, 0.35F, 0.45F), 2.0F);

    private final ServerBossEvent bossEvent = new ServerBossEvent(
            this.getDisplayName(), BossEvent.BossBarColor.BLUE, BossEvent.BossBarOverlay.PROGRESS);

    private int beamCooldown = 60;

    // Client-side rotation state, interpolated by the renderer.
    private float spin;
    private float spinO;

    public RamielEntity(EntityType<? extends RamielEntity> type, Level level)
    {
        super(type, level);
        this.moveControl = new RamielMoveControl(this);
        this.xpReward = 500;
    }

    public static AttributeSupplier.Builder createAttributes()
    {
        return Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 350.0D)
                .add(Attributes.ARMOR, 6.0D)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0D)
                .add(Attributes.ATTACK_DAMAGE, 20.0D)
                .add(Attributes.FOLLOW_RANGE, 100.0D);
    }

    @Override
    protected void registerGoals()
    {
        this.goalSelector.addGoal(1, new BeamAttackGoal(this));
        this.goalSelector.addGoal(2, new HoverGoal(this));
        this.targetSelector.addGoal(1, new NearestAttackableTargetGoal<>(this, Player.class, false));
    }

    @Override
    protected void defineSynchedData()
    {
        super.defineSynchedData();
        this.entityData.define(DATA_CHARGING, false);
    }

    public boolean isCharging()
    {
        return this.entityData.get(DATA_CHARGING);
    }

    private void setCharging(boolean charging)
    {
        this.entityData.set(DATA_CHARGING, charging);
    }

    /** Interpolated body rotation in degrees; spins faster while charging. */
    public float getSpin(float partialTick)
    {
        return Mth.lerp(partialTick, this.spinO, this.spin);
    }

    @Override
    public void tick()
    {
        super.tick();
        if (this.level().isClientSide)
        {
            this.spinO = this.spin;
            this.spin += this.isCharging() ? 6.0F : 0.75F;
        }
    }

    @Override
    protected void customServerAiStep()
    {
        super.customServerAiStep();
        if (this.beamCooldown > 0)
        {
            this.beamCooldown--;
        }
        this.bossEvent.setProgress(this.getHealth() / this.getMaxHealth());
    }

    private Vec3 beamOrigin()
    {
        return this.position().add(0.0D, this.getBbHeight() * 0.5D, 0.0D);
    }

    private void fireBeam(LivingEntity target)
    {
        Vec3 from = this.beamOrigin();
        Vec3 dir = target.getEyePosition().subtract(from).normalize();
        Vec3 farEnd = from.add(dir.scale(BEAM_RANGE));
        BlockHitResult blockHit = this.level().clip(
                new ClipContext(from, farEnd, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, this));
        Vec3 end = blockHit.getLocation();

        for (LivingEntity victim : this.level().getEntitiesOfClass(LivingEntity.class,
                new AABB(from, end).inflate(1.0D), e -> e != this && e.isAlive()))
        {
            Optional<Vec3> hit = victim.getBoundingBox().inflate(0.3D).clip(from, end);
            if (hit.isPresent())
            {
                victim.hurt(this.damageSources().mobAttack(this), BEAM_DAMAGE);
            }
        }

        this.level().explode(this, end.x, end.y, end.z, 3.0F, Level.ExplosionInteraction.MOB);

        if (this.level() instanceof ServerLevel serverLevel)
        {
            double length = end.subtract(from).length();
            Vec3 step = dir.scale(1.5D);
            Vec3 pos = from;
            for (double d = 0.0D; d < length; d += 1.5D)
            {
                serverLevel.sendParticles(ParticleTypes.END_ROD, pos.x, pos.y, pos.z, 2, 0.15D, 0.15D, 0.15D, 0.0D);
                pos = pos.add(step);
            }
        }
        this.playSound(SoundEvents.WARDEN_SONIC_BOOM, 5.0F, 1.3F);
    }

    // ----- boss bar -----

    @Override
    public void startSeenByPlayer(ServerPlayer player)
    {
        super.startSeenByPlayer(player);
        this.bossEvent.addPlayer(player);
    }

    @Override
    public void stopSeenByPlayer(ServerPlayer player)
    {
        super.stopSeenByPlayer(player);
        this.bossEvent.removePlayer(player);
    }

    // ----- durability & presentation -----

    @Override
    public boolean removeWhenFarAway(double distance)
    {
        return false;
    }

    @Override
    public boolean isPushable()
    {
        return false;
    }

    @Override
    protected SoundEvent getAmbientSound()
    {
        return SoundEvents.BEACON_AMBIENT;
    }

    @Override
    protected SoundEvent getHurtSound(DamageSource source)
    {
        return SoundEvents.AMETHYST_BLOCK_HIT;
    }

    @Override
    protected SoundEvent getDeathSound()
    {
        return SoundEvents.GLASS_BREAK;
    }

    @Override
    protected float getSoundVolume()
    {
        return 4.0F;
    }

    // =====================================================================
    // AI
    // =====================================================================

    /** Ghast-style drift toward the wanted position; no pathfinding needed. */
    static class RamielMoveControl extends MoveControl
    {
        private final RamielEntity ramiel;
        private int recalcDelay;

        RamielMoveControl(RamielEntity ramiel)
        {
            super(ramiel);
            this.ramiel = ramiel;
        }

        @Override
        public void tick()
        {
            if (this.operation != Operation.MOVE_TO)
            {
                return;
            }
            if (this.recalcDelay-- > 0)
            {
                return;
            }
            this.recalcDelay = this.ramiel.getRandom().nextInt(5) + 2;
            Vec3 toWanted = new Vec3(this.wantedX - this.ramiel.getX(),
                    this.wantedY - this.ramiel.getY(),
                    this.wantedZ - this.ramiel.getZ());
            double distance = toWanted.length();
            if (distance < 2.0D)
            {
                this.ramiel.setDeltaMovement(this.ramiel.getDeltaMovement().scale(0.7D));
                this.operation = Operation.WAIT;
            }
            else
            {
                this.ramiel.setDeltaMovement(this.ramiel.getDeltaMovement()
                        .add(toWanted.scale(0.03D / distance)));
            }
        }
    }

    /** Keeps a high-altitude standoff position near the target, or bobs idly. */
    static class HoverGoal extends Goal
    {
        private final RamielEntity ramiel;

        HoverGoal(RamielEntity ramiel)
        {
            this.ramiel = ramiel;
            this.setFlags(EnumSet.of(Goal.Flag.MOVE));
        }

        @Override
        public boolean canUse()
        {
            return true;
        }

        @Override
        public boolean requiresUpdateEveryTick()
        {
            return true;
        }

        @Override
        public void tick()
        {
            LivingEntity target = this.ramiel.getTarget();
            MoveControl control = this.ramiel.getMoveControl();
            if (target != null && target.isAlive())
            {
                Vec3 away = this.ramiel.position().subtract(target.position());
                Vec3 flatAway = new Vec3(away.x, 0.0D, away.z);
                if (flatAway.lengthSqr() < 1.0E-4D)
                {
                    flatAway = new Vec3(1.0D, 0.0D, 0.0D);
                }
                Vec3 wanted = target.position()
                        .add(flatAway.normalize().scale(22.0D))
                        .add(0.0D, 16.0D, 0.0D);
                control.setWantedPosition(wanted.x, wanted.y, wanted.z, 1.0D);
            }
            else if (this.ramiel.getRandom().nextInt(60) == 0)
            {
                Vec3 pos = this.ramiel.position();
                control.setWantedPosition(
                        pos.x + (this.ramiel.getRandom().nextDouble() - 0.5D) * 10.0D,
                        pos.y + (this.ramiel.getRandom().nextDouble() - 0.5D) * 4.0D,
                        pos.z + (this.ramiel.getRandom().nextDouble() - 0.5D) * 10.0D,
                        1.0D);
            }
        }
    }

    /** Telegraphed charge-up followed by a hitscan beam and explosion. */
    static class BeamAttackGoal extends Goal
    {
        private final RamielEntity ramiel;
        private int chargeTicks;

        BeamAttackGoal(RamielEntity ramiel)
        {
            this.ramiel = ramiel;
            this.setFlags(EnumSet.of(Goal.Flag.LOOK));
        }

        @Override
        public boolean canUse()
        {
            LivingEntity target = this.ramiel.getTarget();
            return this.ramiel.beamCooldown <= 0
                    && target != null && target.isAlive()
                    && this.ramiel.distanceToSqr(target) < BEAM_RANGE * BEAM_RANGE
                    && this.ramiel.hasLineOfSight(target);
        }

        @Override
        public boolean canContinueToUse()
        {
            LivingEntity target = this.ramiel.getTarget();
            return this.chargeTicks > 0 && target != null && target.isAlive();
        }

        @Override
        public boolean requiresUpdateEveryTick()
        {
            return true;
        }

        @Override
        public void start()
        {
            this.chargeTicks = CHARGE_TICKS;
            this.ramiel.setCharging(true);
            this.ramiel.playSound(SoundEvents.END_PORTAL_SPAWN, 3.0F, 1.6F);
        }

        @Override
        public void stop()
        {
            this.ramiel.setCharging(false);
            this.ramiel.beamCooldown = BEAM_COOLDOWN_TICKS;
        }

        @Override
        public void tick()
        {
            LivingEntity target = this.ramiel.getTarget();
            if (target == null)
            {
                return;
            }
            this.ramiel.getLookControl().setLookAt(target, 30.0F, 30.0F);

            if (this.ramiel.level() instanceof ServerLevel serverLevel)
            {
                Vec3 core = this.ramiel.beamOrigin();
                serverLevel.sendParticles(CHARGE_DUST, core.x, core.y, core.z, 4, 1.6D, 1.6D, 1.6D, 0.0D);
            }

            if (--this.chargeTicks <= 0)
            {
                this.ramiel.fireBeam(target);
            }
        }
    }
}
