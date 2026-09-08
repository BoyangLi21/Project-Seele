package com.projectseele.client.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.world.FacilitySchemaV2;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Explicit screenshot review cameras; restores the player's position, abilities and options. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class RegionalStationPhoto
{
    private static final String MODE=System.getProperty("projectseele.regionalBuild","");
    private static final boolean R07=MODE.equals("r07-photos"),DETAIL=R07||MODE.equals("detail-photos");
    private static final boolean ENABLED=MODE.equals("station-photo")||MODE.equals("quality-photos")||DETAIL;
    private record View(String file,Vec3 position,float yaw,float pitch,String action,int warmup)
    {View(String file,Vec3 position,float yaw,float pitch){this(file,position,yaw,pitch,"",220);}}
    private static volatile boolean actionReady=true;
    private static View[] VIEWS=MODE.equals("quality-photos")?new View[]{
            new View("quality_kirisato_exterior.png",new Vec3(-2918.5,97,-1150.5),-60,8),
            new View("quality_kirisato_402.png",new Vec3(-2846.5,86,-1106.5),25,12),
            new View("quality_airport_current.png",new Vec3(737.5,84,1021.5),0,3),
            new View("quality_station_current.png",new Vec3(-699.5,104.38,171.5),0,12.7F)
    }:new View[]{new View("quality_station_current.png",new Vec3(-699.5,104.38,171.5),0,12.7F)};
    private static boolean entered,ready,captured,finishing,endpointCheckRequested;
    private static int age,frames,finishTicks,oldDistance,view,sceneAge;
    private static boolean oldGui,oldPause,oldFlying;
    private static Vec3 oldPos;
    private static float oldYaw,oldPitch;
    private static GameType oldMode;
    private static ResourceKey<Level> oldDimension;
    private static net.minecraft.client.CameraType oldCamera;

    @SubscribeEvent
    public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!ENABLED||event.phase!=TickEvent.Phase.END)return;
        Minecraft mc=Minecraft.getInstance();if(mc.player==null||mc.getSingleplayerServer()==null)return;
        var server=mc.getSingleplayerServer();Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))return;
        try
        {
            if(finishing){if(++finishTicks>40)mc.stop();return;}
            if(++age<80)return;
            if(!entered)
            {
                if(DETAIL)
                {
                    var data=com.google.gson.JsonParser.parseString(Files.readString(world.resolve(R07?"r07_photo_views.json":"regional_photo_views.json"))).getAsJsonArray();
                    java.util.List<View> views=new java.util.ArrayList<>();
                    for(var item:data)
                    {
                        var d=item.getAsJsonObject();var p=d.getAsJsonArray("position");String file=d.get("file").getAsString();
                        if(!file.matches("[A-Za-z0-9_-]+\\.png"))throw new IllegalArgumentException("Invalid photo filename");
                        views.add(new View(file,new Vec3(p.get(0).getAsDouble(),p.get(1).getAsDouble(),p.get(2).getAsDouble()),d.get("yaw").getAsFloat(),d.get("pitch").getAsFloat(),d.has("action")?d.get("action").getAsString():"",d.has("warmupTicks")?d.get("warmupTicks").getAsInt():220));
                    }
                    if(views.isEmpty())throw new IllegalArgumentException("Empty photo itinerary");
                    VIEWS=views.toArray(View[]::new);
                }
                entered=true;oldDistance=mc.options.renderDistance().get();oldGui=mc.options.hideGui;oldPause=mc.options.pauseOnLostFocus;oldCamera=mc.options.getCameraType();
                mc.options.pauseOnLostFocus=false;mc.options.renderDistance().set(R07?18:DETAIL?10:8);mc.options.hideGui=true;mc.options.setCameraType(net.minecraft.client.CameraType.FIRST_PERSON);mc.options.broadcastOptions();
                actionReady=VIEWS[view].action().isEmpty();
                server.execute(()->{
                    var p=server.getPlayerList().getPlayers().get(0);oldPos=p.position();oldDimension=p.level().dimension();oldMode=p.gameMode.getGameModeForPlayer();oldYaw=p.getYRot();oldPitch=p.getXRot();oldFlying=p.getAbilities().flying;
                    p.setGameMode(GameType.SPECTATOR);position(mc);
                });
            }
            if(!actionReady)
            {
                sceneAge=0;frames=0;
                if(age%20==0)server.execute(()->{
                    var level=server.getLevel(FacilitySchemaV2.DIMENSION);var state=com.projectseele.world.MilitaryR07Director.state(level);
                    String action=VIEWS[view].action();
                    if(action.equals("open"))
                    {
                        if(state.phase==com.projectseele.world.MilitaryR07Director.Phase.WET)com.projectseele.world.MilitaryR07Director.request(level,"drain",null);
                        if(state.phase==com.projectseele.world.MilitaryR07Director.Phase.DRY)com.projectseele.world.MilitaryR07Director.request(level,"door",null);
                        actionReady=state.phase==com.projectseele.world.MilitaryR07Director.Phase.OPEN;
                    }
                    else if(action.equals("wet"))
                    {
                        if(state.phase==com.projectseele.world.MilitaryR07Director.Phase.OPEN)com.projectseele.world.MilitaryR07Director.request(level,"door",null);
                        if(state.phase==com.projectseele.world.MilitaryR07Director.Phase.DRY)com.projectseele.world.MilitaryR07Director.request(level,"fill",null);
                        actionReady=state.phase==com.projectseele.world.MilitaryR07Director.Phase.WET;
                    }
                    else throw new IllegalStateException("Unknown R07 photo action "+action);
                });
                if(age>20000)throw new IllegalStateException("R07 photo machinery did not settle");return;
            }
            sceneAge++;
            if(sceneAge==120)mc.levelRenderer.allChanged();
            if(MODE.equals("quality-photos")&&sceneAge==120&&!endpointCheckRequested)
            {
                endpointCheckRequested=true;
                server.execute(()->{
                    try
                    {
                        var proof=com.projectseele.visual.RegionalNativeTransitInspection.checkRouteEndpoints();
                        Files.writeString(world.resolve("native_endpoint_checks.json"),proof.toString());
                        ProjectSeele.LOGGER.info("NATIVE ROUTE ENDPOINT CHECKS PASS {}",proof);
                    }
                    catch(Exception failure)
                    {
                        ProjectSeele.LOGGER.error("NATIVE ROUTE ENDPOINT CHECKS FAILED",failure);
                        try{Files.writeString(world.resolve("native_endpoint_failure.txt"),failure.toString());}catch(Exception ignored){}
                    }
                });
            }
            if(sceneAge>VIEWS[view].warmup()&&frames>100&&!ready)
            {
                ready=true;Files.writeString(world.resolve("station_photo_ready.json"),"{\"ready\":true,\"renderedSections\":"+mc.levelRenderer.countRenderedChunks()+"}");
                ProjectSeele.LOGGER.info("REGIONAL PHOTO READY file={} sections={} camera={}",VIEWS[view].file(),mc.levelRenderer.countRenderedChunks(),mc.gameRenderer.getMainCamera().getPosition());
                ProjectSeele.LOGGER.info("REGIONAL PHOTO GEOMETRY {}",mc.levelRenderer.getChunkStatistics());
            }
            if(captured&&sceneAge>Math.max(280,VIEWS[view].warmup()+60)&&view+1<VIEWS.length)
            {
                view++;sceneAge=0;frames=0;ready=false;captured=false;actionReady=VIEWS[view].action().isEmpty();server.execute(()->position(mc));
            }
            if(Files.exists(world.resolve("regional_stop_requested"))||age>Math.max(2400,(VIEWS.length+3)*(R07?600:360))||(!MODE.equals("station-photo")&&captured&&view+1==VIEWS.length&&sceneAge>280))
            {
                Files.deleteIfExists(world.resolve("regional_stop_requested"));finishing=true;
                mc.options.hideGui=oldGui;mc.options.renderDistance().set(oldDistance);mc.options.pauseOnLostFocus=oldPause;mc.options.setCameraType(oldCamera);
                server.execute(()->{var p=server.getPlayerList().getPlayers().get(0);p.teleportTo(server.getLevel(oldDimension),oldPos.x,oldPos.y,oldPos.z,oldYaw,oldPitch);p.setGameMode(oldMode);p.fallDistance=0;p.setDeltaMovement(Vec3.ZERO);p.getAbilities().flying=oldFlying;p.onUpdateAbilities();});
            }
        }
        catch(Exception e){ProjectSeele.LOGGER.error("STATION PHOTO",e);mc.stop();}
    }
    @SubscribeEvent
    public static void render(TickEvent.RenderTickEvent event)
    {
        if(!ENABLED||!entered||finishing)return;Minecraft mc=Minecraft.getInstance();if(mc.player==null)return;
        View camera=VIEWS[view];
        if(event.phase==TickEvent.Phase.START){mc.player.setYRot(camera.yaw());mc.player.yRotO=camera.yaw();mc.player.setXRot(camera.pitch());mc.player.xRotO=camera.pitch();return;}
        frames++;
        if(ready&&!captured)
        {
            Screenshot.grab(mc.gameDirectory,camera.file(),mc.getMainRenderTarget(),ignored->{});captured=true;
        }
    }
    private static void position(Minecraft mc)
    {
        var server=mc.getSingleplayerServer();var p=server.getPlayerList().getPlayers().get(0);View camera=VIEWS[view];
        var level=server.getLevel(FacilitySchemaV2.DIMENSION);
        Vec3 eye=camera.position().add(0,1.62,0);var cell=net.minecraft.core.BlockPos.containing(eye);
        var state=level.getBlockState(cell);
        if(DETAIL&&state.getCollisionShape(level,cell).toAabbs().stream().anyMatch(b->b.move(cell).contains(eye)))
            throw new IllegalStateException("Review camera intersects a solid block: "+camera.file()+" "+cell+" "+state);
        p.teleportTo(level,camera.position().x,camera.position().y,camera.position().z,camera.yaw(),camera.pitch());
    }
}
