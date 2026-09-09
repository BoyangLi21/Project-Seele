package com.projectseele.entity;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.projectseele.ProjectSeele;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.phys.Vec3;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** One authored clock drives world roots, poses, sockets and shots. */
public final class FirstBattleClip
{
    public static final int DURATION_TICKS=460,DEATH_TICK=372,RETURN_TICK=432;
    public record BonePose(String[] names,Quaternionf[] rotations,Vector3f[] positions) {}
    public record CameraPose(Vec3 position,Vec3 target,float fov) {}
    private record Role(String[] bones,Quaternionf[][] rotations,Vector3f[][] positions,Map<String,Vec3[]> curves) {}
    private record Data(float fps,Map<String,Role> roles,Vec3[] cameras,Vec3[] targets,float[] fov) {}
    private static final Data DATA=load();
    private static Vec3 vector(JsonArray p){return new Vec3(p.get(0).getAsDouble(),p.get(1).getAsDouble(),p.get(2).getAsDouble());}
    private static Vec3[] vectors(JsonArray rows)
    {
        Vec3[] result=new Vec3[rows.size()];for(int i=0;i<result.length;i++)result[i]=vector(rows.get(i).getAsJsonArray());return result;
    }
    private static Data load()
    {
        try(var stream=FirstBattleClip.class.getResourceAsStream("/assets/projectseele/motion/first_battle_r10.json"))
        {
            if(stream==null)throw new IllegalStateException("Missing first-battle authored clip");
            JsonObject root=JsonParser.parseReader(new InputStreamReader(stream,StandardCharsets.UTF_8)).getAsJsonObject();float fps=root.get("fps").getAsFloat();
            Map<String,Role> roles=new HashMap<>();
            for(String name:List.of("eva","angel"))
            {
                var role=root.getAsJsonObject(name);var names=role.getAsJsonArray("bones");String[] bones=new String[names.size()];
                for(int i=0;i<bones.length;i++)bones[i]=names.get(i).getAsString();
                var frames=role.getAsJsonArray("frames");Quaternionf[][] qs=new Quaternionf[frames.size()][bones.length];Vector3f[][] ps=new Vector3f[frames.size()][bones.length];
                for(int i=0;i<frames.size();i++)
                {
                    var frame=frames.get(i).getAsJsonObject();var rotations=frame.getAsJsonArray("rotation_wxyz");var offsets=frame.getAsJsonObject("bone_position_xyz");
                    if(rotations.size()!=bones.length)throw new IllegalArgumentException("First-battle bone count mismatch");
                    for(int b=0;b<bones.length;b++)
                    {
                        var q=rotations.get(b).getAsJsonArray();qs[i][b]=new Quaternionf(q.get(1).getAsFloat(),q.get(2).getAsFloat(),q.get(3).getAsFloat(),q.get(0).getAsFloat()).normalize();
                        Vec3 p=bones[b].equals("root")?vector(frame.getAsJsonArray("root_m")).scale(112):offsets!=null&&offsets.has(bones[b])?vector(offsets.getAsJsonArray(bones[b])):Vec3.ZERO;
                        ps[i][b]=new Vector3f((float)p.x,(float)p.y,(float)p.z);
                    }
                }
                Map<String,Vec3[]> curves=new HashMap<>();
                for(String curve:List.of("root_blocks","eye_blocks","look_blocks","socket_blocks","socket_outward_blocks","socket_up_blocks","hand_l_blocks","hand_r_blocks","foot_l_blocks","foot_r_blocks","core_blocks","waist_blocks"))
                    if(role.has(curve))curves.put(curve,vectors(role.getAsJsonArray(curve)));
                roles.put(name,new Role(bones,qs,ps,Map.copyOf(curves)));
            }
            var camera=root.getAsJsonObject("camera");var f=camera.getAsJsonArray("fov");float[] fov=new float[f.size()];for(int i=0;i<fov.length;i++)fov[i]=f.get(i).getAsFloat();
            ProjectSeele.LOGGER.info("R10 first battle loaded: fps={} frames={} durationTicks={}",fps,fov.length,DURATION_TICKS);
            return new Data(fps,Map.copyOf(roles),vectors(camera.getAsJsonArray("position")),vectors(camera.getAsJsonArray("target")),fov);
        }
        catch(Exception e){ProjectSeele.LOGGER.error("First-battle clip rejected",e);return null;}
    }
    public static boolean ready(){return DATA!=null;}
    private static float frame(float seconds,int length){return Mth.clamp(seconds*DATA.fps,0,length-1);}
    private static Vec3 sample(Vec3[] values,float seconds)
    {
        if(values==null||values.length==0)return Vec3.ZERO;float f=frame(seconds,values.length);int a=(int)f,b=Math.min(a+1,values.length-1);return values[a].lerp(values[b],f-a);
    }
    public static BonePose pose(boolean eva,float seconds)
    {
        if(DATA==null)return new BonePose(new String[0],new Quaternionf[0],new Vector3f[0]);
        Role role=DATA.roles.get(eva?"eva":"angel");float f=frame(seconds,role.rotations.length);int a=(int)f,b=Math.min(a+1,role.rotations.length-1);float mix=f-a;
        Quaternionf[] qs=new Quaternionf[role.bones.length];Vector3f[] ps=new Vector3f[role.bones.length];
        for(int i=0;i<qs.length;i++){qs[i]=new Quaternionf(role.rotations[a][i]).slerp(role.rotations[b][i],mix);ps[i]=new Vector3f(role.positions[a][i]).lerp(role.positions[b][i],mix);}
        return new BonePose(role.bones,qs,ps);
    }
    public static Vec3 world(FirstBattleSignals.Spec spec,Vec3 local)
    {
        Vec3 f=Vec3.directionFromRotation(0,spec.yaw()),side=new Vec3(f.z,0,-f.x);
        return spec.origin().add(side.scale(local.x)).add(0,local.y,0).add(f.scale(local.z));
    }
    public static float smooth(float value)
    {
        float t=Mth.clamp(value,0,1);return t*t*t*(10+t*(-15+6*t));
    }
    public static Vec3 localPoint(FirstBattleSignals.Spec spec,boolean eva,String curve,float seconds)
    {
        if(DATA==null)return Vec3.ZERO;Vec3 p=sample(DATA.roles.get(eva?"eva":"angel").curves.get(curve),seconds);
        if(!eva)p=p.add(0,spec.initialHeight()*(1-smooth(seconds/1.2F)),(spec.initialDistance()-34)*(1-smooth(seconds/1.2F)));
        return p;
    }
    public static Vec3 point(FirstBattleSignals.Spec spec,boolean eva,String curve,float seconds){return world(spec,localPoint(spec,eva,curve,seconds));}
    public static float yaw(FirstBattleSignals.Spec spec,boolean eva,float seconds)
    {
        return Mth.rotLerp(smooth(seconds/1.2F),eva?spec.evaYaw():spec.angelYaw(),spec.yaw()+(eva?0:180));
    }
    public static CameraPose camera(FirstBattleSignals.Spec spec,float seconds)
    {
        if(DATA==null)return new CameraPose(spec.origin().add(0,45,-50),spec.origin().add(0,30,0),70);
        float f=frame(seconds,DATA.fov.length);int a=(int)f,b=Math.min(a+1,DATA.fov.length-1);
        return new CameraPose(world(spec,sample(DATA.cameras,seconds)),world(spec,sample(DATA.targets,seconds)),Mth.lerp(f-a,DATA.fov[a],DATA.fov[b]));
    }
    public static void applyKinematics(Mob entity)
    {
        if(!(entity instanceof FirstBattleSignals.Actor actor)||!actor.firstBattleSignals().active(entity)||DATA==null)return;
        var signals=actor.firstBattleSignals();var spec=signals.spec(entity);boolean eva=actor.isFirstBattleEva();
        float time=signals.time(entity,1);Vec3 current=point(spec,eva,"root_blocks",time),previous=point(spec,eva,"root_blocks",Math.max(0,time-.05F));
        if("r10-choreography".equals(System.getProperty("projectseele.regionalBuild","")))previous=current;
        entity.setPos(current);entity.xOld=entity.xo=previous.x;entity.yOld=entity.yo=previous.y;entity.zOld=entity.zo=previous.z;
        float heading=yaw(spec,eva,time),oldHeading=yaw(spec,eva,Math.max(0,time-.05F));entity.setYRot(heading);entity.yBodyRot=entity.yHeadRot=heading;entity.yRotO=entity.yBodyRotO=entity.yHeadRotO=oldHeading;
        entity.setDeltaMovement(Vec3.ZERO);entity.fallDistance=0;entity.noPhysics=true;entity.setNoGravity(true);
    }
    public static Vec3 renderOffset(net.minecraft.world.entity.Entity entity,float partial)
    {
        if(!(entity instanceof FirstBattleSignals.Actor actor)||!actor.firstBattleSignals().active(entity)||DATA==null)return Vec3.ZERO;
        var signals=actor.firstBattleSignals();Vec3 desired=point(signals.spec(entity),actor.isFirstBattleEva(),"root_blocks",signals.time(entity,partial));
        Vec3 interpolated=new Vec3(Mth.lerp((double)partial,entity.xOld,entity.getX()),Mth.lerp((double)partial,entity.yOld,entity.getY()),Mth.lerp((double)partial,entity.zOld,entity.getZ()));return desired.subtract(interpolated);
    }
    private FirstBattleClip() {}
}
