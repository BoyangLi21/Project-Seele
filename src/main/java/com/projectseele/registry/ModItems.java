package com.projectseele.registry;

import com.projectseele.ProjectSeele;
import com.projectseele.item.PositronRifleItem;
import net.minecraft.world.item.Item;
import net.minecraftforge.common.ForgeSpawnEggItem;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

public class ModItems
{
    public static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, ProjectSeele.MODID);

    public static final RegistryObject<Item> CORE_FRAGMENT = ITEMS.register("core_fragment",
            () -> new Item(new Item.Properties()));

    public static final RegistryObject<Item> POSITRON_RIFLE = ITEMS.register("positron_rifle",
            () -> new PositronRifleItem(new Item.Properties().stacksTo(1)));

    public static final RegistryObject<Item> RAMIEL_SPAWN_EGG = ITEMS.register("ramiel_spawn_egg",
            () -> new ForgeSpawnEggItem(ModEntities.RAMIEL, 0x4A7FD4, 0xE3242B, new Item.Properties()));

    public static final RegistryObject<Item> EVA_UNIT01_SPAWN_EGG = ITEMS.register("eva_unit01_spawn_egg",
            () -> new ForgeSpawnEggItem(ModEntities.EVA_UNIT01, 0x57288A, 0x39FF6E, new Item.Properties()));
}
