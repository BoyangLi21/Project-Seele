package com.projectseele.mcp;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.projectseele.config.SeeleConfig;
import com.projectseele.world.FacilityWorldPolicy;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.level.levelgen.Heightmap;

/**
 * Terrain inspection and staged, reversible voxel construction for MCP.
 *
 * <p>This service intentionally refuses every generic write in Project
 * SEELE's protected facility saves. Those worlds remain governed by
 * MAP_EDITING_PROTOCOL.md and their existing deterministic builders.</p>
 */
final class SeeleMcpBuildService
{
    private static final long PLAN_TTL_MS = 10 * 60 * 1000L;
    private static final int MAX_CACHED_PLANS = 16;
    private static final int MAX_RECENT_JOBS = 24;

    private static final LinkedHashMap<String, PreparedPlan> PLAN_CACHE =
            new LinkedHashMap<>();
    private static final LinkedHashMap<String, BuildJob> RECENT_JOBS =
            new LinkedHashMap<>();
    private static BuildJob activeJob;
    private static UndoBatch lastUndo;

    private SeeleMcpBuildService() {}

    static JsonObject session(MinecraftServer server)
    {
        ServerPlayer player = activePlayer(server);
        if (player == null)
        {
            return error("NO_ACTIVE_PLAYER",
                    "Join a local world before using Minecraft MCP tools.");
        }
        JsonObject result = new JsonObject();
        result.addProperty("project", "Project SEELE");
        result.addProperty("minecraftVersion", "1.20.1");
        result.addProperty("loader", "Forge 47.4.10");
        result.addProperty("player", player.getGameProfile().getName());
        result.addProperty("dimension",
                player.serverLevel().dimension().location().toString());
        result.add("position", vector(player.blockPosition()));
        result.addProperty("gameMode",
                player.gameMode.getGameModeForPlayer().getName());
        result.addProperty("mutationAllowed", mutationAllowed(server));
        result.addProperty("bridgeEnabled", SeeleMcpBridge.isEnabled());
        return result;
    }

    static JsonObject seeleStatus(MinecraftServer server)
    {
        JsonObject result = new JsonObject();
        result.addProperty("project", "Project SEELE");
        result.addProperty("bridgeEnabled", SeeleMcpBridge.isEnabled());
        result.addProperty("bridgeResponsive",
                SeeleMcpBridge.isServerResponsive());
        result.addProperty("cleanRebuild",
                FacilityWorldPolicy.isCleanRebuild(server));
        result.addProperty("s20Rebuild",
                FacilityWorldPolicy.isS20Rebuild(server));
        result.addProperty("spatialPreviewFrozen",
                FacilityWorldPolicy.isSpatialPreviewFrozen(server));
        result.addProperty("readOnlyArchive",
                FacilityWorldPolicy.isReadOnlyBrokenArchive(server));
        result.addProperty("genericMcpMutationAllowed",
                mutationAllowed(server));
        result.addProperty("activeBuild",
                activeJob == null ? "" : activeJob.id);
        result.addProperty("cachedPlans", PLAN_CACHE.size());
        result.addProperty("players", server.getPlayerCount());
        return result;
    }

    static JsonObject buildsite(MinecraftServer server, JsonObject body)
    {
        ServerPlayer player = activePlayer(server);
        if (player == null)
        {
            return error("NO_ACTIVE_PLAYER",
                    "Join a local world before scanning a build site.");
        }
        int radius = clamp(intOr(body, "radius", 24), 4, 64);
        int step = Math.max(1, (int) Math.ceil(radius / 8.0D));
        ServerLevel level = player.serverLevel();
        BlockPos center = player.blockPosition();
        int minY = Integer.MAX_VALUE;
        int maxY = Integer.MIN_VALUE;
        long totalY = 0L;
        int count = 0;
        JsonArray samples = new JsonArray();
        for (int dx = -radius; dx <= radius; dx += step)
        {
            for (int dz = -radius; dz <= radius; dz += step)
            {
                int x = center.getX() + dx;
                int z = center.getZ() + dz;
                int y = level.getHeight(
                        Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x, z) - 1;
                y = Math.max(level.getMinBuildHeight(), y);
                BlockPos surface = new BlockPos(x, y, z);
                BlockState state = level.getBlockState(surface);
                JsonObject sample = new JsonObject();
                sample.addProperty("dx", dx);
                sample.addProperty("dz", dz);
                sample.addProperty("dy", y - center.getY());
                sample.addProperty("y", y);
                sample.addProperty("block", blockId(state));
                samples.add(sample);
                minY = Math.min(minY, y);
                maxY = Math.max(maxY, y);
                totalY += y;
                count++;
            }
        }
        JsonObject result = new JsonObject();
        result.addProperty("dimension",
                level.dimension().location().toString());
        result.add("center", vector(center));
        result.addProperty("radius", radius);
        result.addProperty("sampleStep", step);
        result.addProperty("sampleCount", count);
        result.addProperty("minSurfaceY", minY);
        result.addProperty("maxSurfaceY", maxY);
        result.addProperty("averageSurfaceY",
                count == 0 ? center.getY() : totalY / (double) count);
        result.addProperty("minDy", minY - center.getY());
        result.addProperty("maxDy", maxY - center.getY());
        result.addProperty("mutationAllowed", mutationAllowed(server));
        result.add("samples", samples);
        return result;
    }

