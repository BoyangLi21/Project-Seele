package com.projectseele.entity;

import com.google.gson.*;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import java.nio.file.*;
import java.util.*;

/** One calibrated skeleton supplies both the displayed attack and its contact sweep. */
public final class SachielGameplayMotionR32
{
    private record Clip(Quaternionf[][] rotations,Vector3f[][] positions,Vec3[] travel,float contact,String side) {}
    private record Data(String[] names,Map<String,EvaBodyPose.Bone> rig,Map<String,Clip> clips) {}
    private static Optional<Data> cached;
    private static Vector3f vector(JsonElement value){var a=value.getAsJsonArray();return new Vector3f(a.get(0).getAsFloat(),a.get(1).getAsFloat(),a.get(2).getAsFloat());}
    private static synchronized Data data()
    {
        if(cached!=null)return cached.orElse(null);
        var file=Path.of("projectseele-local-maps/sachiel_gameplay_r32.json");
        if(!Files.isRegularFile(file)){cached=Optional.empty();return null;}
        try
        {
            var json=JsonParser.parseString(Files.readString(file)).getAsJsonObject();
            if(json.get("schema").getAsInt()!=2||!json.get("rig_key").getAsString().equals("sachiel"))throw new IllegalArgumentException("Sachiel motion contract");
            var names=new ArrayList<String>();for(var n:json.getAsJsonArray("bones"))names.add(n.getAsString());
            Map<String,EvaBodyPose.Bone> rig=new LinkedHashMap<>();
            for(var row:json.getAsJsonArray("rig"))
            {var b=row.getAsJsonObject();String n=b.get("name").getAsString();rig.put(n,new EvaBodyPose.Bone(n,b.has("parent")?b.get("parent").getAsString():null,vector(b.get("pivot")).mul(-1,1,1).div(16),new Quaternionf()));}
            Map<String,Clip> clips=new HashMap<>();
            for(var entry:json.getAsJsonObject("clips").entrySet())
            {
                var c=entry.getValue().getAsJsonObject();var frames=c.getAsJsonArray("frames");var rotations=new Quaternionf[frames.size()][names.size()];var positions=new Vector3f[frames.size()][names.size()];var travel=new Vec3[frames.size()];
                for(int f=0;f<frames.size();f++)
                {
                    var frame=frames.get(f).getAsJsonObject();var qs=frame.getAsJsonArray("rotation_wxyz");
                    for(int b=0;b<names.size();b++)
                    {
                        var q=qs.get(b).getAsJsonArray();rotations[f][b]=new Quaternionf(-q.get(1).getAsFloat(),-q.get(2).getAsFloat(),q.get(3).getAsFloat(),q.get(0).getAsFloat()).normalize();
                        String n=names.get(b);var p=n.equals("root")?vector(frame.get("root_m")).mul(112):frame.has("bone_position_xyz")&&frame.getAsJsonObject("bone_position_xyz").has(n)?vector(frame.getAsJsonObject("bone_position_xyz").get(n)):new Vector3f();
                        positions[f][b]=p.mul(-1,1,1).div(16);
                    }
                    travel[f]=new Vec3(vector(c.getAsJsonArray("trajectory_m").get(f)));
                }
                clips.put(entry.getKey().substring(4),new Clip(rotations,positions,travel,c.get("contact_phase").getAsFloat(),c.get("leading_side").getAsString()));
            }
            cached=Optional.of(new Data(names.toArray(String[]::new),Map.copyOf(rig),Map.copyOf(clips)));return cached.get();
        }
        catch(Exception error){throw new IllegalStateException("Rejected calibrated Sachiel motion",error);}
    }
    public static boolean ready(){return data()!=null;}
    public static String name(int mode){return switch(mode){case SachielStrike.PILE->"cross";case SachielStrike.HOOK->"hook";case SachielStrike.OVERHEAD->"heavy";case SachielStrike.SHOVE->"shove";case SachielStrike.STOMP->"stomp";default->"jab";};}
    public static boolean left(int mode){return data().clips.get(name(mode)).side.equals("l");}
    private static float phase(int mode,float age)
    {
        var c=data().clips.get(name(mode));float contact=SachielStrike.contactStart(mode)+2,progress=Mth.clamp(age,0,SachielStrike.duration(mode));
        return progress<contact?c.contact*progress/contact:Mth.lerp((progress-contact)/(SachielStrike.duration(mode)-contact),c.contact,1);
    }
    public static EvaBodyPose.Sample pose(SachielEntity e,float age)
    {
        var d=data();var c=d.clips.get(name(e.strikeMode()));float at=phase(e.strikeMode(),age)*(c.rotations.length-1);int a=(int)at,b=Math.min(a+1,c.rotations.length-1);var sample=new EvaBodyPose.Sample(d.rig);
        for(int i=0;i<d.names.length;i++){sample.rotations.put(d.names[i],new Quaternionf(c.rotations[a][i]).slerp(c.rotations[b][i],at-a));sample.positions.put(d.names[i],new Vector3f(c.positions[a][i]).lerp(c.positions[b][i],at-a));}
        return sample;
    }
    public static Vec3 travel(int mode,float age)
    {
        var c=data().clips.get(name(mode));float at=phase(mode,age)*(c.travel.length-1);int a=(int)at,b=Math.min(a+1,c.travel.length-1);return c.travel[a].lerp(c.travel[b],at-a);
    }
    public static SachielStrike.Frame contact(SachielEntity e,float age,float partial,boolean left)
    {
        var pose=pose(e,age);String side=left?"l":"r",name=e.strikeMode()==SachielStrike.STOMP?"foot_"+side:"hand_"+side;
        var matrix=SachielStrike.root(e,partial);var local=pose.matrix(name).transformPosition(new Vector3f(pose.rig.get(name).pivot()));var hand=new Vec3(matrix.transformPosition(local));
        String upstream=e.strikeMode()==SachielStrike.STOMP?"shin_"+side:"forearm_"+side;
        var elbow=new Vec3(matrix.transformPosition(pose.matrix(upstream).transformPosition(new Vector3f(pose.rig.get(upstream).pivot()))));
        Vec3 direction=hand.subtract(elbow).normalize();float extension=e.strikeMode()==SachielStrike.PILE?EvaDorsalMechanism.smooth((age-21)/5)*(1-EvaDorsalMechanism.smooth((age-30)/7)):0;
        return new SachielStrike.Frame(hand,hand.add(direction.scale(extension*25)),direction,1,extension);
    }
    private SachielGameplayMotionR32(){}
}
