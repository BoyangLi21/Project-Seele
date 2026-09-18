package com.projectseele.mixin.client;
import com.projectseele.client.PianoScreenCompatibilityR22;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.world.inventory.Slot;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.*;
/** The optional piano adds normal inventory slots over its play keyboard. */
@Mixin(AbstractContainerScreen.class)
public abstract class PianoInventoryOverlayR22Mixin
{
    @Inject(method="renderSlot",at=@At("HEAD"),cancellable=true)
    private void projectSeele$clearKeyboard(GuiGraphics gui,Slot slot,CallbackInfo ci)
    {if(PianoScreenCompatibilityR22.playTab(this))ci.cancel();}
    @Inject(method="findSlot",at=@At("HEAD"),cancellable=true)
    private void projectSeele$noInvisibleInventory(double x,double y,CallbackInfoReturnable<Slot> ci)
    {if(PianoScreenCompatibilityR22.playTab(this))ci.setReturnValue(null);}
}
