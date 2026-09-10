package com.projectseele.entity;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;
/** The EVA-UN monocular lens, expressed in the same body rig used for aiming. */
public final class EvaUNOptics
{
    public static final Vector3f LENS=new Vector3f(0,173,-7.49F).div(16);
    public static Quaternionf orientation(EvaPrototypeEntity eva)
    {return new Quaternionf().rotationY((180-eva.eyeAimYaw())*(float)Math.PI/180).rotateX(-eva.eyeAimPitch()*(float)Math.PI/180);}
    public static Vec3 eye(EvaPrototypeEntity eva,float partial)
    {
        var pose=EvaBodyPose.sample(eva,partial);var b=pose.rig.get("head");var world=EvaRifleKinematics.world(eva,partial);Vector3f joint=new Matrix4f(world).mul(pose.matrix("head")).transformPosition(new Vector3f(b.pivot()));
        Vector3f offset=orientation(eva).transform(new Vector3f(LENS).sub(b.pivot()).mul(EvaScale.RENDER_SCALE));joint.add(offset);return new Vec3(joint.x,joint.y,joint.z);
    }
    private EvaUNOptics() {}
}
