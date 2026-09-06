package com.projectseele.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.world.*;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.LevelResource;

import java.nio.file.Files;
import java.util.HashMap;
import java.util.Map;

/** Short real mid-layer reversal before the explicitly requested coast preparation. */
final class TvCityReversalCheck
{
    private static int stage, age;
    private static boolean done;

    static boolean tick(ServerLevel level) throws Exception
    {
        if (done) return true;
        if (++age > 2400) throw new IllegalStateException("City reversal check timed out");
        BlockPos origin = IntegratedNervMapBuilder.TOKYO3_ORIGIN;
        var data = Tokyo3RetractionSavedData.get(level);
        var status = Tokyo3RetractionDirector.status(level, origin);
        if (stage == 0)
        {
            if (status.depth() != 0 || status.targetDepth() != 0)
                throw new IllegalStateException("Reversal check requires the restored city");
            if (!Tokyo3RetractionDirector.request(level, origin, true).accepted())
                throw new IllegalStateException("Reversal descent refused");
            stage = 1;
            return false;
        }
        var stored = data.get(origin).orElseThrow();
        if (stage == 1)
        {
            if (stored.depth() < 2 || stored.cursor() == 0 && stored.voxelCursor() == 0) return false;
            Map<BlockPos, BlockState> before = roofs(level, stored.depth());
            Tokyo3RetractionDirector.register(level, origin);
            var result = Tokyo3RetractionDirector.request(level, origin, false);
            if (!result.accepted() || !before.equals(roofs(level, stored.depth())))
                throw new IllegalStateException("Register/reversal changed the in-flight roof geometry");
            ProjectSeele.LOGGER.info("TV CITY REVERSAL queued inside layer depth={} cursor={} protectedRoofCells={}",
                    stored.depth(), stored.cursor(), before.size());
            stage = 2;
            return false;
        }
        if (status.depth() != 0 || status.targetDepth() != 0 || stored.cursor() != 0 || stored.voxelCursor() != 0)
            return false;
        if (!ThirdTokyoSurfaceBuilder.inspect(level, origin, 0).valid()
                || LocalMapAssetLoader.inspectTokyo3Skyscrapers(level, origin, 0) != 3
                || LocalMapAssetLoader.inspectTokyo3CargoMismatches(level, origin, 0) != 0)
            throw new IllegalStateException("Reversal did not restore complete city cargo");
        Files.writeString(level.getServer().getWorldPath(LevelResource.ROOT).resolve("tv_preview_city_reversal_checks.txt"),
                "PASS: mid-layer register and reversal preserved roof cells; 93+3 buildings restored\n");
        ProjectSeele.LOGGER.info("TV CITY REVERSAL PASS: complete cargo restored");
        done = true;
        return true;
    }

    private static Map<BlockPos, BlockState> roofs(ServerLevel level, int depth)
    {
        Map<BlockPos, BlockState> result = new HashMap<>();
        for (var tower : ThirdTokyoSurfaceBuilder.movableBuildings(level))
        {
            BlockPos roof = IntegratedNervMapBuilder.TOKYO3_ORIGIN.offset(tower.x(), tower.height() + 1 - depth, tower.z());
            for (int dy = -1; dy <= 2; dy++)
                for (int x = -tower.halfSize(); x <= tower.halfSize(); x++)
                    for (int z = -tower.halfSize(); z <= tower.halfSize(); z++)
                    {
                        BlockPos pos = roof.offset(x, dy, z);
                        result.put(pos, level.getBlockState(pos));
                    }
        }
        return result;
    }
}
