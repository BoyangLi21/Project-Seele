package com.projectseele.client.render;

import com.projectseele.entity.EvaBodyPose;
import com.projectseele.entity.EvaRifleKinematics;
import com.projectseele.entity.EvaScale;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import java.util.*;

/** Shoulder stock, wrist grips and head-to-sight alignment in the final pose commit. */
public final class EvaRifleContactRig
{
    public record Witness(Vec3 expectedMuzzle,double rightError,double leftError,double footDrift,Vec3 stock,Vec3 shoulder) {}
    public static final Map<Integer,Witness> LAST=new HashMap<>();
    private static void absolute(GeoBone b,Matrix4f desired,Matrix4f root)
    {
        Matrix4f rel=EvaRigTransforms.parent(b,root).invert().mul(desired);Vector3f p=EvaRigTransforms.pivot(b);
        Vector3f offset=rel.transformPosition(new Vector3f(p)).sub(p);
        b.setPosX(-offset.x*16);b.setPosY(offset.y*16);b.setPosZ(offset.z*16);
        Vector3f scale=rel.getScale(new Vector3f());b.setScaleX(scale.x);b.setScaleY(scale.y);b.setScaleZ(scale.z);
        EvaRigTransforms.rotate(b,EvaRigTransforms.rotation(rel));
    }
    private static boolean bodyBone(String n)
    {
        return n.equals("root")||n.startsWith("torso_")||n.equals("aim_pitch")||n.equals("neck")||n.equals("head")
                ||n.startsWith("leg_")||n.startsWith("shin_")||n.startsWith("ankle_")||n.startsWith("foot_")
                ||n.startsWith("arm_")||n.startsWith("forearm_")||n.startsWith("wrist_")||n.startsWith("hand_")||n.startsWith("finger_");
    }
    public static EvaMotionEngineV2.BoneWrites apply(EvaUnit01Entity eva,BakedGeoModel model,float partial,Matrix4f root)
    {
        if(eva.getWeapon()!=EvaUnit01Entity.WEAPON_RIFLE||!eva.isPoweredOn()||eva.isNervLogisticsLocked()||eva.isBerserk()
                ||eva.isCrucified()||eva.getVisualPose()!=0||eva.getActivationTicks()>0||root==null)return EvaMotionEngineV2.BoneWrites.empty();
        if(model.getBone("wrist_l").isEmpty()||model.getBone("wrist_r").isEmpty()||model.getBone("finger_middle_l").isEmpty())return EvaMotionEngineV2.BoneWrites.empty();
        var body=EvaBodyPose.sample(eva,partial);Set<String> rotations=new LinkedHashSet<>(),positions=new LinkedHashSet<>();
        for(String n:body.rig.keySet())
        {
            GeoBone b=model.getBone(n).orElse(null);if(b==null||!bodyBone(n))continue;
            if(eva.isVisuallyAirborneForRender())
            {
                // Keep the accepted airborne body, while its real shoulder still carries the gun.
                body.rotations.put(n,new Quaternionf().rotationZYX(b.getRotZ(),b.getRotY(),b.getRotX()));
                body.positions.put(n,new Vector3f(-b.getPosX(),b.getPosY(),b.getPosZ()).div(16));
            }
            else
            {
                EvaRigTransforms.rotate(b,body.rotations.get(n));var p=body.positions.get(n);
                b.setPosX(-p.x*16);b.setPosY(p.y*16);b.setPosZ(p.z*16);b.setScaleX(1);b.setScaleY(1);b.setScaleZ(1);
                rotations.add(n);positions.add(n);
            }
        }
        body.dirty();var f=EvaRifleKinematics.sample(eva,partial,eva.getAimDirectionForPoseCapture(),body,root);
        Vector3f right=f.right().toVector3f(),forward=f.forward().toVector3f(),up=f.up().toVector3f();
        Matrix3f basis=new Matrix3f().setColumn(0,right).setColumn(1,new Vector3f(forward).negate()).setColumn(2,new Vector3f(up).negate());
        Quaternionf gunRotation=new Quaternionf().setFromNormalized(basis);
        GeoBone cannon=model.getBone("cannon").orElseThrow();Vector3f pc=new Vector3f(24.49137F,88.34269F,.87469F).div(16);
        Matrix4f gun=new Matrix4f().translation(f.grip().toVector3f()).rotate(gunRotation).scale(EvaScale.RENDER_SCALE*EvaRifleKinematics.WEAPON_SCALE).translate(new Vector3f(pc).negate());
        Matrix4f attachment=new Matrix4f().translation(-1.97646F/16,7.68353F/16,.33048F/16).translate(pc)
                .rotateZYX((float)Math.toRadians(31.40634),(float)Math.toRadians(18.77208),(float)Math.toRadians(-45.37424))
                .scale(EvaRifleKinematics.WEAPON_SCALE).translate(new Vector3f(pc).negate());
        Matrix4f rightHand=new Matrix4f().translation(new Vector3f(right).fma(-1.5F,up)).mul(gun).mul(attachment.invert());
        Vector3f rightTarget=rightHand.transformPosition(EvaRigTransforms.pivot(model.getBone("hand_r").orElseThrow()));
        Quaternionf qR=EvaRigTransforms.rotation(rightHand);
        Quaternionf leftRelative=new Quaternionf().rotationZYX((float)Math.toRadians(-2.51789),(float)Math.toRadians(-33.31161),(float)Math.toRadians(94.97409))
                .rotateZYX((float)Math.toRadians(-.10716),(float)Math.toRadians(10.32404),(float)Math.toRadians(-12.09838));
        Quaternionf refGun=new Quaternionf().rotationZYX((float)Math.toRadians(16.13605),(float)Math.toRadians(8.19676),(float)Math.toRadians(45.25275))
                .rotateZYX((float)Math.toRadians(-15.83803),(float)Math.toRadians(21.17865),(float)Math.toRadians(94.81682))
                .rotateZYX((float)Math.toRadians(31.40634),(float)Math.toRadians(18.77208),(float)Math.toRadians(-45.37424));
        Quaternionf qL=new Quaternionf(gunRotation).mul(refGun.invert().mul(leftRelative));
        Vector3f palmOffset=EvaRigTransforms.pivot(model.getBone("finger_middle_l").orElseThrow()).sub(EvaRigTransforms.pivot(model.getBone("hand_l").orElseThrow())).mul(.65F*EvaScale.RENDER_SCALE);
        qL.transform(palmOffset);
        Vector3f supportBase=f.grip().subtract(f.up().scale(3.3)).toVector3f().sub(palmOffset);
        var leftUpper=model.getBone("arm_l").orElseThrow();var leftHand=model.getBone("hand_l").orElseThrow();
        var leftShoulder=EvaRigTransforms.point(leftUpper,EvaRigTransforms.pivot(leftUpper),root);
        float reach=(EvaRigTransforms.elbow("l").sub(EvaRigTransforms.pivot(leftUpper)).length()
                +EvaRigTransforms.pivot(leftHand).sub(EvaRigTransforms.elbow("l")).length())*root.getScale(new Vector3f()).y-.1F;
        var fromShoulder=new Vector3f(supportBase).sub(leftShoulder);float along=fromShoulder.dot(forward);
        float discriminant=along*along-fromShoulder.lengthSquared()+reach*reach;
        // A supporting hand can slide along the lower foregrip as the barrel
        // rises. Keep that contact on the gun rather than stretching the arm.
        float supportSlide=Math.min(2F,-along+(float)Math.sqrt(Math.max(0,discriminant)));
        Vector3f leftTarget=new Vector3f(supportBase).fma(supportSlide,forward);
        float out=1,down=.7F;
        float highAim=net.minecraft.util.Mth.clamp((float)(f.forward().y-.35)/.35F,0,1);
        double re=solve(model,"r",rightTarget,qR,new Vector3f(right).mul(out-.35F*highAim).add(0,-down,0),root);
        double le=solve(model,"l",leftTarget,qL,new Vector3f(right).mul(-out).add(0,-down,0),root);
        absolute(cannon,gun,root);
        // Lean the gaze toward the existing sight line. This never moves the weapon.
        var neck=model.getBone("neck").orElseThrow();neck.setRotZ(neck.getRotZ()-.07F*f.ready());
        var head=model.getBone("head").orElseThrow();var eye=EvaRigTransforms.point(head,EvaRigTransforms.pivot(head),root);
        var gaze=f.muzzle().add(f.forward().scale(40)).toVector3f().sub(eye).normalize();var lateral=new Vector3f(gaze).cross(0,1,0).normalize();
        var vertical=new Vector3f(lateral).cross(gaze);var headBasis=new Matrix3f().setColumn(0,lateral).setColumn(1,vertical).setColumn(2,new Vector3f(gaze).negate());
        var headWorld=new Quaternionf().setFromNormalized(headBasis).rotateZ(-.05F*f.ready());EvaRigTransforms.rotate(head,EvaRigTransforms.rotation(EvaRigTransforms.parent(head,root)).invert().mul(headWorld));
        EvaHeadClearance.apply(eva,head,root,gun,headWorld,right,forward,partial);
        var shoulder=EvaRigTransforms.point(model.getBone("arm_r").orElseThrow(),EvaRigTransforms.pivot(model.getBone("arm_r").orElseThrow()),root);
        if(LAST.size()>32)LAST.clear();LAST.put(eva.getId(),new Witness(f.muzzle(),re,le,-1,f.stock(),new Vec3(shoulder.x,shoulder.y,shoulder.z)));
        rotations.addAll(Set.of("neck","head","arm_r","forearm_r","wrist_r","hand_r","arm_l","forearm_l","wrist_l","hand_l","cannon"));
        positions.addAll(Set.of("forearm_r","wrist_r","hand_r","forearm_l","wrist_l","hand_l","cannon"));
        return new EvaMotionEngineV2.BoneWrites(Set.copyOf(rotations),Set.copyOf(positions),"MOTION_ENGINE_LIVE_ACTION");
    }
    private static double solve(BakedGeoModel model,String side,Vector3f target,Quaternionf rotation,Vector3f pole,Matrix4f root)
    {
        return EvaRigTransforms.solveArm(model.getBone("arm_"+side).orElseThrow(),model.getBone("forearm_"+side).orElseThrow(),model.getBone("wrist_"+side).orElseThrow(),model.getBone("hand_"+side).orElseThrow(),side,target,rotation,pole,root);
    }
}
