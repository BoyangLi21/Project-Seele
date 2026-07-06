package com.projectseele.item;

import com.projectseele.config.SeeleConfig;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.RamielEntity;
import com.projectseele.network.ClientboundCannonBeamPacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.registry.ModSounds;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundSource;
import net.minecraft.stats.Stats;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.ProjectileUtil;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.UseAnim;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.PacketDistributor;

/**
 * The Operation-Yashima weapon: an EVA-scale positron sniper cannon. Only
 * fires from the entry plug (riding Unit-01). Hold to charge, release to
 * fire a hitscan shot across the map; hitting an exposed Angel core is an
 * instant kill, anything else just ripples off the A.T. Field.
 */
public class PositronCannonItem extends Item
{
    /** Damage that ends any Angel once the core is bared. */
    private static final float CORE_KILL_DAMAGE = 99999.0F;

    public PositronCannonItem(Properties properties)
    {
        super(properties);
    }

    public static boolean isPiloting(LivingEntity shooter)
    {
        return shooter.getVehicle() instanceof EvaUnit01Entity;
    }

    /** Charge progress 0..1 for HUD and FOV. */
    public static float chargeProgress(LivingEntity user)
    {
        if (!(user.getUseItem().getItem() instanceof PositronCannonItem))
        {
            return 0.0F;
        }
        int used = user.getTicksUsingItem();
        return Math.min(1.0F, used / (float) SeeleConfig.CANNON_CHARGE_TICKS.get());
    }

    @Override
    public int getUseDuration(ItemStack stack)
    {
        return 72000;
    }

    @Override
    public UseAnim getUseAnimation(ItemStack stack)
    {
        return UseAnim.BOW;
    }

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand)
    {
        ItemStack stack = player.getItemInHand(hand);
        if (!isPiloting(player))
        {
            if (!level.isClientSide)
            {
                player.displayClientMessage(
                        Component.translatable("msg.projectseele.cannon_requires_eva"), true);
            }
            return InteractionResultHolder.fail(stack);
        }
        player.startUsingItem(hand);
        level.playSound(null, player.getX(), player.getY(), player.getZ(),
                ModSounds.BEAM_CHARGE.get(), SoundSource.PLAYERS, 1.6F, 1.2F);
        return InteractionResultHolder.consume(stack);
    }

    @Override
    public void releaseUsing(ItemStack stack, Level level, LivingEntity entity, int remainingTicks)
    {
        if (!(entity instanceof Player player))
        {
            return;
        }
        boolean charged = this.getUseDuration(stack) - remainingTicks >= SeeleConfig.CANNON_CHARGE_TICKS.get();
        if (!charged || !isPiloting(player))
        {
            return;
        }
        player.getCooldowns().addCooldown(this, SeeleConfig.CANNON_COOLDOWN_TICKS.get());
        if (level instanceof ServerLevel serverLevel)
        {
            this.fire(serverLevel, player);
            player.awardStat(Stats.ITEM_USED.get(this));
        }
    }

    private void fire(ServerLevel level, Player player)
    {
        Vec3 from = player.getEyePosition();
        Vec3 dir = player.getLookAngle();
        double range = SeeleConfig.CANNON_RANGE.get();
        Vec3 farEnd = from.add(dir.scale(range));
        BlockHitResult blockHit = level.clip(
                new ClipContext(from, farEnd, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, player));
        Vec3 end = blockHit.getLocation();

        EntityHitResult entityHit = ProjectileUtil.getEntityHitResult(level, player, from, end,
                new AABB(from, end).inflate(1.0D),
                e -> e instanceof LivingEntity && e != player && e != player.getVehicle()
                        && !e.isSpectator() && e.isAlive());

        if (entityHit != null)
        {
            end = entityHit.getLocation();
            if (entityHit.getEntity() instanceof RamielEntity ramiel)
            {
                if (ramiel.isCoreHit(end))
                {
                    // The Yashima shot: straight through the bared core.
                    ramiel.hurt(player.damageSources().playerAttack(player), CORE_KILL_DAMAGE);
                }
                else
                {
                    // Sealed shell (or a miss off the core): the field answers.
                    ramiel.hurt(player.damageSources().playerAttack(player),
                            SeeleConfig.CANNON_MOB_DAMAGE.get().floatValue());
                }
            }
            else
            {
                entityHit.getEntity().hurt(player.damageSources().playerAttack(player),
                        SeeleConfig.CANNON_MOB_DAMAGE.get().floatValue());
            }
        }

        // Muzzle sits ahead of the plug so the flash never blinds the pilot.
        Vec3 muzzle = from.add(dir.scale(2.5D)).add(0.0D, -0.4D, 0.0D);
        SeeleNetwork.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> player),
                new ClientboundCannonBeamPacket(muzzle.x, muzzle.y, muzzle.z, end.x, end.y, end.z));
        level.sendParticles(ParticleTypes.END_ROD, end.x, end.y, end.z, 30, 0.5D, 0.5D, 0.5D, 0.2D);
        level.playSound(null, player.getX(), player.getY(), player.getZ(),
                ModSounds.BEAM_FIRE.get(), SoundSource.PLAYERS, 4.0F, 1.25F);
    }
}
