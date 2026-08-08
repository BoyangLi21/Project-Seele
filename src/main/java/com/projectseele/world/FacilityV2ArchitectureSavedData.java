package com.projectseele.world;

import java.util.LinkedHashMap;
import java.util.Map;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/**
 * Durable receipts for small, owner-bounded architecture upgrades.
 *
 * <p>Facility owner completion receipts remain immutable. A revision here
 * records a deliberate correction to already completed geometry without
 * pretending the whole owner was generated again.</p>
 */
public final class FacilityV2ArchitectureSavedData extends SavedData
{
    private static final String DATA_NAME =
            "projectseele_facility_v2_architecture_e1";
    private static final int DATA_VERSION = 1;

    private final Map<String, Integer> revisions = new LinkedHashMap<>();

    public static FacilityV2ArchitectureSavedData get(ServerLevel level)
    {
        return level.getDataStorage().computeIfAbsent(
                FacilityV2ArchitectureSavedData::load,
                FacilityV2ArchitectureSavedData::new, DATA_NAME);
    }

    public static FacilityV2ArchitectureSavedData load(CompoundTag tag)
    {
        FacilityV2ArchitectureSavedData data =
                new FacilityV2ArchitectureSavedData();
        if (tag.getInt("Version") != DATA_VERSION)
        {
            return data;
        }
        ListTag list = tag.getList("Revisions", Tag.TAG_COMPOUND);
        for (int index = 0; index < list.size(); index++)
        {
            CompoundTag record = list.getCompound(index);
            String id = record.getString("Id");
            int revision = Math.max(0, record.getInt("Revision"));
            if (!id.isBlank() && revision > 0)
            {
                data.revisions.put(id, revision);
            }
        }
        return data;
    }

    public boolean needs(String id, int revision)
    {
        return this.revisions.getOrDefault(id, 0) < revision;
    }

    public void markApplied(String id, int revision)
    {
        int previous = this.revisions.getOrDefault(id, 0);
        if (revision > previous)
        {
            this.revisions.put(id, revision);
            this.setDirty();
        }
    }

    @Override
    public CompoundTag save(CompoundTag tag)
    {
        tag.putInt("Version", DATA_VERSION);
        ListTag list = new ListTag();
        for (Map.Entry<String, Integer> entry : this.revisions.entrySet())
        {
            CompoundTag record = new CompoundTag();
            record.putString("Id", entry.getKey());
            record.putInt("Revision", entry.getValue());
            list.add(record);
        }
        tag.put("Revisions", list);
        return tag;
    }
}
