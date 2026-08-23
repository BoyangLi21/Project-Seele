package com.projectseele.client;

import com.mojang.blaze3d.platform.NativeImage;
import com.projectseele.ProjectSeele;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.resources.ResourceLocation;

/** Loads the user-supplied 64x64 Commander Ikari skin for the local player. */
public final class GendoPlayerSkinClient
{
    private static final Path SOURCE = Paths.get(
            "projectseele-local-maps", "gendo_player.png");
    private static final ResourceLocation TEXTURE = new ResourceLocation(
            ProjectSeele.MODID, "dynamic/gendo_player_skin");
    private static boolean checked;
    private static boolean available;

    private GendoPlayerSkinClient()
    {
    }

    public static ResourceLocation textureFor(AbstractClientPlayer player)
    {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.player != player || !ensureLoaded(minecraft))
        {
            return null;
        }
        return TEXTURE;
    }

    private static boolean ensureLoaded(Minecraft minecraft)
    {
        if (checked)
        {
            return available;
        }
        checked = true;
        if (!Files.isRegularFile(SOURCE))
        {
            ProjectSeele.LOGGER.info(
                    "Commander player skin idle: no image at {}", SOURCE);
            return false;
        }
        try (InputStream stream = Files.newInputStream(SOURCE))
        {
            NativeImage image = NativeImage.read(stream);
            if (image.getWidth() != 64 || image.getHeight() != 64)
            {
                image.close();
                ProjectSeele.LOGGER.warn(
                        "Commander player skin must be 64x64: {}", SOURCE);
                return false;
            }
            minecraft.getTextureManager().register(TEXTURE,
                    new DynamicTexture(image));
            available = true;
            return true;
        }
        catch (IOException | RuntimeException exception)
        {
            ProjectSeele.LOGGER.warn(
                    "Commander player skin failed to load from {}", SOURCE,
                    exception);
            return false;
        }
    }
}
