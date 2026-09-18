import java.nio.file.*;
import java.util.*;
import java.lang.reflect.*;
import org.mtr.core.data.*;
import org.mtr.core.operation.ArrivalsRequest;
import org.mtr.core.serializer.*;
import org.mtr.core.simulation.Simulator;
import org.mtr.libraries.com.google.gson.*;
import org.mtr.libraries.it.unimi.dsi.fastutil.objects.ObjectArrayList;
import org.mtr.libraries.it.unimi.dsi.fastutil.longs.LongImmutableList;

/** Tune repeating trips, without modulo-aliasing a full day's departures. */
public final class TransitCadenceR20
{
    static final Gson GSON=new GsonBuilder().setPrettyPrinting().create();
    static JsonObject json(SerializedDataBase x){var j=new JsonObject();x.serializeFullData(new JsonWriter(j));return j;}
    static void generate(Simulator sim,ObjectArrayList<Depot> deps)throws Exception
    {
        Depot.generateDepots(sim,deps);
        for(int i=0;i<1000;i++){sim.tick();Thread.sleep(5);if(i>30&&deps.stream().allMatch(d->d.getLastGeneratedStatus()==Depot.GeneratedStatus.SUCCESSFUL))return;}
        throw new IllegalStateException("Cadence path regeneration failed");
    }
    public static void main(String[] args)throws Exception
    {
        if(!args[0].contains(".Codex"))throw new IllegalArgumentException("staging only");
        var sim=new Simulator("projectseele/geofront",new String[]{"minecraft/overworld","projectseele/geofront","minecraft/the_nether","minecraft/the_end"},Path.of(args[0]),false);
        var deps=new ObjectArrayList<Depot>();Map<Depot,Siding> sidings=new HashMap<>();Field period=Siding.class.getDeclaredField("timeOffsetForRepeating");period.setAccessible(true);
        TransportMode mode=args.length>3?TransportMode.valueOf(args[3]):TransportMode.TRAIN;
        for(var d:sim.depots)if(d.getTransportMode()==mode&&(args.length<3||sim.routes.stream().anyMatch(r->d.getRouteIds().contains(r.getId())&&r.getRouteNumber().equals(args[2]))))
        {
            deps.add(d);var route=sim.routes.stream().filter(r->d.getRouteIds().contains(r.getId())).findFirst().orElseThrow();
            var siding=sim.sidings.stream().filter(s->s.getName().startsWith(route.getRouteNumber()+"车辆段")||s.getName().startsWith(route.getRouteNumber()+" ")).findFirst().orElseThrow();sidings.put(d,siding);siding.clearVehicles();d.setUseRealTime(true);d.setRepeatInfinitely(true);d.getRealTimeDepartures().clear();d.getRealTimeDepartures().add(0);
            siding.setName(route.getRouteNumber()+"车辆段");d.setName(route.getName()+"运行基地");
        }
        if(deps.isEmpty())throw new IllegalStateException("No selected depots; an empty check is not a cadence pass");
        generate(sim,deps);JsonArray tune=new JsonArray();Map<Depot,Long> target=new HashMap<>();
        for(var d:deps){long before=Math.round(period.getDouble(sidings.get(d)));if(before<=0)throw new IllegalStateException("Missing repeat period");target.put(d,Math.max(120000L,((before+59999)/60000)*60000));System.out.println("Cadence "+d.getId()+" "+before+" -> "+target.get(d));}
        for(int iteration=0;iteration<5;iteration++)
        {
            boolean changed=false;
            for(var d:deps)
            {
                long delta=target.get(d)-Math.round(period.getDouble(sidings.get(d)));if(Math.abs(delta)<=1)continue;
                var route=sim.routes.stream().filter(r->d.getRouteIds().contains(r.getId())).findFirst().orElseThrow();Set<Long> ids=new LinkedHashSet<>();for(var rp:route.getRoutePlatforms())ids.add(rp.getPlatform().getId());
                long each=Math.floorDiv(delta,ids.size()),remaining=Math.floorMod(delta,ids.size());
                for(long id:ids){var p=sim.platforms.stream().filter(q->q.getId()==id).findFirst().orElseThrow();p.setDwellTime(p.getDwellTime()+each+(remaining-->0?1:0));}
                changed=true;
            }
            if(!changed)break;generate(sim,deps);
        }
        for(var d:deps)
        {
            long duration=Math.round(period.getDouble(sidings.get(d)));if(Math.abs(duration-target.get(d))>2)throw new IllegalStateException("Not a whole-minute cycle: "+duration);
            int fleet=(int)(target.get(d)/60000);d.getRealTimeDepartures().clear();for(int i=0;i<fleet;i++)d.getRealTimeDepartures().add(i*60000L);
            sidings.get(d).setMaxVehicles(fleet);sidings.get(d).clearVehicles();
            JsonObject row=new JsonObject();row.addProperty("depot",d.getId());row.addProperty("period_ms",duration);row.addProperty("fleet",fleet);row.addProperty("headway_ms",60000);tune.add(row);
        }
        generate(sim,deps);sim.instantDeployDepots(deps);
        for(int i=0;i<1500;i++){sim.tick();Thread.sleep(10);}
        JsonArray all=new JsonArray();boolean pass=true;
        Set<Long> selectedPlatforms=new HashSet<>();
        for(var d:deps)for(var r:sim.routes)if(d.getRouteIds().contains(r.getId()))for(var rp:r.getRoutePlatforms())selectedPlatforms.add(rp.getPlatform().getId());
        for(var p:sim.platforms)if(p.getTransportMode()==mode&&(args.length<3||selectedPlatforms.contains(p.getId())))
        {
            var response=new ArrivalsRequest(new LongImmutableList(new long[]{p.getId()}),8,8).getArrivals(sim);var j=json(response);JsonObject row=new JsonObject();row.addProperty("id",p.getId());row.addProperty("station",p.getStationName());row.add("native",j);
            var values=j.getAsJsonArray("arrivals");JsonArray intervals=new JsonArray(),scheduled=new JsonArray();boolean ok=values.size()>=3;
            for(int i=1;i<values.size();i++)
            {
                var a=values.get(i-1).getAsJsonObject();var b=values.get(i).getAsJsonObject();long diff=b.get("departure").getAsLong()-a.get("departure").getAsLong();intervals.add(diff);
                long planned=diff-b.get("deviation").getAsLong()+a.get("deviation").getAsLong();scheduled.add(planned);ok&=Math.abs(planned-60000)<=2;
            }
            row.add("actual_prediction_intervals_ms",intervals);row.add("scheduled_intervals_ms",scheduled);row.addProperty("scheduled_passed",ok);all.add(row);pass&=ok;
        }
        JsonObject receipt=new JsonObject();receipt.add("cycles",tune);receipt.add("platforms",all);receipt.addProperty("passed",pass);receipt.addProperty("meaning","Native scheduled departures are exactly 60000 ms apart; live predictions retain the engine's actual deviation.");Files.writeString(Path.of(args[1]),GSON.toJson(receipt));sim.save();sim.stop();System.out.println("Minute headway native schedule "+pass);
    }
}