    static JsonObject preview(MinecraftServer server, JsonObject body)
    {
        try
        {
            purgeExpiredPlans();
            PreparedPlan plan = compilePlan(server, unwrapPlan(body));
            PLAN_CACHE.put(plan.id, plan);
            trimOldest(PLAN_CACHE, MAX_CACHED_PLANS);
            return previewResult(plan, mutationAllowed(server));
        }
        catch (PlanException exception)
        {
            return error(exception.code, exception.getMessage());
        }
    }

    static JsonObject execute(MinecraftServer server, JsonObject body)
    {
        if (!mutationAllowed(server))
        {
            return protectedWorldError();
        }
        if (activeJob != null && activeJob.isRunning())
        {
            return error("BUILD_BUSY",
                    "A staged MCP build is already running: " + activeJob.id);
        }
        try
        {
            purgeExpiredPlans();
            PreparedPlan plan;
            String requestedId = stringOr(body, "executePlanId", "").trim();
            if (!requestedId.isEmpty())
            {
                plan = PLAN_CACHE.get(requestedId);
                if (plan == null)
                {
                    return error("PLAN_NOT_FOUND",
                            "The preview plan is missing or expired: "
                                    + requestedId);
                }
            }
            else
            {
                plan = compilePlan(server, unwrapPlan(body));
            }
            ServerLevel level = server.getLevel(plan.dimension);
            if (level == null)
            {
                return error("DIMENSION_UNAVAILABLE",
                        "The previewed dimension is not loaded.");
            }
            activeJob = BuildJob.build(plan);
            RECENT_JOBS.put(activeJob.id, activeJob);
            trimOldest(RECENT_JOBS, MAX_RECENT_JOBS);
            JsonObject result = jobResult(activeJob);
            result.addProperty("message",
                    "Build queued. Poll minecraft_batch_status until complete.");
            return result;
        }
        catch (PlanException exception)
        {
            return error(exception.code, exception.getMessage());
        }
    }

    static JsonObject batchStatus(JsonObject body)
    {
        String requestedId = stringOr(body, "jobId", "").trim();
        BuildJob job = requestedId.isEmpty() ? activeJob
                : RECENT_JOBS.get(requestedId);
        if (job == null)
        {
            return error("JOB_NOT_FOUND",
                    requestedId.isEmpty()
                            ? "There is no active or recent MCP build."
                            : "Unknown MCP build job: " + requestedId);
        }
        return jobResult(job);
    }

    static JsonObject undo(MinecraftServer server)
    {
        if (activeJob != null && activeJob.isRunning())
        {
            return error("BUILD_BUSY",
                    "Wait for the active build to finish before undoing it.");
        }
        if (lastUndo == null || lastUndo.placements.isEmpty())
        {
            return error("NOTHING_TO_UNDO",
                    "No completed MCP build is available to undo.");
        }
        ServerLevel level = server.getLevel(lastUndo.dimension);
        if (level == null)
        {
            return error("DIMENSION_UNAVAILABLE",
                    "The undo dimension is not loaded.");
        }
        activeJob = BuildJob.undo(lastUndo);
        RECENT_JOBS.put(activeJob.id, activeJob);
        trimOldest(RECENT_JOBS, MAX_RECENT_JOBS);
        lastUndo = null;
        JsonObject result = jobResult(activeJob);
        result.addProperty("message",
                "Undo queued. Poll minecraft_batch_status until complete.");
        return result;
    }

