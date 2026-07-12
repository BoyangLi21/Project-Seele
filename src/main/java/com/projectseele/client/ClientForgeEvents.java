package com.projectseele.client;

import com.projectseele.ProjectSeele;
import com.projectseele.client.visual.VisualCaptureManager;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.network.ServerboundEvaControlPacket;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ComputeFovModifierEvent;
import net.minecraftforge.client.event.InputEvent;
import net.minecraftforge.client.event.RenderHandEvent;
import net.minecraftforge.client.event.RenderGuiOverlayEvent;
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
    /** Entry-plug insertion cinematic: counts down after boarding. */
    private static final int INSERTION_LENGTH = 120;
    private static int insertionTicks;
    private static int pilotTicks;
    private static int damageFlashTicks;
    private static float lastEvaHealth = -1.0F;
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

    public static float damageFlash(float partialTick)
    {
        return Mth.clamp((damageFlashTicks - partialTick) / 18.0F, 0.0F, 1.0F);
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
            lastEvaHealth = eva.getHealth();
            playPlugSound(minecraft, SoundEvents.PISTON_EXTEND, 1.4F, 0.55F);
        }
        pilotTicks = piloting ? pilotTicks + 1 : 0;
        wasPiloting = piloting;
        if (insertionTicks > 0 && !minecraft.isPaused())
        {
            if (insertionTicks == 96)
            {
                playPlugSound(minecraft, SoundEvents.IRON_DOOR_CLOSE, 1.2F, 0.72F);
            }
            else if (insertionTicks == 68)
            {
                playPlugSound(minecraft, SoundEvents.BEACON_POWER_SELECT, 1.0F, 0.62F);
            }
            else if (insertionTicks == 32)
            {
                playPlugSound(minecraft, SoundEvents.BEACON_ACTIVATE, 1.0F, 1.18F);
            }
            insertionTicks--;
        }
        if (damageFlashTicks > 0 && !minecraft.isPaused())
        {
            damageFlashTicks--;
        }
        if (eva != null)
        {
            if (lastEvaHealth >= 0.0F && eva.getHealth() < lastEvaHealth)
            {
                damageFlashTicks = 18;
            }
            lastEvaHealth = eva.getHealth();
        }
        else
        {
            lastEvaHealth = -1.0F;
            damageFlashTicks = 0;
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

    private static void playPlugSound(Minecraft minecraft, SoundEvent sound, float volume, float pitch)
    {
        if (minecraft.level != null && minecraft.player != null)
        {
            minecraft.level.playLocalSound(minecraft.player.getX(), minecraft.player.getY(), minecraft.player.getZ(),
                    sound, SoundSource.PLAYERS, volume, pitch, false);
        }
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
            send(ServerboundEvaControlPacket.ACTION_MELEE);
        }
        else if (event.isUseItem())
        {
            // Never let the pilot eat/place things through the plug wall.
            event.setCanceled(true);
            event.setSwingHand(false);
            if (eva.getWeapon() != EvaUnit01Entity.WEAPON_CANNON)
            {
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
    }

    @SubscribeEvent
    public static void onRenderGuiOverlay(RenderGuiOverlayEvent.Pre event)
    {
        if (VisualCaptureManager.isSuppressingGui())
        {
            event.setCanceled(true);
        }
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
