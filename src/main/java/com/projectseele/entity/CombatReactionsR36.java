package com.projectseele.entity;

import com.projectseele.physics.AnatomicalLimbConstraints;
import com.projectseele.physics.CombatBodyProfiles;
import com.projectseele.util.WeakIdentityMap;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/** A hit is absorbed from the current pose, then caught by two placed steps. */
public final class CombatReactionsR36
{
    private record Catch(long start,EvaBodyPose.Sample pose,Vec3 origin,Vec3[] feet,Quaternionf[] soles,float yaw) {}
    private static final WeakIdentityMap<LivingEntity,Catch> CATCHES=new WeakIdentityMap<>();
    private static final ThreadLocal<Boolean> SAMPLING=ThreadLocal.withInitial(()->false);
    public static boolean enabled(LivingEntity e)
    {return e instanceof EvaUnit01Entity eva?EvaGameplayMotionR32.phrases(eva):e instanceof SachielEntity&&SachielGameplayMotionR32.phrases();}
    public static void capture(LivingEntity e,CombatFeelR31.Beat beat)
    {
        if(!enabled(e)||beat.kind()!=CombatFeelR31.STAGGER||SAMPLING.get())return;
        if(e instanceof EvaUnit01Entity eva&&(eva.isPilotProne()||eva.isPilotCrouching()||eva.isNervLogisticsLocked()))return;
        SAMPLING.set(true);
        try
        {
            var pose=e instanceof EvaUnit01Entity eva?EvaBodyPose.sample(eva,0):SachielBodyPoseR35.sample((SachielEntity)e,0);
            Vec3[] feet=new Vec3[2];Quaternionf[] soles=new Quaternionf[2];int i=0;
            for(String side:new String[]{"l","r"})
            {
                var matrix=pose.matrix("foot_"+side);var local=matrix.transformPosition(new Vector3f(pose.rig.get("foot_"+side).pivot()));
                soles[i]=matrix.getUnnormalizedRotation(new Quaternionf());
                local.mul(5).rotateY((180-e.getYRot())*Mth.DEG_TO_RAD);feet[i++]=e.position().add(local.x,local.y,local.z);
            }
            CATCHES.put(e,new Catch(beat.start(),pose,e.position(),feet,soles,e.getYRot()));
        }
        finally{SAMPLING.set(false);}
    }
    public static boolean active(LivingEntity e)
    {
        var beat=CombatFeelR31.beat(e);var c=CATCHES.get(e);
        if(SAMPLING.get()||beat==null||beat.kind()!=CombatFeelR31.STAGGER||c==null||c.start!=beat.start())return false;
        // A buffered attack is legal after the displacement window. Its entry
        // snapshot already contains this recoil; do not hide that new attack
        // under the remaining release of the previous reaction.
        if(CombatFeelR31.age(e,0)>=7&&(e instanceof EvaUnit01Entity eva&&EvaCombatSupportR33.strike(eva)||e instanceof SachielEntity angel&&angel.isStrikeActive()))return false;
        return true;
    }
    public static boolean ownsDisplacement(LivingEntity e)
    {return active(e)&&CombatFeelR31.age(e,0)<7;}
    private static float smooth(float t){t=Mth.clamp(t,0,1);return t*t*(3-2*t);}
    public static EvaBodyPose.Sample apply(LivingEntity e,EvaBodyPose.Sample base,float partial)
    {
        if(!active(e))return base;var c=CATCHES.get(e);var hit=CombatFeelR31.beat(e);var profile=CombatBodyProfiles.get(e);if(profile==null)return base;
        float age=CombatFeelR31.age(e,partial),release=smooth((age-9)/7),load=smooth(age/2)*(1-smooth((age-6)/10));
        var p=new EvaBodyPose.Sample(base.rig);
        for(String n:p.rig.keySet())
        {p.rotations.put(n,new Quaternionf(c.pose.rotations.get(n)).slerp(base.rotations.get(n),release));p.positions.put(n,new Vector3f(c.pose.positions.get(n)).lerp(base.positions.get(n),release));}
        var local=hit.direction().toVector3f().rotateY(-(180-c.yaw)*Mth.DEG_TO_RAD);float force=hit.strength()*load;
        p.rotations.get("torso_lower").rotateX(local.z*.14F*force).rotateZ(-local.x*.12F*force);
        p.rotations.get("torso_upper").rotateX(local.z*.34F*force).rotateZ(-local.x*.24F*force);
        p.rotations.get("head").rotateX(local.z*.17F*force).rotateZ(-local.x*.10F*force);
        float height=p.rig.get("head").pivot().y;
        p.positions.get("root").add(local.x*height*.022F*force,-height*.022F*force,local.z*height*.022F*force);p.dirty();
        // The shoulder recoils before the forearm opens to regain balance.
        float brace=smooth((age-1)/3)*(1-smooth((age-8)/8));
        for(String side:new String[]{"l","r"})
        {
            float sign=side.equals("l")?-1:1;
            p.rotations.get("arm_"+side).rotateZ(sign*.22F*brace).rotateX(-.15F*brace);
            p.rotations.get("forearm_"+side).rotateX(.18F*brace);
        }
        p.dirty();var origin=e.level().isClientSide?e.getPosition(partial):e.position();
        Vec3 moved=origin.subtract(c.origin).multiply(1,0,1),direction=hit.direction().multiply(1,0,1).normalize();
        int first=local.x>.1?1:0;
        for(int i=0;i<2;i++)
        {
            float u=smooth((age-(i==first?1:6))/(i==first?6F:7F));
            double reach=Math.max(moved.horizontalDistance()+.9,4.2*hit.strength());
            var goal=c.feet[i].add(direction.scale(reach*u));
            float lift=(float)Math.sin(Math.PI*u)*height*.04F*5;
            var target=new Vector3f((float)(goal.x-origin.x),(float)(goal.y-origin.y+lift),(float)(goal.z-origin.z))
                    .rotateY(-(180-e.getYRot())*Mth.DEG_TO_RAD).div(5);
            String side=i==0?"l":"r";
            var current=p.matrix("foot_"+side).transformPosition(new Vector3f(p.rig.get("foot_"+side).pivot()));target.lerp(current,release);
            AnatomicalLimbConstraints.reachFoot(p,profile,side,target,c.soles[i]);
        }
        return p;
    }
    private CombatReactionsR36(){}
}