    static void tick(MinecraftServer server)
    {
        BuildJob job = activeJob;
        if (job == null || !job.isRunning())
        {
            return;
        }
        ServerLevel level = server.getLevel(job.dimension);
        if (level == null)
        {
            job.fail("Target dimension is no longer loaded.");
            activeJob = null;
            return;
        }
        int budget = SeeleConfig.MCP_BLOCKS_PER_TICK.get();
        try
        {
            while (budget-- > 0 && job.cursor < job.placements.size())
            {
                Placement placement = job.placements.get(job.cursor);
                if (!job.restoreMode)
                {
                    long key = placement.position.asLong();
                    if (!job.snapshots.containsKey(key))
                    {
                        job.snapshots.put(key,
                                snapshot(level, placement.position));
                    }
                }
                apply(level, placement);
                job.cursor++;
            }
            if (job.cursor >= job.placements.size())
            {
                job.complete();
                if (!job.restoreMode)
                {
                    lastUndo = undoBatch(job);
                }
                activeJob = null;
            }
        }
        catch (RuntimeException exception)
        {
            job.fail(exception.getMessage());
            if (!job.restoreMode && !job.snapshots.isEmpty())
            {
                lastUndo = undoBatch(job);
            }
            activeJob = null;
        }
    }

    static void shutdown(MinecraftServer server)
    {
        BuildJob job = activeJob;
        if (job == null || server == null)
        {
            resetRuntime();
            return;
        }
        ServerLevel level = server.getLevel(job.dimension);
        if (level != null)
        {
            if (job.restoreMode)
            {
                while (job.cursor < job.placements.size())
                {
                    apply(level, job.placements.get(job.cursor++));
                }
            }
            else
            {
                List<Map.Entry<Long, Snapshot>> entries =
                        new ArrayList<>(job.snapshots.entrySet());
                Collections.reverse(entries);
                for (Map.Entry<Long, Snapshot> entry : entries)
                {
                    Snapshot original = entry.getValue();
                    apply(level, new Placement(BlockPos.of(entry.getKey()),
                            original.state, original.blockEntityTag));
                }
            }
        }
        resetRuntime();
    }

    private static void resetRuntime()
    {
        PLAN_CACHE.clear();
        RECENT_JOBS.clear();
        activeJob = null;
        lastUndo = null;
    }

    private static PreparedPlan compilePlan(MinecraftServer server,
                                            JsonObject plan)
            throws PlanException
    {
        ServerPlayer player = activePlayer(server);
        if (player == null)
        {
            throw new PlanException("NO_ACTIVE_PLAYER",
                    "Join a local world before preparing a build plan.");
        }
        if (plan == null)
        {
            throw new PlanException("INVALID_PLAN",
                    "A build plan JSON object is required.");
        }
        ServerLevel level = player.serverLevel();
        String coordMode = stringOr(plan, "coordMode", "relative")
                .trim().toLowerCase(Locale.ROOT);
        BlockPos suppliedOrigin = readVector(plan.get("origin"),
                BlockPos.ZERO, "origin");
        BlockPos origin;
        if (coordMode.equals("absolute"))
        {
            if (!plan.has("origin"))
            {
                throw new PlanException("ORIGIN_REQUIRED",
                        "coordMode=absolute requires origin.");
            }
            origin = suppliedOrigin;
        }
        else if (coordMode.equals("relative"))
        {
            origin = player.blockPosition().offset(suppliedOrigin);
        }
        else
        {
            throw new PlanException("INVALID_COORD_MODE",
                    "coordMode must be relative or absolute.");
        }
        int rotation = normalizeRotation(intOr(plan, "rotation", 0));
        Map<String, String> palette = parsePalette(plan);
        LinkedHashMap<Long, Placement> placements = new LinkedHashMap<>();
        CompileContext context = new CompileContext(level, origin, rotation,
                palette, placements);

        compileVolumes(plan.getAsJsonArray("clearVolumes"),
                "minecraft:air", context);
        compileCuboids(plan.getAsJsonArray("cuboids"), context);
        compileBlocks(plan.getAsJsonArray("blocks"), context);
        JsonArray steps = plan.getAsJsonArray("steps");
        if (steps != null)
        {
            for (JsonElement element : steps)
            {
                if (!element.isJsonObject())
                {
                    throw new PlanException("INVALID_STEP",
                            "Every steps entry must be an object.");
                }
                JsonObject step = element.getAsJsonObject();
                compileVolumes(step.getAsJsonArray("clearVolumes"),
                        "minecraft:air", context);
                compileCuboids(step.getAsJsonArray("cuboids"), context);
                compileBlocks(step.getAsJsonArray("blocks"), context);
            }
        }
        if (placements.isEmpty())
        {
            throw new PlanException("EMPTY_PLAN",
                    "The build plan contains no blocks or cuboids.");
        }
        List<Placement> ordered = new ArrayList<>(placements.values());
        ordered.sort(Comparator
                .comparingInt((Placement value) -> value.position.getY())
                .thenComparingInt(value -> value.position.getX())
                .thenComparingInt(value -> value.position.getZ()));
        Bounds bounds = Bounds.of(ordered);
        String id = "seele-plan-" + UUID.randomUUID();
        String summary = stringOr(plan, "summary", "MCP voxel build");
        return new PreparedPlan(id, summary, level.dimension(), origin,
                rotation, ordered, bounds, System.currentTimeMillis());
    }

