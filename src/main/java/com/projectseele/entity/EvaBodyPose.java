package com.projectseele.entity;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import net.minecraft.util.Mth;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/** The same body pose supplies rendered bones and authoritative firearm sockets. */
public final class EvaBodyPose
{
    public record Bone(String name,String parent,Vector3f pivot,Quaternionf bindRotation) {}
    private record Clip(float duration,Quaternionf[][] rotations,Vector3f[][] positions) {}
    private record Data(String[] names,Map<String,Integer> index,Map<String,Clip> clips,
                        Map<Integer,Map<String,Bone>> rigs,Map<String,Vector3f[]> support,
                        JsonObject prone,JsonObject grip,JsonObject mocap,Map<Integer,Vector3f> eyes,Map<Integer,Map<String,Vector3f[]>> rigSupport,
                        Map<Integer,List<net.minecraft.world.phys.AABB>> carrierHulls,Map<Integer,Map<String,Clip>> combatClips) {}
    private static volatile Data data;

    public static final class Sample
    {
        public final Map<String,Bone> rig;
        public final Map<String,Quaternionf> rotations=new HashMap<>();
        public final Map<String,Vector3f> positions=new HashMap<>();
        private final Map<String,Matrix4f> matrices=new HashMap<>();
        Sample(Map<String,Bone> rig)
        {
            this.rig=rig;for(String n:rig.keySet()){rotations.put(n,new Quaternionf());positions.put(n,new Vector3f());}
        }
        public Matrix4f matrix(String name)
        {
            Matrix4f cached=matrices.get(name);if(cached!=null)return new Matrix4f(cached);
            Bone b=rig.get(name);Vector3f p=b.pivot();var local=new Matrix4f().translation(positions.get(name))
                    .translate(p).rotate(rotations.get(name)).translate(-p.x,-p.y,-p.z);
            if(b.parent()!=null)local=matrix(b.parent()).mul(local);
            matrices.put(name,local);return new Matrix4f(local);
        }
        public void dirty(){matrices.clear();}
    }

