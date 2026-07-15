package com.projectseele.client;

import com.projectseele.config.SeeleConfig;
import com.projectseele.client.fx.ClientFxManager;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.RamielEntity;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.projectile.ProjectileUtil;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.gui.overlay.IGuiOverlay;

/**
 * Cockpit widgets for Unit-01: a status panel while piloting, and the
 * positron-cannon sniper scope while charging a shot. NERV orange, of course.
 */
public final class EvaHud
{
    private static final int NERV_ORANGE = 0xFFFF7A00;
    private static final int AT_CYAN = 0xFF39D8E8;
    private static final int PANEL_BG = 0x90101010;

    private EvaHud() {}

    /** Strategic-blast optical overexposure, registered above the cockpit. */
    public static final IGuiOverlay NUCLEAR_FLASH =
            (gui, graphics, partialTick, width, height) ->
    {
        float opacity = ClientFxManager.nuclearFlashOpacity(partialTick);
        if (opacity <= 0.0F)
        {
            return;
        }
        int alpha = Mth.clamp(Math.round(opacity * 242.0F), 0, 242);
        // The first frames are near-white; the quadratic fade leaves a warm
        // retinal afterimage instead of a hard on/off rectangle.
        int colour = (alpha << 24) | 0x00FFF1CE;
        graphics.fill(0, 0, width, height, colour);
    };

    /**
     * Entry-plug insertion cinematic: dark clunk, LCL floods bottom-to-top,
     * A six-second activation sequence: mechanical lock, LCL pressure,
     * A10 nerve connection, synchronization, then optical clearing.
     */
    public static final IGuiOverlay INSERTION = (gui, guiGraphics, partialTick, width, height) ->
    {
        LocalPlayer player = Minecraft.getInstance().player;
        if (player == null || !(player.getVehicle() instanceof EvaUnit01Entity eva)
                || eva.getActivationTicks() <= 0)
        {
            return;
        }
        float progress = eva.getActivationProgress(partialTick);
        float blackout = progress < 0.12F ? Mth.clamp(progress / 0.08F, 0.0F, 1.0F)
                : Mth.clamp(1.0F - (progress - 0.12F) / 0.22F, 0.0F, 1.0F);
        guiGraphics.fill(0, 0, width, height, ((int) (blackout * 245.0F) << 24));

        float rise = Mth.clamp((progress - 0.12F) / 0.34F, 0.0F, 1.0F);
        float fade = progress > 0.76F ? Mth.clamp(1.0F - (progress - 0.76F) / 0.24F, 0.0F, 1.0F) : 1.0F;
        if (rise > 0.0F)
        {
            int surface = height - Math.round(height * rise);
            int lclAlpha = (int) (190.0F * fade);
            guiGraphics.fill(0, surface, width, height, (lclAlpha << 24) | 0xFF8C1A);
            guiGraphics.fill(0, Math.max(0, surface - 2), width, surface, ((int) (220.0F * fade) << 24) | 0xFFB35C);
            for (int bubble = 0; bubble < 14; bubble++)
            {
                int bx = Math.floorMod(bubble * 97 + (int) (progress * 380.0F), Math.max(1, width));
                int by = height - Math.floorMod(bubble * 53 + (int) (progress * 240.0F), Math.max(1, height));
                if (by >= surface)
                {
                    guiGraphics.fill(bx, by, bx + 2, by + 2, ((int) (135.0F * fade) << 24) | 0xFFE0A0);
                }
            }
        }

        if (progress > 0.42F)
        {
            int scanAlpha = (int) (55.0F * fade);
            for (int y = 0; y < height; y += 5)
            {
                guiGraphics.fill(0, y, width, y + 1, (scanAlpha << 24) | 0xFFB060);
            }
        }

        String stageKey = progress < 0.2F ? "hud.projectseele.plug_lock"
                : progress < 0.48F ? "hud.projectseele.lcl_pressurize"
                : progress < 0.70F ? "hud.projectseele.a10_connect"
                : "hud.projectseele.synch_start";
        guiGraphics.drawCenteredString(gui.getFont(),
                Component.translatable(stageKey).withStyle(ChatFormatting.GOLD, ChatFormatting.BOLD),
                width / 2, height / 2 - 34, NERV_ORANGE);
        int barWidth = Math.min(240, width / 2);
        int bx = width / 2 - barWidth / 2;
        int by = height / 2 - 15;
        guiGraphics.fill(bx, by, bx + barWidth, by + 5, 0xB0202020);
        guiGraphics.fill(bx, by, bx + Math.round(barWidth * progress), by + 5, NERV_ORANGE);
        guiGraphics.drawCenteredString(gui.getFont(), String.format("SYSTEM  %03d%%", Math.round(progress * 100.0F)),
                width / 2, by + 10, 0xFFE8D2B8);
        if (eva.getLaunchPhase() == EvaUnit01Entity.LAUNCH_LOCKED)
        {
            guiGraphics.drawCenteredString(gui.getFont(),
                    Component.translatable("hud.projectseele.launch_standby")
                            .withStyle(ChatFormatting.RED, ChatFormatting.BOLD),
                    width / 2, by + 24, 0xFFFF3030);
        }
    };

