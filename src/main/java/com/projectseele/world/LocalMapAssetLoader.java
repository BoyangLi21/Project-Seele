package com.projectseele.world;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import com.projectseele.ProjectSeele;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Vec3i;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtIo;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructurePlaceSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;

/**
 * Loads private evaluation maps from the active game directory. These files
 * are intentionally absent from the distributable jar and have deterministic
 * clean-room fallbacks when a player has not installed them.
 */
public final class LocalMapAssetLoader
{
    private static final Path ASSET_DIRECTORY =
            Paths.get("projectseele-local-maps");
    private static final Path COMMAND_MODULE =
            ASSET_DIRECTORY.resolve("nerv_command_left.nbt");
    private static final Path TOKYO3_SKYSCRAPER =
            ASSET_DIRECTORY.resolve("tokyo3_skyscraper.nbt");
    private static final String STAGED_WORLD_MARKER =
            ".projectseele_local_map.json";

    private static final BlockPos COMMAND_OFFSET = new BlockPos(-28, -21, -33);
    private static final Vec3i COMMAND_SIZE = new Vec3i(56, 77, 129);
    private static final BlockPos COMMAND_MARKER_A =
            new BlockPos(-30, -22, -35);
    private static final BlockPos COMMAND_MARKER_B =
            new BlockPos(29, 57, 97);
    private static final BlockPos TOKYO3_IMPORT_MARKER =
            new BlockPos(126, -20, 126);
    private static final BlockPos PRIVATE_GEOFRONT_MARKER =
            new BlockPos(126, 80, 126);
    private static final BlockPos SKYSCRAPER_STATE_MARKER =
            new BlockPos(132, -20, 120);
    private static final int SKYSCRAPER_MOVE_QUANTUM = 12;
    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;

    private static final SkyscraperPlacement[] SKYSCRAPERS = {
            new SkyscraperPlacement(new BlockPos(-140, 1, -70),
                    Rotation.NONE),
            new SkyscraperPlacement(new BlockPos(120, 1, -92),
                    Rotation.CLOCKWISE_90),
            new SkyscraperPlacement(new BlockPos(112, 1, 82),
                    Rotation.CLOCKWISE_180),
    };

    private LocalMapAssetLoader() {}

    public static boolean commandModuleAvailable()
    {
        return Files.isRegularFile(COMMAND_MODULE);
    }

    public static boolean skyscraperAvailable()
    {
        return Files.isRegularFile(TOKYO3_SKYSCRAPER);
    }

    /**
     * The legacy EVA-X save has this unusual iron/bedrock/iron vertical
     * signature at its city spawn. The persistent marker survives after the
     * central launch shaft deliberately cuts through that source column.
     */
    public static boolean importedTokyo3Present(BlockGetter level,
                                                BlockPos origin)
    {
        BlockPos marker = origin.offset(TOKYO3_IMPORT_MARKER);
        if (level.getBlockState(marker).is(Blocks.NETHERITE_BLOCK)
                && level.getBlockState(marker.east()).is(Blocks.LODESTONE))
        {
            return true;
        }
        return level.getBlockState(origin.below(2)).is(Blocks.IRON_BLOCK)
                && level.getBlockState(origin.below()).is(Blocks.BEDROCK)
                && level.getBlockState(origin).is(Blocks.IRON_BLOCK);
    }

    /**
     * The prepared evaluation save carries a local-only marker at its world
     * root.  Checking that marker is more reliable than inspecting legacy
     * 1.7 blocks after DataFixer has upgraded the first city chunk.
     */
    public static boolean stagedEvaWorld(ServerLevel level)
    {
        Path worldRoot = level.getServer().getWorldPath(LevelResource.ROOT);
        return Files.isRegularFile(worldRoot.resolve(STAGED_WORLD_MARKER));
    }

