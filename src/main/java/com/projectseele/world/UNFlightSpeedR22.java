package com.projectseele.world;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** A finite allow-list of the commissioned F2 cruise arcs; no taxi/approach changes. */
public final class UNFlightSpeedR22
{
    private static final Set<String> EDGES=load();
    private static Set<String> load()
    {
        try(var stream=UNFlightSpeedR22.class.getResourceAsStream("/data/projectseele/transit/un_f2_fast_edges.txt"))
        {
            if(stream==null)throw new IOException("Missing F2 cruise contract");
            try(var reader=new BufferedReader(new InputStreamReader(stream,StandardCharsets.UTF_8)))
            {return new HashSet<>(reader.lines().filter(s->!s.isBlank()).toList());}
        }
        catch(IOException e){throw new ExceptionInInitializerError(e);}
    }
    private static final ClassValue<java.lang.reflect.Method[]> POSITION=new ClassValue<>()
    {
        @Override protected java.lang.reflect.Method[] computeValue(Class<?> c)
        {try{return new java.lang.reflect.Method[]{c.getMethod("getX"),c.getMethod("getY"),c.getMethod("getZ")};}catch(Exception e){throw new IllegalStateException(e);}}
    };
    private static final ClassValue<java.lang.reflect.Method[]> PATH=new ClassValue<>()
    {
        @Override protected java.lang.reflect.Method[] computeValue(Class<?> c)
        {try{return new java.lang.reflect.Method[]{c.getMethod("getOrderedPosition1"),c.getMethod("getOrderedPosition2")};}catch(Exception e){throw new IllegalStateException(e);}}
    };
    private static String point(Object p) throws ReflectiveOperationException
    {var m=POSITION.get(p.getClass());return m[0].invoke(p)+","+m[1].invoke(p)+","+m[2].invoke(p);}
    public static long adjust(long speed,Object path)
    {
        if(speed!=300)return speed;
        try
        {
            var methods=PATH.get(path.getClass());String a=point(methods[0].invoke(path)),b=point(methods[1].invoke(path));
            return EDGES.contains(a+">"+b)||EDGES.contains(b+">"+a)?540:speed;
        }
        catch(ReflectiveOperationException e){throw new IllegalStateException("MTR path API changed",e);}
    }
    private UNFlightSpeedR22(){}
}
