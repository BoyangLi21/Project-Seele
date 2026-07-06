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

    private Keybinds() {}
}