    private static JsonObject unwrapPlan(JsonObject body)
    {
        if (body != null && body.has("plan") && body.get("plan").isJsonObject())
        {
            return body.getAsJsonObject("plan");
        }
        return body;
    }

    private static Map<String, String> parsePalette(JsonObject plan)
            throws PlanException
    {
        LinkedHashMap<String, String> palette = new LinkedHashMap<>();
        if (!plan.has("palette"))
        {
            return palette;
        }
        if (!plan.get("palette").isJsonObject())
        {
            throw new PlanException("INVALID_PALETTE",
                    "palette must be a JSON object.");
        }
        for (Map.Entry<String, JsonElement> entry
                : plan.getAsJsonObject("palette").entrySet())
        {
            if (!entry.getValue().isJsonPrimitive())
            {
                throw new PlanException("INVALID_PALETTE",
                        "Palette values must be block-state strings.");
            }
            palette.put(entry.getKey(), entry.getValue().getAsString());
        }
        return palette;
    }

    private static void compileVolumes(JsonArray array, String forcedBlock,
                                       CompileContext context)
            throws PlanException
    {
        if (array == null)
        {
            return;
        }
        for (JsonElement element : array)
        {
            if (!element.isJsonObject())
            {
                throw new PlanException("INVALID_CUBOID",
                        "Every clearVolumes entry must be an object.");
            }
            compileCuboid(element.getAsJsonObject(), forcedBlock, context);
        }
    }

    private static void compileCuboids(JsonArray array,
                                       CompileContext context)
            throws PlanException
    {
        if (array == null)
        {
            return;
        }
        for (JsonElement element : array)
        {
            if (!element.isJsonObject())
            {
                throw new PlanException("INVALID_CUBOID",
                        "Every cuboids entry must be an object.");
            }
            compileCuboid(element.getAsJsonObject(), null, context);
        }
    }

    private static void compileCuboid(JsonObject cuboid, String forcedBlock,
                                      CompileContext context)
            throws PlanException
    {
        BlockPos from = readVector(cuboid.get("from"), null, "cuboid.from");
        BlockPos to = readVector(cuboid.get("to"), null, "cuboid.to");
        String rawBlock = forcedBlock == null
                ? stringOr(cuboid, "block", "") : forcedBlock;
        BlockState state = resolveBlockState(rawBlock, context.palette);
        boolean hollow = booleanOr(cuboid, "hollow", false);
        int minX = Math.min(from.getX(), to.getX());
        int maxX = Math.max(from.getX(), to.getX());
        int minY = Math.min(from.getY(), to.getY());
        int maxY = Math.max(from.getY(), to.getY());
        int minZ = Math.min(from.getZ(), to.getZ());
        int maxZ = Math.max(from.getZ(), to.getZ());
        validateLocalBounds(context, minX, maxX, minY, maxY, minZ, maxZ);
        long dx = (long) maxX - minX + 1L;
        long dy = (long) maxY - minY + 1L;
        long dz = (long) maxZ - minZ + 1L;
        long estimated = dx * dy * dz;
        if (hollow && dx > 2L && dy > 2L && dz > 2L)
        {
            estimated -= (dx - 2L) * (dy - 2L) * (dz - 2L);
        }
        ensurePlanCapacity(context, estimated);
        if (!hollow)
        {
            for (int x = minX; x <= maxX; x++)
            {
                for (int y = minY; y <= maxY; y++)
                {
                    for (int z = minZ; z <= maxZ; z++)
                    {
                        put(context, new BlockPos(x, y, z), state);
                    }
                }
            }
            return;
        }
        for (int x = minX; x <= maxX; x++)
        {
            for (int y = minY; y <= maxY; y++)
            {
                put(context, new BlockPos(x, y, minZ), state);
                put(context, new BlockPos(x, y, maxZ), state);
            }
        }
        for (int x = minX; x <= maxX; x++)
        {
            for (int z = minZ; z <= maxZ; z++)
            {
                put(context, new BlockPos(x, minY, z), state);
                put(context, new BlockPos(x, maxY, z), state);
            }
        }
        for (int y = minY; y <= maxY; y++)
        {
            for (int z = minZ; z <= maxZ; z++)
            {
                put(context, new BlockPos(minX, y, z), state);
                put(context, new BlockPos(maxX, y, z), state);
            }
        }
    }

