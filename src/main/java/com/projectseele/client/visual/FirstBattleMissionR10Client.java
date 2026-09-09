package com.projectseele.client.visual;
import com.projectseele.ProjectSeele;
import com.projectseele.visual.FirstBattleMissionR10Review;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class FirstBattleMissionR10Client
{
    private static int wait,ending;private static boolean oldPause,saved;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!FirstBattleMissionR10Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        if(!saved){saved=true;oldPause=mc.options.pauseOnLostFocus;mc.options.pauseOnLostFocus=false;}
        if(FirstBattleMissionR10Review.click&&++wait==25)
        {
            mc.gameMode.useItemOn(mc.player,InteractionHand.MAIN_HAND,new BlockHitResult(new Vec3(-7.5,-58.5,-17.01),Direction.SOUTH,new BlockPos(-8,-59,-18),false));
        }
        if(FirstBattleMissionR10Review.finished&&++ending>30){mc.options.pauseOnLostFocus=oldPause;mc.stop();}
    }
    private FirstBattleMissionR10Client() {}
}
