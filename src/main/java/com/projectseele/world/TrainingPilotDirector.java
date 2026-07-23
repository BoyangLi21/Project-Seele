package com.projectseele.world;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.zip.CRC32;
import java.util.zip.DeflaterOutputStream;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EntryPlugCarrierEntity;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.TrainingPilotEntity;
import com.projectseele.network.ServerboundEvaVideoFramePacket;
import com.projectseele.registry.ModEntities;
import com.projectseele.registry.ModFluids;
import com.projectseele.visual.GeoFrontCommands;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

/** Drives visible dummy boarding and a server-rendered training optical feed. */
public final class TrainingPilotDirector
{
    private static final int FEED_INTERVAL_TICKS = 10;
    private static final int SAMPLE_WIDTH = 40;
    private static final int SAMPLE_HEIGHT = 23;
    private static final double FEED_RANGE = 160.0D;
    private static final double TAN_HALF_FOV_X = Math.tan(Math.toRadians(35.0D));
    private static final double TAN_HALF_FOV_Y = Math.tan(Math.toRadians(22.0D));
    private static final int[] UNIT_COLOURS = {
            0xE88F26, 0x903ECD, 0xD22D34
    };

    private TrainingPilotDirector() {}

    public static ActionResult start(ServerLevel level, int variant)
    {
        EvaHangarBuilder.ensure(level, IntegratedNervMapBuilder.GEOFRONT_ORIGIN);
        EvaLogisticsDirector.ensureFleet(level);
        EvaUnit01Entity unit = EvaLogisticsDirector.canonicalUnit(level, variant);
        if (unit == null || !unit.isAlive())
        {
            return new ActionResult(false, label(variant) + " is not loaded.");
        }
        EntryPlugCarrierEntity plug = EntryPlugDirector.ensureSuspended(level,
                variant, unit);
        if (unit.getFirstPassenger() != null
                || plug != null && plug.getFirstPassenger() != null)
        {
            return new ActionResult(false, label(variant)
                    + " already has an entry-plug occupant.");
        }
        if (plug == null)
        {
            return new ActionResult(false, label(variant)
                    + " external entry plug is unavailable.");
        }
        stop(level, variant);
        TrainingPilotEntity pilot = ModEntities.TRAINING_PILOT.get().create(level);
        if (pilot == null)
        {
            return new ActionResult(false, "Training pilot entity creation failed.");
        }
        BlockPos origin = IntegratedNervMapBuilder.GEOFRONT_ORIGIN;
        BlockPos start = origin.offset(0, EvaHangarBuilder.GALLERY_Y + 1,
                EvaHangarBuilder.GALLERY_Z - 1);
        pilot.assignVariant(variant);
        pilot.setTrainingStage(TrainingPilotEntity.STAGE_WALKING);
        pilot.moveTo(start.getX() + 0.5D, start.getY(), start.getZ() + 0.5D,
                0.0F, 0.0F);
        if (!level.addFreshEntity(pilot))
        {
            return new ActionResult(false, "Training pilot spawn was rejected.");
        }
        ProjectSeele.LOGGER.info(
                "NERV training pilot dispatched: eva={} pilot={} start={}",
                variant, pilot.getStringUUID(), start.toShortString());
        return new ActionResult(true, label(variant)
                + " dummy is walking to the dorsal boarding bridge.");
    }

    public static int stop(ServerLevel level, int variant)
    {
        int removed = 0;
        for (TrainingPilotEntity pilot : pilots(level))
        {
            if (variant >= 0 && pilot.getAssignedVariant() != variant)
            {
                continue;
            }
            pilot.stopRiding();
            pilot.discard();
            removed++;
        }
        return removed;
    }

    public static List<TrainingPilotEntity> pilots(ServerLevel level)
    {
        List<TrainingPilotEntity> result = new ArrayList<>();
        for (Entity entity : level.getAllEntities())
        {
            if (entity instanceof TrainingPilotEntity pilot && pilot.isAlive())
            {
                result.add(pilot);
            }
        }
        return result;
    }

