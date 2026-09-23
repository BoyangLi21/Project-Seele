package com.projectseele.entity;

import net.minecraft.nbt.*;
import net.minecraft.network.syncher.*;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/** The airframe and its original capsule share this persisted rotating cradle frame. */
public final class EvaAirTransportR31
{
    private static final EntityDataAccessor<CompoundTag> FRAME = SynchedEntityData.defineId(EvaUnit01Entity.class, EntityDataSerializers.COMPOUND_TAG);
    public static final float HIP_HEIGHT = 34F;
    public static final float STOW_LIFT = 54F;
    public static boolean bootstrap() { return true; }
    public static void define(SynchedEntityData data) { data.define(FRAME, new CompoundTag()); }
    public static boolean active(EvaUnit01Entity eva) { return eva.getEntityData().get(FRAME).getBoolean("Active"); }
    public static void save(EvaUnit01Entity eva, CompoundTag tag) { tag.put("R31AirCradle", eva.getEntityData().get(FRAME).copy()); }
    public static void load(EvaUnit01Entity eva, CompoundTag tag) { eva.getEntityData().set(FRAME, tag.getCompound("R31AirCradle").copy()); }
    public static void clear(EvaUnit01Entity eva) { if (!eva.level().isClientSide){eva.getEntityData().set(FRAME, new CompoundTag());eva.getPersistentData().remove("R31AirAcceptedPitch");} }

    public static void begin(EvaUnit01Entity eva)
    {
        if (eva.level().isClientSide || active(eva)) return;
        CompoundTag origin = EvaShutdownR30.disabled(eva) && !EvaShutdownR30.pose(eva).isEmpty()
                ? EvaShutdownR30.pose(eva).copy() : EvaShutdownR30.encode(EvaBodyPose.sample(eva, 1));
        CompoundTag tag = new CompoundTag();
        tag.putBoolean("Active", true);
        tag.put("Origin", origin);
        tag.putLong("Since", eva.level().getGameTime());
        tag.putInt("Duration", 1);
        eva.getEntityData().set(FRAME, tag);
        eva.getPersistentData().putFloat("R31AirAcceptedPitch",0);
        eva.stowHandsForShutdownR30();
    }

    public static void transition(EvaUnit01Entity eva, float pitch, float restraint, int duration)
    {
        if (eva.level().isClientSide) return;
        begin(eva);
        CompoundTag tag = eva.getEntityData().get(FRAME).copy();
        boolean releasing=tag.getBoolean("Release");
        if(releasing)tag.put("Origin",EvaShutdownR30.encode(EvaBodyPose.sample(eva,0)));
        tag.remove("Release");tag.remove("ReleaseFrom");tag.remove("ReleaseTo");tag.remove("ReleaseHeld");
        tag.putFloat("FromPitch", releasing?0:pitch(eva, 0));
        tag.putFloat("FromRestraint", releasing?0:restraint(eva, 0));
        tag.putFloat("ToPitch", Mth.clamp(pitch, 0, 90));
        tag.putFloat("ToRestraint", Mth.clamp(restraint, 0, 1));
        tag.putLong("Since", eva.level().getGameTime());
        tag.putInt("Duration", Math.max(1, duration));
        eva.getEntityData().set(FRAME, tag);
    }