    public static void markPrivateGeoFrontShell(ServerLevel level,
                                                BlockPos geoFrontOrigin)
    {
        BlockPos marker = geoFrontOrigin.offset(PRIVATE_GEOFRONT_MARKER);
        set(level, marker, Blocks.NETHERITE_BLOCK.defaultBlockState());
        set(level, marker.above(), Blocks.IRON_BLOCK.defaultBlockState());
        set(level, marker.east(), Blocks.LODESTONE.defaultBlockState());
    }

    public static boolean privateGeoFrontShellPresent(BlockGetter level,
                                                       BlockPos geoFrontOrigin)
    {
        BlockPos marker = geoFrontOrigin.offset(PRIVATE_GEOFRONT_MARKER);
        return level.getBlockState(marker).is(Blocks.NETHERITE_BLOCK)
                && level.getBlockState(marker.above()).is(Blocks.IRON_BLOCK)
                && level.getBlockState(marker.east()).is(Blocks.LODESTONE);
    }

    public static void markImportedTokyo3(ServerLevel level, BlockPos origin)
    {
        BlockPos marker = origin.offset(TOKYO3_IMPORT_MARKER);
        set(level, marker, Blocks.NETHERITE_BLOCK.defaultBlockState());
        set(level, marker.east(), Blocks.LODESTONE.defaultBlockState());
    }

    public static boolean importedTokyo3MarkerPresent(BlockGetter level,
                                                      BlockPos origin)
    {
        BlockPos marker = origin.offset(TOKYO3_IMPORT_MARKER);
        return level.getBlockState(marker).is(Blocks.NETHERITE_BLOCK)
                && level.getBlockState(marker.east()).is(Blocks.LODESTONE);
    }

    public static boolean placeCommandModule(ServerLevel level,
                                             BlockPos geoFrontOrigin)
    {
        if (commandMarkersPresent(level, geoFrontOrigin))
        {
            return true;
        }
        StructureTemplate template = load(level, COMMAND_MODULE);
        if (template == null)
        {
            return false;
        }
        BlockPos base = geoFrontOrigin.offset(COMMAND_OFFSET);
        clearVolume(level, base, COMMAND_SIZE);
        boolean placed = place(level, template, base, Rotation.NONE);
        if (!placed)
        {
            ProjectSeele.LOGGER.error(
                    "Local NERV command module placement returned false at {}", base);
            return false;
        }
        set(level, geoFrontOrigin.offset(COMMAND_MARKER_A),
                Blocks.NETHERITE_BLOCK.defaultBlockState());
        set(level, geoFrontOrigin.offset(COMMAND_MARKER_B),
                Blocks.LODESTONE.defaultBlockState());
        ProjectSeele.LOGGER.info(
                "Loaded private NERV command module at {} size={}x{}x{}",
                base, COMMAND_SIZE.getX(), COMMAND_SIZE.getY(),
                COMMAND_SIZE.getZ());
        return true;
    }

    public static boolean commandMarkersPresent(BlockGetter level,
                                                 BlockPos geoFrontOrigin)
    {
        return level.getBlockState(geoFrontOrigin.offset(COMMAND_MARKER_A))
                .is(Blocks.NETHERITE_BLOCK)
                && level.getBlockState(geoFrontOrigin.offset(COMMAND_MARKER_B))
                .is(Blocks.LODESTONE);
    }

    /** Package contract used when an enclosing shell is rebuilt around the asset. */
    static boolean commandEnvelopeContains(int relativeX, int relativeY,
                                           int relativeZ)
    {
        return relativeX >= COMMAND_OFFSET.getX()
                && relativeX < COMMAND_OFFSET.getX() + COMMAND_SIZE.getX()
                && relativeY >= COMMAND_OFFSET.getY()
                && relativeY < COMMAND_OFFSET.getY() + COMMAND_SIZE.getY()
                && relativeZ >= COMMAND_OFFSET.getZ()
                && relativeZ < COMMAND_OFFSET.getZ() + COMMAND_SIZE.getZ();
    }

