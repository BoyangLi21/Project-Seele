package com.projectseele.client.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import net.minecraft.client.Minecraft;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Camera-only tour of the measured world and the actual installed vehicle models. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class UNWorldR11Tour
{
    public static final boolean ENABLED="r11-worldtour".equals(System.getProperty("projectseele.regionalBuild",""));
    private static JsonArray shots;private static final JsonArray receipt=new JsonArray();private static int age,index,settle,end,oldDistance;private static boolean requested,done,oldPause,oldGui,ready;
    private static Vec3 eye,target;private static Path folder;private static net.minecraft.client.CameraType oldCamera;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null||mc.getSingleplayerServer()==null)return;
        String world=mc.getSingleplayerServer().getWorldPath(LevelResource.ROOT).normalize().getFileName().toString();
        if(!world.equals("SEELE_R11_CANONICAL_ACCEPTANCE")&&!world.equals("SEELE_TV_WORLD_PREVIEW_20260906"))throw new IllegalStateException("R11 tour world boundary");
        if(++age<100)return;
        try
        {
            if(shots==null)
            {
                shots=JsonParser.parseString(Files.readString(mc.gameDirectory.toPath().resolve("projectseele-local-maps/r11_worldtour.json"))).getAsJsonArray();folder=mc.gameDirectory.toPath().resolve("../artifacts/world_motion_r11/world_native_"+System.currentTimeMillis()).normalize();Files.createDirectories(folder);
                oldDistance=mc.options.renderDistance().get();oldPause=mc.options.pauseOnLostFocus;oldGui=mc.options.hideGui;oldCamera=mc.options.getCameraType();mc.options.renderDistance().set(12);mc.options.broadcastOptions();mc.options.pauseOnLostFocus=false;mc.player.connection.sendCommand("gamemode spectator");
            }
            if(done)
            {
                if(++end==1){mc.options.renderDistance().set(oldDistance);mc.options.broadcastOptions();mc.options.hideGui=oldGui;mc.options.pauseOnLostFocus=oldPause;mc.options.setCameraType(oldCamera);mc.setCameraEntity(mc.player);Files.writeString(folder.resolve("receipt.json"),receipt.toString());}
                if(end>30)mc.stop();return;
            }
            if(index>=shots.size()){done=true;return;}
            if(!requested)
            {
                var shot=shots.get(index).getAsJsonObject();eye=vec(shot.getAsJsonArray("eye"));target=vec(shot.getAsJsonArray("target"));Vec3 d=target.subtract(eye);
                mc.player.connection.sendCommand(String.format(Locale.ROOT,"execute in projectseele:geofront run tp @s %.5f %.5f %.5f %.5f %.5f",eye.x,eye.y-mc.player.getEyeHeight(),eye.z,Math.toDegrees(Math.atan2(-d.x,d.z)),-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance()))));
                mc.options.hideGui=true;mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);mc.setCameraEntity(mc.player);requested=true;settle=0;ready=false;
            }
            if(mc.level.dimension().location().toString().equals("projectseele:geofront")&&mc.player.getEyePosition().distanceToSqr(eye)<.2&&mc.screen==null)
            {
                if(settle++==40)mc.levelRenderer.allChanged();
                if(settle>180&&mc.level.hasChunkAt(net.minecraft.core.BlockPos.containing(target)))ready=true;
            }
            if(age>8000)throw new IllegalStateException("UN tour timeout at "+index);
        }
        catch(Exception e){ProjectSeele.LOGGER.error("R11 UN tour failed",e);done=true;}
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!ENABLED||done||!requested||shots==null)return;var mc=Minecraft.getInstance();if(mc.player==null)return;
        if(event.phase==TickEvent.Phase.START)
        {Vec3 d=target.subtract(eye);float yaw=(float)Math.toDegrees(Math.atan2(-d.x,d.z)),pitch=(float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance()));mc.player.setYRot(yaw);mc.player.yRotO=yaw;mc.player.setXRot(pitch);mc.player.xRotO=pitch;return;}
        if(!ready)return;
        try(var image=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget()))
        {
            JsonObject spec=shots.get(index).getAsJsonObject();String name=spec.get("name").getAsString();image.writeToFile(folder.resolve(name+".png"));JsonObject r=spec.deepCopy();r.addProperty("chunks",mc.levelRenderer.getChunkStatistics());receipt.add(r);ProjectSeele.LOGGER.info("R11 UN TOUR captured {}",name);
        }
        catch(Exception e){throw new IllegalStateException(e);}
        requested=false;ready=false;index++;
    }
    private static Vec3 vec(JsonArray a){return new Vec3(a.get(0).getAsDouble(),a.get(1).getAsDouble(),a.get(2).getAsDouble());}
}
