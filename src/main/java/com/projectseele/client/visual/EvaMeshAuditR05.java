package com.projectseele.client.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.zip.GZIPOutputStream;
import java.io.OutputStreamWriter;
import org.joml.Matrix4f;
import org.joml.Vector3f;

/** Test-only capture of vertices actually submitted to the renderer, after joint skinning. */
public final class EvaMeshAuditR05
{
    private static final int[] KEYS={25,65,70,75,80,89,103,130,155,190,270,295,318,345,385,390,396,405,416,440,510,588,610,618,626,639};
    private static int next,target,tick;
    private static JsonObject frame,parts;
    private static Path folder;
    public static void begin(int currentTick,int entity,Path output)
    {
        int cycles=Boolean.getBoolean("projectseele.motionReviewR05All")?3:1;
        frame=null;if(next>=KEYS.length*cycles||currentTick<KEYS[next%KEYS.length]+650*(next/KEYS.length))return;
        tick=currentTick;target=entity;folder=output;frame=new JsonObject();parts=new JsonObject();frame.addProperty("tick",tick);frame.add("parts",parts);
        var level=net.minecraft.client.Minecraft.getInstance().level;
        if(level!=null&&level.getEntity(entity) instanceof com.projectseele.entity.EvaUnit01Entity eva)
        {
            frame.addProperty("variant",eva.getUnitVariant());frame.addProperty("floor",eva.getY());
        }
    }
    public static void capture(int entity,String part,float[] vertices,int stride,float px,float py,float pz,Matrix4f world)
    {
        if(frame==null||target!=entity||parts.has(part))return;
        JsonArray points=new JsonArray();Vector3f v=new Vector3f();
        for(int i=0;i<vertices.length;i+=stride)
        {
            world.transformPosition(v.set(-(vertices[i]+px)/16,(vertices[i+1]+py)/16,(vertices[i+2]+pz)/16));
            points.add(v.x);points.add(v.y);points.add(v.z);
        }
        parts.add(part,points);
    }
    public static void end()
    {
        if(frame==null||parts.size()==0)return;
        try
        {
            Files.createDirectories(folder);
            try(var stream=new GZIPOutputStream(Files.newOutputStream(folder.resolve(String.format("mesh_%04d.json.gz",tick))));var writer=new OutputStreamWriter(stream,StandardCharsets.UTF_8))
            {writer.write(frame.toString());}
            next++;ProjectSeele.LOGGER.info("R05 drawn mesh captured: tick={} parts={}",tick,parts.size());
        }
        catch(Exception failure){throw new IllegalStateException("Native mesh evidence",failure);}
        frame=null;
    }
}
