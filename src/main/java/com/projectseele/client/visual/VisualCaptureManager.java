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
import com.projectseele.client.render.LocalVisualAssetFingerprint;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.MassProductionEvaEntity;
import com.projectseele.entity.RamielEntity;
import com.projectseele.fx.TreeOfLifeLayout;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.network.ServerboundEvaControlPacket;
import com.projectseele.network.ServerboundGeoFrontCameraPacket;
import com.projectseele.registry.ModBlocks;
import com.projectseele.world.GeoFrontBuilder;
import com.projectseele.world.IntegratedNervMapBuilder;
import com.projectseele.world.LocalMapAssetLoader;
import com.projectseele.world.RetractableBuildingCoreBlock;
import com.projectseele.world.ThirdTokyoSurfaceBuilder;
import net.minecraft.client.CameraType;
import net.minecraft.client.CloudStatus;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.material.Fluids;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.jetbrains.annotations.Nullable;

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
    private static final String[] LIVE_ATTACK_VIEWS = {
            "front_close", "side_close", "first_person_clean"
    };
    private static final String[] LIVE_JUMP_VIEWS = {
            "side_close"
    };
    private static Session session;
    private static ImpactSession impactSession;
    private static SiloSession siloSession;
    private static Tokyo3Session tokyo3Session;
    private static Tokyo3RetractionSession tokyo3RetractionSession;
    private static GeoFrontSession geoFrontSession;
    private static GeoFrontSortieSession geoFrontSortieSession;
    private static int shutdownTicks = -1;

    private VisualCaptureManager() {}

    private static boolean isExpectedCannonMesh(String tag)
    {
        return tag.matches("triangle-mesh-14391-p1-[0-9a-f]{8}");
    }

    private static boolean isExpectedRifleMesh(String tag)
    {
        // The 292-triangle TV Pallet Rifle is local-only.  The 240-triangle
        // original rifle remains a legal clean-room fallback for public packs.
        return tag.matches("triangle-mesh-(?:292|240)-p1-[0-9a-f]{8}");
    }

    private static boolean isExpectedN2Mesh(String tag)
    {
        return tag.matches("triangle-mesh-356-p1-[0-9a-f]{8}");
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
        if (siloSession != null)
        {
            siloSession.restore(minecraft);
            siloSession = null;
        }
        if (tokyo3Session != null)
        {
            tokyo3Session.restore(minecraft);
            tokyo3Session = null;
        }
        if (tokyo3RetractionSession != null)
        {
            tokyo3RetractionSession.restore(minecraft);
            tokyo3RetractionSession = null;
        }
        if (geoFrontSession != null)
        {
            geoFrontSession.restore(minecraft);
            geoFrontSession = null;
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
        if (siloSession != null)
        {
            siloSession.restore(minecraft);
            siloSession = null;
        }
        if (tokyo3Session != null)
        {
            tokyo3Session.restore(minecraft);
            tokyo3Session = null;
        }
        if (tokyo3RetractionSession != null)
        {
            tokyo3RetractionSession.restore(minecraft);
            tokyo3RetractionSession = null;
        }
        if (geoFrontSession != null)
        {
            geoFrontSession.restore(minecraft);
            geoFrontSession = null;
        }
        shutdownTicks = -1;
        impactSession = new ImpactSession(origin, yaw, minecraft);
        minecraft.player.displayClientMessage(
                Component.literal("Third Impact visual capture started"), false);
    }

    /** Starts a phase-driven capture of the real entry-plug/catapult state machine. */
    public static void startSilo(int entityId)
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
        if (siloSession != null)
        {
            siloSession.restore(minecraft);
        }
        if (tokyo3Session != null)
        {
            tokyo3Session.restore(minecraft);
            tokyo3Session = null;
        }
        if (tokyo3RetractionSession != null)
        {
            tokyo3RetractionSession.restore(minecraft);
            tokyo3RetractionSession = null;
        }
        if (geoFrontSession != null)
        {
            geoFrontSession.restore(minecraft);
            geoFrontSession = null;
        }
        shutdownTicks = -1;
        siloSession = new SiloSession(entityId, minecraft);
        minecraft.player.displayClientMessage(
                Component.literal("Launch-silo visual capture started"), false);
    }

    /** Starts four fixed views of the complete Tokyo-3 surface sortie district. */
    public static void startTokyo3(BlockPos origin)
    {
        startTokyo3(origin, false);
    }

    /** Starts close battle views that require Ramiel and retracted armour towers. */
    public static void startTokyo3Battle(BlockPos origin)
    {
        startTokyo3(origin, true);
    }

    private static void startTokyo3(BlockPos origin, boolean battle)
    {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null || minecraft.player == null)
        {
            return;
        }
        if (origin.getY() <= -2000)
        {
            ProjectSeele.LOGGER.error(
                    "VISUAL TOKYO3 INVALID: server-side district setup failed");
            shutdownTicks = 20;
            return;
        }
        if (Boolean.getBoolean("projectseele.visualCapture") && minecraft.screen != null)
        {
            minecraft.setScreen(null);
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
        if (siloSession != null)
        {
            siloSession.restore(minecraft);
            siloSession = null;
        }
        if (tokyo3Session != null)
        {
            tokyo3Session.restore(minecraft);
            tokyo3Session = null;
        }
        if (tokyo3RetractionSession != null)
        {
            tokyo3RetractionSession.restore(minecraft);
            tokyo3RetractionSession = null;
        }
        if (geoFrontSession != null)
        {
            geoFrontSession.restore(minecraft);
            geoFrontSession = null;
        }
        shutdownTicks = -1;
        tokyo3Session = new Tokyo3Session(origin, minecraft, battle);
        minecraft.player.displayClientMessage(
                Component.literal(battle
                        ? "Operation Yashima visual capture started"
                        : "Tokyo-3 visual capture started"), false);
    }

    /** Starts a direct before/mid/down/restored comparison of armour towers. */
    public static void startTokyo3Retraction(BlockPos origin)
    {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null || minecraft.player == null)
        {
            return;
        }
        if (origin.getY() <= -2000)
        {
            ProjectSeele.LOGGER.error(
                    "VISUAL TOKYO3 RETRACTION INVALID: server-side district setup failed");
            shutdownTicks = 20;
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
        if (siloSession != null)
        {
            siloSession.restore(minecraft);
            siloSession = null;
        }
        if (tokyo3Session != null)
        {
            tokyo3Session.restore(minecraft);
            tokyo3Session = null;
        }
        if (tokyo3RetractionSession != null)
        {
            tokyo3RetractionSession.restore(minecraft);
        }
        if (geoFrontSession != null)
        {
            geoFrontSession.restore(minecraft);
            geoFrontSession = null;
        }
        shutdownTicks = -1;
        tokyo3RetractionSession = new Tokyo3RetractionSession(origin, minecraft);
        minecraft.player.displayClientMessage(
                Component.literal("Tokyo-3 retraction visual capture started"), false);
    }

    /** Starts four audited views of the independent GeoFront dimension. */
    public static void startGeoFront(BlockPos origin)
    {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null || minecraft.player == null)
        {
            return;
        }
        if (origin.getY() <= -2000)
        {
            ProjectSeele.LOGGER.error(
                    "VISUAL GEOFRONT INVALID: server-side cavern setup failed");
            shutdownTicks = 20;
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
        if (siloSession != null)
        {
            siloSession.restore(minecraft);
            siloSession = null;
        }
        if (tokyo3Session != null)
        {
            tokyo3Session.restore(minecraft);
            tokyo3Session = null;
        }
        if (tokyo3RetractionSession != null)
        {
            tokyo3RetractionSession.restore(minecraft);
            tokyo3RetractionSession = null;
        }
        if (geoFrontSession != null)
        {
            geoFrontSession.restore(minecraft);
        }
        shutdownTicks = -1;
        geoFrontSession = new GeoFrontSession(origin, minecraft);
        minecraft.player.displayClientMessage(
                Component.literal("GeoFront visual capture started"), false);
    }

    /** Starts a synchronized GeoFront-to-Tokyo-3 cross-dimension sortie capture. */
    public static void startGeoFrontSortie(int entityId, BlockPos origin)
    {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null || minecraft.player == null)
        {
            return;
        }
        if (entityId < 0 || origin.getY() <= -2000)
        {
            ProjectSeele.LOGGER.error(
                    "VISUAL GEOFRONT SORTIE INVALID: server-side setup failed");
            shutdownTicks = 20;
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
        if (siloSession != null)
        {
            siloSession.restore(minecraft);
            siloSession = null;
        }
        if (tokyo3Session != null)
        {
            tokyo3Session.restore(minecraft);
            tokyo3Session = null;
        }
        if (tokyo3RetractionSession != null)
        {
            tokyo3RetractionSession.restore(minecraft);
            tokyo3RetractionSession = null;
        }
        if (geoFrontSession != null)
        {
            geoFrontSession.restore(minecraft);
            geoFrontSession = null;
        }
        if (geoFrontSortieSession != null)
        {
            geoFrontSortieSession.restore(minecraft);
        }
        shutdownTicks = -1;
        geoFrontSortieSession = new GeoFrontSortieSession(entityId, origin, minecraft);
        minecraft.player.displayClientMessage(
                Component.literal("GeoFront sortie visual capture started"), false);
    }

    /** Suppress GUI overlays while leaving the world-space EVA body visible. */
    public static boolean isSuppressingGui()
    {
        return impactSession != null || tokyo3Session != null
                || tokyo3RetractionSession != null
                || geoFrontSession != null
                || geoFrontSortieSession != null
                || session != null && session.isCleanFirstPerson();
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
        if (geoFrontSortieSession != null)
        {
            if (!geoFrontSortieSession.tick(minecraft))
            {
                geoFrontSortieSession.restore(minecraft);
                geoFrontSortieSession = null;
            }
            return;
        }
        if (geoFrontSession != null)
        {
            if (!geoFrontSession.tick(minecraft))
            {
                geoFrontSession.restore(minecraft);
                geoFrontSession = null;
            }
            return;
        }
        if (tokyo3RetractionSession != null)
        {
            if (!tokyo3RetractionSession.tick(minecraft))
            {
                tokyo3RetractionSession.restore(minecraft);
                tokyo3RetractionSession = null;
            }
            return;
        }
        if (tokyo3Session != null)
        {
            if (!tokyo3Session.tick(minecraft))
            {
                tokyo3Session.restore(minecraft);
                tokyo3Session = null;
            }
            return;
        }
        if (siloSession != null)
        {
            if (!siloSession.tick(minecraft))
            {
                siloSession.restore(minecraft);
                siloSession = null;
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

    /** Five state-gated frames spanning one real continuous-shaft EVA launch. */
    private static final class GeoFrontSortieSession
    {
        private static final String[] STAGES = {
                "three_units_ready", "entry_plug_locked", "live_pilot_sensor",
                "ascent_mid", "tokyo3_surface_arrival"
        };
        private static final int TIMEOUT_TICKS = 520;

        private int entityId;
        private final BlockPos origin;
        private final CameraType originalCameraType;
        private final boolean originalHideGui;
        private final CloudStatus originalCloudStatus;
        private final LocalVisualAssetFingerprint.Fingerprint bodyFingerprint;
        private final String modelTag;
        private ArmorStand camera;
        private int stage;
        private int settleTicks;
        private int elapsedTicks;
        private boolean positioned;

        GeoFrontSortieSession(int entityId, BlockPos origin, Minecraft minecraft)
        {
            this.entityId = entityId;
            this.origin = origin.immutable();
            this.originalCameraType = minecraft.options.getCameraType();
            this.originalHideGui = minecraft.options.hideGui;
            this.originalCloudStatus = minecraft.options.cloudStatus().get();
            Entity entity = minecraft.level.getEntity(entityId);
            int variant = entity instanceof EvaUnit01Entity unit
                    ? unit.getUnitVariant() : EvaUnit01Entity.UNIT_01;
            this.bodyFingerprint = EvaUnit01Renderer.visualFingerprintForVariant(variant);
            this.modelTag = this.bodyFingerprint.compactTag();
            ProjectSeele.LOGGER.info(
                    "GeoFront sortie capture batch {} uses {}", CAPTURE_BATCH, this.modelTag);
        }

        boolean tick(Minecraft minecraft)
        {
            if (minecraft.level == null || minecraft.player == null)
            {
                return false;
            }
            this.elapsedTicks++;
            if (this.elapsedTicks > TIMEOUT_TICKS)
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL GEOFRONT SORTIE INVALID: timed out before stage {}",
                        this.stage < STAGES.length ? STAGES[this.stage] : "complete");
                shutdownTicks = 20;
                return false;
            }
            if (LocalVisualAssetFingerprint.isStrictMode() && !this.bodyFingerprint.valid())
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL GEOFRONT SORTIE INVALID: high-detail EVA unavailable: {}",
                        this.bodyFingerprint.description());
                shutdownTicks = 20;
                return false;
            }
            EvaUnit01Entity unit = this.resolveUnit(minecraft);
            if (unit == null || !unit.isAlive())
            {
                // The old client entity disappears briefly while the new
                // dimension entity is installed. The overall timeout remains
                // authoritative instead of treating that expected gap as a failure.
                return true;
            }
            if (this.stage == 4 && this.elapsedTicks % 40 == 0)
            {
                ProjectSeele.LOGGER.info(
                        "GeoFront sortie arrival client gate: dimension={} phase={} y={} "
                                + "riding={} vehicleId={} trackedId={}",
                        minecraft.level.dimension().location(), unit.getLaunchPhase(),
                        String.format(java.util.Locale.ROOT, "%.3f", unit.getY()),
                        minecraft.player.getVehicle() == unit,
                        minecraft.player.getVehicle() == null ? -1
                                : minecraft.player.getVehicle().getId(),
                        unit.getId());
            }
            if (!this.stageReady(minecraft, unit))
            {
                return true;
            }
            if (!this.positioned)
            {
                this.positioned = true;
                this.settleTicks = switch (this.stage)
                {
                    case 0 -> 20;
                    case 4 -> 15;
                    case 3 -> 1;
                    case 2 -> 20;
                    default -> 5;
                };
            }
            this.position(minecraft, unit);
            if (this.settleTicks-- > 0)
            {
                return true;
            }
            if (!this.stageReady(minecraft, unit))
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL GEOFRONT SORTIE INVALID: state changed while settling {}",
                        STAGES[this.stage]);
                shutdownTicks = 20;
                return false;
            }
            this.capture(minecraft, unit);
            this.stage++;
            this.positioned = false;
            if (this.stage >= STAGES.length)
            {
                ProjectSeele.LOGGER.info(
                        "GeoFront sortie visual matrix finished: five synchronized stages captured");
                shutdownTicks = 20;
                return false;
            }
            return true;
        }

        @Nullable
        private EvaUnit01Entity resolveUnit(Minecraft minecraft)
        {
            if (minecraft.player.getVehicle() instanceof EvaUnit01Entity ridden)
            {
                this.entityId = ridden.getId();
                return ridden;
            }
            Entity entity = minecraft.level.getEntity(this.entityId);
            return entity instanceof EvaUnit01Entity unit ? unit : null;
        }

        private boolean stageReady(Minecraft minecraft, EvaUnit01Entity unit)
        {
            boolean inGeoFront = minecraft.level.dimension().location().toString()
                    .equals("projectseele:geofront");
            boolean riding = minecraft.player.getVehicle() == unit;
            double ascent = IntegratedNervMapBuilder.ascentDistance();
            return switch (this.stage)
            {
                case 0 -> inGeoFront && unit.getLaunchPhase() == EvaUnit01Entity.LAUNCH_IDLE
                        && !riding;
                case 1 -> inGeoFront && unit.getLaunchPhase() == EvaUnit01Entity.LAUNCH_LOCKED
                        && unit.getActivationTicks() > 65 && riding;
                case 2 -> inGeoFront && unit.getLaunchPhase() == EvaUnit01Entity.LAUNCH_LOCKED
                        && unit.getActivationTicks() > 65 && riding;
                case 3 -> inGeoFront && unit.getLaunchPhase() == EvaUnit01Entity.LAUNCH_ASCENT
                        && unit.getLaunchTicks() >= 45 && unit.getLaunchTicks() <= 100
                        && unit.getY() >= this.origin.getY() + ascent * 0.40D
                        && unit.getY() <= this.origin.getY() + ascent + 8.0D && riding;
                case 4 -> inGeoFront
                        && (unit.getLaunchPhase() == EvaUnit01Entity.LAUNCH_CLEAR
                            || unit.getLaunchPhase() == EvaUnit01Entity.LAUNCH_IDLE)
                        && unit.getY() >= this.origin.getY() + ascent + 1.5D && riding;
                default -> false;
            };
        }

        private void position(Minecraft minecraft, EvaUnit01Entity unit)
        {
            minecraft.options.setCameraType(CameraType.FIRST_PERSON);
            minecraft.options.hideGui = true;
            minecraft.options.cloudStatus().set(CloudStatus.OFF);
            if (this.camera == null || this.camera.level() != minecraft.level)
            {
                this.camera = EntityType.ARMOR_STAND.create(minecraft.level);
                if (this.camera == null)
                {
                    throw new IllegalStateException(
                            "GeoFront sortie visual camera creation failed");
                }
                this.camera.setInvisible(true);
                this.camera.setNoGravity(true);
            }
            float yaw = unit.getYRot() * Mth.DEG_TO_RAD;
            Vec3 forward = new Vec3(-Mth.sin(yaw), 0.0D, Mth.cos(yaw));
            Vec3 right = new Vec3(-forward.z, 0.0D, forward.x);
            Vec3 rear = forward.scale(-1.0D);
            Vec3 target;
            Vec3 cameraPos;
            switch (this.stage)
            {
                case 0 ->
                {
                    target = Vec3.atCenterOf(this.origin.offset(0, 17, -76));
                    cameraPos = Vec3.atCenterOf(this.origin.offset(0, 60, -28));
                }
                case 1 ->
                {
                    target = unit.getEntryPlugSocketPosition().add(0.0D, 1.2D, 0.0D);
                    cameraPos = target.add(rear.scale(4.0D))
                            .add(right.scale(5.25D)).add(0.0D, 3.8D, 0.0D);
                }
                case 2 ->
                {
                    // The automation player remains the real mounted pilot;
                    // only the client camera visits the bridge. This gives a
                    // direct visual proof that the fifth screen is driven by
                    // the active entry-plug eye/yaw/pitch feed.
                    target = Vec3.atCenterOf(this.origin.offset(0, 18, 59));
                    cameraPos = Vec3.atCenterOf(this.origin.offset(0, 18, 84));
                }
                case 3 ->
                {
                    // Stay inside the audited 11x11 clear shaft.  The old
                    // 20x16 offset put the observer behind the reinforced
                    // wall, so a valid ascent looked like an EVA in a void.
                    // Looking upward preserves the Unit's vertical silhouette
                    // instead of foreshortening it into a top-down sprawl.
                    target = unit.position().add(0.0D, 13.5D, 0.0D);
                    cameraPos = target.add(right.scale(4.25D))
                            .add(rear.scale(4.25D)).add(0.0D, -40.0D, 0.0D);
                }
                default ->
                {
                    // The imported 1.7 world can carry a night timestamp.
                    // Pin only the unattended evidence frame to noon so the
                    // surface geometry remains inspectable; gameplay time is
                    // still server-authoritative outside this capture.
                    minecraft.level.setDayTime(6000L);
                    target = unit.position().add(0.0D, 14.0D, 0.0D);
                    cameraPos = target.add(forward.scale(52.0D))
                            .add(right.scale(28.0D)).add(0.0D, 18.0D, 0.0D);
                }
            }
            this.camera.setPos(cameraPos.x, cameraPos.y - this.camera.getEyeHeight(), cameraPos.z);
            lookAt(this.camera, cameraPos, target);
            this.camera.xo = this.camera.getX();
            this.camera.yo = this.camera.getY();
            this.camera.zo = this.camera.getZ();
            this.camera.yRotO = this.camera.getYRot();
            this.camera.xRotO = this.camera.getXRot();
            minecraft.setCameraEntity(this.camera);
        }

        private void capture(Minecraft minecraft, EvaUnit01Entity unit)
        {
            String stageName = STAGES[this.stage];
            ProjectSeele.LOGGER.info(
                    "GeoFront sortie visual stage {}: dimension={} phase={} activation={} "
                            + "launchTicks={} y={}",
                    stageName, minecraft.level.dimension().location(),
                    unit.getLaunchPhase(), unit.getActivationTicks(), unit.getLaunchTicks(),
                    String.format(java.util.Locale.ROOT, "%.3f", unit.getY()));
            try
            {
                File batch = new File(minecraft.gameDirectory,
                        "screenshots/projectseele_visual/" + CAPTURE_BATCH);
                Files.createDirectories(batch.toPath());
                String filename = "geofront_sortie_" + this.modelTag
                        + "_" + stageName + ".png";
                Screenshot.grab(minecraft.gameDirectory,
                        "projectseele_visual/" + CAPTURE_BATCH + "/" + filename,
                        minecraft.getMainRenderTarget(), message -> ProjectSeele.LOGGER.info(
                                "GeoFront sortie visual capture {}/{}: {}",
                                CAPTURE_BATCH, filename, message.getString()));
            }
            catch (Exception exception)
            {
                ProjectSeele.LOGGER.error(
                        "GeoFront sortie visual screenshot failed", exception);
            }
        }

        void restore(Minecraft minecraft)
        {
            minecraft.setCameraEntity(minecraft.player);
            minecraft.options.setCameraType(this.originalCameraType);
            minecraft.options.hideGui = this.originalHideGui;
            minecraft.options.cloudStatus().set(this.originalCloudStatus);
        }
    }

    /** Audited views from the living cavern landscape to Terminal Dogma. */
    private static final class GeoFrontSession
    {
        private static final int INITIAL_SETTLE_TICKS = 180;
        private static final int MAX_CHUNK_WAIT_TICKS = 400;
        private static final int TRACKING_RETRY_TICKS = 40;
        private static final int POST_LOAD_RENDER_TICKS = 20;
        private static final String[] VIEWS = {
                "cavern_overview", "natural_lake", "forest_canopy",
                "nerv_pyramid", "nerv_operations",
                "nerv_support_gallery", "nerv_briefing_room",
                "nerv_medical_support", "nerv_pressure_vestibule",
                "central_dogma_descent", "terminal_dogma",
                "lcl_lake", "lift_terminals"
        };
        private static final int[] LIFT_X = {-28, 0, 28};

        private final BlockPos origin;
        private final Entity originalCamera;
        private final CameraType originalCameraType;
        private final boolean originalHideGui;
        private final CloudStatus originalCloudStatus;
        private ArmorStand camera;
        private int settleTicks = INITIAL_SETTLE_TICKS;
        private int view;
        private boolean positioned;
        private final boolean[] evidence = new boolean[VIEWS.length];
        private int chunkWaitTicks;

        private int renderSettleTicks;
        GeoFrontSession(BlockPos origin, Minecraft minecraft)
        {
            this.origin = origin.immutable();
            this.originalCamera = minecraft.getCameraEntity();
            this.originalCameraType = minecraft.options.getCameraType();
            this.originalHideGui = minecraft.options.hideGui;
            this.originalCloudStatus = minecraft.options.cloudStatus().get();
            ProjectSeele.LOGGER.info(
                    "GeoFront visual capture batch {} at {}", CAPTURE_BATCH, this.origin);
        }

        boolean tick(Minecraft minecraft)
        {
            if (minecraft.level == null || minecraft.player == null)
            {
                return false;
            }
            if (!this.positioned)
            {
                SeeleNetwork.CHANNEL.sendToServer(
                        new ServerboundGeoFrontCameraPacket(this.view));
                this.position(minecraft);
                this.positioned = true;
                return true;
            }
            this.maintainCamera(minecraft);
            if (this.settleTicks-- > 0)
            {
                return true;
            }
            if (!this.viewChunksLoaded(minecraft)
                    && this.chunkWaitTicks < MAX_CHUNK_WAIT_TICKS)
            {
                this.chunkWaitTicks++;
                if (this.chunkWaitTicks % TRACKING_RETRY_TICKS == 1)
                {
                    SeeleNetwork.CHANNEL.sendToServer(
                            new ServerboundGeoFrontCameraPacket(this.view));
                    ProjectSeele.LOGGER.info(
                            "Waiting for GeoFront view chunks: view={} waited={}/{}",
                            VIEWS[this.view], this.chunkWaitTicks,
                            MAX_CHUNK_WAIT_TICKS);
                }
                return true;
            }
            this.chunkWaitTicks = 0;
            if (this.renderSettleTicks++ < POST_LOAD_RENDER_TICKS)
            {
                return true;
            }
            this.renderSettleTicks = 0;
            this.evidence[this.view] = this.auditView(minecraft);
            this.capture(minecraft);
            this.view++;
            if (this.view >= VIEWS.length)
            {
                ProjectSeele.LOGGER.info(
                        "GeoFront visual matrix finished: {} audited map views captured",
                        VIEWS.length);
                boolean valid = true;
                StringBuilder summary = new StringBuilder();
                for (int index = 0; index < VIEWS.length; index++)
                {
                    valid &= this.evidence[index];
                    if (index > 0)
                    {
                        summary.append(' ');
                    }
                    summary.append(VIEWS[index]).append('=')
                            .append(this.evidence[index]);
                }
                ProjectSeele.LOGGER.info(
                        "GeoFront per-view evidence: {} valid={}", summary, valid);
                if (!valid)
                {
                    ProjectSeele.LOGGER.error(
                            "VISUAL GEOFRONT INVALID: a visible camera landmark was missing");
                }
                if (Boolean.getBoolean("projectseele.visualCapture"))
                {
                    shutdownTicks = 30;
                }
                return false;
            }
            this.positioned = false;
            this.chunkWaitTicks = 0;
            this.renderSettleTicks = 0;
            // Chunk delivery follows the real server player. Give each new
            // tracking midpoint four seconds instead of capturing a void
            // horizon one second after the teleport packet.
            this.settleTicks = 80;
            return true;
        }

        private boolean viewChunksLoaded(Minecraft minecraft)
        {
            if (this.camera == null
                    || !minecraft.level.hasChunkAt(this.camera.blockPosition()))
            {
                return false;
            }
            if (VIEWS[this.view].equals("lift_terminals"))
            {
                for (int x : LIFT_X)
                {
                    if (!minecraft.level.hasChunkAt(
                            this.origin.offset(x, 1, -76)))
                    {
                        return false;
                    }
                }
                return true;
            }
            BlockPos landmark = switch (VIEWS[this.view])
            {
                case "natural_lake" -> this.origin.offset(-125, 0, -125);
                case "forest_canopy" -> this.origin.offset(-105, 4, 80);
                case "nerv_pyramid" -> this.origin.offset(0,
                        GeoFrontBuilder.PYRAMID_APEX_Y + 1,
                        GeoFrontBuilder.PYRAMID_CENTRE_Z);
                case "nerv_operations" -> this.origin.offset(29, 57, 97);
                case "nerv_support_gallery" ->
                        this.origin.offset(1, -5, 95);
                case "nerv_briefing_room" ->
                        this.origin.offset(-43, -4, 82);
                case "nerv_medical_support" ->
                        this.origin.offset(39, -4, 82);
                case "nerv_pressure_vestibule" ->
                        this.origin.offset(-1, -21, -34);
                case "central_dogma_descent" ->
                        this.origin.offset(42, -94, -27);
                case "terminal_dogma" -> this.origin.offset(0, -139, 0);
                case "lcl_lake" -> this.origin.offset(48, 1, 0);
                default -> this.origin.offset(-128, 0, -96);
            };
            return minecraft.level.hasChunkAt(landmark);
        }

        private boolean auditView(Minecraft minecraft)
        {
            boolean dimension = minecraft.level.dimension().location().equals(
                    new ResourceLocation(ProjectSeele.MODID, "geofront"));
            boolean landmark;
            switch (VIEWS[this.view])
            {
                case "natural_lake" -> landmark = minecraft.level.getFluidState(
                        this.origin.offset(-125, 0, -125)).is(Fluids.WATER);
                case "forest_canopy" ->
                {
                    landmark = false;
                    for (int y = -2; y <= 8; y++)
                    {
                        landmark |= minecraft.level.getBlockState(
                                this.origin.offset(-105, y, 80))
                                .is(Blocks.STRIPPED_DARK_OAK_LOG);
                    }
                }
                case "nerv_pyramid" -> landmark = minecraft.level.getBlockState(
                        this.origin.offset(0, GeoFrontBuilder.PYRAMID_APEX_Y + 1,
                                GeoFrontBuilder.PYRAMID_CENTRE_Z)).is(Blocks.BEACON);
                case "nerv_operations" -> landmark = minecraft.level.getBlockState(
                        this.origin.offset(29, 57, 97)).is(Blocks.LODESTONE);
                case "nerv_support_gallery" -> landmark =
                        minecraft.level.getBlockState(
                                this.origin.offset(1, -5, 95))
                                .is(Blocks.POLISHED_DEEPSLATE)
                                && minecraft.level.getBlockState(
                                this.origin.offset(0, -2, 98))
                                .is(Blocks.GRAY_STAINED_GLASS)
                                && minecraft.level.getBlockState(
                                this.origin.offset(-18, -4, 94)).isAir()
                                && minecraft.level.getBlockState(
                                this.origin.offset(18, -4, 94)).isAir();
                case "nerv_briefing_room" -> landmark =
                        minecraft.level.getBlockState(
                                this.origin.offset(-43, -4, 82))
                                .is(Blocks.SEA_LANTERN)
                                && minecraft.level.getBlockState(
                                this.origin.offset(-43, 0, 71))
                                .is(Blocks.RED_STAINED_GLASS);
                case "nerv_medical_support" -> landmark =
                        minecraft.level.getBlockState(
                                this.origin.offset(39, -4, 82))
                                .is(Blocks.SMOOTH_QUARTZ_SLAB)
                                && minecraft.level.getBlockState(
                                this.origin.offset(36, -3, 82))
                                .is(Blocks.SEA_LANTERN);                case "nerv_pressure_vestibule" -> landmark =
                        minecraft.level.getBlockState(
                                this.origin.offset(-1, -21, -34))
                                .is(Blocks.POLISHED_BLACKSTONE)
                                && minecraft.level.getBlockState(
                                this.origin.offset(-1, -20, -33)).isAir()
                                && minecraft.level.getBlockState(
                                this.origin.offset(-1, -18, -42))
                                .is(Blocks.ORANGE_STAINED_GLASS);
                case "central_dogma_descent" -> landmark = minecraft.level.getBlockState(
                        this.origin.offset(42, -94, -27)).is(Blocks.LADDER)
                        && !minecraft.level.getBlockState(
                        this.origin.offset(24, -123, -10)).isAir();
                case "terminal_dogma" -> landmark = minecraft.level.getFluidState(
                        this.origin.offset(0, -139, 0)).getFluidType()
                        == com.projectseele.registry.ModFluids.LCL_TYPE.get()
                        && minecraft.level.getBlockState(
                        this.origin.offset(0, -114, -25)).is(Blocks.REDSTONE_BLOCK);
                case "lcl_lake" -> landmark = minecraft.level.getFluidState(
                        this.origin.offset(48, 1, 0)).getFluidType()
                        == com.projectseele.registry.ModFluids.LCL_TYPE.get();
                case "lift_terminals" ->
                {
                    int terminals = 0;
                    for (int x : LIFT_X)
                    {
                        if (minecraft.level.getBlockState(
                                this.origin.offset(x, 1, -76)).is(Blocks.LODESTONE))
                        {
                            terminals++;
                        }
                    }
                    landmark = terminals == 3;
                }
                default -> landmark = minecraft.level.getFluidState(
                        this.origin.offset(-128, 0, -96)).is(Fluids.WATER);
            }
            boolean valid = dimension && landmark;
            ProjectSeele.LOGGER.info(
                    "GeoFront visual view evidence: view={} dimension={} landmark={} valid={}",
                    VIEWS[this.view], dimension, landmark, valid);
            return valid;
        }

        private void audit(Minecraft minecraft)
        {
            boolean floor = minecraft.level.getBlockState(this.origin.offset(
                    150, 0, GeoFrontBuilder.CAVERN_CENTRE_Z)).is(Blocks.GRASS_BLOCK);
            BlockPos sphereCentre = GeoFrontBuilder.cavernCentre(this.origin);
            BlockPos canopySample = sphereCentre.offset(64, 248, 0);
            ResourceLocation canopyId = BuiltInRegistries.BLOCK.getKey(
                    minecraft.level.getBlockState(canopySample).getBlock());
            boolean skyweaveCanopy = canopyId.equals(
                    new ResourceLocation("ars_nouveau", "sky_block"));
            boolean lclLake = minecraft.level.getFluidState(
                    this.origin.offset(48, 1, 0)).getFluidType()
                    == com.projectseele.registry.ModFluids.LCL_TYPE.get();
            boolean naturalLake = minecraft.level.getFluidState(
                    this.origin.offset(-125, 0, -125)).is(Fluids.WATER);
            boolean pyramid = minecraft.level.getBlockState(this.origin.offset(
                    -GeoFrontBuilder.PYRAMID_BASE_HALF_X,
                    GeoFrontBuilder.PYRAMID_BASE_Y,
                    GeoFrontBuilder.PYRAMID_BASE_CENTRE_Z
                            - GeoFrontBuilder.PYRAMID_BASE_HALF_Z))
                    .is(Blocks.CHISELED_DEEPSLATE)
                    && minecraft.level.getBlockState(this.origin.offset(
                    0, GeoFrontBuilder.PYRAMID_APEX_Y + 1,
                    GeoFrontBuilder.PYRAMID_CENTRE_Z)).is(Blocks.BEACON);
            boolean legacyInnerGone = minecraft.level.getBlockState(
                    this.origin.offset(34, 2, 0)).isAir()
                    && minecraft.level.getBlockState(
                    this.origin.offset(0, 2, -34)).isAir();
            var oldSun = minecraft.level.getBlockState(this.origin.offset(0, 88, 0));
            boolean artificialSunGone = !oldSun.is(Blocks.SEA_LANTERN)
                    && !oldSun.is(Blocks.YELLOW_STAINED_GLASS)
                    && !oldSun.is(Blocks.LIGHT);
            var road = minecraft.level.getBlockState(this.origin.offset(100, 0, 74));
            boolean serviceRoad = road.is(Blocks.BLACK_CONCRETE)
                    || road.is(Blocks.LIGHT_GRAY_CONCRETE);
            boolean forest = false;
            for (int x : new int[] {-105, 105})
            {
                for (int y = -2; y <= 6; y++)
                {
                    forest |= minecraft.level.getBlockState(
                            this.origin.offset(x, y, 80)).is(Blocks.STRIPPED_DARK_OAK_LOG);
                }
            }
            int lifts = 0;
            int gantries = 0;
            for (int x : LIFT_X)
            {
                if (minecraft.level.getBlockState(
                        this.origin.offset(x, 1, -76)).is(Blocks.LODESTONE))
                {
                    lifts++;
                }
                if (minecraft.level.getBlockState(
                        this.origin.offset(x, 27, -63)).is(Blocks.LADDER)
                        && !minecraft.level.getBlockState(
                                this.origin.offset(x, 27, -70)).isAir())
                {
                    gantries++;
                }
            }
            boolean bridge = minecraft.level.getBlockState(
                    this.origin.offset(0, 2, 70)).is(Blocks.IRON_BLOCK);
            boolean observation = minecraft.level.getBlockState(
                    this.origin.offset(0, 24, 100)).is(Blocks.LODESTONE);
            boolean operations = minecraft.level.getBlockState(
                    this.origin.offset(0, 8, 0)).is(Blocks.BEACON);
            boolean tacticalDisplay = minecraft.level.getBlockState(
                    this.origin.offset(0, 11, -20)).is(Blocks.RED_STAINED_GLASS);
            boolean accessStairs = minecraft.level.getBlockState(
                    this.origin.offset(-13, 2, 22)).is(Blocks.SMOOTH_QUARTZ_STAIRS);
            boolean centralDogma = minecraft.level.getBlockState(
                    this.origin.offset(42, -30, -27)).is(Blocks.LADDER)
                    && !minecraft.level.getBlockState(
                            this.origin.offset(24, -59, -10)).isAir();
            boolean terminalDogma = minecraft.level.getFluidState(
                    this.origin.offset(0, -75, 0)).getFluidType()
                    == com.projectseele.registry.ModFluids.LCL_TYPE.get()
                    && minecraft.level.getBlockState(
                            this.origin.offset(0, -50, -25)).is(Blocks.REDSTONE_BLOCK)
                    && minecraft.level.getBlockState(
                            this.origin.offset(20, -50, -23)).is(Blocks.RED_STAINED_GLASS)
                    && minecraft.level.getBlockState(
                            this.origin.offset(0, -59, 22)).is(Blocks.LODESTONE);
            int transitLinks = 0;
            for (int x : LIFT_X)
            {
                if (!minecraft.level.getBlockState(
                        this.origin.offset(x, 1, -50)).isAir()
                        && minecraft.level.getBlockState(
                                this.origin.offset(x, 6, -50)).is(Blocks.IRON_BLOCK))
                {
                    transitLinks++;
                }
            }
            boolean valid = floor && skyweaveCanopy && lclLake && naturalLake
                    && forest && serviceRoad && pyramid && legacyInnerGone
                    && artificialSunGone
                    && lifts == 3 && gantries == 3 && bridge && observation
                    && operations && tacticalDisplay && accessStairs
                    && transitLinks == 3 && centralDogma && terminalDogma;
            ProjectSeele.LOGGER.info(
                    "GeoFront visual evidence: floor={} skyweaveCanopy={} realSky={} "
                            + "lclLake={} naturalLake={} forest={} serviceRoad={} "
                            + "nervPyramid={} legacyInnerGone={} artificialSunGone={} "
                            + "lifts={}/3 gantries={}/3 "
                            + "commandBridge={} observation={} operations={} display={} "
                            + "stairs={} transit={}/3 centralDogma={} terminalDogma={} valid={}",
                    floor, skyweaveCanopy, skyweaveCanopy, lclLake, naturalLake,
                    forest, serviceRoad, pyramid, legacyInnerGone, artificialSunGone,
                    lifts, gantries,
                    bridge, observation, operations, tacticalDisplay,
                    accessStairs, transitLinks, centralDogma, terminalDogma,
                    valid);
            if (!valid)
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL GEOFRONT INVALID: one or more cavern landmarks are missing");
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
                    throw new IllegalStateException("GeoFront visual camera creation failed");
                }
                this.camera.setInvisible(true);
                this.camera.setNoGravity(true);
            }
            this.maintainCamera(minecraft);
            minecraft.setCameraEntity(this.camera);
        }

        private void maintainCamera(Minecraft minecraft)
        {
            Vec3 base = Vec3.atLowerCornerOf(this.origin);
            Vec3 target;
            Vec3 cameraPos;
            switch (VIEWS[this.view])
            {
                case "nerv_pyramid" ->
                {
                    // The command module now sits completely inside a long,
                    // full-height pyramid. A far north-west cavern camera
                    // keeps the base, shoulder and apex in one frame while
                    // avoiding the three launch terminals as foreground walls.
                    cameraPos = base.add(-86.0D, 50.0D, -69.0D);
                    target = base.add(0.0D, 30.0D, 31.0D);
                }
                case "natural_lake" ->
                {
                    cameraPos = base.add(-162.0D, 28.0D, -90.0D);
                    target = base.add(-125.0D, 1.0D, -125.0D);
                }
                case "forest_canopy" ->
                {
                    cameraPos = base.add(-70.0D, 32.0D, 125.0D);
                    target = base.add(-105.0D, 7.0D, 80.0D);
                }
                case "nerv_operations" ->
                {
                    // The live panels sit at z=58 in the imported bridge.
                    // Frame them directly instead of treating the whole
                    // 129-block command module as a distant landmark.
                    // Keep the complete five-screen wall and all seven
                    // operator stations inside the horizontal FOV.  The
                    // former close, left-offset camera clipped BATTLE ABORT.
                    cameraPos = base.add(0.0D, 23.0D, 74.0D);
                    target = base.add(0.0D, 21.0D, 57.0D);
                }
                case "nerv_support_gallery" ->
                {
                    // The downloaded bridge's three north exits now open into
                    // a sealed observation gallery with furnished support rooms
                    // on both sides. Shoot diagonally so the real doorways and
                    // pressure-safe glass boundary are visible together.
                    cameraPos = base.add(-12.0D, -1.0D, 97.0D);
                    target = base.add(18.0D, -1.0D, 95.0D);
                }
                case "nerv_briefing_room" ->
                {
                    cameraPos = base.add(-49.0D, 0.0D, 91.0D);
                    target = base.add(-43.0D, -2.0D, 82.0D);
                }
                case "nerv_medical_support" ->
                {
                    cameraPos = base.add(49.0D, 0.0D, 91.0D);
                    target = base.add(40.0D, -2.0D, 82.0D);
                }
                case "nerv_pressure_vestibule" ->
                {
                    // Prove the source module's only south service exit lands
                    // on a lit floor inside a sealed vestibule, never a cliff.
                    cameraPos = base.add(-1.0D, -17.0D, -39.0D);
                    target = base.add(-1.0D, -18.5D, -33.0D);
                }
                case "central_dogma_descent" ->
                {
                    // Stand inside the shaft beside the widened landing
                    // apertures and look down the continuous ladder column.
                    cameraPos = base.add(42.0D, -5.0D, -26.0D);
                    target = base.add(42.0D, -112.0D, -27.0D);
                }
                case "terminal_dogma" ->
                {
                    // The south observation balcony frames the complete red
                    // cross, sealed giant, spear and dedicated LCL pool.
                    // A slight west offset keeps the giant centred while the
                    // east-entering forked spear remains visibly diagonal.
                    cameraPos = base.add(-10.0D, -118.0D, 21.0D);
                    target = base.add(0.0D, -116.0D, -22.0D);
                }
                case "lcl_lake" ->
                {
                    cameraPos = base.add(-82.0D, 17.0D, 12.0D);
                    target = base.add(0.0D, 5.0D, 0.0D);
                }
                case "lift_terminals" ->
                {
                    // The rear/north side is the solid guide-wall face. View
                    // from the south service gantries so all three bays and
                    // entry-plug decks share one unobstructed frame.
                    cameraPos = base.add(0.0D, 18.0D, -38.0D);
                    target = base.add(0.0D, 14.0D, -76.0D);
                }
                default ->
                {
                    cameraPos = base.add(-128.0D, 55.0D, -96.0D);
                    target = base.add(0.0D, 48.0D, -10.0D);
                }
            }
            this.camera.setPos(cameraPos.x,
                    cameraPos.y - this.camera.getEyeHeight(), cameraPos.z);
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
                String filename = "geofront_" + VIEWS[this.view] + ".png";
                Screenshot.grab(minecraft.gameDirectory,
                        "projectseele_visual/" + CAPTURE_BATCH + "/" + filename,
                        minecraft.getMainRenderTarget(), message -> ProjectSeele.LOGGER.info(
                                "GeoFront visual capture {}/{}: {}",
                                CAPTURE_BATCH, filename, message.getString()));
            }
            catch (Exception exception)
            {
                ProjectSeele.LOGGER.error("GeoFront visual screenshot failed", exception);
            }
        }

        void restore(Minecraft minecraft)
        {
            SeeleNetwork.CHANNEL.sendToServer(
                    new ServerboundGeoFrontCameraPacket(-1));
            minecraft.setCameraEntity(
                    this.originalCamera != null ? this.originalCamera : minecraft.player);
            minecraft.options.setCameraType(this.originalCameraType);
            minecraft.options.hideGui = this.originalHideGui;
            minecraft.options.cloudStatus().set(this.originalCloudStatus);
        }
    }

    /** Four audited views of the connected launch apron and surface city. */
    private static final class Tokyo3Session
    {
        private static final int INITIAL_SETTLE_TICKS = 150;
        private static final String[] VIEWS = {
                "skyline_overview", "sortie_street", "power_grid", "battle_plaza"
        };
        private static final int[] LOT_CENTRES =
                {-160, -120, -80, -40, 0, 40, 80, 120, 160};
        private static final int[][] ROAD_POINTS = {
                {-180, -180}, {-180, 180}, {180, -180}, {180, 180},
                {-140, -180}, {140, 180}, {-180, 140}, {180, -140},
        };
        private static final int[][] PYLONS = {
                {-180, -160}, {-180, 0}, {-180, 160},
                {180, -160}, {180, 0}, {180, 160},
        };

        private final BlockPos origin;
        private final Entity originalCamera;
        private final CameraType originalCameraType;
        private final boolean originalHideGui;
        private final CloudStatus originalCloudStatus;
        private final LocalVisualAssetFingerprint.Fingerprint unit00Fingerprint;
        private final LocalVisualAssetFingerprint.Fingerprint unit01Fingerprint;
        private final LocalVisualAssetFingerprint.Fingerprint unit02Fingerprint;
        private final boolean battle;
        private ArmorStand camera;
        private int settleTicks = INITIAL_SETTLE_TICKS;
        private int view;
        private boolean positioned;
        private boolean audited;

        Tokyo3Session(BlockPos origin, Minecraft minecraft, boolean battle)
        {
            this.origin = origin.immutable();
            this.originalCamera = minecraft.getCameraEntity();
            this.originalCameraType = minecraft.options.getCameraType();
            this.originalHideGui = minecraft.options.hideGui;
            this.originalCloudStatus = minecraft.options.cloudStatus().get();
            this.battle = battle;
            this.unit00Fingerprint = EvaUnit01Renderer.visualFingerprintForVariant(
                    EvaUnit01Entity.UNIT_00);
            this.unit01Fingerprint = EvaUnit01Renderer.visualFingerprintForVariant(
                    EvaUnit01Entity.UNIT_01);
            this.unit02Fingerprint = EvaUnit01Renderer.visualFingerprintForVariant(
                    EvaUnit01Entity.UNIT_02);
            ProjectSeele.LOGGER.info(
                    "Tokyo-3 visual capture batch {} at {} battle={} uses unit00={} unit01={} unit02={}",
                    CAPTURE_BATCH, this.origin, this.battle,
                    this.unit00Fingerprint.compactTag(),
                    this.unit01Fingerprint.compactTag(),
                    this.unit02Fingerprint.compactTag());
        }

        boolean tick(Minecraft minecraft)
        {
            if (minecraft.level == null || minecraft.player == null)
            {
                return false;
            }
            if (LocalVisualAssetFingerprint.isStrictMode()
                    && (!this.unit00Fingerprint.valid()
                    || !this.unit01Fingerprint.valid()
                    || !this.unit02Fingerprint.valid()))
            {
                ProjectSeele.LOGGER.error(
                        "Strict Tokyo-3 capture refused: unit00={} unit01={} unit02={}",
                        this.unit00Fingerprint.description(),
                        this.unit01Fingerprint.description(),
                        this.unit02Fingerprint.description());
                if (Boolean.getBoolean("projectseele.visualCapture"))
                {
                    shutdownTicks = 20;
                }
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
            if (this.view >= VIEWS.length)
            {
                ProjectSeele.LOGGER.info(
                        "Tokyo-3 visual matrix finished: four audited city views captured");
                if (Boolean.getBoolean("projectseele.visualCapture"))
                {
                    shutdownTicks = 30;
                }
                return false;
            }
            this.positioned = false;
            this.settleTicks = 16;
            return true;
        }

        private void audit(Minecraft minecraft)
        {
            boolean imported = LocalMapAssetLoader.importedTokyo3MarkerPresent(
                    minecraft.level, this.origin);
            int privateSkyscrapers = LocalMapAssetLoader.inspectTokyo3Skyscrapers(
                    minecraft.level, this.origin);
            int roads = 0;
            for (int[] point : ROAD_POINTS)
            {
                var state = minecraft.level.getBlockState(
                        this.origin.offset(point[0], 0, point[1]));
                if (state.is(Blocks.BLACK_CONCRETE) || state.is(Blocks.GRAY_CONCRETE)
                        || state.is(Blocks.YELLOW_CONCRETE)
                        || state.is(Blocks.LIGHT_GRAY_CONCRETE))
                {
                    roads++;
                }
            }

            int towers = 0;
            for (int x : LOT_CENTRES)
            {
                for (int z : LOT_CENTRES)
                {
                    if (Math.abs(x) <= 40 && Math.abs(z) <= 40
                            || (x == 0 && z == -80)
                            || (x == 80 && z == 0)
                            || (x == 0 && z == 80)
                            || (x == -120 && z == -80)
                            || (x == 120 && z == -80)
                            || (x == 120 && z == 80))
                    {
                        continue;
                    }
                    if (minecraft.level.getBlockState(
                            this.origin.offset(x, towerHeight(x, z) + 1, z))
                            .is(Blocks.REDSTONE_LAMP))
                    {
                        towers++;
                    }
                }
            }

            int pylons = 0;
            for (int[] pylon : PYLONS)
            {
                if (minecraft.level.getBlockState(
                        this.origin.offset(pylon[0], 28, pylon[1]))
                        .is(Blocks.IRON_BLOCK))
                {
                    pylons++;
                }
            }
            AABB cages = new AABB(this.origin).inflate(96.0D, 96.0D, 96.0D);
            var units = minecraft.level.getEntitiesOfClass(
                    EvaUnit01Entity.class, cages, Entity::isAlive);
            int ramielCount = minecraft.level.getEntitiesOfClass(
                    RamielEntity.class,
                    new AABB(this.origin).inflate(192.0D, 128.0D, 192.0D),
                    Entity::isAlive).size();
            boolean variants = units.stream().anyMatch(
                    unit -> unit.getUnitVariant() == EvaUnit01Entity.UNIT_00)
                    && units.stream().anyMatch(
                    unit -> unit.getUnitVariant() == EvaUnit01Entity.UNIT_01)
                    && units.stream().anyMatch(
                    unit -> unit.getUnitVariant() == EvaUnit01Entity.UNIT_02);
            boolean battleBeacon = minecraft.level.getBlockState(
                    this.origin.offset(0, 1, 80)).is(Blocks.BEACON);
            boolean observation = minecraft.level.getBlockState(
                    this.origin.offset(0, 38, 216)).is(Blocks.LODESTONE);
            boolean foundation = minecraft.level.getBlockState(
                    this.origin.offset(224, -4, 0)).is(Blocks.DEEPSLATE_BRICKS);
            int surfaceBeds = 0;
            for (IntegratedNervMapBuilder.LiftLink lift
                    : IntegratedNervMapBuilder.liftLinks())
            {
                if (minecraft.level.getBlockState(lift.surfaceBed())
                        .is(Blocks.LODESTONE))
                {
                    surfaceBeds++;
                }
            }
            boolean towerState = this.battle ? towers == 0 : towers == 66;
            boolean battleState = !this.battle || ramielCount == 1;
            boolean generatedCity = roads == 8 && towerState && pylons == 6
                    && battleBeacon && observation && foundation;
            boolean privateAssets = !imported || privateSkyscrapers == 3;
            boolean cityGeometry = generatedCity && privateAssets
                    && surfaceBeds == 3;
            boolean valid = cityGeometry && battleState
                    && units.size() == 3 && variants
                    && this.unit00Fingerprint.valid()
                    && this.unit01Fingerprint.valid()
                    && this.unit02Fingerprint.valid();
            ProjectSeele.LOGGER.info(
                    "Tokyo-3 visual evidence: battle={} ramiel={} imported={} skyscrapers={}/3 "
                            + "surfaceBeds={}/3 roads={}/8 towers={}/66 pylons={}/6 "
                            + "units={} variants00/01/02={} battleBeacon={} "
                            + "observation={} foundation={} valid={}",
                    this.battle, ramielCount, imported, privateSkyscrapers, surfaceBeds,
                    roads, towers, pylons, units.size(), variants,
                    battleBeacon, observation, foundation, valid);
            if (!valid)
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL TOKYO3 INVALID: city/battle state, three launch EVAs, "
                                + "or required high-detail model fingerprints are incomplete");
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
                    throw new IllegalStateException(
                            "Tokyo-3 visual camera creation failed");
                }
                this.camera.setInvisible(true);
                this.camera.setNoGravity(true);
            }
            this.maintainCamera(minecraft);
            minecraft.setCameraEntity(this.camera);
        }

        private void maintainCamera(Minecraft minecraft)
        {
            // Legacy source level time can arrive one packet late after the
            // dimension switch. Only the unattended review client is pinned
            // to noon and clear weather; ordinary play keeps the natural
            // day/night and weather cycle.
            minecraft.level.setDayTime(6000L);
            minecraft.level.setRainLevel(0.0F);
            minecraft.level.setThunderLevel(0.0F);
            Vec3 base = Vec3.atLowerCornerOf(this.origin);
            Vec3 target;
            Vec3 cameraPos;
            if (this.battle)
            {
                switch (VIEWS[this.view])
                {
                    case "sortie_street" ->
                    {
                        cameraPos = base.add(-58.0D, 30.0D, 142.0D);
                        target = base.add(0.0D, 36.0D, 80.0D);
                    }
                    case "power_grid" ->
                    {
                        cameraPos = base.add(92.0D, 62.0D, 146.0D);
                        target = base.add(0.0D, 38.0D, 72.0D);
                    }
                    case "battle_plaza" ->
                    {
                        cameraPos = base.add(-30.0D, 48.0D, 124.0D);
                        target = base.add(0.0D, 46.0D, 80.0D);
                    }
                    default ->
                    {
                        cameraPos = base.add(0.0D, 64.0D, 158.0D);
                        target = base.add(0.0D, 38.0D, 72.0D);
                    }
                }
            }
            else switch (VIEWS[this.view])
            {
                case "sortie_street" ->
                {
                    cameraPos = base.add(0.0D, 11.0D, 78.0D);
                    target = base.add(0.0D, 12.0D, 6.0D);
                }
                case "power_grid" ->
                {
                    cameraPos = base.add(-138.0D, 44.0D, 35.0D);
                    target = base.add(-88.0D, 18.0D, 0.0D);
                }
                case "battle_plaza" ->
                {
                    cameraPos = base.add(-22.0D, 52.0D, 128.0D);
                    target = base.add(0.0D, 2.0D, 80.0D);
                }
                default ->
                {
                    cameraPos = base.add(0.0D, 70.0D, 145.0D);
                    target = base.add(0.0D, 18.0D, 0.0D);
                }
            }
            this.camera.setPos(cameraPos.x,
                    cameraPos.y - this.camera.getEyeHeight(), cameraPos.z);
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
                String prefix = this.battle ? "tokyo3_battle_" : "tokyo3_";
                String filename = prefix + VIEWS[this.view] + ".png";
                Screenshot.grab(minecraft.gameDirectory,
                        "projectseele_visual/" + CAPTURE_BATCH + "/" + filename,
                        minecraft.getMainRenderTarget(), message -> ProjectSeele.LOGGER.info(
                                "Tokyo-3 visual capture {}/{}: {}",
                                CAPTURE_BATCH, filename, message.getString()));
            }
            catch (Exception exception)
            {
                ProjectSeele.LOGGER.error(
                        "Tokyo-3 visual screenshot failed", exception);
            }
        }

        void restore(Minecraft minecraft)
        {
            minecraft.setCameraEntity(
                    this.originalCamera != null ? this.originalCamera : minecraft.player);
            minecraft.options.setCameraType(this.originalCameraType);
            minecraft.options.hideGui = this.originalHideGui;
            minecraft.options.cloudStatus().set(this.originalCloudStatus);
        }

        private static int towerHeight(int x, int z)
        {
            int gridX = x / 40;
            int gridZ = z / 40;
            return 22 + Math.floorMod(gridX * 31 + gridZ * 17, 6) * 4;
        }
    }

    /** Four synchronized skyline frames proving the complete tower travel cycle. */
    private static final class Tokyo3RetractionSession
    {
        private static final int MAX_DEPTH =
                ThirdTokyoSurfaceBuilder.maximumRetractionDepth();
        private static final int MID_DEPTH = 21;
        private static final int REQUIRED_STABLE_TICKS = 12;
        private static final int TIMEOUT_TICKS = 15000;
        private static final int[] LOT_CENTRES =
                {-160, -120, -80, -40, 0, 40, 80, 120, 160};
        private static final String[] STAGES = {
                "deployed", "mid_descent", "fully_retracted", "restored"
        };
        private static final int[] DEPTHS = {0, MID_DEPTH, MAX_DEPTH, 0};
        private static final boolean[] EXPECT_ARMED = {false, true, true, false};

        private final BlockPos origin;
        private final Entity originalCamera;
        private final CameraType originalCameraType;
        private final boolean originalHideGui;
        private final CloudStatus originalCloudStatus;
        private ArmorStand camera;
        private int stage;
        private int stableTicks;
        private int totalTicks;

        Tokyo3RetractionSession(BlockPos origin, Minecraft minecraft)
        {
            this.origin = origin.immutable();
            this.originalCamera = minecraft.getCameraEntity();
            this.originalCameraType = minecraft.options.getCameraType();
            this.originalHideGui = minecraft.options.hideGui;
            this.originalCloudStatus = minecraft.options.cloudStatus().get();
            this.position(minecraft);
            ProjectSeele.LOGGER.info(
                    "Tokyo-3 retraction visual batch {} at {}", CAPTURE_BATCH, this.origin);
        }

        boolean tick(Minecraft minecraft)
        {
            if (minecraft.level == null || minecraft.player == null)
            {
                return false;
            }
            this.totalTicks++;
            if (this.totalTicks > TIMEOUT_TICKS)
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL TOKYO3 RETRACTION INVALID: client sequence exceeded {} ticks",
                        TIMEOUT_TICKS);
                if (Boolean.getBoolean("projectseele.visualCapture"))
                {
                    shutdownTicks = 20;
                }
                return false;
            }
            this.maintainCamera(minecraft);
            Audit audit = this.audit(minecraft, DEPTHS[this.stage],
                    EXPECT_ARMED[this.stage]);
            if (!audit.valid())
            {
                this.stableTicks = 0;
                return true;
            }
            if (++this.stableTicks < REQUIRED_STABLE_TICKS)
            {
                return true;
            }

            ProjectSeele.LOGGER.info(
                    "Tokyo-3 retraction visual evidence: stage={} depth={} "
                            + "towerStates={}/66 ceilingStates={}/66 "
                            + "cores={}/66 armed={}/66 valid={}",
                    STAGES[this.stage], DEPTHS[this.stage], audit.towers(),
                    audit.ceiling(), audit.cores(), audit.armed(), audit.valid());
            this.capture(minecraft, STAGES[this.stage]);
            this.stage++;
            this.stableTicks = 0;
            if (this.stage >= STAGES.length)
            {
                ProjectSeele.LOGGER.info(
                        "Tokyo-3 retraction visual matrix finished: deployed, "
                                + "mid-descent, fully retracted and restored captured");
                if (Boolean.getBoolean("projectseele.visualCapture"))
                {
                    shutdownTicks = 30;
                }
                return false;
            }
            return true;
        }

        private Audit audit(Minecraft minecraft, int depth, boolean expectedArmed)
        {
            int towers = 0;
            int ceiling = 0;
            int cores = 0;
            int armed = 0;
            for (int x : LOT_CENTRES)
            {
                for (int z : LOT_CENTRES)
                {
                    if (Math.abs(x) <= 40 && Math.abs(z) <= 40
                            || (x == 0 && z == -80)
                            || (x == 80 && z == 0)
                            || (x == 0 && z == 80)
                            || (x == -120 && z == -80)
                            || (x == 120 && z == -80)
                            || (x == 120 && z == 80))
                    {
                        continue;
                    }
                    int visibleHeight = Math.max(0, towerHeight(x, z) - depth);
                    var signature = minecraft.level.getBlockState(
                            this.origin.offset(x,
                                    visibleHeight > 0 ? visibleHeight + 1 : 0, z));
                    boolean shellClear = minecraft.level.getBlockState(
                            this.origin.offset(x - 12, 1, z)).isAir()
                            && minecraft.level.getBlockState(
                            this.origin.offset(x + 12, 1, z)).isAir()
                            && minecraft.level.getBlockState(
                            this.origin.offset(x, 1, z - 12)).isAir()
                            && minecraft.level.getBlockState(
                            this.origin.offset(x, 1, z + 12)).isAir();
                    if (visibleHeight > 0 ? signature.is(Blocks.REDSTONE_LAMP)
                            : signature.is(ModBlocks.RETRACTABLE_BUILDING_CORE.get())
                            && shellClear)
                    {
                        towers++;
                    }
                    ThirdTokyoSurfaceBuilder.TowerSpec tower =
                            new ThirdTokyoSurfaceBuilder.TowerSpec(
                                    x, z, towerHeight(x, z), 12, false);
                    int roofY = ThirdTokyoSurfaceBuilder.ceilingRoofRelativeY(tower);
                    int travelDepth = Math.max(tower.height(), -roofY);
                    int ceilingVisible = Math.max(0, Math.min(tower.height(),
                            depth - travelDepth));
                    boolean ceilingSignature = ceilingVisible == 0
                            ? minecraft.level.getBlockState(
                            this.origin.offset(x, roofY, z)).isAir()
                            : minecraft.level.getBlockState(
                            this.origin.offset(x, roofY, z))
                            .is(Blocks.REDSTONE_LAMP)
                            && minecraft.level.getBlockState(this.origin.offset(
                            x, roofY - ceilingVisible - 1, z))
                            .is(Blocks.SEA_LANTERN);
                    if (ceilingSignature)
                    {
                        ceiling++;
                    }
                    var core = minecraft.level.getBlockState(this.origin.offset(x, 0, z));
                    if (core.is(ModBlocks.RETRACTABLE_BUILDING_CORE.get()))
                    {
                        cores++;
                        if (core.getValue(RetractableBuildingCoreBlock.ARMED))
                        {
                            armed++;
                        }
                    }
                }
            }
            int expectedArmedCount = expectedArmed ? 66 : 0;
            return new Audit(towers, ceiling, cores, armed,
                    towers == 66 && ceiling == 66
                            && cores == 66 && armed == expectedArmedCount);
        }

        private void position(Minecraft minecraft)
        {
            minecraft.options.setCameraType(CameraType.FIRST_PERSON);
            minecraft.options.hideGui = true;
            minecraft.options.cloudStatus().set(CloudStatus.OFF);
            this.camera = EntityType.ARMOR_STAND.create(minecraft.level);
            if (this.camera == null)
            {
                throw new IllegalStateException(
                        "Tokyo-3 retraction camera creation failed");
            }
            this.camera.setInvisible(true);
            this.camera.setNoGravity(true);
            this.maintainCamera(minecraft);
            minecraft.setCameraEntity(this.camera);
        }

        private void maintainCamera(Minecraft minecraft)
        {
            Vec3 base = Vec3.atLowerCornerOf(this.origin);
            Vec3 cameraPos;
            Vec3 target;
            if (this.stage == 2)
            {
                cameraPos = base.add(0.0D, -250.0D, 260.0D);
                target = base.add(0.0D, -180.0D, 0.0D);
            }
            else
            {
                cameraPos = base.add(0.0D, 90.0D, 300.0D);
                target = base.add(0.0D, 18.0D, 0.0D);
            }
            this.camera.setPos(cameraPos.x,
                    cameraPos.y - this.camera.getEyeHeight(), cameraPos.z);
            lookAt(this.camera, cameraPos, target);
            this.camera.xo = this.camera.getX();
            this.camera.yo = this.camera.getY();
            this.camera.zo = this.camera.getZ();
            this.camera.yRotO = this.camera.getYRot();
            this.camera.xRotO = this.camera.getXRot();
            minecraft.setCameraEntity(this.camera);
        }

        private void capture(Minecraft minecraft, String name)
        {
            try
            {
                File batch = new File(minecraft.gameDirectory,
                        "screenshots/projectseele_visual/" + CAPTURE_BATCH);
                Files.createDirectories(batch.toPath());
                String filename = "tokyo3_retraction_" + name + ".png";
                Screenshot.grab(minecraft.gameDirectory,
                        "projectseele_visual/" + CAPTURE_BATCH + "/" + filename,
                        minecraft.getMainRenderTarget(), message -> ProjectSeele.LOGGER.info(
                                "Tokyo-3 retraction visual capture {}/{}: {}",
                                CAPTURE_BATCH, filename, message.getString()));
            }
            catch (Exception exception)
            {
                ProjectSeele.LOGGER.error(
                        "Tokyo-3 retraction visual screenshot failed", exception);
            }
        }

        void restore(Minecraft minecraft)
        {
            minecraft.setCameraEntity(
                    this.originalCamera != null ? this.originalCamera : minecraft.player);
            minecraft.options.setCameraType(this.originalCameraType);
            minecraft.options.hideGui = this.originalHideGui;
            minecraft.options.cloudStatus().set(this.originalCloudStatus);
        }

        private static int towerHeight(int x, int z)
        {
            int gridX = x / 40;
            int gridZ = z / 40;
            return 22 + Math.floorMod(gridX * 31 + gridZ * 17, 6) * 4;
        }

        private record Audit(int towers, int ceiling, int cores, int armed,
                             boolean valid) {}
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
        private final LocalVisualAssetFingerprint.Fingerprint unitFingerprint;
        private final LocalVisualAssetFingerprint.Fingerprint massFingerprint;
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
            this.unitFingerprint = EvaUnit01Renderer.visualFingerprintForVariant(
                    EvaUnit01Entity.UNIT_01);
            this.massFingerprint = LocalVisualAssetFingerprint.inspect("mass_production_eva");
            this.unitMeshTag = this.unitFingerprint.compactTag();
            this.massMeshTag = this.massFingerprint.compactTag();
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
            if (LocalVisualAssetFingerprint.isStrictMode()
                    && (!this.unitFingerprint.valid() || !this.massFingerprint.valid()))
            {
                ProjectSeele.LOGGER.error(
                        "Strict Impact capture refused: unit01={} mass={}",
                        this.unitFingerprint.description(), this.massFingerprint.description());
                if (Boolean.getBoolean("projectseele.visualCapture"))
                {
                    shutdownTicks = 20;
                }
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
            Vec3 frontNormal = TreeOfLifeLayout.frontNormal(this.yaw);
            long facingCount = minecraft.level.getEntitiesOfClass(
                    MassProductionEvaEntity.class, formation, Entity::isAlive).stream()
                    .filter(mass -> Vec3.directionFromRotation(0.0F, mass.getYRot())
                            .dot(frontNormal) > 0.999D)
                    .count();
            long ritualCount = minecraft.level.getEntitiesOfClass(
                    MassProductionEvaEntity.class, formation, Entity::isAlive).stream()
                    .filter(MassProductionEvaEntity::isRitualFormation)
                    .count();
            EvaUnit01Entity crucified = minecraft.level.getEntitiesOfClass(
                    EvaUnit01Entity.class, formation,
                    unit -> unit.isAlive() && unit.getUnitVariant() == EvaUnit01Entity.UNIT_01
                            && unit.isCrucified()).stream().findFirst().orElse(null);
            boolean unitFacingFront = crucified != null
                    && Vec3.directionFromRotation(0.0F, crucified.getYRot())
                    .dot(frontNormal) > 0.999D;
            ProjectSeele.LOGGER.info(
                    "Impact visual evidence: massCount={} massFacingFront={} massRitual={} crucifiedUnit01={} unitFacingFront={} unit01={} mass={}",
                    massCount, facingCount, ritualCount, crucified != null,
                    unitFacingFront,
                    this.unitMeshTag, this.massMeshTag);
            if (massCount != 9 || facingCount != 9 || ritualCount != 9 || crucified == null
                    || !unitFacingFront
                    || !this.unitFingerprint.valid() || !this.massFingerprint.valid())
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
            double frameTop = TreeOfLifeLayout.localY(TreeOfLifeLayout.MALKUTH)
                    + FRAME_TOP_MARGIN;
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

    /**
     * Captures the actual launch-bed state machine rather than freezing an EVA
     * in a synthetic pose. Every frame waits on synchronized entity data, so a
     * missing insertion, stalled countdown or skipped ascent becomes a timeout
     * instead of a falsely green screenshot run.
     */
    private static final class SiloSession
    {
        private static final String[] STAGES = {
                "gantry_rear_socket", "plug_descent_external", "plug_descent_cockpit",
                "hatch_locked", "ascent_mid", "surface_clear"
        };
        private static final int TIMEOUT_TICKS = 420;

        private final int entityId;
        private final Entity originalCamera;
        private final CameraType originalCameraType;
        private final boolean originalHideGui;
        private final float originalYaw;
        private final float originalPitch;
        private final LocalVisualAssetFingerprint.Fingerprint bodyFingerprint;
        private final String modelTag;
        private ArmorStand camera;
        private int stage;
        private int settleTicks;
        private int elapsedTicks;
        private boolean positioned;

        SiloSession(int entityId, Minecraft minecraft)
        {
            this.entityId = entityId;
            this.originalCamera = minecraft.getCameraEntity();
            this.originalCameraType = minecraft.options.getCameraType();
            this.originalHideGui = minecraft.options.hideGui;
            this.originalYaw = minecraft.player.getYRot();
            this.originalPitch = minecraft.player.getXRot();
            Entity entity = minecraft.level.getEntity(entityId);
            int variant = entity instanceof EvaUnit01Entity unit
                    ? unit.getUnitVariant() : EvaUnit01Entity.UNIT_01;
            this.bodyFingerprint = EvaUnit01Renderer.visualFingerprintForVariant(variant);
            this.modelTag = this.bodyFingerprint.compactTag();
            if (!this.bodyFingerprint.valid())
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL SILO CAPTURE INVALID: required high-detail EVA is unavailable: {}",
                        this.bodyFingerprint.description());
            }
            ProjectSeele.LOGGER.info("Launch-silo capture batch {} uses {}",
                    CAPTURE_BATCH, this.modelTag);
        }

        boolean tick(Minecraft minecraft)
        {
            if (minecraft.level == null || minecraft.player == null)
            {
                return false;
            }
            this.elapsedTicks++;
            if (this.elapsedTicks > TIMEOUT_TICKS)
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL SILO CAPTURE INVALID: timed out before stage {}",
                        this.stage < STAGES.length ? STAGES[this.stage] : "complete");
                shutdownTicks = 20;
                return false;
            }
            Entity entity = minecraft.level.getEntity(this.entityId);
            if (!(entity instanceof EvaUnit01Entity unit) || !unit.isAlive())
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL SILO CAPTURE INVALID: launch EVA {} is missing", this.entityId);
                shutdownTicks = 20;
                return false;
            }
            if (LocalVisualAssetFingerprint.isStrictMode() && !this.bodyFingerprint.valid())
            {
                shutdownTicks = 20;
                return false;
            }
            if (this.stage >= STAGES.length)
            {
                shutdownTicks = 20;
                return false;
            }
            if (!this.stageReady(minecraft, unit))
            {
                return true;
            }
            if (!this.positioned)
            {
                this.positioned = true;
                this.settleTicks = this.stage >= 4 ? 2 : 5;
            }
            this.position(minecraft, unit);
            if (this.settleTicks-- > 0)
            {
                return true;
            }
            if (!this.stageReady(minecraft, unit))
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL SILO CAPTURE INVALID: state changed while settling stage {} "
                                + "(phase={} activation={} launchTicks={})",
                        STAGES[this.stage], unit.getLaunchPhase(), unit.getActivationTicks(),
                        unit.getLaunchTicks());
                shutdownTicks = 20;
                return false;
            }
            this.capture(minecraft, unit);
            this.stage++;
            this.positioned = false;
            if (this.stage >= STAGES.length)
            {
                ProjectSeele.LOGGER.info(
                        "Launch-silo visual matrix finished: six synchronized stages captured");
                minecraft.player.displayClientMessage(Component.literal(
                        "Launch-silo capture complete: screenshots/projectseele_visual/"
                                + CAPTURE_BATCH), false);
                shutdownTicks = 20;
                return false;
            }
            return true;
        }

        private boolean stageReady(Minecraft minecraft, EvaUnit01Entity unit)
        {
            int phase = unit.getLaunchPhase();
            int activation = unit.getActivationTicks();
            boolean riding = minecraft.player.getVehicle() == unit;
            return switch (this.stage)
            {
                case 0 -> phase == EvaUnit01Entity.LAUNCH_IDLE && !riding;
                case 1, 2 -> phase == EvaUnit01Entity.LAUNCH_LOCKED
                        && activation > 65 && riding;
                case 3 -> phase == EvaUnit01Entity.LAUNCH_LOCKED
                        && activation > 20 && activation <= 50 && riding;
                case 4 -> phase == EvaUnit01Entity.LAUNCH_ASCENT
                        && unit.getLaunchTicks() >= 8 && unit.getLaunchTicks() <= 23 && riding;
                case 5 -> phase == EvaUnit01Entity.LAUNCH_CLEAR && riding;
                default -> false;
            };
        }

        private void position(Minecraft minecraft, EvaUnit01Entity unit)
        {
            minecraft.options.setCameraType(CameraType.FIRST_PERSON);
            if (this.stage == 2)
            {
                minecraft.options.hideGui = false;
                minecraft.setCameraEntity(minecraft.player);
                minecraft.player.setYRot(unit.getYRot());
                minecraft.player.setYHeadRot(unit.getYRot());
                minecraft.player.setXRot(12.0F);
                minecraft.gui.getChat().clearMessages(false);
                return;
            }
            minecraft.options.hideGui = true;
            if (this.camera == null)
            {
                this.camera = EntityType.ARMOR_STAND.create(minecraft.level);
                if (this.camera == null)
                {
                    throw new IllegalStateException("Launch-silo visual camera creation failed");
                }
                this.camera.setInvisible(true);
                this.camera.setNoGravity(true);
            }
            float yaw = unit.getYRot() * Mth.DEG_TO_RAD;
            Vec3 forward = new Vec3(-Mth.sin(yaw), 0.0D, Mth.cos(yaw));
            Vec3 right = new Vec3(-forward.z, 0.0D, forward.x);
            Vec3 rear = forward.scale(-1.0D);
            Vec3 socket = unit.getEntryPlugSocketPosition();
            Vec3 target;
            Vec3 cameraPos;
            switch (this.stage)
            {
                case 0 ->
                {
                    // Stand on the actual rear gantry and sight through its
                    // personnel doorway at the authoritative socket. The old
                    // 27x16 offset put the camera beyond the seven-block shaft
                    // wall, producing a frame made almost entirely of blocks.
                    target = socket;
                    cameraPos = socket.add(rear.scale(9.0D))
                            .add(right.scale(2.0D)).add(0.0D, 0.4D, 0.0D);
                }
                case 1 ->
                {
                    // Rear-right corner of the 13x13 clear shaft. This keeps
                    // the travelling white capsule, both hatch leaves and the
                    // Unit's upper back in one unobstructed three-quarter view.
                    target = socket.add(0.0D, 1.2D, 0.0D);
                    cameraPos = socket.add(rear.scale(4.0D))
                            .add(right.scale(5.25D)).add(0.0D, 3.8D, 0.0D);
                }
                case 3 ->
                {
                    // Mirror the insertion view after the capsule is internal
                    // so the closed dorsal leaves are legible and no hidden
                    // full-length plug can appear outside the armour.
                    target = socket;
                    cameraPos = socket.add(rear.scale(4.0D))
                            .subtract(right.scale(5.25D)).add(0.0D, 2.8D, 0.0D);
                }
                case 4 ->
                {
                    // Look down through the already-open surface shutter. A
                    // camera beside the moving carrier cannot fit outside the
                    // 8.5-block EVA and inside the 13-block shaft at once.
                    target = unit.position().add(0.0D, 15.0D, 0.0D);
                    cameraPos = unit.position().add(right.scale(5.4D))
                            .add(rear.scale(5.4D)).add(0.0D, 45.0D, 0.0D);
                }
                default ->
                {
                    target = unit.position().add(0.0D, 14.0D, 0.0D);
                    cameraPos = target.add(forward.scale(48.0D))
                            .add(right.scale(22.0D)).add(0.0D, 11.0D, 0.0D);
                }
            }
            this.camera.setPos(cameraPos.x, cameraPos.y - this.camera.getEyeHeight(), cameraPos.z);
            lookAt(this.camera, cameraPos, target);
            this.camera.xo = this.camera.getX();
            this.camera.yo = this.camera.getY();
            this.camera.zo = this.camera.getZ();
            this.camera.yRotO = this.camera.getYRot();
            this.camera.xRotO = this.camera.getXRot();
            minecraft.setCameraEntity(this.camera);
        }

        private void capture(Minecraft minecraft, EvaUnit01Entity unit)
        {
            String stageName = STAGES[this.stage];
            ProjectSeele.LOGGER.info(
                    "Launch-silo visual stage {}: phase={} activation={} launchTicks={} y={}",
                    stageName, unit.getLaunchPhase(), unit.getActivationTicks(),
                    unit.getLaunchTicks(), String.format(java.util.Locale.ROOT, "%.3f", unit.getY()));
            try
            {
                File batch = new File(minecraft.gameDirectory,
                        "screenshots/projectseele_visual/" + CAPTURE_BATCH);
                Files.createDirectories(batch.toPath());
                String filename = "silo_" + this.modelTag + "_" + stageName + ".png";
                Screenshot.grab(minecraft.gameDirectory,
                        "projectseele_visual/" + CAPTURE_BATCH + "/" + filename,
                        minecraft.getMainRenderTarget(), message -> ProjectSeele.LOGGER.info(
                                "Launch-silo visual capture {}/{}: {}",
                                CAPTURE_BATCH, filename, message.getString()));
            }
            catch (Exception exception)
            {
                ProjectSeele.LOGGER.error("Launch-silo visual screenshot failed", exception);
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
        private final boolean originalUseDown;
        private final float originalYaw;
        private final float originalPitch;
        private final String bodyModelTag;
        private final String modelTag;
        private final LocalVisualAssetFingerprint.Fingerprint bodyFingerprint;
        private final String unitName;
        private final String[] views;
        private final boolean massSubject;
        private ArmorStand camera;
        private int view;
        private int settleTicks;
        private boolean positioned;
        private boolean poseAudited;
        private boolean liveTriggerSent;
        private double liveActionStartY = Double.NaN;
        private float referenceYaw = Float.NaN;

        Session(int entityId, int pose, Minecraft minecraft)
        {
            this.entityId = entityId;
            this.requestedPose = pose;
            this.originalCamera = minecraft.getCameraEntity();
            this.originalCameraType = minecraft.options.getCameraType();
            this.originalHideGui = minecraft.options.hideGui;
            this.originalUseDown = minecraft.options.keyUse.isDown();
            this.originalYaw = minecraft.player.getYRot();
            this.originalPitch = minecraft.player.getXRot();
            Entity visualEntity = minecraft.level == null ? null : minecraft.level.getEntity(entityId);
            this.massSubject = visualEntity instanceof MassProductionEvaEntity;
            this.poseName = this.massSubject
                    ? MassProductionEvaEntity.visualPoseName(pose) : poseName(pose);
            this.views = this.massSubject ? MASS_VIEWS
                    : this.poseName.equals("live_jump") ? LIVE_JUMP_VIEWS
                    : this.isLiveAttack() ? LIVE_ATTACK_VIEWS : VIEWS;
            int variant = visualEntity instanceof EvaUnit01Entity eva
                    ? eva.getUnitVariant() : EvaUnit01Entity.UNIT_01;
            this.unitName = this.massSubject ? "mass" : switch (variant)
            {
                case EvaUnit01Entity.UNIT_00 -> "unit00";
                case EvaUnit01Entity.UNIT_02 -> "unit02";
                default -> "unit01";
            };
            this.bodyFingerprint = this.massSubject
                    ? LocalVisualAssetFingerprint.inspect("mass_production_eva")
                    : EvaUnit01Renderer.visualFingerprintForVariant(variant);
            this.bodyModelTag = this.bodyFingerprint.compactTag();
            boolean cannonPose = !this.massSubject && this.poseName.contains("cannon");
            boolean riflePose = !this.massSubject && this.poseName.contains("rifle");
            boolean n2Pose = !this.massSubject && this.poseName.equals("n2_ready");
            String weaponName = cannonPose ? "positron" : riflePose ? "rifle"
                    : n2Pose ? "n2" : null;
            String weaponTag = cannonPose
                    ? LocalTriangleMeshLayer.captureTag(EvaUnit01Renderer.positronMeshResource())
                    : riflePose
                    ? LocalTriangleMeshLayer.captureTag(EvaUnit01Renderer.rifleMeshResource())
                    : n2Pose
                    ? LocalTriangleMeshLayer.captureTag(EvaUnit01Renderer.n2MeshResource())
                    : null;
            this.modelTag = weaponTag == null ? this.bodyModelTag
                    : this.bodyModelTag + "__" + weaponName + "-" + weaponTag;
            boolean weaponMeshValid = weaponTag == null
                    || cannonPose && isExpectedCannonMesh(weaponTag)
                    || riflePose && isExpectedRifleMesh(weaponTag)
                    || n2Pose && isExpectedN2Mesh(weaponTag);
            if (!this.bodyFingerprint.valid()
                    || !weaponMeshValid)
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
            if (LocalVisualAssetFingerprint.isStrictMode() && !this.bodyFingerprint.valid())
            {
                ProjectSeele.LOGGER.error("Strict Visual capture refused: {}",
                        this.bodyFingerprint.description());
                minecraft.player.displayClientMessage(Component.literal(
                        "Visual capture refused: local high-detail resources are invalid"), false);
                if (Boolean.getBoolean("projectseele.visualCapture"))
                {
                    shutdownTicks = 20;
                }
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
            // A ridden Mob is free to copy the pilot's yaw again on the next
            // tick.  Capture labels are meaningless if that turns the airframe
            // between FRONT/SIDE/BACK frames, so the initial body heading is a
            // hard session invariant.  Lock every interpolation field as well;
            // otherwise the renderer can still blend toward the stale heading.
            this.maintainSubjectOrientation(entity);
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
                this.liveTriggerSent = false;
                return true;
            }
            if (entity instanceof EvaUnit01Entity unit)
            {
                this.maintainFirstPerson(minecraft, unit);
            }
            if (this.isLiveAttack() && !this.liveTriggerSent)
            {
                if (this.settleTicks-- > 0)
                {
                    return true;
                }
                int action = this.liveAttackAction();
                this.liveActionStartY = entity.getY();
                SeeleNetwork.CHANNEL.sendToServer(new ServerboundEvaControlPacket(action));
                this.liveTriggerSent = true;
                this.settleTicks = this.liveAttackContactDelay();
                ProjectSeele.LOGGER.info(
                        "Visual live trigger {} action {} for view {}",
                        this.poseName, action, this.views[this.view]);
                return true;
            }
            if (this.poseName.equals("live_jump") && this.liveTriggerSent
                    && this.camera != null)
            {
                // Track the real airframe instead of leaving the fixed lab
                // camera sixty blocks below it during the ascent sample.
                this.position(minecraft, entity);
            }
            if (this.settleTicks-- > 0)
            {
                return true;
            }
            if (this.poseName.equals("live_jump") && !Double.isNaN(this.liveActionStartY))
            {
                ProjectSeele.LOGGER.info(
                        "Visual live jump sample: deltaY={} velocityY={}",
                        String.format("%.3f", entity.getY() - this.liveActionStartY),
                        String.format("%.3f", entity.getDeltaMovement().y));
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
            // The cockpit weapon frame is an end-to-end proof of the RMB
            // optical feed. Every other frame keeps the key released so the
            // clean first-person views still inspect the physical world mesh.
            minecraft.options.keyUse.setDown((this.poseName.contains("rifle")
                            || this.poseName.contains("cannon"))
                    && name.equals("first_person_cockpit"));
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
                        || unit.getVisualPose() == EvaUnit01Entity.VISUAL_CROUCH_WALK
                        || unit.getVisualPose() == EvaUnit01Entity.VISUAL_PRONE
                        || unit.getVisualPose() == EvaUnit01Entity.VISUAL_CRAWL
                        || unit.getVisualPose() == EvaUnit01Entity.VISUAL_PRONE_CANNON
                        || unit.getVisualPose() == EvaUnit01Entity.VISUAL_PRONE_KNIFE_CONTACT
                        || unit.getVisualPose() == EvaUnit01Entity.VISUAL_PRONE_LANCE_CONTACT
                        || unit.getVisualPose() == EvaUnit01Entity.VISUAL_PRONE_RIFLE
                        || unit.getVisualPose() == EvaUnit01Entity.VISUAL_CROUCH_KNIFE_CONTACT
                        || unit.getVisualPose() == EvaUnit01Entity.VISUAL_CROUCH_LANCE_CONTACT
                        || unit.getVisualPose() == EvaUnit01Entity.VISUAL_CROUCH_RIFLE_CONTACT);
            Vec3 centre = subject.position().add(0.0D,
                    subject.getBbHeight() * (faceClose ? (lowFace ? 0.60D : 0.84D) : 0.52D), 0.0D);
            float yaw = this.referenceYaw * Mth.DEG_TO_RAD;
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
                // A previous pose ends on the PITCH_DOWN frame.  The local
                // player can otherwise send that stale 70-degree look angle
                // back to the server while the next pose's external cameras
                // are settling, which visibly depresses the synchronized
                // cannon even though the capture command set server pitch 0.
                minecraft.player.setYRot(this.referenceYaw);
                minecraft.player.setYHeadRot(this.referenceYaw);
                minecraft.player.setXRot(0.0F);
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

        private void maintainSubjectOrientation(Entity subject)
        {
            subject.setYRot(this.referenceYaw);
            subject.setXRot(0.0F);
            subject.yRotO = this.referenceYaw;
            subject.xRotO = 0.0F;
            if (subject instanceof net.minecraft.world.entity.LivingEntity living)
            {
                living.setYBodyRot(this.referenceYaw);
                living.setYHeadRot(this.referenceYaw);
                living.yBodyRotO = this.referenceYaw;
                living.yHeadRotO = this.referenceYaw;
            }
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
            minecraft.options.keyUse.setDown(this.originalUseDown);
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
                case EvaUnit01Entity.VISUAL_RUN_CONTACT -> "run_contact";
                case EvaUnit01Entity.VISUAL_JUMP -> "jump";
                case EvaUnit01Entity.VISUAL_FALL -> "fall";
                case EvaUnit01Entity.VISUAL_KNIFE_WINDUP -> "knife_windup";
                case EvaUnit01Entity.VISUAL_KNIFE_CONTACT -> "knife_contact";
                case EvaUnit01Entity.VISUAL_KNIFE_RECOVERY -> "knife_recovery";
                case EvaUnit01Entity.VISUAL_KNIFE_READY -> "knife_ready";
                case EvaUnit01Entity.VISUAL_CROUCH -> "crouch";
                case EvaUnit01Entity.VISUAL_CROUCH_WALK -> "crouch_walk";
                case EvaUnit01Entity.VISUAL_PRONE -> "prone";
                case EvaUnit01Entity.VISUAL_CRAWL -> "crawl";
                case EvaUnit01Entity.VISUAL_PRONE_CANNON -> "prone_cannon";
                case EvaUnit01Entity.VISUAL_LANCE_READY -> "lance_ready";
                case EvaUnit01Entity.VISUAL_LANCE_WINDUP -> "lance_windup";
                case EvaUnit01Entity.VISUAL_LANCE_CONTACT -> "lance_contact";
                case EvaUnit01Entity.VISUAL_LANCE_RECOVERY -> "lance_recovery";
                case EvaUnit01Entity.VISUAL_CANNON -> "cannon";
                case EvaUnit01Entity.VISUAL_RIFLE -> "rifle";
                case EvaUnit01Entity.VISUAL_CROUCH_KNIFE_CONTACT -> "crouch_knife_contact";
                case EvaUnit01Entity.VISUAL_PRONE_KNIFE_CONTACT -> "prone_knife_contact";
                case EvaUnit01Entity.VISUAL_CROUCH_LANCE_CONTACT -> "crouch_lance_contact";
                case EvaUnit01Entity.VISUAL_PRONE_LANCE_CONTACT -> "prone_lance_contact";
                case EvaUnit01Entity.VISUAL_N2_READY -> "n2_ready";
                case EvaUnit01Entity.VISUAL_RIFLE_WALK_CONTACT -> "rifle_walk_contact";
                case EvaUnit01Entity.VISUAL_CROUCH_RIFLE_CONTACT -> "crouch_rifle_contact";
                case EvaUnit01Entity.VISUAL_PRONE_RIFLE -> "prone_rifle";
                case EvaUnit01Entity.VISUAL_LIVE_MELEE -> "live_melee";
                case EvaUnit01Entity.VISUAL_LIVE_KNIFE -> "live_knife";
                case EvaUnit01Entity.VISUAL_LIVE_LANCE -> "live_lance";
                case EvaUnit01Entity.VISUAL_LIVE_RIFLE -> "live_rifle";
                case EvaUnit01Entity.VISUAL_LIVE_KNIFE_HEAVY -> "live_knife_heavy";
                case EvaUnit01Entity.VISUAL_LIVE_JUMP -> "live_jump";
                default -> "normal";
            };
        }

        private boolean isLiveAttack()
        {
            return this.poseName.startsWith("live_");
        }

        private int liveAttackAction()
        {
            return switch (this.poseName)
            {
                case "live_rifle" -> ServerboundEvaControlPacket.ACTION_RIFLE_FIRE;
                case "live_knife_heavy" -> ServerboundEvaControlPacket.ACTION_SMASH;
                case "live_jump" -> ServerboundEvaControlPacket.ACTION_JUMP;
                default -> ServerboundEvaControlPacket.ACTION_MELEE;
            };
        }

        private int liveAttackContactDelay()
        {
            return switch (this.poseName)
            {
                case "live_lance" -> 8;
                case "live_knife" -> 9;
                case "live_knife_heavy" -> 11;
                case "live_melee" -> 4;
                case "live_rifle" -> 1;
                // Screenshot compression can stall the integrated server for
                // forty ticks.  Wait long enough to observe synchronized
                // server motion rather than photographing the send frame.
                case "live_jump" -> 40;
                default -> 1;
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
                // Keep this synchronized with VisualLabAutomation.ALL_POSES.
                // The dynamic jump is the final end-to-end input frame.
                return pose.equals(unitName.equals("mass") ? "ritual" : "live_jump");
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
