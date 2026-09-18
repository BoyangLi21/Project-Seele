package com.projectseele.mixin.client;
import com.projectseele.client.*;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
@Mixin(LocalPlayer.class)
public abstract class LocalPlayerLiftPacketsR22Mixin
{
    @Inject(method="sendPosition",at=@At("HEAD"),cancellable=true)
    private void projectSeele$afterNativeCarrier(CallbackInfo ci)
    {if(LiftPassengerPacketsR22.defer((Player)(Object)this))ci.cancel();}
}
