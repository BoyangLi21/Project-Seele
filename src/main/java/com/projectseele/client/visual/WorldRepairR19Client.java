package com.projectseele.client.visual;

import com.projectseele.visual.WorldRepairR19Review;
import net.minecraft.client.Minecraft;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.phys.*;
import net.minecraft.core.Direction;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class WorldRepairR19Client
{
    private static int distance=-1,exitTicks;private static boolean reported;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!WorldRepairR19Review.ENABLED||event.phase!=TickEvent.Phase.END)return;
        var mc=Minecraft.getInstance();mc.options.pauseOnLostFocus=false;
        if(WorldRepairR19Review.finished)
        {
            if(distance>=0){mc.options.renderDistance().set(distance);mc.options.broadcastOptions();distance=-1;}
            if("r19-boards-tour".equals(System.getProperty("projectseele.regionalBuild","")))return;
            if(++exitTicks>30)mc.stop();return;
        }
        if(mc.player==null||mc.level==null||mc.screen!=null)return;
        if(distance<0){distance=mc.options.renderDistance().get();mc.options.renderDistance().set(8);mc.options.broadcastOptions();}
        WorldRepairR19Review.clientReady=true;
        if(!reported&&mc.getSingleplayerServer()!=null)
        {
            reported=true;var data=new com.google.gson.JsonObject();var keys=new com.google.gson.JsonObject();
            for(var key:mc.options.keyMappings)if(key.getName().contains("xaero"))keys.addProperty(key.getName(),key.getTranslatedKeyMessage().getString());
            data.add("xaeroKeys",keys);data.addProperty("distantHorizonsLoaded",net.minecraftforge.fml.ModList.get().isLoaded("distanthorizons"));
            data.addProperty("minimapLoaded",net.minecraftforge.fml.ModList.get().isLoaded("xaerominimap"));data.addProperty("worldMapLoaded",net.minecraftforge.fml.ModList.get().isLoaded("xaeroworldmap"));
            try{java.nio.file.Files.writeString(mc.getSingleplayerServer().getWorldPath(net.minecraft.world.level.storage.LevelResource.ROOT).resolve("r19_client_check.json"),data.toString());}catch(java.io.IOException e){throw new IllegalStateException(e);}
        }
        var click=WorldRepairR19Review.click;
        if(click!=null&&mc.gameMode!=null)
        {
            Vec3 point=Vec3.atCenterOf(click).add(0,0,.3);Vec3 delta=point.subtract(mc.player.getEyePosition());
            mc.player.setYRot((float)Math.toDegrees(Math.atan2(-delta.x,delta.z)));mc.player.setXRot((float)-Math.toDegrees(Math.atan2(delta.y,delta.horizontalDistance())));
            mc.gameMode.useItemOn(mc.player,InteractionHand.MAIN_HAND,new BlockHitResult(point,Direction.SOUTH,click,false));
            WorldRepairR19Review.click=null;
        }
    }
}