    private static float sample(EvaUnit01Entity eva, String channel, float partial)
    {
        CompoundTag tag = eva.getEntityData().get(FRAME);
        double t = Mth.clamp((eva.level().getGameTime() - tag.getLong("Since") + (double)partial)
                / Math.max(1, tag.getInt("Duration")), 0, 1);
        float ease = (float)(t*t*t*(t*(t*6-15)+10));
        return Mth.lerp(ease, tag.getFloat("From"+channel), tag.getFloat("To"+channel));
    }
    public static float pitch(EvaUnit01Entity eva, float partial) { return sample(eva, "Pitch", partial); }
    public static float restraint(EvaUnit01Entity eva, float partial) { return sample(eva, "Restraint", partial); }
    public static float jawOpening(EvaUnit01Entity eva,float partial)
    {
        var tag=eva.getEntityData().get(FRAME);
        if(tag.getBoolean("Release"))
            return EvaDorsalMechanism.smooth((float)((eva.level().getGameTime()-tag.getLong("Since")+(double)partial)/Math.max(1,tag.getInt("Duration"))));
        return 1-restraint(eva,partial);
    }
    public static float acceptedPitch(EvaUnit01Entity eva)
    {return eva.getPersistentData().contains("R31AirAcceptedPitch")?eva.getPersistentData().getFloat("R31AirAcceptedPitch"):pitch(eva,-1);}
    public static void acceptPitch(EvaUnit01Entity eva,float pitch)
    {if(!eva.level().isClientSide)eva.getPersistentData().putFloat("R31AirAcceptedPitch",pitch);}
    public static void holdAtPitch(EvaUnit01Entity eva,float pitch)
    {
        if(!active(eva)||eva.level().isClientSide)return;
        var tag=eva.getEntityData().get(FRAME).copy();float restraint=restraint(eva,0);
        tag.putFloat("FromPitch",pitch);tag.putFloat("ToPitch",pitch);tag.putFloat("FromRestraint",restraint);tag.putFloat("ToRestraint",restraint);tag.putInt("Duration",1);tag.putLong("Since",eva.level().getGameTime());eva.getEntityData().set(FRAME,tag);
    }
    public static void hold(EvaUnit01Entity eva)
    {
        if(!active(eva))return;
        var tag=eva.getEntityData().get(FRAME);
        if(tag.getBoolean("Release"))
        {
            if(tag.getBoolean("ReleaseHeld"))return;
            var now=EvaShutdownR30.encode(EvaBodyPose.sample(eva,0));tag=tag.copy();tag.put("ReleaseFrom",now);tag.put("ReleaseTo",now.copy());tag.putBoolean("ReleaseHeld",true);tag.putInt("Duration",1);tag.putLong("Since",eva.level().getGameTime());eva.getEntityData().set(FRAME,tag);return;
        }
        if(tag.getInt("Duration")==1&&tag.getFloat("FromPitch")==tag.getFloat("ToPitch")
                &&tag.getFloat("FromRestraint")==tag.getFloat("ToRestraint"))return;
        holdAtPitch(eva,acceptedPitch(eva));
    }
    public static void release(EvaUnit01Entity eva,int duration)
    {
        if(eva.level().isClientSide||!active(eva))return;
        var current=EvaShutdownR30.encode(EvaBodyPose.sample(eva,0));
        EvaShutdownR30.ensureUnpilotedR31(eva);
        var target=EvaShutdownR30.disabled(eva)?EvaShutdownR30.pose(eva).copy():current.copy();
        var tag=eva.getEntityData().get(FRAME).copy();tag.putBoolean("Release",true);tag.remove("ReleaseHeld");tag.put("ReleaseFrom",current);tag.put("ReleaseTo",target);tag.putInt("ReleaseMode",EvaShutdownR30.mode(eva));tag.putLong("Since",eva.level().getGameTime());tag.putInt("Duration",Math.max(1,duration));
        tag.putFloat("FromPitch",0);tag.putFloat("ToPitch",0);tag.putFloat("FromRestraint",1);tag.putFloat("ToRestraint",1);eva.getEntityData().set(FRAME,tag);
    }
    public static void refreshRelease(EvaUnit01Entity eva,int duration)
    {
        var tag=eva.getEntityData().get(FRAME);
        if(tag.getBoolean("Release")&&tag.getInt("ReleaseMode")!=EvaShutdownR30.mode(eva))release(eva,duration);
    }
    public static float lift(float pitch)
    {
        float angle=pitch*Mth.DEG_TO_RAD;
        // A reduced intermediate lift keeps the entire prone-rotation envelope
        // below the keel; the dorsal saddle reaches its recess after folding.
        return STOW_LIFT*(float)Math.sin(angle)-8F*(float)Math.sin(2*angle);
    }
    /** Matches the rendered body, not its independently eased position packets. */
    public static Vec3 framePosition(EvaUnit01Entity eva,float partial)
    {
        if(!eva.level().isClientSide)return eva.position();
        if(eva.hasActiveCarrierMotion())return eva.carrierRenderPosition(partial);
        return new Vec3(Mth.lerp((double)partial,eva.xOld,eva.getX()),Mth.lerp((double)partial,eva.yOld,eva.getY()),Mth.lerp((double)partial,eva.zOld,eva.getZ()));
    }
    public static float frameYaw(EvaUnit01Entity eva,float partial)
    {return eva.level().isClientSide?Mth.rotLerp(partial,eva.yBodyRotO,eva.yBodyRot):eva.yBodyRot;}