    /** Full entry-plug cockpit: frame, synchro readout, status, warnings. */
    public static final IGuiOverlay COCKPIT = (gui, guiGraphics, partialTick, width, height) ->
    {
        LocalPlayer player = Minecraft.getInstance().player;
        if (player == null || !(player.getVehicle() instanceof EvaUnit01Entity eva))
        {
            return;
        }

        float damageFlash = ClientForgeEvents.damageFlash(partialTick);
        if (damageFlash > 0.0F)
        {
            int alpha = Math.round(110.0F * damageFlash);
            guiGraphics.fill(0, 0, width, height, (alpha << 24) | 0xA00000);
        }

        // --- plug ambience: faint LCL-orange edges + corner frame ---
        int lcl = 0x14FF8C1A;
        int edge = Math.round(Math.min(width, height) * 0.045F);
        guiGraphics.fill(0, 0, width, edge, lcl);
        guiGraphics.fill(0, height - edge, width, height, lcl);
        guiGraphics.fill(0, edge, edge, height - edge, lcl);
        guiGraphics.fill(width - edge, edge, width, height - edge, lcl);
        int cLen = 34;
        int m = 6;
        int frame = 0xB0FF7A00;
        guiGraphics.fill(m, m, m + cLen, m + 2, frame);
        guiGraphics.fill(m, m, m + 2, m + cLen, frame);
        guiGraphics.fill(width - m - cLen, m, width - m, m + 2, frame);
        guiGraphics.fill(width - m - 2, m, width - m, m + cLen, frame);
        guiGraphics.fill(m, height - m - 2, m + cLen, height - m, frame);
        guiGraphics.fill(m, height - m - cLen, m + 2, height - m, frame);
        guiGraphics.fill(width - m - cLen, height - m - 2, width - m, height - m, frame);
        guiGraphics.fill(width - m - 2, height - m - cLen, width - m, height - m, frame);

        // --- top-centre: synchronization follows the live airframe ---
        float time = (System.currentTimeMillis() % 600000L) / 1000.0F;
        float synchro = eva.getSynchronizationRatio(partialTick);
        ChatFormatting synchroColour = synchro < 25.0F ? ChatFormatting.RED
                : synchro >= 50.0F ? ChatFormatting.GREEN : ChatFormatting.GOLD;
        guiGraphics.drawCenteredString(gui.getFont(),
                Component.literal(String.format("SYNCHRO  %.1f%%", synchro))
                        .withStyle(synchroColour),
                width / 2, m + 6, NERV_ORANGE);
        String roleKey = switch (eva.getUnitVariant())
        {
            case EvaUnit01Entity.UNIT_00 -> "hud.projectseele.role_prototype";
            case EvaUnit01Entity.UNIT_02 -> "hud.projectseele.role_assault";
            default -> "hud.projectseele.role_test";
        };
        guiGraphics.drawString(gui.getFont(), Component.translatable(roleKey).withStyle(ChatFormatting.DARK_GRAY),
                m + 6, m + 6, 0xFFB8A48D);

        int heading = Math.floorMod(Math.round(player.getYRot()), 360);
        guiGraphics.drawCenteredString(gui.getFont(),
                Component.literal(String.format("HDG %03d   PITCH %+03d", heading, Math.round(-player.getXRot())))
                        .withStyle(ChatFormatting.DARK_GRAY),
                width / 2, m + 18, 0xFFB8A48D);

        if (eva.isLaunchSequenceActive())
        {
            String launchKey = switch (eva.getLaunchPhase())
            {
                case EvaUnit01Entity.LAUNCH_LOCKED -> "hud.projectseele.launch_interlock";
                case EvaUnit01Entity.LAUNCH_ASCENT -> "hud.projectseele.launch_ascent";
                default -> "hud.projectseele.launch_surface_clear";
            };
            guiGraphics.drawCenteredString(gui.getFont(),
                    Component.translatable(launchKey).withStyle(ChatFormatting.RED, ChatFormatting.BOLD),
                    width / 2, m + 30, 0xFFFF3030);
        }

        // Helmet sight and artificial horizon. It stays subtle until the
        // dedicated cannon scope takes over, giving the plug a stable frame
        // of reference while the 24-block body moves underneath it.
        int cx = width / 2;
        int cy = height / 2;
        int horizonY = cy + Mth.clamp(Math.round(player.getXRot() * 1.2F), -42, 42);
        guiGraphics.fill(cx - 34, horizonY, cx - 8, horizonY + 1, 0x80FF7A00);
        guiGraphics.fill(cx + 8, horizonY, cx + 34, horizonY + 1, 0x80FF7A00);
        guiGraphics.fill(cx - 1, cy - 4, cx + 2, cy + 5, 0xA0FF7A00);
        guiGraphics.fill(cx - 4, cy - 1, cx + 5, cy + 2, 0xA0FF7A00);

        // --- hull warning strip ---
        float hullFrac = eva.getHealth() / eva.getMaxHealth();
        if (hullFrac <= 0.34F)
        {
            boolean blink = ((int) (time * 2.5F)) % 2 == 0;
            if (blink)
            {
                guiGraphics.drawCenteredString(gui.getFont(),
                        Component.translatable("hud.projectseele.emergency")
                                .withStyle(ChatFormatting.DARK_RED, ChatFormatting.BOLD),
                        width / 2, m + 18, 0xFFFF2020);
            }
        }

        int x = 10;
        int y = height - 64;
        int barWidth = 130;

        guiGraphics.fill(x - 4, y - 14, x + barWidth + 4, y + 36, PANEL_BG);
        guiGraphics.fill(x - 4, y - 14, x + barWidth + 4, y - 13, NERV_ORANGE);
        guiGraphics.fill(x - 4, y + 35, x + barWidth + 4, y + 36, NERV_ORANGE);

        guiGraphics.drawString(gui.getFont(),
                eva.getDisplayName().copy().withStyle(ChatFormatting.GOLD),
                x, y - 10, NERV_ORANGE);
        guiGraphics.drawString(gui.getFont(),
                String.format("%.0f / %.0f", eva.getHealth(), eva.getMaxHealth()),
                x + barWidth - 52, y - 10, 0xFFDDDDDD);

        // Hull bar.
        float hull = Mth.clamp(eva.getHealth() / eva.getMaxHealth(), 0.0F, 1.0F);
        int hullColor = hull > 0.5F ? 0xFF35D435 : hull > 0.25F ? 0xFFE0C020 : 0xFFD43535;
        guiGraphics.fill(x, y + 2, x + barWidth, y + 10, 0xFF202020);
        guiGraphics.fill(x, y + 2, x + Math.round(barWidth * hull), y + 10, hullColor);

        // A.T. Field bar: cyan when raised, grey when down.
        float at = Mth.clamp(eva.getAtFieldEnergy() / eva.getAtFieldCapacity(), 0.0F, 1.0F);
        boolean atOn = eva.isAtFieldOn();
        guiGraphics.fill(x, y + 14, x + barWidth, y + 22, 0xFF202020);
        guiGraphics.fill(x, y + 14, x + Math.round(barWidth * at), y + 22,
                atOn ? AT_CYAN : 0xFF5A6068);
        guiGraphics.drawString(gui.getFont(),
                Component.translatable("hud.projectseele.at_field")
                        .withStyle(atOn ? ChatFormatting.AQUA : ChatFormatting.DARK_GRAY),
                x, y + 25, 0xFFFFFFFF);

        // Weapon line.
        guiGraphics.drawString(gui.getFont(),
                Component.translatable(eva.getWeaponTranslationKey())
                        .withStyle(ChatFormatting.YELLOW),
                x + 44, y + 25, 0xFFFFFFFF);

        String stanceKey = eva.isShieldBraced() ? "hud.projectseele.stance_shield"
                : eva.isPilotProne() ? "hud.projectseele.stance_prone"
                : eva.isPilotCrouching() ? "hud.projectseele.stance_crouch"
                : eva.isPilotSprinting() ? "hud.projectseele.stance_sprint"
                : "hud.projectseele.stance_walk";
        Component stance = Component.translatable(stanceKey).withStyle(
                eva.isShieldBraced() ? ChatFormatting.AQUA
                        : eva.isPilotSprinting() ? ChatFormatting.GREEN : ChatFormatting.GRAY);
        guiGraphics.drawString(gui.getFont(), stance, width - 10 - gui.getFont().width(stance),
                height - 24, 0xFFFFFFFF);

        if (ClientForgeEvents.pilotTicks() < 240)
        {
            String controlsKey = eva.getUnitVariant() == EvaUnit01Entity.UNIT_00
                    ? "hud.projectseele.controls_unit00" : "hud.projectseele.controls";
            Component controls = Component.translatable(controlsKey)
                    .withStyle(ChatFormatting.GRAY);
            guiGraphics.drawString(gui.getFont(), controls,
                    width - 10 - gui.getFont().width(controls), height - 12, 0xFFFFFFFF);
        }
    };