    public static void tickPilot(TrainingPilotEntity pilot)
    {
        if (!(pilot.level() instanceof ServerLevel level)
                || !level.dimension().equals(GeoFrontCommands.GEOFRONT))
        {
            return;
        }
        int variant = pilot.getAssignedVariant();
        if (pilot.getVehicle() instanceof EntryPlugCarrierEntity plug)
        {
            if (plug.getAssignedVariant() != variant)
            {
                pilot.stopRiding();
                return;
            }
            pilot.setInvisible(true);
            pilot.setTrainingStage(TrainingPilotEntity.STAGE_IN_PLUG);
            return;
        }
        if (pilot.getVehicle() instanceof EvaUnit01Entity unit)
        {
            if (unit.getUnitVariant() != variant)
            {
                pilot.stopRiding();
                return;
            }
            pilot.setInvisible(true);
            pilot.setTrainingStage(TrainingPilotEntity.STAGE_LINKED);
            float scan = (float) Math.sin((pilot.tickCount + variant * 37)
                    * 0.025D);
            float pitchScan = (float) Math.sin((pilot.tickCount + variant * 19)
                    * 0.017D);
            float yaw = unit.getYRot() + scan * 34.0F;
            float pitch = -4.0F + pitchScan * 12.0F;
            pilot.setYRot(yaw);
            pilot.setXRot(pitch);
            pilot.yBodyRot = yaw;
            pilot.yHeadRot = yaw;
            return;
        }

        pilot.setInvisible(false);
        pilot.setTrainingStage(TrainingPilotEntity.STAGE_WALKING);
        EvaUnit01Entity unit = EvaLogisticsDirector.canonicalUnit(level, variant);
        EntryPlugCarrierEntity plug = unit == null ? null
                : EntryPlugDirector.ensureSuspended(level, variant, unit);
        if (unit == null || !unit.isAlive() || unit.getFirstPassenger() != null
                || plug == null || plug.getFirstPassenger() != null)
        {
            pilot.getNavigation().stop();
            return;
        }
        BlockPos target = EvaHangarBuilder.boardingPosition(
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN, variant);
        Vec3 destination = Vec3.atBottomCenterOf(target);
        if (pilot.position().distanceToSqr(destination) <= 2.75D * 2.75D)
        {
            pilot.getNavigation().stop();
            if (plug.boardPassenger(pilot))
            {
                pilot.setInvisible(true);
                pilot.setTrainingStage(TrainingPilotEntity.STAGE_IN_PLUG);
                level.playSound(null, target, SoundEvents.IRON_DOOR_CLOSE,
                        SoundSource.BLOCKS, 1.4F, 0.78F);
                ProjectSeele.LOGGER.info(
                        "NERV training pilot boarded external plug: eva={} pilot={} bridge={}",
                        variant, pilot.getStringUUID(), target.toShortString());
            }
            return;
        }
        if (pilot.tickCount % 20 == 1 || pilot.getNavigation().isDone())
        {
            pilot.getNavigation().moveTo(destination.x, destination.y,
                    destination.z, 1.05D);
        }
        pilot.getLookControl().setLookAt(unit, 25.0F, 25.0F);
    }

    public static void tickFeeds(MinecraftServer server)
    {
        if (server.getTickCount() % FEED_INTERVAL_TICKS != 0)
        {
            return;
        }
        ServerLevel level = server.getLevel(GeoFrontCommands.GEOFRONT);
        if (level == null
                || !ServerboundEvaVideoFramePacket.hasCommandViewers(level))
        {
            return;
        }
        for (TrainingPilotEntity pilot : pilots(level))
        {
            if (!(pilot.getVehicle() instanceof EvaUnit01Entity unit)
                    || unit.getFirstPassenger() != pilot
                    || ServerboundEvaVideoFramePacket.isHumanFeedActive(
                            level, unit.getUnitVariant()))
            {
                continue;
            }
            byte[] png = trainingFrame(level, pilot, unit);
            ServerboundEvaVideoFramePacket.relayTrainingFrame(
                    level, unit.getUnitVariant(), png);
        }
    }

