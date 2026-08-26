package com.projectseele.world;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

import com.projectseele.ProjectSeele;

/** Writes sparse operator commands to the local motion-lab sidecar. */
final class EvaLivePhysicsControl
{
    private static final int COMMAND_BYTES = 256;
    private static final int FLAG_RESET = 1 << 0;
    private static final int FLAG_IMPULSE = 1 << 1;

    private EvaLivePhysicsControl() {}

    static boolean reset(int unitId)
    {
        return write(unitId, FLAG_RESET, 0.0F, 0.0F);
    }

    static boolean lateralImpulse(int unitId, float deltaVelocity)
    {
        return write(unitId, FLAG_IMPULSE, 0.0F, deltaVelocity);
    }

    private static boolean write(int unitId, int flags,
                                 float velocityX, float velocityY)
    {
        Path direct = Path.of("seele_physics_live.bin");
        Path fallback = Path.of("run", "seele_physics_live.bin");
        Path path = Files.isRegularFile(direct) ? direct : fallback;
        if (!Files.isRegularFile(path))
        {
            return false;
        }
        try (FileChannel channel = FileChannel.open(path,
                StandardOpenOption.READ, StandardOpenOption.WRITE))
        {
            ByteBuffer old = ByteBuffer.allocate(Long.BYTES)
                    .order(ByteOrder.LITTLE_ENDIAN);
            channel.read(old, 0L);
            old.flip();
            long sequence = old.remaining() == Long.BYTES
                    ? old.getLong() + 1L : 1L;
            ByteBuffer packet = ByteBuffer.allocate(COMMAND_BYTES)
                    .order(ByteOrder.LITTLE_ENDIAN);
            packet.putLong(sequence);
            packet.putLong(System.nanoTime());
            packet.putInt(flags);
            packet.putInt(unitId);
            packet.putFloat(velocityX);
            packet.putFloat(velocityY);
            packet.position(COMMAND_BYTES);
            packet.flip();
            while (packet.hasRemaining())
            {
                channel.write(packet, 0L + packet.position());
            }
            channel.force(false);
            return true;
        }
        catch (IOException exception)
        {
            ProjectSeele.LOGGER.error(
                    "EVA live physics command write failed", exception);
            return false;
        }
    }
}
