package com.projectseele.client;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.network.ServerboundEvaControlPacket;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.util.Mth;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ComputeFovModifierEvent;
import net.minecraftforge.client.event.InputEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Client-side pilot input: keybinds, attack interception, sniper zoom. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class ClientForgeEvents
{
    /** Tracks the held use-key while the cannon is out (charge start/stop). */
    private static boolean chargeHeld;

    private ClientForgeEvents() {}

    private static void send(int action)
    {
        SeeleNetwork.CHANNEL.sendToServer(new ServerboundEvaControlPacket(action));
    }

    private static EvaUnit01Entity ridden(LocalPlayer player)
    {
        return player != null && player.getVehicle() instanceof EvaUnit01Entity eva ? eva : null;
    }

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END)
        {
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        LocalPlayer player = minecraft.player;
        EvaUnit01Entity eva = ridden(player);

        while (Keybinds.CYCLE_WEAPON.consumeClick())
        {
            if (eva != null)
            {
                send(ServerboundEvaControlPacket.ACTION_CYCLE_WEAPON);
            }
        }
        while (Keybinds.TOGGLE_AT_FIELD.consumeClick())
        {
            if (eva != null)
            {
                send(ServerboundEvaControlPacket.ACTION_TOGGLE_AT_FIELD);
            }
        }

        // Hold-to-charge: mirror the use key into charge start/stop packets.
        boolean wantCharge = eva != null
                && eva.getWeapon() == EvaUnit01Entity.WEAPON_CANNON
                && minecraft.screen == null
                && minecraft.options.keyUse.isDown();
        if (wantCharge != chargeHeld)
        {
            chargeHeld = wantCharge;
            send(wantCharge
                    ? ServerboundEvaControlPacket.ACTION_CHARGE_START
                    : ServerboundEvaControlPacket.ACTION_CHARGE_STOP);
        }
    }

    /** Left-click from the plug drives the Unit's melee, not the pilot's arm. */
    @SubscribeEvent
    public static void onInteractionKey(InputEvent.InteractionKeyMappingTriggered event)
    {
        LocalPlayer player = Minecraft.getInstance().player;
        if (event.isAttack() && ridden(player) != null)
        {
            event.setCanceled(true);
            event.setSwingHand(false);
            send(ServerboundEvaControlPacket.ACTION_MELEE);
        }
    }

    @SubscribeEvent
    public static void onComputeFovModifier(ComputeFovModifierEvent event)
    {
        // Sniper zoom: the scope narrows as the positron cannon charges.
        if (event.getPlayer() instanceof LocalPlayer player)
        {
            EvaUnit01Entity eva = ridden(player);
            if (eva != null && eva.getWeapon() == EvaUnit01Entity.WEAPON_CANNON && eva.getCannonCharge() > 0)
            {
                event.setNewFovModifier(Mth.lerp(eva.chargeProgress(), 1.0F, 0.16F));
            }
        }
    }
}