    /** Asset markers live just outside its cleared NBT volume and must survive shell work. */
    static boolean isCommandMarkerOffset(int relativeX, int relativeY,
                                         int relativeZ)
    {
        return COMMAND_MARKER_A.equals(new BlockPos(relativeX, relativeY, relativeZ))
                || COMMAND_MARKER_B.equals(new BlockPos(relativeX, relativeY, relativeZ));
    }

    public static int placeTokyo3Skyscrapers(ServerLevel level,
                                             BlockPos tokyo3Origin)
    {
        return placeTokyo3Skyscrapers(level, tokyo3Origin, 0);
    }

    /**
     * Places every private high-rise at its authoritative travel depth. The
     * source NBT stays local; only these deterministic placement rules ship.
     */
    public static int placeTokyo3Skyscrapers(ServerLevel level,
                                             BlockPos tokyo3Origin,
                                             int retractionDepth)
    {
        StructureTemplate template = load(level, TOKYO3_SKYSCRAPER);
        if (template == null)
        {
            return 0;
        }
        int placed = 0;
        for (int index = 0; index < SKYSCRAPERS.length; index++)
        {
            SkyscraperPlacement placement = SKYSCRAPERS[index];
            Vec3i size = template.getSize(placement.rotation());
            int drop = skyscraperDrop(placement, size, retractionDepth);
            BlockPos surfaceBase = tokyo3Origin.offset(placement.offset());
            BlockPos base = surfaceBase.below(drop);
            BlockPos travelMarker = skyscraperMarker(base, index);
            BlockPos stateMarker = skyscraperStateMarker(tokyo3Origin, index);
            if (level.getBlockState(travelMarker).is(Blocks.NETHERITE_BLOCK)
                    && level.getBlockState(stateMarker).is(Blocks.LODESTONE))
            {
                placed++;
                continue;
            }

            // Version 15 and earlier always left imported towers on the
            // surface. Clear that old copy once before materialising the
            // authoritative position.
            if (!base.equals(surfaceBase))
            {
                clearVolume(level, surfaceBase, size);
                set(level, skyscraperMarker(surfaceBase, index),
                        Blocks.AIR.defaultBlockState());
            }
            clearVolume(level, base, size);
            if (place(level, template, base, placement.rotation()))
            {
                set(level, travelMarker, Blocks.NETHERITE_BLOCK.defaultBlockState());
                set(level, stateMarker, Blocks.LODESTONE.defaultBlockState());
                placed++;
            }
        }
        if (placed > 0)
        {
            ProjectSeele.LOGGER.info(
                    "Tokyo-3 private skyscraper set present: {}/{} depth={}",
                    placed, SKYSCRAPERS.length, retractionDepth);
        }
        return placed;
    }

    /**
     * Coarse whole-structure travel. Twelve-block steps keep the imported
     * 5,996-block meshes visibly moving without replaying three templates on
     * every server tick.
     */
    public static void applyTokyo3RetractionDepth(ServerLevel level,
                                                  BlockPos tokyo3Origin,
                                                  int oldDepth, int newDepth)
    {
        StructureTemplate template = load(level, TOKYO3_SKYSCRAPER);
        if (template == null)
        {
            return;
        }
        for (int index = 0; index < SKYSCRAPERS.length; index++)
        {
            SkyscraperPlacement placement = SKYSCRAPERS[index];
            Vec3i size = template.getSize(placement.rotation());
            int oldDrop = skyscraperDrop(placement, size, oldDepth);
            int newDrop = skyscraperDrop(placement, size, newDepth);
            if (oldDrop == newDrop)
            {
                continue;
            }
            BlockPos surfaceBase = tokyo3Origin.offset(placement.offset());
            BlockPos oldBase = surfaceBase.below(oldDrop);
            BlockPos newBase = surfaceBase.below(newDrop);
            clearVolume(level, oldBase, size);
            set(level, skyscraperMarker(oldBase, index),
                    Blocks.AIR.defaultBlockState());
            clearVolume(level, newBase, size);
            if (!place(level, template, newBase, placement.rotation()))
            {
                ProjectSeele.LOGGER.error(
                        "Private Tokyo-3 skyscraper {} failed to move depth {} -> {}",
                        index, oldDepth, newDepth);
                continue;
            }
            set(level, skyscraperMarker(newBase, index),
                    Blocks.NETHERITE_BLOCK.defaultBlockState());
            set(level, skyscraperStateMarker(tokyo3Origin, index),
                    Blocks.LODESTONE.defaultBlockState());
        }
    }

