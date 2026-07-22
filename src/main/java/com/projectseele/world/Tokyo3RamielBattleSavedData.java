package com.projectseele.world;

import java.util.Collection;
import java.util.LinkedHashMap;
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

/** Persistent Ramiel battle ownership for each integrated Tokyo-3 district. */
public final class Tokyo3RamielBattleSavedData extends SavedData
{
    private static final String DATA_NAME = "projectseele_tokyo3_ramiel_battle";
    private static final int DATA_VERSION = 1;

    private final Map<Long, StoredBattle> battles = new LinkedHashMap<>();

    public static Tokyo3RamielBattleSavedData get(ServerLevel level)
    {
        return level.getDataStorage().computeIfAbsent(
                Tokyo3RamielBattleSavedData::load,
                Tokyo3RamielBattleSavedData::new, DATA_NAME);
    }

    public static Tokyo3RamielBattleSavedData load(CompoundTag tag)
    {
        Tokyo3RamielBattleSavedData data = new Tokyo3RamielBattleSavedData();
        int version = tag.contains("Version", Tag.TAG_INT)
                ? tag.getInt("Version") : 1;
        if (version != DATA_VERSION)
        {
            ProjectSeele.LOGGER.error(
                    "Unsupported Tokyo-3 Ramiel battle SavedData version {}; ignoring battles",
                    version);
            return data;
        }
        ListTag entries = tag.getList("Battles", Tag.TAG_COMPOUND);
        for (int index = 0; index < entries.size(); index++)
        {
            CompoundTag entry = entries.getCompound(index);
            if (!entry.contains("Origin", Tag.TAG_LONG)
                    || !entry.hasUUID("Ramiel"))
            {
                continue;
            }
            StoredBattle battle = new StoredBattle(
                    BlockPos.of(entry.getLong("Origin")),
                    entry.getUUID("Ramiel"),
                    Math.max(0, entry.getInt("ClearTicks")));
            data.battles.put(battle.origin().asLong(), battle);
        }
        return data;
    }

    public Collection<StoredBattle> battles()
    {
        return java.util.List.copyOf(this.battles.values());
    }

    public Optional<StoredBattle> get(BlockPos origin)
    {
        return Optional.ofNullable(this.battles.get(origin.asLong()));
    }

    public void put(StoredBattle battle)
    {
        this.battles.put(battle.origin().asLong(), battle);
        this.setDirty();
    }

    public void remove(BlockPos origin)
    {
        if (this.battles.remove(origin.asLong()) != null)
        {
            this.setDirty();
        }
    }

    @Override
    public CompoundTag save(CompoundTag tag)
    {
        tag.putInt("Version", DATA_VERSION);
        ListTag entries = new ListTag();
        for (StoredBattle battle : this.battles.values())
        {
            CompoundTag entry = new CompoundTag();
            entry.putLong("Origin", battle.origin().asLong());
            entry.putUUID("Ramiel", battle.ramiel());
            entry.putInt("ClearTicks", battle.clearTicks());
            entries.add(entry);
        }
        tag.put("Battles", entries);
        return tag;
    }

    public record StoredBattle(BlockPos origin, UUID ramiel, int clearTicks)
    {
        public StoredBattle
        {
            origin = origin.immutable();
            clearTicks = Math.max(0, clearTicks);
        }
    }
}
