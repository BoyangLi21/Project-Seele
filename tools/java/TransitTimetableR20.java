import java.nio.file.*;
import org.mtr.core.data.*;
import org.mtr.core.operation.ArrivalsRequest;
import org.mtr.core.serializer.*;
import org.mtr.core.simulation.Simulator;
import org.mtr.libraries.com.google.gson.*;
import org.mtr.libraries.it.unimi.dsi.fastutil.longs.LongImmutableList;
public final class TransitTimetableR20
{
    public static void main(String[] args)throws Exception
    {
        if(!args[0].contains(".Codex"))throw new IllegalArgumentException("staging only");
        var sim=new Simulator("projectseele/geofront",new String[]{"projectseele/geofront"},Path.of(args[0]),false);
        for(int i=0;i<100;i++){sim.tick();Thread.sleep(10);}
        JsonArray out=new JsonArray();
        for(var p:sim.platforms)
        {
            JsonObject row=new JsonObject();row.addProperty("id",p.getId());row.addProperty("station",p.getStationName());
            var arrival=new ArrivalsRequest(new LongImmutableList(new long[]{p.getId()}),8,8).getArrivals(sim);JsonObject details=new JsonObject();arrival.serializeFullData(new JsonWriter(details));row.add("native",details);out.add(row);
        }
        Files.writeString(Path.of(args[1]),new GsonBuilder().setPrettyPrinting().create().toJson(out));sim.stop();
    }
}