    /** Entry-plug optical fire control: independent of the enormous world-space cannon. */
    public static final IGuiOverlay SCOPE = (gui, guiGraphics, partialTick, width, height) ->
    {
        Minecraft minecraft = Minecraft.getInstance();
        LocalPlayer player = minecraft.player;
        if (player == null || !(player.getVehicle() instanceof EvaUnit01Entity eva))
        {
            return;
        }
        if (eva.getWeapon() == EvaUnit01Entity.WEAPON_N2
                && (ClientForgeEvents.isWeaponUseHeld() || eva.getN2ArmTicks() > 0))
        {
            renderN2Arming(guiGraphics, gui.getFont(), eva, width, height);
            return;
        }
        if (ClientForgeEvents.isRifleSightActive(eva))
        {
            renderRifleSight(guiGraphics, gui.getFont(), player, eva, width, height);
            return;
        }
        if (!ClientForgeEvents.isCannonScopeActive(eva))
        {
            return;
        }
        int cx = width / 2;
        int cy = height / 2;
        float progress = eva.chargeProgress();
        boolean ready = progress >= 1.0F;
        int lockColour = ready ? 0xFF66FF7A : NERV_ORANGE;

        // Original entry-plug optical feed: cool LCL glass, sparse engineering
        // grid and orange NERV instrumentation. No anime frame is copied.
        guiGraphics.fill(0, 0, width, height, 0x4F020912);
        int gridX = Math.max(48, width / 16);
        int gridY = Math.max(36, height / 12);
        for (int x = cx % gridX; x < width; x += gridX)
        {
            guiGraphics.fill(x, 0, x + 1, height, 0x2439D8E8);
        }
        for (int y = cy % gridY; y < height; y += gridY)
        {
            guiGraphics.fill(0, y, width, y + 1, 0x2439D8E8);
        }
        int edge = Math.max(10, width / 90);
        guiGraphics.fill(0, 0, width, edge, 0xD006090D);
        guiGraphics.fill(0, height - edge, width, height, 0xD006090D);
        guiGraphics.fill(0, edge, edge, height - edge, 0xB006090D);
        guiGraphics.fill(width - edge, edge, width, height - edge, 0xB006090D);

        Component title = Component.translatable("hud.projectseele.yashima_fire_control")
                .withStyle(ChatFormatting.GOLD, ChatFormatting.BOLD);
        guiGraphics.drawString(gui.getFont(), title, edge + 8, edge + 7, 0xFFFFFFFF);
        String power = String.format("GRID LOAD %05.1f%%", progress * 100.0F);
        guiGraphics.drawString(gui.getFont(), power,
                width - edge - 8 - gui.getFont().width(power), edge + 7,
                ready ? 0xFF66FF7A : 0xFFFFB000);

        // Twin acquisition symbols converge on the optical axis as the
        // national-grid charge stabilises. Their overlap is the fire cue.
        int travel = Math.max(42, Math.min(116, width / 9));
        int offset = Math.round((1.0F - progress) * travel);
        int pulse = 2 + Math.round((Mth.sin((player.tickCount + partialTick) * 0.24F) + 1.0F) * 2.0F);
        drawDiamond(guiGraphics, cx - offset, cy, 20 + pulse, lockColour);
        drawDiamond(guiGraphics, cx + offset, cy, 14 + pulse, lockColour);
        drawDiamond(guiGraphics, cx, cy, 5, ready ? 0xFFFFFFFF : AT_CYAN);

        // Cover vanilla's crosshair and replace it with a mechanically clean
        // boresight. The same player look vector is used by the server ray.
        guiGraphics.fill(cx - 4, cy - 4, cx + 5, cy + 5, 0xFF020912);
        int reach = Math.max(42, Math.min(86, width / 12));
        int gap = ready ? 5 : 9;
        guiGraphics.fill(cx - reach, cy, cx - gap, cy + 1, lockColour);
        guiGraphics.fill(cx + gap, cy, cx + reach, cy + 1, lockColour);
        guiGraphics.fill(cx, cy - reach, cx + 1, cy - gap, lockColour);
        guiGraphics.fill(cx, cy + gap, cx + 1, cy + reach, lockColour);

        int bracket = Math.max(84, Math.min(138, Math.min(width, height) / 3));
        drawCornerBrackets(guiGraphics, cx, cy, bracket, 24, lockColour);
        int scanY = cy - bracket + Math.floorMod(player.tickCount * 3, bracket * 2);
        guiGraphics.fill(cx - bracket + 3, scanY, cx + bracket - 3, scanY + 1, 0x5539D8E8);

        int barW = Math.max(180, Math.min(360, width / 3));
        int by = Math.min(height - edge - 34, cy + bracket + 14);
        guiGraphics.fill(cx - barW / 2, by, cx + barW / 2, by + 8, 0xFF202020);
        guiGraphics.fill(cx - barW / 2, by, cx - barW / 2 + Math.round(barW * progress), by + 8,
                ready ? 0xFF35D435 : NERV_ORANGE);
        Component chargeText = ready
                ? Component.translatable("hud.projectseele.charge_ready").withStyle(ChatFormatting.GREEN)
                : Component.translatable("hud.projectseele.charging").withStyle(ChatFormatting.GOLD);
        guiGraphics.drawCenteredString(gui.getFont(), chargeText, cx, by + 12, 0xFFFFFFFF);

        scopeReadout(guiGraphics, gui.getFont(), player, eva, cx,
                Math.max(edge + 24, cy - bracket - 26), ready,
                SeeleConfig.CANNON_RANGE.get());
    };

