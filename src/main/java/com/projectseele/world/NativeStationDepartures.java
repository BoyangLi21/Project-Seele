package com.projectseele.world;

import com.projectseele.visual.RegionalNativeTransitInspection;
import net.minecraft.core.BlockPos;
import java.lang.reflect.Constructor;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;
import java.util.HashMap;

/** Reads the running MTR simulator's own arrival/departure predictions. */
public final class NativeStationDepartures
{
    public record Snapshot(long platformId, long clock, List<Long> departures, List<String> rows) {}
    private static final DateTimeFormatter CLOCK = DateTimeFormatter.ofPattern("HH:mm").withZone(ZoneId.of("Asia/Shanghai"));
    private record Cached(long until, Snapshot snapshot) {}
    private static final Map<Object,Map<BlockPos,Cached>> CACHE = new WeakHashMap<>();
    private static Object call(Object object, String method) throws ReflectiveOperationException
    {
        return object.getClass().getMethod(method).invoke(object);
    }
    private static String shortName(Object object, String method, int limit) throws ReflectiveOperationException
    {
        String text = String.valueOf(call(object, method)).split("\\|", 2)[0].trim();
        return text.length() > limit ? text.substring(0, limit) : text;
    }
    public static Snapshot read(BlockPos centre) throws ReflectiveOperationException
    {
        Object simulator = RegionalNativeTransitInspection.simulator();
        if (simulator == null) return new Snapshot(-1, 0, List.of(), List.of("正在读取运行信息"));
        var cache = CACHE.computeIfAbsent(simulator, ignored -> new HashMap<>());
        long moment = System.nanoTime();Cached cached = cache.get(centre);
        if (cached != null && cached.until() > moment) return cached.snapshot();
        Object nearest = null;double distance = 16;
        for (Object platform : (Iterable<?>) simulator.getClass().getField("platforms").get(simulator))
        {
            Object pos = call(platform, "getMidPosition");
            double dx = ((Number)call(pos,"getX")).doubleValue() - centre.getX();
            double dy = ((Number)call(pos,"getY")).doubleValue() - centre.getY();
            double dz = ((Number)call(pos,"getZ")).doubleValue() - centre.getZ();
            double next = dx*dx + dy*dy*4 + dz*dz;
            if (next < distance) { nearest = platform;distance = next; }
        }
        if (nearest == null) return new Snapshot(-1, 0, List.of(), List.of("本站台暂无运行信息"));
        long id = ((Number)call(nearest, "getId")).longValue();
        Class<?> longs = Class.forName("org.mtr.libraries.it.unimi.dsi.fastutil.longs.LongImmutableList");
        Object ids = longs.getConstructor(long[].class).newInstance((Object)new long[]{id});
        Class<?> requestClass = Class.forName("org.mtr.core.operation.ArrivalsRequest");
        Constructor<?> constructor = requestClass.getConstructor(longs, int.class, int.class);
        Object request = constructor.newInstance(ids, 2, 2);
        Object response = requestClass.getMethod("getArrivals", simulator.getClass()).invoke(request, simulator);
        long now = ((Number)call(response, "getCurrentTime")).longValue();
        List<String> rows = new ArrayList<>();List<Long> times = new ArrayList<>();
        for (Object arrival : (Iterable<?>)call(response, "getArrivals"))
        {
            long departure = ((Number)call(arrival, "getDeparture")).longValue();
            String route = shortName(arrival, "getRouteNumber", 7);
            if (route.isBlank()) route = shortName(arrival, "getRouteName", 10);
            String destination = shortName(arrival, "getDestination", 15);
            long seconds = Math.max(0, (departure - now) / 1000);
            String eta = seconds <= 30 ? "即将进站" : "约" + ((seconds + 59) / 60) + "分钟";
            rows.add(CLOCK.format(Instant.ofEpochMilli(departure)) + "  " + route + "  " + destination + "  " + eta);
            times.add(departure);
        }
        if (rows.isEmpty()) rows.add("当前暂无待发班次");
        Snapshot snapshot = new Snapshot(id, now, List.copyOf(times), List.copyOf(rows));
        cache.put(centre.immutable(), new Cached(moment + 1_000_000_000L, snapshot));
        return snapshot;
    }
    private NativeStationDepartures() {}
}
