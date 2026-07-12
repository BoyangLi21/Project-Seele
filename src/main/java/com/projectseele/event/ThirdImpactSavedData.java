package com.projectseele.event;

import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.phys.Vec3;

/** Versioned per-dimension persistence for active Third-Impact timelines. */
public final class ThirdImpactSavedData extends SavedData
{
    private static final String DATA_NAME = "projectseele_third_impact";
    private static final int DATA_VERSION = 1;

    private final Map<UUID, StoredImpact> impacts = new LinkedHashMap<>();

    public static ThirdImpactSavedData get(ServerLevel level)
    {
        return level.getDataStorage().computeIfAbsent(
                ThirdImpactSavedData::load, ThirdImpactSavedData::new, DATA_NAME);
    }

    public static ThirdImpactSavedData load(CompoundTag tag)
    {
        ThirdImpactSavedData data = new ThirdImpactSavedData();
        ListTag entries = tag.getList("Impacts", Tag.TAG_COMPOUND);
        for (int i = 0; i < entries.size(); i++)
        {
            CompoundTag entry = entries.getCompound(i);
            if (!entry.hasUUID("Id"))
            {
                continue;
            }
            double x = entry.getDouble("OriginX");
            double y = entry.getDouble("OriginY");
            double z = entry.getDouble("OriginZ");
            float yaw = entry.getFloat("Yaw");
            if (!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z)
                    || !Float.isFinite(yaw))
            {
                continue;
            }
            Map<Integer, UUID> vessels = new LinkedHashMap<>();
            ListTag vesselEntries = entry.getList("Vessels", Tag.TAG_COMPOUND);
            for (int vesselIndex = 0; vesselIndex < vesselEntries.size(); vesselIndex++)
            {
                CompoundTag vessel = vesselEntries.getCompound(vesselIndex);
                int node = vessel.getInt("Node");
                if (node >= 0 && node < 10 && vessel.hasUUID("Id"))
                {
                    vessels.put(node, vessel.getUUID("Id"));
                }
            }
            StoredImpact impact = new StoredImpact(entry.getUUID("Id"), new Vec3(x, y, z),
                    yaw, entry.getBoolean("HasUnit"), Math.max(0, entry.getInt("Ticks")),
                    vessels);
            data.impacts.put(impact.id(), impact);
        }
        return data;
    }

    public Collection<StoredImpact> impacts()
    {
        return java.util.List.copyOf(this.impacts.values());
    }

    public void put(StoredImpact impact)
    {
        this.impacts.put(impact.id(), impact);
        this.setDirty();
    }

    public void remove(UUID id)
    {
        if (this.impacts.remove(id) != null)
        {
            this.setDirty();
        }
    }

    @Override
    public CompoundTag save(CompoundTag tag)
    {
        tag.putInt("Version", DATA_VERSION);
        ListTag entries = new ListTag();
        for (StoredImpact impact : this.impacts.values())
        {
            CompoundTag entry = new CompoundTag();
            entry.putUUID("Id", impact.id());
            entry.putDouble("OriginX", impact.origin().x);
            entry.putDouble("OriginY", impact.origin().y);
            entry.putDouble("OriginZ", impact.origin().z);
            entry.putFloat("Yaw", impact.yaw());
            entry.putBoolean("HasUnit", impact.hasUnit());
            entry.putInt("Ticks", impact.ticks());
            ListTag vesselEntries = new ListTag();
            for (Map.Entry<Integer, UUID> vessel : impact.vessels().entrySet())
            {
                CompoundTag vesselEntry = new CompoundTag();
                vesselEntry.putInt("Node", vessel.getKey());
                vesselEntry.putUUID("Id", vessel.getValue());
                vesselEntries.add(vesselEntry);
            }
            entry.put("Vessels", vesselEntries);
            entries.add(entry);
        }
        tag.put("Impacts", entries);
        return tag;
    }

    public record StoredImpact(UUID id, Vec3 origin, float yaw, boolean hasUnit,
                               int ticks, Map<Integer, UUID> vessels)
    {
        public StoredImpact
        {
            vessels = Map.copyOf(vessels);
        }
    }
}
