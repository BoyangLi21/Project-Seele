package com.projectseele.network;

import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.util.Arrays;
import java.util.Random;
import javax.imageio.ImageIO;

/** Codec and transport tests use actual high-entropy images and decoded pixels. */
public final class EvaVideoCodecTest
{
    private static void require(boolean condition,String message)
    {
        if(!condition)throw new AssertionError(message);
    }

    public static void main(String[] arguments) throws Exception
    {
        long start=System.nanoTime();int cases=0,maxBytes=0;Random random=new Random(260908);
        for(int width:new int[]{640,1280,1920})for(boolean noisy:new boolean[]{false,true})
        {
            int height=width*9/16;
            BufferedImage original=new BufferedImage(width,height,BufferedImage.TYPE_INT_RGB);
            for(int y=0;y<height;y++)for(int x=0;x<width;x++)
                original.setRGB(x,y,noisy?random.nextInt(1<<24):(x*255/width)<<16|(y*255/height)<<8|83);
            for(int budget:new int[]{64*1024,384*1024,768*1024})
            {
                var encoded=EvaFrameCodec.encode(original,.94F,budget);byte[] data=encoded.bytes();
                require(data.length<=budget,"Frame exceeded byte budget");
                var size=EvaFrameCodec.inspect(data);require(size!=null,"Encoder produced invalid header");
                var decoded=ImageIO.read(new ByteArrayInputStream(data));
                require(decoded.getWidth()==size.width()&&decoded.getHeight()==size.height(),"Header and decoded dimensions differ");
                require(decoded.getWidth()<=width,"Codec upscaled unexpectedly");
                if(!noisy&&budget>=384*1024)
                {
                    int pixel=decoded.getRGB(decoded.getWidth()/2,decoded.getHeight()/2);
                    require(Math.abs(((pixel>>16)&255)-127)<8&&Math.abs((pixel&255)-83)<8,"Colour channels changed");
                }
                int chunks=EvaVideoFrameTransport.chunkCount(data.length);
                var assembly=new EvaVideoFrameTransport.Assembly(4,chunks,data.length);
                for(int n=chunks-1;n>=0;n--)
                {
                    byte[] chunk=EvaVideoFrameTransport.chunk(data,n);
                    require(assembly.accept(n,chunk),"Out-of-order chunk rejected");
                    require(assembly.accept(n,chunk),"Identical duplicate rejected");
                }
                require(assembly.complete()&&Arrays.equals(data,assembly.join()),"Assembled frame differs");
                byte[] conflict=EvaVideoFrameTransport.chunk(data,0);conflict[0]^=1;
                require(!assembly.accept(0,conflict),"Conflicting duplicate accepted");
                maxBytes=Math.max(maxBytes,data.length);cases++;
            }
        }
        require(EvaFrameCodec.inspect(new byte[26])==null,"Random header accepted");
        require(EvaFrameCodec.inspect(new byte[EvaVideoFrameTransport.MAX_FRAME_BYTES+1])==null,"Oversized frame accepted");
        require(!EvaFrameCodec.allowedSize(8192,4608)&&!EvaFrameCodec.allowedSize(1280,1080),"Invalid dimensions accepted");
        require(!EvaVideoFrameTransport.validHeader(0,1,10,new byte[11]),"Bad fragment length accepted");
        System.out.printf("Cockpit codec PASS: %d actual-image cases; maximum=%d bytes; elapsed=%.2fs%n",cases,maxBytes,(System.nanoTime()-start)/1e9);
    }
}
