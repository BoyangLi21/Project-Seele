package com.projectseele.mixin;

import com.projectseele.world.S20MovingElevatorsAdapter;
import com.supermartijn642.movingelevators.elevator.ElevatorGroup;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Applies NERV clearance to the chosen destination, not the whole panel. */
@Mixin(value = ElevatorGroup.class, remap = false)
public abstract class MovingElevatorGroupAccessMixin
{
    @Inject(method = "onDisplayPress", at = @At("HEAD"),
            cancellable = true, remap = false)
    private void projectSeele$checkDestinationClearance(
            int floorLevel, int floorOffset, Player player,
            CallbackInfo callback)
    {
        if (!S20MovingElevatorsAdapter.allowDisplayPress(
                (ElevatorGroup) (Object) this,
                floorLevel, floorOffset, player))
        {
            callback.cancel();
        }
    }
}
