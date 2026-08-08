package com.projectseele.world;

import java.util.Collection;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import com.projectseele.ProjectSeele;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/** Per-dimension persistence for Tokyo-3 building depth and requested state. */
public final class Tokyo3RetractionSavedData extends SavedData
{
    private static final String DATA_NAME = "projectseele_tokyo3_retraction";
    private static final int DATA_VERSION = 6;

    private final Map<Long, StoredDistrict> districts = new LinkedHashMap<>();

    public static Tokyo3RetractionSavedData get(ServerLevel level)
    {
        return level.getDataStorage().computeIfAbsent(
                Tokyo3RetractionSavedData::load,
                Tokyo3RetractionSavedData::new,
                DATA_NAME);
    }

    public static Tokyo3RetractionSavedData load(CompoundTag tag)
    {
        Tokyo3RetractionSavedData data = new Tokyo3RetractionSavedData();
        int version = tag.contains("Version", Tag.TAG_INT) ? tag.getInt("Version") : 1;
        if (version < 1 || version > DATA_VERSION)
        {
            ProjectSeele.LOGGER.error(
                    "Unsupported Tokyo-3 retraction SavedData version {}; ignoring districts",
                    version);
            return data;
        }
        ListTag entries = tag.getList("Districts", Tag.TAG_COMPOUND);
        int maximum = ThirdTokyoSurfaceBuilder.maximumRetractionDepth();
        for (int i = 0; i < entries.size(); i++)
        {
            CompoundTag entry = entries.getCompound(i);
            if (!entry.contains("Origin", Tag.TAG_LONG))
            {
                continue;
            }
            BlockPos origin = BlockPos.of(entry.getLong("Origin"));
            int depth = clamp(entry.getInt("Depth"), 0, maximum);
            int targetDepth = clamp(entry.getInt("TargetDepth"), 0, maximum);
            if (version == 1 && targetDepth >= 42)
            {
                // Version 1 stopped after deleting the 42-block surface
                // skyline. Continue that same emergency order until every
                // generated building reaches the real GeoFront ceiling.
                targetDepth = maximum;
            }
            long nextStepAt = Math.max(0L, entry.getLong("NextStepAt"));
            // Absent in districts written before the layer was spread across
            // ticks; restarting a partial layer from tower zero is harmless
            // because every tower write is idempotent.
            int totalTowers = ThirdTokyoSurfaceBuilder.movableBuildings().size()
                    + LocalMapAssetLoader.tokyo3SkyscraperCount();
            int cursor = version >= 2
                    ? clamp(entry.getInt("Cursor"), 0,
                            totalTowers)
                    : 0;
            int voxelCursor = version >= 4
                    ? Math.max(0, entry.getInt("VoxelCursor"))
                    : 0;
            int queuedTargetDepth = version >= 5
                    ? clampQueuedTarget(entry.getInt("QueuedTargetDepth"), maximum)
                    : -1;
            String fault = version >= 6 ? entry.getString("Fault") : "";
            StoredDistrict district = new StoredDistrict(origin, depth, targetDepth,
                    nextStepAt, cursor, voxelCursor, queuedTargetDepth, fault);
            data.districts.put(origin.asLong(), district);
        }
        if (version == 1 && !data.districts.isEmpty())
        {
            ProjectSeele.LOGGER.warn(
                    "Migrated Tokyo-3 retraction state from surface-only v1 "
                            + "to physical GeoFront ceiling-city v2");
        }
        if (version == 2 && !data.districts.isEmpty())
        {
            ProjectSeele.LOGGER.info(
                    "Migrated Tokyo-3 layer cursor v2 -> v3; imported high-rise progress is now durable");
        }
        if (version == 3 && !data.districts.isEmpty())
        {
            ProjectSeele.LOGGER.info(
                    "Migrated Tokyo-3 travel v3 -> v4; imported towers now resume inside a bounded voxel transaction");
        }
        if (version == 4 && !data.districts.isEmpty())
        {
            ProjectSeele.LOGGER.info(
                    "Migrated Tokyo-3 travel v4 -> v5; reversals now wait for the active layer transaction");
        }
        if (version == 5 && !data.districts.isEmpty())
        {
            ProjectSeele.LOGGER.info(
                    "Migrated Tokyo-3 travel v5 -> v6; failed layers now persist fail-closed diagnostics");
        }
        return data;
    }

