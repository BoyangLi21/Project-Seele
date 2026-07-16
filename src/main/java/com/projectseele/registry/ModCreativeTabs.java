package com.projectseele.registry;

import com.projectseele.ProjectSeele;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.RegistryObject;

public class ModCreativeTabs
{
    public static final DeferredRegister<CreativeModeTab> TABS =
            DeferredRegister.create(Registries.CREATIVE_MODE_TAB, ProjectSeele.MODID);

    public static final RegistryObject<CreativeModeTab> MAIN = TABS.register("main",
            () -> CreativeModeTab.builder()
                    .title(Component.translatable("itemGroup.projectseele"))
                    .icon(() -> ModItems.POSITRON_RIFLE.get().getDefaultInstance())
                    .displayItems((parameters, output) -> {
                        output.accept(ModItems.POSITRON_RIFLE.get());
                        output.accept(ModItems.CORE_FRAGMENT.get());
                        output.accept(ModItems.S2_ENGINE_FRAGMENT.get());
                        output.accept(ModItems.RETRACTABLE_BUILDING_CORE.get());
                        output.accept(ModItems.RAMIEL_SPAWN_EGG.get());
                        output.accept(ModItems.EVA_UNIT01_SPAWN_EGG.get());
                        output.accept(ModItems.EVA_UNIT00_SPAWN_EGG.get());
                        output.accept(ModItems.EVA_UNIT02_SPAWN_EGG.get());
                        output.accept(ModItems.SACHIEL_SPAWN_EGG.get());
                        output.accept(ModItems.SHAMSHEL_SPAWN_EGG.get());
                        output.accept(ModItems.ZERUEL_SPAWN_EGG.get());
                        output.accept(ModItems.ISRAFEL_SPAWN_EGG.get());
                        output.accept(ModItems.MASS_PRODUCTION_EVA_SPAWN_EGG.get());
                        output.accept(ModItems.NERV_CONSTRUCTION_KIT.get());
                        output.accept(ModItems.NERV_BEACON.get());
                        output.accept(ModItems.LANCE_OF_LONGINUS.get());
                        output.accept(ModItems.SEELE_SCENARIO.get());
                    })
                    .build());
}
