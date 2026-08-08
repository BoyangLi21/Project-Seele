package com.projectseele.client;

import java.io.IOException;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicBoolean;

import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.math.Axis;
import com.projectseele.ProjectSeele;
import com.projectseele.client.visual.VisualCaptureManager;
import com.projectseele.config.SeeleConfig;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.network.ClientboundPilotStatusPacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.network.ServerboundEvaVideoFramePacket;
import com.projectseele.visual.GeoFrontCommands;
import com.projectseele.world.IntegratedNervMapBuilder;
import com.projectseele.world.EvaPilotResolver;
import com.projectseele.world.FacilitySchemaV2;
import com.projectseele.world.FacilityV2CommandInteriorDirector;
import net.minecraft.world.level.block.Blocks;
import com.projectseele.world.NervOperationsCentreBuilder;
import com.projectseele.world.PerformanceCounters;
import com.projectseele.world.S20CommandPresentationDirector;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.gui.Font;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.Util;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.client.gui.overlay.IGuiOverlay;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Matrix3f;
import org.joml.Matrix4f;

/**
 * Captures the final cockpit view at low resolution and renders authenticated
 * remote frames on three physical 16:9 screens in NERV operations.
 */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE,
        value = Dist.CLIENT)
public final class EvaCommandFeedClient
{
    public static final IGuiOverlay CAPTURE_OVERLAY =
            (gui, graphics, partialTick, width, height) -> captureIfDue();

    /**
     * A full render-target readback and PNG upload is intentionally low-rate.
     * Four captures per second stalled the pilot client even when nobody was
     * actively watching the operations-room screen.
     */
    private static final int CAPTURE_INTERVAL_TICKS = 20;
    private static final long FRAME_STALE_NANOS = 3_000_000_000L;
    private static final double DISPLAY_RANGE_SQR = 150.0D * 150.0D;
    private static final float SCREEN_WIDTH = 10.5F;
    private static final float SCREEN_HEIGHT =
            SCREEN_WIDTH * ServerboundEvaVideoFramePacket.FRAME_HEIGHT
                    / ServerboundEvaVideoFramePacket.FRAME_WIDTH;
    private static final int[] SCREEN_X = {-12, 0, 12};
    /*
     * The S19 command asset already owns one measured amber sloped screen.
     * Divide that authored 15-block face into three optical feeds; never draw
     * the retired z=-68 video wall in front of it.
     */
    private static final double[] V2_SCREEN_X = {-4.0D, 1.0D, 6.0D};
    private static final double[] V2_SCREEN_Y =
            {-319.5D, -319.5D, -319.5D};
    private static final double[] V2_SCREEN_Z =
            {-36.0D, -36.0D, -36.0D};
    private static final float[] V2_SCREEN_YAW = {0.0F, 0.0F, 0.0F};
    private static final float[] V2_SCREEN_PITCH =
            {-27.3F, -27.3F, -27.3F};
    private static final float[] V2_SCREEN_WIDTH =
            {4.5F, 4.5F, 4.5F};
    /*
     * The upper authored mask is a tall 17x35 sloped plane.  Three landscape
     * pilot feeds therefore stack along its long axis instead of becoming
     * three tiny tiles across its narrow width.
     */
    private static final double[] S20_SCREEN_X = {28.0D, 28.0D, 28.0D};
    private static final double[] S20_SCREEN_Y =
            {-406.90D, -415.795D, -424.69D};
    private static final double[] S20_SCREEN_Z =
            {327.38D, 322.793D, 318.20D};
    private static final float S20_SCREEN_YAW = 180.0F;
    private static final float S20_UPPER_SCREEN_PITCH = -27.3F;
    /**
     * The measured mask lies at -68.8 degrees, which is almost flat: its
     * normal points nearly straight at the ceiling, so an operator standing in
     * front of it reads the pilot rows at a glancing angle.  Standing the
     * board up by seven degrees turns the face toward the room without pulling
     * the raster off the authored slope.
     */
    private static final float S20_LOWER_SCREEN_PITCH = -61.8F;
    private static final long SCREEN_TRANSITION_NANOS = 400_000_000L;
    private static final float[] SCREEN_VISIBILITY = {1.0F, 1.0F, 1.0F, 1.0F};
    private static final float[] SCREEN_TARGET = {1.0F, 1.0F, 1.0F, 1.0F};
    private static final AtomicBoolean CAPTURE_IN_FLIGHT =
            new AtomicBoolean();
    private static final DynamicTexture[] TEXTURES =
            new DynamicTexture[3];
    private static final long[] LAST_FRAME_NANOS = new long[3];
    private static final ResourceLocation[] TEXTURE_IDS = {
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/eva_command_feed_00"),
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/eva_command_feed_01"),
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/eva_command_feed_02")
    };
    private static final DynamicTexture[] STANDBY_TEXTURES =
            new DynamicTexture[3];
    private static final ResourceLocation[] STANDBY_TEXTURE_IDS = {
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/eva_command_standby_00"),
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/eva_command_standby_01"),
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/eva_command_standby_02")
    };
    private static DynamicTexture tacticalTexture;
    private static final ResourceLocation TACTICAL_TEXTURE_ID =
            new ResourceLocation(ProjectSeele.MODID,
                    "dynamic/nerv_tactical_overview");
    /*
     * The board is 15 blocks wide.  At 1/0.070 font pixels per block a line of
     * thirty-five characters just fits between its amber margins, which is the
     * widest row the status layout below ever produces.
     */
    private static final float TACTICAL_TEXT_SCALE = 0.070F;
    private static final int TACTICAL_LINE_HEIGHT = 20;
    private static final int TACTICAL_LEFT = -97;
    private static final int TACTICAL_TOP = -272;
    private static ClientboundPilotStatusPacket.Unit[] pilotStatus;
    private static final int[][] UNIT_COLOURS = {
            {232, 143, 38}, {144, 62, 205}, {210, 45, 52}
    };

