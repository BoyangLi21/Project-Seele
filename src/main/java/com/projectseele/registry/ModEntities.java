package com.projectseele.registry;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
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

    public static final RegistryObject<EntityType<EvaUnit01Entity>> EVA_UNIT01 = ENTITY_TYPES.register("eva_unit01",
            () -> EntityType.Builder.of(EvaUnit01Entity::new, MobCategory.MISC)
                    .sized(3.4F, 12.0F)
                    .fireImmune()
                    .clientTrackingRange(10)
                    .build("eva_unit01"));
}
