package com.projectseele.registry;

import com.projectseele.ProjectSeele;
import com.projectseele.world.CommandSeatBackBlock;
import com.projectseele.world.OneWayGlassBlock;
import com.projectseele.world.RetractableBuildingCoreBlock;
import com.projectseele.world.UmbilicalPylonBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.GlassBlock;
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

    public static final RegistryObject<Block> UMBILICAL_PYLON = BLOCKS.register(
            "umbilical_pylon",
            () -> new UmbilicalPylonBlock(BlockBehaviour.Properties.copy(
                    Blocks.POLISHED_DEEPSLATE).strength(8.0F, 1200.0F)
                    .lightLevel(state -> 6).noOcclusion()));

    /** Scratch-free structural glazing for command-room sight lines. */
    public static final RegistryObject<Block> CLEAR_GLASS = BLOCKS.register(
            "clear_glass",
            () -> new GlassBlock(BlockBehaviour.Properties.copy(Blocks.GLASS)
                    .strength(1.2F, 8.0F).noOcclusion()
                    .isValidSpawn((state, level, position, type) -> false)
                    .isRedstoneConductor((state, level, position) -> false)
                    .isSuffocating((state, level, position) -> false)
                    .isViewBlocking((state, level, position) -> false)));

    /** Commander-office glazing: clear inward, pyramid skin outward. */
    public static final RegistryObject<Block> ONE_WAY_GLASS = BLOCKS.register(
            "one_way_glass",
            () -> new OneWayGlassBlock(
                    BlockBehaviour.Properties.copy(Blocks.GLASS)
                            .strength(2.0F, 12.0F).noOcclusion()
                            .isValidSpawn((state, level, position, type) -> false)
                            .isRedstoneConductor((state, level, position) -> false)
                            .isSuffocating((state, level, position) -> false)
                            .isViewBlocking((state, level, position) -> false)));

    /**
     * Non-ticking GeoFront equivalent of Ars Nouveau Skyweave. The Ars block
     * creates one animated block entity per voxel; a 640-diameter sphere has
     * over 1.8 million shell voxels, so the original material is not viable.
     */
    public static final RegistryObject<Block> GEOFRONT_SKYWEAVE = BLOCKS.register(
            "geofront_skyweave",
            () -> new GlassBlock(BlockBehaviour.Properties.copy(Blocks.GLASS)
                    .strength(4.0F, 30.0F).lightLevel(state -> 4)
                    .noOcclusion()
                    .isValidSpawn((state, level, position, type) -> false)
                    .isRedstoneConductor((state, level, position) -> false)
                    .isSuffocating((state, level, position) -> false)
                    .isViewBlocking((state, level, position) -> false)));

    /**
     * Inert two-block command-chair backrest.  Replaces the iron trapdoors the
     * command dais used to lean on, which every redstone pulse in the console
     * bank swung open.
     */
    public static final RegistryObject<Block> COMMAND_SEAT_BACK = BLOCKS.register(
            "command_seat_back",
            () -> new CommandSeatBackBlock(BlockBehaviour.Properties.copy(
                    Blocks.POLISHED_DEEPSLATE).strength(2.0F, 12.0F)
                    .noOcclusion()
                    .isRedstoneConductor((state, level, position) -> false)
                    .isSuffocating((state, level, position) -> false)
                    .isViewBlocking((state, level, position) -> false)));

    public static final RegistryObject<LiquidBlock> LCL_BLOCK = BLOCKS.register(
            "lcl",
            () -> new LiquidBlock(ModFluids.LCL_SOURCE,
                    BlockBehaviour.Properties.copy(Blocks.WATER)
                            .lightLevel(state -> 4).noLootTable()));

    private ModBlocks() {}
}
