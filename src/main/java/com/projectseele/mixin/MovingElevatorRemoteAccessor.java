package com.projectseele.mixin;

import com.supermartijn642.movingelevators.blocks.RemoteControllerBlockEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Server-side bridge for the migrated in-cabin selector's measured floor. */
@Mixin(value = RemoteControllerBlockEntity.class, remap = false)
public interface MovingElevatorRemoteAccessor
{
    @Accessor("isInCabin")
    void projectSeele$setInCabin(boolean inCabin);

    @Accessor("cabinFloorIndex")
    void projectSeele$setCabinFloorIndex(int floorIndex);
}
