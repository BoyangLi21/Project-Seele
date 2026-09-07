import java.nio.file.*;
import org.mtr.core.data.*;
import org.mtr.core.serializer.*;
import org.mtr.core.simulation.Simulator;
import org.mtr.libraries.com.google.gson.*;

/** Retains the authored boarding interval even when the one-aircraft shuttle is late. */
public final class RegionalFlightDwellSettings
{
    private static JsonObject json(SerializedDataBase object){JsonObject j=new JsonObject();object.serializeFullData(new JsonWriter(j));return j;}
    public static void main(String[] args) throws Exception
    {
        Path root=Path.of(args[0]).toAbsolutePath().normalize();
        if(java.util.stream.StreamSupport.stream(root.spliterator(),false).noneMatch(p->p.toString().equalsIgnoreCase(".Codex")))throw new IllegalArgumentException("Copied staging only");
        Simulator sim=new Simulator("projectseele/geofront",new String[]{"projectseele/geofront"},root,false);
        Siding siding=sim.sidings.stream().filter(s->s.getName().startsWith("F1 ")&&s.getTransportMode()==TransportMode.AIRPLANE).findFirst().orElseThrow();
        JsonObject before=json(siding);siding.setDelayedVehicleReduceDwellTimePercentage(0);siding.setEarlyVehicleIncreaseDwellTime(false);
        JsonObject after=json(siding),compare=after.deepCopy();
        for(String key:new String[]{"delayedVehicleReduceDwellTimePercentage","earlyVehicleIncreaseDwellTime"})compare.add(key,before.get(key));
        if(!compare.equals(before))throw new IllegalStateException("Unrelated native siding data changed");
        JsonObject proof=new JsonObject();proof.addProperty("passed",true);proof.addProperty("id",siding.getHexId());proof.add("before",before);proof.add("after",after);
        sim.save();sim.stop();Files.writeString(Path.of(args[1]),new GsonBuilder().setPrettyPrinting().create().toJson(proof));
    }
}