    private static int lastCaptureTick = -CAPTURE_INTERVAL_TICKS;
    private static ClientLevel captureLevel;
    private static int captureEvaId = Integer.MIN_VALUE;
    private static ClientLevel activeLevel;
    private static boolean captureDemanded;
    private static long lastScreenTransitionNanos = System.nanoTime();

    private EvaCommandFeedClient() {}

    private static void captureIfDue()
    {
        Minecraft minecraft = Minecraft.getInstance();
        EvaUnit01Entity eva = minecraft.player == null
                ? null : EvaPilotResolver.controlTarget(minecraft.player);
        if (!SeeleConfig.liveCockpitVideoEnabled()
                || !captureDemanded
                || minecraft.player == null || minecraft.level == null
                || minecraft.screen != null
                || VisualCaptureManager.isSuppressingGui()
                || eva == null
                || EvaPilotResolver.pilot(eva) != minecraft.player
                || !eva.isAlive())
        {
            return;
        }
        if (captureLevel != minecraft.level || captureEvaId != eva.getId())
        {
            captureLevel = minecraft.level;
            captureEvaId = eva.getId();
            lastCaptureTick = minecraft.player.tickCount
                    - CAPTURE_INTERVAL_TICKS;
        }
        int tick = minecraft.player.tickCount;
        if (tick - lastCaptureTick < CAPTURE_INTERVAL_TICKS
                || !CAPTURE_IN_FLIGHT.compareAndSet(false, true))
        {
            return;
        }
        lastCaptureTick = tick;

        NativeImage full;
        try
        {
            full = Screenshot.takeScreenshot(
                    minecraft.getMainRenderTarget());
            PerformanceCounters.recordFramebufferCapture();
        }
        catch (RuntimeException exception)
        {
            CAPTURE_IN_FLIGHT.set(false);
            ProjectSeele.LOGGER.warn(
                    "Unable to capture EVA command feed", exception);
            return;
        }
        int variant = eva.getUnitVariant();
        Util.ioPool().execute(() -> encodeAndSend(
                minecraft, variant, full));
    }

    /**
     * The pilot client cannot know whether a remote operator is watching the
     * command wall. Server demand keeps GPU readback and PNG compression at
     * zero cost in normal one-player testing.
     */
    public static void setCaptureDemand(boolean demanded)
    {
        captureDemanded = demanded;
    }

