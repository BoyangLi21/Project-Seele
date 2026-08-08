package com.projectseele.world;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/** Durable cursor for an explicitly started FacilitySchema v2 build phase. */
public final class FacilityV2ProgrammeSavedData extends SavedData
{
    private static final String DATA_NAME =
            "projectseele_facility_v2_programme_e2";

    private boolean active;
    private String programme = "";
    private int index;
    private String failure = "";

    public static FacilityV2ProgrammeSavedData get(ServerLevel level)
    {
        return level.getDataStorage().computeIfAbsent(
                FacilityV2ProgrammeSavedData::load,
                FacilityV2ProgrammeSavedData::new, DATA_NAME);
    }

    private static FacilityV2ProgrammeSavedData load(CompoundTag tag)
    {
        FacilityV2ProgrammeSavedData data =
                new FacilityV2ProgrammeSavedData();
        data.active = tag.getBoolean("Active");
        data.programme = tag.getString("Programme");
        data.index = Math.max(0, tag.getInt("Index"));
        data.failure = tag.getString("Failure");
        return data;
    }

    public void start(String programme)
    {
        if (this.active)
        {
            throw new IllegalStateException(
                    "Facility programme already active: " + this.programme);
        }
        this.active = true;
        this.programme = programme;
        this.index = 0;
        this.failure = "";
        this.setDirty();
    }

    public void advance()
    {
        this.index++;
        this.setDirty();
    }

    public void complete()
    {
        this.active = false;
        this.failure = "";
        this.setDirty();
    }

    public void fail(String reason)
    {
        this.active = false;
        this.failure = reason;
        this.setDirty();
    }

    public boolean active()
    {
        return this.active;
    }

    public String programme()
    {
        return this.programme;
    }

    public int index()
    {
        return this.index;
    }

    public String summary()
    {
        return "programme=" + (this.programme.isBlank()
                ? "none" : this.programme)
                + " active=" + this.active
                + " index=" + this.index
                + (this.failure.isBlank() ? "" : " failure=" + this.failure);
    }

    @Override
    public CompoundTag save(CompoundTag tag)
    {
        tag.putBoolean("Active", this.active);
        tag.putString("Programme", this.programme);
        tag.putInt("Index", this.index);
        tag.putString("Failure", this.failure);
        return tag;
    }
}
