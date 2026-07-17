package com.projectseele.registry;

import com.projectseele.ProjectSeele;
import com.projectseele.world.RetractableBuildingCoreBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LiquidBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

/** Blocks used by Project SEELE structures and map systems. */
public final class ModBlocks
{
    public static final DeferredRegister<Block> BLOCKS = DeferredRegister.create(
            ForgeRegistries.BLOCKS, ProjectSeele.MODID);

    public static final RegistryObject<Block> RETRACTABLE_BUILDING_CORE = BLOCKS.register(
            "retractable_building_core",
            () -> new RetractableBuildingCoreBlock(BlockBehaviour.Properties.copy(
                    Blocks.POLISHED_DEEPSLATE).strength(8.0F, 1200.0F)
                    .lightLevel(state -> state.getValue(
                            RetractableBuildingCoreBlock.ARMED) ? 10 : 3)));

    public static final RegistryObject<LiquidBlock> LCL_BLOCK = BLOCKS.register(
            "lcl",
            () -> new LiquidBlock(ModFluids.LCL_SOURCE,
                    BlockBehaviour.Properties.copy(Blocks.WATER)
                            .lightLevel(state -> 4).noLootTable()));

    private ModBlocks() {}
}
