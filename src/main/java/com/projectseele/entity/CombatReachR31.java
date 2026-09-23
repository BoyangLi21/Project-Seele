package com.projectseele.entity;

import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/** Reach of the two real wrist chains, including the palm-to-finger contact offset. */
public final class CombatReachR31
{
    public record ArmError(String side,Vec3 shoulder,Vec3 palm,Vec3 wrist,
                           double upperLength,double forearmLength,double distance,double error) {}
    public record Errors(ArmError left,ArmError right)
    {
        public double maximum(){return Math.max(left.error(),right.error());}
        public boolean reachable(){return Double.isFinite(maximum())&&maximum()<=.18;}
    }

    /** lift is ADDITIONAL height above the victim's current position, not absolute world Y. */
    public static boolean canReach(EvaUnit01Entity eva,LivingEntity victim,double lift)
    {return errors(eva,victim,lift).reachable();}

    public static Errors errors(EvaUnit01Entity eva,LivingEntity victim,double lift)
    {
        if(!Double.isFinite(lift))return new Errors(invalid("l"),invalid("r"));
        var body=posedBody(eva,1,true);Matrix4f world=EvaRifleKinematics.world(eva,1);
        return new Errors(arm(eva,victim,lift,body,world,"l"),arm(eva,victim,lift,body,world,"r"));
    }

    public static Vec3 clampContact(EvaUnit01Entity eva,String side,Vec3 contact)
    {return clampContact(eva,side,contact,1F);}

    /** The client must pass its render partial; server contacts pass 1. */
    public static Vec3 clampContact(EvaUnit01Entity eva,String side,Vec3 contact,float partial)
    {
        var body=posedBody(eva,partial,false);var upper=body.rig.get("arm_"+side);var hand=body.rig.get("hand_"+side);var middle=body.rig.get("finger_middle_"+side);
        if(upper==null||hand==null||middle==null)return contact;
        Vector3f elbow=elbow(body,side);double a=upper.pivot().distance(elbow)*EvaScale.RENDER_SCALE,b=hand.pivot().distance(elbow)*EvaScale.RENDER_SCALE;
        Vec3 shoulder=new Vec3(EvaRifleKinematics.world(eva,partial).mul(body.matrix("arm_"+side)).transformPosition(new Vector3f(upper.pivot())));
        double palm=middle.pivot().distance(hand.pivot())*.62*EvaScale.RENDER_SCALE;
        Vec3 wrist=contact.add(0,-palm,0),direction=wrist.subtract(shoulder);double distance=direction.length();
        if(distance<1e-8)direction=new Vec3(0,-1,0);else direction=direction.scale(1/distance);
        double low=Math.abs(a-b)+.75,high=a+b-.75;
        double wanted=Math.max(low,Math.min(high,distance));
        return shoulder.add(direction.scale(wanted)).add(0,palm,0);
    }

    private static EvaBodyPose.Sample posedBody(EvaUnit01Entity eva,float partial,boolean assumeGrab)
    {
        var body=EvaBodyPose.sample(eva,partial);int action=EvaCombatR31.action(eva);
        float age=EvaCombatR31.age(eva,partial),weight=action==EvaCombatR31.NONE?1:(float)CombatMotionR29.ease(age/6);
        if(action==EvaCombatR31.AIR_STRIKE)
        {
            weight*=1-(float)CombatMotionR29.ease((age-20)/7);
            offset(body,"torso_upper",-.12F*weight,-.30F*(float)CombatMotionR29.ease((age-4)/7)*weight);
        }
        else if(assumeGrab||action>=EvaCombatR31.REACH&&action<=EvaCombatR31.THROW)
        {
        float throwing=action==EvaCombatR31.THROW?(float)CombatMotionR29.ease(age/13):0;
        // Matches the composed grab torso in EvaCombatPoseR31, on top of the
        // authoritative body sample rather than an assumed neutral shoulder.
        offset(body,"torso_lower",-.08F*weight,.12F*throwing*weight);
        offset(body,"torso_upper",(.08F-.32F*throwing)*weight,-.25F*throwing*weight);
        }
        body.dirty();return body;
    }

    private static void offset(EvaBodyPose.Sample body,String name,float x,float y)
    {
        var q=body.rotations.get(name);if(q==null)return;var angle=EvaShutdownR30.euler(q);
        body.rotations.put(name,new Quaternionf().rotationZYX(angle.z,angle.y+y,angle.x+x));
    }

    private static ArmError arm(EvaUnit01Entity eva,LivingEntity victim,double lift,EvaBodyPose.Sample body,Matrix4f world,String side)
    {
        var upper=body.rig.get("arm_"+side);var hand=body.rig.get("hand_"+side);
        var middle=body.rig.get("finger_middle_"+side);
        if(upper==null||hand==null||middle==null)return invalid(side);
        var elbow=elbow(body,side);
        double a=upper.pivot().distance(elbow)*EvaScale.RENDER_SCALE,b=hand.pivot().distance(elbow)*EvaScale.RENDER_SCALE;
        Vec3 shoulder=new Vec3(new Matrix4f(world).mul(body.matrix("arm_"+side)).transformPosition(new Vector3f(upper.pivot())));
        Vec3 palm=EvaCombatR31.grip(eva,victim,side.equals("l"),1).add(0,lift,0);
        // The hand frame maps its middle-finger axis to world up. Pulling the
        // wrist down by this amount makes the actual palm, not the wrist, grip.
        double palmLength=middle.pivot().distance(hand.pivot())*.62*EvaScale.RENDER_SCALE;
        Vec3 wrist=palm.add(0,-palmLength,0);double distance=shoulder.distanceTo(wrist);
        double error=Math.max(Math.max(0,distance-(a+b-.001)),Math.max(0,Math.abs(a-b)+.001-distance));
        return new ArmError(side,shoulder,palm,wrist,a,b,distance,error);
    }
    private static ArmError invalid(String side)
    {return new ArmError(side,Vec3.ZERO,Vec3.ZERO,Vec3.ZERO,0,0,0,Double.POSITIVE_INFINITY);}
    private static Vector3f elbow(EvaBodyPose.Sample body,String side)
    {var marker=body.rig.get("r30_elbow_socket_"+side);return marker==null?new Vector3f(side.equals("l")?-23.489652F:23.489652F,123.435069F,7.737214F).div(16):new Vector3f(marker.pivot());}
    private CombatReachR31() {}
}
