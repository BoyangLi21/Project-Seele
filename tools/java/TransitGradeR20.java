import java.nio.file.*;
import java.util.*;
import org.mtr.core.data.*;
import org.mtr.core.serializer.*;
import org.mtr.core.simulation.Simulator;
import org.mtr.libraries.com.google.gson.*;
import org.mtr.libraries.it.unimi.dsi.fastutil.objects.ObjectArrayList;
public final class TransitGradeR20
{
    static JsonObject json(SerializedDataBase x){var j=new JsonObject();x.serializeFullData(new JsonWriter(j));return j;}
    static JsonArray objects(Collection<? extends SerializedDataBase> x){var a=new JsonArray();for(var v:x)a.add(json(v));return a;}
    public static void main(String[] args)throws Exception
    {
        Path stage=Path.of(args[0]);if(!stage.toString().contains(".Codex"))throw new IllegalArgumentException("stage required");var plan=JsonParser.parseString(Files.readString(Path.of(args[1]))).getAsJsonObject();
        var sim=new Simulator("projectseele/geofront",new String[]{"minecraft/overworld","projectseele/geofront","minecraft/the_nether","minecraft/the_end"},stage,false);
        Map<String,Rail> desired=new HashMap<>();for(var r:plan.getAsJsonArray("rails")){var q=new Rail(new JsonReader(r.getAsJsonObject()));if(!q.isValid())throw new IllegalStateException("Invalid rail");desired.put(q.getHexId(),q);}
        List<String> removed=new ArrayList<>(),added=new ArrayList<>();for(var rail:new ArrayList<>(sim.rails))if(!desired.containsKey(rail.getHexId())){removed.add(rail.getHexId());sim.rails.remove(rail);}
        Set<String> existing=new HashSet<>();sim.rails.forEach(r->existing.add(r.getHexId()));for(var entry:desired.entrySet())if(!existing.contains(entry.getKey())){sim.rails.add(entry.getValue());added.add(entry.getKey());}
        String line=args.length>3?args[3]:"C1";int expected=args.length>4?Integer.parseInt(args[4]):5;
        if(removed.size()!=expected||added.size()!=expected)throw new IllegalStateException("Unexpected geometry scope "+removed.size()+"/"+added.size());sim.sync();
        var route=sim.routes.stream().filter(r->r.getRouteNumber().equals(line)).findFirst().orElseThrow();var depot=sim.depots.stream().filter(d->d.getRouteIds().contains(route.getId())).findFirst().orElseThrow();var siding=sim.sidings.stream().filter(s->s.getName().startsWith(line+"车辆段")).findFirst().orElseThrow();siding.clearVehicles();var deps=new ObjectArrayList<Depot>();deps.add(depot);TransitCadenceR20.generate(sim,deps);
        if(line.equals("F1")){sim.instantDeployDepots(deps);for(int i=0;i<250;i++){sim.tick();Thread.sleep(10);}}
        JsonObject out=new JsonObject();out.addProperty("passed",depot.getLastGeneratedStatus()==Depot.GeneratedStatus.SUCCESSFUL);out.add("stations",objects(sim.stations));out.add("platforms",objects(sim.platforms));out.add("routes",objects(sim.routes));out.add("depots",objects(sim.depots));out.add("removed",new Gson().toJsonTree(removed));out.add("added",new Gson().toJsonTree(added));JsonArray curves=new JsonArray();
        for(var r:sim.rails){var q=new JsonObject();q.addProperty("id",r.getHexId());q.addProperty("mode",r.getTransportMode().name());q.addProperty("kind",r.isPlatform()?"platform":r.isSiding()?"siding":"rail");q.add("geometry",json(r));var pts=new JsonArray();for(double d=0;d<=r.railMath.getLength();d+=.75){var p=r.railMath.getPosition(d,false);var a=new JsonArray();a.add(p.x);a.add(p.y);a.add(p.z);pts.add(a);}q.add("points",pts);curves.add(q);}out.add("curves",curves);
        Files.createDirectories(Path.of(args[2]).getParent());Files.writeString(Path.of(args[2]),new GsonBuilder().setPrettyPrinting().create().toJson(out));sim.save();sim.stop();System.out.println(line+" geometry updated "+removed.size()+" rails");
    }
}
