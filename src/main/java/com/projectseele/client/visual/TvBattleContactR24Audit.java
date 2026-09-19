package com.projectseele.client.visual;

import com.google.gson.*;
import com.projectseele.entity.*;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import java.nio.file.*;
import java.util.*;

/** Actual vertices submitted by the live renderer, after pose blending and skinning. */
public final class TvBattleContactR24Audit
{
    public static final boolean ENABLED="r24-campaign".equals(System.getProperty("projectseele.regionalBuild",""))&&!Boolean.getBoolean("projectseele.firstBattleMovieOnly");
    private static final Set<String> seen=new HashSet<>();private static final JsonArray rows=new JsonArray();
    private static JsonObject markers;
    public static void sample(EvaUnit01Entity eva,String bone,float[] vertices,int stride,float px,float py,float pz,Matrix4f world)
    {
        if(!ENABLED||!eva.isFirstBattleActive()||!(bone.startsWith("foot_")||bone.startsWith("shin_")||bone.startsWith("leg_")))return;
        float time=eva.firstBattleSignals().time(eva,1);String key=bone+":"+Math.round(time*10);if(!seen.add(key))return;
        var spec=eva.firstBattleSignals().spec(eva);float lowest=Float.POSITIVE_INFINITY;Vector3f v=new Vector3f();
        for(int i=0;i<vertices.length;i+=stride)
        {world.transformPosition(v.set(-(vertices[i]+px)/16,(vertices[i+1]+py)/16,(vertices[i+2]+pz)/16));lowest=Math.min(lowest,v.y);}
        var row=new JsonObject();row.addProperty("time",time);row.addProperty("part",bone);row.addProperty("mesh_min_above_floor",lowest-spec.origin().y);
        if(bone.startsWith("foot_"))
        {
            if(markers==null)try{markers=JsonParser.parseString(Files.readString(Path.of("projectseele-local-maps/r24_contact_markers.json"))).getAsJsonObject();}catch(Exception e){throw new IllegalStateException(e);}
            var marker=markers.getAsJsonArray(bone);world.transformPosition(v.set(marker.get(0).getAsFloat(),marker.get(1).getAsFloat(),marker.get(2).getAsFloat()));var expected=FirstBattleClip.point(spec,true,bone+"_blocks",time);
            row.addProperty("marker_error",v.distance(expected.toVector3f()));row.addProperty("actual_marker_y",v.y);row.addProperty("authored_marker_y",expected.y);
        }
        rows.add(row);
        if(rows.size()%24==0)try{Files.writeString(Path.of("../artifacts/facility_r24/validation/native_battle_contacts.json"),new GsonBuilder().setPrettyPrinting().create().toJson(rows));}catch(Exception e){throw new IllegalStateException(e);}
    }
    private TvBattleContactR24Audit(){}
}