    private static byte[] trainingFrame(ServerLevel level,
                                        TrainingPilotEntity pilot,
                                        EvaUnit01Entity unit)
    {
        int[] samples = new int[SAMPLE_WIDTH * SAMPLE_HEIGHT];
        Vec3 eye = pilot.getEyePosition();
        Vec3 forward = Vec3.directionFromRotation(
                pilot.getXRot(), pilot.getYRot()).normalize();
        Vec3 right = forward.cross(new Vec3(0.0D, 1.0D, 0.0D));
        right = right.lengthSqr() < 1.0E-6D
                ? new Vec3(1.0D, 0.0D, 0.0D) : right.normalize();
        Vec3 up = right.cross(forward).normalize();
        for (int row = 0; row < SAMPLE_HEIGHT; row++)
        {
            double vertical = (1.0D - (row + 0.5D)
                    / SAMPLE_HEIGHT * 2.0D) * TAN_HALF_FOV_Y;
            for (int column = 0; column < SAMPLE_WIDTH; column++)
            {
                double horizontal = ((column + 0.5D)
                        / SAMPLE_WIDTH * 2.0D - 1.0D) * TAN_HALF_FOV_X;
                Vec3 direction = forward.add(right.scale(horizontal))
                        .add(up.scale(vertical)).normalize();
                BlockHitResult hit = level.clip(new ClipContext(
                        eye, eye.add(direction.scale(FEED_RANGE)),
                        ClipContext.Block.COLLIDER, ClipContext.Fluid.ANY,
                        pilot));
                samples[row * SAMPLE_WIDTH + column] = sampleColour(
                        level, eye, direction, hit);
            }
        }
        int width = ServerboundEvaVideoFramePacket.FRAME_WIDTH;
        int height = ServerboundEvaVideoFramePacket.FRAME_HEIGHT;
        int[] pixels = new int[width * height];
        for (int y = 0; y < height; y++)
        {
            int sourceY = y * SAMPLE_HEIGHT / height;
            for (int x = 0; x < width; x++)
            {
                int sourceX = x * SAMPLE_WIDTH / width;
                int colour = samples[sourceY * SAMPLE_WIDTH + sourceX];
                if ((y & 3) == 3)
                {
                    colour = shade(colour, 0.82D);
                }
                pixels[y * width + x] = colour;
            }
        }
        paintOverlay(pixels, width, height, unit.getUnitVariant());
        return encodePng(width, height, pixels);
    }

    private static int sampleColour(ServerLevel level, Vec3 eye,
                                    Vec3 direction, BlockHitResult hit)
    {
        if (hit.getType() == HitResult.Type.MISS)
        {
            double sky = Mth.clamp(direction.y * 0.5D + 0.5D, 0.0D, 1.0D);
            return mix(0x182538, 0x78A9E8, sky);
        }
        BlockPos position = hit.getBlockPos();
        BlockState state = level.getBlockState(position);
        int colour;
        if (state.getFluidState().getFluidType() == ModFluids.LCL_TYPE.get())
        {
            colour = 0xE98720;
        }
        else if (state.getFluidState().is(FluidTags.WATER))
        {
            colour = 0x315FAD;
        }
        else if (state.getFluidState().is(FluidTags.LAVA))
        {
            colour = 0xF04A16;
        }
        else if (state.is(BlockTags.LEAVES)
                || state.is(Blocks.GRASS_BLOCK)
                || state.is(Blocks.MOSS_BLOCK))
        {
            colour = 0x497B36;
        }
        else
        {
            colour = state.getMapColor(level, position).col;
            if (colour == 0)
            {
                colour = 0x777A80;
            }
        }
        double distance = eye.distanceTo(hit.getLocation());
        double brightness = Mth.clamp(1.05D - distance / 240.0D,
                0.38D, 1.0D);
        brightness *= switch (hit.getDirection())
        {
            case DOWN -> 0.58D;
            case NORTH, SOUTH -> 0.83D;
            case EAST, WEST -> 0.70D;
            default -> 1.0D;
        };
        return shade(colour, brightness);
    }

    private static void paintOverlay(int[] pixels, int width, int height,
                                     int variant)
    {
        int accent = UNIT_COLOURS[Mth.clamp(variant, 0, 2)];
        fill(pixels, width, height, 0, 0, width, 2, accent);
        fill(pixels, width, height, 0, height - 2, width, 2, accent);
        fill(pixels, width, height, 0, 0, 2, height, accent);
        fill(pixels, width, height, width - 2, 0, 2, height, accent);
        fill(pixels, width, height, 8, 7, 28, 2, accent);
        fill(pixels, width, height, width - 36, 7, 28, 2, accent);
        int centreX = width / 2;
        int centreY = height / 2;
        fill(pixels, width, height, centreX - 8, centreY, 6, 1, accent);
        fill(pixels, width, height, centreX + 3, centreY, 6, 1, accent);
        fill(pixels, width, height, centreX, centreY - 8, 1, 6, accent);
        fill(pixels, width, height, centreX, centreY + 3, 1, 6, accent);
        for (int bar = 0; bar < 8; bar++)
        {
            fill(pixels, width, height, 12 + bar * 9, height - 10,
                    6, 2, bar < 5 ? accent : shade(accent, 0.35D));
        }
    }

