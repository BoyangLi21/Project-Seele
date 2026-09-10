package com.projectseele.client.visual;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.projectseele.entity.*;
import com.projectseele.world.EntryPlugKinematics;
import net.minecraft.client.Minecraft;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import java.nio.file.*;
import java.util.HashMap;
import java.util.Map;

/** Independent native bone-matrix witnesses, enabled only in the disposable mechanical fixtures. */
public final class EvaDorsalR13Audit
{
    public static final boolean ENABLED=java.util.Set.of("r11-mechanics","r11-canonical").contains(System.getProperty("projectseele.regionalBuild",""));
    private static final class Frame {long time;Matrix4f liner,cover;}
    private static final Map<Integer,Frame> FRAMES=new HashMap<>();
    private static final JsonArray ROWS=new JsonArray();
    private static Path output;
    private static double maximumMouth,maximumCover,minimumAxis=1;
    private static int count;
    private static Vec3 point(Matrix4f matrix,Vec3 raw)
    {
        Vector3f p=matrix.transformPosition(new Vector3f((float)-raw.x/16,(float)raw.y/16,(float)raw.z/16));return new Vec3(p.x,p.y,p.z);
    }
    private static JsonArray array(Vec3 point)
    {JsonArray a=new JsonArray();a.add(point.x);a.add(point.y);a.add(point.z);return a;}
    public static void capture(EvaUnit01Entity eva,String bone,Matrix4f world)
    {
        if(!ENABLED||!(bone.equals("dorsal_liner")||bone.equals("dorsal_cover")))return;
        float open=EvaDorsalMechanism.open(eva),bow=EvaDorsalMechanism.bow(eva);if(open<.05F||bow<.98F)return;
        long time=FirstBattleSignals.clientFrameTime();Frame frame=FRAMES.computeIfAbsent(eva.getId(),i->new Frame());
        if(frame.time!=time){frame.time=time;frame.liner=frame.cover=null;}
        if(bone.equals("dorsal_liner"))frame.liner=new Matrix4f(world);else frame.cover=new Matrix4f(world);
        if(frame.liner==null||frame.cover==null)return;
        var profile=EvaDorsalProfile.of(eva);Vec3 raw=profile.centreModel(),axis=profile.hingeAxisModel();
        Vec3 actual=point(frame.liner,raw),direction=point(frame.liner,raw.add(profile.outwardModel())).subtract(actual).normalize();
        var socket=EntryPlugKinematics.socketTransform(eva);Vec3 renderedSocket=socket.translation().add(0,.01*EvaScale.RENDER_SCALE,0);double mouth=actual.distanceTo(renderedSocket),dot=direction.dot(socket.transformVector(new Vec3(0,0,1)).normalize());
        Quaternionf swing=new Quaternionf().rotationAxis((float)Math.toRadians(profile.openAngle()*open),(float)axis.x,(float)axis.y,(float)axis.z);
        Vec3 delta=raw.subtract(profile.hingeModel());Vector3f moved=swing.transform(new Vector3f((float)delta.x,(float)delta.y,(float)delta.z));Vec3 expectedRaw=profile.hingeModel().add(moved.x,moved.y,moved.z);
        double cover=point(frame.cover,raw).distanceTo(point(frame.liner,expectedRaw));maximumMouth=Math.max(maximumMouth,mouth);maximumCover=Math.max(maximumCover,cover);minimumAxis=Math.min(minimumAxis,dot);
        if(++count%8==0)
        {
            JsonObject row=new JsonObject();row.addProperty("variant",eva instanceof EvaPrototypeEntity?3:eva.getUnitVariant());row.addProperty("uuid",eva.getStringUUID());row.addProperty("open",open);row.addProperty("bow",bow);row.add("rendered_mouth",array(actual));row.add("socket",array(socket.translation()));row.addProperty("geo_renderer_lift",.01*EvaScale.RENDER_SCALE);row.addProperty("mouth_error",mouth);row.addProperty("axis_dot",dot);row.addProperty("cover_error",cover);ROWS.add(row);
        }
        if(count==1||count%24==0)
        {
            try
            {
                if(output==null){output=Minecraft.getInstance().gameDirectory.toPath().resolve("../artifacts/dorsal_tv_r13/native_pose_"+System.currentTimeMillis()+".json").normalize();Files.createDirectories(output.getParent());}
                JsonObject report=new JsonObject();report.addProperty("passed",maximumMouth<.05&&maximumCover<.05&&minimumAxis>.999);report.addProperty("samples",count);report.addProperty("max_mouth_error",maximumMouth);report.addProperty("max_cover_error",maximumCover);report.addProperty("minimum_axis_dot",minimumAxis);report.add("rows",ROWS);Files.writeString(output,report.toString());
            }
            catch(Exception e){throw new IllegalStateException("Dorsal render witness could not be saved",e);}
        }
        frame.liner=frame.cover=null;
    }
    private EvaDorsalR13Audit() {}
}
