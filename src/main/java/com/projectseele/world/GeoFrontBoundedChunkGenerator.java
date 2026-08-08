package com.projectseele.world;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.biome.BiomeManager;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.levelgen.GenerationStep;
import net.minecraft.world.level.levelgen.NoiseBasedChunkGenerator;
import net.minecraft.world.level.levelgen.NoiseGeneratorSettings;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.blending.Blender;

/**
 * Natural-surface generator with bounded, load-bearing GeoFront caverns.
 *
 * <p>The delegated noise settings produce real geology everywhere. This
 * generator then removes only the air portion of one of the frozen candidate
 * ellipsoids, leaving a thick terrain mass below it and solid geology outside
 * it. Facility owners plus their one-block guard remain solid until their own
 * receipt-controlled builders carve them.</p>
 */
public final class GeoFrontBoundedChunkGenerator
        extends NoiseBasedChunkGenerator
{
    public static final String GENERATOR_VERSION =
            "geofront-bounded-baseline-r2";
    public static final Codec<GeoFrontBoundedChunkGenerator> CODEC =
            RecordCodecBuilder.create(instance -> instance.group(
                    BiomeSource.CODEC.fieldOf("biome_source")
                            .forGetter(GeoFrontBoundedChunkGenerator
                                    ::getBiomeSource),
                    NoiseGeneratorSettings.CODEC.fieldOf("settings")
                            .forGetter(GeoFrontBoundedChunkGenerator
                                    ::generatorSettings),
                    Codec.INT.fieldOf("candidate_index")
                            .forGetter(generator -> generator.candidateIndex),
                    Codec.INT.fieldOf("surface_datum")
                            .forGetter(generator -> generator.surfaceDatum)
            ).apply(instance, instance.stable(
                    GeoFrontBoundedChunkGenerator::new)));

    private final int candidateIndex;
    private final int surfaceDatum;
    private final boolean baselineEnabled;
    private final FacilitySchemaV2.ResolvedManifest activeManifest;

    public GeoFrontBoundedChunkGenerator(
            BiomeSource biomeSource,
            Holder<NoiseGeneratorSettings> settings,
            int candidateIndex, int surfaceDatum)
    {
        super(biomeSource, settings);
        this.candidateIndex = candidateIndex;
        this.surfaceDatum = surfaceDatum;
        this.baselineEnabled =
                candidateIndex == FacilitySchemaV2.ACTIVE_CANDIDATE_INDEX
                && surfaceDatum == FacilitySchemaV2.WORLDGEN_SURFACE_DATUM;
        this.activeManifest = FacilitySchemaV2.resolve(
                FacilitySchemaV2.ACTIVE_CANDIDATE_INDEX,
                FacilitySchemaV2.WORLDGEN_SURFACE_DATUM);
    }

    @Override
    protected Codec<? extends net.minecraft.world.level.chunk.ChunkGenerator>
    codec()
    {
        return CODEC;
    }

    /**
     * Bootstrap authority is the frozen generator contract, not the natural
     * surface relief above it. Surface owners establish their own reviewed
     * datum, while this identity proves that the committed cavern and roof
     * baseline will be generated at the schema coordinates.
     */
    boolean matchesFacilityBaselineContract()
    {
        return this.baselineEnabled
                && this.candidateIndex
                == FacilitySchemaV2.ACTIVE_CANDIDATE_INDEX
                && this.surfaceDatum
                == FacilitySchemaV2.WORLDGEN_SURFACE_DATUM;
    }

    @Override
    public CompletableFuture<ChunkAccess> fillFromNoise(
            Executor executor, Blender blender, RandomState randomState,
            StructureManager structureManager, ChunkAccess chunk)
    {
        return super.fillFromNoise(executor, blender, randomState,
                        structureManager, chunk)
                .thenApply(generated ->
                {
                    this.carveBoundedBaseline(generated);
                    return generated;
                });
    }

    /**
     * Vanilla caves remain available in the surrounding natural continent,
     * but are disabled across the one committed GeoFront footprint so a
     * random cave cannot puncture its roof or a reserved facility shaft.
     */
    @Override
    public void applyCarvers(
            WorldGenRegion region, long seed, RandomState randomState,
            BiomeManager biomeManager, StructureManager structureManager,
            ChunkAccess chunk, GenerationStep.Carving step)
    {
        if (this.candidateFor(chunk.getPos()) == null)
        {
            super.applyCarvers(region, seed, randomState, biomeManager,
                    structureManager, chunk, step);
        }
    }

    private void carveBoundedBaseline(ChunkAccess chunk)
    {
        FacilitySchemaV2.ResolvedManifest candidate =
                this.candidateFor(chunk.getPos());
        if (candidate == null)
        {
            return;
        }

        BlockPos centre = candidate.centre();
        ChunkPos chunkPos = chunk.getPos();
        int minX = chunkPos.getMinBlockX();
        int minZ = chunkPos.getMinBlockZ();
        int minY = Math.max(chunk.getMinBuildHeight(),
                GeoFrontFabricPlan.CAVERN_BOTTOM_Y);
        int maxY = Math.min(chunk.getMaxBuildHeight(),
                GeoFrontFabricPlan.CAVERN_TOP_Y + 1);
        BlockPos.MutableBlockPos position = new BlockPos.MutableBlockPos();

        for (int localZ = 0; localZ < 16; localZ++)
        {
            int worldZ = minZ + localZ;
            double dz = (worldZ + 0.5D - centre.getZ())
                    / GeoFrontFabricPlan.CAVERN_RADIUS_XZ;
            for (int localX = 0; localX < 16; localX++)
            {
                int worldX = minX + localX;
                double dx = (worldX + 0.5D - centre.getX())
                        / GeoFrontFabricPlan.CAVERN_RADIUS_XZ;
                double radial = 1.0D - dx * dx - dz * dz;
                if (radial <= 0.0D)
                {
                    continue;
                }

                double verticalRadius =
                        GeoFrontFabricPlan.CAVERN_RADIUS_Y
                                * Math.sqrt(radial);
                int rawBottom = (int) Math.ceil(
                        GeoFrontFabricPlan.CAVERN_CENTRE_Y
                                - verticalRadius);
                int rawTopExclusive = (int) Math.floor(
                        GeoFrontFabricPlan.CAVERN_CENTRE_Y
                                + verticalRadius) + 1;
                int relativeX = worldX - centre.getX();
                int relativeZ = worldZ - centre.getZ();
                int terrainTop = GeoFrontFabricPlan.terrainHeight(
                        relativeX, relativeZ);
                int carveMin = Math.max(minY,
                        Math.max(rawBottom, terrainTop + 1));
                int carveMax = Math.min(maxY, rawTopExclusive);

                for (int y = carveMin; y < carveMax; y++)
                {
                    position.set(worldX, y, worldZ);
                    if (GeoFrontFabricPlan.ownerGuarded(
                            candidate, position))
                    {
                        continue;
                    }
                    chunk.setBlockState(position,
                            Blocks.AIR.defaultBlockState(), false);
                }
            }
        }
        chunk.setUnsaved(true);
    }

    private FacilitySchemaV2.ResolvedManifest candidateFor(
            ChunkPos chunk)
    {
        if (!this.baselineEnabled)
        {
            // Codec/config mismatch fails closed: keep complete geology.
            return null;
        }
        int minX = chunk.getMinBlockX();
        int maxX = chunk.getMaxBlockX();
        int minZ = chunk.getMinBlockZ();
        int maxZ = chunk.getMaxBlockZ();
        int radius = GeoFrontFabricPlan.CAVERN_RADIUS_XZ;
        BlockPos centre = this.activeManifest.centre();
        if (maxX >= centre.getX() - radius
                && minX <= centre.getX() + radius
                && maxZ >= centre.getZ() - radius
                && minZ <= centre.getZ() + radius)
        {
            return this.activeManifest;
        }
        return null;
    }
}
