package com.projectseele.world;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/** Durable identity registry for saved FacilitySchema v2 lift cabins. */
public final class FacilityV2LiftSavedData extends SavedData
{
    private static final String DATA_NAME =
            "projectseele_facility_v2_lifts_e2";
    private static final int DATA_VERSION = 4;

    private final Map<String, UUID> cabins = new LinkedHashMap<>();
    private final Map<String, InstallationState> installationStates =
            new LinkedHashMap<>();
    private final Map<String, Integer> rescueRecoveryRevisions =
            new LinkedHashMap<>();
    private final Map<String, Integer> architectureRevisions =
            new LinkedHashMap<>();

    public enum InstallationState
    {
        PENDING,
        INSTALLED,
        FAULT
    }

    public static FacilityV2LiftSavedData get(ServerLevel level)
    {
        return level.getDataStorage().computeIfAbsent(
                FacilityV2LiftSavedData::load,
                FacilityV2LiftSavedData::new, DATA_NAME);
    }

    public static FacilityV2LiftSavedData load(CompoundTag tag)
    {
        FacilityV2LiftSavedData data = new FacilityV2LiftSavedData();
        int version = tag.getInt("Version");
        if (version < 1 || version > DATA_VERSION)
        {
            return data;
        }
        ListTag list = tag.getList("Cabins", Tag.TAG_COMPOUND);
        for (int index = 0; index < list.size(); index++)
        {
            CompoundTag cabin = list.getCompound(index);
            String id = cabin.getString("Id");
            if (!id.isBlank() && cabin.hasUUID("Uuid"))
            {
                data.cabins.put(id, cabin.getUUID("Uuid"));
            }
            if (!id.isBlank())
            {
                InstallationState state = InstallationState.INSTALLED;
                if (version >= 2 && cabin.contains("InstallationState"))
                {
                    try
                    {
                        state = InstallationState.valueOf(
                                cabin.getString("InstallationState"));
                    }
                    catch (IllegalArgumentException ignored)
                    {
                        state = InstallationState.FAULT;
                    }
                }
                data.installationStates.put(id, state);
                if (version >= 3)
                {
                    data.rescueRecoveryRevisions.put(id,
                            cabin.getInt("RescueRecoveryRevision"));
                }
                if (version >= 4)
                {
                    data.architectureRevisions.put(id,
                            cabin.getInt("ArchitectureRevision"));
                }
            }
        }
        return data;
    }

    public Optional<UUID> cabin(String liftId)
    {
        return Optional.ofNullable(this.cabins.get(liftId));
    }

    public InstallationState installationState(String liftId)
    {
        return this.installationStates.getOrDefault(liftId,
                InstallationState.PENDING);
    }

    public boolean requestCommissioning(String liftId)
    {
        if (liftId == null || liftId.isBlank())
        {
            throw new IllegalArgumentException(
                    "Persistent lift identity cannot be empty");
        }
        if (this.installationStates.containsKey(liftId))
        {
            return this.installationStates.get(liftId)
                    == InstallationState.PENDING;
        }
        this.installationStates.put(liftId, InstallationState.PENDING);
        this.setDirty();
        return true;
    }

    public void register(String liftId, UUID uuid)
    {
        if (liftId == null || liftId.isBlank() || uuid == null)
        {
            throw new IllegalArgumentException(
                    "Persistent lift identity cannot be empty");
        }
        UUID previousUuid = this.cabins.put(liftId, uuid);
        InstallationState previousState = this.installationStates.put(
                liftId, InstallationState.INSTALLED);
        if (!uuid.equals(previousUuid)
                || previousState != InstallationState.INSTALLED)
        {
            this.setDirty();
        }
    }

    public void markFault(String liftId)
    {
        if (liftId == null || liftId.isBlank())
        {
            return;
        }
        if (this.installationStates.put(liftId,
                InstallationState.FAULT) != InstallationState.FAULT)
        {
            this.setDirty();
        }
    }

    /**
     * Clears one stale persistent identity during an explicitly versioned
     * rescue migration. Normal runtime faults remain fail-closed and never
     * enter this path.
     */
    public boolean requestRescueRecommissioning(String liftId)
    {
        if (liftId == null || liftId.isBlank()
                || installationState(liftId) != InstallationState.FAULT)
        {
            return false;
        }
        this.cabins.remove(liftId);
        this.installationStates.put(liftId, InstallationState.PENDING);
        this.setDirty();
        return true;
    }

    public boolean needsRescueRecovery(String liftId, int revision)
    {
        return this.rescueRecoveryRevisions.getOrDefault(liftId, 0)
                < revision;
    }

    public void markRescueRecoveryApplied(String liftId, int revision)
    {
        int previous = this.rescueRecoveryRevisions.getOrDefault(liftId, 0);
        if (revision > previous)
        {
            this.rescueRecoveryRevisions.put(liftId, revision);
            this.setDirty();
        }
    }

    public boolean needsArchitectureRevision(String liftId, int revision)
    {
        return this.architectureRevisions.getOrDefault(liftId, 0)
                < revision;
    }

    public void markArchitectureRevisionApplied(
            String liftId, int revision)
    {
        int previous = this.architectureRevisions.getOrDefault(liftId, 0);
        if (revision > previous)
        {
            this.architectureRevisions.put(liftId, revision);
            this.setDirty();
        }
    }

    @Override
    public CompoundTag save(CompoundTag tag)
    {
        tag.putInt("Version", DATA_VERSION);
        ListTag list = new ListTag();
        for (Map.Entry<String, UUID> entry : this.cabins.entrySet())
        {
            CompoundTag cabin = new CompoundTag();
            cabin.putString("Id", entry.getKey());
            cabin.putUUID("Uuid", entry.getValue());
            cabin.putString("InstallationState",
                    this.installationStates.getOrDefault(entry.getKey(),
                            InstallationState.INSTALLED).name());
            cabin.putInt("RescueRecoveryRevision",
                    this.rescueRecoveryRevisions.getOrDefault(
                            entry.getKey(), 0));
            cabin.putInt("ArchitectureRevision",
                    this.architectureRevisions.getOrDefault(
                            entry.getKey(), 0));
            list.add(cabin);
        }
        for (Map.Entry<String, InstallationState> entry
                : this.installationStates.entrySet())
        {
            if (this.cabins.containsKey(entry.getKey()))
            {
                continue;
            }
            CompoundTag cabin = new CompoundTag();
            cabin.putString("Id", entry.getKey());
            cabin.putString("InstallationState", entry.getValue().name());
            cabin.putInt("RescueRecoveryRevision",
                    this.rescueRecoveryRevisions.getOrDefault(
                            entry.getKey(), 0));
            cabin.putInt("ArchitectureRevision",
                    this.architectureRevisions.getOrDefault(
                            entry.getKey(), 0));
            list.add(cabin);
        }
        tag.put("Cabins", list);
        return tag;
    }
}