    /** Applies the server-authoritative power state; rendering eases to it. */
    public static void setCommandScreenMask(int visibleMask)
    {
        for (int screen = 0; screen < SCREEN_TARGET.length; screen++)
        {
            SCREEN_TARGET[screen] = (visibleMask & 1 << screen) != 0
                    ? 1.0F : 0.0F;
        }
        lastScreenTransitionNanos = System.nanoTime();
    }

    private static void updateCommandScreenTransitions()
    {
        long now = System.nanoTime();
        float step = Math.min(1.0F,
                (now - lastScreenTransitionNanos)
                        / (float) SCREEN_TRANSITION_NANOS);
        lastScreenTransitionNanos = now;
        for (int screen = 0; screen < SCREEN_VISIBILITY.length; screen++)
        {
            float current = SCREEN_VISIBILITY[screen];
            float target = SCREEN_TARGET[screen];
            if (current < target)
            {
                SCREEN_VISIBILITY[screen] = Math.min(target, current + step);
            }
            else if (current > target)
            {
                SCREEN_VISIBILITY[screen] = Math.max(target, current - step);
            }
        }
    }

    private static void encodeAndSend(Minecraft minecraft, int variant,
                                      NativeImage full)
    {
        try (full;
             NativeImage reduced = new NativeImage(
                     ServerboundEvaVideoFramePacket.FRAME_WIDTH,
                     ServerboundEvaVideoFramePacket.FRAME_HEIGHT, false))
        {
            full.resizeSubRectTo(0, 0, full.getWidth(), full.getHeight(),
                    reduced);
            byte[] png = reduced.asByteArray();
            PerformanceCounters.recordPngEncode();
            if (png.length <= ServerboundEvaVideoFramePacket.MAX_FRAME_BYTES)
            {
                minecraft.execute(() -> SeeleNetwork.CHANNEL.sendToServer(
                        new ServerboundEvaVideoFramePacket(variant, png)));
            }
        }
        catch (IOException | RuntimeException exception)
        {
            ProjectSeele.LOGGER.warn(
                    "Unable to encode EVA command feed", exception);
        }
        finally
        {
            CAPTURE_IN_FLIGHT.set(false);
        }
    }

    public static void acceptFrame(int variant, byte[] png)
    {
        if (!SeeleConfig.videoFrameRelayEnabled()
                || variant < EvaUnit01Entity.UNIT_00
                || variant > EvaUnit01Entity.UNIT_02)
        {
            return;
        }
        NativeImage image = null;
        try
        {
            image = NativeImage.read(png);
            if (image.getWidth()
                    != ServerboundEvaVideoFramePacket.FRAME_WIDTH
                    || image.getHeight()
                    != ServerboundEvaVideoFramePacket.FRAME_HEIGHT)
            {
                image.close();
                return;
            }

            Minecraft minecraft = Minecraft.getInstance();
            DynamicTexture texture = TEXTURES[variant];
            if (texture == null)
            {
                texture = new DynamicTexture(image);
                TEXTURES[variant] = texture;
                minecraft.getTextureManager().register(
                        TEXTURE_IDS[variant], texture);
            }
            else
            {
                NativeImage previous = texture.getPixels();
                texture.setPixels(image);
                if (previous != null)
                {
                    previous.close();
                }
            }
            texture.upload();
            LAST_FRAME_NANOS[variant] = System.nanoTime();
        }
        catch (IOException | RuntimeException exception)
        {
            if (image != null)
            {
                image.close();
            }
            ProjectSeele.LOGGER.warn(
                    "Rejected EVA command feed frame", exception);
        }
    }

    /** True only while this client owns a recently decoded command-room frame. */
    public static boolean hasFreshFrame(int variant)
    {
        return variant >= EvaUnit01Entity.UNIT_00
                && variant <= EvaUnit01Entity.UNIT_02
                && TEXTURES[variant] != null
                && System.nanoTime() - LAST_FRAME_NANOS[variant]
                        <= FRAME_STALE_NANOS;
    }

