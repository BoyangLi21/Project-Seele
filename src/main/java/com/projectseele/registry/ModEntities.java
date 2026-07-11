package com.projectseele.registry;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.RamielEntity;
import com.projectseele.entity.SachielEntity;
import com.projectseele.entity.MassProductionEvaEntity;
import com.projectseele.entity.ShamshelEntity;
import com.projectseele.entity.ZeruelEntity;
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
                    .sized(15.0F, 15.0F)
                    .fireImmune()
                    .clientTrackingRange(12)
                    .build("ramiel"));

    // Tracking ranges below are wide because scenario staging can park these
    // entities hundreds of blocks up the Tree of Life.
    public static final RegistryObject<EntityType<EvaUnit01Entity>> EVA_UNIT01 = ENTITY_TYPES.register("eva_unit01",
            () -> EntityType.Builder.of(EvaUnit01Entity::new, MobCategory.MISC)
                    .sized(8.5F, 30.0F)
                    .fireImmune()
                    .clientTrackingRange(64)
                    .build("eva_unit01"));

    public static final RegistryObject<EntityType<EvaUnit01Entity>> EVA_UNIT00 = ENTITY_TYPES.register("eva_unit00",
            () -> EntityType.Builder.of(EvaUnit01Entity::new, MobCategory.MISC)
                    .sized(8.5F, 30.0F)
                    .fireImmune()
                    .clientTrackingRange(12)
                    .build("eva_unit00"));

    public static final RegistryObject<EntityType<EvaUnit01Entity>> EVA_UNIT02 = ENTITY_TYPES.register("eva_unit02",
            () -> EntityType.Builder.of(EvaUnit01Entity::new, MobCategory.MISC)
                    .sized(8.5F, 30.0F)
                    .fireImmune()
                    .clientTrackingRange(12)
                    .build("eva_unit02"));

    public static final RegistryObject<EntityType<SachielEntity>> SACHIEL = ENTITY_TYPES.register("sachiel",
            () -> EntityType.Builder.of(SachielEntity::new, MobCategory.MONSTER)
                    .sized(9.0F, 24.0F).fireImmune().clientTrackingRange(14).build("sachiel"));

    public static final RegistryObject<EntityType<MassProductionEvaEntity>> MASS_PRODUCTION_EVA =
            ENTITY_TYPES.register("mass_production_eva",
                    () -> EntityType.Builder.of(MassProductionEvaEntity::new, MobCategory.MONSTER)
                            .sized(10.0F, 26.0F).fireImmune().clientTrackingRange(16)
                            .build("mass_production_eva"));

    public static final RegistryObject<EntityType<ShamshelEntity>> SHAMSHEL = ENTITY_TYPES.register("shamshel",
            () -> EntityType.Builder.of(ShamshelEntity::new, MobCategory.MONSTER)
                    .sized(10.0F, 20.0F).fireImmune().clientTrackingRange(14).build("shamshel"));

    public static final RegistryObject<EntityType<ZeruelEntity>> ZERUEL = ENTITY_TYPES.register("zeruel",
            () -> EntityType.Builder.of(ZeruelEntity::new, MobCategory.MONSTER)
                    .sized(12.0F, 28.0F).fireImmune().clientTrackingRange(18).build("zeruel"));
}