    private static void fill(int[] pixels, int width, int height,
                             int x, int y, int areaWidth, int areaHeight,
                             int colour)
    {
        for (int py = Math.max(0, y); py < Math.min(height, y + areaHeight); py++)
        {
            for (int px = Math.max(0, x); px < Math.min(width, x + areaWidth); px++)
            {
                pixels[py * width + px] = colour;
            }
        }
    }

    private static int mix(int from, int to, double amount)
    {
        double safe = Mth.clamp(amount, 0.0D, 1.0D);
        int red = (int) Mth.lerp(safe, from >> 16 & 0xFF, to >> 16 & 0xFF);
        int green = (int) Mth.lerp(safe, from >> 8 & 0xFF, to >> 8 & 0xFF);
        int blue = (int) Mth.lerp(safe, from & 0xFF, to & 0xFF);
        return red << 16 | green << 8 | blue;
    }

    private static int shade(int colour, double brightness)
    {
        int red = Mth.clamp((int) ((colour >> 16 & 0xFF) * brightness), 0, 255);
        int green = Mth.clamp((int) ((colour >> 8 & 0xFF) * brightness), 0, 255);
        int blue = Mth.clamp((int) ((colour & 0xFF) * brightness), 0, 255);
        return red << 16 | green << 8 | blue;
    }

    private static byte[] encodePng(int width, int height, int[] pixels)
    {
        try
        {
            ByteArrayOutputStream raw = new ByteArrayOutputStream(
                    height * (width * 3 + 1));
            for (int y = 0; y < height; y++)
            {
                raw.write(0);
                for (int x = 0; x < width; x++)
                {
                    int colour = pixels[y * width + x];
                    raw.write(colour >> 16 & 0xFF);
                    raw.write(colour >> 8 & 0xFF);
                    raw.write(colour & 0xFF);
                }
            }
            ByteArrayOutputStream compressed = new ByteArrayOutputStream();
            try (DeflaterOutputStream deflater =
                         new DeflaterOutputStream(compressed))
            {
                raw.writeTo(deflater);
            }
            ByteArrayOutputStream png = new ByteArrayOutputStream();
            DataOutputStream output = new DataOutputStream(png);
            output.write(new byte[] {(byte) 0x89, 0x50, 0x4E, 0x47,
                    0x0D, 0x0A, 0x1A, 0x0A});
            ByteArrayOutputStream headerBytes = new ByteArrayOutputStream();
            DataOutputStream header = new DataOutputStream(headerBytes);
            header.writeInt(width);
            header.writeInt(height);
            header.writeByte(8);
            header.writeByte(2);
            header.writeByte(0);
            header.writeByte(0);
            header.writeByte(0);
            writeChunk(output, "IHDR", headerBytes.toByteArray());
            writeChunk(output, "IDAT", compressed.toByteArray());
            writeChunk(output, "IEND", new byte[0]);
            output.flush();
            return png.toByteArray();
        }
        catch (IOException exception)
        {
            ProjectSeele.LOGGER.error("Unable to encode NERV training feed", exception);
            return new byte[0];
        }
    }

    private static void writeChunk(DataOutputStream output, String type,
                                   byte[] data) throws IOException
    {
        byte[] name = type.getBytes(java.nio.charset.StandardCharsets.US_ASCII);
        output.writeInt(data.length);
        output.write(name);
        output.write(data);
        CRC32 crc = new CRC32();
        crc.update(name);
        crc.update(data);
        output.writeInt((int) crc.getValue());
    }

    private static String label(int variant)
    {
        return String.format(Locale.ROOT, "EVA-%02d", variant);
    }

    public record ActionResult(boolean accepted, String message) {}
}