    @SubscribeEvent
    public static void onRenderLevelStage(RenderLevelStageEvent event)
    {
        /*
         * Screens must be drawn before the translucent chunk layer.  Glass
         * writes depth, so the old AFTER_PARTICLES pass rejected every screen
         * fragment viewed through glass even though the glass was transparent.
         */
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_CUTOUT_BLOCKS)
        {
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        ClientLevel level = minecraft.level;
        if (level == null || minecraft.player == null
                || !level.dimension().equals(GeoFrontCommands.GEOFRONT))
        {
            activeLevel = level;
            PerformanceCounters.leaveClientScenario();
            return;
        }
        PerformanceCounters.recordClientFrame();
        if (activeLevel != level)
        {
            activeLevel = level;
            for (int index = 0; index < LAST_FRAME_NANOS.length; index++)
            {
                LAST_FRAME_NANOS[index] = 0L;
            }
        }

        var v2Centre = FacilitySchemaV2.CANDIDATE_CENTRES.get(
                FacilitySchemaV2.ACTIVE_CANDIDATE_INDEX);
        var v2Marker = v2Centre.offset(
                FacilityV2CommandInteriorDirector.MARKER_X,
                FacilityV2CommandInteriorDirector.MARKER_Y,
                FacilityV2CommandInteriorDirector.MARKER_Z);
        boolean facilityV2 = level.getBlockState(v2Marker)
                .is(Blocks.RED_NETHER_BRICKS);
        boolean s20Marker = level.getBlockState(
                S20CommandPresentationDirector.COMMAND_MARKER)
                .is(Blocks.STRUCTURE_VOID);
        /*
         * The marker lives six chunks behind the command seats and may reach
         * the client after the room itself at short render distance.  The
         * approved physical screen-control bank is an equally strict local
         * signature and keeps every display from vanishing during that load
         * window.
         */
        boolean s20Controls = level.getBlockState(
                new net.minecraft.core.BlockPos(32, -407, 286))
                .getBlock()
                instanceof net.minecraft.world.level.block.ButtonBlock;
        boolean s20 = s20Marker || s20Controls;

        var origin = IntegratedNervMapBuilder.GEOFRONT_ORIGIN;
        var importedAnchor = origin.offset(0, 17, 58);
        boolean importedVideoWall = level.getBlockState(
                importedAnchor.offset(0, 4, -1)).is(Blocks.BLACK_CONCRETE)
                && level.getBlockState(importedAnchor.offset(-18, 4, -1))
                .is(Blocks.POLISHED_DEEPSLATE);
        var anchor = s20 ? new net.minecraft.core.BlockPos(
                (int) S20CommandPresentationDirector.UPPER_SCREEN_X,
                (int) S20CommandPresentationDirector.UPPER_SCREEN_Y,
                (int) S20CommandPresentationDirector.UPPER_SCREEN_Z)
                : facilityV2 ? v2Centre.offset(1, -320, -36)
                : importedVideoWall ? importedAnchor
                : origin.offset(0, 7,
                        NervOperationsCentreBuilder.DISPLAY_Z + 1);
        if (minecraft.player.position().distanceToSqr(
                Vec3.atCenterOf(anchor)) > DISPLAY_RANGE_SQR)
        {
            return;
        }

        ensureStandbyTextures(minecraft);
        updateCommandScreenTransitions();
        if (s20)
        {
            ensureTacticalTexture(minecraft);
        }
        long now = System.nanoTime();
        Vec3 camera = event.getCamera().getPosition();
        for (int variant = 0; variant < 3; variant++)
        {
            boolean live = TEXTURES[variant] != null
                    && now - LAST_FRAME_NANOS[variant]
                    <= FRAME_STALE_NANOS;
            ResourceLocation texture = live ? TEXTURE_IDS[variant]
                    : STANDBY_TEXTURE_IDS[variant];
            if (s20)
            {
                Vec3 centre = new Vec3(
                        S20_SCREEN_X[variant],
                        S20_SCREEN_Y[variant],
                        S20_SCREEN_Z[variant]);
                renderScreen(event.getPoseStack(), camera, centre,
                        texture, minecraft, 15.0F,
                        15.0F * ServerboundEvaVideoFramePacket.FRAME_HEIGHT
                                / ServerboundEvaVideoFramePacket.FRAME_WIDTH,
                        S20_SCREEN_YAW, S20_UPPER_SCREEN_PITCH,
                        SCREEN_VISIBILITY[variant]);
            }
            else if (facilityV2)
            {
                Vec3 centre = new Vec3(
                        v2Centre.getX() + V2_SCREEN_X[variant] + 0.5D,
                        V2_SCREEN_Y[variant],
                        v2Centre.getZ() + V2_SCREEN_Z[variant] + 0.56D);
                float width = V2_SCREEN_WIDTH[variant];
                renderScreen(event.getPoseStack(), camera, centre,
                        texture, minecraft, width,
                        width * ServerboundEvaVideoFramePacket.FRAME_HEIGHT
                                / ServerboundEvaVideoFramePacket.FRAME_WIDTH,
                        V2_SCREEN_YAW[variant],
                        V2_SCREEN_PITCH[variant], 1.0F);
            }
            else
            {
                Vec3 centre = Vec3.atCenterOf(
                        anchor.offset(SCREEN_X[variant], 4, 0))
                        .add(0.0D, 0.0D, -0.48D);
                renderScreen(event.getPoseStack(), camera, centre,
                        texture, minecraft, SCREEN_WIDTH, SCREEN_HEIGHT,
                        0.0F, 0.0F, 1.0F);
            }
        }
        if (s20 && tacticalTexture != null)
        {
            renderScreen(event.getPoseStack(), camera, new Vec3(
                            S20CommandPresentationDirector.LOWER_SCREEN_X,
                            S20CommandPresentationDirector.LOWER_SCREEN_Y,
                            S20CommandPresentationDirector.LOWER_SCREEN_Z),
                    TACTICAL_TEXTURE_ID, minecraft, 15.0F, 40.5F,
                    S20_SCREEN_YAW, S20_LOWER_SCREEN_PITCH,
                    SCREEN_VISIBILITY[3]);
            renderPilotStatusBoard(event.getPoseStack(), camera, minecraft,
                    SCREEN_VISIBILITY[3]);
        }
        // The un-switched rear city-status wall is a server-maintained
        // TextDisplay in S20.  Keeping it out of this client-only renderer
        // makes it visible to every operator and prevents command glass or a
        // late marker chunk from silently suppressing all of its data.
    }

