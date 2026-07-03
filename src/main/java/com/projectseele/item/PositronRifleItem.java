package com.projectseele.item;

import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.stats.Stats;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.ProjectileUtil;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;

/**
 * Hitscan energy rifle: the player's only anti-Angel weapon until EVA units
 * arrive in Phase 2.
 */
public class PositronRifleItem extends Item
{
    private static final double RANGE = 96.0D;
    private static final float DAMAGE = 16.0F;
    private static final int COOLDOWN_TICKS = 25;

    public PositronRifleItem(Properties properties)
    {
        super(properties);
    }

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand)
    {
        ItemStack stack = player.getItemInHand(hand);
        player.getCooldowns().addCooldown(this, COOLDOWN_TICKS);
        level.playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.BEACON_DEACTIVATE, SoundSource.PLAYERS, 1.5F, 1.7F);
        if (level instanceof ServerLevel serverLevel)
        {
            this.fire(serverLevel, player);
        }
        player.awardStat(Stats.ITEM_USED.get(this));
        return InteractionResultHolder.sidedSuccess(stack, level.isClientSide());
    }

    private void fire(ServerLevel level, Player player)
    {
        Vec3 from = player.getEyePosition();
        Vec3 dir = player.getLookAngle();
        Vec3 farEnd = from.add(dir.scale(RANGE));
        BlockHitResult blockHit = level.clip(
                new ClipContext(from, farEnd, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, player));
        Vec3 end = blockHit.getLocation();

        EntityHitResult entityHit = ProjectileUtil.getEntityHitResult(level, player, from, end,
                new AABB(from, end).inflate(1.0D),
                e -> e instanceof LivingEntity && e != player && !e.isSpectator() && e.isAlive());
        if (entityHit != null)
        {
            end = entityHit.getLocation();
            entityHit.getEntity().hurt(player.damageSources().playerAttack(player), DAMAGE);
        }

        Vec3 step = dir.scale(1.2D);
        Vec3 pos = from.add(dir.scale(1.5D)); // start clear of the muzzle
        double length = end.subtract(from).length();
        for (double d = 1.5D; d < length; d += 1.2D)
        {
            level.sendParticles(ParticleTypes.ELECTRIC_SPARK, pos.x, pos.y, pos.z, 1, 0.02D, 0.02D, 0.02D, 0.0D);
            pos = pos.add(step);
        }
        level.sendParticles(ParticleTypes.ELECTRIC_SPARK, end.x, end.y, end.z, 12, 0.25D, 0.25D, 0.25D, 0.05D);
    }
}
