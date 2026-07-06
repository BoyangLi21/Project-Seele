package com.projectseele.client;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.item.PositronCannonItem;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.util.Mth;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ComputeFovModifierEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Client-side gameplay hooks that live on the Forge bus. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class ClientForgeEvents
{
    private ClientForgeEvents() {}

    @SubscribeEvent
    public static void onComputeFovModifier(ComputeFovModifierEvent event)
    {
        // Sniper zoom: the scope narrows as the positron cannon charges.
        if (event.getPlayer() instanceof LocalPlayer player
                && player.isUsingItem()
                && player.getUseItem().getItem() instanceof PositronCannonItem
                && player.getVehicle() instanceof EvaUnit01Entity)
        {
            float progress = PositronCannonItem.chargeProgress(player);
            event.setNewFovModifier(Mth.lerp(progress, 1.0F, 0.16F));
        }
    }
}
