package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.projectseele.entity.EvaRifleKinematics;
import com.projectseele.entity.EvaScale;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.*;
import software.bernie.geckolib.util.RenderUtils;
import java.util.*;

/** Final firearm contact solve, called only inside the post-Gecko pose commit. */
public final class EvaRifleContactRig
{
    public record Witness(Vec3 expectedMuzzle,double rightError,double leftError,double footDrift){}
    public static final Map<Integer,Witness> LAST=new HashMap<>();
    private static final Set<String> BONES=Set.of("torso_upper","head","aim_pitch","arm_r","forearm_r","wrist_r","hand_r","arm_l","forearm_l","wrist_l","hand_l","cannon");
    // GeoBone already contains Gecko's X reflection; only JSON mesh coordinates need it.
    private static Vector3f pivot(GeoBone b){return new Vector3f(b.getPivotX()/16,b.getPivotY()/16,b.getPivotZ()/16);}
    private static Matrix4f matrix(GeoBone b)
    {
        PoseStack p=new PoseStack();List<GeoBone> chain=new ArrayList<>();
        for(GeoBone v=b;v!=null;v=v.getParent())chain.add(v);
        Collections.reverse(chain);for(GeoBone v:chain)RenderUtils.prepMatrixForBone(p,v);
        return new Matrix4f(p.last().pose());
    }
    private static Matrix4f parent(GeoBone b,Matrix4f root){return b.getParent()==null?new Matrix4f(root):new Matrix4f(root).mul(matrix(b.getParent()));}
    private static Quaternionf rotation(Matrix4f m){return m.getUnnormalizedRotation(new Quaternionf()).normalize();}
    private static void rotate(GeoBone b,Quaternionf q)
    {
        Vector3f e=EvaMotionEngineV2.motionQuaternionToAuthoredEuler(q.normalize());b.setRotX(e.x);b.setRotY(e.y);b.setRotZ(e.z);
    }
    private static void absolute(GeoBone b,Matrix4f desired,Matrix4f root)
    {
        Matrix4f rel=parent(b,root).invert().mul(desired);Vector3f p=pivot(b);
        Vector3f offset=rel.transformPosition(new Vector3f(p)).sub(p);
        b.setPosX(-offset.x*16);b.setPosY(offset.y*16);b.setPosZ(offset.z*16);
        Vector3f scale=rel.getScale(new Vector3f());b.setScaleX(scale.x);b.setScaleY(scale.y);b.setScaleZ(scale.z);rotate(b,rotation(rel));
    }
    private static Vector3f worldPivot(GeoBone b,Matrix4f root){return new Matrix4f(root).mul(matrix(b)).transformPosition(pivot(b));}
    private static void resetPosition(GeoBone b){var s=b.getInitialSnapshot();b.setPosX(s.getOffsetX());b.setPosY(s.getOffsetY());b.setPosZ(s.getOffsetZ());b.setScaleX(1);b.setScaleY(1);b.setScaleZ(1);}
    private static void aimBone(GeoBone b,Vector3f rest,Vector3f direction,Matrix4f root)
    {
        Vector3f desired=rotation(parent(b,root)).invert().transform(new Vector3f(direction)).normalize();
        rotate(b,new Quaternionf().rotationTo(new Vector3f(rest).normalize(),desired));
    }
    private static double arm(BakedGeoModel model,String side,Vector3f target,Quaternionf handRotation,Vector3f pole,Matrix4f root)
    {
        GeoBone upper=model.getBone("arm_"+side).orElseThrow(),lower=model.getBone("forearm_"+side).orElseThrow(),wrist=model.getBone("wrist_"+side).orElseThrow(),hand=model.getBone("hand_"+side).orElseThrow();
        for(GeoBone b:List.of(upper,lower,wrist,hand))resetPosition(b);
        wrist.setRotX(0);wrist.setRotY(0);wrist.setRotZ(0);
        Vector3f shoulder=worldPivot(upper,root);float worldScale=root.getScale(new Vector3f()).y;
        Vector3f upperRest=pivot(lower).sub(pivot(upper)),lowerRest=pivot(hand).sub(pivot(lower));
        float a=upperRest.length()*worldScale,b=lowerRest.length()*worldScale;
        Vector3f direction=new Vector3f(target).sub(shoulder);float actualDistance=direction.length();
        if(actualDistance<1e-6F)direction.set(0,-1,0);else direction.div(actualDistance);
        float distance=Math.max(Math.abs(a-b)+.01F,Math.min(a+b-.015F,actualDistance));
        float along=(a*a-b*b+distance*distance)/(2*distance),height=(float)Math.sqrt(Math.max(0,a*a-along*along));
        Vector3f bend=new Vector3f(pole).sub(new Vector3f(direction).mul(pole.dot(direction)));
        if(bend.lengthSquared()<1e-8F)
        {
            bend.set(Math.abs(direction.z)<.9F?new Vector3f(0,0,1):new Vector3f(1,0,0));
            bend.sub(new Vector3f(direction).mul(bend.dot(direction)));
        }
        bend.normalize();
        Vector3f elbow=new Vector3f(shoulder).fma(along,direction).fma(height,bend);
        aimBone(upper,upperRest,new Vector3f(elbow).sub(shoulder),root);
        Vector3f actualElbow=worldPivot(lower,root);aimBone(lower,lowerRest,new Vector3f(target).sub(actualElbow),root);
        Quaternionf local=rotation(parent(hand,root)).invert().mul(handRotation);rotate(hand,local);
        return worldPivot(hand,root).distance(target);
    }
    public static EvaMotionEngineV2.BoneWrites apply(EvaUnit01Entity eva,BakedGeoModel model,float partial,Matrix4f modelToWorld)
    {
        if(eva.getWeapon()!=EvaUnit01Entity.WEAPON_RIFLE||!eva.isPoweredOn()||eva.isNervLogisticsLocked()||eva.isBerserk()||modelToWorld==null)return EvaMotionEngineV2.BoneWrites.empty();
        if(model.getBone("wrist_l").isEmpty()||model.getBone("wrist_r").isEmpty()
                ||model.getBone("finger_middle_l").isEmpty())return EvaMotionEngineV2.BoneWrites.empty();
        GeoBone footL=model.getBone("foot_l").orElseThrow(),footR=model.getBone("foot_r").orElseThrow();
        Vector3f beforeL=worldPivot(footL,modelToWorld),beforeR=worldPivot(footR,modelToWorld);
        boolean proneBody=EvaRifleProneBody.apply(eva,model,partial);
        if(!proneBody)
        {
            model.getBone("torso_upper").ifPresent(b->b.setRotX(b.getRotX()-(float)Math.toRadians(11)));
        }
        if(!proneBody)
        {
            EvaRifleMocap.apply(eva,model,partial);
            EvaRifleProneBody.remember(eva,model);
        }
        model.getBone("aim_pitch").ifPresent(b->{b.setRotX(0);b.setRotY(0);b.setRotZ(0);});
        var f=EvaRifleKinematics.sample(eva,partial,eva.getAimDirectionForPoseCapture());
        Vector3f right=f.right().toVector3f(),forward=f.forward().toVector3f(),up=f.up().toVector3f();
        Matrix3f basis=new Matrix3f().setColumn(0,right).setColumn(1,new Vector3f(forward).negate()).setColumn(2,new Vector3f(up).negate());
        Quaternionf gunRotation=new Quaternionf().setFromNormalized(basis);
        GeoBone head=model.getBone("head").orElseThrow();
        Matrix3f headBasis=new Matrix3f().setColumn(0,right).setColumn(1,up).setColumn(2,new Vector3f(forward).negate());
        Quaternionf headWorld=new Quaternionf().setFromNormalized(headBasis);
        rotate(head,rotation(parent(head,modelToWorld)).invert().mul(headWorld));
        GeoBone cannon=model.getBone("cannon").orElseThrow();
        // The shared gun mesh keeps its own pivot even when a unit's socket differs.
        Vector3f pc=new Vector3f(24.49137F/16,88.34269F/16,.87469F/16);
        Matrix4f gun=new Matrix4f().translation(f.grip().toVector3f()).rotate(gunRotation).scale(EvaScale.RENDER_SCALE*EvaRifleKinematics.WEAPON_SCALE).translate(new Vector3f(pc).negate());
        Matrix4f attachment=new Matrix4f().translation(-1.97646F/16,7.68353F/16,.33048F/16).translate(pc)
                .rotateZYX((float)Math.toRadians(31.40634),(float)Math.toRadians(18.77208),(float)Math.toRadians(-45.37424))
                .scale(EvaRifleKinematics.WEAPON_SCALE).translate(new Vector3f(pc).negate());
        Matrix4f rightHand=new Matrix4f(gun).mul(attachment.invert());
        Vector3f rightTarget=rightHand.transformPosition(pivot(model.getBone("hand_r").orElseThrow()));
        Quaternionf qR=rotation(rightHand);
        // Support the measured fore-end with the palm rather than placing the wrist inside it.
        Quaternionf leftRelative=new Quaternionf().rotationZYX((float)Math.toRadians(-2.51789),(float)Math.toRadians(-33.31161),(float)Math.toRadians(94.97409))
                .rotateZYX((float)Math.toRadians(-.10716),(float)Math.toRadians(10.32404),(float)Math.toRadians(-12.09838));
        Quaternionf refGun=new Quaternionf().rotationZYX((float)Math.toRadians(16.13605),(float)Math.toRadians(8.19676),(float)Math.toRadians(45.25275))
                .rotateZYX((float)Math.toRadians(-15.83803),(float)Math.toRadians(21.17865),(float)Math.toRadians(94.81682))
                .rotateZYX((float)Math.toRadians(31.40634),(float)Math.toRadians(18.77208),(float)Math.toRadians(-45.37424));
        Quaternionf qL=new Quaternionf(gunRotation).mul(refGun.invert().mul(leftRelative));
        Vector3f palmOffset=pivot(model.getBone("finger_middle_l").orElseThrow())
                .sub(pivot(model.getBone("hand_l").orElseThrow())).mul(.65F*EvaScale.RENDER_SCALE);
        qL.transform(palmOffset);
        Vector3f leftTarget=f.grip().add(f.forward().scale(6)).subtract(f.up().scale(.55)).toVector3f().sub(palmOffset);
        double re=arm(model,"r",rightTarget,qR,new Vector3f(right).mul(.7F).add(0,-1,0),modelToWorld);
        double le=arm(model,"l",leftTarget,qL,new Vector3f(right).mul(-.7F).add(0,-1,0),modelToWorld);
        absolute(cannon,gun,modelToWorld);
        double drift=proneBody?-1:Math.max(beforeL.distance(worldPivot(footL,modelToWorld)),beforeR.distance(worldPivot(footR,modelToWorld)));
        if(LAST.size()>32)LAST.clear();LAST.put(eva.getId(),new Witness(f.muzzle(),re,le,drift));
        Set<String> rotations=new LinkedHashSet<>(BONES);
        Set<String> positions=new LinkedHashSet<>(Set.of("arm_r","forearm_r","wrist_r","hand_r","arm_l","forearm_l","wrist_l","hand_l","cannon"));
        if(proneBody){rotations.addAll(EvaRifleProneBody.BONES);positions.addAll(EvaRifleProneBody.BONES);}
        return new EvaMotionEngineV2.BoneWrites(Set.copyOf(rotations),Set.copyOf(positions),"MOTION_ENGINE_LIVE_ACTION");
    }
}
