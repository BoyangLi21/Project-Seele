package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import java.util.ArrayList;
import java.util.Collections;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.util.RenderUtils;

final class EvaRigTransforms
{
    static Vector3f pivot(GeoBone bone) { return new Vector3f(bone.getPivotX(),bone.getPivotY(),bone.getPivotZ()).div(16); }
    static Matrix4f model(GeoBone bone)
    {
        var chain=new ArrayList<GeoBone>();for(var b=bone;b!=null;b=b.getParent())chain.add(b);
        Collections.reverse(chain);var pose=new PoseStack();for(var b:chain)RenderUtils.prepMatrixForBone(pose,b);
        return new Matrix4f(pose.last().pose());
    }
    static Matrix4f parent(GeoBone bone,Matrix4f root) { return bone.getParent()==null?new Matrix4f(root):new Matrix4f(root).mul(model(bone.getParent())); }
    static Quaternionf rotation(Matrix4f matrix) { return matrix.getUnnormalizedRotation(new Quaternionf()).normalize(); }
    static void rotate(GeoBone bone,Quaternionf q)
    {
        var a=EvaMotionEngineV2.motionQuaternionToAuthoredEuler(q);bone.setRotX(a.x);bone.setRotY(a.y);bone.setRotZ(a.z);
    }
    static Vector3f point(GeoBone bone,Vector3f point,Matrix4f root) { return new Matrix4f(root).mul(model(bone)).transformPosition(new Vector3f(point)); }
    static Vector3f elbow(String side) { return new Vector3f(side.equals("l")?-23.489652F:23.489652F,123.435069F,7.737214F).div(16); }
    static void hinge(GeoBone bone,Vector3f centre)
    {
        var delta=new Vector3f(centre).sub(pivot(bone));var q=new Quaternionf().rotationZYX(bone.getRotZ(),bone.getRotY(),bone.getRotX());
        var offset=new Vector3f(delta).sub(q.transform(new Vector3f(delta)));
        bone.setPosX(-offset.x*16);bone.setPosY(offset.y*16);bone.setPosZ(offset.z*16);
    }
    private static Matrix3f frame(Vector3f direction,Vector3f axis)
    {
        var y=new Vector3f(direction).normalize();var x=new Vector3f(axis).sub(new Vector3f(y).mul(axis.dot(y))).normalize();
        return new Matrix3f().setColumn(0,x).setColumn(1,y).setColumn(2,new Vector3f(x).cross(y));
    }
    private static void orient(GeoBone bone,Vector3f rest,Vector3f direction,Vector3f hingeAxis,Matrix4f root)
    {
        var q=new Quaternionf().setFromNormalized(frame(direction,hingeAxis).mul(frame(rest,new Vector3f(1,0,0)).transpose()));
        rotate(bone,rotation(parent(bone,root)).invert().mul(q));
    }
    static double solveArm(GeoBone upper,GeoBone lower,GeoBone wrist,GeoBone hand,String side,
                           Vector3f target,Quaternionf handRotation,Vector3f pole,Matrix4f root)
    {
        var centre=elbow(side);var shoulder=point(upper,pivot(upper),root);
        float scale=root.getScale(new Vector3f()).y;var u=new Vector3f(centre).sub(pivot(upper));var v=pivot(hand).sub(centre);
        float a=u.length()*scale,b=v.length()*scale;var direction=new Vector3f(target).sub(shoulder);float length=direction.length();
        if(length<1e-6F)direction.set(0,-1,0);else direction.div(length);
        float distance=Math.max(Math.abs(a-b)+.001F,Math.min(a+b-.001F,length));
        float along=(a*a-b*b+distance*distance)/(2*distance),height=(float)Math.sqrt(Math.max(0,a*a-along*along));
        var bend=new Vector3f(pole).sub(new Vector3f(direction).mul(pole.dot(direction)));
        if(bend.lengthSquared()<1e-8F)bend.set(0,0,1).sub(new Vector3f(direction).mul(direction.z));
        bend.normalize();var joint=new Vector3f(shoulder).fma(along,direction).fma(height,bend);
        var du=new Vector3f(joint).sub(shoulder);var dl=new Vector3f(target).sub(joint);var axis=new Vector3f(du).cross(dl);
        if(axis.lengthSquared()<1e-8F)axis.set(du).cross(bend);
        axis.normalize();var localSide=rotation(parent(upper,root)).transform(new Vector3f(1,0,0));if(axis.dot(localSide)<0)axis.negate();
        for(var bone:new GeoBone[]{lower,wrist,hand}){bone.setPosX(0);bone.setPosY(0);bone.setPosZ(0);}
        wrist.setRotX(0);wrist.setRotY(0);wrist.setRotZ(0);
        orient(upper,u,du,axis,root);var actual=parent(lower,root).transformPosition(new Vector3f(centre));
        orient(lower,v,new Vector3f(target).sub(actual),axis,root);hinge(lower,centre);
        rotate(hand,rotation(parent(hand,root)).invert().mul(handRotation));
        return point(hand,pivot(hand),root).distance(target);
    }
}
