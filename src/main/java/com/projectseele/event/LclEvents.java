package com.projectseele.event;

import com.projectseele.ProjectSeele;
import com.projectseele.registry.ModFluids;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.material.FluidState;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** LCL oxygenation and restrained suspension particles. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class LclEvents
{
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
            if (living.tickCount % 12 == 0)
            {
                level.sendParticles(ParticleTypes.BUBBLE_COLUMN_UP,
                        living.getX(), living.getEyeY() - 0.4D, living.getZ(),
                        3, 0.28D, 0.22D, 0.28D, 0.018D);
            }
        }
    }
}
