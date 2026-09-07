package com.projectseele.visual;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.lang.reflect.Field;
import java.util.Collection;

/** Read-only inspection of the installed MTR version without a compile-time dependency. */
public final class RegionalNativeTransitInspection
{
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
