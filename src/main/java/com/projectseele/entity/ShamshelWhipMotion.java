package com.projectseele.entity;

import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import java.util.*;

/** Measured rig pivots; one FK curve drives both visible whips and server contacts. */
public final class ShamshelWhipMotion
{
    public static final int CYCLE = 34, CONTACT_START = 12, CONTACT_END = 23;
    private static final float[][] PIVOTS = {{51.868429F,155.598410F,-11.655827F},
            {60.027508F,121.796513F,-29.139567F},{62.941464F,87.994615F,-52.451220F},{60.610299F,54.192717F,-67.603795F}};
    public static float smooth(float x) { x = Mth.clamp(x, 0, 1); return x*x*(3-2*x); }
    public static float envelope(float age) { return age < 0 ? 0 : smooth(age/10)*(1-smooth((age-23)/11)); }
    public static Vector3f rotation(int side, int segment, int activeSide, float age, float clock)
    {
        float idle = (float)Math.sin(clock*.055-segment*.55+side)*.025F;
        if (age < 0 || side != activeSide) return new Vector3f(idle, 0, idle*.4F);
        float weight = envelope(age), drive = smooth((age-11-segment*1.1F)/9);
        return new Vector3f((segment==0?1.12F:.045F)*weight+idle*(1-weight),
                side*((segment==0?.72F:.11F)*(1-2*drive))*weight,
                side*(segment==0?.13F:.045F)*weight);
    }
    public static float bodyPitch(float age) { return -.04F*envelope(age); }
    private static Vector3f pivot(int side, int index)
    {
        float[] p=PIVOTS[index]; return new Vector3f(-side*p[0],p[1],p[2]).div(16);
    }
    private static void rotate(Matrix4f m, Vector3f pivot, Vector3f r)
    { m.translate(pivot).rotateZ(r.z).rotateY(r.y).rotateX(r.x).translate(-pivot.x,-pivot.y,-pivot.z); }
    public static List<Vec3> points(ShamshelEntity actor, float age, float partial)
    {
        int side=actor.sweepSide();
        Vec3 origin=actor.level().isClientSide?actor.getPosition(partial):actor.position();
        float yaw=actor.isSweeping()?actor.sweepYaw():(actor.level().isClientSide?Mth.rotLerp(partial,actor.yBodyRotO,actor.yBodyRot):actor.yBodyRot);
        var matrix=new Matrix4f().translation(origin.toVector3f()).rotateY((float)Math.toRadians(180-yaw)).scale(5);
        rotate(matrix,new Vector3f(0,93.822528F/16,0),new Vector3f(bodyPitch(age),0,0));
        List<Vec3> points=new ArrayList<>();
        for(int i=0;i<4;i++)
        {
            Vector3f p=pivot(side,i); points.add(new Vec3(matrix.transformPosition(new Vector3f(p))));
            rotate(matrix,p,rotation(side,i,side,age,actor.tickCount+partial));
        }
        points.add(new Vec3(matrix.transformPosition(new Vector3f(-side*65,20,-78).div(16))));
        return points;
    }
    private ShamshelWhipMotion() {}
}