    /** Receives the server-sampled fleet telemetry for the tactical board. */
    public static void setPilotStatus(
            ClientboundPilotStatusPacket.Unit[] units)
    {
        pilotStatus = units;
    }

    /**
     * Draws pilot telemetry on the lower orange board.
     *
     * <p>The board used to be a static painted texture, so it never said
     * anything about the three pilots it exists to monitor.  Text is laid on
     * the same authored plane as the raster and collapses with it when the
     * operator switches the screen off.</p>
     */
    private static void renderPilotStatusBoard(
            PoseStack poseStack, Vec3 camera, Minecraft minecraft,
            float visibility)
    {
        float eased = visibility * visibility * (3.0F - 2.0F * visibility);
        if (eased <= 0.05F)
        {
            return;
        }
        poseStack.pushPose();
        poseStack.translate(
                S20CommandPresentationDirector.LOWER_SCREEN_X - camera.x,
                S20CommandPresentationDirector.LOWER_SCREEN_Y - camera.y,
                S20CommandPresentationDirector.LOWER_SCREEN_Z - camera.z);
        /*
         * The raster plane is built as yaw 180 then pitch.  Conjugating that
         * pair by the yaw leaves a single opposite X rotation, which lands the
         * glyphs on the same plane while keeping the transform right-handed:
         * mirroring it instead reverses the winding and the text render type
         * culls every quad away.
         */
        poseStack.mulPose(Axis.XP.rotationDegrees(-S20_LOWER_SCREEN_PITCH));
        poseStack.translate(0.0D, 0.0D, -0.03D);
        poseStack.scale(1.0F, eased, 1.0F);
        poseStack.scale(-TACTICAL_TEXT_SCALE, -TACTICAL_TEXT_SCALE,
                TACTICAL_TEXT_SCALE);

        MultiBufferSource.BufferSource buffers =
                minecraft.renderBuffers().bufferSource();
        Font font = minecraft.font;
        Matrix4f pose = poseStack.last().pose();
        int amber = 0xFFF6A020;
        int rule = 0xFF6B4418;
        int label = 0xFF9FB2BD;
        int value = 0xFFE6ECEF;
        int alert = 0xFFFF4C4C;

        int row = 0;
        row = line(font, pose, buffers, row,
                "NERV MAGI / PILOT STATUS", amber);
        row = line(font, pose, buffers, row,
                "===============================", rule);
        ClientboundPilotStatusPacket.Unit[] units = pilotStatus;
        for (int variant = 0; variant < 3; variant++)
        {
            ClientboundPilotStatusPacket.Unit unit =
                    units == null || variant >= units.length
                            ? null : units[variant];
            int[] tint = UNIT_COLOURS[variant];
            int unitColour = 0xFF000000 | tint[0] << 16
                    | tint[1] << 8 | tint[2];
            if (unit == null)
            {
                row = line(font, pose, buffers, row,
                        String.format(Locale.ROOT, "EVA-%02d  AWAITING MAGI LINK",
                                variant), unitColour);
                row++;
                continue;
            }
            row = line(font, pose, buffers, row, String.format(Locale.ROOT,
                    "EVA-%02d  %s", variant, unit.phase()), unitColour);
            if (!unit.present())
            {
                row = line(font, pose, buffers, row,
                        "  NO CANONICAL CHASSIS", alert);
                row = line(font, pose, buffers, row,
                        "-------------------------------", rule);
                continue;
            }
            row = line(font, pose, buffers, row, String.format(Locale.ROOT,
                    "  PILOT  %s", unit.pilot().isEmpty()
                            ? "NONE / DUMMY PLUG" : unit.pilot()),
                    unit.pilot().isEmpty() ? label : value);
            row = line(font, pose, buffers, row, String.format(Locale.ROOT,
                    "  SYNC   %5.1f%%   AT %4.0f/%4.0f",
                    unit.sync() * 100.0F, unit.atEnergy(),
                    unit.atCapacity()), value);
            row = line(font, pose, buffers, row, String.format(Locale.ROOT,
                    "  POWER  %s", powerLabel(unit)),
                    unit.externalPower() ? value : amber);
            row = line(font, pose, buffers, row, String.format(Locale.ROOT,
                    "  HULL   %4.0f / %4.0f   FEED %s",
                    unit.health(), unit.maxHealth(),
                    unit.liveFeed() ? "LIVE" : "STBY"), value);
            if (unit.berserk())
            {
                row = line(font, pose, buffers, row,
                        "  *** BERSERK - NO CONTROL ***", alert);
            }
            row = line(font, pose, buffers, row,
                    "-------------------------------", rule);
        }
        line(font, pose, buffers, row,
                "GEOFRONT COMMAND LINK   ONLINE", amber);
        buffers.endBatch();
        poseStack.popPose();
    }

