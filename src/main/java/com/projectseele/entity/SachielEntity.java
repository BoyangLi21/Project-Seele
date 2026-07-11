package com.projectseele.entity;

import com.projectseele.fx.AtFieldFX;
import com.projectseele.fx.CrossExplosionFX;
import com.projectseele.network.ClientboundNukeFxPacket;
import com.projectseele.network.SeeleNetwork;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.world.entity.ai.goal.WaterAvoidingRandomStrollGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.Level.ExplosionInteraction;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.PacketDistributor;

/** Third Angel: a close-range giant that ends the fight with a cross-shaped self-destruction. */
public class SachielEntity extends Monster implements Angel
{
    private static final float AT_FIELD_MAX = 900.0F;
    private float atField = AT_FIELD_MAX;
    private int spearCooldown = 45;
    private int selfDestructTicks = -1;

    public SachielEntity(EntityType<? extends SachielEntity> type, Level level)
    {
        super(type, level);
        this.setMaxUpStep(2.0F);
    }

    public static AttributeSupplier.Builder createAttributes()
    {
        return Monster.createMonsterAttributes()
                .add(Attributes.MAX_HEALTH, 800.0D)
                .add(Attributes.ARMOR, 10.0D)
                .add(Attributes.MOVEMENT_SPEED, 0.28D)
                .add(Attributes.ATTACK_DAMAGE, 42.0D)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0D)
                .add(Attributes.FOLLOW_RANGE, 96.0D);
    }

    @Override
    protected void registerGoals()
    {
        this.goalSelector.addGoal(2, new MeleeAttackGoal(this, 1.0D, true));
        this.goalSelector.addGoal(7, new WaterAvoidingRandomStrollGoal(this, 0.65D));
        this.targetSelector.addGoal(1, new NearestAttackableTargetGoal<>(this, EvaUnit01Entity.class, true));
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, true));
    }

    @Override
    public void tick()
    {
        super.tick();
        if (this.level().isClientSide)
        {
            return;
        }
        if (this.selfDestructTicks >= 0)
        {
            this.setDeltaMovement(Vec3.ZERO);
            if (--this.selfDestructTicks <= 0)
            {
                selfDestruct();
            }
            return;
        }
        LivingEntity target = this.getTarget();
        if (target != null && target.isAlive() && --this.spearCooldown <= 0)
        {
            this.spearCooldown = 75;
            if (this.distanceToSqr(target) > 100.0D && this.distanceToSqr(target) < 3600.0D
                    && this.hasLineOfSight(target))
            {
                target.hurt(this.damageSources().mobAttack(this), 55.0F);
                target.push((target.getX() - this.getX()) * 0.12D, 0.55D,
                        (target.getZ() - this.getZ()) * 0.12D);
            }
        }
        if (this.getHealth() <= this.getMaxHealth() * 0.14F)
        {
            this.selfDestructTicks = 60;
        }
    }

    @Override
    public boolean hurt(DamageSource source, float amount)
    {
        if (this.selfDestructTicks >= 0)
        {
            return false;
        }
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
        if (amount >= this.getHealth())
        {
            this.setHealth(1.0F);
            this.selfDestructTicks = 45;
            return true;
        }
        return super.hurt(source, amount);
    }

    private void selfDestruct()
    {
        if (!(this.level() instanceof ServerLevel server))
        {
            return;
        }
        Vec3 center = this.position().add(0.0D, 8.0D, 0.0D);
        CrossExplosionFX.spawn(server, center, 2.2F);
        SeeleNetwork.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> this),
                new ClientboundNukeFxPacket(center.x, center.y, center.z, 3.2F, true));
        server.explode(this, this.getX(), this.getY() + 4.0D, this.getZ(), 16.0F, ExplosionInteraction.MOB);
        this.discard();
    }

    public float getAtField()
    {
        return this.atField;
    }
}
