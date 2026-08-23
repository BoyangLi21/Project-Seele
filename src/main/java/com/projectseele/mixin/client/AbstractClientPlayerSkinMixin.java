package com.projectseele.mixin.client;

import com.projectseele.client.GendoPlayerSkinClient;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.resources.ResourceLocation;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Replaces only this client's own skin; remote players keep their profiles. */
@Mixin(AbstractClientPlayer.class)
public abstract class AbstractClientPlayerSkinMixin
{
    @Inject(method = "getSkinTextureLocation", at = @At("HEAD"),
            cancellable = true)
    private void projectSeele$useCommanderSkin(
            CallbackInfoReturnable<ResourceLocation> callback)
    {
        ResourceLocation texture = GendoPlayerSkinClient.textureFor(
                (AbstractClientPlayer)(Object)this);
        if (texture != null)
        {
            callback.setReturnValue(texture);
        }
    }
}