    private static void compileBlocks(JsonArray array,
                                      CompileContext context)
            throws PlanException
    {
        if (array == null)
        {
            return;
        }
        ensurePlanCapacity(context, array.size());
        for (JsonElement element : array)
        {
            if (!element.isJsonObject())
            {
                throw new PlanException("INVALID_BLOCK",
                        "Every blocks entry must be an object.");
            }
            JsonObject block = element.getAsJsonObject();
            BlockPos position = readVector(block.has("pos")
                    ? block.get("pos") : block, null, "block.pos");
            BlockState state = resolveBlockState(
                    stringOr(block, "block", ""), context.palette);
            put(context, position, state);
        }
    }

    private static void ensurePlanCapacity(CompileContext context,
                                           long additional)
            throws PlanException
    {
        long limit = SeeleConfig.MCP_MAX_PLAN_BLOCKS.get();
        if (additional < 0L || additional > limit
                || context.placements.size() + additional > limit)
        {
            throw new PlanException("PLAN_TOO_LARGE",
                    "The plan exceeds the configured limit of " + limit
                            + " block writes.");
        }
    }

    private static void put(CompileContext context, BlockPos local,
                            BlockState state) throws PlanException
    {
        BlockPos rotated = rotate(local, context.rotation);
        int radius = SeeleConfig.MCP_MAX_BUILD_RADIUS.get();
        if (Math.abs(rotated.getX()) > radius
                || Math.abs(rotated.getZ()) > radius)
        {
            throw new PlanException("OUTSIDE_BUILD_RADIUS",
                    "Plan coordinates exceed the configured horizontal radius "
                            + radius + ".");
        }
        BlockPos world = context.origin.offset(rotated);
        if (world.getY() < context.level.getMinBuildHeight()
                || world.getY() >= context.level.getMaxBuildHeight())
        {
            throw new PlanException("OUTSIDE_WORLD_HEIGHT",
                    "Plan position is outside the dimension height: " + world);
        }
        context.placements.put(world.asLong(),
                new Placement(world.immutable(),
                        rotateState(state, context.rotation), null));
        if (context.placements.size() > SeeleConfig.MCP_MAX_PLAN_BLOCKS.get())
        {
            throw new PlanException("PLAN_TOO_LARGE",
                    "The plan has too many unique block positions.");
        }
    }

    private static void validateLocalBounds(CompileContext context,
                                            int minX, int maxX,
                                            int minY, int maxY,
                                            int minZ, int maxZ)
            throws PlanException
    {
        int radius = SeeleConfig.MCP_MAX_BUILD_RADIUS.get();
        if (Math.abs((long) minX) > radius
                || Math.abs((long) maxX) > radius
                || Math.abs((long) minZ) > radius
                || Math.abs((long) maxZ) > radius)
        {
            throw new PlanException("OUTSIDE_BUILD_RADIUS",
                    "Cuboid coordinates exceed the configured horizontal "
                            + "radius " + radius + ".");
        }
        long worldMinY = (long) context.origin.getY() + minY;
        long worldMaxY = (long) context.origin.getY() + maxY;
        if (worldMinY < context.level.getMinBuildHeight()
                || worldMaxY >= context.level.getMaxBuildHeight())
        {
            throw new PlanException("OUTSIDE_WORLD_HEIGHT",
                    "Cuboid coordinates exceed the dimension height.");
        }
    }

    private static BlockState resolveBlockState(String raw,
                                                Map<String, String> palette)
            throws PlanException
    {
        String expanded = palette.getOrDefault(raw, raw);
        if (expanded == null || expanded.isBlank())
        {
            throw new PlanException("MISSING_BLOCK",
                    "Every block or cuboid needs a block state.");
        }
        String value = expanded.trim();
        String blockName = value;
        String properties = "";
        int bracket = value.indexOf('[');
        if (bracket >= 0)
        {
            if (!value.endsWith("]"))
            {
                throw new PlanException("INVALID_BLOCK_STATE",
                        "Malformed block state: " + value);
            }
            blockName = value.substring(0, bracket);
            properties = value.substring(bracket + 1, value.length() - 1);
        }
        ResourceLocation id = ResourceLocation.tryParse(blockName);
        if (id == null || !BuiltInRegistries.BLOCK.containsKey(id))
        {
            throw new PlanException("UNKNOWN_BLOCK",
                    "Unknown block: " + blockName);
        }
        Block block = BuiltInRegistries.BLOCK.get(id);
        BlockState state = block.defaultBlockState();
        if (!properties.isBlank())
        {
            for (String assignment : properties.split(","))
            {
                String[] pair = assignment.trim().split("=", 2);
                if (pair.length != 2)
                {
                    throw new PlanException("INVALID_BLOCK_STATE",
                            "Malformed block property: " + assignment);
                }
                Property<?> property = block.getStateDefinition()
                        .getProperty(pair[0].trim());
                if (property == null)
                {
                    throw new PlanException("UNKNOWN_BLOCK_PROPERTY",
                            blockName + " has no property " + pair[0]);
                }
                state = setProperty(state, property, pair[1].trim(), blockName);
            }
        }
        return state;
    }