    private static int line(Font font, Matrix4f pose,
                            MultiBufferSource.BufferSource buffers,
                            int row, String text, int colour)
    {
        font.drawInBatch(text, TACTICAL_LEFT,
                TACTICAL_TOP + row * TACTICAL_LINE_HEIGHT, colour, false,
                pose, buffers, Font.DisplayMode.POLYGON_OFFSET, 0,
                LightTexture.FULL_BRIGHT);
        return row + 1;
    }

    private static String powerLabel(ClientboundPilotStatusPacket.Unit unit)
    {
        if (unit.externalPower())
        {
            return "EXTERNAL UMBILICAL";
        }
        int seconds = Math.max(0, unit.powerTicks()) / 20;
        return String.format(Locale.ROOT, "INTERNAL %02d:%02d",
                seconds / 60, seconds % 60);
    }

    private static void ensureTacticalTexture(Minecraft minecraft)
    {
        if (tacticalTexture != null)
        {
            return;
        }
        NativeImage image = new NativeImage(192, 384, false);
        int background = rgba(4, 6, 8, 255);
        int amber = rgba(246, 150, 32, 255);
        int red = rgba(215, 45, 42, 255);
        int dim = rgba(70, 35, 20, 255);
        for (int y = 0; y < image.getHeight(); y++)
        {
            for (int x = 0; x < image.getWidth(); x++)
            {
                boolean grid = x % 24 == 0 || y % 24 == 0;
                image.setPixelRGBA(x, y, grid ? dim : background);
            }
        }
        fillRect(image, 0, 0, 192, 4, amber);
        fillRect(image, 0, 380, 192, 4, amber);
        fillRect(image, 0, 0, 4, 384, amber);
        fillRect(image, 188, 0, 4, 384, amber);
        /*
         * Backdrop only.  The former painted bars and tactical diamond sat
         * where the pilot rows are now drawn and read as data they were not:
         * three faint bands mark the unit blocks and nothing else claims to
         * mean anything.
         */
        fillRect(image, 14, 30, 164, 2, red);
        for (int unit = 0; unit < 3; unit++)
        {
            int top = 52 + unit * 104;
            fillRect(image, 14, top, 164, 1, dim);
            fillRect(image, 14, top + 96, 164, 1, dim);
        }
        fillRect(image, 14, 356, 164, 2, red);
        tacticalTexture = new DynamicTexture(image);
        minecraft.getTextureManager().register(
                TACTICAL_TEXTURE_ID, tacticalTexture);
    }

