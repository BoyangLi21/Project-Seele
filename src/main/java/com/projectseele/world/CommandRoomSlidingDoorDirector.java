package com.projectseele.world;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.NervSlidingDoorEntity;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/** Runtime owner for the reviewed 3x2 command-room sliding doors. */
public final class CommandRoomSlidingDoorDirector
{
    public static final String MARKER =
            ".projectseele_command_sliding_doors_r01.json";
    private static final Map<MinecraftServer, RuntimeConfig> CONFIG =
            new WeakHashMap<>();
    private static final List<DoorSpec> DOORS = List.of(
            door(0, 8, -429, 282, Direction.NORTH),
            door(1, 13, -429, 282, Direction.NORTH),
            door(2, 43, -429, 282, Direction.NORTH),
            door(3, 48, -429, 282, Direction.NORTH),
            door(4, 28, -424, 286, Direction.SOUTH),
            door(5, 24, -423, 254, Direction.WEST),
            door(6, 11, -423, 268, Direction.NORTH),
            door(7, 17, -423, 268, Direction.NORTH),
            door(8, 39, -423, 268, Direction.NORTH),
            door(9, 45, -423, 268, Direction.NORTH),
            door(10, 20, -423, 278, Direction.EAST),
            door(11, 36, -423, 278, Direction.EAST),
            door(12, 21, -422, 283, Direction.NORTH),
            door(13, 35, -422, 283, Direction.NORTH),
            door(14, 24, -418, 254, Direction.WEST),
            door(15, 28, -413, 284, Direction.SOUTH),
            door(16, 24, -409, 270, Direction.NORTH),
            door(17, 32, -409, 270, Direction.NORTH),
            door(18, 28, -406, 272, Direction.NORTH));

    private CommandRoomSlidingDoorDirector() {}

    private static DoorSpec door(int id, int x, int y, int z,
                                 Direction facing)
    {
        return new DoorSpec(id, new BlockPos(x, y, z), facing);
    }

    public static void tick(ServerLevel level)
    {
        if (!enabled(level) || level.getGameTime() % 2L != 0L)
        {
            return;
        }
        for (DoorSpec spec : DOORS)
        {
            if (!config(level).doorIds().contains(spec.id()))
            {
                continue;
            }
            if (!level.hasChunkAt(spec.lower()))
            {
                continue;
            }
            NervSlidingDoorEntity door = NervSlidingDoorEntity.reconcile(
                    level, spec.id(), spec.axisX(), spec.centre());
            if (door != null && spec.redstonePowered(level))
            {
                door.requestRedstoneOpen();
            }
        }
    }

    public static boolean handleUse(ServerPlayer player, BlockPos position)
    {
        ServerLevel level = player.serverLevel();
        if (!enabled(level)
                || !(level.getBlockState(position).getBlock()
                instanceof ButtonBlock))
        {
            return false;
        }
        Integer doorId = config(level).buttons().get(position);
        DoorSpec spec = doorId == null ? null : spec(doorId);
        if (spec == null)
        {
            return false;
        }
        NervSlidingDoorEntity door = NervSlidingDoorEntity.reconcile(
                level, spec.id(), spec.axisX(), spec.centre());
        if (door == null)
        {
            return false;
        }
        door.requestOpen();
        return true;
    }

    public static void maintainCollision(ServerLevel level, int doorId,
                                         boolean closed)
    {
        DoorSpec spec = spec(doorId);
        if (spec == null || !level.hasChunkAt(spec.lower()))
        {
            return;
        }
        for (BlockPos position : spec.aperture())
        {
            if (closed)
            {
                if (level.getBlockState(position).isAir())
                {
                    level.setBlock(position, Blocks.BARRIER.defaultBlockState(),
                            net.minecraft.world.level.block.Block.UPDATE_CLIENTS);
                }
            }
            else if (level.getBlockState(position).is(Blocks.BARRIER))
            {
                level.setBlock(position, Blocks.AIR.defaultBlockState(),
                        net.minecraft.world.level.block.Block.UPDATE_CLIENTS);
            }
        }
    }

    public static boolean apertureOccupied(ServerLevel level, int doorId)
    {
        DoorSpec spec = spec(doorId);
        if (spec == null)
        {
            return false;
        }
        return !level.getEntities((Entity)null, spec.apertureBounds(),
                entity -> entity.isAlive()
                        && !(entity instanceof NervSlidingDoorEntity)).isEmpty();
    }