    public static int inspectTokyo3Skyscrapers(BlockGetter level,
                                               BlockPos tokyo3Origin)
    {
        int found = 0;
        for (int index = 0; index < SKYSCRAPERS.length; index++)
        {
            if (level.getBlockState(skyscraperStateMarker(tokyo3Origin, index))
                    .is(Blocks.LODESTONE))
            {
                found++;
            }
        }
        return found;
    }

    private static int skyscraperDrop(SkyscraperPlacement placement,
                                      Vec3i size, int depth)
    {
        int centreX = placement.offset().getX() + size.getX() / 2;
        int centreZ = placement.offset().getZ() + size.getZ() / 2;
        ThirdTokyoSurfaceBuilder.TowerSpec envelope =
                new ThirdTokyoSurfaceBuilder.TowerSpec(
                        centreX, centreZ, size.getY(),
                        Math.max(size.getX(), size.getZ()) / 2, true);
        int topAtSurface = placement.offset().getY() + size.getY() - 1;
        int targetDrop = Math.max(0, topAtSurface
                - ThirdTokyoSurfaceBuilder.ceilingRoofRelativeY(envelope));
        int bounded = Math.max(0, Math.min(depth, targetDrop));
        if (bounded == targetDrop)
        {
            return targetDrop;
        }
        return bounded / SKYSCRAPER_MOVE_QUANTUM * SKYSCRAPER_MOVE_QUANTUM;
    }

    private static BlockPos skyscraperMarker(BlockPos base, int index)
    {
        return base.below().offset(index, 0, 0);
    }

    private static BlockPos skyscraperStateMarker(BlockPos origin, int index)
    {
        return origin.offset(SKYSCRAPER_STATE_MARKER).offset(index * 2, 0, 0);
    }
    private static StructureTemplate load(ServerLevel level, Path path)
    {
        if (!Files.isRegularFile(path))
        {
            return null;
        }
        try
        {
            CompoundTag root = NbtIo.readCompressed(path.toFile());
            StructureTemplate template = new StructureTemplate();
            template.load(level.registryAccess().lookup(Registries.BLOCK)
                    .orElseThrow(), root);
            return template;
        }
        catch (IOException | RuntimeException exception)
        {
            ProjectSeele.LOGGER.error("Unable to load private map asset {}",
                    path.toAbsolutePath(), exception);
            return null;
        }
    }

    private static boolean place(ServerLevel level, StructureTemplate template,
                                 BlockPos base, Rotation rotation)
    {
        StructurePlaceSettings settings = new StructurePlaceSettings()
                .setMirror(Mirror.NONE)
                .setRotation(rotation)
                .setIgnoreEntities(false)
                .setKnownShape(true);
        return template.placeInWorld(level, base, base, settings,
                RandomSource.create(0x5345454c45L), UPDATE_CLIENTS);
    }

    private static void clearVolume(ServerLevel level, BlockPos base,
                                    Vec3i size)
    {
        for (int x = 0; x < size.getX(); x++)
        {
            for (int z = 0; z < size.getZ(); z++)
            {
                for (int y = 0; y < size.getY(); y++)
                {
                    BlockPos position = base.offset(x, y, z);
                    if (!level.getBlockState(position).isAir())
                    {
                        set(level, position, Blocks.AIR.defaultBlockState());
                    }
                }
            }
        }
    }

    private static void set(ServerLevel level, BlockPos position,
                            net.minecraft.world.level.block.state.BlockState state)
    {
        level.setBlock(position, state, UPDATE_CLIENTS);
    }

    private record SkyscraperPlacement(BlockPos offset, Rotation rotation) {}
}
