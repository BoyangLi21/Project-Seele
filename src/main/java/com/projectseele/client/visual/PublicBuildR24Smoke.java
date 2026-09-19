package com.projectseele.client.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.List;

/** Public-only startup/resource smoke; it deliberately does not open a private save. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class PublicBuildR24Smoke
{
    private static final boolean ENABLED="r24-public-smoke".equals(System.getProperty("projectseele.regionalBuild",""));
    private static int age;private static boolean done;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END)return;
        var mc=Minecraft.getInstance();if(mc.getOverlay()!=null||mc.screen==null||++age<60)return;
        var report=new JsonObject();var checked=new JsonArray();String error="";
        try
        {
            if(Files.isDirectory(mc.gameDirectory.toPath().resolve("resourcepacks/eva_real_model")))throw new IllegalStateException("Private resource pack present in public smoke");
            if(mc.level!=null)throw new IllegalStateException("Public startup smoke must not open a world");
            for(String required:List.of("movingelevators","geckolib","mtr"))
                if(!net.minecraftforge.fml.ModList.get().isLoaded(required))throw new IllegalStateException("Missing public dependency "+required);
            for(String path:List.of("mesh/period_details_r24.json","textures/entity/chest/nerv_equipment_r24.png",
                    "textures/block/period_station_concrete_r24.png","blockstates/period_fixture.json",
                    "sounds/shamshel_whip_charge.ogg","sounds/staff_radio_connect.ogg"))
            {
                try(var input=mc.getResourceManager().open(new ResourceLocation(ProjectSeele.MODID,path)))
                {if(input.read()==-1)throw new IllegalStateException("Empty resource "+path);checked.add(path);}
            }
            report.addProperty("minecraft_menu",mc.screen.getClass().getSimpleName());
            report.addProperty("opengl_renderer",org.lwjgl.opengl.GL11.glGetString(org.lwjgl.opengl.GL11.GL_RENDERER));
            report.addProperty("moving_elevators_loaded",net.minecraftforge.fml.ModList.get().isLoaded("movingelevators"));
            report.addProperty("geckolib_loaded",net.minecraftforge.fml.ModList.get().isLoaded("geckolib"));
            report.addProperty("mtr_loaded",net.minecraftforge.fml.ModList.get().isLoaded("mtr"));
            report.addProperty("private_pack_absent",true);report.addProperty("no_world_opened",true);
            try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget()))
            {
                Path p=mc.gameDirectory.toPath().resolve("../artifacts/public_smoke_r24.png").normalize();Files.createDirectories(p.getParent());image.writeToFile(p);
            }
        }
        catch(Exception failure){error=failure.toString();ProjectSeele.LOGGER.error("Public source startup smoke",failure);}
        report.addProperty("passed",error.isEmpty());report.addProperty("error",error);report.add("checked_resources",checked);
        report.addProperty("scope","Actual public-only client startup and resource loading; not a private-world or full gameplay test");
        try{Path p=mc.gameDirectory.toPath().resolve("../artifacts/public_smoke_r24.json").normalize();Files.createDirectories(p.getParent());Files.writeString(p,new GsonBuilder().setPrettyPrinting().create().toJson(report));}
        catch(Exception failure){ProjectSeele.LOGGER.error("Public smoke report",failure);}
        done=true;mc.stop();
    }
    private PublicBuildR24Smoke(){}
}
