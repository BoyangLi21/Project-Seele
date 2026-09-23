package com.projectseele.client.visual;

import com.google.gson.*;
import com.projectseele.client.Keybinds;
import com.projectseele.entity.*;
import com.projectseele.network.*;
import com.projectseele.visual.MechanicsR31Review;
import com.projectseele.world.EntryPlugKinematics;
import net.minecraft.client.*;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.*;
import java.nio.file.*;
import java.util.*;

/** Actual submitted bone matrices and capsule draw transform, not a planned pose proxy. */
@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class MechanicsR31Client
{
    private record Bone(float x,float y,float z,float px,float py,float pz,float sx,float sy,float sz) {}
    private static final Map<Integer,Map<String,Bone>> BASE=new HashMap<>();
    private static final Map<Integer,Integer> LAST_REVISION=new HashMap<>();
    private static final Map<String,Map<String,Float>> DORMANT_X=new HashMap<>();
    private static final Set<String> PHOTOS=new HashSet<>();
    private static final JsonArray boneFrames=new JsonArray(),plugFrames=new JsonArray(),socketFrames=new JsonArray(),inputFrames=new JsonArray(),photoFrames=new JsonArray(),aircraftFrames=new JsonArray(),cradleFrames=new JsonArray(),headFrames=new JsonArray();
    private static final Set<String> BODY=Set.of("root","torso_lower","torso_upper","head","arm_l","arm_r","forearm_l","forearm_r","wrist_l","wrist_r","hand_l","hand_r","leg_l","leg_r","shin_l","shin_r","ankle_l","ankle_r","foot_l","foot_r");
    private static boolean started,oldPause,oldGui;private static int oldDistance,oldFov,end,epoch;private static CameraType oldCamera;
    private static Path folder;private static long frameCount,firstFrame,lastFrame;private static double maxPlugDrawError,maxSocketError;
    private static net.minecraft.world.entity.Entity transportCamera;
    private static long renderSerial,evaDrawSerial=-1,aircraftDrawSerial=-1,cradleDrawSerial=-1,headDrawSerial=-1;
    private static boolean transportCameraReady;
    private static Vec3 lastAircraftDrawOrigin=Vec3.ZERO,lastEvaDrawPoint=Vec3.ZERO;
    private static Vec3 lastCradleDrawPoint=Vec3.ZERO,lastHeadForward=Vec3.ZERO;
    private static int lastCradleTriangles,lastCradleRods;
    private static int serial(java.util.UUID id){for(int i=0;i<2;i++)if(id.equals(MechanicsR31Review.unitIds[i]))return i;return -1;}
    private static int plugSerial(java.util.UUID id){for(int i=0;i<2;i++)if(id.equals(MechanicsR31Review.plugIds[i]))return i;return -1;}
    private static JsonArray vector(Vec3 p){var a=new JsonArray();a.add(p.x);a.add(p.y);a.add(p.z);return a;}
    private static void fail(String why){MechanicsR31Review.clientError=why;MechanicsR31Review.clientFailed=true;}
    private static Map<String,Float> dormantX(EvaPrototypeEntity eva)
    {
        return DORMANT_X.computeIfAbsent(eva.experimentalAssetName(),asset->{
            Map<String,Float> result=new HashMap<>();
            var location=new net.minecraft.resources.ResourceLocation("projectseele","animations/"+asset+".animation.json");
            try(var reader=Minecraft.getInstance().getResourceManager().getResource(location).orElseThrow().openAsReader())
            {
                var bones=JsonParser.parseReader(reader).getAsJsonObject().getAsJsonObject("animations").getAsJsonObject("animation.eva_unit01.dormant").getAsJsonObject("bones");
                for(String name:List.of("torso_upper","head")){var r=bones.getAsJsonObject(name).getAsJsonArray("rotation");result.put(name,(float)Math.toRadians(-r.get(0).getAsFloat()));}
            }
            catch(Exception e){fail("Cannot verify authored dormant transition: "+e);}
            return Map.copyOf(result);
        });
    }

    /** Call at the final pose-graph commit, after shutdown/air-transport overlays. */
    public static void captureBones(EvaUnit01Entity entity,BakedGeoModel model,float partial,Matrix4f modelToWorld)
    {
        if(!MechanicsR31Review.ENABLED||MechanicsR31Review.done||!(entity instanceof EvaPrototypeEntity eva))return;
        int serial=serial(eva.getUUID());if(serial<0||serial!=MechanicsR31Review.serial)return;
        MechanicsR31Review.modelFrames.incrementAndGet(serial);
        Map<String,Bone> pose=new LinkedHashMap<>();Set<String> names=new LinkedHashSet<>(BODY);names.addAll(List.of("r30_thruster_l","r30_thruster_r","finger_index_r","finger_thumb_r","finger_index_l","finger_thumb_l"));
        for(String name:names)model.getBone(name).ifPresent(b->pose.put(name,new Bone(b.getRotX(),b.getRotY(),b.getRotZ(),b.getPosX(),b.getPosY(),b.getPosZ(),b.getScaleX(),b.getScaleY(),b.getScaleZ())));
        int revision=eva.mechanicalRevisionR30();Integer prior=LAST_REVISION.put(serial,revision);boolean edge=prior==null||prior!=revision;
        boolean baseline=MechanicsR31Review.stageName.equals("base_reset")&&revision==MechanicsR31Review.baseRevision[serial];
        boolean reset=Set.of("dirty_reset","verify_reset").contains(MechanicsR31Review.stageName)&&revision==MechanicsR31Review.resetRevision[serial];
        if(baseline){BASE.put(serial,pose);MechanicsR31Review.baselineFrames.incrementAndGet(serial);}
        double rotation=0,checkedRotation=0,position=0,scale=0;int resetFrame=0;var base=BASE.get(serial);
        if(reset&&base!=null)
        {
            resetFrame=MechanicsR31Review.resetFrames.incrementAndGet(serial);
            for(var e:pose.entrySet())
            {
                Bone b=e.getValue(),a=base.get(e.getKey());if(a==null)continue;
                rotation=Math.max(rotation,Math.max(Math.abs(a.x-b.x),Math.max(Math.abs(a.y-b.y),Math.abs(a.z-b.z))));
                double dx=Math.abs(a.x-b.x);Float authored=dormantX(eva).get(e.getKey());
                if(resetFrame<=8&&authored!=null)
                {
                    float bind=model.getBone(e.getKey()).orElseThrow().getInitialSnapshot().getRotX(),target=bind+authored;
                    // Cold baseline and dirty reset both begin at bind, then
                    // Gecko enters the authored 2/6-degree dormant nod. Only
                    // these measured channels may follow that closed segment.
                    if(Math.abs(a.x-target)<.0001F&&b.x>=Math.min(bind,target)-.0001F&&b.x<=Math.max(bind,target)+.0001F)dx=0;
                }
                checkedRotation=Math.max(checkedRotation,Math.max(dx,Math.max(Math.abs(a.y-b.y),Math.abs(a.z-b.z))));
                position=Math.max(position,Math.max(Math.abs(a.px-b.px),Math.max(Math.abs(a.py-b.py),Math.abs(a.pz-b.pz))));
                scale=Math.max(scale,Math.max(Math.abs(a.sx-b.sx),Math.max(Math.abs(a.sy-b.sy),Math.abs(a.sz-b.sz))));
            }
            if(checkedRotation>.05||position>.3||scale>.002)fail("UN"+serial+" reset frame="+resetFrame+" checked_angle="+checkedRotation+" raw_angle="+rotation+" position="+position+" scale="+scale);
        }
        if(eva.getUNSerial()!=serial||EvaBodyPose.rigKey(eva)!=3+serial)fail("Original UN UUID rendered with wrong serial/rig: "+serial);
        if(edge||baseline&&MechanicsR31Review.baselineFrames.get(serial)<=12||reset&&MechanicsR31Review.resetFrames.get(serial)<=12)
        {
            var r=new JsonObject();r.addProperty("serial",serial);r.addProperty("revision",revision);r.addProperty("first_frame_of_revision",edge);r.addProperty("stage",MechanicsR31Review.stageName);r.addProperty("rotation_delta_rad",rotation);r.addProperty("offset_delta_model_units",position);r.addProperty("bone_scale_delta",scale);r.add("bones",new Gson().toJsonTree(pose));
            r.addProperty("checked_rotation_delta_rad",checkedRotation);r.addProperty("authored_dormant_intro_window",reset&&resetFrame<=8);
            if(modelToWorld!=null){var s=modelToWorld.getScale(new Vector3f());r.add("submitted_model_scale",vector(new Vec3(s)));if(Math.abs(s.y-EvaScale.RENDER_SCALE)>.01)fail("UN rendered at unexpected scale: "+s);}
            boneFrames.add(r);
        }
    }

    /** Call on the visible entry_plug mesh part using its actual draw matrix. */
    public static void capturePlug(EntryPlugCarrierEntity plug,Matrix4f drawWorld,float partial)
    {
        if(!MechanicsR31Review.ENABLED||MechanicsR31Review.done)return;int serial=plugSerial(plug.getUUID());if(serial<0)return;
        var rendered=plug.getInterpolatedCanonicalTransform(partial);Vec3 actual=new Vec3(drawWorld.transformPosition(new Vector3f()));double error=actual.distanceTo(rendered.translation());
        maxPlugDrawError=Math.max(maxPlugDrawError,error);MechanicsR31Review.visiblePlugFrames.incrementAndGet(serial);
        var scale=drawWorld.getScale(new Vector3f());Quaternionf q=drawWorld.getUnnormalizedRotation(new Quaternionf()).normalize();float dot=Math.abs(q.dot(rendered.rotation()));double rotation=Math.toDegrees(2*Math.acos(Math.max(-1,Math.min(1,dot))));
        if(error>.05||rotation>.25||Math.abs(scale.y-EvaScale.ENTRY_PLUG_RENDER_SCALE)>.01)fail("Original capsule draw diverged: serial="+serial+" translation="+error+" rotation="+rotation+" scale="+scale);
        if(plugFrames.size()<1000&&(MechanicsR31Review.visiblePlugFrames.get(serial)<15||plug.tickCount%20==0))
        {
            var r=new JsonObject();r.addProperty("serial",serial);r.addProperty("stage",MechanicsR31Review.stageName);r.addProperty("draw_error",error);r.addProperty("rotation_error_deg",rotation);r.add("actual_draw_origin",vector(actual));r.add("render_pose",vector(rendered.translation()));r.add("canonical_pose",vector(plug.getCanonicalTransform().translation()));plugFrames.add(r);
        }
    }

    /** Actual torso_upper mesh frame locates the dorsal port during cradle rotation. */
    public static void captureSocket(EvaUnit01Entity entity,Matrix4f torsoWorld,float partial)
    {
        if(!MechanicsR31Review.ENABLED||MechanicsR31Review.done||!(entity instanceof EvaPrototypeEntity eva))return;
        int serial=serial(eva.getUUID());if(serial<0)return;var mc=Minecraft.getInstance();if(mc.level==null)return;
        var profile=EvaDorsalProfile.of(eva);var c=profile.centreModel();var o=profile.outwardModel();
        Vector3f centre=torsoWorld.transformPosition(new Vector3f((float)-c.x,(float)c.y,(float)c.z).div(16));
        lastEvaDrawPoint=new Vec3(centre);if(serial==0&&transportCameraReady&&inCamera(lastEvaDrawPoint))evaDrawSerial=renderSerial;
        if(!EvaAirTransportR31.active(eva))return;
        EntryPlugCarrierEntity plug=null;for(var e:mc.level.entitiesForRendering())if(e instanceof EntryPlugCarrierEntity p&&p.getUUID().equals(MechanicsR31Review.plugIds[serial])){plug=p;break;}if(plug==null||!plug.isLockedToEva()||plug.getLinkedEva()!=eva)return;
        Vector3f axis=torsoWorld.transformDirection(new Vector3f((float)-o.x,(float)o.y,(float)o.z)).normalize();Vec3 tip=new Vec3(centre).subtract(new Vec3(axis).scale(EntryPlugKinematics.LOCK_DEPTH_BLOCKS));
        Vec3 actual=plug.getInterpolatedCanonicalTransform(partial).translation();double error=actual.distanceTo(tip);maxSocketError=Math.max(maxSocketError,error);
        float pitch=EvaAirTransportR31.pitch(eva,partial);MechanicsR31Review.transportSamples.incrementAndGet(0);
        if(pitch>38&&pitch<52)MechanicsR31Review.transportSamples.incrementAndGet(1);if(pitch>89)MechanicsR31Review.transportSamples.incrementAndGet(2);
        MechanicsR31Review.maximumTransportSocketError=Math.max(MechanicsR31Review.maximumTransportSocketError,error);
        if(!Double.isFinite(error)||error>MechanicsR31Review.SOCKET_ERROR_LIMIT)fail("Actual UN mesh/capsule transport mismatch: "+error+" m, pitch="+pitch+", render="+renderSerial);
        if(socketFrames.size()<1800&&(pitch>38&&pitch<52||pitch>89||renderSerial%8==0)){var r=new JsonObject();r.addProperty("serial",serial);r.addProperty("render_frame",renderSerial);r.addProperty("pitch",pitch);r.addProperty("actual_mesh_to_capsule_error",Double.isFinite(error)?error:-1);r.add("actual_mesh_locked_tip",vector(tip));r.add("capsule_render_tip",vector(actual));socketFrames.add(r);}
    }
    /** Called after the real aircraft body draw, with the submitted world matrix. */
    public static void captureAircraft(UNTransportEntity plane,Matrix4f actualDrawWorld,float partial)
    {
        if(!MechanicsR31Review.ENABLED||MechanicsR31Review.done||plane.groundCart()||plane.serial()!=0||plane.cargoEntityId()!=MechanicsR31Review.actorId)return;
        lastAircraftDrawOrigin=new Vec3(actualDrawWorld.transformPosition(new Vector3f()));
        if(transportCameraReady&&inCamera(lastAircraftDrawOrigin))aircraftDrawSerial=renderSerial;
        if(aircraftFrames.size()<1800)
        {
            var r=aircraftState(plane,partial);r.add("actual_draw_origin",vector(lastAircraftDrawOrigin));r.addProperty("in_camera",transportCameraReady&&inCamera(lastAircraftDrawOrigin));aircraftFrames.add(r);
        }
    }
    private static JsonObject aircraftState(UNTransportEntity plane,float partial)
    {
        var r=new JsonObject();r.addProperty("render_frame",renderSerial);r.addProperty("aircraft_id",plane.getId());r.addProperty("aircraft_uuid",plane.getUUID().toString());r.addProperty("tick_count",plane.tickCount);
        r.addProperty("target_deployment",plane.targetDeployment());r.addProperty("render_rig",plane.rig(partial));r.addProperty("render_jaws",plane.jaws(partial));r.addProperty("carrying",plane.carrying());r.addProperty("cargo_entity_id",plane.cargoEntityId());r.addProperty("cargo_resolved",plane.level().getEntity(plane.cargoEntityId()) instanceof EvaUnit01Entity);return r;
    }
    /** Counts only support geometry whose nondegenerate vertices were submitted this frame. */
    public static void captureCradle(UNTransportEntity plane,Matrix4f actualDrawWorld,float partial,int triangles,int rods)
    {
        if(!MechanicsR31Review.ENABLED||MechanicsR31Review.done||plane.groundCart()||plane.serial()!=0||plane.cargoEntityId()!=MechanicsR31Review.actorId)return;
        lastCradleDrawPoint=new Vec3(actualDrawWorld.transformPosition(new Vector3f(0,EvaAirTransportR31.HIP_HEIGHT,0)));lastCradleTriangles=triangles;lastCradleRods=rods;
        boolean submitted=triangles>0&&rods==8,visible=transportCameraReady&&inCamera(lastCradleDrawPoint);
        if(submitted){MechanicsR31Review.cradleSamples.incrementAndGet(0);if(visible)cradleDrawSerial=renderSerial;}
        if(cradleFrames.size()<1800)
        {
            var r=aircraftState(plane,partial);r.addProperty("submitted_nondegenerate_triangles",triangles);r.addProperty("submitted_rod_segments",rods);r.addProperty("in_camera",visible);r.add("actual_cradle_midpoint",vector(lastCradleDrawPoint));var values=new JsonArray();for(float value:actualDrawWorld.get(new float[16]))values.add(value);r.add("actual_draw_world_matrix",values);cradleFrames.add(r);
        }
    }
    /** Model front is -Z; the actual head draw must face world -Y when horizontally stowed. */
    public static void captureHeadFacing(EvaUnit01Entity entity,Matrix4f actualHeadWorld,float partial)
    {
        if(!MechanicsR31Review.ENABLED||MechanicsR31Review.done||!(entity instanceof EvaPrototypeEntity eva)||serial(eva.getUUID())!=0||!EvaAirTransportR31.active(eva))return;
        Vector3f direction=actualHeadWorld.transformDirection(new Vector3f(0,0,-1)).normalize();
        if(!Float.isFinite(direction.x)||!Float.isFinite(direction.y)||!Float.isFinite(direction.z)){fail("Non-finite actual head forward matrix");return;}
        lastHeadForward=new Vec3(direction);headDrawSerial=renderSerial;
        float pitch=EvaAirTransportR31.pitch(eva,partial);
        if(pitch>89)
        {
            MechanicsR31Review.headFacingSamples.incrementAndGet(0);MechanicsR31Review.maximumHeadForwardY=Math.max(MechanicsR31Review.maximumHeadForwardY,direction.y);
            if(!Float.isFinite(direction.y)||direction.y>=-.9F)fail("Horizontal payload head is not facing the ground: actual forward="+lastHeadForward+", pitch="+pitch);
        }
        if(headFrames.size()<1800&&(pitch>89||renderSerial%8==0)){var r=new JsonObject();r.addProperty("render_frame",renderSerial);r.addProperty("signal_pitch",pitch);r.add("actual_head_front_world",vector(lastHeadForward));headFrames.add(r);}
    }
    private static boolean inCamera(Vec3 point)
    {
        var mc=Minecraft.getInstance();var camera=mc.gameRenderer.getMainCamera();Vec3 delta=point.subtract(camera.getPosition()),forward=new Vec3(camera.getLookVector());
        double depth=delta.dot(forward);if(depth<=0)return false;Vec3 right=forward.cross(new Vec3(0,1,0)).normalize(),up=right.cross(forward).normalize();
        double tangent=Math.tan(Math.toRadians(mc.options.fov().get())*.5),aspect=mc.getWindow().getWidth()/(double)Math.max(1,mc.getWindow().getHeight());
        return Math.abs(delta.dot(up))<depth*tangent*.92&&Math.abs(delta.dot(right))<depth*tangent*aspect*.92;
    }
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!MechanicsR31Review.ENABLED||event.phase!=TickEvent.Phase.END)return;var mc=Minecraft.getInstance();if(mc.player==null||mc.level==null)return;
        if(!started)
        {
            var server=mc.getSingleplayerServer();if(server==null||!server.getWorldPath(LevelResource.ROOT).normalize().getFileName().toString().equals(MechanicsR31Review.WORLD))throw new IllegalStateException("Mechanical fixture world boundary");
            started=true;oldPause=mc.options.pauseOnLostFocus;oldGui=mc.options.hideGui;oldDistance=mc.options.renderDistance().get();oldFov=mc.options.fov().get();oldCamera=mc.options.getCameraType();mc.options.pauseOnLostFocus=false;mc.options.renderDistance().set(8);mc.options.broadcastOptions();mc.options.setCameraType(CameraType.FIRST_PERSON);
            folder=mc.gameDirectory.toPath().resolve("../artifacts/facility_r31/native_mechanics_"+System.currentTimeMillis()).normalize();try{Files.createDirectories(folder);}catch(Exception e){throw new IllegalStateException(e);}MechanicsR31Review.mediaFolder=folder.toString();MechanicsR31Review.ready=true;
        }
        if(mc.screen!=null)mc.setScreen(null);
        if(MechanicsR31Review.inputEpoch!=epoch)
        {
            epoch=MechanicsR31Review.inputEpoch;int input=MechanicsR31Review.inputAction;
            if(input==1||input==2)SeeleNetwork.CHANNEL.sendToServer(new ServerboundEvaControlPacket(input==1?ServerboundEvaControlPacket.ACTION_CROUCH_START:ServerboundEvaControlPacket.ACTION_CROUCH_STOP));
            if(input==3){SeeleNetwork.CHANNEL.sendToServer(new ServerboundEvaControlPacket(ServerboundEvaControlPacket.ACTION_CROUCH_STOP));SeeleNetwork.CHANNEL.sendToServer(new ServerboundEvaControlPacket(ServerboundEvaControlPacket.ACTION_TOGGLE_PRONE));}
            if(input==4)KeyMapping.click(mc.options.keyAttack.getKey());
            var r=new JsonObject();r.addProperty("epoch",epoch);r.addProperty("input",input);r.addProperty("stage",MechanicsR31Review.stageName);inputFrames.add(r);
        }
        boolean piloting=mc.player.getRootVehicle() instanceof EvaPrototypeEntity;
        mc.options.hideGui=!mc.player.isPassenger();mc.options.setCameraType(piloting?CameraType.THIRD_PERSON_BACK:CameraType.FIRST_PERSON);
        if(MechanicsR31Review.stageName.equals("transport")){if(mc.options.renderDistance().get()!=12){mc.options.renderDistance().set(12);mc.options.broadcastOptions();}mc.options.fov().set(84);}
        if(mc.player.isPassenger()){mc.player.setYRot(0);mc.player.setXRot(MechanicsR31Review.lookPitch);}
        if(MechanicsR31Review.done&&++end>30)
        {
            try
            {
                var r=new JsonObject();r.add("bone_frames",boneFrames);r.add("capsule_draw_frames",plugFrames);r.add("transport_socket_frames",socketFrames);r.add("native_inputs",inputFrames);r.add("actual_draw_photo_frames",photoFrames);r.add("aircraft_draw_frames",aircraftFrames);r.add("cradle_draw_frames",cradleFrames);r.add("head_facing_frames",headFrames);r.addProperty("gate_revision",3);r.addProperty("transport_orientation","face_down");r.addProperty("scope",MechanicsR31Review.TRANSPORT_ONLY?"original_un00_transport_only":"mechanics");r.addProperty("socket_error_limit_metres",MechanicsR31Review.SOCKET_ERROR_LIMIT);r.addProperty("transport_socket_sample_count",MechanicsR31Review.transportSamples.get(0));r.addProperty("actual_cradle_draw_samples",MechanicsR31Review.cradleSamples.get(0));r.addProperty("actual_90deg_head_facing_samples",MechanicsR31Review.headFacingSamples.get(0));r.addProperty("maximum_90deg_head_forward_y",MechanicsR31Review.maximumHeadForwardY);r.addProperty("max_capsule_draw_error",maxPlugDrawError);r.addProperty("max_transport_socket_error",Double.isFinite(maxSocketError)?maxSocketError:-1);r.addProperty("actual_render_frames",frameCount);r.addProperty("average_fps",lastFrame>firstFrame?(frameCount-1)*1e9/(lastFrame-firstFrame):0);r.addProperty("client_error",MechanicsR31Review.clientError);Files.writeString(folder.resolve("render_witnesses.json"),new GsonBuilder().setPrettyPrinting().create().toJson(r));
            }
            catch(Exception e){throw new IllegalStateException(e);}
            mc.options.pauseOnLostFocus=oldPause;mc.options.hideGui=oldGui;mc.options.renderDistance().set(oldDistance);mc.options.fov().set(oldFov);mc.options.broadcastOptions();mc.options.setCameraType(oldCamera);mc.setCameraEntity(mc.player);mc.stop();
        }
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event)
    {
        if(!MechanicsR31Review.ENABLED||!started)return;var mc=Minecraft.getInstance();if(mc.player==null)return;
        if(event.phase==TickEvent.Phase.START)
        {
            renderSerial++;transportCameraReady=false;
            if(MechanicsR31Review.stageName.equals("transport")&&mc.level!=null&&mc.level.getEntity(MechanicsR31Review.actorId) instanceof EvaPrototypeEntity eva)
            {
                if(transportCamera==null){transportCamera=net.minecraft.world.entity.EntityType.ARMOR_STAND.create(mc.level);transportCamera.setInvisible(true);}
                Vec3 root=eva.carrierRenderPosition(event.renderTickTime),hip=EvaAirTransportR31.active(eva)?EvaAirTransportR31.point(eva,new Vec3(0,EvaAirTransportR31.HIP_HEIGHT,0),event.renderTickTime):root.add(0,34,0),aircraft=root.add(0,112,0);
                for(var e:mc.level.entitiesForRendering())if(e instanceof UNTransportEntity plane&&!plane.groundCart()&&plane.serial()==0&&plane.cargoEntityId()==eva.getId()){aircraft=plane.carrying()?root.add(0,plane.hoistDistance(),0):plane.getPosition(event.renderTickTime);break;}
                Vec3 target=hip.lerp(aircraft,.5),position=target.add(65,4,72),direction=target.subtract(position);
                transportCamera.setPos(position.x,position.y-transportCamera.getEyeHeight(),position.z);transportCamera.xo=transportCamera.xOld=transportCamera.getX();transportCamera.yo=transportCamera.yOld=transportCamera.getY();transportCamera.zo=transportCamera.zOld=transportCamera.getZ();
                float yaw=(float)Math.toDegrees(Math.atan2(-direction.x,direction.z)),pitch=(float)-Math.toDegrees(Math.atan2(direction.y,direction.horizontalDistance()));transportCamera.setYRot(yaw);transportCamera.yRotO=yaw;transportCamera.setYHeadRot(yaw);if(transportCamera instanceof net.minecraft.world.entity.LivingEntity living)living.yHeadRotO=yaw;transportCamera.setXRot(pitch);transportCamera.xRotO=pitch;
                mc.options.setCameraType(CameraType.FIRST_PERSON);mc.setCameraEntity(transportCamera);transportCameraReady=true;
            }
            else
            {
                mc.setCameraEntity(mc.player);
                if(MechanicsR31Review.observerTarget!=null){var d=MechanicsR31Review.observerTarget.subtract(mc.player.getEyePosition());float yaw=(float)Math.toDegrees(Math.atan2(-d.x,d.z)),pitch=(float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance()));mc.player.setYRot(yaw);mc.player.yRotO=yaw;mc.player.setXRot(pitch);mc.player.xRotO=pitch;}
            }
        }
        if(event.phase!=TickEvent.Phase.END||MechanicsR31Review.done)return;
        long now=System.nanoTime();if(frameCount++==0)firstFrame=now;lastFrame=now;
        String photo=MechanicsR31Review.photo;
        if(MechanicsR31Review.stageName.equals("transport"))
        {
            photo="";
            if(transportCameraReady&&evaDrawSerial==renderSerial&&aircraftDrawSerial==renderSerial&&cradleDrawSerial==renderSerial&&mc.level.getEntity(MechanicsR31Review.actorId) instanceof EvaPrototypeEntity eva)
            {
                float pitch=EvaAirTransportR31.pitch(eva,event.renderTickTime);
                if(MechanicsR31Review.transportPhase.equals("CLAMP")&&pitch<15)photo="horizontal_00_clamp";
                if(pitch>38&&pitch<52)photo="horizontal_01_45deg";if(pitch>89&&headDrawSerial==renderSerial&&lastHeadForward.y<-.9)photo="horizontal_02_90deg";
                if(MechanicsR31Review.transportPhase.equals("RELEASE")&&pitch<1)photo="horizontal_03_unload";
            }
        }
        if(!photo.isEmpty()&&PHOTOS.add(photo))try(var capture=net.minecraft.client.Screenshot.takeScreenshot(mc.getMainRenderTarget()))
        {
            capture.writeToFile(folder.resolve(photo+".png"));MechanicsR31Review.capturedPhotos.add(photo);
            if(photo.startsWith("horizontal_")){var r=new JsonObject();r.addProperty("photo",photo);r.addProperty("render_frame",renderSerial);r.addProperty("same_frame_eva_mesh_draw",evaDrawSerial==renderSerial);r.addProperty("same_frame_aircraft_mesh_draw",aircraftDrawSerial==renderSerial);r.addProperty("same_frame_cradle_mesh_draw",cradleDrawSerial==renderSerial);r.addProperty("submitted_cradle_triangles",lastCradleTriangles);r.addProperty("submitted_rod_segments",lastCradleRods);r.addProperty("same_frame_head_mesh_draw",headDrawSerial==renderSerial);if(headDrawSerial==renderSerial)r.add("actual_head_front_world",vector(lastHeadForward));r.add("camera",vector(mc.gameRenderer.getMainCamera().getPosition()));r.add("actual_aircraft_draw_origin",vector(lastAircraftDrawOrigin));r.add("actual_eva_mesh_point",vector(lastEvaDrawPoint));r.add("actual_cradle_midpoint",vector(lastCradleDrawPoint));photoFrames.add(r);}
        }
        catch(Exception e){throw new IllegalStateException(e);}
    }
    private MechanicsR31Client() {}
}
