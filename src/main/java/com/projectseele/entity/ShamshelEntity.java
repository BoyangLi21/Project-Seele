package com.projectseele.entity;

import com.projectseele.fx.AtFieldFX;
import com.projectseele.fx.CrossExplosionFX;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/** Fourth Angel: low-hovering pursuit type with a pair of sweeping energy whips. */
public class ShamshelEntity extends Monster implements Angel
{
    private float atField = 700.0F;
    private int sweepCooldown = 30;

    public ShamshelEntity(EntityType<? extends ShamshelEntity> type, Level level)
    {
        super(type, level);
        this.setNoGravity(true);
    }

    public static AttributeSupplier.Builder createAttributes()
    {
        return Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 620.0D)
                .add(Attributes.ARMOR, 7.0D)
                .add(Attributes.ATTACK_DAMAGE, 30.0D)
                .add(Attributes.MOVEMENT_SPEED, 0.34D)
                .add(Attributes.FLYING_SPEED, 0.38D)
                .add(Attributes.FOLLOW_RANGE, 96.0D)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0D);
    }

    @Override
    protected void registerGoals()
    {
        this.targetSelector.addGoal(1, new NearestAttackableTargetGoal<>(this, EvaUnit01Entity.class, true));
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, true));
    }

    @Override
    public void tick()
    {
        super.tick();
        this.setNoGravity(true);
        LivingEntity target = this.getTarget();
        if (target == null || !target.isAlive())
        {
            this.setDeltaMovement(this.getDeltaMovement().scale(0.85D).add(0.0D,
                    Math.sin(this.tickCount * 0.08D) * 0.006D, 0.0D));
            return;
        }
        Vec3 aim = target.getBoundingBox().getCenter().subtract(this.position().add(0.0D, 6.0D, 0.0D));
        double distance = aim.length();
        if (distance > 12.0D)
        {
            this.setDeltaMovement(this.getDeltaMovement().scale(0.70D).add(aim.normalize().scale(0.10D)));
        }
        if (!this.level().isClientSide && distance < 28.0D && --this.sweepCooldown <= 0)
        {
            this.sweepCooldown = 34;
            Vec3 center = this.position().add(aim.normalize().scale(10.0D)).add(0.0D, 6.0D, 0.0D);
            AABB sweep = new AABB(center, center).inflate(13.0D, 7.0D, 13.0D);
            for (LivingEntity victim : this.level().getEntitiesOfClass(LivingEntity.class, sweep,
                    e -> e != this && (e instanceof EvaUnit01Entity || e instanceof Player)))
            {
                victim.hurt(this.damageSources().mobAttack(this), 30.0F);
                Vec3 push = victim.position().subtract(this.position()).normalize().scale(1.4D);
                victim.push(push.x, 0.45D, push.z);
            }
        }
    }

    @Override
    public boolean hurt(DamageSource source, float amount)
    {
        if (this.atField > 0.0F)
        {
            if (source.getEntity() instanceof EvaUnit01Entity eva
                    && eva.getWeapon() != EvaUnit01Entity.WEAPON_CANNON)
            {
                this.atField = Math.max(0.0F, this.atField - amount);
                if (this.level() instanceof ServerLevel server)
                {
                    AtFieldFX.ripple(server, this.getBoundingBox().getCenter(), eva.getForward());
                }
                return true;
            }
            return false;
        }
        return super.hurt(source, amount);
    }

    @Override
    public void die(DamageSource source)
    {
        if (this.level() instanceof ServerLevel server)
        {
            CrossExplosionFX.spawn(server, this.position(), 1.25F);
        }
        super.die(source);
    }
}
