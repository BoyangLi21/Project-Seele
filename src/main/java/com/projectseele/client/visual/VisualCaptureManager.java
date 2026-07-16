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
import com.projectseele.fx.TreeOfLifeLayout;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.network.ServerboundEvaControlPacket;
import com.projectseele.registry.ModBlocks;
import com.projectseele.world.RetractableBuildingCoreBlock;
import net.minecraft.client.CameraType;
import net.minecraft.client.CloudStatus;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.level.block.Blocks;
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
        tokyo3Session = new Tokyo3Session(origin, minecraft);
        minecraft.player.displayClientMessage(
                Component.literal("Tokyo-3 visual capture started"), false);
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

    /** Suppress GUI overlays while leaving the world-space EVA body visible. */
    public static boolean isSuppressingGui()
    {
        return impactSession != null || tokyo3Session != null
                || tokyo3RetractionSession != null
                || geoFrontSession != null
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

    /** Four audited views of the independent GeoFront development cavern. */
    private static final class GeoFrontSession
    {
        private static final int INITIAL_SETTLE_TICKS = 180;
        private static final String[] VIEWS = {
                "cavern_overview", "nerv_pyramid", "lcl_lake", "lift_terminals"
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
        private boolean audited;

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
                        "GeoFront visual matrix finished: four audited cavern views captured");
                if (Boolean.getBoolean("projectseele.visualCapture"))
                {
                    shutdownTicks = 30;
                }
                return false;
            }
            this.positioned = false;
            this.settleTicks = 18;
            return true;
        }

        private void audit(Minecraft minecraft)
        {
            boolean floor = minecraft.level.getBlockState(
                    this.origin.offset(100, 0, 0)).is(Blocks.DEEPSLATE_TILES);
            var wallState = minecraft.level.getBlockState(
                    this.origin.offset(112, 32, 0));
            boolean wall = wallState.is(Blocks.DEEPSLATE)
                    || wallState.is(Blocks.CALCITE)
                    || wallState.is(Blocks.POLISHED_BASALT);
            boolean lake = minecraft.level.getBlockState(
                    this.origin.offset(48, 1, 0)).is(Blocks.ORANGE_STAINED_GLASS);
            boolean pyramid = minecraft.level.getBlockState(
                    this.origin.offset(0, 29, 0)).is(Blocks.BEACON);
            boolean sun = minecraft.level.getBlockState(
                    this.origin.offset(0, 88, 0)).is(Blocks.SEA_LANTERN);
            int lifts = 0;
            for (int x : LIFT_X)
            {
                if (minecraft.level.getBlockState(
                        this.origin.offset(x, 1, -76)).is(Blocks.LODESTONE))
                {
                    lifts++;
                }
            }
            boolean bridge = minecraft.level.getBlockState(
                    this.origin.offset(0, 2, 70)).is(Blocks.IRON_BLOCK);
            boolean observation = minecraft.level.getBlockState(
                    this.origin.offset(0, 24, 100)).is(Blocks.LODESTONE);
            boolean valid = floor && wall && lake && pyramid && sun
                    && lifts == 3 && bridge && observation;
            ProjectSeele.LOGGER.info(
                    "GeoFront visual evidence: floor={} wall={} lclLake={} "
                            + "nervPyramid={} artificialSun={} lifts={}/3 "
                            + "commandBridge={} observation={} valid={}",
                    floor, wall, lake, pyramid, sun, lifts, bridge, observation, valid);
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
                    cameraPos = base.add(72.0D, 38.0D, 70.0D);
                    target = base.add(0.0D, 14.0D, 0.0D);
                }
                case "lcl_lake" ->
                {
                    cameraPos = base.add(-82.0D, 17.0D, 12.0D);
                    target = base.add(0.0D, 5.0D, 0.0D);
                }
                case "lift_terminals" ->
                {
                    cameraPos = base.add(0.0D, 34.0D, -108.0D);
                    target = base.add(0.0D, 10.0D, -68.0D);
                }
                default ->
                {
                    cameraPos = base.add(0.0D, 62.0D, 104.0D);
                    target = base.add(0.0D, 32.0D, 0.0D);
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
        private static final int[] LOT_CENTRES = {-80, -40, 0, 40, 80};
        private static final int[][] ROAD_POINTS = {
                {-100, -100}, {-100, 100}, {100, -100}, {100, 100},
                {-60, -100}, {60, 100}, {-100, 60}, {100, -60},
        };
        private static final int[][] PYLONS = {
                {-100, -80}, {-100, 0}, {-100, 80},
                {100, -80}, {100, 0}, {100, 80},
        };

        private final BlockPos origin;
        private final Entity originalCamera;
        private final CameraType originalCameraType;
        private final boolean originalHideGui;
        private final CloudStatus originalCloudStatus;
        private final LocalVisualAssetFingerprint.Fingerprint unit00Fingerprint;
        private final LocalVisualAssetFingerprint.Fingerprint unit01Fingerprint;
        private final LocalVisualAssetFingerprint.Fingerprint unit02Fingerprint;
        private ArmorStand camera;
        private int settleTicks = INITIAL_SETTLE_TICKS;
        private int view;
        private boolean positioned;
        private boolean audited;

        Tokyo3Session(BlockPos origin, Minecraft minecraft)
        {
            this.origin = origin.immutable();
            this.originalCamera = minecraft.getCameraEntity();
            this.originalCameraType = minecraft.options.getCameraType();
            this.originalHideGui = minecraft.options.hideGui;
            this.originalCloudStatus = minecraft.options.cloudStatus().get();
            this.unit00Fingerprint = EvaUnit01Renderer.visualFingerprintForVariant(
                    EvaUnit01Entity.UNIT_00);
            this.unit01Fingerprint = EvaUnit01Renderer.visualFingerprintForVariant(
                    EvaUnit01Entity.UNIT_01);
            this.unit02Fingerprint = EvaUnit01Renderer.visualFingerprintForVariant(
                    EvaUnit01Entity.UNIT_02);
            ProjectSeele.LOGGER.info(
                    "Tokyo-3 visual capture batch {} at {} uses unit00={} unit01={} unit02={}",
                    CAPTURE_BATCH, this.origin,
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
                            || (x == 0 && z == 80))
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
            AABB cages = new AABB(this.origin).inflate(80.0D, 64.0D, 80.0D);
            var units = minecraft.level.getEntitiesOfClass(
                    EvaUnit01Entity.class, cages, Entity::isAlive);
            boolean variants = units.stream().anyMatch(
                    unit -> unit.getUnitVariant() == EvaUnit01Entity.UNIT_00)
                    && units.stream().anyMatch(
                    unit -> unit.getUnitVariant() == EvaUnit01Entity.UNIT_01)
                    && units.stream().anyMatch(
                    unit -> unit.getUnitVariant() == EvaUnit01Entity.UNIT_02);
            boolean battleBeacon = minecraft.level.getBlockState(
                    this.origin.offset(0, 1, 80)).is(Blocks.BEACON);
            boolean observation = minecraft.level.getBlockState(
                    this.origin.offset(0, 38, 112)).is(Blocks.LODESTONE);
            boolean foundation = minecraft.level.getBlockState(
                    this.origin.offset(120, -4, 0)).is(Blocks.DEEPSLATE_BRICKS);
            boolean valid = roads == 8 && towers == 13 && pylons == 6
                    && units.size() == 3 && variants && battleBeacon && observation
                    && foundation
                    && this.unit00Fingerprint.valid()
                    && this.unit01Fingerprint.valid()
                    && this.unit02Fingerprint.valid();
            ProjectSeele.LOGGER.info(
                    "Tokyo-3 visual evidence: roads={}/8 towers={}/13 pylons={}/6 "
                            + "units={} variants00/01/02={} battleBeacon={} "
                            + "observation={} foundation={} valid={}",
                    roads, towers, pylons, units.size(), variants,
                    battleBeacon, observation, foundation, valid);
            if (!valid)
            {
                ProjectSeele.LOGGER.error(
                        "VISUAL TOKYO3 INVALID: city structure, three launch EVAs, "
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
            Vec3 base = Vec3.atLowerCornerOf(this.origin);
            Vec3 target;
            Vec3 cameraPos;
            switch (VIEWS[this.view])
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
                String filename = "tokyo3_" + VIEWS[this.view] + ".png";
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
        private static final int MAX_DEPTH = 42;
        private static final int MID_DEPTH = MAX_DEPTH / 2;
        private static final int REQUIRED_STABLE_TICKS = 12;
        private static final int TIMEOUT_TICKS = 2600;
        private static final int[] LOT_CENTRES = {-80, -40, 0, 40, 80};
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
                            + "towerStates={}/13 cores={}/13 armed={}/13 valid={}",
                    STAGES[this.stage], DEPTHS[this.stage], audit.towers(),
                    audit.cores(), audit.armed(), audit.valid());
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
            int cores = 0;
            int armed = 0;
            for (int x : LOT_CENTRES)
            {
                for (int z : LOT_CENTRES)
                {
                    if (Math.abs(x) <= 40 && Math.abs(z) <= 40
                            || (x == 0 && z == -80)
                            || (x == 80 && z == 0)
                            || (x == 0 && z == 80))
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
            int expectedArmedCount = expectedArmed ? 13 : 0;
            return new Audit(towers, cores, armed,
                    towers == 13 && cores == 13 && armed == expectedArmedCount);
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
            Vec3 cameraPos = base.add(0.0D, 62.0D, 148.0D);
            Vec3 target = base.add(0.0D, 15.0D, 0.0D);
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

        private record Audit(int towers, int cores, int armed, boolean valid) {}
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
