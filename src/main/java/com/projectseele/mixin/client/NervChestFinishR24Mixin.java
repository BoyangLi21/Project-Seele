package com.projectseele.mixin.client;

import com.projectseele.client.render.NervChestFinishR24;
import net.minecraft.client.renderer.blockentity.ChestRenderer;
import net.minecraft.client.resources.model.Material;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.properties.ChestType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(ChestRenderer.class)
public abstract class NervChestFinishR24Mixin
{
    @Inject(method="getMaterial",at=@At("HEAD"),cancellable=true,remap=false)
    private void seele$equipmentCase(BlockEntity entity,ChestType type,CallbackInfoReturnable<Material> callback)
    {Material selected=NervChestFinishR24.material(entity);if(selected!=null)callback.setReturnValue(selected);}
}