    public static void resetRuntime()
    {
        synchronized (CONFIG)
        {
            CONFIG.clear();
        }
    }

    private static DoorSpec spec(int id)
    {
        return id >= 0 && id < DOORS.size() ? DOORS.get(id) : null;
    }

    private static boolean enabled(ServerLevel level)
    {
        if (level.dimension() != FacilitySchemaV2.DIMENSION)
        {
            return false;
        }
        MinecraftServer server = level.getServer();
        return config(level).enabled();
    }

    private static RuntimeConfig config(ServerLevel level)
    {
        MinecraftServer server = level.getServer();
        synchronized (CONFIG)
        {
            return CONFIG.computeIfAbsent(server, ignored ->
            {
                Path marker = server.getWorldPath(LevelResource.ROOT)
                        .resolve(MARKER);
                if (!Files.isRegularFile(marker))
                {
                    return new RuntimeConfig(false, Map.of(), Set.of());
                }
                try
                {
                    JsonObject root = JsonParser.parseString(
                            Files.readString(marker)).getAsJsonObject();
                    Map<BlockPos, Integer> buttons = new HashMap<>();
                    Set<Integer> doorIds = new HashSet<>();
                    JsonArray doors = root.getAsJsonArray("doors");
                    if (doors != null)
                    {
                        for (JsonElement element : doors)
                        {
                            JsonObject door = element.getAsJsonObject();
                            int id = door.get("id").getAsInt();
                            doorIds.add(id);
                            for (JsonElement buttonElement
                                    : door.getAsJsonArray("buttons"))
                            {
                                JsonArray value = buttonElement.getAsJsonArray();
                                buttons.put(new BlockPos(
                                        value.get(0).getAsInt(),
                                        value.get(1).getAsInt(),
                                        value.get(2).getAsInt()), id);
                            }
                        }
                    }
                    ProjectSeele.LOGGER.info(
                            "NERV command-room sliding doors enabled: count={} buttons={}",
                            DOORS.size(), buttons.size());
                    return new RuntimeConfig(true, Map.copyOf(buttons),
                            Set.copyOf(doorIds));
                }
                catch (Exception exception)
                {
                    ProjectSeele.LOGGER.error(
                            "Cannot read command-room sliding door marker {}",
                            marker, exception);
                    return new RuntimeConfig(false, Map.of(), Set.of());
                }
            });
        }
    }

    private record DoorSpec(int id, BlockPos lower, Direction facing)
    {
        boolean axisX()
        {
            return this.facing.getAxis() == Direction.Axis.Z;
        }

        Vec3 centre()
        {
            return new Vec3(this.lower.getX() + 0.5D,
                    this.lower.getY(), this.lower.getZ() + 0.5D);
        }

        List<BlockPos> aperture()
        {
            java.util.ArrayList<BlockPos> result = new java.util.ArrayList<>(6);
            for (int vertical = 0; vertical < 2; vertical++)
            {
                for (int width = -1; width <= 1; width++)
                {
                    result.add(this.axisX()
                            ? this.lower.offset(width, vertical, 0)
                            : this.lower.offset(0, vertical, width));
                }
            }
            return result;
        }

        AABB apertureBounds()
        {
            if (this.axisX())
            {
                return new AABB(this.lower.getX() - 1.0D,
                        this.lower.getY(), this.lower.getZ(),
                        this.lower.getX() + 2.0D,
                        this.lower.getY() + 2.0D,
                        this.lower.getZ() + 1.0D);
            }
            return new AABB(this.lower.getX(), this.lower.getY(),
                    this.lower.getZ() - 1.0D,
                    this.lower.getX() + 1.0D,
                    this.lower.getY() + 2.0D,
                    this.lower.getZ() + 2.0D);
        }

        boolean redstonePowered(ServerLevel level)
        {
            for (int vertical = 0; vertical <= 2; vertical++)
            {
                for (int width = -4; width <= 4; width++)
                {
                    BlockPos sensor = this.axisX()
                            ? this.lower.offset(width, vertical, 0)
                            : this.lower.offset(0, vertical, width);
                    if (level.hasNeighborSignal(sensor))
                    {
                        return true;
                    }
                }
            }
            return false;
        }
    }

    private record RuntimeConfig(boolean enabled,
                                 Map<BlockPos, Integer> buttons,
                                 Set<Integer> doorIds) {}
}
