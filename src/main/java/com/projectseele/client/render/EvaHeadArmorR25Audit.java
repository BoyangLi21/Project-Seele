package com.projectseele.client.render;

import com.google.gson.*;
import com.projectseele.entity.*;
import net.minecraft.resources.ResourceLocation;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import java.nio.file.*;
import java.util.*;

/** Review-only surface-intersection witnesses from the actual drawn bone matrices. */
public final class EvaHeadArmorR25Audit
{
    public static final boolean ENABLED=Set.of("r25-terrain","r25-rifle").contains(System.getProperty("projectseele.regionalBuild",""));
    private static final Set<String> PARTS=Set.of("head","pylon_l","pylon_r","dorsal_cover");
    private static final class Frame{long time;boolean sampled;final Map<String,Matrix4f> poses=new HashMap<>();}
    private static final Map<Integer,Frame> FRAMES=new HashMap<>();
    private static final Map<String,EvaHeadClearance.Node> ARMOR=new HashMap<>();
    private static final Map<String,List<EvaHeadClearance.Triangle>> HEADS=new HashMap<>();
    private static final JsonArray ROWS=new JsonArray();private static Path output;
    public static void capture(EvaUnit01Entity eva,String bone,Matrix4f world)
    {
        if(!ENABLED||!PARTS.contains(bone)||eva.rifleProneBlend(1)<.95F||eva.tickCount%10!=0)return;
        long now=FirstBattleSignals.clientFrameTime();var frame=FRAMES.computeIfAbsent(eva.getId(),id->new Frame());
        if(now!=frame.time){frame.time=now;frame.poses.clear();frame.sampled=false;}
        frame.poses.put(bone,new Matrix4f(world));if(frame.sampled||frame.poses.size()!=PARTS.size())return;frame.sampled=true;
        String name=eva instanceof EvaPrototypeEntity un?(un.getUNSerial()==0?"eva_prototype":"eva_un01"):"eva_unit0"+eva.getUnitVariant();
        var resource=new ResourceLocation("projectseele","mesh/"+name+".mesh.json");
        var head=HEADS.computeIfAbsent(name,key->EvaHeadClearance.triangles(resource,"head"));
        var row=new JsonObject();row.addProperty("tick",eva.tickCount);row.addProperty("head_pitch",eva.pilotHeadPitchForRender(1));row.addProperty("head_yaw",eva.pilotHeadYawForRender(1));
        row.addProperty("weapon",eva.getWeapon());row.addProperty("stance",eva.rifleStanceLevel(1));
        row.addProperty("variant",eva.getUnitVariant());
        row.addProperty("weapon_pitch",eva.getCannonAimPitch());
        for(String part:List.of("pylon_l","pylon_r","dorsal_cover"))
        {
            var tree=ARMOR.computeIfAbsent(name+"/"+part,key->{var ts=EvaHeadClearance.triangles(resource,part);return ts.isEmpty()?null:EvaHeadClearance.tree(ts);});
            if(tree==null){row.addProperty(part,-1);continue;}
            Matrix4f transform=new Matrix4f(frame.poses.get(part)).invert().mul(frame.poses.get("head"));int hits=0;
            for(var t:head)
            {
                var posed=new EvaHeadClearance.Triangle(transform.transformPosition(new Vector3f(t.a())),transform.transformPosition(new Vector3f(t.b())),transform.transformPosition(new Vector3f(t.c())));
                if(EvaHeadClearance.hits(tree,posed))hits++;
            }
            row.addProperty(part,hits);
        }
        ROWS.add(row);
        try
        {
            if(output==null){output=Path.of("../artifacts/facility_r25/head_armor_"+System.currentTimeMillis()+".json");Files.createDirectories(output.getParent());}
            var report=new JsonObject();report.addProperty("native_drawn_matrices",true);report.add("samples",ROWS);Files.writeString(output,report.toString());
        }
        catch(Exception e){throw new IllegalStateException("Native head/armor evidence",e);}
    }
    private EvaHeadArmorR25Audit() {}
}
