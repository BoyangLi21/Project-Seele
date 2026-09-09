package com.projectseele.entity;
import com.google.gson.JsonParser;
import com.projectseele.ProjectSeele;
import net.minecraft.world.phys.Vec3;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
/** Support hull from the actual weapon, shared by rendered attachment and ballistics. */
public final class EvaRifleClearance
{
    private static final Vec3[] POINTS=load();
    private static Vec3[] load()
    {
        try(var in=EvaRifleClearance.class.getResourceAsStream("/assets/projectseele/motion/rifle_clearance_r10.json"))
        {
            var a=JsonParser.parseReader(new InputStreamReader(in,StandardCharsets.UTF_8)).getAsJsonObject().getAsJsonArray("points");Vec3[] result=new Vec3[a.size()];
            for(int i=0;i<result.length;i++){var p=a.get(i).getAsJsonArray();result[i]=new Vec3(p.get(0).getAsDouble(),p.get(1).getAsDouble(),p.get(2).getAsDouble());}return result;
        }
        catch(Exception failure){ProjectSeele.LOGGER.error("Rifle clearance hull unavailable",failure);return new Vec3[0];}
    }
    public static double lift(Vec3 grip,Vec3 right,Vec3 forward,Vec3 up,double floor)
    {
        double minimum=Double.POSITIVE_INFINITY;
        for(Vec3 p:POINTS)minimum=Math.min(minimum,grip.y+right.y*p.x+forward.y*p.y+up.y*p.z);
        return Math.max(0,floor+.12-minimum);
    }
    private EvaRifleClearance() {}
}
