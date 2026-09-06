package com.projectseele.client.visual;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

import com.projectseele.ProjectSeele;
import net.minecraft.core.BlockPos;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.util.Mth;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Camera-only inspection of the explicitly named TV world reconstruction preview. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, value = Dist.CLIENT)
public final class TvWorldVisualReview
{
    private static final boolean ENABLED = "review".equals(System.getProperty("projectseele.tvWorldPreviewReview", ""));
    private static final String BATCH = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
    private static final Shot[] SHOTS = {
        new Shot("01_city_skyline", new Vec3(-170,195,45), new Vec3(30,130,220)),
        new Shot("02_east_coast", new Vec3(305,112,390), new Vec3(535,64,280)),
        new Shot("03_lake_and_hq", new Vec3(-160,-365,445), new Vec3(28,-421,290)),
        new Shot("04_underground_lake", new Vec3(-210,-422,320), new Vec3(-460,-473,405)),
        new Shot("05_flat_ceiling", new Vec3(30,-340,160), new Vec3(30,24,280)),
        new Shot("06_outer_dome", new Vec3(1450,-345,350), new Vec3(1260,-130,296)),
        new Shot("07_hangar", new Vec3(30.5,-410,123.5), new Vec3(30.5,-421,160.5)),
        new Shot("08_retained_tv_interior", new Vec3(-1,-446.38,274), new Vec3(-1,-446,301)),
        new Shot("09_surface_lift", new Vec3(108.5,82,273.5), new Vec3(126,82,273.5))
    };
    private static int age;
    private static int view;
    private static int settle;
    private static int renderFrames;
    private static boolean initialized;
    private static boolean requested;
    private static boolean capture;
    private static boolean done;
    private static int finishTicks;
    private static boolean renderGridReady;

    private TvWorldVisualReview() {}

