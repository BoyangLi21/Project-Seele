import java.nio.file.*;
import java.util.*;
import org.mtr.core.data.*;
import org.mtr.core.simulation.Simulator;
import org.mtr.core.operation.ArrivalsRequest;
import org.mtr.core.serializer.*;
import org.mtr.libraries.com.google.gson.*;
import org.mtr.libraries.it.unimi.dsi.fastutil.objects.ObjectArrayList;
import org.mtr.libraries.it.unimi.dsi.fastutil.longs.LongImmutableList;
public final class TransitWarmupR20
{
    static JsonObject json(SerializedDataBase x){var j=new JsonObject();x.serializeFullData(new JsonWriter(j));return j;}
    public static void main(String[] args)throws Exception
    {
        if(!args[0].contains(".Codex"))throw new IllegalArgumentException("staging only");
        var sim=new Simulator("projectseele/geofront",new String[]{"minecraft/overworld","projectseele/geofront","minecraft/the_nether","minecraft/the_end"},Path.of(args[0]),false);
        var deps=new ObjectArrayList<Depot>();for(var d:sim.depots)if(d.getTransportMode()==TransportMode.TRAIN)deps.add(d);
        for(var s:sim.sidings)if(s.getTransportMode()==TransportMode.TRAIN)s.clearVehicles();Depot.generateDepots(sim,deps);
        long end=System.currentTimeMillis()+500000,next=0;
        while(System.currentTimeMillis()<end)
        {
            sim.tick();Thread.sleep(10);
            if(System.currentTimeMillis()>next){next=System.currentTimeMillis()+60000;System.out.println("R20 natural dispatch: remaining="+(end-System.currentTimeMillis())/1000+"s "+sim.sidings.stream().map(s->s.getName()+":"+json(s).getAsJsonArray("vehicles").size()).toList());}
        }
        var result=new JsonObject();var stations=new JsonArray();boolean schedule=true;
        for(var p:sim.platforms)if(p.getTransportMode()==TransportMode.TRAIN)
        {
            var j=json(new ArrivalsRequest(new LongImmutableList(new long[]{p.getId()}),12,12).getArrivals(sim));var arrivals=j.getAsJsonArray("arrivals");var row=new JsonObject();row.addProperty("platform",p.getId());row.addProperty("station",p.getStationName());row.add("native",j);
            var planned=new TreeSet<Long>();long maxDelay=0;for(var x:arrivals){var a=x.getAsJsonObject();planned.add(a.get("departure").getAsLong()-a.get("deviation").getAsLong());maxDelay=Math.max(maxDelay,Math.abs(a.get("deviation").getAsLong()));}
            Long previous=null;var intervals=new JsonArray();boolean ok=planned.size()>=4;
            for(long t:planned){if(previous!=null){long d=t-previous;intervals.add(d);ok&=Math.abs(d-60000)<=2;}previous=t;}
            row.add("scheduled_intervals_ms",intervals);row.addProperty("max_prediction_deviation_ms",maxDelay);row.addProperty("scheduled_passed",ok);stations.add(row);schedule&=ok;
        }
        result.addProperty("scheduled_passed",schedule);result.add("platforms",stations);result.addProperty("dispatch","Real native depot departures; no instant-deploy position sampling");
        Files.writeString(Path.of(args[1]),new GsonBuilder().setPrettyPrinting().create().toJson(result));sim.save();sim.stop();System.out.println("R20 natural dispatch schedule "+schedule);
    }
}
