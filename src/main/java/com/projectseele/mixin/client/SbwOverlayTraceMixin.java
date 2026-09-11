package com.projectseele.mixin.client;

import com.projectseele.entity.EntryPlugCarrierEntity;
import com.projectseele.world.EvaPilotResolver;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.BlockHitResult;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** SBW weapon sights are inactive while SEELE owns the cockpit or spectator view. */
@Pseudo
@Mixin(targets="com.atsuishio.superbwarfare.client.overlay.OverlayTraceHandler",remap=false)
public abstract class SbwOverlayTraceMixin
{
    @Shadow public static Entity cameraEntity;
    @Shadow public static Entity cameraMaxRangeEntity;
    @Shadow public static BlockHitResult blockMaxRangeResult;

    @Inject(method="handleCameraTrace",at=@At("HEAD"),cancellable=true,remap=false)
    private static void seele$ownedCockpit(Player player,CallbackInfo callback)
    {
        if(player.isSpectator()||player.getRootVehicle() instanceof EntryPlugCarrierEntity
                ||EvaPilotResolver.controlTarget(player)!=null)
        {
            cameraEntity=null;cameraMaxRangeEntity=null;blockMaxRangeResult=null;
            callback.cancel();
        }
    }
}