    private static void renderRifleSight(GuiGraphics graphics, Font font, LocalPlayer player,
                                         EvaUnit01Entity eva, int width, int height)
    {
        int cx = width / 2;
        int cy = height / 2;
        int edge = Math.max(8, width / 120);
        int sight = Math.max(72, Math.min(126, Math.min(width, height) / 3));
        int green = 0xFF75F08A;

        // Original entry-plug optical feed: a compact rifle director rather
        // than a copied series frame. RMB switches to this camera feed while
        // third person continues to see the physical two-hand shoulder pose.
        graphics.fill(0, 0, width, height, 0x3600070B);
        graphics.fill(0, 0, width, edge, 0xE0080B0F);
        graphics.fill(0, height - edge, width, height, 0xE0080B0F);
        graphics.fill(0, edge, edge, height - edge, 0xB0080B0F);
        graphics.fill(width - edge, edge, width, height - edge, 0xB0080B0F);

        Component title = Component.translatable("hud.projectseele.rifle_fire_control")
                .withStyle(ChatFormatting.GOLD, ChatFormatting.BOLD);
        graphics.drawString(font, title, edge + 8, edge + 7, 0xFFFFFFFF);
        Component mode = Component.translatable("hud.projectseele.rifle_auto")
                .withStyle(ChatFormatting.GREEN);
        graphics.drawString(font, mode, width - edge - 8 - font.width(mode), edge + 7, 0xFFFFFFFF);

        drawCornerBrackets(graphics, cx, cy, sight, 20, green);
        drawDiamond(graphics, cx, cy, 9, NERV_ORANGE);
        graphics.fill(cx - sight - 28, cy, cx - 13, cy + 1, 0xB075F08A);
        graphics.fill(cx + 13, cy, cx + sight + 28, cy + 1, 0xB075F08A);
        graphics.fill(cx, cy - sight - 18, cx + 1, cy - 13, 0xB075F08A);
        graphics.fill(cx, cy + 13, cx + 1, cy + sight + 18, 0xB075F08A);

        int scanY = cy - sight + Math.floorMod(player.tickCount * 4, sight * 2);
        graphics.fill(cx - sight + 4, scanY, cx + sight - 4, scanY + 1, 0x4039D8E8);
        scopeReadout(graphics, font, player, eva, cx, cy + sight + 14,
                true, SeeleConfig.EVA_RIFLE_RANGE.get());
    }

