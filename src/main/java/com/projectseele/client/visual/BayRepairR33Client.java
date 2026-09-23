package com.projectseele.client.visual;

import com.projectseele.visual.BayRepairR33Review;
import net.minecraft.client.*;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class BayRepairR33Client
{
    private static Path folder;private static String shot="";private static int closing;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent e)
    {
        if(!BayRepairR33Review.ENABLED||e.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        try
        {
            if(folder==null){folder=Path.of("../artifacts/combat_foundation_r33/repair_"+System.currentTimeMillis());Files.createDirectories(folder);mc.options.pauseOnLostFocus=false;mc.options.hideGui=true;mc.options.setCameraType(CameraType.FIRST_PERSON);mc.options.fov().set(95);BayRepairR33Review.ready=true;}
            if(mc.screen!=null)mc.setScreen(null);
            if(mc.level.getEntity(BayRepairR33Review.actorId) instanceof com.projectseele.entity.EvaUnit01Entity eva)
            {
                var d=eva.position().add(0,BayRepairR33Review.VISUAL_ONLY?46:32,0).subtract(mc.player.getEyePosition());float yaw=(float)Math.toDegrees(Math.atan2(-d.x,d.z));float pitch=(float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance()));
                mc.player.setYRot(yaw);mc.player.yRotO=yaw;mc.player.setXRot(pitch);mc.player.xRotO=pitch;
            }
            if(BayRepairR33Review.done&&++closing>35)mc.stop();
        }
        catch(Exception failure){throw new IllegalStateException(failure);}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent e)
    {
        if(!BayRepairR33Review.ENABLED||folder==null||e.phase!=TickEvent.Phase.END)return;
        if(!BayRepairR33Review.shot.isEmpty()&&!shot.equals(BayRepairR33Review.shot))try
        {
            shot=BayRepairR33Review.shot;var mc=Minecraft.getInstance();try(var capture=Screenshot.takeScreenshot(mc.getMainRenderTarget())){capture.writeToFile(folder.resolve(shot+".png"));}
            var report=new com.google.gson.JsonObject();report.add("draws",new com.google.gson.Gson().toJsonTree(com.projectseele.client.render.EvaBayMachineryR33.REVIEW_DRAWS));report.add("phases",new com.google.gson.Gson().toJsonTree(com.projectseele.client.render.EvaBayMachineryR33.REVIEW_PHASES));
            var platforms=new com.google.gson.JsonArray();for(var entity:mc.level.entitiesForRendering())if(entity instanceof com.projectseele.entity.NervCarrierPlatformEntity g)
            {var row=new com.google.gson.JsonObject();row.addProperty("id",g.getId());row.addProperty("position",g.position().toString());row.addProperty("variant",g.getUnitVariant());row.addProperty("gantry",g.isRestraintGantry());row.addProperty("crane",g.isPlugCrane());row.addProperty("repair",g.repairProgressR33());row.addProperty("bounds",g.getBoundingBox().toString());platforms.add(row);}
            report.add("platforms",platforms);Files.writeString(folder.resolve(shot+"_draws.json"),new com.google.gson.GsonBuilder().setPrettyPrinting().create().toJson(report));
        }
        catch(Exception failure){throw new IllegalStateException(failure);}
    }
    private BayRepairR33Client(){}
}
