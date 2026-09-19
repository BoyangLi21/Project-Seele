package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.world.*;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.phys.Vec3;
import java.nio.file.*;

/** Export exact production capsule poses; Python checks the rendered machinery. */
public final class PlugRouteR25Witness
{
    public static void capture(ServerLevel level, Path world) throws Exception
    {
        var result=new JsonArray();
        for(int unit=0;unit<3;unit++)
        {
            var eva=EvaLogisticsDirector.canonicalUnit(level,unit);
            var plug=EntryPlugDirector.canonical(level,unit);
            if(eva==null||plug==null||!EvaLogisticsDirector.status(level,unit).phase().equals("PARKED"))
                throw new IllegalStateException("All three original parked units are needed for the capsule sweep");
            var yaw=new org.joml.Quaternionf().rotationY((float)Math.toRadians(180-eva.getYRot()));
            var frame=new RigidTransform(eva.position(),yaw.x,yaw.y,yaw.z,yaw.w);
            var inverse=frame.inverse();var row=new JsonObject();row.addProperty("variant",unit);
            row.addProperty("eva_uuid",eva.getStringUUID());row.addProperty("plug_uuid",plug.getStringUUID());
            var poses=new JsonArray();var dock=plug.getCanonicalTransform();
            for(int i=0;i<=400;i++)
            {
                var pose=inverse.compose(EntryPlugKinematics.insertionTransform(eva,dock,i/400D));
                var sample=new JsonObject();sample.addProperty("progress",i/400D);
                var a=new JsonArray();a.add(pose.translation().x);a.add(pose.translation().y);a.add(pose.translation().z);
                var q=new JsonArray();q.add(pose.qx());q.add(pose.qy());q.add(pose.qz());q.add(pose.qw());
                sample.add("translation",a);sample.add("quaternion_xyzw",q);poses.add(sample);
            }
            row.add("poses",poses);result.add(row);
        }
        Files.writeString(world.resolve("r25_plug_route_witness.json"),new Gson().toJson(result));
    }
    private PlugRouteR25Witness() {}
}
