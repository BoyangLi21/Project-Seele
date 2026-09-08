package com.projectseele.network;

import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import javax.imageio.IIOImage;
import javax.imageio.ImageIO;
import javax.imageio.ImageWriteParam;
import javax.imageio.plugins.jpeg.JPEGImageWriteParam;
import javax.imageio.stream.MemoryCacheImageOutputStream;

/** A cockpit image is compressed to its byte budget before entering the transport. */
public final class EvaFrameCodec
{
    public static final int MIN_WIDTH = 320;
    public static final int MAX_WIDTH = 1920;
    public static final int MAX_HEIGHT = 1080;
    public record Size(int width,int height) {}
    public record Encoded(byte[] bytes,int width,int height,float quality) {}

    private EvaFrameCodec() {}

    public static boolean allowedSize(int width,int height)
    {
        return width>=MIN_WIDTH&&width<=MAX_WIDTH&&height>=180&&height<=MAX_HEIGHT
                &&width*9==height*16;
    }

    public static Encoded encode(BufferedImage image,float requestedQuality,int byteBudget) throws IOException
    {
        if(!allowedSize(image.getWidth(),image.getHeight()))throw new IOException("Unsupported cockpit image size");
        int budget=Math.min(EvaVideoFrameTransport.MAX_FRAME_BYTES,Math.max(16*1024,byteBudget));
        float quality=Math.max(.18F,Math.min(.94F,requestedQuality));
        BufferedImage current=image;
        while(true)
        {
            float last=-1;
            for(float candidate:new float[]{quality,.72F,.52F,.36F,.22F,.18F})
            {
                float q=Math.min(quality,candidate);if(q==last)continue;last=q;
                byte[] bytes=jpeg(current,q);
                if(bytes.length<=budget)return new Encoded(bytes,current.getWidth(),current.getHeight(),q);
            }
            int width=Math.max(MIN_WIDTH,(current.getWidth()*3/4)/16*16);
            if(width==current.getWidth())throw new IOException("Cockpit image cannot fit the configured budget");
            BufferedImage smaller=new BufferedImage(width,width*9/16,BufferedImage.TYPE_INT_RGB);
            Graphics2D graphics=smaller.createGraphics();
            try
            {
                graphics.setRenderingHint(RenderingHints.KEY_INTERPOLATION,RenderingHints.VALUE_INTERPOLATION_BILINEAR);
                graphics.drawImage(current,0,0,smaller.getWidth(),smaller.getHeight(),null);
            }
            finally { graphics.dispose(); }
            current=smaller;
        }
    }

    private static byte[] jpeg(BufferedImage image,float quality) throws IOException
    {
        var writers=ImageIO.getImageWritersByFormatName("jpeg");
        if(!writers.hasNext())throw new IOException("JPEG writer unavailable");
        var writer=writers.next();
        try(var bytes=new ByteArrayOutputStream();var output=new MemoryCacheImageOutputStream(bytes))
        {
            writer.setOutput(output);var parameters=writer.getDefaultWriteParam();
            parameters.setCompressionMode(ImageWriteParam.MODE_EXPLICIT);parameters.setCompressionQuality(quality);
            if(parameters instanceof JPEGImageWriteParam jpeg)jpeg.setOptimizeHuffmanTables(true);
            writer.write(null,new IIOImage(image,null,null),parameters);output.flush();return bytes.toByteArray();
        }
        finally { writer.dispose(); }
    }

    /** Header-only validation bounds the allocation before either client decodes pixels. */
    public static Size inspect(byte[] data)
    {
        if(data==null||data.length<24||data.length>EvaVideoFrameTransport.MAX_FRAME_BYTES)return null;
        if((data[0]&255)==137&&data[1]==80&&data[2]==78&&data[3]==71&&data[4]==13&&data[5]==10&&data[6]==26&&data[7]==10)
        {
            if(data[12]!=73||data[13]!=72||data[14]!=68||data[15]!=82)return null;
            int width=integer(data,16),height=integer(data,20);
            return allowedSize(width,height)?new Size(width,height):null;
        }
        if((data[0]&255)!=255||(data[1]&255)!=216)return null;
        int at=2;
        while(at+4<=data.length)
        {
            if((data[at++]&255)!=255)return null;
            while(at<data.length&&(data[at]&255)==255)at++;
            if(at>=data.length)return null;
            int marker=data[at++]&255;
            if(marker==216||marker==217||marker==1||marker>=208&&marker<=215)continue;
            if(at+2>data.length)return null;
            int length=shortValue(data,at);
            if(length<2||at+length>data.length)return null;
            if(marker>=192&&marker<=207&&marker!=196&&marker!=200&&marker!=204)
            {
                if(length<8)return null;
                int height=shortValue(data,at+3),width=shortValue(data,at+5);
                return allowedSize(width,height)?new Size(width,height):null;
            }
            if(marker==218)return null;
            at+=length;
        }
        return null;
    }

    private static int shortValue(byte[] data,int at) { return (data[at]&255)<<8|data[at+1]&255; }
    private static int integer(byte[] data,int at)
    {
        return (data[at]&255)<<24|(data[at+1]&255)<<16|(data[at+2]&255)<<8|data[at+3]&255;
    }
}
