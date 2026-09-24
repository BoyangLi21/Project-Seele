import com.google.gson.*;
import com.projectseele.physics.ArticulatedBody;
import java.nio.file.*;
import java.util.*;
import org.joml.*;

/** Loads the shipped classes and nested libraries, never the development class directory. */
public final class PackagedPhysicsR35Smoke
{
    static Matrix4f matrix(JsonArray values)
    {float[] f=new float[16];for(int i=0;i<16;i++)f[i]=values.get(i).getAsFloat();return new Matrix4f().set(f).transpose();}
    public static void main(String[] args)throws Exception
    {
        var definition=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject().getAsJsonObject("models").getAsJsonObject("1");
        Map<String,Matrix4f> pose=new HashMap<>();
        for(var entry:definition.getAsJsonArray("bodies"))
        {var b=entry.getAsJsonObject();pose.put(b.get("name").getAsString(),matrix(b.getAsJsonArray("initial")).mul(matrix(b.getAsJsonArray("bind")).invert()));}
        try(var body=new ArticulatedBody(definition,pose))
        {
            body.addStaticBox(new Vector3f(0,-.5F,0),new Vector3f(50,.5F,50),new Quaternionf());
            body.impulse("torso_upper",new Vector3f(0,1.7F,0),new Vector3f(0,0,65));
            for(int i=0;i<720;i++)body.step(1F/120);
            var frame=body.frame();if(!Float.isFinite(frame.min().y)||frame.min().y<-.08F||frame.min().y>.08F||frame.supportContacts()==0)throw new IllegalStateException("Packaged physical floor/contact failure: "+frame);
            var report=new JsonObject();report.addProperty("passed",true);report.addProperty("body_count",frame.deformation().size());report.addProperty("min_y",frame.min().y);report.addProperty("contacts",frame.supportContacts());report.addProperty("loaded_from",String.valueOf(ArticulatedBody.class.getProtectionDomain().getCodeSource().getLocation()));
            Files.writeString(Path.of(args[1]),new GsonBuilder().setPrettyPrinting().create().toJson(report));System.out.println("PACKAGED_PHYSICS_R35_PASS "+report);
        }
    }
}
