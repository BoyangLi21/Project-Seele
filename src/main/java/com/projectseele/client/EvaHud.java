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

    /** Full entry-plug cockpit: frame, synchro readout, status, warnings. */
    public static final IGuiOverlay COCKPIT = (gui, guiGraphics, partialTick, width, height) ->
    {
        LocalPlayer player = Minecraft.getInstance().player;
        if (player == null || !(player.getVehicle() instanceof EvaUnit01Entity eva))
        {
            return;
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
                Component.translatable("hud.projectseele.eva_status").withStyle(ChatFormatting.GOLD),
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
        float at = Mth.clamp(eva.getAtFieldEnergy() / EvaUnit01Entity.getAtFieldMax(), 0.0F, 1.0F);
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
            default -> "msg.projectseele.weapon_fists";
        };
        guiGraphics.drawString(gui.getFont(),
                Component.translatable(weaponKey).withStyle(ChatFormatting.YELLOW),
                x + 44, y + 25, 0xFFFFFFFF);
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
            if (ramiel.isCoreHit(entityHit.getLocation()))
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
