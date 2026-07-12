package com.projectseele.entity;

import com.projectseele.fx.CrossExplosionFX;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

/** White SEELE mass-production unit. It revives until an EVA knife destroys its exposed core. */
public class MassProductionEvaEntity extends Monster implements GeoEntity
{
    private static final RawAnimation ANIM_IDLE = RawAnimation.begin().thenLoop("animation.entity_mp.idle_1");
    private static final RawAnimation ANIM_WALK = RawAnimation.begin().thenLoop("animation.entity_mp.move");
    private static final RawAnimation ANIM_RITUAL = RawAnimation.begin().thenLoop("animation.entity_mp.ritual");
    private static final RawAnimation ANIM_ATTACK = RawAnimation.begin().thenPlay("animation.entity_mp.attack");
    private final AnimatableInstanceCache geoCache = GeckoLibUtil.createInstanceCache(this);
    private int reviveTicks;
    private boolean coreBroken;
    private int attackCooldown;

    public MassProductionEvaEntity(EntityType<? extends MassProductionEvaEntity> type, Level level)
    {
        super(type, level);
        this.setNoGravity(true);
        this.setMaxUpStep(2.5F);
    }

    public static AttributeSupplier.Builder createAttributes()
    {
        return Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 420.0D)
                .add(Attributes.ARMOR, 12.0D)
                .add(Attributes.ATTACK_DAMAGE, 34.0D)
                .add(Attributes.MOVEMENT_SPEED, 0.32D)
                .add(Attributes.FLYING_SPEED, 0.40D)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0D)
                .add(Attributes.FOLLOW_RANGE, 128.0D);
    }

    @Override
    protected void registerGoals()
    {
        this.targetSelector.addGoal(1, new NearestAttackableTargetGoal<>(this, EvaUnit01Entity.class, true));
    }

    @Override
    public void tick()
    {
        super.tick();
        this.setNoGravity(true);
        if (this.reviveTicks > 0)
        {
            this.setDeltaMovement(Vec3.ZERO);
            if (--this.reviveTicks == 0)
            {
                this.setHealth(this.getMaxHealth());
                if (this.level() instanceof ServerLevel server)
                {
                    CrossExplosionFX.spawn(server, this.position(), 0.22F);
                }
            }
            return;
        }
        LivingEntity target = this.getTarget();
        if (target == null || !target.isAlive())
        {
            return;
        }
        Vec3 delta = target.getBoundingBox().getCenter().subtract(this.position().add(0.0D, 9.0D, 0.0D));
        double distance = delta.length();
        if (distance > 7.0D)
        {
            this.setDeltaMovement(this.getDeltaMovement().scale(0.72D)
                    .add(delta.normalize().scale(distance > 30.0D ? 0.12D : 0.07D)));
        }
        if (distance < 12.0D && --this.attackCooldown <= 0)
        {
            this.attackCooldown = 24;
            this.swing(InteractionHand.MAIN_HAND, true);
            this.triggerAnim("strike", "attack");
            target.hurt(this.damageSources().mobAttack(this), 34.0F);
            target.push(delta.x * 0.05D, 0.3D, delta.z * 0.05D);
        }
    }

    @Override
    public boolean hurt(DamageSource source, float amount)
    {
        if (this.reviveTicks > 0)
        {
            return false;
        }
        if (source.getEntity() instanceof EvaUnit01Entity eva
                && (eva.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE
                    || eva.getWeapon() == EvaUnit01Entity.WEAPON_LANCE)
                && this.getHealth() <= this.getMaxHealth() * 0.28F)
        {
            this.coreBroken = true;
        }
        if (!this.coreBroken && amount >= this.getHealth())
        {
            this.setHealth(1.0F);
            this.reviveTicks = 120;
            return true;
        }
        return super.hurt(source, amount);
    }

    public boolean isReviving()
    {
        return this.reviveTicks > 0;
    }

    /** Inert vessels parked on the Sephirot during the Third Impact tableau. */
    public boolean isRitualFormation()
    {
        return this.isNoAi() && this.isNoGravity();
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers)
    {
        controllers.add(new AnimationController<>(this, "base", 6, state ->
        {
            if (this.isRitualFormation())
            {
                return state.setAndContinue(ANIM_RITUAL);
            }
            return state.setAndContinue(state.isMoving() ? ANIM_WALK : ANIM_IDLE);
        }));
        controllers.add(new AnimationController<>(this, "strike", 2, state -> PlayState.STOP)
                .triggerableAnim("attack", ANIM_ATTACK));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache()
    {
        return this.geoCache;
    }
}