    private static void ensureStandbyTextures(Minecraft minecraft)
    {
        for (int variant = 0; variant < STANDBY_TEXTURES.length; variant++)
        {
            if (STANDBY_TEXTURES[variant] != null)
            {
                continue;
            }
            NativeImage image = new NativeImage(
                    ServerboundEvaVideoFramePacket.FRAME_WIDTH,
                    ServerboundEvaVideoFramePacket.FRAME_HEIGHT, false);
            paintStandby(image, variant);
            DynamicTexture texture = new DynamicTexture(image);
            STANDBY_TEXTURES[variant] = texture;
            minecraft.getTextureManager().register(
                    STANDBY_TEXTURE_IDS[variant], texture);
        }
    }

    private static void paintStandby(NativeImage image, int variant)
    {
        int width = image.getWidth();
        int height = image.getHeight();
        int[] colour = UNIT_COLOURS[variant];
        int accent = rgba(colour[0], colour[1], colour[2], 255);
        int dim = rgba(colour[0] / 4, colour[1] / 4, colour[2] / 4, 255);
        int background = rgba(5, 9, 12, 255);
        for (int y = 0; y < height; y++)
        {
            for (int x = 0; x < width; x++)
            {
                boolean scan = y % 8 == 0;
                boolean grid = x % 20 == 0 || y % 20 == 0;
                image.setPixelRGBA(x, y, scan || grid ? dim : background);
            }
        }
        fillRect(image, 0, 0, width, 3, accent);
        fillRect(image, 0, height - 3, width, 3, accent);
        fillRect(image, 0, 0, 3, height, accent);
        fillRect(image, width - 3, 0, 3, height, accent);
        fillRect(image, 8, 8, 36, 4, accent);
        fillRect(image, width - 44, 8, 36, 4, accent);
        drawDigit(image, 58, 27, 0, accent);
        drawDigit(image, 82, 27, variant, accent);
        for (int bar = 0; bar < 7; bar++)
        {
            fillRect(image, 24 + bar * 17, 72, 11, 3,
                    bar < 2 ? accent : dim);
        }
    }

    private static void drawDigit(NativeImage image, int x, int y,
                                  int digit, int colour)
    {
        int mask = switch (digit)
        {
            case 1 -> 0b0000110;
            case 2 -> 0b1011011;
            default -> 0b0111111;
        };
        if ((mask & 0b0000001) != 0)
        {
            fillRect(image, x + 3, y, 13, 3, colour);
        }
        if ((mask & 0b0000010) != 0)
        {
            fillRect(image, x + 16, y + 3, 3, 12, colour);
        }
        if ((mask & 0b0000100) != 0)
        {
            fillRect(image, x + 16, y + 18, 3, 12, colour);
        }
        if ((mask & 0b0001000) != 0)
        {
            fillRect(image, x + 3, y + 30, 13, 3, colour);
        }
        if ((mask & 0b0010000) != 0)
        {
            fillRect(image, x, y + 18, 3, 12, colour);
        }
        if ((mask & 0b0100000) != 0)
        {
            fillRect(image, x, y + 3, 3, 12, colour);
        }
        if ((mask & 0b1000000) != 0)
        {
            fillRect(image, x + 3, y + 15, 13, 3, colour);
        }
    }

