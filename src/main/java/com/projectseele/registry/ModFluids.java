package com.projectseele.registry;

import com.projectseele.ProjectSeele;
import com.projectseele.fluid.LclFluidType;
import net.minecraft.world.level.material.FlowingFluid;
import net.minecraft.world.level.material.Fluid;
import net.minecraftforge.fluids.FluidType;
import net.minecraftforge.fluids.ForgeFlowingFluid;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

/** Independent facility fluids; never replaces vanilla water textures or tags. */
public final class ModFluids
{
    public static final DeferredRegister<FluidType> FLUID_TYPES = DeferredRegister.create(
            ForgeRegistries.Keys.FLUID_TYPES, ProjectSeele.MODID);
    public static final DeferredRegister<Fluid> FLUIDS = DeferredRegister.create(
            ForgeRegistries.FLUIDS, ProjectSeele.MODID);

    public static final RegistryObject<FluidType> LCL_TYPE = FLUID_TYPES.register(
            "lcl", LclFluidType::new);
    public static final RegistryObject<FlowingFluid> LCL_SOURCE = FLUIDS.register(
            "lcl", () -> new ForgeFlowingFluid.Source(properties()));
    public static final RegistryObject<FlowingFluid> FLOWING_LCL = FLUIDS.register(
            "flowing_lcl", () -> new ForgeFlowingFluid.Flowing(properties()));

    private ModFluids() {}

    private static ForgeFlowingFluid.Properties properties()
    {
        return new ForgeFlowingFluid.Properties(LCL_TYPE, LCL_SOURCE, FLOWING_LCL)
                .block(ModBlocks.LCL_BLOCK)
                .slopeFindDistance(4)
                .levelDecreasePerBlock(1)
                .tickRate(5)
                .explosionResistance(100.0F);
    }
}
