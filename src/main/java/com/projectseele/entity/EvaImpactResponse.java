package com.projectseele.entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import com.projectseele.util.WeakIdentityMap;
import java.util.*;

/** Directional damped recoil without stopping the locomotion clock or taking pilot control. */
public final class EvaImpactResponse
{
    private record Impulse(long tick,Vec3 direction,float strength,float height) {}
    private static final WeakIdentityMap<LivingEntity,List<Impulse>> HITS=new WeakIdentityMap<>();
    public record Pose(float pitch,float roll,float head,float energy) {}
    public static void displace(EvaUnit01Entity eva,Vec3 direction,float strength)
    {
        if(eva.level().isClientSide&&CombatReactionsR36.ownsDisplacement(eva))
        {eva.setDeltaMovement(0,eva.getDeltaMovement().y,0);return;}
        if(eva.isNervLogisticsLocked()||eva.isLaunchSequenceActive()||eva.isFirstBattleActive()||com.projectseele.physics.CombatBodyDynamics.active(eva))return;
        Vec3 outward=direction.multiply(1,0,1);if(outward.lengthSqr()<1e-8)return;outward=outward.normalize();
        Vec3 velocity=eva.getDeltaMovement();double desired=Math.min(1.65,.5+strength),current=velocity.dot(outward);
        if(current<desired)eva.setDeltaMovement(velocity.add(outward.scale(desired-current)));
        eva.hasImpulse=true;eva.hurtMarked=true;
    }
    public static void add(LivingEntity actor,long tick,Vec3 direction,float strength,float height)
    {
        if(!Double.isFinite(direction.lengthSqr())||!Float.isFinite(strength)||strength<=0)return;
        var list=HITS.computeIfAbsent(actor,e->new ArrayList<>());list.removeIf(i->tick-i.tick>24);list.add(new Impulse(tick,direction.normalize(),(float)Math.min(1.3,strength),height));if(list.size()>5)list.remove(0);
    }
    public static Pose sample(LivingEntity entity,float partial)
    {
        if(entity instanceof FirstBattleSignals.Actor actor&&actor.firstBattleSignals().active(entity))return new Pose(0,0,0,0);
        var list=HITS.get(entity);if(list==null)return new Pose(0,0,0,0);double p=0,r=0,h=0,e=0;double yaw=Math.toRadians(entity.yBodyRot);Vec3 forward=new Vec3(-Math.sin(yaw),0,Math.cos(yaw)),right=new Vec3(forward.z,0,-forward.x);
        for(var hit:list)
        {
            double t=(entity.level().getGameTime()-hit.tick)+(double)partial;if(t<0||t>=24)continue;
            double shape=CombatMotionR29.recoil(t)*hit.strength;
            p-=shape*hit.direction.dot(forward)*.31;r+=shape*hit.direction.dot(right)*.28;
            // Head lag follows the same force; rear and side hits must not all nod forward.
            h-=CombatMotionR29.recoil(t-1.5)*hit.strength*hit.direction.dot(forward)*(hit.height>.78?.08:.025);
            e=Math.max(e,CombatMotionR29.brace(t)*hit.strength);
        }
        float weight=entity instanceof EvaUnit01Entity eva?(eva.isPilotProne()?.35F:eva.hasLiveActionForRender(partial)?.75F:1):1;
        return new Pose((float)Math.max(-.36,Math.min(.36,p))*weight,(float)Math.max(-.32,Math.min(.32,r))*weight,(float)Math.max(-.16,Math.min(.16,h))*weight,(float)e);
    }
    public static void applyBody(EvaBodyPose.Sample body,EvaUnit01Entity eva,float partial)
    {
        var p=sample(eva,partial);if(p.energy<.0001)return;
        body.rotations.get("torso_lower").rotateX(p.pitch*.25F).rotateZ(p.roll*.25F);body.rotations.get("torso_upper").rotateX(p.pitch*.75F).rotateZ(p.roll*.75F);body.dirty();
        if(eva.getWeapon()!=EvaUnit01Entity.WEAPON_RIFLE)body.rotations.get("head").rotateX(p.pitch*.35F+p.head).rotateZ(p.roll*.35F);
    }
    private EvaImpactResponse() {}
}
