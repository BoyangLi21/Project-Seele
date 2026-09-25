package com.projectseele.client.visual;
import com.projectseele.visual.TransportReturnR39Review;
import net.minecraft.client.Minecraft;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
@Mod.EventBusSubscriber(modid="projectseele",value=net.minecraftforge.api.distmarker.Dist.CLIENT)
public final class TransportReturnR39Client {
 private static int delay;
 @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event){
  if(!TransportReturnR39Review.ENABLED||event.phase!=TickEvent.Phase.END)return;
  var mc=Minecraft.getInstance();mc.options.pauseOnLostFocus=false;
  if(TransportReturnR39Review.done&&++delay>30)mc.stop();
 }
}