    private static <T extends Comparable<T>> BlockState setProperty(
            BlockState state, Property<T> property, String value,
            String blockName) throws PlanException
    {
        Optional<T> parsed = property.getValue(value);
        if (parsed.isEmpty())
        {
            throw new PlanException("INVALID_BLOCK_PROPERTY",
                    "Invalid " + property.getName() + " value for "
                            + blockName + ": " + value);
        }
        return state.setValue(property, parsed.get());
    }

    private static BlockPos readVector(JsonElement element,
                                       BlockPos fallback, String label)
            throws PlanException
    {
        if (element == null || element.isJsonNull())
        {
            if (fallback != null)
            {
                return fallback;
            }
            throw new PlanException("MISSING_VECTOR", label + " is required.");
        }
        try
        {
            if (element.isJsonArray())
            {
                JsonArray array = element.getAsJsonArray();
                if (array.size() != 3)
                {
                    throw new PlanException("INVALID_VECTOR",
                            label + " must contain [x,y,z].");
                }
                return new BlockPos(array.get(0).getAsInt(),
                        array.get(1).getAsInt(), array.get(2).getAsInt());
            }
            if (element.isJsonObject())
            {
                JsonObject object = element.getAsJsonObject();
                return new BlockPos(object.get("x").getAsInt(),
                        object.get("y").getAsInt(),
                        object.get("z").getAsInt());
            }
        }
        catch (PlanException exception)
        {
            throw exception;
        }
        catch (RuntimeException exception)
        {
            throw new PlanException("INVALID_VECTOR",
                    label + " must contain integer x, y and z values.");
        }
        throw new PlanException("INVALID_VECTOR",
                label + " must be [x,y,z] or {x,y,z}.");
    }

    private static BlockPos rotate(BlockPos position, int rotation)
    {
        return switch (rotation)
        {
            case 90 -> new BlockPos(-position.getZ(), position.getY(),
                    position.getX());
            case 180 -> new BlockPos(-position.getX(), position.getY(),
                    -position.getZ());
            case 270 -> new BlockPos(position.getZ(), position.getY(),
                    -position.getX());
            default -> position;
        };
    }

    private static BlockState rotateState(BlockState state, int rotation)
    {
        return state.rotate(switch (rotation)
        {
            case 90 -> Rotation.CLOCKWISE_90;
            case 180 -> Rotation.CLOCKWISE_180;
            case 270 -> Rotation.COUNTERCLOCKWISE_90;
            default -> Rotation.NONE;
        });
    }

    private static int normalizeRotation(int rotation) throws PlanException
    {
        int normalized = Math.floorMod(rotation, 360);
        if (normalized != 0 && normalized != 90
                && normalized != 180 && normalized != 270)
        {
            throw new PlanException("INVALID_ROTATION",
                    "rotation must be 0, 90, 180 or 270 degrees.");
        }
        return normalized;
    }

    private static boolean mutationAllowed(MinecraftServer server)
    {
        return !FacilityWorldPolicy.isCleanRebuild(server)
                && !FacilityWorldPolicy.isS20Rebuild(server)
                && !FacilityWorldPolicy.isSpatialPreviewFrozen(server)
                && !FacilityWorldPolicy.isReadOnlyBrokenArchive(server);
    }

    private static JsonObject protectedWorldError()
    {
        return error("PROTECTED_WORLD",
                "Generic MCP writes are disabled in Project SEELE facility, "
                        + "recovery, and frozen-preview saves. Use a disposable "
                        + "development world or an approved deterministic patch.");
    }

    private static ServerPlayer activePlayer(MinecraftServer server)
    {
        List<ServerPlayer> players = server.getPlayerList().getPlayers();
        return players.isEmpty() ? null : players.get(0);
    }

    private static Snapshot snapshot(ServerLevel level, BlockPos position)
    {
        BlockState state = level.getBlockState(position);
        BlockEntity entity = level.getBlockEntity(position);
        CompoundTag tag = entity == null ? null : entity.saveWithFullMetadata();
        return new Snapshot(state, tag);
    }

    private static void apply(ServerLevel level, Placement placement)
    {
        level.setBlock(placement.position, placement.state,
                Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE);
        if (placement.blockEntityTag != null)
        {
            BlockEntity entity = level.getBlockEntity(placement.position);
            if (entity != null)
            {
                entity.load(placement.blockEntityTag.copy());
                entity.setChanged();
            }
        }
    }