    private static void renderN2Arming(GuiGraphics graphics, Font font,
                                       EvaUnit01Entity eva, int width, int height)
    {
        float progress = eva.n2ArmProgress();
        int cx = width / 2;
        int cy = height / 2;
        boolean blink = (eva.tickCount / 4) % 2 == 0;
        graphics.fill(0, 0, width, height, blink ? 0x66A00000 : 0x4A780000);
        graphics.fill(0, 0, width, 6, 0xFFFF2400);
        graphics.fill(0, height - 6, width, height, 0xFFFF2400);
        int radius = Math.max(58, Math.min(128, Math.min(width, height) / 4));
        drawDiamond(graphics, cx, cy, radius, 0xFFFF3A20);
        drawDiamond(graphics, cx, cy, Math.max(18, radius - Math.round(radius * progress)),
                0xFFFFFFFF);
        Component warning = Component.translatable("hud.projectseele.n2_arming")
                .withStyle(ChatFormatting.RED, ChatFormatting.BOLD);
        graphics.drawCenteredString(font, warning, cx, cy - radius - 28, 0xFFFFFFFF);
        float seconds = Math.max(0.0F,
                (SeeleConfig.N2_ARM_TICKS.get() - eva.getN2ArmTicks()) / 20.0F);
        String countdown = String.format("T−%.1f s", seconds);
        graphics.drawCenteredString(font, countdown, cx, cy - 5, 0xFFFFFFFF);
        int barW = Math.max(180, Math.min(420, width / 2));
        graphics.fill(cx - barW / 2, cy + radius + 15, cx + barW / 2, cy + radius + 24, 0xDD180000);
        graphics.fill(cx - barW / 2, cy + radius + 15,
                cx - barW / 2 + Math.round(barW * progress), cy + radius + 24, 0xFFFF2400);
        graphics.drawCenteredString(font,
                Component.translatable("hud.projectseele.n2_abort"), cx, cy + radius + 30,
                0xFFFFD0C8);
    }

