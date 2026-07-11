package com.projectseele.registry;

import com.projectseele.ProjectSeele;
import com.projectseele.item.PositronRifleItem;
import com.projectseele.item.SeeleScenarioItem;
import com.projectseele.item.NervConstructionKitItem;
import com.projectseele.item.NervBeaconItem;
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
    public static final RegistryObject<Item> S2_ENGINE_FRAGMENT = ITEMS.register("s2_engine_fragment",
            () -> new Item(new Item.Properties().fireResistant()));

    public static final RegistryObject<Item> POSITRON_RIFLE = ITEMS.register("positron_rifle",
            () -> new PositronRifleItem(new Item.Properties().stacksTo(1)));

    public static final RegistryObject<Item> RAMIEL_SPAWN_EGG = ITEMS.register("ramiel_spawn_egg",
            () -> new ForgeSpawnEggItem(ModEntities.RAMIEL, 0x4A7FD4, 0xE3242B, new Item.Properties()));

    public static final RegistryObject<Item> EVA_UNIT01_SPAWN_EGG = ITEMS.register("eva_unit01_spawn_egg",
            () -> new ForgeSpawnEggItem(ModEntities.EVA_UNIT01, 0x57288A, 0x39FF6E, new Item.Properties()));
    public static final RegistryObject<Item> EVA_UNIT00_SPAWN_EGG = ITEMS.register("eva_unit00_spawn_egg",
            () -> new ForgeSpawnEggItem(ModEntities.EVA_UNIT00, 0xE89B2C, 0xF5F5E8, new Item.Properties()));
    public static final RegistryObject<Item> EVA_UNIT02_SPAWN_EGG = ITEMS.register("eva_unit02_spawn_egg",
            () -> new ForgeSpawnEggItem(ModEntities.EVA_UNIT02, 0xB51F28, 0xF2C230, new Item.Properties()));

    public static final RegistryObject<Item> SACHIEL_SPAWN_EGG = ITEMS.register("sachiel_spawn_egg",
            () -> new ForgeSpawnEggItem(ModEntities.SACHIEL, 0x202623, 0xEAF0E5, new Item.Properties()));
    public static final RegistryObject<Item> SHAMSHEL_SPAWN_EGG = ITEMS.register("shamshel_spawn_egg",
            () -> new ForgeSpawnEggItem(ModEntities.SHAMSHEL, 0x5B162A, 0xEF3C4A, new Item.Properties()));
    public static final RegistryObject<Item> ZERUEL_SPAWN_EGG = ITEMS.register("zeruel_spawn_egg",
            () -> new ForgeSpawnEggItem(ModEntities.ZERUEL, 0xE4E2D8, 0x181414, new Item.Properties()));
    public static final RegistryObject<Item> MASS_PRODUCTION_EVA_SPAWN_EGG = ITEMS.register("mass_production_eva_spawn_egg",
            () -> new ForgeSpawnEggItem(ModEntities.MASS_PRODUCTION_EVA, 0xE2DED2, 0xA51620, new Item.Properties()));
    public static final RegistryObject<Item> SEELE_SCENARIO = ITEMS.register("seele_scenario",
            () -> new SeeleScenarioItem(new Item.Properties().stacksTo(1).fireResistant()));
    public static final RegistryObject<Item> NERV_CONSTRUCTION_KIT = ITEMS.register("nerv_construction_kit",
            () -> new NervConstructionKitItem(new Item.Properties().stacksTo(1)));
    public static final RegistryObject<Item> NERV_BEACON = ITEMS.register("nerv_beacon",
            () -> new NervBeaconItem(new Item.Properties().stacksTo(1).fireResistant()));
}
