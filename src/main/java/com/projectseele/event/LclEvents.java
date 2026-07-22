package com.projectseele.event;

import com.projectseele.ProjectSeele;
import com.projectseele.config.SeeleConfig;
import com.projectseele.registry.ModFluids;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.level.material.FluidState;
import net.minecraftforge.event.entity.item.ItemExpireEvent;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** LCL oxygenation, recovery and submerged-item preservation. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class LclEvents
{
    private static final int ITEM_LIFETIME_EXTENSION_TICKS = 20 * 10;

    private LclEvents() {}

    @SubscribeEvent
    public static void onLivingTick(LivingEvent.LivingTickEvent event)
    {
        LivingEntity living = event.getEntity();
        BlockPos eyes = BlockPos.containing(living.getEyePosition());
        FluidState fluid = living.level().getFluidState(eyes);
        double sampledEyeY = living.getEyeY() - 0.11111111D;
        double surfaceY = eyes.getY() + fluid.getHeight(living.level(), eyes);
        if (fluid.getFluidType() != ModFluids.LCL_TYPE.get()
                || surfaceY <= sampledEyeY)
        {
            return;
        }
        if (living.level() instanceof ServerLevel level)
        {
            living.setAirSupply(living.getMaxAirSupply());
            int interval = healIntervalTicks();
            double amount = healAmount();
            if (living instanceof ServerPlayer
                    && amount > 0.0D
                    && living.tickCount % interval == 0
                    && living.getHealth() < living.getMaxHealth())
            {
                living.heal((float) amount);
            }
            if (living.tickCount % 12 == 0)
            {
                level.sendParticles(ParticleTypes.BUBBLE_COLUMN_UP,
                        living.getX(), living.getEyeY() - 0.4D, living.getZ(),
                        3, 0.28D, 0.22D, 0.28D, 0.018D);
            }
        }
    }

    @SubscribeEvent
    public static void onItemExpire(ItemExpireEvent event)
    {
        ItemEntity item = event.getEntity();
        if (!itemsPersist() || !touchesLcl(item))
        {
            return;
        }

        // The vanilla expiry clock remains intact. Extending it in short
        // windows means an item cannot vanish in LCL, but resumes normal
        // expiry shortly after a player removes it from the fluid.
        event.setExtraLife(ITEM_LIFETIME_EXTENSION_TICKS);
        event.setCanceled(true);
    }

    private static boolean touchesLcl(ItemEntity item)
    {
        double[] samples = {
                item.getBoundingBox().minY - 0.04D,
                item.getBoundingBox().minY + 0.03D,
                item.getBoundingBox().maxY - 0.03D
        };
        for (double sampleY : samples)
        {
            BlockPos pos = BlockPos.containing(item.getX(), sampleY, item.getZ());
            FluidState fluid = item.level().getFluidState(pos);
            double surfaceY = pos.getY() + fluid.getHeight(item.level(), pos);
            if (fluid.getFluidType() == ModFluids.LCL_TYPE.get()
                    && surfaceY >= sampleY)
            {
                return true;
            }
        }
        return false;
    }

    private static int healIntervalTicks()
    {
        return SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.LCL_HEAL_INTERVAL_TICKS.get() : 40;
    }

    private static double healAmount()
    {
        return SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.LCL_HEAL_AMOUNT.get() : 1.0D;
    }

    private static boolean itemsPersist()
    {
        return !SeeleConfig.COMMON_SPEC.isLoaded()
                || SeeleConfig.LCL_ITEMS_PERSIST.get();
    }
}