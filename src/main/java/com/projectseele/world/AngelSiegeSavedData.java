package com.projectseele.world;

import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import com.projectseele.ProjectSeele;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/** Versioned per-dimension state for player-built NERV beacon defenses. */
public final class AngelSiegeSavedData extends SavedData
{
    private static final String DATA_NAME = "projectseele_angel_sieges";
    private static final int DATA_VERSION = 1;

    private final Map<Long, StoredSiege> sieges = new LinkedHashMap<>();

    public static AngelSiegeSavedData get(ServerLevel level)
    {
        return level.getDataStorage().computeIfAbsent(
                AngelSiegeSavedData::load,
                AngelSiegeSavedData::new, DATA_NAME);
    }

    public static AngelSiegeSavedData load(CompoundTag tag)
    {
        AngelSiegeSavedData data = new AngelSiegeSavedData();
        int version = tag.contains("Version", Tag.TAG_INT)
                ? tag.getInt("Version") : 1;
        if (version != DATA_VERSION)
        {
            ProjectSeele.LOGGER.error(
                    "Unsupported Angel siege SavedData version {}; ignoring sieges",
                    version);
            return data;
        }
        ListTag entries = tag.getList("Sieges", Tag.TAG_COMPOUND);
        for (int index = 0; index < entries.size(); index++)
        {
            CompoundTag entry = entries.getCompound(index);
            if (!entry.contains("Beacon", Tag.TAG_LONG)
                    || !entry.hasUUID("Event")
                    || !entry.hasUUID("Owner"))
            {
                continue;
            }
            ListTag spawnedEntries = entry.getList("Spawned", Tag.TAG_COMPOUND);
            java.util.ArrayList<UUID> spawned = new java.util.ArrayList<>();
            for (int spawnedIndex = 0; spawnedIndex < spawnedEntries.size(); spawnedIndex++)
            {
                CompoundTag entity = spawnedEntries.getCompound(spawnedIndex);
                if (entity.hasUUID("Id"))
                {
                    spawned.add(entity.getUUID("Id"));
                }
            }
            StoredSiege siege = new StoredSiege(
                    BlockPos.of(entry.getLong("Beacon")),
                    entry.getUUID("Event"), entry.getUUID("Owner"),
                    Math.max(0L, entry.getLong("StartedAt")),
                    entry.getInt("NextWave"), entry.getInt("Integrity"),
                    spawned);
            data.sieges.put(siege.beacon().asLong(), siege);
        }
        return data;
    }

    public Collection<StoredSiege> sieges()
    {
        return List.copyOf(this.sieges.values());
    }

    public Optional<StoredSiege> nearest(BlockPos position, double maximumDistance)
    {
        double maximumDistanceSqr = maximumDistance * maximumDistance;
        return this.sieges.values().stream()
                .filter(siege -> siege.beacon().distSqr(position) <= maximumDistanceSqr)
                .min((left, right) -> Double.compare(
                        left.beacon().distSqr(position),
                        right.beacon().distSqr(position)));
    }

    public void put(StoredSiege siege)
    {
        this.sieges.put(siege.beacon().asLong(), siege);
        this.setDirty();
    }

    public void remove(BlockPos beacon)
    {
        if (this.sieges.remove(beacon.asLong()) != null)
        {
            this.setDirty();
        }
    }

    @Override
    public CompoundTag save(CompoundTag tag)
    {
        tag.putInt("Version", DATA_VERSION);
        ListTag entries = new ListTag();
        for (StoredSiege siege : this.sieges.values())
        {
            CompoundTag entry = new CompoundTag();
            entry.putLong("Beacon", siege.beacon().asLong());
            entry.putUUID("Event", siege.eventId());
            entry.putUUID("Owner", siege.owner());
            entry.putLong("StartedAt", siege.startedAt());
            entry.putInt("NextWave", siege.nextWave());
            entry.putInt("Integrity", siege.integrity());
            ListTag spawned = new ListTag();
            for (UUID id : siege.spawned())
            {
                CompoundTag entity = new CompoundTag();
                entity.putUUID("Id", id);
                spawned.add(entity);
            }
            entry.put("Spawned", spawned);
            entries.add(entry);
        }
        tag.put("Sieges", entries);
        return tag;
    }

    public record StoredSiege(BlockPos beacon, UUID eventId, UUID owner,
                              long startedAt, int nextWave, int integrity,
                              List<UUID> spawned)
    {
        public StoredSiege
        {
            beacon = beacon.immutable();
            nextWave = Math.max(0, Math.min(3, nextWave));
            integrity = Math.max(0, integrity);
            spawned = List.copyOf(spawned);
        }

        public StoredSiege withWave(int wave, List<UUID> entityIds)
        {
            return new StoredSiege(this.beacon, this.eventId, this.owner,
                    this.startedAt, wave, this.integrity, entityIds);
        }

        public StoredSiege withIntegrity(int value)
        {
            return new StoredSiege(this.beacon, this.eventId, this.owner,
                    this.startedAt, this.nextWave, value, this.spawned);
        }
    }
}