    private static void drawCornerBrackets(GuiGraphics graphics, int cx, int cy,
                                           int radius, int length, int colour)
    {
        graphics.fill(cx - radius, cy - radius, cx - radius + length, cy - radius + 2, colour);
        graphics.fill(cx - radius, cy - radius, cx - radius + 2, cy - radius + length, colour);
        graphics.fill(cx + radius - length, cy - radius, cx + radius, cy - radius + 2, colour);
        graphics.fill(cx + radius - 2, cy - radius, cx + radius, cy - radius + length, colour);
        graphics.fill(cx - radius, cy + radius - 2, cx - radius + length, cy + radius, colour);
        graphics.fill(cx - radius, cy + radius - length, cx - radius + 2, cy + radius, colour);
        graphics.fill(cx + radius - length, cy + radius - 2, cx + radius, cy + radius, colour);
        graphics.fill(cx + radius - 2, cy + radius - length, cx + radius, cy + radius, colour);
    }

    private static void drawDiamond(GuiGraphics graphics, int cx, int cy, int radius, int colour)
    {
        drawLine(graphics, cx, cy - radius, cx + radius, cy, colour);
        drawLine(graphics, cx + radius, cy, cx, cy + radius, colour);
        drawLine(graphics, cx, cy + radius, cx - radius, cy, colour);
        drawLine(graphics, cx - radius, cy, cx, cy - radius, colour);
    }