    private static JsonObject resource(String path)throws Exception
    {
        try(var stream=EvaBodyPose.class.getResourceAsStream("/assets/projectseele/"+path))
        {
            if(stream==null)throw new IllegalStateException(path);
            return JsonParser.parseReader(new InputStreamReader(stream,StandardCharsets.UTF_8)).getAsJsonObject();
        }
    }
    public static synchronized void reload()
    {
        try
        {
            Path path=Path.of(System.getProperty("projectseele.bodyPoseReview","projectseele-local-maps/eva_body_r25.json"));
            if(!Files.isRegularFile(path))path=Path.of("projectseele-local-maps/eva_body_r11.json");
            if(!Files.isRegularFile(path))path=Path.of("projectseele-local-maps/eva_body_r06.json");
            if(!Files.isRegularFile(path))path=Path.of("projectseele-local-maps/eva_body_r05.json");
            JsonObject all;
            if(Files.isRegularFile(path))all=JsonParser.parseString(Files.readString(path)).getAsJsonObject();
            else
            {
                all=new JsonObject();all.add("motion",resource("motion/eva_connected_locomotion_v1.json"));
                all.add("rig",resource("eva/eva_rig_schema.json").get("bones"));
            }
            var motion=all.getAsJsonObject("motion");var boneNames=motion.getAsJsonArray("bones");String[] names=new String[boneNames.size()];Map<String,Integer> index=new HashMap<>();
            for(int i=0;i<names.length;i++){names[i]=boneNames.get(i).getAsString();index.put(names[i],i);}
            Map<String,Clip> clips=new HashMap<>();
            for(var e:motion.getAsJsonObject("clips").entrySet())
            {
                var c=e.getValue().getAsJsonObject();var fs=c.getAsJsonArray("frames");Quaternionf[][] qs=new Quaternionf[fs.size()][names.length];Vector3f[][] ps=new Vector3f[fs.size()][names.length];
                for(int f=0;f<fs.size();f++)
                {
                    var frame=fs.get(f).getAsJsonObject();var a=frame.getAsJsonArray("rotation_wxyz");
                    for(int b=0;b<names.length;b++)
                    {
                        var q=a.get(b).getAsJsonArray();qs[f][b]=new Quaternionf(-q.get(1).getAsFloat(),-q.get(2).getAsFloat(),q.get(3).getAsFloat(),q.get(0).getAsFloat()).normalize();
                        Vector3f v=new Vector3f();if(names[b].equals("root"))v=vector(frame.get("root_m")).mul(112);
                        else if(frame.has("bone_position_xyz")&&frame.getAsJsonObject("bone_position_xyz").has(names[b]))v=vector(frame.getAsJsonObject("bone_position_xyz").get(names[b]));
                        ps[f][b]=v.mul(-1,1,1).div(16);
                    }
                }
                clips.put(e.getKey(),new Clip(c.get("duration_seconds").getAsFloat(),qs,ps));
            }
            Map<Integer,Map<String,Bone>> rigs=new HashMap<>();
            for(int variant=0;variant<5;variant++)
            {
                if(variant>=3&&(!all.has("rigs")||!all.getAsJsonObject("rigs").has(Integer.toString(variant))))continue;
                var list=all.has("rigs")?all.getAsJsonObject("rigs").getAsJsonArray(Integer.toString(variant)):all.getAsJsonArray("rig");Map<String,Bone> bones=new HashMap<>();
                for(var e:list)
                {
                    var b=e.getAsJsonObject();String parent=b.has("parent")&&!b.get("parent").isJsonNull()?b.get("parent").getAsString():null;
                    String name=b.get("name").getAsString();Vector3f bind=b.has("rotation")?vector(b.get("rotation")):b.has("bindRotationDegrees")?vector(b.get("bindRotationDegrees")):new Vector3f();bind.mul(Mth.DEG_TO_RAD);
                    bones.put(name,new Bone(name,parent,vector(b.get("pivot")).mul(-1,1,1).div(16),new Quaternionf().rotationZYX(bind.z,-bind.y,-bind.x)));
                }
                rigs.put(variant,Map.copyOf(bones));
            }
            Map<String,Vector3f[]> support=new HashMap<>();
            if(all.has("support"))for(var e:all.getAsJsonObject("support").entrySet())
            {
                var a=e.getValue().getAsJsonArray();Vector3f[] points=new Vector3f[a.size()];for(int i=0;i<points.length;i++)points[i]=vector(a.get(i)).div(16);support.put(e.getKey(),points);
            }
            Map<Integer,Vector3f> eyes=new HashMap<>();
            for(int variant:rigs.keySet())eyes.put(variant,all.has("eye_positions")&&all.getAsJsonObject("eye_positions").has(Integer.toString(variant))?vector(all.getAsJsonObject("eye_positions").get(Integer.toString(variant))).div(16):new Vector3f(variant==0?0:.15F,10.64F,-.75F));
            Map<Integer,Map<String,Vector3f[]>> rigSupport=new HashMap<>();
            if(all.has("rig_support"))for(var entry:all.getAsJsonObject("rig_support").entrySet())
            {
                Map<String,Vector3f[]> points=new HashMap<>();for(var e:entry.getValue().getAsJsonObject().entrySet())
                {var a=e.getValue().getAsJsonArray();Vector3f[] p=new Vector3f[a.size()];for(int i=0;i<p.length;i++)p[i]=vector(a.get(i)).div(16);points.put(e.getKey(),p);}rigSupport.put(Integer.parseInt(entry.getKey()),Map.copyOf(points));
            }
            Map<Integer,List<net.minecraft.world.phys.AABB>> carrierHulls=new HashMap<>();
            if(all.has("carrier_hulls"))for(var entry:all.getAsJsonObject("carrier_hulls").entrySet())
            {
                var boxes=new ArrayList<net.minecraft.world.phys.AABB>();
                for(var row:entry.getValue().getAsJsonArray())
                {var a=row.getAsJsonArray();boxes.add(new net.minecraft.world.phys.AABB(a.get(0).getAsDouble(),a.get(1).getAsDouble(),a.get(2).getAsDouble(),a.get(3).getAsDouble(),a.get(4).getAsDouble(),a.get(5).getAsDouble()));}
                carrierHulls.put(Integer.parseInt(entry.getKey()),List.copyOf(boxes));
            }
            Map<Integer,Map<String,Clip>> combatClips=new HashMap<>();
            for(int variant:rigs.keySet())
            {
                var capture=Path.of("projectseele-local-maps/eva_combat_capture_r31"+(variant>=3?(variant==3?"_un00":"_un01"):"")+".json");
                if(Files.isRegularFile(capture))combatClips.put(variant,readCombatClipsR31(JsonParser.parseString(Files.readString(capture)).getAsJsonObject(),names));
            }
            data=new Data(names,index,Map.copyOf(clips),Map.copyOf(rigs),Map.copyOf(support),object(all,"prone"),object(all,"grip"),object(all,"rifle_mocap"),Map.copyOf(eyes),Map.copyOf(rigSupport),Map.copyOf(carrierHulls),Map.copyOf(combatClips));
            ProjectSeele.LOGGER.info("EVA shared body/socket pose loaded: private={} clips={} bones={}",Files.isRegularFile(path),clips.size(),names.length);
        }
        catch(Exception failure){throw new IllegalStateException("Shared EVA body pose could not load",failure);}
    }
    private static JsonObject object(JsonObject p,String n){return p.has(n)?p.getAsJsonObject(n):new JsonObject();}
    private static Map<String,Clip> readCombatClipsR31(JsonObject capture,String[] names)
    {
        var order=capture.getAsJsonArray("bones");if(order.size()!=names.length)throw new IllegalArgumentException("R31 capture bone count");
        for(int i=0;i<names.length;i++)if(!order.get(i).getAsString().equals(names[i]))throw new IllegalArgumentException("R31 capture bone order");
        Map<String,Clip> result=new HashMap<>();
        for(var entry:capture.getAsJsonObject("clips").entrySet())
        {
            var clip=entry.getValue().getAsJsonObject();var frames=clip.getAsJsonArray("frames");var rotations=new Quaternionf[frames.size()][names.length];var positions=new Vector3f[frames.size()][names.length];
            for(int f=0;f<frames.size();f++)
            {
                var frame=frames.get(f).getAsJsonObject();var q=frame.getAsJsonArray("rotation_wxyz");
                for(int b=0;b<names.length;b++)
                {
                    var value=q.get(b).getAsJsonArray();rotations[f][b]=new Quaternionf(-value.get(1).getAsFloat(),-value.get(2).getAsFloat(),value.get(3).getAsFloat(),value.get(0).getAsFloat()).normalize();
                    var p=names[b].equals("root")?vector(frame.get("root_m")).mul(112):frame.has("bone_position_xyz")&&frame.getAsJsonObject("bone_position_xyz").has(names[b])?vector(frame.getAsJsonObject("bone_position_xyz").get(names[b])):new Vector3f();
                    positions[f][b]=p.mul(-1,1,1).div(16);
                }
            }
            result.put(entry.getKey(),new Clip(clip.get("duration_seconds").getAsFloat(),rotations,positions));
        }
        return Map.copyOf(result);
    }
    public static boolean combatCaptureReadyR31(EvaUnit01Entity e,String clip)
    {if(data==null)reload();return data.combatClips().getOrDefault(rigKey(e),Map.of()).containsKey(clip);}
    public static List<net.minecraft.world.phys.AABB> carrierHulls(EvaUnit01Entity eva)
    {if(data==null)reload();return data.carrierHulls().getOrDefault(rigKey(eva),List.of());}
    private static Vector3f vector(JsonElement e){var a=e.getAsJsonArray();return new Vector3f(a.get(0).getAsFloat(),a.get(1).getAsFloat(),a.get(2).getAsFloat());}
    private static Vector3f first(JsonElement e)
    {
        if(e.isJsonObject())e=e.getAsJsonObject().entrySet().stream().min(Comparator.comparingDouble(p->Double.parseDouble(p.getKey()))).orElseThrow().getValue();
        return vector(e);
    }
    private static Sample clip(Data d,int variant,String name,float phase)
    {
        var c=d.combatClips().getOrDefault(variant,Map.of()).getOrDefault(name,d.clips().get(name));var result=new Sample(d.rigs().get(variant));float f=Mth.clamp(phase,0,1)*(c.rotations().length-1);int a=(int)f,b=Math.min(a+1,c.rotations().length-1);
        for(int i=0;i<d.names().length;i++){result.rotations.put(d.names()[i],new Quaternionf(c.rotations()[a][i]).slerp(c.rotations()[b][i],f-a));result.positions.put(d.names()[i],new Vector3f(c.positions()[a][i]).lerp(c.positions()[b][i],f-a));}
        for(var bone:result.rig.values())if(bone.name().contains("_axis_"))result.rotations.put(bone.name(),new Quaternionf(bone.bindRotation()));
        return result;
    }
    private static Sample mix(Sample a,Sample b,float amount)
    {
        for(String n:a.rig.keySet()){a.rotations.get(n).slerp(b.rotations.get(n),amount);a.positions.get(n).lerp(b.positions.get(n),amount);}a.dirty();return a;
    }
    private static Quaternionf mocap(Data d,String name,float phase)
    {
        if(!d.mocap().has("clips"))return new Quaternionf().rotationXYZ(-.20F,-.25F,0);
        var frames=d.mocap().getAsJsonObject("clips").getAsJsonObject(name).getAsJsonArray("frames");float at=phase*(frames.size()-1);int a=(int)at,b=Math.min(a+1,frames.size()-1);Quaternionf[] out=new Quaternionf[2];
        for(int j=0;j<2;j++)
        {
            var x=frames.get(a).getAsJsonArray().get(j).getAsJsonArray();var y=frames.get(b).getAsJsonArray().get(j).getAsJsonArray();out[j]=new Quaternionf(x.get(1).getAsFloat(),x.get(2).getAsFloat(),x.get(3).getAsFloat(),x.get(0).getAsFloat()).slerp(new Quaternionf(y.get(1).getAsFloat(),y.get(2).getAsFloat(),y.get(3).getAsFloat(),y.get(0).getAsFloat()),at-a);
        }
        return out[0].mul(out[1]);
    }
    public static boolean hasSupportedStances(){if(data==null)reload();return data.clips().containsKey("rifle_stance");}
    public static boolean hasTerrainStances(){if(data==null)reload();return data.clips().containsKey("unarmed_stance");}
    public static Vector3f eyePoint(int variant){if(data==null)reload();return new Vector3f(data.eyes().get(variant));}
    public static int rigKey(EvaUnit01Entity eva)
    {if(data==null)reload();int candidate=eva instanceof EvaPrototypeEntity un?3+un.getUNSerial():eva.getUnitVariant();return data.rigs().containsKey(candidate)?candidate:eva.getUnitVariant();}
    public static boolean hasOwnUnRig(EvaUnit01Entity eva){return eva.isExperimentalUnit()&&rigKey(eva)>=3;}
    public static Vector3f eyePoint(EvaUnit01Entity eva){return eva instanceof EvaPrototypeEntity un?EvaUNOptics.lens(un):eyePoint(eva.getUnitVariant());}
    public static net.minecraft.world.phys.Vec3 opticalEye(EvaUnit01Entity eva,float partial)
    {
        var body=sample(eva,partial);if(!EvaAirTransportR31.active(eva)&&!EvaShutdownR30.displayed(eva))body.rotations.get("head").rotateY((float)Math.toRadians(-eva.pilotHeadYawForRender(partial))).rotateX((float)Math.toRadians(-eva.pilotHeadPitchForRender(partial)));body.dirty();
        var p=new Matrix4f(EvaRifleKinematics.world(eva,partial)).mul(body.matrix("head")).transformPosition(eyePoint(eva));return new net.minecraft.world.phys.Vec3(p.x,p.y,p.z);
    }
    public static Sample sample(EvaUnit01Entity entity,float partial)
    {
        if(data==null)reload();Data d=data;int variant=rigKey(entity);float phase=entity.rifleGaitPhase(partial);phase-=Mth.floor(phase);
        if(EvaAirTransportR31.active(entity))return EvaAirTransportR31.sample(entity,new Sample(d.rigs().get(variant)),partial);
        if(EvaShutdownR30.displayed(entity)&&!EvaShutdownR30.pose(entity).isEmpty())
        {
            var frozen=new Sample(d.rigs().get(variant));EvaShutdownR30.decode(EvaShutdownR30.pose(entity),frozen);
            float blend=EvaShutdownR30.collapse(entity,partial);
            if(blend<1&&!EvaShutdownR30.origin(entity).isEmpty()){var old=new Sample(d.rigs().get(variant));EvaShutdownR30.decode(EvaShutdownR30.origin(entity),old);return mix(old,frozen,blend);}
            return frozen;
        }
        float time=((entity.level().getGameTime()%24000)+partial)/20;float idlePhase=(time/2.5F)%1;
        float move=entity.rifleMoveBlend(partial),run=entity.rifleRunBlend(partial),crouch=entity.rifleCrouchBlend(partial),prone=entity.rifleProneBlend(partial);prone=prone*prone*prone*(10+prone*(-15+6*prone));
        var gait=mix(clip(d,variant,"walk",phase),clip(d,variant,"run",phase),run);
        boolean supported=d.clips().containsKey("rifle_stance");float stance=entity.rifleStanceLevel(partial);
        Sample body;
        if(supported)
        {
            boolean armed=entity.getWeapon()==EvaUnit01Entity.WEAPON_RIFLE;
            body=clip(d,variant,!armed&&d.clips().containsKey("unarmed_stance")?"unarmed_stance":"rifle_stance",stance/3);
            if(stance<.001F)body=mix(clip(d,variant,"idle",idlePhase),body,move);
            float supportWeight=Mth.clamp((stance-1)/.5F,0,1);
            supportWeight=supportWeight*supportWeight*(3-2*supportWeight);
            float mobility=move*(1-supportWeight);
            if(mobility>0)body=mix(body,mix(gait,clip(d,variant,"crouch_walk",phase),Math.min(1,stance)),mobility);
            if(stance>2.5F&&move>0&&d.clips().containsKey("prone_crawl"))
            {
                float t=Mth.clamp((stance-2.5F)*2,0,1);t=t*t*(3-2*t);
                body=mix(body,clip(d,variant,"prone_crawl",phase),move*t);
            }
        }
        else
        {
            var standing=mix(clip(d,variant,"idle",idlePhase),gait,move);
            var low=mix(clip(d,variant,"crouch_idle",idlePhase),clip(d,variant,"crouch_walk",phase),move);
            body=mix(standing,low,crouch);
            if(move<.05F&&crouch>.001F&&crouch<.999F)body=clip(d,variant,"stand_to_crouch",crouch);
        }
        var bareChest=new Quaternionf(body.rotations.get("torso_lower")).mul(body.rotations.get("torso_upper"));
        var chest=new Quaternionf(bareChest);if(!supported)chest.rotateY(-.22F);
        var captured=mocap(d,"idle",(time/4)%1).slerp(mocap(d,"walk",phase).slerp(mocap(d,"run",phase),run),move);
        captured.slerp(chest,supported?Math.min(1,stance):crouch);
        float ready=entity.rifleReadyBlend(partial);ready=ready*ready*(3-2*ready);
        captured=bareChest.slerp(captured,ready);
        body.rotations.put("torso_upper",new Quaternionf(body.rotations.get("torso_lower")).invert().mul(captured));body.dirty();
        if(!supported&&prone>0&&!d.prone().entrySet().isEmpty())
        {
            var lying=new Sample(body.rig);
            for(var e:d.prone().entrySet())
            {
                if(!lying.rig.containsKey(e.getKey()))continue;var channels=e.getValue().getAsJsonObject();
                if(channels.has("rotation")){var v=first(channels.get("rotation")).mul(Mth.DEG_TO_RAD);lying.rotations.put(e.getKey(),new Quaternionf().rotationZYX(v.z,-v.y,-v.x));}
                if(channels.has("position"))lying.positions.put(e.getKey(),first(channels.get("position")).mul(-1,1,1).div(16));
            }
            body=mix(body,lying,prone);
        }
        // Ground the actual body hull during stance blending, including chest support in prone.
        float floor=Float.POSITIVE_INFINITY;
        for(var e:d.rigSupport().getOrDefault(variant,d.support()).entrySet())
        {
            if(!body.rig.containsKey(e.getKey()))continue;var matrix=body.matrix(e.getKey());
            for(var v:e.getValue())floor=Math.min(floor,matrix.m01()*v.x+matrix.m11()*v.y+matrix.m21()*v.z+matrix.m31());
        }
        // Authored support clips already include the deformed ankle surfaces.
        // Applying the rigid-foot correction again would lift the prone belly.
        if(Float.isFinite(floor)&&(variant>=3||!(supported&&(stance>1.01F||move<.05F))))
        {
            body.positions.get("root").y-=floor;body.dirty();
        }
        for(var b:body.rig.values())if(b.name().contains("_axis_"))body.rotations.put(b.name(),new Quaternionf(b.bindRotation()));
        for(var e:d.grip().entrySet())if(entity.getWeapon()==EvaUnit01Entity.WEAPON_RIFLE&&e.getKey().startsWith("finger_")&&body.rig.containsKey(e.getKey()))
        {
            var c=e.getValue().getAsJsonObject();if(c.has("rotation")){var v=first(c.get("rotation")).mul(Mth.DEG_TO_RAD);body.rotations.put(e.getKey(),new Quaternionf().rotationZYX(v.z,-v.y,-v.x));}
        }
        float cervicalOffset=EvaCervicalKinematicsR25.modelOffset(entity,partial)/16F;
        if(cervicalOffset>0 && body.rig.containsKey("head"))
        {
            var bones=new HashMap<>(body.rig);var head=bones.get("head");
            bones.put("head",new Bone(head.name(),head.parent(),new Vector3f(head.pivot()).add(0,cervicalOffset,cervicalOffset),head.bindRotation()));
            var corrected=new Sample(Map.copyOf(bones));corrected.rotations.putAll(body.rotations);corrected.positions.putAll(body.positions);body=corrected;
        }
        int combat=EvaCombatR31.action(entity);float combatAge=EvaCombatR31.age(entity,partial);
        String capture=switch(combat){case EvaCombatR31.REACH,EvaCombatR31.HOLD->"r31_grapple_start";case EvaCombatR31.THROW->"r31_shoulder_throw";case EvaCombatR31.AIR_STRIKE,EvaCombatR31.AIR_SLAM,EvaCombatR31.LAND->"r31_air_downstrike";default->"";};
        if(!capture.isEmpty()&&combatCaptureReadyR31(entity,capture))
        {
            float capturePhase=switch(combat){case EvaCombatR31.HOLD->.47F;case EvaCombatR31.REACH->.47F*combatAge/18;case EvaCombatR31.THROW->combatAge/26;case EvaCombatR31.LAND->.7F+combatAge/40;default->combatAge/28;};
            float w=(float)CombatMotionR29.ease(combatAge/5);if(combat==EvaCombatR31.HOLD)w=1;
            if(combat==EvaCombatR31.THROW)w*=1-(float)CombatMotionR29.ease((combatAge-21)/5);
            body=mix(body,clip(d,variant,capture,capturePhase),w);
            preserveJointCentres(body);
        }
        EvaTerrainSupport.apply(entity,body);EvaImpactResponse.applyBody(body,entity,partial);body.dirty();
        var beat=CombatFeelR31.beat(entity);
        if(beat!=null&&(beat.kind()==CombatFeelR31.DOWN||beat.kind()==CombatFeelR31.THROWN))
        {
            float age=CombatFeelR31.age(entity,partial);
            if(EvaRecoveryPoseR31.ready(entity))body=EvaRecoveryPoseR31.apply(entity,body,inactivePoseR30(entity,true),age,beat.duration(),beat.kind()==CombatFeelR31.THROWN&&!entity.onGround());
            else
            {
                float w=(float)CombatMotionR29.ease(age/12)*(1-(float)CombatMotionR29.ease((age-beat.duration()+18)/18));
                body=mix(body,inactivePoseR30(entity,true),w);
            }
        }
        return body;
    }