    public Collection<StoredDistrict> districts()
    {
        return java.util.List.copyOf(this.districts.values());
    }

    public Optional<StoredDistrict> get(BlockPos origin)
    {
        return Optional.ofNullable(this.districts.get(origin.asLong()));
    }

    public Optional<StoredDistrict> nearest(BlockPos position, double maximumDistance)
    {
        double maximumDistanceSqr = maximumDistance * maximumDistance;
        return this.districts.values().stream()
                .filter(district -> district.origin().distSqr(position) <= maximumDistanceSqr)
                .min((left, right) -> Double.compare(
                        left.origin().distSqr(position), right.origin().distSqr(position)));
    }

    public void put(StoredDistrict district)
    {
        this.districts.put(district.origin().asLong(), district);
        this.setDirty();
    }

    /**
     * Removes retired district controllers without touching any world block.
     * S20 has one authored Tokyo-3 origin; carrying the legacy prototype
     * origin beside it leaves a second independent movement transaction in
     * SavedData and can make old controls move the wrong skyline.
     */
    public List<StoredDistrict> removeAllExcept(BlockPos retainedOrigin)
    {
        ArrayList<StoredDistrict> removed = new ArrayList<>();
        long retained = retainedOrigin.asLong();
        this.districts.entrySet().removeIf(entry ->
        {
            if (entry.getKey() == retained)
            {
                return false;
            }
            removed.add(entry.getValue());
            return true;
        });
        if (!removed.isEmpty())
        {
            this.setDirty();
        }
        return List.copyOf(removed);
    }

    @Override
    public CompoundTag save(CompoundTag tag)
    {
        tag.putInt("Version", DATA_VERSION);
        ListTag entries = new ListTag();
        for (StoredDistrict district : this.districts.values())
        {
            CompoundTag entry = new CompoundTag();
            entry.putLong("Origin", district.origin().asLong());
            entry.putInt("Depth", district.depth());
            entry.putInt("TargetDepth", district.targetDepth());
            entry.putLong("NextStepAt", district.nextStepAt());
            entry.putInt("Cursor", district.cursor());
            entry.putInt("VoxelCursor", district.voxelCursor());
            entry.putInt("QueuedTargetDepth", district.queuedTargetDepth());
            entry.putString("Fault", district.fault());
            entries.add(entry);
        }
        tag.put("Districts", entries);
        return tag;
    }

    private static int clamp(int value, int minimum, int maximum)
    {
        return Math.max(minimum, Math.min(maximum, value));
    }

    private static int clampQueuedTarget(int value, int maximum)
    {
        return value < 0 ? -1 : clamp(value, 0, maximum);
    }

    /**
     * @param cursor how many towers of the layer in flight have already been
     *               stepped; zero whenever no layer is mid-flight.
     * @param voxelCursor next ordered voxel within the imported tower at
     *                    {@code cursor}; zero for generated towers and between
     *                    imported towers.
     */
    public record StoredDistrict(BlockPos origin, int depth, int targetDepth,
                                 long nextStepAt, int cursor, int voxelCursor,
                                 int queuedTargetDepth, String fault)
    {
        public StoredDistrict
        {
            origin = origin.immutable();
            fault = fault == null ? "" : fault;
        }

        public StoredDistrict(BlockPos origin, int depth, int targetDepth,
                              long nextStepAt)
        {
            this(origin, depth, targetDepth, nextStepAt, 0, 0, -1, "");
        }

        public StoredDistrict(BlockPos origin, int depth, int targetDepth,
                              long nextStepAt, int cursor)
        {
            this(origin, depth, targetDepth, nextStepAt, cursor, 0, -1, "");
        }

        public StoredDistrict(BlockPos origin, int depth, int targetDepth,
                              long nextStepAt, int cursor, int voxelCursor)
        {
            this(origin, depth, targetDepth, nextStepAt, cursor, voxelCursor, -1, "");
        }

        public StoredDistrict(BlockPos origin, int depth, int targetDepth,
                              long nextStepAt, int cursor, int voxelCursor,
                              int queuedTargetDepth)
        {
            this(origin, depth, targetDepth, nextStepAt, cursor, voxelCursor,
                    queuedTargetDepth, "");
        }

        public boolean faulted()
        {
            return !this.fault.isBlank();
        }
    }
}
