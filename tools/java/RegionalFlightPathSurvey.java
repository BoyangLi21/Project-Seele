import java.nio.file.*;
import org.mtr.core.data.*;
import org.mtr.core.serializer.*;
import org.mtr.core.simulation.Simulator;
import org.mtr.libraries.com.google.gson.*;

/** Samples the installed native flight curves, including generated airborne legs. */
public final class RegionalFlightPathSurvey
{
    public static void main(String[] args) throws Exception
    {
        Path root=Path.of(args[0]).toAbsolutePath().normalize();
        if(java.util.stream.StreamSupport.stream(root.spliterator(),false).noneMatch(p->p.toString().equalsIgnoreCase(".Codex")))
            throw new IllegalArgumentException("Read a copied native database");
        Simulator sim=new Simulator("projectseele/geofront",new String[]{"projectseele/geofront"},root,false);
        JsonArray segments=new JsonArray();int index=0;
        String requested=args.length>2?args[2]:"";
        for(Depot depot:sim.depots)if(depot.getTransportMode()==TransportMode.AIRPLANE&&(requested.isEmpty()||sim.routes.stream().anyMatch(r->depot.getRouteIds().contains(r.getId())&&r.getRouteNumber().equals(requested))))
            for(PathData path:depot.getPath())
            {
                JsonObject segment=new JsonObject();segment.addProperty("id",(requested.isEmpty()?"air":requested)+"_native_"+index++);
                segment.addProperty("kind","flight");segment.addProperty("mode","AIRPLANE");
                double length=path.getRailLength();segment.addProperty("length",length);JsonArray points=new JsonArray();
                for(double distance=0;distance<length+4;distance+=4)
                {
                    var v=path.getPosition(path.getStartDistance()+Math.min(distance,length));
                    JsonArray point=new JsonArray();point.add(v.x);point.add(v.y);point.add(v.z);points.add(point);
                    if(distance>=length)break;
                }
                segment.add("points",points);segments.add(segment);
            }
        Files.writeString(Path.of(args[1]),new GsonBuilder().setPrettyPrinting().create().toJson(segments));
        sim.stop();System.out.println("Native flight path segments="+segments.size());
    }
}
