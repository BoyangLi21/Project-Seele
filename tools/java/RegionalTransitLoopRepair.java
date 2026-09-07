import java.nio.file.*;
import java.util.*;
import org.mtr.core.data.*;
import org.mtr.core.operation.UpdateDataRequest;
import org.mtr.core.serializer.*;
import org.mtr.core.simulation.Simulator;
import org.mtr.libraries.com.google.gson.*;
import org.mtr.libraries.it.unimi.dsi.fastutil.objects.ObjectArrayList;

/** Validates and closes the two explicitly circular services in a copied native database. */
public final class RegionalTransitLoopRepair
{
    private static final Gson GSON=new GsonBuilder().setPrettyPrinting().create();
    private static JsonObject json(SerializedDataBase value)
    {
        JsonObject result=new JsonObject();value.serializeFullData(new JsonWriter(result));return result;
    }
    public static void main(String[] args) throws Exception
    {
        Path root=Path.of(args[0]).toAbsolutePath().normalize(),out=Path.of(args[1]);
        if(java.util.stream.StreamSupport.stream(root.spliterator(),false).noneMatch(p->p.toString().equalsIgnoreCase(".Codex")))
            throw new IllegalArgumentException("Only a copied .Codex staging database may be changed");
        Simulator sim=new Simulator("projectseele/geofront",new String[]{"projectseele/geofront"},root,false);
        JsonObject proof=new JsonObject();JsonArray results=new JsonArray();
        Map<String,JsonObject> rails=new HashMap<>(),untouchedRoutes=new HashMap<>();
        sim.rails.forEach(r->rails.put(r.getHexId(),json(r)));
        sim.routes.forEach(r->{if(!Set.of("C1","F1").contains(r.getRouteNumber()))untouchedRoutes.put(r.getHexId(),json(r));});
        ObjectArrayList<Depot> depots=new ObjectArrayList<>();
        UpdateDataRequest update=new UpdateDataRequest(sim);
        for(String code:List.of("C1","F1"))
        {
            Route route=sim.routes.stream().filter(r->r.getRouteNumber().equals(code)).findFirst().orElseThrow();
            Depot depot=sim.depots.stream().filter(d->d.getRouteIds().contains(route.getId())).findFirst().orElseThrow();
            if(!depot.getRepeatInfinitely())throw new IllegalStateException("Expected the authored repeating service "+code);
            JsonObject record=new JsonObject();record.addProperty("line",code);record.add("routeBefore",json(route));record.add("depotBefore",json(depot));
            var stops=route.getRoutePlatforms();
            // Infinite repetition wraps the stored path; it does not generate the missing return leg.
            long first=stops.get(0).getPlatform().getId();
            int originalCount=code.equals("C1")?4:2;
            if(stops.size()==originalCount)stops.add(new RoutePlatformData(first));
            else if(stops.size()!=originalCount+1||stops.get(stops.size()-1).getPlatform().getId()!=first)
                throw new IllegalStateException("Unexpected stop sequence "+code);
            update.addRoute(route);update.addDepot(depot);depots.add(depot);
            record.add("routeAfter",json(route));results.add(record);
        }
        update.update();sim.sync();Depot.generateDepots(sim,depots);
        boolean passed=false;
        for(int i=0;i<10000;i++)
        {
            sim.tick();Thread.sleep(5);
            if(i>20&&depots.stream().allMatch(d->d.getLastGeneratedStatus()==Depot.GeneratedStatus.SUCCESSFUL)){passed=true;break;}
        }
        for(int i=0;i<depots.size();i++)
        {
            Depot d=depots.get(i);JsonObject r=results.get(i).getAsJsonObject();r.add("depotAfter",json(d));
            r.addProperty("status",d.getLastGeneratedStatus().name());r.addProperty("pathSegments",d.getPath().size());
            JsonArray gaps=new JsonArray();
            for(int j=1;j<d.getPath().size();j++)
            {
                var a=json(d.getPath().get(j-1)).getAsJsonObject("endPosition");
                var b=json(d.getPath().get(j)).getAsJsonObject("startPosition");
                if(!a.equals(b)){JsonObject gap=new JsonObject();gap.addProperty("index",j);gap.add("previousEnd",a);gap.add("nextStart",b);gaps.add(gap);}
            }
            r.add("internalPathGaps",gaps);passed &= gaps.isEmpty();
        }
        for(Rail r:sim.rails)if(!json(r).equals(rails.get(r.getHexId())))throw new IllegalStateException("Rail geometry changed");
        for(Route r:sim.routes)if(untouchedRoutes.containsKey(r.getHexId())&&!json(r).equals(untouchedRoutes.get(r.getHexId())))throw new IllegalStateException("Unrelated route changed");
        proof.add("services",results);proof.addProperty("passed",passed);proof.addProperty("railsUnchanged",rails.size());
        Files.writeString(out,GSON.toJson(proof));
        if(!passed){sim.stop();throw new IllegalStateException("Closed route validation failed; inspect "+out);}
        sim.save();sim.stop();System.out.println("Closed native routes validated: "+out);
    }
}
