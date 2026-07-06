package com.projectseele.client;

import com.projectseele.config.SeeleConfig;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.RamielEntity;
import com.projectseele.item.PositronCannonItem;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
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
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.gui.overlay.IGuiOverlay;

/**
 * Cockpit widgets for Unit-01: a status panel while piloting, and the
 * positron-cannon sniper scope while charging a shot. NERV orange, of course.
 */
public final class EvaHud
{
    private static final int NERV_ORANGE = 0xFFFF7A00;
    private static final int PANEL_BG = 0x90101010;

    private EvaHud() {}

    /** Machine status, bottom-left, whenever the player sits in the plug. */
    public static final IGuiOverlay COCKPIT = (gui, guiGraphics, partialTick, width, height) ->
    {
        LocalPlayer player = Minecraft.getInstance().player;
        if (player == null || !(player.getVehicle() instanceof EvaUnit01Entity eva))
        {
            return;
        }
        int x = 10;
        int y = height - 46;
        int barWidth = 130;

        guiGraphics.fill(x - 4, y - 14, x + barWidth + 4, y + 18, PANEL_BG);
        guiGraphics.fill(x - 4, y - 14, x + barWidth + 4, y - 13, NERV_ORANGE);
        guiGraphics.fill(x - 4, y + 17, x + barWidth + 4, y + 18, NERV_ORANGE);

        guiGraphics.drawString(gui.getFont(),
                Component.translatable("hud.projectseele.eva_status").withStyle(ChatFormatting.GOLD),
                x, y - 10, NERV_ORANGE);

        float fraction = Mth.clamp(eva.getHealth() / eva.getMaxHealth(), 0.0F, 1.0F);
        int fill = Math.round(barWidth * fraction);
        int color = fraction > 0.5F ? 0xFF35D435 : fraction > 0.25F ? 0xFFE0C020 : 0xFFD43535;
        guiGraphics.fill(x, y + 2, x + barWidth, y + 10, 0xFF202020);
        guiGraphics.fill(x, y + 2, x + fill, y + 10, color);
        guiGraphics.drawString(gui.getFont(),
                String.format("%.0f / %.0f", eva.getHealth(), eva.getMaxHealth()),
                x + barWidth - 52, y - 10, 0xFFDDDDDD);
    };

    /** Sniper scope: crosshair, charge bar, rangefinder and core-lock call-outs. */
    public static final IGuiOverlay SCOPE = (gui, guiGraphics, partialTick, width, height) ->
    {
        Minecraft minecraft = Minecraft.getInstance();
        LocalPlayer player = minecraft.player;
        if (player == null || !player.isUsingItem()
                || !(player.getUseItem().getItem() instanceof PositronCannonItem)
                || !(player.getVehicle() instanceof EvaUnit01Entity))
        {
            return;
        }
        int cx = width / 2;
        int cy = height / 2;
        float progress = PositronCannonItem.chargeProgress(player);

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
        scopeReadout(guiGraphics, gui.getFont(), player, cx, cy - b - 24, ready);
    };

    private static void scopeReadout(GuiGraphics guiGraphics, net.minecraft.client.gui.Font font,
                                     LocalPlayer player, int cx, int y, boolean ready)
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
                e -> e instanceof LivingEntity && e != player && e != player.getVehicle()
                        && !e.isSpectator() && e.isAlive());

        double distance = (entityHit != null ? entityHit.getLocation() : end).distanceTo(from);
        String distText = blockHit.getType() == net.minecraft.world.phys.HitResult.Type.MISS && entityHit == null
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