    /** Used by the CPU socket/capsule path as well as the final Gecko bone writer. */
    public static EvaBodyPose.Sample sample(EvaUnit01Entity eva, EvaBodyPose.Sample result, float partial)
    {
        var tag=eva.getEntityData().get(FRAME);
        if(tag.getBoolean("Release"))
        {
            EvaShutdownR30.decode(tag.getCompound("ReleaseFrom"),result);var target=new EvaBodyPose.Sample(result.rig);EvaShutdownR30.decode(tag.getCompound("ReleaseTo"),target);
            float t=EvaDorsalMechanism.smooth((float)((eva.level().getGameTime()-tag.getLong("Since")+(double)partial)/Math.max(1,tag.getInt("Duration"))));
            for(String name:result.rig.keySet()){result.rotations.get(name).slerp(target.rotations.get(name),t);result.positions.get(name).lerp(target.positions.get(name),t);}result.dirty();return result;
        }
        EvaShutdownR30.decode(tag.getCompound("Origin"), result);
        float weight = restraint(eva, partial);
        for (var bone : result.rig.values())
        {
            Quaternionf rest = bone.name().contains("_axis_") ? new Quaternionf(bone.bindRotation()) : new Quaternionf();
            if (bone.name().equals("head")) rest.rotateX(.07F);
            if (bone.name().equals("forearm_l") || bone.name().equals("forearm_r")) rest.rotateX(.08F);
            result.rotations.get(bone.name()).slerp(rest, weight);
            result.positions.get(bone.name()).lerp(new Vector3f(), weight);
        }
        float angle = pitch(eva, partial);
        Quaternionf turn = new Quaternionf().rotationX(-angle * Mth.DEG_TO_RAD);
        Vector3f hinge = new Vector3f(0, HIP_HEIGHT / EvaScale.RENDER_SCALE, 0);
        Vector3f rootPivot = result.rig.get("root").pivot();
        Vector3f rootPos = result.positions.get("root");
        rootPos.add(rootPivot).sub(hinge);
        turn.transform(rootPos);
        rootPos.add(hinge).sub(rootPivot).add(0, lift(angle) / EvaScale.RENDER_SCALE, 0);
        result.rotations.put("root", turn.mul(result.rotations.get("root")));
        result.dirty();
        return result;
    }

    /** Cradle-local metres to the actual moving assembly's world coordinates. */
    public static Vec3 point(EvaUnit01Entity eva, Vec3 local, float partial)
    {
        float angle = pitch(eva, partial);
        Vector3f p = new Vector3f((float)local.x, (float)local.y-HIP_HEIGHT, (float)local.z);
        new Quaternionf().rotationX(-angle*Mth.DEG_TO_RAD).transform(p);
        p.add(0, HIP_HEIGHT+lift(angle), 0);
        p.rotateY((180-frameYaw(eva,partial))*Mth.DEG_TO_RAD);
        Vec3 root = framePosition(eva,partial);
        return root.add(p.x,p.y,p.z);
    }
    private EvaAirTransportR31() {}
}