    private static void drawLine(GuiGraphics graphics, int x0, int y0, int x1, int y1, int colour)
    {
        int steps = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0));
        if (steps == 0)
        {
            graphics.fill(x0, y0, x0 + 1, y0 + 1, colour);
            return;
        }
        for (int index = 0; index <= steps; index++)
        {
            int x = Math.round(Mth.lerp(index / (float) steps, x0, x1));
            int y = Math.round(Mth.lerp(index / (float) steps, y0, y1));
            graphics.fill(x, y, x + 1, y + 1, colour);
        }
    }

    private static void scopeReadout(GuiGraphics guiGraphics, Font font,
                                     LocalPlayer player, EvaUnit01Entity eva, int cx, int y,
                                     boolean ready, double range)
    {
        Vec3 from = player.getEyePosition();
        // Use the same clamped pilot rotation sampled by the server at trigger
        // release. The synchronized skeleton pitch can trail local mouse input
        // by one network frame and must not move the optical rangefinder left.
        Vec3 dir = Vec3.directionFromRotation(
                Mth.clamp(player.getXRot(), -EvaUnit01Entity.MAX_CANNON_AIM_PITCH,
                        EvaUnit01Entity.MAX_CANNON_AIM_PITCH),
                player.getYRot());
        Vec3 farEnd = from.add(dir.scale(range));
        BlockHitResult blockHit = player.level().clip(
                new ClipContext(from, farEnd, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, player));
        Vec3 end = blockHit.getLocation();
        EntityHitResult entityHit = ProjectileUtil.getEntityHitResult(player.level(), player, from, end,
                new AABB(from, end).inflate(1.0D),
                e -> e instanceof LivingEntity && e != player && e != eva
                        && !e.isSpectator() && e.isAlive());

        double distance = (entityHit != null ? entityHit.getLocation() : end).distanceTo(from);
        String distText = blockHit.getType() == HitResult.Type.MISS && entityHit == null
                ? "----"
                : String.format("%.0f m", distance);
        guiGraphics.drawCenteredString(font, "DIST " + distText, cx, y, 0xFFCCCCCC);

        if (entityHit != null && entityHit.getEntity() instanceof RamielEntity ramiel)
        {
            Component callout;
            if (ramiel.isCoreShot(from, dir))
            {
                boolean blink = (player.tickCount / 4) % 2 == 0;
                callout = Component.translatable("hud.projectseele.core_lock")
                        .withStyle(blink && ready ? ChatFormatting.GREEN : ChatFormatting.RED,
                                ChatFormatting.BOLD);
            }
            else if (ramiel.isExposed())
            {
                callout = Component.translatable("hud.projectseele.core_exposed")
                        .withStyle(ChatFormatting.YELLOW);
            }
            else
            {
                callout = Component.translatable("hud.projectseele.at_field")
                        .withStyle(ChatFormatting.GOLD);
            }
            guiGraphics.drawCenteredString(font, callout, cx, y + 12, 0xFFFFFFFF);
        }
    }
}
