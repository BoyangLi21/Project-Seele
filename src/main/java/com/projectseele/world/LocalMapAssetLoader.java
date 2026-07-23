package com.projectseele.world;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Set;

import com.projectseele.ProjectSeele;
import net.minecraft.core.BlockPos;
import net.minecraft.core.SectionPos;
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
    private static final Vec3i SKYSCRAPER_TEMPLATE_SIZE =
            new Vec3i(23, 82, 12);
    private static final int UPDATE_CLIENTS = Block.UPDATE_CLIENTS;

    /**
     * Sparse, distinctive blocks sampled through the local 5,996-block
     * template. A state marker alone must never pass the city audit after the
     * building body was cleared or a travel placement failed.
     */
    private static final SkyscraperSignature[] SKYSCRAPER_SIGNATURES = {
            new SkyscraperSignature(new BlockPos(21, 8, 2),
                    Blocks.REDSTONE_LAMP),
            new SkyscraperSignature(new BlockPos(1, 9, 7),
                    Blocks.REDSTONE_LAMP),
            new SkyscraperSignature(new BlockPos(1, 53, 3),
                    Blocks.REDSTONE_LAMP),
            new SkyscraperSignature(new BlockPos(21, 53, 8),
                    Blocks.REDSTONE_LAMP),
            new SkyscraperSignature(new BlockPos(18, 74, 7),
                    Blocks.END_ROD),
            new SkyscraperSignature(new BlockPos(19, 74, 8),
                    Blocks.END_ROD),
            new SkyscraperSignature(new BlockPos(5, 80, 3),
                    Blocks.LIGHTNING_ROD),
    };

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
        if (!template.getSize().equals(SKYSCRAPER_TEMPLATE_SIZE))
        {
            ProjectSeele.LOGGER.error(
                    "Private Tokyo-3 skyscraper template size changed: expected={} actual={}",
                    SKYSCRAPER_TEMPLATE_SIZE, template.getSize());
            return 0;
        }

        int placed = 0;
        for (int index = 0; index < SKYSCRAPERS.length; index++)
        {
            SkyscraperPlacement placement = SKYSCRAPERS[index];
            Vec3i rotatedSize = template.getSize(placement.rotation());
            int drop = skyscraperDrop(placement, rotatedSize, retractionDepth);
            BlockPos surfaceBase = tokyo3Origin.offset(placement.offset());
            BlockPos base = surfaceBase.below(drop);
            BlockPos travelMarker = skyscraperMarker(base, index);
            BlockPos stateMarker = skyscraperStateMarker(tokyo3Origin, index);

            boolean travelPresent = level.getBlockState(travelMarker)
                    .is(Blocks.NETHERITE_BLOCK);
            boolean bodyPresent = skyscraperBodyPresent(
                    level, base, placement.rotation());
            if (travelPresent && bodyPresent)
            {
                if (!level.getBlockState(stateMarker).is(Blocks.LODESTONE))
                {
                    set(level, stateMarker, Blocks.LODESTONE.defaultBlockState());
                }
                placed++;
                continue;
            }

            // The state marker is only a completion receipt. Invalidate it
            // before clearing or writing any part of the real building.
            set(level, stateMarker, Blocks.AIR.defaultBlockState());
            clearStaleSkyscraperCopies(level, tokyo3Origin, placement,
                    template.getSize(), index, base);
            clearSkyscraperVolume(level, base, template.getSize(),
                    placement.rotation());
            set(level, travelMarker, Blocks.AIR.defaultBlockState());

            boolean written = place(level, template, base, placement.rotation());
            if (written && skyscraperBodyPresent(
                    level, base, placement.rotation()))
            {
                set(level, travelMarker, Blocks.NETHERITE_BLOCK.defaultBlockState());
                set(level, stateMarker, Blocks.LODESTONE.defaultBlockState());
                placed++;
            }
            else
            {
                // A partial write must remain visibly incomplete so the next
                // setup/ensure pass retries it instead of trusting stale NBT.
                set(level, travelMarker, Blocks.AIR.defaultBlockState());
                set(level, stateMarker, Blocks.AIR.defaultBlockState());
                ProjectSeele.LOGGER.error(
                        "Private Tokyo-3 skyscraper {} failed structural placement at {} depth={}",
                        index, base, retractionDepth);
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
        if (!template.getSize().equals(SKYSCRAPER_TEMPLATE_SIZE))
        {
            ProjectSeele.LOGGER.error(
                    "Private Tokyo-3 skyscraper travel refused: expected size={} actual={}",
                    SKYSCRAPER_TEMPLATE_SIZE, template.getSize());
            return;
        }

        for (int index = 0; index < SKYSCRAPERS.length; index++)
        {
            SkyscraperPlacement placement = SKYSCRAPERS[index];
            Vec3i rotatedSize = template.getSize(placement.rotation());
            int oldDrop = skyscraperDrop(placement, rotatedSize, oldDepth);
            int newDrop = skyscraperDrop(placement, rotatedSize, newDepth);
            BlockPos surfaceBase = tokyo3Origin.offset(placement.offset());
            BlockPos oldBase = surfaceBase.below(oldDrop);
            BlockPos newBase = surfaceBase.below(newDrop);
            BlockPos stateMarker = skyscraperStateMarker(tokyo3Origin, index);

            if (oldDrop == newDrop)
            {
                BlockPos travelMarker = skyscraperMarker(newBase, index);
                if (level.getBlockState(travelMarker).is(Blocks.NETHERITE_BLOCK)
                        && skyscraperBodyPresent(
                        level, newBase, placement.rotation()))
                {
                    set(level, stateMarker, Blocks.LODESTONE.defaultBlockState());
                    continue;
                }

                // A vanished body can be detected between twelve-block travel
                // steps. Repair it at the authoritative SavedData depth now.
                set(level, stateMarker, Blocks.AIR.defaultBlockState());
                clearStaleSkyscraperCopies(level, tokyo3Origin, placement,
                        template.getSize(), index, newBase);
                clearSkyscraperVolume(level, newBase, template.getSize(),
                        placement.rotation());
                set(level, travelMarker, Blocks.AIR.defaultBlockState());
                if (place(level, template, newBase, placement.rotation())
                        && skyscraperBodyPresent(
                        level, newBase, placement.rotation()))
                {
                    set(level, travelMarker,
                            Blocks.NETHERITE_BLOCK.defaultBlockState());
                    set(level, stateMarker, Blocks.LODESTONE.defaultBlockState());
                }
                else
                {
                    set(level, travelMarker, Blocks.AIR.defaultBlockState());
                    ProjectSeele.LOGGER.error(
                            "Private Tokyo-3 skyscraper {} failed repair at depth {}",
                            index, newDepth);
                }
                continue;
            }

            // Clear the completion receipt before the destructive half of a
            // move. A crash or failed write can therefore never look complete.
            set(level, stateMarker, Blocks.AIR.defaultBlockState());
            clearSkyscraperVolume(level, oldBase, template.getSize(),
                    placement.rotation());
            set(level, skyscraperMarker(oldBase, index),
                    Blocks.AIR.defaultBlockState());
            clearSkyscraperVolume(level, newBase, template.getSize(),
                    placement.rotation());
            set(level, skyscraperMarker(newBase, index),
                    Blocks.AIR.defaultBlockState());

            boolean moved = place(level, template, newBase, placement.rotation())
                    && skyscraperBodyPresent(
                    level, newBase, placement.rotation());
            if (moved)
            {
                set(level, skyscraperMarker(newBase, index),
                        Blocks.NETHERITE_BLOCK.defaultBlockState());
                set(level, stateMarker, Blocks.LODESTONE.defaultBlockState());
                continue;
            }

            // Remove any partial destination write, then make a best-effort
            // rollback. The state marker deliberately remains absent even when
            // rollback succeeds, forcing the next pass to reconcile SavedData.
            clearSkyscraperVolume(level, newBase, template.getSize(),
                    placement.rotation());
            set(level, skyscraperMarker(newBase, index),
                    Blocks.AIR.defaultBlockState());
            clearSkyscraperVolume(level, oldBase, template.getSize(),
                    placement.rotation());
            boolean restored = place(
                    level, template, oldBase, placement.rotation())
                    && skyscraperBodyPresent(
                    level, oldBase, placement.rotation());
            set(level, skyscraperMarker(oldBase, index), restored
                    ? Blocks.NETHERITE_BLOCK.defaultBlockState()
                    : Blocks.AIR.defaultBlockState());
            set(level, stateMarker, Blocks.AIR.defaultBlockState());
            ProjectSeele.LOGGER.error(
                    "Private Tokyo-3 skyscraper {} failed to move depth {} -> {}; restoredOld={}",
                    index, oldDepth, newDepth, restored);
        }
    }

    public static int inspectTokyo3Skyscrapers(BlockGetter level,
                                               BlockPos tokyo3Origin)
    {
        return inspectTokyo3Skyscrapers(level, tokyo3Origin, 0);
    }

    /**
     * Counts only complete buildings at the position implied by the current
     * persisted retraction depth. A remote completion marker cannot mask a
     * missing body or a tower stranded at a previous travel quantum.
     */
    public static int inspectTokyo3Skyscrapers(BlockGetter level,
                                               BlockPos tokyo3Origin,
                                               int retractionDepth)
    {
        int found = 0;
        for (int index = 0; index < SKYSCRAPERS.length; index++)
        {
            SkyscraperPlacement placement = SKYSCRAPERS[index];
            Vec3i rotatedSize = rotatedSkyscraperSize(placement.rotation());
            int drop = skyscraperDrop(placement, rotatedSize, retractionDepth);
            BlockPos base = tokyo3Origin.offset(placement.offset()).below(drop);
            if (level.getBlockState(skyscraperStateMarker(tokyo3Origin, index))
                    .is(Blocks.LODESTONE)
                    && level.getBlockState(skyscraperMarker(base, index))
                    .is(Blocks.NETHERITE_BLOCK)
                    && skyscraperBodyPresent(
                    level, base, placement.rotation()))
            {
                found++;
            }
        }
        return found;
    }

    /** Adds every chunk touched by the three rotated private high-rises. */
    public static void addTokyo3SkyscraperTravelChunks(
            BlockPos tokyo3Origin, Set<Long> chunks)
    {
        for (SkyscraperPlacement placement : SKYSCRAPERS)
        {
            SkyscraperBounds bounds = skyscraperBounds(placement.rotation());
            int baseX = tokyo3Origin.getX() + placement.offset().getX();
            int baseZ = tokyo3Origin.getZ() + placement.offset().getZ();
            for (int chunkX = SectionPos.blockToSectionCoord(
                    baseX + bounds.minimumX());
                 chunkX <= SectionPos.blockToSectionCoord(
                         baseX + bounds.maximumX()); chunkX++)
            {
                for (int chunkZ = SectionPos.blockToSectionCoord(
                        baseZ + bounds.minimumZ());
                     chunkZ <= SectionPos.blockToSectionCoord(
                             baseZ + bounds.maximumZ()); chunkZ++)
                {
                    chunks.add(net.minecraft.world.level.ChunkPos.asLong(
                            chunkX, chunkZ));
                }
            }
        }
    }

    private static boolean skyscraperBodyPresent(BlockGetter level,
                                                  BlockPos base,
                                                  Rotation rotation)
    {
        for (SkyscraperSignature signature : SKYSCRAPER_SIGNATURES)
        {
            BlockPos transformed = StructureTemplate.transform(
                    signature.offset(), Mirror.NONE, rotation, BlockPos.ZERO);
            if (!level.getBlockState(base.offset(transformed))
                    .is(signature.block()))
            {
                return false;
            }
        }
        return true;
    }

    private static Vec3i rotatedSkyscraperSize(Rotation rotation)
    {
        if (rotation == Rotation.CLOCKWISE_90
                || rotation == Rotation.COUNTERCLOCKWISE_90)
        {
            return new Vec3i(SKYSCRAPER_TEMPLATE_SIZE.getZ(),
                    SKYSCRAPER_TEMPLATE_SIZE.getY(),
                    SKYSCRAPER_TEMPLATE_SIZE.getX());
        }
        return SKYSCRAPER_TEMPLATE_SIZE;
    }

    /**
     * Removes complete private-template copies left at an earlier travel quantum.
     * Either our receipt or all seven body signatures is required, allowing
     * schema upgrades to remove legacy unmarked surface duplicates safely.
     */
    private static void clearStaleSkyscraperCopies(ServerLevel level,
                                                   BlockPos tokyo3Origin,
                                                   SkyscraperPlacement placement,
                                                   Vec3i templateSize,
                                                   int index,
                                                   BlockPos expectedBase)
    {
        Vec3i rotatedSize = rotatedSkyscraperSize(placement.rotation());
        BlockPos surfaceBase = tokyo3Origin.offset(placement.offset());
        int previousDrop = Integer.MIN_VALUE;
        int maximumDepth = ThirdTokyoSurfaceBuilder.maximumRetractionDepth();
        for (int depth = 0; depth <= maximumDepth; depth++)
        {
            int drop = skyscraperDrop(placement, rotatedSize, depth);
            if (drop == previousDrop)
            {
                continue;
            }
            previousDrop = drop;
            BlockPos candidate = surfaceBase.below(drop);
            if (!candidate.equals(expectedBase)
                    && (level.getBlockState(skyscraperMarker(candidate, index))
                    .is(Blocks.NETHERITE_BLOCK)
                    || skyscraperBodyPresent(
                            level, candidate, placement.rotation())))
            {
                clearSkyscraperVolume(level, candidate, templateSize,
                        placement.rotation());
                set(level, skyscraperMarker(candidate, index),
                        Blocks.AIR.defaultBlockState());
            }
        }
    }

    /**
     * Rotation happens around the template origin, so clockwise variants can
     * occupy negative relative X/Z. Clear the transformed bounds rather than a
     * positive-only box beginning at the placement origin.
     */
    private static void clearSkyscraperVolume(ServerLevel level, BlockPos base,
                                              Vec3i templateSize,
                                              Rotation rotation)
    {
        int maximumX = templateSize.getX() - 1;
        int maximumZ = templateSize.getZ() - 1;
        int minimumRelativeX = Integer.MAX_VALUE;
        int maximumRelativeX = Integer.MIN_VALUE;
        int minimumRelativeZ = Integer.MAX_VALUE;
        int maximumRelativeZ = Integer.MIN_VALUE;
        for (int x : new int[] {0, maximumX})
        {
            for (int z : new int[] {0, maximumZ})
            {
                BlockPos transformed = StructureTemplate.transform(
                        new BlockPos(x, 0, z), Mirror.NONE, rotation,
                        BlockPos.ZERO);
                minimumRelativeX = Math.min(minimumRelativeX, transformed.getX());
                maximumRelativeX = Math.max(maximumRelativeX, transformed.getX());
                minimumRelativeZ = Math.min(minimumRelativeZ, transformed.getZ());
                maximumRelativeZ = Math.max(maximumRelativeZ, transformed.getZ());
            }
        }

        for (int x = minimumRelativeX; x <= maximumRelativeX; x++)
        {
            for (int z = minimumRelativeZ; z <= maximumRelativeZ; z++)
            {
                for (int y = 0; y < templateSize.getY(); y++)
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

    private static int skyscraperDrop(SkyscraperPlacement placement,
                                      Vec3i size, int depth)
    {
        SkyscraperBounds bounds = skyscraperBounds(placement.rotation());
        int minimumX = placement.offset().getX() + bounds.minimumX();
        int maximumX = placement.offset().getX() + bounds.maximumX();
        int minimumZ = placement.offset().getZ() + bounds.minimumZ();
        int maximumZ = placement.offset().getZ() + bounds.maximumZ();
        int topAtSurface = placement.offset().getY() + size.getY() - 1;
        int targetDrop = Math.max(0, topAtSurface
                - ThirdTokyoSurfaceBuilder.ceilingRoofRelativeYForBounds(
                        minimumX, maximumX, minimumZ, maximumZ));
        int bounded = Math.max(0, Math.min(depth, targetDrop));
        if (bounded == targetDrop)
        {
            return targetDrop;
        }
        return bounded / SKYSCRAPER_MOVE_QUANTUM * SKYSCRAPER_MOVE_QUANTUM;
    }

    private static SkyscraperBounds skyscraperBounds(Rotation rotation)
    {
        int maximumX = SKYSCRAPER_TEMPLATE_SIZE.getX() - 1;
        int maximumZ = SKYSCRAPER_TEMPLATE_SIZE.getZ() - 1;
        int minimumRelativeX = Integer.MAX_VALUE;
        int maximumRelativeX = Integer.MIN_VALUE;
        int minimumRelativeZ = Integer.MAX_VALUE;
        int maximumRelativeZ = Integer.MIN_VALUE;
        for (int x : new int[] {0, maximumX})
        {
            for (int z : new int[] {0, maximumZ})
            {
                BlockPos transformed = StructureTemplate.transform(
                        new BlockPos(x, 0, z), Mirror.NONE, rotation,
                        BlockPos.ZERO);
                minimumRelativeX = Math.min(minimumRelativeX, transformed.getX());
                maximumRelativeX = Math.max(maximumRelativeX, transformed.getX());
                minimumRelativeZ = Math.min(minimumRelativeZ, transformed.getZ());
                maximumRelativeZ = Math.max(maximumRelativeZ, transformed.getZ());
            }
        }
        return new SkyscraperBounds(minimumRelativeX, maximumRelativeX,
                minimumRelativeZ, maximumRelativeZ);
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

    private record SkyscraperSignature(BlockPos offset, Block block) {}

    private record SkyscraperBounds(int minimumX, int maximumX,
                                    int minimumZ, int maximumZ) {}
}
