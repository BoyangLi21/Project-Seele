package com.projectseele.network;

import java.util.Arrays;

/** Bounded chunking contract for 720p cockpit frames on Forge payloads. */
public final class EvaVideoFrameTransport
{
    public static final int MAX_FRAME_BYTES = 1024 * 1024;
    public static final int MAX_CHUNK_BYTES = 24 * 1024;
    public static final int MAX_CHUNKS =
            (MAX_FRAME_BYTES + MAX_CHUNK_BYTES - 1) / MAX_CHUNK_BYTES;
    private static final long ASSEMBLY_TIMEOUT_NANOS = 5_000_000_000L;

    private EvaVideoFrameTransport() {}

    public static int chunkCount(int totalBytes)
    {
        return (totalBytes + MAX_CHUNK_BYTES - 1) / MAX_CHUNK_BYTES;
    }

    public static byte[] chunk(byte[] frame, int chunkIndex)
    {
        int start = chunkIndex * MAX_CHUNK_BYTES;
        int end = Math.min(frame.length, start + MAX_CHUNK_BYTES);
        return Arrays.copyOfRange(frame, start, end);
    }

    public static boolean validHeader(int chunkIndex, int chunkCount,
                                      int totalBytes, byte[] chunk)
    {
        if (totalBytes <= 0 || totalBytes > MAX_FRAME_BYTES
                || chunkCount <= 0 || chunkCount > MAX_CHUNKS
                || chunkCount != chunkCount(totalBytes)
                || chunkIndex < 0 || chunkIndex >= chunkCount
                || chunk == null)
        {
            return false;
        }
        int expected = Math.min(MAX_CHUNK_BYTES,
                totalBytes - chunkIndex * MAX_CHUNK_BYTES);
        return expected > 0 && chunk.length == expected;
    }

    public static final class Assembly
    {
        private final int frameId;
        private final int totalBytes;
        private final byte[][] chunks;
        private int receivedChunks;
        private int receivedBytes;
        private long lastTouchedNanos;

        public Assembly(int frameId, int chunkCount, int totalBytes)
        {
            this.frameId = frameId;
            this.totalBytes = totalBytes;
            this.chunks = new byte[chunkCount][];
            this.lastTouchedNanos = System.nanoTime();
        }

        public boolean matches(int wantedFrameId, int chunkCount,
                               int wantedTotalBytes)
        {
            return this.frameId == wantedFrameId
                    && this.chunks.length == chunkCount
                    && this.totalBytes == wantedTotalBytes;
        }

        public boolean accept(int chunkIndex, byte[] chunk)
        {
            if (!validHeader(chunkIndex, this.chunks.length,
                    this.totalBytes, chunk))
            {
                return false;
            }
            this.lastTouchedNanos = System.nanoTime();
            if (this.chunks[chunkIndex] != null)
            {
                return Arrays.equals(this.chunks[chunkIndex], chunk);
            }
            this.chunks[chunkIndex] = chunk;
            this.receivedChunks++;
            this.receivedBytes += chunk.length;
            return true;
        }

        public boolean complete()
        {
            return this.receivedChunks == this.chunks.length
                    && this.receivedBytes == this.totalBytes;
        }

        public boolean expired(long nowNanos)
        {
            return nowNanos - this.lastTouchedNanos
                    > ASSEMBLY_TIMEOUT_NANOS;
        }

        public byte[] join()
        {
            if (!complete())
            {
                return null;
            }
            byte[] frame = new byte[this.totalBytes];
            int offset = 0;
            for (byte[] chunk : this.chunks)
            {
                System.arraycopy(chunk, 0, frame, offset, chunk.length);
                offset += chunk.length;
            }
            return frame;
        }
    }
}