    private static UndoBatch undoBatch(BuildJob job)
    {
        List<Map.Entry<Long, Snapshot>> entries =
                new ArrayList<>(job.snapshots.entrySet());
        Collections.reverse(entries);
        List<Placement> placements = new ArrayList<>(entries.size());
        for (Map.Entry<Long, Snapshot> entry : entries)
        {
            Snapshot original = entry.getValue();
            placements.add(new Placement(BlockPos.of(entry.getKey()),
                    original.state, original.blockEntityTag));
        }
        return new UndoBatch(job.dimension, placements);
    }

    private static JsonObject previewResult(PreparedPlan plan,
                                            boolean mutationAllowed)
    {
        JsonObject result = new JsonObject();
        result.addProperty("success", true);
        result.addProperty("planId", plan.id);
        result.addProperty("summary", plan.summary);
        result.addProperty("dimension", plan.dimension.location().toString());
        result.add("resolvedOrigin", vector(plan.origin));
        result.addProperty("appliedRotation", plan.rotation);
        result.addProperty("blockCount", plan.placements.size());
        result.add("bounds", plan.bounds.toJson());
        result.add("materials", materialCounts(plan.placements));
        JsonArray previewBlocks = new JsonArray();
        for (int index = 0; index < Math.min(24, plan.placements.size()); index++)
        {
            Placement placement = plan.placements.get(index);
            JsonObject item = new JsonObject();
            item.add("pos", vector(placement.position));
            item.addProperty("block", blockId(placement.state));
            previewBlocks.add(item);
        }
        result.add("previewBlocks", previewBlocks);
        result.addProperty("expiresInSeconds", PLAN_TTL_MS / 1000L);
        result.addProperty("mutationAllowed", mutationAllowed);
        result.addProperty("exactExecution",
                "Call minecraft_execute_build_plan with executePlanId.");
        return result;
    }

    private static JsonObject jobResult(BuildJob job)
    {
        JsonObject result = new JsonObject();
        result.addProperty("success", !job.status.equals("failed"));
        result.addProperty("jobId", job.id);
        result.addProperty("planId", job.planId);
        result.addProperty("summary", job.summary);
        result.addProperty("status", job.status);
        result.addProperty("restoreMode", job.restoreMode);
        result.addProperty("completedBlocks", job.cursor);
        result.addProperty("totalBlocks", job.placements.size());
        result.addProperty("progress", job.placements.isEmpty() ? 1.0D
                : job.cursor / (double) job.placements.size());
        if (job.failure != null)
        {
            result.addProperty("failure", job.failure);
        }
        return result;
    }

    private static JsonObject materialCounts(List<Placement> placements)
    {
        LinkedHashMap<String, Integer> counts = new LinkedHashMap<>();
        for (Placement placement : placements)
        {
            counts.merge(blockId(placement.state), 1, Integer::sum);
        }
        JsonObject result = new JsonObject();
        counts.entrySet().stream()
                .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
                .forEach(entry -> result.addProperty(
                        entry.getKey(), entry.getValue()));
        return result;
    }

    private static String blockId(BlockState state)
    {
        ResourceLocation id = BuiltInRegistries.BLOCK.getKey(state.getBlock());
        if (state == state.getBlock().defaultBlockState())
        {
            return id.toString();
        }
        StringBuilder value = new StringBuilder(id.toString()).append('[');
        boolean first = true;
        for (Property<?> property : state.getProperties())
        {
            if (!first)
            {
                value.append(',');
            }
            first = false;
            value.append(property.getName()).append('=')
                    .append(propertyValue(state, property));
        }
        return value.append(']').toString();
    }

    private static <T extends Comparable<T>> String propertyValue(
            BlockState state, Property<T> property)
    {
        return property.getName(state.getValue(property));
    }

    private static JsonObject vector(BlockPos position)
    {
        JsonObject result = new JsonObject();
        result.addProperty("x", position.getX());
        result.addProperty("y", position.getY());
        result.addProperty("z", position.getZ());
        return result;
    }

    private static JsonObject error(String code, String message)
    {
        JsonObject result = new JsonObject();
        JsonObject error = new JsonObject();
        error.addProperty("code", code);
        error.addProperty("message", message);
        result.add("error", error);
        return result;
    }

    private static String stringOr(JsonObject object, String key,
                                   String fallback)
    {
        if (object == null || !object.has(key)
                || object.get(key).isJsonNull())
        {
            return fallback;
        }
        try
        {
            return object.get(key).getAsString();
        }
        catch (RuntimeException exception)
        {
            return fallback;
        }
    }

