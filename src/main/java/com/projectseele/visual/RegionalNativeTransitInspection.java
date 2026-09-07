package com.projectseele.visual;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.lang.reflect.Field;
import java.util.Collection;

/** Read-only inspection of the installed MTR version without a compile-time dependency. */
public final class RegionalNativeTransitInspection
{
    /** Read-only regression at exact terminal distances and smoothing overshoots. */
    public static JsonObject checkRouteEndpoints() throws ReflectiveOperationException
    {
        Object sim=simulator();JsonArray results=new JsonArray();
        var vehicleClass=Class.forName("org.mtr.core.data.Vehicle");
        var doubles=Class.forName("org.mtr.libraries.it.unimi.dsi.fastutil.doubles.DoubleArrayList");
        var sample=vehicleClass.getDeclaredMethod("getPosition",double.class,doubles);sample.setAccessible(true);
        for(Object siding:(Iterable<?>)sim.getClass().getField("sidings").get(sim))
        {
            String name=(String)siding.getClass().getMethod("getName").invoke(siding);
            if(!name.startsWith("F1 ")&&!name.startsWith("C1 "))continue;
            var field=siding.getClass().getDeclaredField("vehicles");field.setAccessible(true);
            for(Object vehicle:(Iterable<?>)field.get(siding))
            {
                if(!(Boolean)vehicleClass.getMethod("getIsOnRoute").invoke(vehicle))continue;
                Object extra=vehicleClass.getField("vehicleExtraData").get(vehicle);
                var path=(java.util.List<?>)extra.getClass().getField("immutablePath").get(extra);
                Object last=path.get(path.size()-2),sentinel=path.get(path.size()-1);
                if(((Number)sentinel.getClass().getMethod("getEndDistance").invoke(sentinel)).doubleValue()!=Double.MAX_VALUE)continue;
                double boundary=((Number)last.getClass().getMethod("getEndDistance").invoke(last)).doubleValue();
                double length=((Number)last.getClass().getMethod("getRailLength").invoke(last)).doubleValue();
                for(double offset:new double[]{-.001,0,.75})
                {
                    Object actual=sample.invoke(vehicle,boundary+offset,doubles.getConstructor().newInstance());
                    Object expected=last.getClass().getMethod("getPosition",double.class).invoke(last,length+Math.min(0,offset));
                    double error=0;
                    for(String axis:new String[]{"x","y","z"})error+=Math.pow(actual.getClass().getField(axis).getDouble(actual)-expected.getClass().getField(axis).getDouble(expected),2);
                    if(error>.000001)throw new IllegalStateException("Native endpoint sample left the actual rail: "+name+" offset="+offset+" error="+error);
                    JsonObject row=new JsonObject();row.addProperty("service",name);row.addProperty("offset",offset);row.addProperty("error",Math.sqrt(error));results.add(row);
                }
            }
        }
        if(results.size()<6)throw new IllegalStateException("Both native repeating services must be present for endpoint checks");
        JsonObject result=new JsonObject();result.addProperty("passed",true);result.add("samples",results);return result;
    }
    public static Object simulator() throws ReflectiveOperationException
    {
        Field mainField = Class.forName("org.mtr.mod.Init").getDeclaredField("main");
        mainField.setAccessible(true);
        Object main = mainField.get(null);
        if (main == null) return null;
        Field field = main.getClass().getDeclaredField("simulators");
        field.setAccessible(true);
        for (Object simulator : (Iterable<?>)field.get(main))
            if ("projectseele/geofront".equals(simulator.getClass().getField("dimension").get(simulator))) return simulator;
        return null;
    }

    public static JsonObject snapshot() throws ReflectiveOperationException
    {
        Object simulator = simulator();
        if (simulator == null) return null;
        JsonObject report = new JsonObject();
        for (String name : new String[]{"rails","stations","platforms","routes","sidings","depots"})
            report.addProperty(name, ((Collection<?>)simulator.getClass().getField(name).get(simulator)).size());
        JsonArray vehicles = new JsonArray();
        for (Object siding : (Iterable<?>)simulator.getClass().getField("sidings").get(simulator))
        {
            Field field = siding.getClass().getDeclaredField("vehicles");
            field.setAccessible(true);
            for (Object vehicle : (Iterable<?>)field.get(siding))
            {
                Object head = vehicle.getClass().getMethod("getHeadPosition").invoke(vehicle);
                if (head == null) continue;
                JsonObject item = new JsonObject();
                item.addProperty("siding", (String)siding.getClass().getMethod("getName").invoke(siding));
                item.addProperty("moving", (Boolean)vehicle.getClass().getMethod("isMoving").invoke(vehicle));
                for (String axis : new String[]{"x","y","z"}) item.addProperty(axis, head.getClass().getField(axis).getDouble(head));
                vehicles.add(item);
            }
        }
        report.add("vehicles",vehicles);
        return report;
    }
}
