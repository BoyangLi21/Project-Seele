package com.projectseele.world;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/**
 * Restart-safe receipt for the cosmetic command-room layer.
 *
 * <p>The structural COMMAND_VOLUME receipt is intentionally immutable once it
 * has been accepted.  Interior art revisions therefore advance through this
 * separate cursor and never reopen or invalidate the room's civil owner.</p>
 */
public final class FacilityV2CommandInteriorSavedData extends SavedData
{
    private static final String DATA_NAME =
            "projectseele_facility_v2_command_interior_e2";

    private int targetRevision;
    private int appliedRevision;
    private long cursor;
    private boolean commandAssetInstalled;

    public static FacilityV2CommandInteriorSavedData get(ServerLevel level)
    {
        return level.getDataStorage().computeIfAbsent(
                FacilityV2CommandInteriorSavedData::load,
                FacilityV2CommandInteriorSavedData::new, DATA_NAME);
    }

    public static FacilityV2CommandInteriorSavedData load(CompoundTag tag)
    {
        FacilityV2CommandInteriorSavedData data =
                new FacilityV2CommandInteriorSavedData();
        data.targetRevision = Math.max(0, tag.getInt("TargetRevision"));
        data.appliedRevision = Math.max(0, tag.getInt("AppliedRevision"));
        data.cursor = Math.max(0L, tag.getLong("Cursor"));
        data.commandAssetInstalled = tag.getBoolean("CommandAssetInstalled");
        return data;
    }

    public void prepare(int revision)
    {
        if (this.appliedRevision >= revision)
        {
            return;
        }
        if (this.targetRevision != revision)
        {
            this.targetRevision = revision;
            this.cursor = 0L;
            this.commandAssetInstalled = false;
            this.setDirty();
        }
    }

    public boolean needsWork(int revision)
    {
        return this.appliedRevision < revision;
    }

    public long cursor()
    {
        return this.cursor;
    }

    public int appliedRevision()
    {
        return this.appliedRevision;
    }

    public boolean commandAssetInstalled()
    {
        return this.commandAssetInstalled;
    }

    public void markCommandAssetInstalled()
    {
        this.commandAssetInstalled = true;
        this.setDirty();
    }

    public void updateCursor(long newCursor)
    {
        this.cursor = Math.max(0L, newCursor);
        this.setDirty();
    }

    public void complete(int revision)
    {
        this.targetRevision = revision;
        this.appliedRevision = revision;
        this.cursor = 0L;
        this.setDirty();
    }

    public void reset()
    {
        this.targetRevision = 0;
        this.appliedRevision = 0;
        this.cursor = 0L;
        this.commandAssetInstalled = false;
        this.setDirty();
    }

    @Override
    public CompoundTag save(CompoundTag tag)
    {
        tag.putInt("TargetRevision", this.targetRevision);
        tag.putInt("AppliedRevision", this.appliedRevision);
        tag.putLong("Cursor", this.cursor);
        tag.putBoolean("CommandAssetInstalled",
                this.commandAssetInstalled);
        return tag;
    }
}
