package com.projectseele.client;

import com.projectseele.ProjectSeele;
import com.projectseele.client.render.EvaCockpitArms;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.network.ServerboundEvaControlPacket;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.InteractionHand;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ComputeFovModifierEvent;
import net.minecraftforge.client.event.InputEvent;
import net.minecraftforge.client.event.RenderHandEvent;
import net.minecraftforge.client.event.RenderPlayerEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.lwjgl.glfw.GLFW;

/** Client-side pilot input: keybinds, attack interception, sniper zoom. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class ClientForgeEvents
{
    /** Tracks the held use-key while the cannon is out (charge start/stop). */
    private static boolean chargeHeld;
    private static boolean crouchHeld;
    private static boolean sprintHeld;
    private static boolean jumpHeld;
    private static boolean cockpitLeftSwing;
    private static int cockpitAction = EvaCockpitArms.ACTION_NONE;
    private static int cockpitActionTicks;
    private static EvaCockpitArms cockpitArms;
    /** Entry-plug insertion cinematic: counts down after boarding. */
    private static final int INSERTION_LENGTH = 50;
    private static int insertionTicks;
    private static int pilotTicks;
    private static boolean wasPiloting;

    private ClientForgeEvents() {}

    /** 0..1 elapsed progress of the plug-insertion overlay, or -1 when idle. */
    public static float insertionProgress(float partialTick)
    {
        if (insertionTicks <= 0)
        {
            return -1.0F;
        }
        return Mth.clamp((INSERTION_LENGTH - insertionTicks + partialTick) / INSERTION_LENGTH, 0.0F, 1.0F);
    }

    public static int pilotTicks()
    {
        return pilotTicks;
    }

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
        Minecraft minecraft = Minecraft.getInstance();
        LocalPlayer player = minecraft.player;
        EvaUnit01Entity eva = ridden(player);

        // While piloting, Shift belongs to the Unit's legs. Clear vanilla's
        // dismount input before LocalPlayer processes it; V is the explicit
        // entry-plug eject key.
        boolean rawCrouch = eva != null && rawKey(minecraft,
                GLFW.GLFW_KEY_LEFT_SHIFT, GLFW.GLFW_KEY_RIGHT_SHIFT);
        if (event.phase == TickEvent.Phase.START)
        {
            if (eva != null)
            {
                minecraft.options.keyShift.setDown(false);
                player.setShiftKeyDown(false);
            }
            return;
        }

        // Boarding transition: play the entry-plug insertion cinematic.
        boolean piloting = eva != null;
        if (piloting && !wasPiloting)
        {
            insertionTicks = INSERTION_LENGTH;
            pilotTicks = 0;
        }
        pilotTicks = piloting ? pilotTicks + 1 : 0;
        wasPiloting = piloting;
        if (insertionTicks > 0 && !minecraft.isPaused())
        {
            insertionTicks--;
        }
        if (cockpitActionTicks > 0 && !minecraft.isPaused())
        {
            cockpitActionTicks--;
            if (cockpitActionTicks == 0)
            {
                cockpitAction = EvaCockpitArms.ACTION_NONE;
            }
        }

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
        while (Keybinds.EXIT_EVA.consumeClick())
        {
            if (eva != null)
            {
                send(ServerboundEvaControlPacket.ACTION_EXIT);
            }
        }
        while (Keybinds.STOMP.consumeClick())
        {
            if (eva != null && eva.getWeapon() != EvaUnit01Entity.WEAPON_CANNON)
            {
                cockpitAction = EvaCockpitArms.ACTION_STOMP;
                cockpitActionTicks = 12;
                send(ServerboundEvaControlPacket.ACTION_STOMP);
            }
        }
        while (Keybinds.TOGGLE_PRONE.consumeClick())
        {
            if (eva != null)
            {
                send(ServerboundEvaControlPacket.ACTION_TOGGLE_PRONE);
            }
        }

        if (eva != null && minecraft.screen == null)
        {
            boolean rawSprint = rawKey(minecraft,
                    GLFW.GLFW_KEY_LEFT_CONTROL, GLFW.GLFW_KEY_RIGHT_CONTROL);
            boolean rawJump = minecraft.options.keyJump.isDown();
            if (rawCrouch != crouchHeld)
            {
                crouchHeld = rawCrouch;
                send(rawCrouch ? ServerboundEvaControlPacket.ACTION_CROUCH_START
                        : ServerboundEvaControlPacket.ACTION_CROUCH_STOP);
            }
            if (rawSprint != sprintHeld)
            {
                sprintHeld = rawSprint;
                send(rawSprint ? ServerboundEvaControlPacket.ACTION_SPRINT_START
                        : ServerboundEvaControlPacket.ACTION_SPRINT_STOP);
            }
            if (rawJump && !jumpHeld)
            {
                send(ServerboundEvaControlPacket.ACTION_JUMP);
            }
            jumpHeld = rawJump;
            minecraft.options.keyShift.setDown(false);
            player.setShiftKeyDown(false);
        }
        else
        {
            crouchHeld = false;
            sprintHeld = false;
            jumpHeld = false;
        }

        // Hold-to-charge: mirror the use key into charge start/stop packets.
        boolean wantCharge = eva != null
                && eva.getWeapon() == EvaUnit01Entity.WEAPON_CANNON
                && minecraft.screen == null
                && minecraft.options.keyUse.isDown();
        if (wantCharge != chargeHeld)
        {
            if (!wantCharge && chargeHeld && eva != null && eva.chargeProgress() >= 1.0F)
            {
                cockpitAction = EvaCockpitArms.ACTION_FIRE;
                cockpitActionTicks = 12;
            }
            chargeHeld = wantCharge;
            send(wantCharge
                    ? ServerboundEvaControlPacket.ACTION_CHARGE_START
                    : ServerboundEvaControlPacket.ACTION_CHARGE_STOP);
        }
    }

    private static boolean rawKey(Minecraft minecraft, int left, int right)
    {
        long window = minecraft.getWindow().getWindow();
        return GLFW.glfwGetKey(window, left) == GLFW.GLFW_PRESS
                || GLFW.glfwGetKey(window, right) == GLFW.GLFW_PRESS;
    }

    /**
     * From the plug the mouse drives the Unit, not the pilot's own hands:
     * left-click swings and right-click slams. With the cannon out,
     * right-click is the charge trigger handled by the hold-tracking above.
     */
    @SubscribeEvent
    public static void onInteractionKey(InputEvent.InteractionKeyMappingTriggered event)
    {
        LocalPlayer player = Minecraft.getInstance().player;
        EvaUnit01Entity eva = ridden(player);
        if (eva == null)
        {
            return;
        }
        if (event.isAttack())
        {
            event.setCanceled(true);
            event.setSwingHand(false);
            cockpitLeftSwing = !cockpitLeftSwing;
            cockpitAction = eva.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE
                    ? EvaCockpitArms.ACTION_RIGHT
                    : cockpitLeftSwing ? EvaCockpitArms.ACTION_LEFT : EvaCockpitArms.ACTION_RIGHT;
            cockpitActionTicks = 12;
            send(ServerboundEvaControlPacket.ACTION_MELEE);
        }
        else if (event.isUseItem())
        {
            // Never let the pilot eat/place things through the plug wall.
            event.setCanceled(true);
            event.setSwingHand(false);
            if (eva.getWeapon() != EvaUnit01Entity.WEAPON_CANNON)
            {
                cockpitAction = EvaCockpitArms.ACTION_SMASH;
                cockpitActionTicks = 12;
                send(ServerboundEvaControlPacket.ACTION_SMASH);
            }
        }
    }

    @SubscribeEvent
    public static void onRenderHand(RenderHandEvent event)
    {
        Minecraft minecraft = Minecraft.getInstance();
        EvaUnit01Entity eva = ridden(minecraft.player);
        if (eva == null || !minecraft.options.getCameraType().isFirstPerson())
        {
            return;
        }
        event.setCanceled(true);
        if (event.getHand() != InteractionHand.MAIN_HAND)
        {
            return;
        }
        if (cockpitArms == null)
        {
            cockpitArms = new EvaCockpitArms(minecraft.getEntityModels().bakeLayer(EvaCockpitArms.LAYER));
            ProjectSeele.LOGGER.info("EVA cockpit arms renderer active");
        }
        cockpitArms.render(event.getPoseStack(), event.getMultiBufferSource(), event.getPackedLight(),
                eva, event.getPartialTick(), cockpitAction, cockpitActionTicks);
    }

    @SubscribeEvent
    public static void onRenderPlayer(RenderPlayerEvent.Pre event)
    {
        if (event.getEntity().getVehicle() instanceof EvaUnit01Entity)
        {
            event.setCanceled(true);
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
