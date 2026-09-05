package com.projectseele.client.visual;

import java.io.BufferedWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.projectseele.ProjectSeele;
import com.projectseele.client.render.EvaPoseGraph;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.network.ServerboundEvaControlPacket;
import com.projectseele.world.EvaPilotResolver;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import software.bernie.geckolib.cache.object.BakedGeoModel;

/** Explicit userdev replay through normal pilot packets, in a disposable save only. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, value = Dist.CLIENT)
public final class EvaConnectedActionReview
{
    private static final boolean ENABLED = Boolean.getBoolean("projectseele.connectedActionReview");
    private static final String BATCH = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
    private static int wait;
    private static int tick;
    private static int frame;
    private static int capturedTick = -1;
    private static int poseTick = -1;
    private static int entityId = -1;
    private static int serverStart = -1;
    private static int previousTick = -1;
    private static int warmupFrames;
    private static boolean finished;
    private static Entity camera;
    private static BufferedWriter poses;

    private EvaConnectedActionReview() {}

    @SubscribeEvent
    public static void tick(TickEvent.ClientTickEvent event)
    {
        Minecraft mc = Minecraft.getInstance();
        if (!ENABLED || finished || event.phase != TickEvent.Phase.END
                || mc.player == null || mc.level == null || mc.getSingleplayerServer() == null) return;
        Path world = mc.getSingleplayerServer().getWorldPath(LevelResource.ROOT).normalize();
        if (!world.getFileName().toString().startsWith("SEELE_EVA_CONNECTED_REVIEW"))
        {
            finished = true;
            ProjectSeele.LOGGER.error("Connected action review requires a disposable SEELE_EVA_CONNECTED_REVIEW save");
            return;
        }
        mc.options.pauseOnLostFocus = false;
        if (++wait < 100) return;
        if (wait == 100)
        {
            mc.player.connection.sendCommand("seele motionlab reset");
            mc.player.connection.sendCommand("seele motionlab demo unit01 stop");
            mc.player.connection.sendCommand("seele motionlab weapon unit01 fists");
            mc.player.connection.sendCommand("seele motionlab enter unit01");
            return;
        }
        EvaUnit01Entity eva = EvaPilotResolver.controlTarget(mc.player);
        if (eva == null || eva.getActivationTicks() > 0 || !eva.isPoweredOn())
        {
            if (wait > 700) finish(mc, "pilot_setup_timeout");
            return;
        }
        entityId = eva.getId();
        if (serverStart < 0)
        {
            positionCamera(mc, eva);
            if (warmupFrames < 10) return;
            serverStart = mc.getSingleplayerServer().getTickCount();
        }
        tick = mc.getSingleplayerServer().getTickCount() - serverStart;
        if (poses == null)
        {
            ProjectSeele.LOGGER.info("Connected action review started: batch={} entity={} world={}", BATCH, entityId, world);
            try
            {
                Path dir = mc.gameDirectory.toPath().resolve("screenshots/projectseele_connected/" + BATCH);
                Files.createDirectories(dir);
                poses = Files.newBufferedWriter(dir.resolve("poses.jsonl"), StandardCharsets.UTF_8);
            }
            catch (Exception exception)
            {
                throw new IllegalStateException("Unable to create action review", exception);
            }
        }
        boolean moving = tick >= 30 && tick < 110 || tick >= 200 && tick < 225
                || tick >= 270 && tick < 362
                || tick >= 590 && tick < 650;
        boolean running = tick >= 65 && tick < 110;
        boolean backward = tick >= 590;
        mc.options.keyUp.setDown(moving && !backward);
        mc.options.keyDown.setDown(moving && backward);
        mc.options.keySprint.setDown(running);
        mc.player.input.up = moving && !backward;
        mc.player.input.down = moving && backward;
        mc.player.input.forwardImpulse = moving ? backward ? -1.0F : 1.0F : 0.0F;
        mc.player.zza = mc.player.input.forwardImpulse;
        mc.player.xxa = 0.0F;
        mc.player.setYRot(0.0F);
        mc.player.setXRot(0.0F);
        if (at(65)) send(ServerboundEvaControlPacket.ACTION_SPRINT_START);
        if (at(110)) send(ServerboundEvaControlPacket.ACTION_SPRINT_STOP);
        if (at(160))
        {
            send(ServerboundEvaControlPacket.ACTION_SPRINT_STOP);
            send(ServerboundEvaControlPacket.ACTION_CROUCH_START);
        }
        if (at(245) || at(575)) send(ServerboundEvaControlPacket.ACTION_CROUCH_STOP);
        if (tick >= 270 && tick < 323 && tick / 4 != previousTick / 4) send(ServerboundEvaControlPacket.ACTION_MELEE);
        if (at(318)) send(ServerboundEvaControlPacket.ACTION_STOMP);
        if (at(365)) mc.player.connection.sendCommand("seele motionlab weapon unit01 knife");
        if (at(380) || at(465) || at(550)) send(ServerboundEvaControlPacket.ACTION_MELEE);
        if (at(400)) send(ServerboundEvaControlPacket.ACTION_SMASH);
        if (at(558)) send(ServerboundEvaControlPacket.ACTION_CROUCH_START);
        positionCamera(mc, eva);
        previousTick = tick;
        if (tick >= 690) finish(mc, "complete");
    }

    private static boolean at(int requested)
    {
        return previousTick < requested && tick >= requested;
    }

    private static void send(int action)
    {
        SeeleNetwork.CHANNEL.sendToServer(new ServerboundEvaControlPacket(action));
    }

    private static void positionCamera(Minecraft mc, EvaUnit01Entity eva)
    {
        if (camera == null)
        {
            camera = EntityType.ARMOR_STAND.create(mc.level);
            if (camera == null) throw new IllegalStateException("review camera");
            camera.setInvisible(true);
            camera.setNoGravity(true);
        }
        Vec3 target = eva.position().add(0, 28, 0);
        Vec3 position = eva.position().add(60, 32, 48);
        Vec3 delta = target.subtract(position);
        camera.setPos(position.x, position.y - camera.getEyeHeight(), position.z);
        camera.setYRot((float)(Mth.atan2(delta.z, delta.x) * Mth.RAD_TO_DEG) - 90.0F);
        camera.setXRot((float)(-Mth.atan2(delta.y, delta.horizontalDistance()) * Mth.RAD_TO_DEG));
        camera.setYHeadRot(camera.getYRot());
        if (camera instanceof LivingEntity living) living.yHeadRotO = living.yHeadRot;
        camera.xo = camera.getX(); camera.yo = camera.getY(); camera.zo = camera.getZ();
        camera.xOld = camera.getX(); camera.yOld = camera.getY(); camera.zOld = camera.getZ();
        camera.yRotO = camera.getYRot(); camera.xRotO = camera.getXRot();
        mc.options.hideGui = true;
        mc.options.setCameraType(CameraType.FIRST_PERSON);
        mc.setCameraEntity(camera);
    }

    public static void recordPose(EvaUnit01Entity eva, BakedGeoModel model, float partialTick)
    {
        if (!ENABLED || finished || eva.getId() != entityId) return;
        if (serverStart < 0)
        {
            warmupFrames++;
            return;
        }
        if (poses == null || poseTick == tick) return;
        poseTick = tick;
        JsonObject row = new JsonObject();
        row.addProperty("tick", tick);
        row.addProperty("image", frame + 1);
        row.addProperty("entityTick", eva.tickCount + partialTick);
        row.addProperty("key", eva.poseTransitionKey(partialTick));
        JsonArray world = new JsonArray();
        world.add(eva.getX()); world.add(eva.getY()); world.add(eva.getZ());
        row.add("world", world);
        JsonObject transforms = new JsonObject();
        for (String name : EvaPoseGraph.contract().boneOrder())
        {
            model.getBone(name).ifPresent(bone ->
            {
                JsonArray values = new JsonArray();
                values.add(bone.getRotX()); values.add(bone.getRotY()); values.add(bone.getRotZ());
                values.add(bone.getPosX()); values.add(bone.getPosY()); values.add(bone.getPosZ());
                transforms.add(name, values);
            });
        }
        row.add("bones", transforms);
        try
        {
            poses.write(row.toString());
            poses.newLine();
        }
        catch (Exception exception)
        {
            throw new IllegalStateException("review pose write", exception);
        }
    }

    @SubscribeEvent
    public static void render(TickEvent.RenderTickEvent event)
    {
        if (!ENABLED || finished || poses == null || event.phase != TickEvent.Phase.END
                || tick == capturedTick) return;
        Minecraft mc = Minecraft.getInstance();
        capturedTick = tick;
        frame++;
        Screenshot.grab(mc.gameDirectory, "projectseele_connected/" + BATCH
                        + String.format("/frame_%04d.png", frame), mc.getMainRenderTarget(), ignored -> {});
    }

    private static void finish(Minecraft mc, String reason)
    {
        finished = true;
        mc.options.keyUp.setDown(false);
        mc.options.keyDown.setDown(false);
        mc.options.keySprint.setDown(false);
        mc.setCameraEntity(mc.player);
        try
        {
            if (poses != null) poses.close();
        }
        catch (Exception exception)
        {
            ProjectSeele.LOGGER.error("Closing connected action review", exception);
        }
        ProjectSeele.LOGGER.info("Connected action review finished: batch={} reason={} ticks={} frames={}",
                BATCH, reason, tick, frame);
        mc.stop();
    }
}
