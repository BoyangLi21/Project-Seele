package com.projectseele.entity;

import com.projectseele.config.SeeleConfig;
import net.minecraft.util.Mth;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

/** Shared world-space weapon anchor. Animation, hands and ballistics use this frame. */
public final class EvaRifleKinematics
{
    public static final float WEAPON_SCALE=.72F;
    // Measured centre of the visible Pallet Rifle barrel cap, relative to its grip.
    public static final double CAP_FORWARD=20.3010625D*WEAPON_SCALE;
    public static final double CAP_DOWN=.1561192D*WEAPON_SCALE;
    public record Frame(Vec3 grip,Vec3 muzzle,Vec3 forward,Vec3 up,Vec3 right,float ready,float recoil){}
    public static Frame sample(EvaUnit01Entity eva,float partial,Vec3 opticalDirection)
    {
        float crouch=eva.rifleCrouchBlend(partial),prone=eva.rifleProneBlend(partial),ready=eva.rifleReadyBlend(partial),recoil=eva.rifleRecoilBlend(partial);
        prone=prone*prone*prone*(10+prone*(-15+6*prone));
        double yaw=Math.toRadians(Mth.rotLerp(partial,eva.yRotO,eva.getYRot()));
        Vec3 forward=new Vec3(-Math.sin(yaw),0,Math.cos(yaw));
        Vec3 right=new Vec3(-forward.z,0,forward.x);
        double height=Mth.lerp(prone,Mth.lerp(crouch,43.5D,31.5D),9.4D);
        double reach=Mth.lerp(prone,10.2D,28D);
        Vec3 origin=eva.level().isClientSide?new Vec3(Mth.lerp(partial,eva.xOld,eva.getX()),Mth.lerp(partial,eva.yOld,eva.getY()),Mth.lerp(partial,eva.zOld,eva.getZ())):eva.position();
        Vec3 grip=origin.add(right.scale(Mth.lerp(prone,5D,4.5D))).add(0,height-(1-ready)*7,0).add(forward.scale(reach-recoil*.38));
        var pilot=eva.getPilotEntity();Vec3 sight=pilot==null?origin.add(0,55,0):pilot.getEyePosition(partial);
        double range=SeeleConfig.EVA_RIFLE_RANGE.get();Vec3 end=sight.add(opticalDirection.scale(range));
        var hit=eva.level().clip(new ClipContext(sight,end,ClipContext.Block.COLLIDER,ClipContext.Fluid.NONE,eva));
        Vec3 target=hit.getType()==HitResult.Type.MISS?end:hit.getLocation();
        Vec3 aim=target.subtract(grip).normalize();
        if(aim.lengthSqr()<1.0e-8D)aim=opticalDirection.normalize();
        // The low-ready lift is a real shared pose; firing waits for the shoulder seat.
        aim=aim.add(0,-(1-ready)*.7+recoil*.009,0).normalize();
        Vec3 lateral=aim.cross(new Vec3(0,1,0));
        lateral=lateral.lengthSqr()<1.0e-8D?right:lateral.normalize();
        Vec3 up=lateral.cross(aim).normalize();
        Vec3 muzzle=grip.add(aim.scale(CAP_FORWARD)).subtract(up.scale(CAP_DOWN)).add(lateral.scale(-.0014665D*WEAPON_SCALE));
        return new Frame(grip,muzzle,aim,up,lateral,ready,recoil);
    }
}
