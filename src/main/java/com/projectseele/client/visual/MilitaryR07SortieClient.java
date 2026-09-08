package com.projectseele.client.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.visual.MilitaryR07SortieReview;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class MilitaryR07SortieClient
{
    private static int finish,last=-1;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!MilitaryR07SortieReview.ENABLED||event.phase!=TickEvent.Phase.END)return;
        Minecraft mc=Minecraft.getInstance();mc.options.pauseOnLostFocus=false;
        int drive=MilitaryR07SortieReview.drive,phase=MilitaryR07SortieReview.phase;
        mc.options.keyUp.setDown(drive>0);mc.options.keyDown.setDown(drive<0);
        if(mc.player!=null&&mc.player.getVehicle() instanceof com.projectseele.entity.EvaPrototypeEntity)
        {mc.player.setYRot(0);mc.player.setXRot(0);}
        if(mc.player!=null&&phase>=3&&phase!=last)
        {Screenshot.grab(mc.gameDirectory,"r07_sortie_phase_"+phase+".png",mc.getMainRenderTarget(),ignored->{});last=phase;}
        if(MilitaryR07SortieReview.finished&&++finish>40)mc.stop();
    }
}
