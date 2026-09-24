import com.google.gson.*;
import com.projectseele.physics.ArticulatedBody;
import java.nio.file.*;
import java.util.*;
import org.joml.*;

/** Fast knockdowns onto a one-block slab, using only the shipped runtime. */
public final class PackagedPhysicsR36Smoke
{
    static Matrix4f matrix(JsonArray values)
    {float[] f=new float[16];for(int i=0;i<16;i++)f[i]=values.get(i).getAsFloat();return new Matrix4f().set(f).transpose();}
    public static void main(String[] args)throws Exception
    {
        var models=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject().getAsJsonObject("models");var rows=new JsonArray();
        for(String key:new String[]{"1","4","sachiel"})
        {
            var definition=models.getAsJsonObject(key);Map<String,Matrix4f> pose=new HashMap<>();
            for(var entry:definition.getAsJsonArray("bodies"))
            {var b=entry.getAsJsonObject();var m=matrix(b.getAsJsonArray("initial")).mul(matrix(b.getAsJsonArray("bind")).invert());m.m31(m.m31()+.45F);pose.put(b.get("name").getAsString(),m);}
            try(var body=new ArticulatedBody(definition,pose))
            {
                body.addStaticBox(new Vector3f(0,-.02F,0),new Vector3f(50,.02F,50),new Quaternionf());
                body.velocity(new Vector3f(.5F,-2.8F,.7F));body.impulse("torso_upper",new Vector3f(0,2.15F,0),new Vector3f(0,-40,65));
                float minimum=Float.POSITIVE_INFINITY;
                for(int i=0;i<160;i++){body.step(.05F);minimum=java.lang.Math.min(minimum,body.frame().min().y);}
                var frame=body.frame();boolean pass=Float.isFinite(minimum)&&minimum>-.04F&&frame.supportContacts()>0;
                var row=new JsonObject();row.addProperty("rig",key);row.addProperty("passed",pass);row.addProperty("minimum_y_blocks",minimum/.04F);row.addProperty("floor_thickness_blocks",1);row.addProperty("contacts",frame.supportContacts());rows.add(row);
            }
        }
        Path fixturePath=Path.of("artifacts/combat_direction_r36/rotational_floor_fixture.json");
        if(!Files.isRegularFile(fixturePath))throw new IllegalStateException("Missing captured R36 crouched contact fixture: "+fixturePath);
        {
            var fixture=JsonParser.parseString(Files.readString(fixturePath)).getAsJsonObject();var definition=models.getAsJsonObject("1");
            for(boolean inherited:new boolean[]{false,true})for(boolean neighbor:new boolean[]{false,true})
            {
                Map<String,Matrix4f> pose=new HashMap<>(),previous=new HashMap<>();
                for(var e:fixture.getAsJsonObject("pose").entrySet())pose.put(e.getKey(),matrix(e.getValue().getAsJsonArray()));
                for(var e:fixture.getAsJsonObject("previous").entrySet())previous.put(e.getKey(),matrix(e.getValue().getAsJsonArray()));
                try(var body=new ArticulatedBody(definition,pose))
                {
                    float initial=body.frame().min().y;body.addStaticBox(new Vector3f(0,-.02F,0),new Vector3f(50,.02F,50),new Quaternionf());
                    if(neighbor)
                    {
                        Map<String,Matrix4f> other=new HashMap<>();for(var e:fixture.getAsJsonObject("actor_pose").entrySet())other.put(e.getKey(),matrix(e.getValue().getAsJsonArray()));
                        body.beginActorFrame();body.actor("other",models.getAsJsonObject("sachiel"),other,matrix(fixture.getAsJsonArray("actor_frame")));body.endActorFrame();
                    }
                    if(inherited)body.motionFromPose(previous,.1F);
                    body.impulse("torso_upper",new Vector3f(-.12F,1.24F,-.19F),new Vector3f(0,-40,65));float minimum=initial;
                    for(int i=0;i<160;i++){body.step(.05F);minimum=java.lang.Math.min(minimum,body.frame().min().y);}
                    var row=new JsonObject();row.addProperty("rig","native_crouch_"+inherited+"_neighbor_"+neighbor);row.addProperty("passed",Float.isFinite(minimum)&&minimum>-.04F);row.addProperty("initial_y_blocks",initial/.04F);row.addProperty("minimum_y_blocks",minimum/.04F);rows.add(row);
                }
            }
        }
        var report=new JsonObject();report.add("cases",rows);boolean pass=true;for(var row:rows)pass&=row.getAsJsonObject().get("passed").getAsBoolean();report.addProperty("passed",pass);
        report.addProperty("loaded_from",String.valueOf(ArticulatedBody.class.getProtectionDomain().getCodeSource().getLocation()));
        Files.writeString(Path.of(args[1]),new GsonBuilder().setPrettyPrinting().create().toJson(report));System.out.println(report);
        if(!pass)throw new IllegalStateException("Thin-floor CCD regression");
    }
}
