package com.projectseele.client.visual;

import com.mojang.blaze3d.platform.NativeImage;
import com.projectseele.mixin.client.NativeImagePixelsAccessor;
import java.io.IOException;
import java.nio.file.Path;
import org.lwjgl.stb.STBImageWrite;
import org.lwjgl.system.MemoryUtil;

/** Encodes an owned screenshot directly, without per-pixel Java image copies. */
public final class NativeReviewFrames
{
    public static void writeJpeg(NativeImage image,Path path)throws IOException
    {
        long address=((NativeImagePixelsAccessor)(Object)image).projectseele$getPixels();
        if(address==0)throw new IOException("Screenshot is already closed");
        int channels=image.format().components();
        int bytes=Math.multiplyExact(Math.multiplyExact(image.getWidth(),image.getHeight()),channels);
        if(!STBImageWrite.stbi_write_jpg(path.toString(),image.getWidth(),image.getHeight(),channels,MemoryUtil.memByteBuffer(address,bytes),90))
            throw new IOException("Native screenshot encoding failed: "+path);
    }
    private NativeReviewFrames(){}
}
