package com.projectseele.client.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.visual.VehicleManualR24Review;
import net.minecraft.client.Minecraft;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.InteractionHand;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class VehicleManualR24Client
{
    private static int stage,age,end;private static Path folder;private static Object api;private static Class<?> apiType;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!VehicleManualR24Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();
        if(VehicleManualR24Review.finished){if(++end>30){mc.setScreen(null);mc.stop();}return;}
        if(!VehicleManualR24Review.ready||mc.player==null||mc.gameMode==null)return;
        try
        {
            if(stage==0)
            {
                if(!mc.player.isCreative()||!BuiltInRegistries.ITEM.getKey(mc.player.getMainHandItem().getItem()).toString().equals("patchouli:guide_book"))return;
                folder=mc.gameDirectory.toPath().resolve("../artifacts/facility_r24/manual_native_"+System.currentTimeMillis()).normalize();Files.createDirectories(folder);
                api=Class.forName("vazkii.patchouli.api.PatchouliAPI").getMethod("get").invoke(null);
                apiType=Class.forName("vazkii.patchouli.api.PatchouliAPI$IPatchouliAPI");
                mc.gameMode.useItem(mc.player,InteractionHand.MAIN_HAND);stage=1;age=0;
            }
            if(++age<60)return;
            if(stage==1||stage==2)
            {
                Object open=apiType.getMethod("getOpenBookGui").invoke(api);
                if(!VehicleManualR24Review.BOOK.equals(open)||mc.screen==null||!mc.screen.getClass().getName().contains("GuiBook"))throw new IllegalStateException("Native book GUI did not open");
                try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget())){image.writeToFile(folder.resolve(stage==1?"manual_landing.png":"vehicle_controls.png"));}
                Files.writeString(folder.resolve("stage_"+stage+".json"),new com.google.gson.Gson().toJson(java.util.Map.of("screen",mc.screen.getClass().getName(),"book",String.valueOf(open))));
                if(stage==1){apiType.getMethod("openBookEntry",ResourceLocation.class,ResourceLocation.class,int.class).invoke(api,VehicleManualR24Review.BOOK,new ResourceLocation("superbwarfare","vehicle/control"),0);stage=2;age=0;}
                else{stage=3;mc.setScreen(null);VehicleManualR24Review.clientDone=true;}
            }
        }
        catch(Exception error){VehicleManualR24Review.clientError=error.toString();VehicleManualR24Review.clientDone=true;stage=3;mc.setScreen(null);ProjectSeele.LOGGER.error("R24 native vehicle manual GUI",error);}
    }
    private VehicleManualR24Client(){}
}
