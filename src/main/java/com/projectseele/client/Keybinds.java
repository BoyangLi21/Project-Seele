package com.projectseele.client;

import com.mojang.blaze3d.platform.InputConstants;
import net.minecraft.client.KeyMapping;
import org.lwjgl.glfw.GLFW;

/** Pilot keybinds, registered in ClientEvents. */
public final class Keybinds
{
    public static final String CATEGORY = "key.categories.projectseele";

    public static final KeyMapping CYCLE_WEAPON = new KeyMapping(
            "key.projectseele.cycle_weapon", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_R, CATEGORY);
    public static final KeyMapping TOGGLE_AT_FIELD = new KeyMapping(
            "key.projectseele.toggle_at_field", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_G, CATEGORY);
    public static final KeyMapping EXIT_EVA = new KeyMapping(
            "key.projectseele.exit_eva", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_V, CATEGORY);
    public static final KeyMapping STOMP = new KeyMapping(
            "key.projectseele.stomp", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_B, CATEGORY);
    public static final KeyMapping TOGGLE_PRONE = new KeyMapping(
            "key.projectseele.toggle_prone", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_Z, CATEGORY);
    // Pilot-initiated launch abort while silo-locked: recalls the airframe to
    // its wet cage without waiting for a command-room release.
    public static final KeyMapping CANCEL_LAUNCH = new KeyMapping(
            "key.projectseele.cancel_launch", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_C, CATEGORY);
    // Temporary pilot-side release for rapid visual testing. The server still
    // requires the normal occupied LAUNCH_LOCKED state and a linked silo bed.
    public static final KeyMapping SELF_LAUNCH = new KeyMapping(
            "key.projectseele.self_launch", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_X, CATEGORY);

    private Keybinds() {}
}
