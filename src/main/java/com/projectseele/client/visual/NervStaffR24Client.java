package com.projectseele.client.visual;

import com.projectseele.client.screen.StaffConversationScreen;
import com.projectseele.visual.NervStaffR24Review;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Exercise actual UI mouse/key paths and capture the received server state. */
@Mod.EventBusSubscriber(modid = "projectseele", value = Dist.CLIENT)
public final class NervStaffR24Client
{
    private static boolean initialized, oldPause, oldGui;
    private static int oldDistance, end, settled;
    private static String photo = "";
    private static Path folder;
    private static final com.google.gson.JsonArray views = new com.google.gson.JsonArray();

    private static void click(StaffConversationScreen screen, String title)
    {
        for (var child : List.copyOf(screen.children()))
            if (child instanceof Button button && button.getMessage().getString().equals(title))
            {
                if (!button.active) throw new IllegalStateException("Disabled native UI button: " + title);
                double x = button.getX() + button.getWidth() * .5, y = button.getY() + button.getHeight() * .5;
                if (!screen.mouseClicked(x, y, 0)) throw new IllegalStateException("Native UI click was not consumed: " + title);
                screen.mouseReleased(x, y, 0); return;
            }
        throw new IllegalStateException("Missing native UI button: " + title);
    }

    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if (!NervStaffR24Review.ENABLED || event.phase != TickEvent.Phase.END) return;
        var mc = Minecraft.getInstance(); if (mc.player == null || mc.level == null) return;
        if (!initialized)
        {
            initialized = true; oldPause = mc.options.pauseOnLostFocus; oldGui = mc.options.hideGui; oldDistance = mc.options.renderDistance().get();
            mc.options.pauseOnLostFocus = false; mc.options.hideGui = false; mc.options.renderDistance().set(6); mc.options.broadcastOptions();
            folder = mc.gameDirectory.toPath().resolve("../artifacts/"+(NervStaffR24Review.R25?"facility_r25":"facility_r24")+"/native_staff_" + System.currentTimeMillis()).normalize();
            try { Files.createDirectories(folder); } catch (Exception failure) { throw new IllegalStateException(failure); }
            NervStaffR24Review.ready = true;
        }
        if (NervStaffR24Review.finished)
        {
            if (++end > 35)
            {
                mc.setScreen(null); mc.options.pauseOnLostFocus = oldPause; mc.options.hideGui = oldGui;
                mc.options.renderDistance().set(oldDistance); mc.options.broadcastOptions();
                try { Files.writeString(folder.resolve("views.json"), views.toString()); } catch (Exception failure) { throw new IllegalStateException(failure); }
                mc.stop();
            }
            return;
        }
        String request = NervStaffR24Review.input;
        if (request.isEmpty() || NervStaffR24Review.inputs.contains(request)) return;
        if(request.equals("phone"))
        {
            if(!mc.player.getMainHandItem().is(com.projectseele.registry.ModItems.SATELLITE_PHONE.get()))return;
            mc.gameMode.useItem(mc.player,net.minecraft.world.InteractionHand.MAIN_HAND);
            NervStaffR24Review.inputs.add(request);return;
        }
        if (!(mc.screen instanceof StaffConversationScreen screen)) return;
        switch (request)
        {
            case "query" ->
            {
                EditBox field = screen.children().stream().filter(EditBox.class::isInstance).map(EditBox.class::cast).findFirst().orElseThrow();
                screen.mouseClicked(field.getX() + 8, field.getY() + 8, 0);
                for (char c : "能发射初号机吗？".toCharArray()) screen.charTyped(c, 0);
                screen.keyPressed(257, 0, 0);
            }
            case "deploy", "redeploy" -> { click(screen, "指挥"); click(screen, "整备后发射"); }
            case "cancel" -> click(screen, "取消后续操作");
            case "recover" -> { click(screen, "指挥"); click(screen, "回收"); }
            case "contacts" -> click(screen,"通讯录");
            case "pilot_contact" -> click(screen,"碇真嗣");
            case "board_dummy" -> {click(screen,"指挥");click(screen,"驾驶员登机");}
            case "close", "close_radio", "close_pilot" -> screen.keyPressed(256, 0, 0);
            default -> throw new IllegalStateException(request);
        }
        NervStaffR24Review.inputs.add(request);
    }

    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if (!NervStaffR24Review.ENABLED || !initialized || NervStaffR24Review.finished || event.phase != TickEvent.Phase.END) return;
        var mc = Minecraft.getInstance(); String desired = NervStaffR24Review.photo;
        if (desired.isEmpty() || NervStaffR24Review.photos.contains(desired) || !(mc.screen instanceof StaffConversationScreen screen)) return;
        settled = desired.equals(photo) ? settled + 1 : 0; photo = desired;
        if (settled < 55) return;
        try (var image = net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget()))
        {
            image.writeToFile(folder.resolve(desired + ".png"));
            var record = new com.google.gson.JsonObject(); record.addProperty("name", desired);
            record.add("snapshot", new com.google.gson.Gson().toJsonTree(screen.snapshot()));
            record.addProperty("width", screen.width); record.addProperty("height", screen.height);
            record.addProperty("pauses_game", screen.isPauseScreen()); views.add(record);
            NervStaffR24Review.photos.add(desired);
        }
        catch (Exception failure) { throw new IllegalStateException(failure); }
    }
    private NervStaffR24Client() {}
}
