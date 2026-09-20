import java.nio.file.*;
import java.util.*;
import org.mtr.core.data.*;
import org.mtr.core.operation.*;
import org.mtr.core.serializer.*;
import org.mtr.core.simulation.Simulator;
import org.mtr.core.tool.Angle;
import org.mtr.libraries.com.google.gson.*;
import org.mtr.libraries.it.unimi.dsi.fastutil.objects.ObjectArrayList;

/** Insert a stop into the existing S1 alignment and retain all service identities. */
public final class AirportStopR28
{
    static JsonObject json(SerializedDataBase v){JsonObject o=new JsonObject();v.serializeFullData(new JsonWriter(o));return o;}
    static Position pos(int x,int y,int z){return new Position(x,y,z);}
    static boolean same(JsonObject p,Position q){return p.get("x").getAsLong()==q.getX()&&p.get("y").getAsLong()==q.getY()&&p.get("z").getAsLong()==q.getZ();}
    public static void main(String[] args)throws Exception
    {
        Path root=Path.of(args[0]).toAbsolutePath(),out=Path.of(args[1]);
        if(!root.toString().contains(".Codex"))throw new IllegalArgumentException("Copied staging store required");Files.createDirectories(out);
        Simulator sim=new Simulator("projectseele/geofront",new String[]{"minecraft/overworld","projectseele/geofront","minecraft/the_nether","minecraft/the_end"},root,false);
        Route route=sim.routes.stream().filter(r->r.getRouteNumber().equals("S1")).findFirst().orElseThrow();
        Depot depot=sim.depots.stream().filter(d->d.getRouteIds().contains(route.getId())).findFirst().orElseThrow();
        Siding siding=sim.sidings.stream().filter(s->s.getName().equals(route.getRouteNumber()+"车辆段")).findFirst().orElseThrow();
        JsonObject receipt=new JsonObject();JsonArray removed=new JsonArray(),added=new JsonArray(),platforms=new JsonArray();
        Map<Integer,Platform> stops=new HashMap<>();DeleteDataRequest deletion=new DeleteDataRequest();
        for(int z:new int[]{124,132})
        {
            Position a=pos(440,106,z),b=pos(1030,98,z);
            Rail old=sim.rails.stream().filter(r->{var j=json(r);return same(j.getAsJsonObject("position1"),a)&&same(j.getAsJsonObject("position2"),b)||same(j.getAsJsonObject("position2"),a)&&same(j.getAsJsonObject("position1"),b);}).findFirst().orElseThrow();
            if(old.isPlatform()||old.isSiding())throw new IllegalStateException("Cannot retire a platform");
            removed.add(old.getHexId());deletion.addRailId(old.getHexId());
        }
        deletion.delete(sim);sim.sync();UpdateDataRequest rails=new UpdateDataRequest(sim);
        for(int z:new int[]{124,132})
        {
            Position[] points={pos(440,106,z),pos(520,104,z),pos(650,104,z),pos(1030,98,z)};
            for(int i=0;i<3;i++)
            {
                var styles=new ObjectArrayList<String>();styles.add("default_3d");
                Rail rail=i==1?Rail.newPlatformRail(points[i],Angle.E,points[i+1],Angle.W,Rail.Shape.QUADRATIC,100,styles,TransportMode.TRAIN):
                    Rail.newRail(points[i],Angle.E,points[i+1],Angle.W,Rail.Shape.QUADRATIC,100,styles,z==132?90:0,z==124?90:0,false,false,true,false,true,TransportMode.TRAIN);
                if(!rail.isValid())throw new IllegalStateException("Invalid airport throat");rails.addRail(rail);added.add(rail.getHexId());
            }
        }
        rails.update();sim.sync();UpdateDataRequest changes=new UpdateDataRequest(sim);
        for(int z:new int[]{124,132})
        {
            Platform platform=sim.platforms.stream().filter(p->{var j=json(p);return same(j.getAsJsonObject("position1"),pos(520,104,z))&&same(j.getAsJsonObject("position2"),pos(650,104,z));}).findFirst().orElseThrow();
            platform.setName(z==132?"1":"2");platform.setDwellTime(14000);stops.put(z,platform);changes.addPlatform(platform);platforms.add(platform.getId());
        }
        var sequence=route.getRoutePlatforms();
        for(int i=sequence.size()-1;i>=0;i--)
        {
            long id=json(sequence.get(i)).get("platformId").getAsLong();
            if(id==3154024312482277635L)sequence.add(i+1,new RoutePlatformData(stops.get(132).getId()));
            if(id==1513300505441324941L)sequence.add(i+1,new RoutePlatformData(stops.get(124).getId()));
        }
        changes.addRoute(route);
        Station station=sim.stations.stream().filter(s->s.getName().equals("NERV 航空基地")).findFirst().orElseThrow();
        station.setCorners(pos(364,64,-40),pos(710,116,158));changes.addStation(station);
        siding.clearVehicles();changes.addSiding(siding);changes.update();sim.sync();
        var depots=new ObjectArrayList<Depot>();depots.add(depot);Depot.generateDepots(sim,depots);boolean dispatched=false;
        for(int tick=0;tick<1800;tick++)
        {
            sim.tick();Thread.sleep(10);
            if(tick%200==0)System.out.println("Airport regeneration "+tick+" "+depot.getLastGeneratedStatus());
            if(!dispatched&&tick>30&&depot.getLastGeneratedStatus()==Depot.GeneratedStatus.SUCCESSFUL){sim.instantDeployDepots(depots);dispatched=true;}
            if(dispatched&&tick>300)break;
        }
        if(!dispatched)throw new IllegalStateException("S1 path regeneration failed");
        receipt.addProperty("passed",true);receipt.add("retired_rails",removed);receipt.add("new_rails",added);receipt.add("new_platforms",platforms);
        receipt.addProperty("route",route.getId());receipt.addProperty("station",station.getId());receipt.addProperty("depot",depot.getId());receipt.addProperty("siding",siding.getId());
        Files.writeString(out.resolve("airport_native_receipt.json"),new GsonBuilder().setPrettyPrinting().create().toJson(receipt));sim.save();sim.stop();
    }
}
