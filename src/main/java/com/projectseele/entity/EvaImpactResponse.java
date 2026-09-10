package com.projectseele.entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import java.util.*;

/** Directional damped recoil without stopping the locomotion clock or taking pilot control. */
public final class EvaImpactResponse
{
    private record Impulse(long tick,Vec3 direction,float strength,float height) {}
    private static final Map<LivingEntity,List<Impulse>> HITS=Collections.synchronizedMap(new WeakHashMap<>());
    public record Pose(float pitch,float roll,float head,float energy) {}
    public static void add(LivingEntity actor,long tick,Vec3 direction,float strength,float height)
    {
        var list=HITS.computeIfAbsent(actor,e->new ArrayList<>());list.removeIf(i->tick-i.tick>24);list.add(new Impulse(tick,direction,(float)Math.min(1.3,strength),height));if(list.size()>5)list.remove(0);
    }
    public static Pose sample(LivingEntity entity,float partial)
    {
        if(entity instanceof FirstBattleSignals.Actor actor&&actor.firstBattleSignals().active(entity))return new Pose(0,0,0,0);
        var list=HITS.get(entity);if(list==null)return new Pose(0,0,0,0);double p=0,r=0,h=0,e=0;double yaw=Math.toRadians(entity.yBodyRot);Vec3 forward=new Vec3(-Math.sin(yaw),0,Math.cos(yaw)),right=new Vec3(forward.z,0,-forward.x);
        for(var hit:list)
        {
            double t=(entity.level().getGameTime()+partial-hit.tick)/20D;if(t<0||t>1.2)continue;
            double shape=Math.sin(t*18)*Math.exp(-t*7.5)*2.3*hit.strength;
            p+=shape*hit.direction.dot(forward)*.115;r-=shape*hit.direction.dot(right)*.105;h+=shape*(hit.height>.78?1.4:.45)*.065;e=Math.max(e,Math.abs(shape));
        }
        float weight=entity instanceof EvaUnit01Entity eva?(eva.isPilotProne()?.3F:eva.hasLiveActionForRender(partial)?.4F:1):1;
        return new Pose((float)Math.max(-.20,Math.min(.20,p))*weight,(float)Math.max(-.20,Math.min(.20,r))*weight,(float)Math.max(-.16,Math.min(.16,h))*weight,(float)e);
    }
    public static void applyBody(EvaBodyPose.Sample body,EvaUnit01Entity eva,float partial)
    {
        var p=sample(eva,partial);if(p.energy<.0001)return;
        body.rotations.get("torso_lower").rotateX(p.pitch*.25F).rotateZ(p.roll*.25F);body.rotations.get("torso_upper").rotateX(p.pitch*.75F).rotateZ(p.roll*.75F);body.dirty();
        if(eva.getWeapon()!=EvaUnit01Entity.WEAPON_RIFLE)body.rotations.get("head").rotateX(p.pitch*.35F+p.head).rotateZ(p.roll*.35F);
    }
    private EvaImpactResponse() {}
}
