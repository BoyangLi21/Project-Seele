package com.projectseele.entity;

import com.projectseele.config.SeeleConfig;
import com.projectseele.registry.ModSounds;
import net.minecraft.network.syncher.*;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;

/** Roar and feral strikes share the ordinary mesh/contact path, not instant damage. */
public final class EvaBerserkMotionR34
{
    private static final EntityDataAccessor<Integer> AGE=SynchedEntityData.defineId(EvaUnit01Entity.class,EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> KIND=SynchedEntityData.defineId(EvaUnit01Entity.class,EntityDataSerializers.INT);
    private static final EntityDataAccessor<Float> YAW=SynchedEntityData.defineId(EvaUnit01Entity.class,EntityDataSerializers.FLOAT);
    private static final com.projectseele.util.WeakIdentityMap<EvaUnit01Entity,Stroke> STROKES=new com.projectseele.util.WeakIdentityMap<>();
    private static final class Stroke {LivingEntity victim;Vec3 previous;boolean hit;}
    public static boolean bootstrap(){return true;}
    public static void clear(EvaUnit01Entity e){e.getEntityData().set(AGE,-1);STROKES.remove(e);}
    public static void define(SynchedEntityData d){d.define(AGE,-1);d.define(KIND,0);d.define(YAW,0F);}
    public static boolean active(EvaUnit01Entity e){return e.isBerserk()&&EvaGameplayMotionR32.directed(e)&&e.getEntityData().get(AGE)>=0;}
    public static boolean striking(EvaUnit01Entity e){return active(e)&&e.getEntityData().get(KIND)>1;}
    public static String name(EvaUnit01Entity e){return switch(e.getEntityData().get(KIND)){case 2->"berserk_l";case 3->"berserk_r";default->"berserk_roar";};}
    public static int duration(EvaUnit01Entity e){return e.getEntityData().get(KIND)==1?70:26;}
    public static float phase(EvaUnit01Entity e,float partial){return Mth.clamp((e.getEntityData().get(AGE)+partial)/duration(e),0,1);}
    public static void begin(EvaUnit01Entity e,int kind,LivingEntity target)
    {
        if(e.level().isClientSide||!EvaGameplayMotionR32.directed(e)||active(e))return;
        EvaGameplayMotionR32.beginAction(e);e.getEntityData().set(KIND,kind);e.getEntityData().set(AGE,0);e.getEntityData().set(YAW,e.getYRot());
        Stroke s=new Stroke();s.victim=target;STROKES.put(e,s);
    }
    public static void tick(EvaUnit01Entity e)
    {
        if(!active(e)||e.level().isClientSide)return;
        e.getNavigation().stop();e.setDeltaMovement(0,e.getDeltaMovement().y,0);
        float yaw=e.getEntityData().get(YAW);e.setYRot(yaw);e.yBodyRot=e.yHeadRot=yaw;
        if(CombatFeelR31.hitPaused(e))return;
        int age=e.getEntityData().get(AGE)+1;e.getEntityData().set(AGE,age);
        if(striking(e))
        {
            float now=phase(e,0),before=Math.max(0,now-1F/duration(e));String clip=name(e),side=clip.endsWith("l")?"l":"r";
            e.moveCombatRootR34(EvaGameplayMotionR32.root(e,clip,now).subtract(EvaGameplayMotionR32.root(e,clip,before)));
            var state=STROKES.get(e);Vec3 hand=EvaGameplayMotionR32.hand(e,side,0);
            if(age==7)EvaMovementSounds.swing(e,3);
            if(state!=null&&state.victim!=null&&state.victim.isAlive()&&!state.hit&&now>=.27F&&now<=.65F)
            {
                Vec3 from=state.previous==null?hand:state.previous;
                var contact=com.projectseele.physics.CombatBodyContacts.clip(state.victim,from,hand,1.8);
                boolean unobstructed=e.level().clip(new net.minecraft.world.level.ClipContext(from,hand,net.minecraft.world.level.ClipContext.Block.COLLIDER,net.minecraft.world.level.ClipContext.Fluid.NONE,e)).getType()==net.minecraft.world.phys.HitResult.Type.MISS;
                if(unobstructed&&contact.isPresent())
                {
                    float multiplier=SeeleConfig.COMMON_SPEC.isLoaded()?SeeleConfig.EVA_BERSERK_DAMAGE_MULTIPLIER.get().floatValue():2.5F;
                    Vec3 point=contact.orElse(hand),direction=state.victim.position().subtract(e.position()).normalize();
                    state.hit=com.projectseele.event.EvaHitFeedback.hurt(state.victim,e.damageSources().mobAttack(e),20*multiplier,point,direction);
                    if(state.hit)EvaMovementSounds.play(e,point,ModSounds.EVA_IMPACT.get(),5,1);
                }
            }
            if(state!=null)state.previous=hand;
        }
        if(age>=duration(e)){e.getEntityData().set(AGE,-1);STROKES.remove(e);}
    }
    private EvaBerserkMotionR34(){}
}
