package com.projectseele.client.visual;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

import com.projectseele.ProjectSeele;
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

/** Camera-only inspection of the explicitly named disposable pyramid preview. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, value = Dist.CLIENT)
public final class PyramidInteriorReview
{
    private static final boolean ENABLED = Boolean.getBoolean("projectseele.pyramidInteriorReview");
    private static final String BATCH = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
    private static final Shot[] SHOTS = {
        new Shot("01_existing_link", new Vec3(28.5,-446.38,267.5), new Vec3(4,-446.38,267.5)),
        new Shot("02_west_gallery", new Vec3(-1,-446.38,274), new Vec3(-1,-446.0,301)),
        new Shot("03_briefing", new Vec3(-24.2,-446.25,296), new Vec3(-14.3,-446.5,281)),
        new Shot("04_duty", new Vec3(-8,-446.25,273), new Vec3(-21,-446.3,267)),
        new Shot("05_west_stair", new Vec3(-12,-446.38,302.5), new Vec3(-8,-453.4,312.5)),
        new Shot("06_service_deck", new Vec3(10.5,-459.38,321.2), new Vec3(34,-457.8,294)),
        new Shot("07_service_axis", new Vec3(28.5,-459.38,321), new Vec3(28.5,-457.5,290)),
        new Shot("08_east_comms", new Vec3(80,-446.35,297), new Vec3(64,-446.8,287)),
        new Shot("09_east_connection", new Vec3(55,-446.38,280), new Vec3(48,-446.38,276))
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

    private PyramidInteriorReview() {}

    @SubscribeEvent
    public static void tick(TickEvent.ClientTickEvent event)
    {
        if (!ENABLED || done || event.phase != TickEvent.Phase.END) return;
        Minecraft mc=Minecraft.getInstance();
        if (mc.player==null || mc.level==null || mc.getSingleplayerServer()==null) return;
        Path world=mc.getSingleplayerServer().getWorldPath(LevelResource.ROOT).normalize();
        if (!world.getFileName().toString().startsWith("SEELE_PYRAMID_TV_PREVIEW"))
        {
            done=true;
            ProjectSeele.LOGGER.error("Pyramid review refused: not the disposable preview save");
            return;
        }
        mc.options.pauseOnLostFocus=false;
        if (++age<80) return;
        if (age>2400)
        {
            done=true;
            ProjectSeele.LOGGER.error("Pyramid review timed out at view {}",view);
            mc.stop();
            return;
        }
        if (!initialized)
        {
            initialized=true;
            mc.player.connection.sendCommand("gamemode spectator");
            ProjectSeele.LOGGER.info("Pyramid interior review started: batch={} world={}",BATCH,world);
        }
        if (view>=SHOTS.length)
        {
            if (finishTicks++==0)
            {
                mc.options.hideGui=false;
                mc.player.connection.sendCommand("execute in projectseele:geofront run tp @s 28.5 -448 267.5 90 0");
                mc.player.connection.sendCommand("gamemode creative");
            }
            if (finishTicks>40)
            {
                done=true;
                ProjectSeele.LOGGER.info("Pyramid interior review complete: batch={} views={}",BATCH,SHOTS.length);
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
                && mc.player.getEyePosition().distanceToSqr(shot.eye)<0.1D && mc.screen==null)
        {
            if (++settle>=35 && renderFrames>=20) capture=true;
        }
    }

    @SubscribeEvent
    public static void render(TickEvent.RenderTickEvent event)
    {
        if (!ENABLED || done || event.phase!=TickEvent.Phase.END || !requested || view>=SHOTS.length) return;
        renderFrames++;
        if (!capture) return;
        Minecraft mc=Minecraft.getInstance();
        Shot shot=SHOTS[view];
        try
        {
            Files.createDirectories(mc.gameDirectory.toPath().resolve("screenshots/projectseele_pyramid_tv/"+BATCH));
            Screenshot.grab(mc.gameDirectory,"projectseele_pyramid_tv/"+BATCH+"/"+shot.name+".png",
                    mc.getMainRenderTarget(),ignored -> {});
            ProjectSeele.LOGGER.info("Pyramid review captured: {} eye={} target={}",shot.name,shot.eye,shot.target);
        }
        catch (Exception exception)
        {
            throw new IllegalStateException("pyramid screenshot",exception);
        }
        capture=false;requested=false;view++;
    }

    private record Shot(String name,Vec3 eye,Vec3 target) {}
}
