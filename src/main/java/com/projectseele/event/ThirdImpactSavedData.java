package com.projectseele.event;

import java.util.Collection;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

import com.projectseele.ProjectSeele;
import com.projectseele.fx.TreeOfLifeLayout;
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
    private static final int DATA_VERSION = 2;
    private static final int MAX_STORED_TICKS = 20 * 195;
    public static final int OUTCOME_RUNNING = 0;
    public static final int OUTCOME_ACCEPTED = 1;
    public static final int OUTCOME_REJECTED = 2;

    private final Map<UUID, StoredImpact> impacts = new LinkedHashMap<>();

    public static ThirdImpactSavedData get(ServerLevel level)
    {
        return level.getDataStorage().computeIfAbsent(
                ThirdImpactSavedData::load, ThirdImpactSavedData::new, DATA_NAME);
    }

    public static ThirdImpactSavedData load(CompoundTag tag)
    {
        ThirdImpactSavedData data = new ThirdImpactSavedData();
        int version = tag.contains("Version", Tag.TAG_INT) ? tag.getInt("Version") : 1;
        if (version < 1 || version > DATA_VERSION)
        {
            ProjectSeele.LOGGER.error(
                    "Unsupported Third Impact SavedData version {}; ignoring timelines", version);
            return data;
        }
        ListTag entries = tag.getList("Impacts", Tag.TAG_COMPOUND);
        for (int i = 0; i < entries.size(); i++)
        {
            CompoundTag entry = entries.getCompound(i);
            if (!entry.hasUUID("Id")
                    || !entry.contains("OriginX", Tag.TAG_DOUBLE)
                    || !entry.contains("OriginY", Tag.TAG_DOUBLE)
                    || !entry.contains("OriginZ", Tag.TAG_DOUBLE)
                    || !entry.contains("Yaw", Tag.TAG_FLOAT))
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
            HashSet<UUID> seenVessels = new HashSet<>();
            ListTag vesselEntries = entry.getList("Vessels", Tag.TAG_COMPOUND);
            for (int vesselIndex = 0; vesselIndex < vesselEntries.size(); vesselIndex++)
            {
                CompoundTag vessel = vesselEntries.getCompound(vesselIndex);
                int node = vessel.getInt("Node");
                if (node >= 0 && node < TreeOfLifeLayout.NODES.length
                        && node != TreeOfLifeLayout.TIFERET && vessel.hasUUID("Id")
                        && seenVessels.add(vessel.getUUID("Id")))
                {
                    vessels.put(node, vessel.getUUID("Id"));
                }
            }
            int outcome = version >= 2 ? entry.getInt("Outcome") : OUTCOME_RUNNING;
            if (outcome < OUTCOME_RUNNING || outcome > OUTCOME_REJECTED)
            {
                outcome = OUTCOME_RUNNING;
            }
            int ticks = Math.min(MAX_STORED_TICKS, Math.max(0, entry.getInt("Ticks")));
            if (outcome == OUTCOME_RUNNING && ticks >= 20 * 60)
            {
                // A v1/crash snapshot at the transition must execute finish,
                // not skip past equality on its first restored tick.
                ticks = 20 * 60 - 1;
            }
            StoredImpact impact = new StoredImpact(entry.getUUID("Id"), new Vec3(x, y, z),
                    yaw, entry.getBoolean("HasUnit"), ticks, outcome, vessels);
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
            entry.putInt("Outcome", impact.outcome());
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
                               int ticks, int outcome, Map<Integer, UUID> vessels)
    {
        public StoredImpact
        {
            vessels = Map.copyOf(vessels);
        }
    }
}
