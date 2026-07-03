package com.projectseele.registry;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.RamielEntity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

public class ModEntities
{
    public static final DeferredRegister<EntityType<?>> ENTITY_TYPES =
            DeferredRegister.create(ForgeRegistries.ENTITY_TYPES, ProjectSeele.MODID);

    public static final RegistryObject<EntityType<RamielEntity>> RAMIEL = ENTITY_TYPES.register("ramiel",
            () -> EntityType.Builder.of(RamielEntity::new, MobCategory.MONSTER)
                    .sized(6.0F, 6.0F)
                    .fireImmune()
                    .clientTrackingRange(10)
                    .build("ramiel"));
}
