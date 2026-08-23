package com.projectseele.world;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.WeakHashMap;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.projectseele.ProjectSeele;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/** One rigid legacy-to-coastal coordinate transform per server save. */
public final class S24CoordinateTransform
{
    private static final Map<MinecraftServer, Delta> CACHE =
            new WeakHashMap<>();
    private static final Delta ZERO = new Delta(0, 0, 0);

    private S24CoordinateTransform() {}

    public static BlockPos apply(MinecraftServer server, BlockPos legacy)
    {
        Delta delta = delta(server);
        return legacy.offset(delta.x(), delta.y(), delta.z());
    }

    public static BlockPos inverse(MinecraftServer server, BlockPos world)
    {
        Delta delta = delta(server);
        return world.offset(-delta.x(), -delta.y(), -delta.z());
    }

    public static Vec3 apply(MinecraftServer server, Vec3 legacy)
    {
        Delta delta = delta(server);
        return legacy.add(delta.x(), delta.y(), delta.z());
    }

    public static AABB apply(MinecraftServer server, AABB legacy)
    {
        Delta delta = delta(server);
        return legacy.move(delta.x(), delta.y(), delta.z());
    }

    public static Delta delta(MinecraftServer server)
    {
        if (!FacilityWorldPolicy.isS22Coastal(server))
        {
            return ZERO;
        }
        synchronized (CACHE)
        {
            return CACHE.computeIfAbsent(server,
                    S24CoordinateTransform::readDelta);
        }
    }

    private static Delta readDelta(MinecraftServer server)
    {
        Path marker = server.getWorldPath(LevelResource.ROOT).resolve(
                ".projectseele_s24_coastal.json");
        if (!Files.isRegularFile(marker))
        {
            // Compatibility with the first vertical-only S22 prototype.
            return new Delta(0, -12, 0);
        }
        try
        {
            JsonObject object = JsonParser.parseString(
                    Files.readString(marker)).getAsJsonObject();
            JsonArray transform = object.getAsJsonArray("transform");
            if (transform == null || transform.size() != 3)
            {
                throw new IllegalStateException(
                        "S24 marker has no three-axis transform");
            }
            Delta result = new Delta(
                    transform.get(0).getAsInt(),
                    transform.get(1).getAsInt(),
                    transform.get(2).getAsInt());
            ProjectSeele.LOGGER.info(
                    "S24 coastal coordinate transform active: ({}, {}, {})",
                    result.x(), result.y(), result.z());
            return result;
        }
        catch (IOException | RuntimeException exception)
        {
            throw new IllegalStateException(
                    "Cannot read S24 coordinate transform from " + marker,
                    exception);
        }
    }

    public record Delta(int x, int y, int z) {}
}
