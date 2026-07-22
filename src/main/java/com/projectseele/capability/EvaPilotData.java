package com.projectseele.capability;

import com.projectseele.config.SeeleConfig;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.util.Mth;

/** Persistent neural-connection progress owned by one pilot. */
public final class EvaPilotData
{
    private static final float FALLBACK_INITIAL_SYNCHRONIZATION = 40.0F;
    private static final float FALLBACK_MAX_SYNCHRONIZATION = 100.0F;
    private static final int GROWTH_INTERVAL_TICKS = 20 * 60;

    private float synchronization = initialSynchronization();
    private int activeDrivingTicks;

    public float synchronization()
    {
        return this.synchronization;
    }

    public int activeDrivingTicks()
    {
        return this.activeDrivingTicks;
    }

    /** Returns true only when a full minute grants visible progress. */
    public boolean tickActiveDriving()
    {
        this.activeDrivingTicks++;
        if (this.activeDrivingTicks < GROWTH_INTERVAL_TICKS)
        {
            return false;
        }
        this.activeDrivingTicks = 0;
        return this.increase(driveGainPerMinute()) > 0.0F;
    }

    public float increase(float amount)
    {
        float oldValue = this.synchronization;
        this.synchronization = Mth.clamp(oldValue + Math.max(0.0F, amount),
                0.0F, maxSynchronization());
        return this.synchronization - oldValue;
    }

    public void setSynchronization(float value)
    {
        this.synchronization = Mth.clamp(value, 0.0F, maxSynchronization());
    }

    public void copyFrom(EvaPilotData other)
    {
        this.synchronization = other.synchronization;
        this.activeDrivingTicks = other.activeDrivingTicks;
    }

    public CompoundTag serialize()
    {
        CompoundTag tag = new CompoundTag();
        tag.putFloat("Synchronization", this.synchronization);
        tag.putInt("ActiveDrivingTicks", this.activeDrivingTicks);
        return tag;
    }

    public void deserialize(CompoundTag tag)
    {
        this.synchronization = tag.contains("Synchronization")
                ? Mth.clamp(tag.getFloat("Synchronization"), 0.0F, maxSynchronization())
                : initialSynchronization();
        this.activeDrivingTicks = Mth.clamp(tag.getInt("ActiveDrivingTicks"),
                0, GROWTH_INTERVAL_TICKS - 1);
    }

    public static float initialSynchronization()
    {
        return SeeleConfig.COMMON_SPEC != null && SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.EVA_SYNC_INITIAL.get().floatValue()
                : FALLBACK_INITIAL_SYNCHRONIZATION;
    }

    public static float maxSynchronization()
    {
        return SeeleConfig.COMMON_SPEC != null && SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.EVA_SYNC_MAX.get().floatValue()
                : FALLBACK_MAX_SYNCHRONIZATION;
    }

    private static float driveGainPerMinute()
    {
        return SeeleConfig.COMMON_SPEC != null && SeeleConfig.COMMON_SPEC.isLoaded()
                ? SeeleConfig.EVA_SYNC_DRIVE_GAIN_PER_MINUTE.get().floatValue()
                : 0.25F;
    }
}