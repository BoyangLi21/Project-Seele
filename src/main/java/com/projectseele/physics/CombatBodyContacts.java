package com.projectseele.physics;

import com.projectseele.entity.*;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import java.util.*;

/** Sweeps against posed body surfaces after Minecraft's coarse candidate query. */
public final class CombatBodyContacts
{
    private record Part(String bone,Matrix4f bind,List<float[][]> hulls,List<Vector3f> vertices) {}
    private static final Map<String,List<Part>> CACHE=new java.util.concurrent.ConcurrentHashMap<>();
    private static List<Part> parts(CombatBodyProfiles.Profile profile)
    {
        return CACHE.computeIfAbsent(profile.key(),key->{
            List<Part> parts=new ArrayList<>();
            for(var element:profile.definition().getAsJsonArray("bodies"))
            {
                var row=element.getAsJsonObject();float[] a=new float[16];for(int i=0;i<16;i++)a[i]=row.getAsJsonArray("bind").get(i).getAsFloat();
                Matrix4f bind=new Matrix4f().set(a).transpose();List<float[][]> hulls=new ArrayList<>();
                if(row.has("hull_planes"))for(var hull:row.getAsJsonArray("hull_planes"))
                {
                    var planes=hull.getAsJsonArray();float[][] values=new float[planes.size()][4];
                    for(int i=0;i<values.length;i++)for(int j=0;j<4;j++)values[i][j]=planes.get(i).getAsJsonArray().get(j).getAsFloat();hulls.add(values);
                }
                if(hulls.isEmpty())
                {
                    var size=row.getAsJsonArray("size");float x=size.get(0).getAsFloat(),y=row.get("shape").getAsString().equals("box")?size.get(1).getAsFloat():size.get(1).getAsFloat()*.5F+x,z=size.size()>2?size.get(2).getAsFloat():x;
                    hulls.add(new float[][]{{1,0,0,-x},{-1,0,0,-x},{0,1,0,-y},{0,-1,0,-y},{0,0,1,-z},{0,0,-1,-z}});
                }
                List<Vector3f> vertices=new ArrayList<>();
                if(row.has("hulls"))for(var hull:row.getAsJsonArray("hulls"))for(var vertex:hull.getAsJsonArray())vertices.add(CombatBodyProfiles.vector(vertex.getAsJsonArray()));
                parts.add(new Part(row.get("name").getAsString(),bind,hulls,List.copyOf(vertices)));
            }return List.copyOf(parts);
        });
    }
    public static double torsoFrontage(LivingEntity actor,Vec3 toward)
    {
        var profile=CombatBodyProfiles.get(actor);if(profile==null)return Double.NaN;
        var pose=CombatBodyDynamics.raw(actor,0);
        double current=frontage(actor,toward,profile,pose);
        // Reserve the trunk space of the committed contact pose before a
        // lunge. Checking only today's guard pose let the next shoulder/head
        // animation grow through the opponent after both roots had stopped.
        if(actor instanceof EvaUnit01Entity eva)
        {
            var next=EvaGameplayMotionR32.committedContactPose(eva);
            if(next!=null)current=Math.max(current,frontage(actor,toward,profile,next));
        }
        else if(actor instanceof SachielEntity angel&&SachielGameplayMotionR32.phrases()&&angel.isStrikeActive())
            current=Math.max(current,frontage(actor,toward,profile,SachielGameplayMotionR32.pose(angel,SachielStrike.contactStart(angel.strikeMode())+2)));
        return current;
    }
    private static double frontage(LivingEntity actor,Vec3 toward,CombatBodyProfiles.Profile profile,EvaBodyPose.Sample pose)
    {
        var matrices=CombatBodyProfiles.physicalMatrices(pose,profile);
        var direction=toward.toVector3f().rotateY(-(180-actor.getYRot())*(float)Math.PI/180);float reach=Float.NEGATIVE_INFINITY;
        for(var part:parts(profile))if(part.bone.startsWith("torso_")||part.bone.equals("head"))
        {
            var matrix=new Matrix4f(matrices.get(part.bone)).mul(part.bind);
            for(var vertex:part.vertices)reach=Math.max(reach,matrix.transformPosition(new Vector3f(vertex)).dot(direction));
        }
        return Float.isFinite(reach)?Math.max(0,reach/CombatBodyProfiles.BLOCK_TO_PHYSICS):Double.NaN;
    }
    public static Vec3 strikeAim(LivingEntity attacker,LivingEntity target)
    {
        Vec3 centre=target.getBoundingBox().getCenter();var profile=CombatBodyProfiles.get(target);
        if(profile!=null)
        {
            var pose=CombatBodyDynamics.active(target)?CombatBodyDynamics.sample(target,0):CombatBodyDynamics.raw(target,0);
            for(var part:parts(profile))if(part.bone.equals("torso_upper"))
            {
                var transform=new Matrix4f(CombatBodyProfiles.physicalMatrices(pose,profile).get(part.bone)).mul(part.bind);
                var point=transform.getTranslation(new Vector3f()).div(CombatBodyProfiles.BLOCK_TO_PHYSICS).rotateY((180-target.getYRot())*(float)Math.PI/180);
                centre=target.position().add(point.x,point.y,point.z);break;
            }
        }
        Vec3 direction=target.position().subtract(attacker.position()).multiply(1,0,1).normalize();
        return clip(target,centre.subtract(direction.scale(70)),centre,.2).orElse(centre).add(direction.scale(.65));
    }
    public static Optional<Vec3> clip(LivingEntity target,Vec3 from,Vec3 to,double radius)
    {
        var profile=CombatBodyProfiles.get(target);
        boolean field=target instanceof Angel angel&&angel.getAtField()>0||target instanceof EvaUnit01Entity eva&&eva.isAtFieldOn()&&eva.getAtFieldEnergy()>0;
        if(field||profile==null||!(target instanceof EvaUnit01Entity||target instanceof SachielEntity))
        {var box=target.getBoundingBox().inflate(radius);return box.contains(from)?Optional.of(from):box.clip(from,to);}
        var pose=CombatBodyDynamics.active(target)?CombatBodyDynamics.sample(target,0):CombatBodyDynamics.raw(target,0);
        AnatomicalLimbConstraints.apply(pose,profile);var matrices=CombatBodyProfiles.physicalMatrices(pose,profile);
        float angle=-(180-target.getYRot())*(float)Math.PI/180,scale=CombatBodyProfiles.BLOCK_TO_PHYSICS;
        Vector3f start=from.subtract(target.position()).toVector3f().rotateY(angle).mul(scale),end=to.subtract(target.position()).toVector3f().rotateY(angle).mul(scale);
        float best=Float.POSITIVE_INFINITY;
        for(var part:parts(profile))
        {
            Matrix4f inverse=new Matrix4f(matrices.get(part.bone)).mul(part.bind).invert();Vector3f p=inverse.transformPosition(new Vector3f(start)),q=inverse.transformPosition(new Vector3f(end));
            for(var hull:part.hulls)
            {
                float enter=0,leave=Math.min(1,best);boolean miss=false;
                for(var plane:hull)
                {
                    float a=plane[0]*p.x+plane[1]*p.y+plane[2]*p.z+plane[3]-(float)radius*scale;
                    float b=plane[0]*q.x+plane[1]*q.y+plane[2]*q.z+plane[3]-(float)radius*scale;
                    if(a>0&&b>0){miss=true;break;}if(a<=0&&b<=0)continue;
                    float t=a/(a-b);if(a>0)enter=Math.max(enter,t);else leave=Math.min(leave,t);
                    if(enter>leave){miss=true;break;}
                }
                if(!miss&&enter<=leave)best=Math.min(best,enter);
            }
        }
        return Float.isFinite(best)?Optional.of(from.lerp(to,best)):Optional.empty();
    }
    public static net.minecraft.world.phys.AABB coreBounds(LivingEntity actor)
    {
        var profile=CombatBodyProfiles.get(actor);if(profile==null)return actor.getBoundingBox();
        var pose=CombatBodyDynamics.active(actor)?CombatBodyDynamics.sample(actor,0):CombatBodyDynamics.raw(actor,0);
        var matrices=CombatBodyProfiles.physicalMatrices(pose,profile);net.minecraft.world.phys.AABB result=null;
        for(var part:parts(profile))if(part.bone.startsWith("torso_"))
        {
            var transform=new Matrix4f(matrices.get(part.bone)).mul(part.bind);
            for(var vertex:part.vertices)
            {
                var p=transform.transformPosition(new Vector3f(vertex)).div(CombatBodyProfiles.BLOCK_TO_PHYSICS).rotateY((180-actor.getYRot())*(float)Math.PI/180);
                var v=actor.position().add(p.x,p.y,p.z);var box=new net.minecraft.world.phys.AABB(v,v);result=result==null?box:result.minmax(box);
            }
        }
        return result==null?actor.getBoundingBox():result;
    }
    private CombatBodyContacts(){}
}
