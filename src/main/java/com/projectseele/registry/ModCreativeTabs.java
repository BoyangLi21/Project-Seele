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
                        output.accept(ModItems.RAMIEL_SPAWN_EGG.get());
                    })
                    .build());
}
