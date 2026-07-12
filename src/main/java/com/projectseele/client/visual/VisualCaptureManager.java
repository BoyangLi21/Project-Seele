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
            "front", "side", "back", "first_person_clean", "first_person_cockpit"
    };
    private static Session session;

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

    /** Keep hand rendering active while the clean capture hides GUI layers. */
    public static boolean isSuppressingGui()
    {
        return session != null && session.isCleanFirstPerson();
    }

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END || session == null)
        {
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
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
            if (this.view >= VIEWS.length)
            {
                minecraft.player.displayClientMessage(Component.literal(
                        "Visual capture complete: screenshots/projectseele_visual"), false);
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
                if (name.endsWith("clean"))
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
            double distance = Math.max(48.0D, unit.getBbHeight() * 1.8D);
            Vec3 cameraPos = switch (name)
            {
                // Offset the profile camera slightly along the forward axis
                // so lab rulers/door fixtures cannot occlude the subject.
                case "side" -> centre.add(right.scale(distance)).add(forward.scale(12.0D));
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
            minecraft.player.setYRot(unit.getYRot());
            minecraft.player.setYHeadRot(unit.getYRot());
            minecraft.player.setXRot(12.0F);
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
            return this.view < VIEWS.length && VIEWS[this.view].equals("first_person_clean");
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
                case EvaUnit01Entity.VISUAL_CANNON -> "cannon";
                default -> "normal";
            };
        }
    }
}