    public static Sample inactivePoseR30(EvaUnit01Entity entity,boolean prone)
    {
        if(data==null)reload();var d=data;String clip=d.clips.containsKey("unarmed_stance")?"unarmed_stance":"rifle_stance";
        var result=clip(d,rigKey(entity),prone?"idle":clip,prone?0:1F/3F);
        if(prone)
        {
            // A disabled humanoid relaxes onto its back. Reusing a live rifle
            // prone pose left the arms aiming and compressed the new UN knees.
            result.rotations.get("root").rotationXYZ((float)Math.PI/2,0,.10F);
            result.rotations.get("torso_lower").rotationXYZ(-.10F,0,0);
            result.rotations.get("torso_upper").rotationXYZ(.10F,-.12F,0);
            result.rotations.get("head").rotationXYZ(.08F,.30F,-.10F);
            for(String side:List.of("l","r"))
            {
                boolean left=side.equals("l");result.rotations.get("leg_"+side).rotationXYZ(left?.24F:.12F,0,left?-.12F:.12F);
                result.rotations.get("shin_"+side).rotationXYZ(left?-.60F:-.32F,0,0);
                result.rotations.get("arm_"+side).rotationXYZ(.18F,0,left?-.32F:.27F);
                result.rotations.get("forearm_"+side).rotationXYZ(left?.48F:.68F,0,0);
            }
        }
        else result.rotations.get("head").rotateX(.25F);
        preserveJointCentres(result);
        result.dirty();
        if(prone||hasOwnUnRig(entity))
        {
            float floor=Float.POSITIVE_INFINITY;for(var entry:d.rigSupport().getOrDefault(rigKey(entity),d.support()).entrySet())
            {if(!result.rig.containsKey(entry.getKey()))continue;var matrix=result.matrix(entry.getKey());for(var v:entry.getValue())floor=Math.min(floor,matrix.m01()*v.x+matrix.m11()*v.y+matrix.m21()*v.z+matrix.m31());}
            if(Float.isFinite(floor))result.positions.get("root").y-=floor;
        }
        result.dirty();return result;
    }

    /** Recompute the offset from the composed rotation, never blend the two independently. */
    public static void preserveJointCentres(Sample pose)
    {
        for(String side:List.of("l","r"))for(String family:List.of("shin_","forearm_"))
        {
            String name=family+side;if(!pose.rig.containsKey(name))continue;
            String marker=(family.equals("shin_")?"r30_knee_socket_":"r30_elbow_socket_")+side;
            Vector3f centre=pose.rig.containsKey(marker)?new Vector3f(pose.rig.get(marker).pivot())
                    :family.equals("shin_")?new Vector3f(pose.rig.get(name).pivot()).add(0,11.4F/16,0)
                    :new Vector3f(side.equals("l")?-23.489652F:23.489652F,123.435069F,7.737214F).div(16);
            Vector3f delta=centre.sub(pose.rig.get(name).pivot());
            pose.positions.put(name,new Vector3f(delta).sub(pose.rotations.get(name).transform(new Vector3f(delta))));
        }
        pose.dirty();
    }
}
