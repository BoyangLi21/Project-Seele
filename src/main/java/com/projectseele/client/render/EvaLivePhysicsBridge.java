package com.projectseele.client.render;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

import com.projectseele.ProjectSeele;
import net.minecraft.util.Mth;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/** Reads the local motion-lab MuJoCo sidecar without animation assets. */
public final class EvaLivePhysicsBridge
{
    public static final String[] BONES = {
            "torso_lower", "torso_upper", "head",
            "arm_l", "forearm_l", "hand_l",
            "arm_r", "forearm_r", "hand_r",
            "leg_l", "shin_l", "foot_l",
            "leg_r", "shin_r", "foot_r"
    };
    private static final int VISUAL_OFFSET = 768;
    private static final int SHARED_BYTES = 1280;
    private static final int FLAG_POLICY_LIVE = 1 << 8;
    private static final long STALE_NANOS = 1_000_000_000L;
    private static FileChannel channel;
    private static MappedByteBuffer mapping;
    private static long sequence;
    private static long lastArrivalNanos;
    private static long previousArrivalNanos;
    private static Snapshot previous;
    private static Snapshot current;
    private static boolean connectedLogged;
    private static boolean waitingLogged;

    private EvaLivePhysicsBridge() {}

    public static Snapshot sample()
    {
        poll();
        long now = System.nanoTime();
        if (current == null || now - lastArrivalNanos > STALE_NANOS)
        {
            if (!waitingLogged)
            {
                ProjectSeele.LOGGER.warn(
                        "EVA live physics is waiting for a fresh sidecar state");
                waitingLogged = true;
            }
            return null;
        }
        waitingLogged = false;
        if (previous == null || lastArrivalNanos <= previousArrivalNanos)
        {
            return current;
        }
        long interval = Math.max(1L, lastArrivalNanos - previousArrivalNanos);
        float alpha = Mth.clamp((float)(now - lastArrivalNanos)
                / (float)interval, 0.0F, 1.0F);
        Vector3f root = new Vector3f(previous.rootMeters)
                .lerp(current.rootMeters, alpha);
        Quaternionf[] rotations = new Quaternionf[BONES.length];
        for (int index = 0; index < rotations.length; index++)
        {
            rotations[index] = new Quaternionf(previous.rotations[index])
                    .slerp(current.rotations[index], alpha).normalize();
        }
        return new Snapshot(current.sequence, current.physicsTimestampNanos,
                current.flags, root, rotations, current.contactMask,
                current.leftForce, current.rightForce);
    }

    private static void poll()
    {
        if (!ensureMapped())
        {
            return;
        }
        try
        {
            ByteBuffer view = mapping.duplicate().order(ByteOrder.LITTLE_ENDIAN);
            long first = view.getLong(VISUAL_OFFSET);
            if (first == 0L || (first & 1L) != 0L || first == sequence)
            {
                return;
            }
            view.position(VISUAL_OFFSET + 8);
            long timestamp = view.getLong();
            int flags = view.getInt();
            view.getInt(); // unit id
            Vector3f root = new Vector3f(
                    view.getFloat(), view.getFloat(), view.getFloat());
            // Root orientation is also represented by torso_lower. Consume it
            // to keep the debug packet layout stable without applying it twice.
            view.getFloat();
            view.getFloat();
            view.getFloat();
            view.getFloat();
            Quaternionf[] rotations = new Quaternionf[BONES.length];
            for (int index = 0; index < rotations.length; index++)
            {
                float w = view.getFloat();
                float x = view.getFloat();
                float y = view.getFloat();
                float z = view.getFloat();
                rotations[index] = new Quaternionf(x, y, z, w).normalize();
            }
            long contactMask = view.getLong();
            float leftForce = view.getFloat();
            float rightForce = view.getFloat();
            long second = view.getLong(VISUAL_OFFSET);
            if (first != second || (flags & FLAG_POLICY_LIVE) == 0)
            {
                return;
            }
            Snapshot next = new Snapshot(first, timestamp, flags, root,
                    rotations, contactMask, leftForce, rightForce);
            previous = current;
            previousArrivalNanos = lastArrivalNanos;
            current = next;
            sequence = first;
            lastArrivalNanos = System.nanoTime();
            if (!connectedLogged)
            {
                connectedLogged = true;
                ProjectSeele.LOGGER.info(
                        "EVA live physics connected: sequence={} bones={} source=trained-policy+mujoco",
                        sequence, BONES.length);
            }
        }
        catch (RuntimeException exception)
        {
            closeMapping();
            ProjectSeele.LOGGER.error(
                    "EVA live physics state read failed", exception);
        }
    }

    private static boolean ensureMapped()
    {
        if (mapping != null)
        {
            return true;
        }
        Path direct = Path.of("seele_physics_live.bin");
        Path fallback = Path.of("run", "seele_physics_live.bin");
        Path path = Files.isRegularFile(direct) ? direct : fallback;
        if (!Files.isRegularFile(path))
        {
            return false;
        }
        try
        {
            channel = FileChannel.open(path, StandardOpenOption.READ);
            if (channel.size() < SHARED_BYTES)
            {
                closeMapping();
                return false;
            }
            mapping = channel.map(FileChannel.MapMode.READ_ONLY,
                    0L, SHARED_BYTES);
            mapping.order(ByteOrder.LITTLE_ENDIAN);
            return true;
        }
        catch (IOException exception)
        {
            closeMapping();
            return false;
        }
    }

    private static void closeMapping()
    {
        mapping = null;
        if (channel != null)
        {
            try
            {
                channel.close();
            }
            catch (IOException ignored)
            {
            }
        }
        channel = null;
        sequence = 0L;
        previous = null;
        current = null;
        connectedLogged = false;
    }

    public record Snapshot(long sequence, long physicsTimestampNanos,
                           int flags, Vector3f rootMeters,
                           Quaternionf[] rotations, long contactMask,
                           float leftForce, float rightForce) {}
}
