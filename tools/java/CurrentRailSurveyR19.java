import java.nio.file.*;
import java.util.*;
import org.mtr.core.data.*;
import org.mtr.core.simulation.Simulator;
import org.mtr.libraries.com.google.gson.*;

/** Sample the currently installed rail geometry using MTR's own curve evaluator. */
public final class CurrentRailSurveyR19
{
    public static void main(String[] args) throws Exception
    {
        Path source=Path.of(args[0]).toAbsolutePath().normalize();
        if (!source.toString().contains(".Codex")) throw new IllegalArgumentException("A copied transit database is required");
        String dimension="projectseele/geofront";
        Simulator simulator=new Simulator(dimension,new String[]{"minecraft/overworld",dimension,"minecraft/the_nether","minecraft/the_end"},source,false);
        JsonArray result=new JsonArray();
        for (Rail rail:simulator.rails)
        {
            if (rail.getTransportMode()!=TransportMode.TRAIN) continue;
            JsonObject row=new JsonObject();row.addProperty("id",rail.getHexId());row.addProperty("mode","TRAIN");
            row.addProperty("kind",rail.isPlatform()?"platform":rail.isSiding()?"siding":"rail");
            double length=rail.railMath.getLength();row.addProperty("length",length);JsonArray points=new JsonArray();
            for(double distance=0;distance<=length;distance+=.5)
            {
                var p=rail.railMath.getPosition(distance,false);JsonArray point=new JsonArray();point.add(p.x);point.add(p.y);point.add(p.z);points.add(point);
            }
            row.add("points",points);result.add(row);
        }
        Files.writeString(Path.of(args[1]),new GsonBuilder().create().toJson(result));
        simulator.stop();System.out.println("Current native TRAIN rails sampled: "+result.size());
    }
}
