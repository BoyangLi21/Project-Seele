package com.projectseele.registry;

import com.mojang.serialization.Codec;
import com.projectseele.ProjectSeele;
import com.projectseele.world.GeoFrontBoundedChunkGenerator;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.RegistryObject;

public final class ModWorldgen
{
    public static final DeferredRegister<Codec<? extends ChunkGenerator>>
            CHUNK_GENERATORS = DeferredRegister.create(
                    Registries.CHUNK_GENERATOR, ProjectSeele.MODID);

    public static final RegistryObject<Codec<? extends ChunkGenerator>>
            GEOFRONT_BOUNDED = CHUNK_GENERATORS.register(
                    "geofront_bounded",
                    () -> GeoFrontBoundedChunkGenerator.CODEC);

    private ModWorldgen() {}
}
