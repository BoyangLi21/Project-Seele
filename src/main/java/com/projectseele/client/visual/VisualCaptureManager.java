package com.projectseele.client.visual;

import java.io.File;
import java.nio.file.Files;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Deterministic multi-angle PNG capture for Visual Lab regression checks. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class VisualCaptureManager
{
    private static final String[] VIEWS = {
            "front", "side", "back", "front_close", "side_close", "side_opposite_close",
            "first_person_clean", "first_person_cockpit",
            "first_person_yaw_left", "first_person_yaw_right",
            "first_person_pitch_up", "first_person_pitch_down"
    };
    private static Session session;
    private static int shutdownTicks = -1;

    private VisualCaptureManager() {}

    public static void start(int entityId, int pose)
    {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null || minecraft.player == null)
        {
            return;
        }
        if (session != null)
        {
            session.restore(minecraft);
        }
        session = new Session(entityId, pose, minecraft);
        minecraft.player.displayClientMessage(Component.literal("Visual capture started"), false);
    }

    /** Suppress GUI overlays while leaving the world-space EVA body visible. */
    public static boolean isSuppressingGui()
    {
        return session != null && session.isCleanFirstPerson();
    }

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END)
        {
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        if (shutdownTicks >= 0 && shutdownTicks-- == 0)
        {
            ProjectSeele.LOGGER.info("Visual Lab screenshots complete; closing unattended client");
            minecraft.stop();
            return;
        }
        if (session == null)
        {
            return;
        }
        if (minecraft.isPaused())
        {
            return;
        }
        if (!session.tick(minecraft))
        {
            session.restore(minecraft);
            session = null;
        }
    }

    private static final class Session
    {
        private final int entityId;
        private final String poseName;
        private final Entity originalCamera;
        private final CameraType originalCameraType;
        private final boolean originalHideGui;
        private final float originalYaw;
        private final float originalPitch;
        private ArmorStand camera;
        private int view;
        private int settleTicks;
        private boolean positioned;
        private float referenceYaw = Float.NaN;

        Session(int entityId, int pose, Minecraft minecraft)
        {
            this.entityId = entityId;
            this.poseName = poseName(pose);
            this.originalCamera = minecraft.getCameraEntity();
            this.originalCameraType = minecraft.options.getCameraType();
            this.originalHideGui = minecraft.options.hideGui;
            this.originalYaw = minecraft.player.getYRot();
            this.originalPitch = minecraft.player.getXRot();
        }

        boolean tick(Minecraft minecraft)
        {
            if (minecraft.level == null || minecraft.player == null)
            {
                return false;
            }
            Entity entity = minecraft.level.getEntity(this.entityId);
            if (!(entity instanceof EvaUnit01Entity unit) || !unit.isAlive())
            {
                minecraft.player.displayClientMessage(Component.literal("Visual capture failed: Unit-01 missing"), false);
                return false;
            }
            if (Float.isNaN(this.referenceYaw))
            {
                this.referenceYaw = unit.getYRot();
            }
            if (this.view >= VIEWS.length)
            {
                minecraft.player.displayClientMessage(Component.literal(
                        "Visual capture complete: screenshots/projectseele_visual"), false);
                if (isLastAutomatedPose(this.poseName))
                {
                    shutdownTicks = 20;
                }
                return false;
            }
            if (!this.positioned)
            {
                this.position(minecraft, unit);
                this.positioned = true;
                this.settleTicks = 8;
                return true;
            }
            this.maintainFirstPerson(minecraft, unit);
            if (this.settleTicks-- > 0)
            {
                return true;
            }
            this.capture(minecraft);
            this.view++;
            this.positioned = false;
            return true;
        }

        private void position(Minecraft minecraft, EvaUnit01Entity unit)
        {
            String name = VIEWS[this.view];
            minecraft.options.setCameraType(CameraType.FIRST_PERSON);
            if (name.startsWith("first_person"))
            {
                minecraft.setCameraEntity(minecraft.player);
                // F1/hideGui also disables RenderHandEvent. Leave it false
                // and cancel GUI overlays separately for a clean arm frame.
                minecraft.options.hideGui = false;
                if (!name.endsWith("cockpit"))
                {
                    minecraft.gui.getChat().clearMessages(false);
                }
                this.maintainFirstPerson(minecraft, unit);
                return;
            }
            minecraft.options.hideGui = true;
            if (this.camera == null)
            {
                this.camera = EntityType.ARMOR_STAND.create(minecraft.level);
                if (this.camera == null)
                {
                    throw new IllegalStateException("Visual camera creation failed");
                }
                this.camera.setInvisible(true);
                this.camera.setNoGravity(true);
            }
            Vec3 centre = unit.position().add(0.0D, unit.getBbHeight() * 0.52D, 0.0D);
            float yaw = unit.getYRot() * Mth.DEG_TO_RAD;
            Vec3 forward = new Vec3(-Mth.sin(yaw), 0.0D, Mth.cos(yaw));
            Vec3 right = new Vec3(-forward.z, 0.0D, forward.x);
            boolean close = name.endsWith("close");
            double distance = close
                    ? Math.max(30.0D, unit.getBbHeight() * 1.12D)
                    : Math.max(48.0D, unit.getBbHeight() * 1.8D);
            Vec3 cameraPos = switch (name)
            {
                // Offset the profile camera slightly along the forward axis
                // so lab rulers/door fixtures cannot occlude the subject.
                case "side", "side_close" -> centre.add(right.scale(distance))
                        .add(forward.scale(close ? 8.0D : 12.0D));
                case "side_opposite_close" -> centre.subtract(right.scale(distance))
                        .add(forward.scale(8.0D));
                case "back" -> centre.subtract(forward.scale(distance));
                default -> centre.add(forward.scale(distance));
            };
            this.camera.setPos(cameraPos.x, cameraPos.y - this.camera.getEyeHeight(), cameraPos.z);
            lookAt(this.camera, cameraPos, centre);
            // The debug camera is deliberately not added to the level. Keep
            // its interpolation history in lockstep with its current pose or
            // Camera.setup() blends from (0, 0, 0) and photographs an
            // unrelated part of the lab.
            this.camera.xo = this.camera.getX();
            this.camera.yo = this.camera.getY();
            this.camera.zo = this.camera.getZ();
            this.camera.yRotO = this.camera.getYRot();
            this.camera.xRotO = this.camera.getXRot();
            minecraft.setCameraEntity(this.camera);
        }

        private void maintainFirstPerson(Minecraft minecraft, EvaUnit01Entity unit)
        {
            if (!VIEWS[this.view].startsWith("first_person"))
            {
                return;
            }
            String name = VIEWS[this.view];
            float yaw = this.referenceYaw;
            float pitch = 12.0F;
            if (name.endsWith("yaw_left"))
            {
                yaw -= 90.0F;
            }
            else if (name.endsWith("yaw_right"))
            {
                yaw += 90.0F;
            }
            else if (name.endsWith("pitch_up"))
            {
                pitch = -35.0F;
            }
            else if (name.endsWith("pitch_down"))
            {
                pitch = 70.0F;
            }
            minecraft.player.setYRot(yaw);
            minecraft.player.setYHeadRot(yaw);
            minecraft.player.setXRot(pitch);
        }

        private void capture(Minecraft minecraft)
        {
            try
            {
                File output = new File(minecraft.gameDirectory, "screenshots/projectseele_visual");
                Files.createDirectories(output.toPath());
                String filename = "unit01_" + VIEWS[this.view] + "_" + this.poseName + ".png";
                Screenshot.grab(minecraft.gameDirectory, "projectseele_visual/" + filename,
                        minecraft.getMainRenderTarget(), message -> ProjectSeele.LOGGER.info(
                                "Visual capture {}: {}", filename, message.getString()));
            }
            catch (Exception exception)
            {
                ProjectSeele.LOGGER.error("Visual screenshot failed", exception);
            }
        }

        void restore(Minecraft minecraft)
        {
            minecraft.setCameraEntity(this.originalCamera != null ? this.originalCamera : minecraft.player);
            minecraft.options.setCameraType(this.originalCameraType);
            minecraft.options.hideGui = this.originalHideGui;
            if (minecraft.player != null)
            {
                minecraft.player.setYRot(this.originalYaw);
                minecraft.player.setXRot(this.originalPitch);
            }
        }

        boolean isCleanFirstPerson()
        {
            return this.view < VIEWS.length
                    && VIEWS[this.view].startsWith("first_person")
                    && !VIEWS[this.view].endsWith("cockpit");
        }

        private static void lookAt(Entity camera, Vec3 position, Vec3 target)
        {
            Vec3 delta = target.subtract(position);
            double horizontal = Math.sqrt(delta.x * delta.x + delta.z * delta.z);
            camera.setYRot((float) (Mth.atan2(delta.z, delta.x) * Mth.RAD_TO_DEG) - 90.0F);
            camera.setXRot((float) -(Mth.atan2(delta.y, horizontal) * Mth.RAD_TO_DEG));
            camera.setYHeadRot(camera.getYRot());
        }

        private static String poseName(int pose)
        {
            return switch (pose)
            {
                case EvaUnit01Entity.VISUAL_IDLE -> "idle";
                case EvaUnit01Entity.VISUAL_WALK_CONTACT -> "walk_contact";
                case EvaUnit01Entity.VISUAL_KNIFE_WINDUP -> "knife_windup";
                case EvaUnit01Entity.VISUAL_KNIFE_CONTACT -> "knife_contact";
                case EvaUnit01Entity.VISUAL_KNIFE_RECOVERY -> "knife_recovery";
                case EvaUnit01Entity.VISUAL_CANNON -> "cannon";
                default -> "normal";
            };
        }

        private static boolean isLastAutomatedPose(String pose)
        {
            if (!Boolean.getBoolean("projectseele.visualCapture"))
            {
                return false;
            }
            String requested = System.getProperty("projectseele.visualCapturePose", "all");
            if (requested.equals("all"))
            {
                return pose.equals("cannon");
            }
            String[] poses = requested.split(",");
            return poses.length > 0 && pose.equals(poses[poses.length - 1].trim());
        }
    }
}
