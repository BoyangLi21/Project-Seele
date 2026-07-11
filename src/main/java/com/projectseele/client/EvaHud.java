package com.projectseele.client;

import com.projectseele.config.SeeleConfig;
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

    /**
     * Entry-plug insertion cinematic: dark clunk, LCL floods bottom-to-top,
     * A six-second activation sequence: mechanical lock, LCL pressure,
     * A10 nerve connection, synchronization, then optical clearing.
     */
    public static final IGuiOverlay INSERTION = (gui, guiGraphics, partialTick, width, height) ->
    {
        float progress = ClientForgeEvents.insertionProgress(partialTick);
        if (progress < 0.0F)
        {
            return;
        }
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

        // --- top-centre: synchro readout (placeholder until Phase 2.3) ---
        float time = (System.currentTimeMillis() % 600000L) / 1000.0F;
        float synchro = 41.3F + 1.8F * Mth.sin(time * 0.13F) + 0.6F * Mth.sin(time * 1.7F);
        guiGraphics.drawCenteredString(gui.getFont(),
                Component.literal(String.format("SYNCHRO  %.1f%%", synchro))
                        .withStyle(ChatFormatting.GOLD),
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
        String weaponKey = switch (eva.getWeapon())
        {
            case EvaUnit01Entity.WEAPON_KNIFE -> "msg.projectseele.weapon_knife";
            case EvaUnit01Entity.WEAPON_CANNON -> "msg.projectseele.weapon_cannon";
            case EvaUnit01Entity.WEAPON_LANCE -> "msg.projectseele.weapon_lance";
            default -> "msg.projectseele.weapon_fists";
        };
        guiGraphics.drawString(gui.getFont(),
                Component.translatable(weaponKey).withStyle(ChatFormatting.YELLOW),
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

    /** Sniper scope: crosshair, charge bar, rangefinder and core-lock call-outs. */
    public static final IGuiOverlay SCOPE = (gui, guiGraphics, partialTick, width, height) ->
    {
        Minecraft minecraft = Minecraft.getInstance();
        LocalPlayer player = minecraft.player;
        if (player == null || !(player.getVehicle() instanceof EvaUnit01Entity eva)
                || eva.getWeapon() != EvaUnit01Entity.WEAPON_CANNON
                || eva.getCannonCharge() <= 0)
        {
            return;
        }
        int cx = width / 2;
        int cy = height / 2;
        float progress = eva.chargeProgress();

        // Scope shading around a central window.
        int frameH = Math.round(height * 0.14F);
        int frameW = Math.round(width * 0.18F);
        int shade = 0xC8000000;
        guiGraphics.fill(0, 0, width, frameH, shade);
        guiGraphics.fill(0, height - frameH, width, height, shade);
        guiGraphics.fill(0, frameH, frameW, height - frameH, shade);
        guiGraphics.fill(width - frameW, frameH, width, height - frameH, shade);

        // Crosshair with a breathing gap.
        int reach = 70;
        int gap = 10 - Math.round(6 * progress);
        guiGraphics.fill(cx - reach, cy, cx - gap, cy + 1, NERV_ORANGE);
        guiGraphics.fill(cx + gap, cy, cx + reach, cy + 1, NERV_ORANGE);
        guiGraphics.fill(cx, cy - reach, cx + 1, cy - gap, NERV_ORANGE);
        guiGraphics.fill(cx, cy + gap, cx + 1, cy + reach, NERV_ORANGE);
        // Corner brackets.
        int b = 110;
        int len = 22;
        guiGraphics.fill(cx - b, cy - b, cx - b + len, cy - b + 2, NERV_ORANGE);
        guiGraphics.fill(cx - b, cy - b, cx - b + 2, cy - b + len, NERV_ORANGE);
        guiGraphics.fill(cx + b - len, cy - b, cx + b, cy - b + 2, NERV_ORANGE);
        guiGraphics.fill(cx + b - 2, cy - b, cx + b, cy - b + len, NERV_ORANGE);
        guiGraphics.fill(cx - b, cy + b - 2, cx - b + len, cy + b, NERV_ORANGE);
        guiGraphics.fill(cx - b, cy + b - len, cx - b + 2, cy + b, NERV_ORANGE);
        guiGraphics.fill(cx + b - len, cy + b - 2, cx + b, cy + b, NERV_ORANGE);
        guiGraphics.fill(cx + b - 2, cy + b - len, cx + b, cy + b, NERV_ORANGE);

        // Charge bar.
        int barW = 180;
        int by = cy + b + 14;
        boolean ready = progress >= 1.0F;
        guiGraphics.fill(cx - barW / 2, by, cx + barW / 2, by + 8, 0xFF202020);
        guiGraphics.fill(cx - barW / 2, by, cx - barW / 2 + Math.round(barW * progress), by + 8,
                ready ? 0xFF35D435 : NERV_ORANGE);
        Component chargeText = ready
                ? Component.translatable("hud.projectseele.charge_ready").withStyle(ChatFormatting.GREEN)
                : Component.translatable("hud.projectseele.charging").withStyle(ChatFormatting.GOLD);
        guiGraphics.drawCenteredString(gui.getFont(), chargeText, cx, by + 12, 0xFFFFFFFF);

        // Rangefinder + target designation.
        scopeReadout(guiGraphics, gui.getFont(), player, eva, cx, cy - b - 24, ready);
    };

    private static void scopeReadout(GuiGraphics guiGraphics, Font font,
                                     LocalPlayer player, EvaUnit01Entity eva, int cx, int y, boolean ready)
    {
        double range = SeeleConfig.CANNON_RANGE.get();
        Vec3 from = player.getEyePosition();
        Vec3 dir = player.getLookAngle();
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
