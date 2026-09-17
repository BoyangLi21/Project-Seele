import java.nio.file.*;
import java.util.*;
import org.mtr.core.data.*;
import org.mtr.core.operation.UpdateDataRequest;
import org.mtr.core.serializer.*;
import org.mtr.core.simulation.Simulator;
import org.mtr.libraries.com.google.gson.*;
import org.mtr.libraries.it.unimi.dsi.fastutil.objects.ObjectArrayList;

/** Rebuild an explicitly approved alignment in a new isolated native store. */
public final class TransitRebuildR20
{
    static final Gson GSON=new GsonBuilder().setPrettyPrinting().create();
    static JsonObject json(SerializedDataBase v){JsonObject o=new JsonObject();v.serializeFullData(new JsonWriter(o));return o;}
    static JsonArray objects(Collection<? extends SerializedDataBase> values){JsonArray a=new JsonArray();for(var v:values)a.add(json(v));return a;}
    public static void main(String[] args)throws Exception
    {
        Path root=Path.of(args[1]).toAbsolutePath().normalize(),out=Path.of(args[2]);
        if(!root.toString().contains(".Codex")||Files.exists(root))throw new IllegalArgumentException("A NEW .Codex native staging directory is required");
        JsonObject plan=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();Files.createDirectories(root);Files.createDirectories(out);
        Simulator sim=new Simulator("projectseele/geofront",new String[]{"minecraft/overworld","projectseele/geofront","minecraft/the_nether","minecraft/the_end"},root,false);
        for(var x:plan.getAsJsonArray("rails"))
        {
            Rail rail=new Rail(new JsonReader(x.getAsJsonObject()));
            if(!rail.isValid())throw new IllegalStateException("Invalid native rail: "+x);
            sim.rails.add(rail);
        }
        for(var x:plan.getAsJsonArray("stations"))sim.stations.add(new Station(new JsonReader(x.getAsJsonObject()),sim));
        for(var x:plan.getAsJsonArray("platforms"))sim.platforms.add(new Platform(new JsonReader(x.getAsJsonObject()),sim));
        for(var x:plan.getAsJsonArray("routes"))sim.routes.add(new Route(new JsonReader(x.getAsJsonObject()),sim));
        for(var x:plan.getAsJsonArray("depots"))
        {
            JsonObject j=x.getAsJsonObject().deepCopy();j.remove("path");sim.depots.add(new Depot(new JsonReader(j),sim));
        }
        for(var x:plan.getAsJsonArray("sidings"))sim.sidings.add(new Siding(new JsonReader(x.getAsJsonObject()),sim));
        for(var x:plan.getAsJsonArray("lifts"))sim.lifts.add(new Lift(new JsonReader(x.getAsJsonObject()),sim));
        sim.sync();sim.setGameTime(0,1200000,true);
        for(var d:sim.depots)d.init();for(var s:sim.sidings)s.init();
        var depots=new ObjectArrayList<Depot>(sim.depots);Depot.generateDepots(sim,depots);
        boolean deployed=false;Map<Long,Set<Long>> positions=new HashMap<>();sim.sidings.forEach(s->positions.put(s.getId(),new HashSet<>()));
        for(int t=0;t<12000;t++)
        {
            sim.tick();Thread.sleep(10);
            if(t%500==0)System.out.println("R20 native "+t+" "+depots.stream().map(d->d.getName()+":"+d.getLastGeneratedStatus()).toList());
            if(!deployed&&t>50&&depots.stream().allMatch(d->d.getLastGeneratedStatus()==Depot.GeneratedStatus.SUCCESSFUL))
            {sim.instantDeployDepots(depots);deployed=true;}
            if(deployed&&t%100==0)
            {
                for(var s:sim.sidings)for(var v:json(s).getAsJsonArray("vehicles"))positions.get(s.getId()).add(Math.round(v.getAsJsonObject().get("railProgress").getAsDouble()));
                if(t>1500&&positions.values().stream().allMatch(v->v.size()>8))break;
            }
        }
        JsonObject result=new JsonObject();JsonArray status=new JsonArray();boolean passed=deployed;
        for(var d:depots)
        {
            JsonObject row=new JsonObject();row.addProperty("depot",d.getId());row.addProperty("name",d.getName());row.addProperty("status",d.getLastGeneratedStatus().name());row.addProperty("path_segments",d.getPath().size());row.addProperty("repeat",d.getRepeatInfinitely());row.addProperty("real_time",d.getUseRealTime());row.addProperty("scheduled_departures",d.getRealTimeDepartures().size());status.add(row);
            passed&=d.getLastGeneratedStatus()==Depot.GeneratedStatus.SUCCESSFUL;
        }
        result.add("depots",status);JsonArray ps=new JsonArray();
        for(var s:sim.sidings){JsonObject row=new JsonObject();row.addProperty("id",s.getId());row.addProperty("positions",positions.get(s.getId()).size());row.addProperty("fleet_limit",s.getMaxVehicles());row.addProperty("vehicles",json(s).getAsJsonArray("vehicles").size());ps.add(row);passed&=positions.get(s.getId()).size()>8;}
        result.add("progress",ps);result.addProperty("passed",passed);
        JsonArray curves=new JsonArray();
        for(var r:sim.rails)
        {
            JsonObject c=new JsonObject();c.addProperty("id",r.getHexId());c.addProperty("mode",r.getTransportMode().name());c.addProperty("kind",r.isPlatform()?"platform":r.isSiding()?"siding":"rail");c.add("geometry",json(r));JsonArray points=new JsonArray();
            for(double d=0;d<=r.railMath.getLength();d+=.75){var p=r.railMath.getPosition(d,false);JsonArray a=new JsonArray();a.add(p.x);a.add(p.y);a.add(p.z);points.add(a);}c.add("points",points);curves.add(c);
        }
        result.add("curves",curves);result.add("platforms",objects(sim.platforms));result.add("stations",objects(sim.stations));result.add("routes",objects(sim.routes));
        Files.writeString(out.resolve("native_commission.json"),GSON.toJson(result));sim.save();sim.stop();
        System.out.println("R20 commissioning "+passed);if(!passed)throw new IllegalStateException("Native commissioning failed; staged data must not be installed");
    }
}