    private static void fillRect(NativeImage image, int x, int y,
                                 int width, int height, int colour)
    {
        for (int py = y; py < y + height; py++)
        {
            for (int px = x; px < x + width; px++)
            {
                image.setPixelRGBA(px, py, colour);
            }
        }
    }

    private static int rgba(int red, int green, int blue, int alpha)
    {
        return alpha << 24 | blue << 16 | green << 8 | red;
    }

    private static void renderScreen(PoseStack poseStack, Vec3 camera,
                                     Vec3 centre,
                                     ResourceLocation texture,
                                     Minecraft minecraft,
                                     float width, float height,
                                     float yaw, float pitch,
                                     float visibility)
    {
        float eased = visibility * visibility
                * (3.0F - 2.0F * visibility);
        if (eased <= 0.003F)
        {
            return;
        }
        poseStack.pushPose();
        poseStack.translate(centre.x - camera.x,
                centre.y - camera.y, centre.z - camera.z);
        poseStack.mulPose(Axis.YP.rotationDegrees(yaw));
        poseStack.mulPose(Axis.XP.rotationDegrees(pitch));
        // NERV-style power-on/off: luminance fades while the raster opens or
        // collapses vertically from its centre over roughly 0.4 seconds.
        poseStack.scale(1.0F, Math.max(0.015F, eased), 1.0F);
        MultiBufferSource.BufferSource buffers =
                minecraft.renderBuffers().bufferSource();
        RenderType renderType = RenderType.entityTranslucent(texture);
        VertexConsumer consumer = buffers.getBuffer(renderType);
        Matrix4f pose = poseStack.last().pose();
        Matrix3f normal = poseStack.last().normal();
        float halfWidth = width * 0.5F;
        float halfHeight = height * 0.5F;
        vertex(consumer, pose, normal,
                -halfWidth, -halfHeight, 0.0F, 0.0F, 1.0F, eased);
        vertex(consumer, pose, normal,
                halfWidth, -halfHeight, 0.0F, 1.0F, 1.0F, eased);
        vertex(consumer, pose, normal,
                halfWidth, halfHeight, 0.0F, 1.0F, 0.0F, eased);
        vertex(consumer, pose, normal,
                -halfWidth, halfHeight, 0.0F, 0.0F, 0.0F, eased);
        // The measured S20 masks are viewed both directly and through the
        // command glazing.  Emit the reverse winding as well: relying on one
        // guessed normal made every raster disappear when the camera crossed
        // the authored plane, even though the physical display was present.
        vertex(consumer, pose, normal,
                -halfWidth, halfHeight, -0.002F, 0.0F, 0.0F, eased, -1.0F);
        vertex(consumer, pose, normal,
                halfWidth, halfHeight, -0.002F, 1.0F, 0.0F, eased, -1.0F);
        vertex(consumer, pose, normal,
                halfWidth, -halfHeight, -0.002F, 1.0F, 1.0F, eased, -1.0F);
        vertex(consumer, pose, normal,
                -halfWidth, -halfHeight, -0.002F, 0.0F, 1.0F, eased, -1.0F);
        buffers.endBatch(renderType);
        poseStack.popPose();
    }

    private static void vertex(VertexConsumer consumer, Matrix4f pose,
                               Matrix3f normal, float x, float y, float z,
                               float u, float v, float alpha)
    {
        vertex(consumer, pose, normal, x, y, z, u, v, alpha, 1.0F);
    }

    private static void vertex(VertexConsumer consumer, Matrix4f pose,
                               Matrix3f normal, float x, float y, float z,
                               float u, float v, float alpha, float normalZ)
    {
        consumer.vertex(pose, x, y, z)
                .color(255, 255, 255,
                        Math.max(0, Math.min(255,
                                Math.round(alpha * 255.0F))))
                .uv(u, v)
                .overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(LightTexture.FULL_BRIGHT)
                .normal(normal, 0.0F, 0.0F, normalZ)
                .endVertex();
    }
}
