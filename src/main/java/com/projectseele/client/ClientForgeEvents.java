package com.projectseele.client;

import com.projectseele.ProjectSeele;
import com.projectseele.client.visual.VisualCaptureManager;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.network.ServerboundEntryPlugPacket;
import com.projectseele.network.ServerboundEvaControlPacket;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ComputeFovModifierEvent;
import net.minecraftforge.client.event.InputEvent;
import net.minecraftforge.client.event.RenderHandEvent;
import net.minecraftforge.client.event.RenderGuiOverlayEvent;
import net.minecraftforge.client.event.RenderPlayerEvent;
import net.minecraftforge.client.gui.overlay.VanillaGuiOverlay;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.lwjgl.glfw.GLFW;

/** Client-side pilot input: keybinds, attack interception, sniper zoom. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class ClientForgeEvents
{
    /** Tracks the held use-key for cannon charge or N2 arming edges. */
    private static boolean chargeHeld;
    /** Local optical sight state; rifle fire itself remains server-authoritative. */
    private static boolean rifleAimHeld;
    private static boolean crouchHeld;
    private static boolean sprintHeld;
    private static boolean jumpHeld;
    /** A held jump stays pending until the EVA's synchronized sequence acknowledges it. */
    private static boolean jumpRequestPending;
    private static int jumpRequestSequence;
    private static int jumpRequestId;
    private static int jumpRequestIdCounter;
    private static int jumpRequestRetryTicks;
    private static int jumpRequestEvaId = -1;
    private static final int JUMP_REQUEST_RETRY_INTERVAL = 4;
    /** Entry-plug insertion cinematic: counts down after boarding. */
    private static final int INSERTION_LENGTH = 120;
    private static int insertionTicks;
    private static int pilotTicks;
    private static int damageFlashTicks;
    private static float lastEvaHealth = -1.0F;
    private static boolean wasPiloting;
    /** Forge may report the same use press once for each hand. */
    private static int lastEntryPlugRequestTick = Integer.MIN_VALUE;

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

    /** Immediate local input state, used so optical/N2 overlays do not wait for a round trip. */
    public static boolean isWeaponUseHeld()
    {
        return chargeHeld;
    }

    public static boolean isCannonScopeActive(EvaUnit01Entity eva)
    {
        return eva != null && eva.getWeapon() == EvaUnit01Entity.WEAPON_CANNON
                && (chargeHeld || eva.getCannonCharge() > 0);
    }

    public static boolean isRifleSightActive(EvaUnit01Entity eva)
    {
        return eva != null && eva.getWeapon() == EvaUnit01Entity.WEAPON_RIFLE
                && rifleAimHeld;
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
            if (eva != null && eva.isMeleeWeapon())
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
            if (eva.getWeapon() == EvaUnit01Entity.WEAPON_CANNON
                    || eva.getWeapon() == EvaUnit01Entity.WEAPON_RIFLE)
            {
                // Keep the camera, server ray and physical aim parent on one
                // mechanical elevation envelope. Without this, the optical
                // crosshair can look beyond the barrel's clamped hit ray.
                float pitch = Mth.clamp(player.getXRot(),
                        EvaUnit01Entity.MIN_CANNON_AIM_PITCH,
                        EvaUnit01Entity.MAX_CANNON_AIM_PITCH);
                player.setXRot(pitch);
                player.xRotO = pitch;
            }
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
            handleJumpInput(eva, rawJump);
            minecraft.options.keyShift.setDown(false);
            player.setShiftKeyDown(false);
        }
        else
        {
            // Send release edges before clearing the client cache. Otherwise
            // opening a menu while Shift/Ctrl is held can leave the server
            // EVA permanently crouched or sprinting after the key is released
            // behind the GUI.
            if (eva != null)
            {
                if (crouchHeld)
                {
                    send(ServerboundEvaControlPacket.ACTION_CROUCH_STOP);
                }
                if (sprintHeld)
                {
                    send(ServerboundEvaControlPacket.ACTION_SPRINT_STOP);
                }
            }
            crouchHeld = false;
            sprintHeld = false;
            clearJumpRequest();
        }

        // Hold-to-use: cannon optical charge and N2 arming share one validated
        // server edge, but expose different synchronized progress values.
        boolean wantCharge = eva != null
                && (eva.getWeapon() == EvaUnit01Entity.WEAPON_CANNON
                    || eva.getWeapon() == EvaUnit01Entity.WEAPON_N2)
                && minecraft.screen == null
                && minecraft.options.keyUse.isDown();
        if (wantCharge != chargeHeld)
        {
            chargeHeld = wantCharge;
            send(wantCharge
                    ? ServerboundEvaControlPacket.ACTION_CHARGE_START
                    : ServerboundEvaControlPacket.ACTION_CHARGE_STOP);
        }
        rifleAimHeld = eva != null
                && eva.getWeapon() == EvaUnit01Entity.WEAPON_RIFLE
                && minecraft.screen == null
                && minecraft.options.keyUse.isDown();

        // The pallet SMG is automatic. The client may request every tick;
        // the entity's authoritative cooldown determines the actual fire rate.
        if (eva != null && eva.getWeapon() == EvaUnit01Entity.WEAPON_RIFLE
                && minecraft.screen == null && minecraft.options.keyAttack.isDown())
        {
            send(ServerboundEvaControlPacket.ACTION_RIFLE_FIRE);
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
            if (player != null && event.isUseItem() && !player.isShiftKeyDown())
            {
                EvaUnit01Entity entryTarget = findEntryPlugTarget(player);
                if (entryTarget != null)
                {
                    // The synthetic dorsal plug sits outside parts of the
                    // coarse 8.5-wide collision box. Extend only this narrow
                    // aimed interaction; the server repeats every gate.
                    event.setCanceled(true);
                    event.setSwingHand(false);
                    if (lastEntryPlugRequestTick != player.tickCount)
                    {
                        lastEntryPlugRequestTick = player.tickCount;
                        SeeleNetwork.CHANNEL.sendToServer(
                                new ServerboundEntryPlugPacket(entryTarget.getId()));
                    }
                }
            }
            return;
        }
        if (event.isAttack())
        {
            event.setCanceled(true);
            event.setSwingHand(false);
            if (eva.isMeleeWeapon())
            {
                send(ServerboundEvaControlPacket.ACTION_MELEE);
            }
        }
        else if (event.isUseItem())
        {
            // Never let the pilot eat/place things through the plug wall.
            event.setCanceled(true);
            event.setSwingHand(false);
            if (eva.isMeleeWeapon())
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
        // Suppress the player's normal item/skin hands. The EVA is already
        // rendered once in world space by EvaUnit01Renderer; drawing it again
        // here would create a second camera-space pose that can never remain
        // identical to the third-person skeleton.
        event.setCanceled(true);
    }

    @SubscribeEvent
    public static void onRenderGuiOverlay(RenderGuiOverlayEvent.Pre event)
    {
        if (VisualCaptureManager.isSuppressingGui())
        {
            event.setCanceled(true);
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        EvaUnit01Entity eva = ridden(minecraft.player);
        boolean opticalSight = isCannonScopeActive(eva) || isRifleSightActive(eva);
        if (opticalSight && (event.getOverlay() == VanillaGuiOverlay.HOTBAR.type()
                || event.getOverlay() == VanillaGuiOverlay.CROSSHAIR.type()))
        {
            event.setCanceled(true);
        }
    }

    /**
     * Do not consume a jump press merely because activation, launch interlock,
     * or a transient server ground check prevents it on the first tick. The
     * synchronized jump sequence is the acknowledgement; until it changes a
     * held key retries at a low rate once local control is available.
     */
    private static void handleJumpInput(EvaUnit01Entity eva, boolean rawJump)
    {
        if (!rawJump)
        {
            clearJumpRequest();
            return;
        }

        if (!jumpHeld || jumpRequestEvaId != eva.getId())
        {
            jumpHeld = true;
            jumpRequestPending = true;
            jumpRequestSequence = eva.getJumpSequence();
            jumpRequestId = ++jumpRequestIdCounter;
            jumpRequestRetryTicks = 0;
            jumpRequestEvaId = eva.getId();
        }

        if (!jumpRequestPending)
        {
            return;
        }
        if (eva.getJumpSequence() != jumpRequestSequence)
        {
            jumpRequestPending = false;
            return;
        }

        boolean locallyUnlocked = eva.getActivationTicks() <= 20
                && !eva.isLaunchSequenceActive() && eva.getCannonCharge() <= 0;
        if (!locallyUnlocked)
        {
            // Leave the request armed. A key held through entry-plug startup
            // is sent on the first unlocked client tick instead of vanishing.
            jumpRequestRetryTicks = 0;
            return;
        }
        if (jumpRequestRetryTicks > 0)
        {
            jumpRequestRetryTicks--;
            return;
        }

        SeeleNetwork.CHANNEL.sendToServer(new ServerboundEvaControlPacket(
                ServerboundEvaControlPacket.ACTION_JUMP, jumpRequestId));
        jumpRequestRetryTicks = JUMP_REQUEST_RETRY_INTERVAL - 1;
    }

    private static void clearJumpRequest()
    {
        jumpHeld = false;
        jumpRequestPending = false;
        jumpRequestRetryTicks = 0;
        jumpRequestEvaId = -1;
        jumpRequestId = -1;
    }

    private static EvaUnit01Entity findEntryPlugTarget(LocalPlayer player)
    {
        AABB search = player.getBoundingBox().inflate(12.0D, 32.0D, 12.0D);
        return player.level().getEntitiesOfClass(EvaUnit01Entity.class, search,
                        unit -> unit.isAlive() && !unit.isVehicle()
                                && !unit.isLaunchSequenceActive()
                                && unit.isEntryPlugTargeted(player)
                                && hasClearEntryPlugPath(player, unit)).stream()
                .min((left, right) -> Double.compare(
                        left.getEntryPlugSocketPosition().distanceToSqr(player.getEyePosition()),
                        right.getEntryPlugSocketPosition().distanceToSqr(player.getEyePosition())))
                .orElse(null);
    }

    /**
     * Do not consume a normal right-click merely because an EVA socket lies
     * behind a wall. The server repeats this trace before authorizing entry.
     */
    private static boolean hasClearEntryPlugPath(LocalPlayer player, EvaUnit01Entity unit)
    {
        Vec3 eye = player.getEyePosition();
        Vec3 socket = unit.getEntryPlugSocketPosition();
        BlockHitResult hit = player.level().clip(new ClipContext(
                eye, socket, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, player));
        return hit.getType() == HitResult.Type.MISS
                || hit.getLocation().distanceToSqr(socket) <= 0.75D * 0.75D;
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
            if (isCannonScopeActive(eva))
            {
                event.setNewFovModifier(Mth.lerp(eva.chargeProgress(), 1.0F, 0.16F));
            }
            else if (isRifleSightActive(eva))
            {
                event.setNewFovModifier(0.72F);
            }
        }
    }
}
