package com.projectseele.client.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.visual.MilitaryR07EquipmentReview;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class MilitaryR07EquipmentClient
{
    private static int finish,ticks;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!MilitaryR07EquipmentReview.ENABLED||event.phase!=TickEvent.Phase.END)return;
        Minecraft mc=Minecraft.getInstance();mc.options.pauseOnLostFocus=false;
        for(var key:mc.options.keyMappings)
        {
            if(key.getName().equals("key.superbwarfare.move_forward"))key.setDown((MilitaryR07EquipmentReview.input&4)!=0);
            if(key.getName().equals("key.superbwarfare.move_space"))key.setDown((MilitaryR07EquipmentReview.input&16)!=0);
        }
        if(++ticks%100==0&&mc.player!=null&&mc.player.getVehicle()!=null)
        {
            var vehicle=mc.player.getVehicle();
            try { ProjectSeele.LOGGER.info("R07 CLIENT DRIVE vehicle={} input={} forward={} power={} position={}",vehicle.getType(),MilitaryR07EquipmentReview.input,vehicle.getClass().getMethod("forwardInputDown").invoke(vehicle),vehicle.getClass().getMethod("getPower").invoke(vehicle),vehicle.position()); }
            catch(ReflectiveOperationException ignored){}
        }
        if(MilitaryR07EquipmentReview.stage==4&&mc.player!=null&&mc.player.getVehicle()!=null)
        {
            var vehicle=mc.player.getVehicle();
            try { vehicle.getClass().getMethod("mouseInput",double.class,double.class).invoke(vehicle,0D,vehicle.getDeltaMovement().horizontalDistance()>.5&&vehicle.getXRot()>-12?-2D:0D); }
            catch(ReflectiveOperationException e){throw new IllegalStateException(e);}
        }
        if(MilitaryR07EquipmentReview.finished&&++finish>40)mc.stop();
    }
}
