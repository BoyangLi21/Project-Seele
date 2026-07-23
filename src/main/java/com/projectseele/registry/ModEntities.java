package com.projectseele.registry;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EntryPlugCarrierEntity;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.LilithEntity;
import com.projectseele.entity.NervCarrierPlatformEntity;
import com.projectseele.entity.RamielEntity;
import com.projectseele.entity.SachielEntity;
import com.projectseele.entity.MassProductionEvaEntity;
import com.projectseele.entity.ShamshelEntity;
import com.projectseele.entity.ZeruelEntity;
import com.projectseele.entity.TrainingPilotEntity;
import com.projectseele.entity.IsrafelEntity;
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

    public static final RegistryObject<EntityType<EntryPlugCarrierEntity>> ENTRY_PLUG_CARRIER =
            ENTITY_TYPES.register("entry_plug_carrier",
                    () -> EntityType.Builder.of(EntryPlugCarrierEntity::new,
                                    MobCategory.MISC)
                            .sized(1.5F, 6.0F)
                            .fireImmune()
                            .clientTrackingRange(24)
                            .updateInterval(1)
                            .build("entry_plug_carrier"));

    public static final RegistryObject<EntityType<NervCarrierPlatformEntity>>
            NERV_CARRIER_PLATFORM = ENTITY_TYPES.register(
                    "nerv_carrier_platform",
                    () -> EntityType.Builder.of(NervCarrierPlatformEntity::new,
                                    MobCategory.MISC)
                            .noSave()
                            .sized(11.0F, 0.6F)
                            .clientTrackingRange(32)
                            .updateInterval(1)
                            .setShouldReceiveVelocityUpdates(false)
                            .build("nerv_carrier_platform"));

    public static final RegistryObject<EntityType<TrainingPilotEntity>> TRAINING_PILOT =
            ENTITY_TYPES.register("training_pilot",
                    () -> EntityType.Builder.of(TrainingPilotEntity::new,
                                    MobCategory.MISC)
                            .sized(0.6F, 1.8F)
                            .clientTrackingRange(12)
                            .build("training_pilot"));

    public static final RegistryObject<EntityType<SachielEntity>> SACHIEL = ENTITY_TYPES.register("sachiel",
            () -> EntityType.Builder.of(SachielEntity::new, MobCategory.MONSTER)
                    .sized(9.0F, 24.0F).fireImmune().clientTrackingRange(14).build("sachiel"));

    public static final RegistryObject<EntityType<MassProductionEvaEntity>> MASS_PRODUCTION_EVA =
            ENTITY_TYPES.register("mass_production_eva",
                    () -> EntityType.Builder.of(MassProductionEvaEntity::new, MobCategory.MONSTER)
                            // The fixed Tree camera is 120 blocks off-plane;
                            // crown/nadir vessels add 67 vertical blocks. A
                            // range of 16 dropped those four client-side while
                            // the server still held a 9/9 formation.
                            .sized(10.0F, 26.0F).fireImmune().clientTrackingRange(32)
                            .build("mass_production_eva"));

    public static final RegistryObject<EntityType<ShamshelEntity>> SHAMSHEL = ENTITY_TYPES.register("shamshel",
            () -> EntityType.Builder.of(ShamshelEntity::new, MobCategory.MONSTER)
                    .sized(10.0F, 20.0F).fireImmune().clientTrackingRange(14).build("shamshel"));

    public static final RegistryObject<EntityType<ZeruelEntity>> ZERUEL = ENTITY_TYPES.register("zeruel",
            () -> EntityType.Builder.of(ZeruelEntity::new, MobCategory.MONSTER)
                    .sized(12.0F, 28.0F).fireImmune().clientTrackingRange(18).build("zeruel"));

    public static final RegistryObject<EntityType<IsrafelEntity>> ISRAFEL = ENTITY_TYPES.register("israfel",
            () -> EntityType.Builder.of(IsrafelEntity::new, MobCategory.MONSTER)
                    .sized(9.0F, 24.0F).fireImmune().clientTrackingRange(16).build("israfel"));
    public static final RegistryObject<EntityType<LilithEntity>> LILITH =
            ENTITY_TYPES.register("lilith",
                    () -> EntityType.Builder.of(LilithEntity::new, MobCategory.MISC)
                            .sized(1.0F, 1.0F).fireImmune()
                            .clientTrackingRange(24).updateInterval(20)
                            .build("lilith"));
}
