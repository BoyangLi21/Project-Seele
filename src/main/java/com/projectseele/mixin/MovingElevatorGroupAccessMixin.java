package com.projectseele.mixin;

import com.projectseele.world.S20MovingElevatorsAdapter;
import com.supermartijn642.movingelevators.elevator.ElevatorGroup;
import com.supermartijn642.movingelevators.elevator.ElevatorCage;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Keeps NERV destination clearance and whole-car source selection in native calls. */
@Mixin(value = ElevatorGroup.class, remap = false)
public abstract class MovingElevatorGroupAccessMixin
{
    @Redirect(method = "isCageAvailableAt(IZLnet/minecraft/world/entity/player/Player;)Z",
            at = @At(value = "INVOKE", target = "Lcom/supermartijn642/movingelevators/elevator/ElevatorCage;canCreateCage(Lnet/minecraft/world/level/Level;Lnet/minecraft/core/BlockPos;IIILnet/minecraft/world/entity/player/Player;)Z"),
            remap = false)
    private boolean projectSeele$requireWholeCommandCage(
            Level level, BlockPos anchor, int sizeX, int sizeY, int sizeZ,
            Player player)
    {
        // Keep the dependency's cache/sync and block-safety checks, but do
        // not let an overlapping stop capture a slice of the real car.
        return S20MovingElevatorsAdapter.validCommandCageSource(
                level, (ElevatorGroup) (Object) this, anchor)
                && ElevatorCage.canCreateCage(level, anchor,
                sizeX, sizeY, sizeZ, player);
    }

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