    private static int intOr(JsonObject object, String key, int fallback)
    {
        if (object == null || !object.has(key)
                || object.get(key).isJsonNull())
        {
            return fallback;
        }
        try
        {
            return object.get(key).getAsInt();
        }
        catch (RuntimeException exception)
        {
            return fallback;
        }
    }

    private static boolean booleanOr(JsonObject object, String key,
                                     boolean fallback)
    {
        if (object == null || !object.has(key)
                || object.get(key).isJsonNull())
        {
            return fallback;
        }
        try
        {
            return object.get(key).getAsBoolean();
        }
        catch (RuntimeException exception)
        {
            return fallback;
        }
    }

    private static int clamp(int value, int minimum, int maximum)
    {
        return Math.max(minimum, Math.min(maximum, value));
    }

    private static void purgeExpiredPlans()
    {
        long cutoff = System.currentTimeMillis() - PLAN_TTL_MS;
        PLAN_CACHE.entrySet().removeIf(
                entry -> entry.getValue().createdAtMs < cutoff);
    }

    private static <T> void trimOldest(LinkedHashMap<String, T> values,
                                       int maximum)
    {
        while (values.size() > maximum)
        {
            String first = values.keySet().iterator().next();
            values.remove(first);
        }
    }

    private record CompileContext(ServerLevel level, BlockPos origin,
                                  int rotation, Map<String, String> palette,
                                  LinkedHashMap<Long, Placement> placements)
    {
    }

    private record Placement(BlockPos position, BlockState state,
                             CompoundTag blockEntityTag)
    {
    }

    private record Snapshot(BlockState state, CompoundTag blockEntityTag)
    {
    }

    private record PreparedPlan(String id, String summary,
                                ResourceKey<Level> dimension,
                                BlockPos origin, int rotation,
                                List<Placement> placements, Bounds bounds,
                                long createdAtMs)
    {
    }

    private record UndoBatch(ResourceKey<Level> dimension,
                             List<Placement> placements)
    {
    }

    private record Bounds(BlockPos minimum, BlockPos maximum)
    {
        private static Bounds of(List<Placement> placements)
        {
            int minX = Integer.MAX_VALUE;
            int minY = Integer.MAX_VALUE;
            int minZ = Integer.MAX_VALUE;
            int maxX = Integer.MIN_VALUE;
            int maxY = Integer.MIN_VALUE;
            int maxZ = Integer.MIN_VALUE;
            for (Placement placement : placements)
            {
                BlockPos position = placement.position;
                minX = Math.min(minX, position.getX());
                minY = Math.min(minY, position.getY());
                minZ = Math.min(minZ, position.getZ());
                maxX = Math.max(maxX, position.getX());
                maxY = Math.max(maxY, position.getY());
                maxZ = Math.max(maxZ, position.getZ());
            }
            return new Bounds(new BlockPos(minX, minY, minZ),
                    new BlockPos(maxX, maxY, maxZ));
        }

        private JsonObject toJson()
        {
            JsonObject result = new JsonObject();
            result.add("min", vector(minimum));
            result.add("max", vector(maximum));
            return result;
        }
    }

    private static final class BuildJob
    {
        private final String id;
        private final String planId;
        private final String summary;
        private final ResourceKey<Level> dimension;
        private final List<Placement> placements;
        private final boolean restoreMode;
        private final LinkedHashMap<Long, Snapshot> snapshots =
                new LinkedHashMap<>();
        private int cursor;
        private String status = "running";
        private String failure;

        private BuildJob(String planId, String summary,
                         ResourceKey<Level> dimension,
                         List<Placement> placements, boolean restoreMode)
        {
            this.id = "seele-job-" + UUID.randomUUID();
            this.planId = planId;
            this.summary = summary;
            this.dimension = dimension;
            this.placements = placements;
            this.restoreMode = restoreMode;
        }

        private static BuildJob build(PreparedPlan plan)
        {
            return new BuildJob(plan.id, plan.summary, plan.dimension,
                    plan.placements, false);
        }

        private static BuildJob undo(UndoBatch batch)
        {
            return new BuildJob("undo", "Undo last MCP build",
                    batch.dimension, batch.placements, true);
        }

        private boolean isRunning()
        {
            return status.equals("running");
        }

        private void complete()
        {
            status = "complete";
        }

        private void fail(String message)
        {
            status = "failed";
            failure = message == null ? "Unknown block-write failure" : message;
        }
    }

    private static final class PlanException extends Exception
    {
        private final String code;

        private PlanException(String code, String message)
        {
            super(message);
            this.code = code;
        }
    }
}
