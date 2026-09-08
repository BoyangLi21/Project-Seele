package com.projectseele.entity;

import com.projectseele.config.SeeleConfig;
import net.minecraft.util.Mth;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;
import org.joml.Vector3f;

/** The evaluated shoulder carries the stock; the head is free to find the sights. */
public final class EvaRifleKinematics
{
    public static final float WEAPON_SCALE=.72F;
    public static final double CAP_FORWARD=20.3010625D*WEAPON_SCALE;
    public static final double CAP_DOWN=.1561192D*WEAPON_SCALE;
    private static final double STOCK_BACK=49.700046D/16*EvaScale.RENDER_SCALE*WEAPON_SCALE;
    private static final double STOCK_UP=7.656318D/16*EvaScale.RENDER_SCALE*WEAPON_SCALE;
    public record Frame(Vec3 grip,Vec3 muzzle,Vec3 stock,Vec3 forward,Vec3 up,Vec3 right,float ready,float recoil) {}
    public static Matrix4f world(EvaUnit01Entity entity,float partial)
    {
        Vec3 position=entity.level().isClientSide?entity.getPosition(partial):entity.position();
        float yaw=entity.level().isClientSide?Mth.rotLerp(partial,entity.yBodyRotO,entity.yBodyRot):entity.yBodyRot;
        return new Matrix4f().translation(position.toVector3f()).rotateY((180-yaw)*Mth.DEG_TO_RAD).scale(EvaScale.RENDER_SCALE);
    }
    public static Frame sample(EvaUnit01Entity entity,float partial,Vec3 direction)
    {
        return sample(entity,partial,direction,EvaBodyPose.sample(entity,partial),world(entity,partial));
    }
    public static Frame sample(EvaUnit01Entity entity,float partial,Vec3 opticalDirection,EvaBodyPose.Sample body,Matrix4f world)
    {
        var bone=body.rig.get("arm_r");Vector3f p=new Matrix4f(world).mul(body.matrix("arm_r")).transformPosition(new Vector3f(bone.pivot()));
        Vec3 shoulder=new Vec3(p.x,p.y,p.z);
        var chest=new Matrix4f(world).mul(body.matrix("torso_upper"));Vector3f lateral=chest.transformDirection(new Vector3f(1,0,0)).normalize();
        Vec3 right=new Vec3(lateral.x,lateral.y,lateral.z);
        Vector3f facing=world.transformDirection(new Vector3f(0,0,-1)).normalize();Vec3 forward=new Vec3(facing.x,0,facing.z).normalize();
        float prone=entity.rifleProneBlend(partial),ready=entity.rifleReadyBlend(partial),recoil=entity.rifleRecoilBlend(partial);
        // Rotate about the pad's shoulder contact. Holding its upper corner
        // fixed made the lower stock swing through the upper arm at steep pitch.
        // Measured over the running torso cycle; Unit-00's round shell is wider.
        double helmetClearance=switch(entity.getUnitVariant()) { case 0->2.8; case 2->1.9; default->1.4; };
        Vec3 pocket=shoulder.add(right.scale(helmetClearance)).add(forward.scale(2)).add(0,Mth.lerp(prone,-1.5D,.2D),0);
        Vec3 stock=pocket.add(0,5,0);
        var pilot=entity.getPilotEntity();Vec3 sight=pilot==null?shoulder.add(0,7,0):pilot.getEyePosition(partial);
        Vec3 end=sight.add(opticalDirection.scale(SeeleConfig.EVA_RIFLE_RANGE.get()));
        var hit=entity.level().clip(new ClipContext(sight,end,ClipContext.Block.COLLIDER,ClipContext.Fluid.NONE,entity));
        Vec3 target=hit.getType()==HitResult.Type.MISS?end:hit.getLocation();
        Vec3 aim=target.subtract(stock).normalize();if(aim.lengthSqr()<1e-8)aim=opticalDirection.normalize();
        for(int pass=0;pass<2;pass++)
        {
            Vec3 axis=aim.cross(new Vec3(0,1,0));if(axis.lengthSqr()<1e-8)axis=right;else axis=axis.normalize();
            Vec3 vertical=axis.cross(aim).normalize();stock=pocket.add(vertical.scale(5));
            aim=target.subtract(stock).add(vertical.scale(STOCK_UP+CAP_DOWN)).normalize();
        }
        aim=aim.add(0,-(1-ready)*.6+recoil*.008,0).normalize();
        // Do not pitch the long barrel through the floor while lying down.
        double availableHeight=Math.max(.5,stock.y-entity.getY()-1.1);
        double maxDown=Math.min(.98,availableHeight/(STOCK_BACK+CAP_FORWARD));
        if(aim.y < -maxDown)
        {
            Vec3 flat=new Vec3(aim.x,0,aim.z).normalize();aim=flat.scale(Math.sqrt(1-maxDown*maxDown)).add(0,-maxDown,0);
        }
        Vec3 axisRight=aim.cross(new Vec3(0,1,0));axisRight=axisRight.lengthSqr()<1e-8?right:axisRight.normalize();
        Vec3 up=axisRight.cross(aim).normalize();stock=pocket.add(up.scale(5)).subtract(aim.scale(recoil*.22));
        Vec3 grip=stock.add(aim.scale(STOCK_BACK)).subtract(up.scale(STOCK_UP));
        Vec3 muzzle=grip.add(aim.scale(CAP_FORWARD)).subtract(up.scale(CAP_DOWN)).add(axisRight.scale(-.0014665D*WEAPON_SCALE));
        return new Frame(grip,muzzle,stock,aim,up,axisRight,ready,recoil);
    }
}
