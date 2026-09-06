package com.projectseele.world;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LeavesBlock;
import net.minecraft.world.level.levelgen.Heightmap;

/** One explicit pass over fresh preview land, outside the retained urban footprint. */
public final class TvWorldSurfaceLandscape
{
    private static final int UPDATE = Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE;

    private TvWorldSurfaceLandscape() {}

    public static void finishChunk(ServerLevel level, ChunkPos chunk)
    {
        if (!TvWorldPreviewTerrain.active(level)) throw new IllegalArgumentException("TV preview only");
        level.getChunk(chunk.x, chunk.z);
        int minX = chunk.getMinBlockX(), minZ = chunk.getMinBlockZ();
        for (int z = minZ; z < minZ + 16; z++)
            for (int x = minX; x < minX + 16; x++)
            {
                if (insideCity(x, z, 0)) continue;
                int y = level.getHeight(Heightmap.Types.OCEAN_FLOOR, x, z) - 1;
                if (y < 40 || y > 210) continue;
                BlockPos top = new BlockPos(x, y, z);
                if (!natural(level.getBlockState(top).getBlock())) continue;
                for (int d = 0; d < 4; d++)
                {
                    BlockPos p = top.below(d);
                    if (!natural(level.getBlockState(p).getBlock())) break;
                    Block material = y <= 63 ? (d == 0 ? Blocks.GRAVEL : Blocks.SAND)
                            : d == 0 ? Blocks.GRASS_BLOCK : Blocks.DIRT;
                    level.setBlock(p, material.defaultBlockState(), UPDATE);
                }
            }
        for (int trial = 0; trial < 2; trial++)
        {
            long seed = mix(chunk.x * 3 + trial, chunk.z);
            int x = minX + 2 + (int) Math.floorMod(seed, 12);
            int z = minZ + 2 + (int) Math.floorMod(seed >>> 12, 12);
            if (insideCity(x, z, 60)) continue;
            double density = Math.max(blob(x, z, -310, -70, 260),
                    Math.max(blob(x, z, -320, 590, 290), blob(x, z, 350, 650, 310)));
            if (Math.floorMod(seed >>> 25, 1000) > 650 * density) continue;
            int y = level.getHeight(Heightmap.Types.OCEAN_FLOOR, x, z) - 1;
            if (y < 65 || !level.getBlockState(new BlockPos(x, y, z)).is(Blocks.GRASS_BLOCK)) continue;
            tree(level, new BlockPos(x, y, z), 7 + (int) Math.floorMod(seed >>> 35, 4), seed);
        }
    }

    private static void tree(ServerLevel level, BlockPos base, int height, long seed)
    {
        for (int y = 1; y <= height; y++)
            if (!level.getBlockState(base.above(y)).isAir()) return;
        Block trunk = Math.floorMod(seed, 6) == 0 ? Blocks.BIRCH_LOG : Blocks.OAK_LOG;
        for (int y = 1; y <= height; y++) level.setBlock(base.above(y), trunk.defaultBlockState(), UPDATE);
        var leaves = Blocks.OAK_LEAVES.defaultBlockState().setValue(LeavesBlock.PERSISTENT, true);
        for (int y = height - 4; y <= height + 2; y++)
            for (int z = -4; z <= 4; z++)
                for (int x = -4; x <= 4; x++)
                {
                    if ((x * x + z * z) / 16.0 + Math.pow((y - height + 1) / 3.5, 2) >= 1) continue;
                    BlockPos p = base.offset(x, y, z);
                    if (level.getBlockState(p).isAir()) level.setBlock(p, leaves, UPDATE);
                }
    }

    private static boolean natural(Block block)
    {
        return block == Blocks.STONE || block == Blocks.DIRT || block == Blocks.GRASS_BLOCK
                || block == Blocks.GRAVEL || block == Blocks.SAND || block == Blocks.COARSE_DIRT;
    }

    private static boolean insideCity(int x, int z, int margin)
    {
        return x >= -194 - margin && x <= 254 + margin && z >= -4 - margin && z <= 444 + margin;
    }

    private static double blob(int x, int z, int cx, int cz, int radius)
    {
        return Math.exp(-((double) (x - cx) * (x - cx) + (double) (z - cz) * (z - cz)) / (radius * radius));
    }

    private static long mix(int x, int z)
    {
        long value = x * 341873128712L ^ z * 132897987541L;
        value = (value ^ (value >>> 33)) * 0xff51afd7ed558ccdL;
        return value ^ (value >>> 33);
    }
}
