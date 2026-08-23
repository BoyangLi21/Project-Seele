package com.projectseele.registry;

import com.projectseele.ProjectSeele;
import com.projectseele.world.UmbilicalPylonBlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

/** Block entities used by interactive NERV infrastructure. */
public final class ModBlockEntities
{
    public static final DeferredRegister<BlockEntityType<?>> BLOCK_ENTITY_TYPES =
            DeferredRegister.create(ForgeRegistries.BLOCK_ENTITY_TYPES,
                    ProjectSeele.MODID);

    public static final RegistryObject<BlockEntityType<UmbilicalPylonBlockEntity>>
            UMBILICAL_PYLON = BLOCK_ENTITY_TYPES.register("umbilical_pylon",
            () -> BlockEntityType.Builder.of(UmbilicalPylonBlockEntity::new,
                    ModBlocks.UMBILICAL_PYLON.get()).build(null));

    private ModBlockEntities() {}
}
