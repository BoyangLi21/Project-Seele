package com.projectseele.client.visual;

import java.io.File;
import java.nio.file.Files;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

import com.projectseele.ProjectSeele;
import com.projectseele.client.render.EvaUnit01Renderer;
import com.projectseele.client.render.LocalTriangleMeshLayer;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.MassProductionEvaEntity;
import com.projectseele.fx.TreeOfLifeLayout;
import net.minecraft.client.CameraType;
import net.minecraft.client.CloudStatus;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Deterministic multi-angle PNG capture for Visual Lab regression checks. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class VisualCaptureManager
{
    private static final String CAPTURE_BATCH = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss")
            .format(LocalDateTime.now());
    /** One stable renderer baseline per EVA variant inside a capture batch. */
    private static final Map<String, String> BATCH_MODEL_TAGS = new HashMap<>();
    /** Counts completed named states so repeated custom pose lists close only on their last occurrence. */
    private static final Map<String, Integer> AUTOMATED_POSE_OCCURRENCES = new HashMap<>();
    private static final String[] VIEWS = {
            "front", "side", "back", "front_close", "side_close", "side_opposite_close", "face_close",
            "first_person_clean", "first_person_cockpit",
            "first_person_yaw_left", "first_person_yaw_right",
            "first_person_pitch_up", "first_person_pitch_down"
    };
    private static final String[] MASS_VIEWS = {
            "front", "side", "back", "front_close", "side_close",
            "side_opposite_close", "face_close"
    };
    private static final ResourceLocation MASS_MESH = new ResourceLocation(
            ProjectSeele.MODID, "mesh/mass_production_eva.mesh.json");
    private static Session session;
    private static ImpactSession impactSession;
    private static int shutdownTicks = -1;

    private VisualCaptureManager() {}

    private static boolean isExpectedBodyMesh(String unitName, String tag)
    {
        String contract = switch (unitName)
        {
            case "unit00" -> "triangle-mesh-3692-p17-[0-9a-f]{8}";
            case "unit02" -> "triangle-mesh-3952-p17-[0-9a-f]{8}";
            case "mass" -> "triangle-mesh-4901-p15-[0-9a-f]{8}";
            default -> "triangle-mesh-4226-p17-[0-9a-f]{8}";
        };
        return tag.matches(contract);
    }

    private static boolean isExpectedCannonMesh(String tag)
    {
        return tag.matches("triangle-mesh-14391-p1-[0-9a-f]{8}");
    }

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
            session = null;
        }
        if (impactSession != null)
        {
            impactSession.restore(minecraft);
            impactSession = null;
        }
        shutdownTicks = -1;
        session = new Session(entityId, pose, minecraft);
        minecraft.player.displayClientMessage(Component.literal("Visual capture started"), false);
    }

    /** Starts the complete multi-angle Third-Impact visual regression. */
    public static void startImpact(Vec3 origin, float yaw)
    {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null || minecraft.player == null)
        {
            return;
        }
        if (session != null)
        {
            session.restore(minecraft);
            session = null;
        }
        if (impactSession != null)
        {
            impactSession.restore(minecraft);
            impactSession = null;
        }
        shutdownTicks = -1;
        impactSession = new ImpactSession(origin, yaw, minecraft);
        minecraft.player.displayClientMessage(
                Component.literal("Third Impact visual capture started"), false);
    }

    /** Suppress GUI overlays while leaving the world-space EVA body visible. */
    public static boolean isSuppressingGui()
    {
        return impactSession != null || session != null && session.isCleanFirstPerson();
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
        if (minecraft.isPaused())
        {
            return;
        }
        if (impactSession != null)
        {
            if (!impactSession.tick(minecraft))
            {
                impactSession.restore(minecraft);
                impactSession = null;
            }
            return;
        }
        if (session == null)
        {
            return;
        }
        if (!session.tick(minecraft))
        {
            session.restore(minecraft);
            session = null;
        }
    }

    /** Fixed multi-angle capture of the complete Tree, rather than one entity. */
    private static final class ImpactSession
    {
        private static final int SETTLE_TICKS = 150;
        private static final double CAMERA_DISTANCE = 180.0D;
        private static final double FRAME_BOTTOM = -15.0D;
        private static final double FRAME_TOP_MARGIN = 38.0D;
        private static final String[] IMPACT_VIEWS = {
                "front", "oblique", "tiferet_close"
        };

        private final Vec3 origin;
        private final float yaw;
        private final Entity originalCamera;
        private final CameraType originalCameraType;
        private final boolean originalHideGui;
        private final CloudStatus originalCloudStatus;
        private final String unitMeshTag;
        private final String massMeshTag;
        private ArmorStand camera;
        private int settleTicks = SETTLE_TICKS;
        private int view;
        private boolean positioned;
        private boolean audited;

        ImpactSession(Vec3 origin, float yaw, Minecraft minecraft)
        {
            this.origin = origin;
            this.yaw = yaw;
            this.originalCamera = minecraft.getCameraEntity();
            this.originalCameraType = minecraft.options.getCameraType();
            this.originalHideGui = minecraft.options.hideGui;
            this.originalCloudStatus = minecraft.options.cloudStatus().get();
            this.unitMeshTag = LocalTriangleMeshLayer.captureTag(
                    EvaUnit01Renderer.meshResourceForVariant(EvaUnit01Entity.UNIT_01));
            this.massMeshTag = LocalTriangleMeshLayer.captureTag(MASS_MESH);
            ProjectSeele.LOGGER.info(
                    "Impact visual capture batch {} uses unit01={} mass={}",
                    CAPTURE_BATCH, this.unitMeshTag, this.massMeshTag);
        }

        boolean tick(Minecraft minecraft)
        {
            if (minecraft.level == null || minecraft.player == null)
            {
                return false;
            }
            if (!this.positioned)
            {
                this.position(minecraft);
                this.positioned = true;
                return true;
            }
            this.maintainCamera(minecraft);
            if (this.settleTicks-- > 0)
            {
                return true;
            }

            if (!this.audited)
            {
                this.audit(minecraft);
                this.audited = true;
            }
            this.capture(minecraft);
            this.view++;
            if (this.view >= IMPACT_VIEWS.length)
            {
                if (Boolean.getBoolean("projectseele.visualCapture"))
                {
                    shutdownTicks = 30;
                }
                return false;
            }
            this.positioned = false;
            this.settleTicks = 12;
            return true;
        }

        private void audit(Minecraft minecraft)
        {
            AABB formation = new AABB(this.origin, this.origin).inflate(230.0D);
            int massCount = minecraft.level.getEntitiesOfClass(
                    MassProductionEvaEntity.class, formation, Entity::isAlive).size();
            float expectedYaw = TreeOfLifeLayout.frontFacingYawDegrees(this.yaw);
            long facingCount = minecraft.level.getEntitiesOfClass(
                    MassProductionEvaEntity.class, formation, Entity::isAlive).stream()
                    .filter(mass -> Math.abs(Mth.wrapDegrees(mass.getYRot() - expectedYaw)) < 1.0F)
                    .count();
            long ritualCount = minecraft.level.getEntitiesOfClass(
                    MassProductionEvaEntity.class, formation, Entity::isAlive).stream()
                    .filter(MassProductionEvaEntity::isRitualFormation)
                    .count();
            EvaUnit01Entity crucified = minecraft.level.getEntitiesOfClass(
                    EvaUnit01Entity.class, formation,
                    unit -> unit.isAlive() && unit.getUnitVariant() == EvaUnit01Entity.UNIT_01
                            && unit.isCrucified()).stream().findFirst().orElse(null);
            ProjectSeele.LOGGER.info(
                    "Impact visual evidence: massCount={} massFacingFront={} massRitual={} crucifiedUnit01={} unit01={} mass={}",
                    massCount, facingCount, ritualCount, crucified != null,
                    this.unitMeshTag, this.massMeshTag);
            if (massCount != 9 || facingCount != 9 || ritualCount != 9 || crucified == null
                    || !isExpectedBodyMesh("unit01", this.unitMeshTag)
                    || !isExpectedBodyMesh("mass", this.massMeshTag))
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL IMPACT INVALID: expected 9 front-facing ritual Mass Production EVAs, a crucified Unit-01, and both local triangle meshes");
            }
        }

        private void position(Minecraft minecraft)
        {
            minecraft.options.setCameraType(CameraType.FIRST_PERSON);
            minecraft.options.hideGui = true;
            minecraft.options.cloudStatus().set(CloudStatus.OFF);
            if (this.camera == null)
            {
                this.camera = EntityType.ARMOR_STAND.create(minecraft.level);
                if (this.camera == null)
                {
                    throw new IllegalStateException("Impact visual camera creation failed");
                }
                this.camera.setInvisible(true);
                this.camera.setNoGravity(true);
            }
            this.maintainCamera(minecraft);
            minecraft.setCameraEntity(this.camera);
        }

        private void maintainCamera(Minecraft minecraft)
        {
            double frameTop = TreeOfLifeLayout.localY(9) + FRAME_TOP_MARGIN;
            Vec3 fullTarget = this.origin.add(
                    0.0D, (FRAME_BOTTOM + frameTop) * 0.5D, 0.0D);
            Vec3 front = new Vec3(Mth.sin(this.yaw), 0.0D, Mth.cos(this.yaw));
            Vec3 right = new Vec3(-front.z, 0.0D, front.x);
            String viewName = IMPACT_VIEWS[this.view];
            Vec3 target = viewName.equals("tiferet_close")
                    ? TreeOfLifeLayout.worldNode(
                            this.origin, this.yaw, TreeOfLifeLayout.TIFERET)
                    : fullTarget;
            Vec3 cameraPos = switch (viewName)
            {
                case "oblique" -> target.add(front.scale(CAMERA_DISTANCE * 0.92D))
                        .add(right.scale(72.0D));
                case "tiferet_close" -> target.add(front.scale(68.0D))
                        .add(right.scale(10.0D));
                default -> target.add(front.scale(CAMERA_DISTANCE));
            };
            this.camera.setPos(cameraPos.x, cameraPos.y - this.camera.getEyeHeight(), cameraPos.z);
            lookAt(this.camera, cameraPos, target);
            this.camera.xo = this.camera.getX();
            this.camera.yo = this.camera.getY();
            this.camera.zo = this.camera.getZ();
            this.camera.yRotO = this.camera.getYRot();
            this.camera.xRotO = this.camera.getXRot();
            minecraft.setCameraEntity(this.camera);
        }

        private void capture(Minecraft minecraft)
        {
            try
            {
                File batch = new File(minecraft.gameDirectory,
                        "screenshots/projectseele_visual/" + CAPTURE_BATCH);
                Files.createDirectories(batch.toPath());
                String filename = "impact_" + IMPACT_VIEWS[this.view] + ".png";
                Screenshot.grab(minecraft.gameDirectory,
                        "projectseele_visual/" + CAPTURE_BATCH + "/" + filename,
                        minecraft.getMainRenderTarget(), message -> ProjectSeele.LOGGER.info(
                                "Impact visual capture {}/{}: {}",
                                CAPTURE_BATCH, filename, message.getString()));
            }
            catch (Exception exception)
            {
                ProjectSeele.LOGGER.error("Impact visual screenshot failed", exception);
            }
        }

        void restore(Minecraft minecraft)
        {
            minecraft.setCameraEntity(this.originalCamera != null ? this.originalCamera : minecraft.player);
            minecraft.options.setCameraType(this.originalCameraType);
            minecraft.options.hideGui = this.originalHideGui;
            minecraft.options.cloudStatus().set(this.originalCloudStatus);
        }
    }

    private static void lookAt(Entity camera, Vec3 position, Vec3 target)
    {
        Vec3 delta = target.subtract(position);
        double horizontal = Math.sqrt(delta.x * delta.x + delta.z * delta.z);
        camera.setYRot((float) (Mth.atan2(delta.z, delta.x) * Mth.RAD_TO_DEG) - 90.0F);
        camera.setXRot((float) -(Mth.atan2(delta.y, horizontal) * Mth.RAD_TO_DEG));
        camera.setYHeadRot(camera.getYRot());
    }

    private static final class Session
    {
        private final int entityId;
        private final int requestedPose;
        private final String poseName;
        private final Entity originalCamera;
        private final CameraType originalCameraType;
        private final boolean originalHideGui;
        private final float originalYaw;
        private final float originalPitch;
        private final String bodyModelTag;
        private final String modelTag;
        private final String unitName;
        private final String[] views;
        private final boolean massSubject;
        private ArmorStand camera;
        private int view;
        private int settleTicks;
        private boolean positioned;
        private boolean poseAudited;
        private float referenceYaw = Float.NaN;

        Session(int entityId, int pose, Minecraft minecraft)
        {
            this.entityId = entityId;
            this.requestedPose = pose;
            this.originalCamera = minecraft.getCameraEntity();
            this.originalCameraType = minecraft.options.getCameraType();
            this.originalHideGui = minecraft.options.hideGui;
            this.originalYaw = minecraft.player.getYRot();
            this.originalPitch = minecraft.player.getXRot();
            Entity visualEntity = minecraft.level == null ? null : minecraft.level.getEntity(entityId);
            this.massSubject = visualEntity instanceof MassProductionEvaEntity;
            this.views = this.massSubject ? MASS_VIEWS : VIEWS;
            this.poseName = this.massSubject
                    ? MassProductionEvaEntity.visualPoseName(pose) : poseName(pose);
            int variant = visualEntity instanceof EvaUnit01Entity eva
                    ? eva.getUnitVariant() : EvaUnit01Entity.UNIT_01;
            this.unitName = this.massSubject ? "mass" : switch (variant)
            {
                case EvaUnit01Entity.UNIT_00 -> "unit00";
                case EvaUnit01Entity.UNIT_02 -> "unit02";
                default -> "unit01";
            };
            this.bodyModelTag = LocalTriangleMeshLayer.captureTag(this.massSubject
                    ? MASS_MESH : EvaUnit01Renderer.meshResourceForVariant(variant));
            String weaponTag = !this.massSubject && this.poseName.contains("cannon")
                    ? LocalTriangleMeshLayer.captureTag(
                            EvaUnit01Renderer.positronMeshResource()) : null;
            this.modelTag = weaponTag == null ? this.bodyModelTag
                    : this.bodyModelTag + "__positron-" + weaponTag;
            if (!isExpectedBodyMesh(this.unitName, this.bodyModelTag)
                    || weaponTag != null && !isExpectedCannonMesh(weaponTag))
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL CAPTURE INVALID: {} loaded {} instead of the required local meshes",
                        this.unitName, this.modelTag);
            }
            String previousModelTag = BATCH_MODEL_TAGS.putIfAbsent(
                    this.unitName, this.bodyModelTag);
            if (previousModelTag != null && !previousModelTag.equals(this.bodyModelTag))
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL BATCH INVALID: {} renderer changed from {} to {} before pose {}",
                        this.unitName, previousModelTag, this.bodyModelTag, this.poseName);
            }
            ProjectSeele.LOGGER.info("Visual capture batch {} pose {} uses {}",
                    CAPTURE_BATCH, this.poseName, this.modelTag);
        }

        boolean tick(Minecraft minecraft)
        {
            if (minecraft.level == null || minecraft.player == null)
            {
                return false;
            }
            Entity entity = minecraft.level.getEntity(this.entityId);
            if (entity == null || !entity.isAlive()
                    || this.massSubject && !(entity instanceof MassProductionEvaEntity)
                    || !this.massSubject && !(entity instanceof EvaUnit01Entity))
            {
                minecraft.player.displayClientMessage(Component.literal(
                        "Visual capture failed: subject missing"), false);
                return false;
            }
            if (Float.isNaN(this.referenceYaw))
            {
                this.referenceYaw = entity.getYRot();
            }
            if (this.view >= this.views.length)
            {
                minecraft.player.displayClientMessage(Component.literal(
                        "Visual capture complete: screenshots/projectseele_visual/"
                                + CAPTURE_BATCH), false);
                if (isLastAutomatedPose(this.unitName, this.poseName))
                {
                    shutdownTicks = 20;
                }
                return false;
            }
            if (!this.positioned)
            {
                this.position(minecraft, entity);
                this.positioned = true;
                this.settleTicks = 8;
                return true;
            }
            if (entity instanceof EvaUnit01Entity unit)
            {
                this.maintainFirstPerson(minecraft, unit);
            }
            if (this.settleTicks-- > 0)
            {
                return true;
            }
            if (this.massSubject && !this.poseAudited)
            {
                int clientPose = ((MassProductionEvaEntity) entity).getVisualPose();
                if (clientPose != this.requestedPose)
                {
                    ProjectSeele.LOGGER.error(
                            "VISUAL MASS POSE INVALID: requested {} ({}) but client has {} ({})",
                            this.requestedPose, this.poseName, clientPose,
                            MassProductionEvaEntity.visualPoseName(clientPose));
                }
                else
                {
                    ProjectSeele.LOGGER.info(
                            "Visual Mass pose synchronized: {} ({})",
                            this.requestedPose, this.poseName);
                }
                this.poseAudited = true;
            }
            this.capture(minecraft);
            this.view++;
            this.positioned = false;
            return true;
        }

        private void position(Minecraft minecraft, Entity subject)
        {
            String name = this.views[this.view];
            minecraft.options.setCameraType(CameraType.FIRST_PERSON);
            if (name.startsWith("first_person"))
            {
                EvaUnit01Entity unit = (EvaUnit01Entity) subject;
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
            boolean faceClose = name.equals("face_close");
            boolean lowFace = subject instanceof EvaUnit01Entity unit
                    && (unit.getVisualPose() == EvaUnit01Entity.VISUAL_CROUCH
                        || unit.getVisualPose() == EvaUnit01Entity.VISUAL_PRONE
                        || unit.getVisualPose() == EvaUnit01Entity.VISUAL_PRONE_CANNON);
            Vec3 centre = subject.position().add(0.0D,
                    subject.getBbHeight() * (faceClose ? (lowFace ? 0.60D : 0.84D) : 0.52D), 0.0D);
            float yaw = subject.getYRot() * Mth.DEG_TO_RAD;
            Vec3 forward = new Vec3(-Mth.sin(yaw), 0.0D, Mth.cos(yaw));
            Vec3 right = new Vec3(-forward.z, 0.0D, forward.x);
            boolean close = name.endsWith("close");
            double distance = faceClose ? 10.0D : close
                    ? Math.max(30.0D, subject.getBbHeight() * 1.12D)
                    : Math.max(48.0D, subject.getBbHeight() * 1.8D);
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
            if (!this.views[this.view].startsWith("first_person"))
            {
                return;
            }
            String name = this.views[this.view];
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
                File batch = new File(output, CAPTURE_BATCH);
                Files.createDirectories(batch.toPath());
                String filename = this.unitName + "_" + this.modelTag + "_" + this.views[this.view]
                        + "_" + this.poseName + ".png";
                Screenshot.grab(minecraft.gameDirectory,
                        "projectseele_visual/" + CAPTURE_BATCH + "/" + filename,
                        minecraft.getMainRenderTarget(), message -> ProjectSeele.LOGGER.info(
                                "Visual capture {}/{}: {}", CAPTURE_BATCH, filename,
                                message.getString()));
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
            return this.view < this.views.length
                    && this.views[this.view].startsWith("first_person")
                    && !this.views[this.view].endsWith("cockpit");
        }

        private static void lookAt(Entity camera, Vec3 position, Vec3 target)
        {
            VisualCaptureManager.lookAt(camera, position, target);
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
                case EvaUnit01Entity.VISUAL_CROUCH -> "crouch";
                case EvaUnit01Entity.VISUAL_PRONE -> "prone";
                case EvaUnit01Entity.VISUAL_PRONE_CANNON -> "prone_cannon";
                case EvaUnit01Entity.VISUAL_LANCE_WINDUP -> "lance_windup";
                case EvaUnit01Entity.VISUAL_LANCE_CONTACT -> "lance_contact";
                case EvaUnit01Entity.VISUAL_LANCE_RECOVERY -> "lance_recovery";
                case EvaUnit01Entity.VISUAL_CANNON -> "cannon";
                default -> "normal";
            };
        }

        private static boolean isLastAutomatedPose(String unitName, String pose)
        {
            if (!Boolean.getBoolean("projectseele.visualCapture"))
            {
                return false;
            }
            int observed = AUTOMATED_POSE_OCCURRENCES.merge(
                    unitName + ":" + pose, 1, Integer::sum);
            String requested = System.getProperty("projectseele.visualCapturePose", "all");
            if (requested.equals("all"))
            {
                return pose.equals(unitName.equals("mass") ? "ritual" : "cannon");
            }
            String[] poses = requested.split(",");
            if (poses.length == 0)
            {
                return false;
            }
            String last = poses[poses.length - 1].trim();
            int expectedOccurrences = 0;
            for (String requestedPose : poses)
            {
                if (last.equals(requestedPose.trim()))
                {
                    expectedOccurrences++;
                }
            }
            return pose.equals(last) && observed >= expectedOccurrences;
        }
    }
}
