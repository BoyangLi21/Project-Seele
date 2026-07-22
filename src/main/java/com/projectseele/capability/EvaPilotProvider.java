package com.projectseele.capability;

import com.projectseele.ProjectSeele;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.common.capabilities.Capability;
import net.minecraftforge.common.capabilities.ICapabilitySerializable;
import net.minecraftforge.common.util.LazyOptional;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/** Forge attachment wrapper for one player's persistent pilot data. */
public final class EvaPilotProvider implements ICapabilitySerializable<CompoundTag>
{
    public static final ResourceLocation ID = new ResourceLocation(
            ProjectSeele.MODID, "eva_pilot");

    private final EvaPilotData data = new EvaPilotData();
    private final LazyOptional<EvaPilotData> optional = LazyOptional.of(() -> this.data);

    @Override
    public <T> @NotNull LazyOptional<T> getCapability(@NotNull Capability<T> capability,
                                                       @Nullable Direction side)
    {
        return capability == EvaPilotCapability.DATA ? this.optional.cast() : LazyOptional.empty();
    }

    @Override
    public CompoundTag serializeNBT()
    {
        return this.data.serialize();
    }

    @Override
    public void deserializeNBT(CompoundTag tag)
    {
        this.data.deserialize(tag);
    }
}