    @SubscribeEvent
    public static void tick(TickEvent.ClientTickEvent event)
    {
        if (!ENABLED || done || event.phase != TickEvent.Phase.END) return;
        Minecraft mc=Minecraft.getInstance();
        if (mc.player==null || mc.level==null || mc.getSingleplayerServer()==null) return;
        Path world=mc.getSingleplayerServer().getWorldPath(LevelResource.ROOT).normalize();
        if (!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))
        {
            done=true;
            ProjectSeele.LOGGER.error("TV world review refused: not the disposable preview save");
            return;
        }
        mc.options.pauseOnLostFocus=false;
        if (++age<80) return;
        if (age>9000)
        {
            done=true;
            ProjectSeele.LOGGER.error("TV world review timed out at view {}",view);
            mc.stop();
            return;
        }
        if (!initialized)
        {
            initialized=true;
            mc.options.renderDistance().set(18);
            mc.options.broadcastOptions();
            mc.player.connection.sendCommand("gamemode spectator");
            ProjectSeele.LOGGER.info("TV world visual review started: batch={} world={}",BATCH,world);
        }
        if (!renderGridReady && mc.level.dimension().location().toString().equals("projectseele:geofront")
                && mc.options.getEffectiveRenderDistance() >= 18)
        {
            // The server acknowledges the larger radius after the dimension
            // transfer. Rebuild the client grid only after that acknowledgement.
            mc.levelRenderer.allChanged();
            renderGridReady = true;
            settle = 0;
            renderFrames = 0;
            ProjectSeele.LOGGER.info("TV world render grid rebuilt: effective={} stats={}",
                    mc.options.getEffectiveRenderDistance(), mc.levelRenderer.getChunkStatistics());
        }
        if (view>=SHOTS.length)
        {
            if (finishTicks++==0)
            {
                mc.options.hideGui=false;
                mc.player.connection.sendCommand("execute in projectseele:geofront run tp @s 112.5 80 273.5 -90 0");
                mc.player.connection.sendCommand("gamemode creative");
            }
            if (finishTicks>40)
            {
                done=true;
                ProjectSeele.LOGGER.info("TV world visual review complete: batch={} views={}",BATCH,SHOTS.length);
                mc.stop();
            }
            return;
        }
        Shot shot=SHOTS[view];
        if (!requested)
        {
            requested=true; settle=0; renderFrames=0;
            Vec3 d=shot.target.subtract(shot.eye);
            float yaw=(float)(Mth.atan2(d.z,d.x)*Mth.RAD_TO_DEG)-90.0F;
            float pitch=(float)(-Mth.atan2(d.y,d.horizontalDistance())*Mth.RAD_TO_DEG);
            mc.player.connection.sendCommand(String.format(Locale.ROOT,
                    "execute in projectseele:geofront run tp @s %.5f %.5f %.5f %.5f %.5f",
                    shot.eye.x,shot.eye.y-mc.player.getEyeHeight(),shot.eye.z,yaw,pitch));
            mc.options.setCameraType(CameraType.FIRST_PERSON);
            mc.setCameraEntity(mc.player);
            mc.options.hideGui=true;
        }
        if (mc.level.dimension().location().toString().equals("projectseele:geofront")
                && mc.player.getEyePosition().distanceToSqr(shot.eye)<0.1D && mc.screen==null
                && mc.level.hasChunk(Mth.floor(shot.target.x) >> 4, Mth.floor(shot.target.z) >> 4))
        {
            if (renderGridReady && ++settle>=180 && renderFrames>=90) capture=true;
        }
    }

    @SubscribeEvent
    public static void render(TickEvent.RenderTickEvent event)
    {
        if (!ENABLED || done || !requested || view>=SHOTS.length) return;
        Minecraft mc=Minecraft.getInstance();
        Shot shot=SHOTS[view];
        if (mc.player == null) return;
        if (event.phase == TickEvent.Phase.START)
        {
            Vec3 direction=shot.target.subtract(shot.eye);
            float yaw=(float)(Mth.atan2(direction.z,direction.x)*Mth.RAD_TO_DEG)-90.0F;
            float pitch=(float)(-Mth.atan2(direction.y,direction.horizontalDistance())*Mth.RAD_TO_DEG);
            mc.player.setYRot(yaw);
            mc.player.yRotO=yaw;
            mc.player.setXRot(pitch);
            mc.player.xRotO=pitch;
            return;
        }
        renderFrames++;
        if (!capture) return;
        try
        {
            Files.createDirectories(mc.gameDirectory.toPath().resolve("screenshots/projectseele_tv_world/"+BATCH));
            Screenshot.grab(mc.gameDirectory,"projectseele_tv_world/"+BATCH+"/"+shot.name+".png",
                    mc.getMainRenderTarget(),ignored -> {});
            ProjectSeele.LOGGER.info("TV world review captured: {} eye={} target={}",shot.name,shot.eye,shot.target);
            ProjectSeele.LOGGER.info("TV world capture renderer: effective={} stats={}",
                    mc.options.getEffectiveRenderDistance(), mc.levelRenderer.getChunkStatistics());
            var camera=mc.gameRenderer.getMainCamera();
            ProjectSeele.LOGGER.info("TV world actual camera: pos={} yaw={} pitch={} rendered={}",
                    camera.getPosition(),camera.getYRot(),camera.getXRot(),mc.levelRenderer.countRenderedChunks());
            int loaded=0;
            int cx=Mth.floor(shot.eye.x)>>4, cz=Mth.floor(shot.eye.z)>>4;
            for (int z=cz-17;z<=cz+17;z++)
                for(int x=cx-17;x<=cx+17;x++) if(mc.level.hasChunk(x,z)) loaded++;
            BlockPos probe=BlockPos.containing(shot.target.x,shot.eye.y>0?80:-450,shot.target.z);
            ProjectSeele.LOGGER.info("TV world chunk evidence: loaded={}/1225 probe={} state={} chunk={} compiled={}",
                    loaded,probe,mc.level.getBlockState(probe),mc.level.getChunkAt(probe).getClass().getSimpleName(),
                    mc.levelRenderer.isChunkCompiled(probe));
        }
        catch (Exception exception)
        {
            throw new IllegalStateException("TV world screenshot",exception);
        }
        capture=false;requested=false;view++;
    }

    private record Shot(String name,Vec3 eye,Vec3 target) {}
}
