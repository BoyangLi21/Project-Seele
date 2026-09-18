package com.projectseele.client.visual;
import com.projectseele.visual.PreparationR22Review;
import net.minecraft.client.Minecraft;
import net.minecraft.core.Direction;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.phys.*;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class PreparationR22Client
{
    private static int age,exit;private static boolean opened,pressed,saved;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent e)
    {
        if(!PreparationR22Review.ENABLED||e.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();mc.options.pauseOnLostFocus=false;
        if(PreparationR22Review.finished){if(++exit>40)mc.stop();return;}
        if(!PreparationR22Review.ready||mc.player==null||mc.level==null)return;
        if(++age<80)return;
        if(!opened){mc.gameMode.useItemOn(mc.player,InteractionHand.MAIN_HAND,new BlockHitResult(Vec3.atCenterOf(PreparationR22Review.PIANO),Direction.NORTH,PreparationR22Review.PIANO,false));opened=true;return;}
        if(mc.screen!=null&&mc.screen.getClass().getName().endsWith("PianoPlayScreen"))
        {
            if(!pressed){mc.screen.keyPressed(org.lwjgl.glfw.GLFW.GLFW_KEY_Z,0,0);pressed=true;age=0;}
            if(pressed&&age>=100){mc.screen.keyReleased(org.lwjgl.glfw.GLFW.GLFW_KEY_Z,0,0);PreparationR22Review.released=true;mc.player.closeContainer();}
        }
    }
    @SubscribeEvent public static void frame(TickEvent.RenderTickEvent e)
    {
        if(!PreparationR22Review.ENABLED||e.phase!=TickEvent.Phase.END||saved||!pressed)return;
        var mc=Minecraft.getInstance();if(mc.screen==null||age<90)return;
        try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget()))
        {var out=Path.of("../artifacts/access_r22/piano_playable.png");Files.createDirectories(out.getParent());image.writeToFile(out);saved=true;}
        catch(Exception x){throw new IllegalStateException(x);}
    }
}
