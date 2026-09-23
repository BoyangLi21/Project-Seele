package com.projectseele.entity;

import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;
import org.joml.Vector3f;

/** Shared hand and bone-lance trajectory. The client skin and server contact use the same curve. */
public final class SachielStrike
{
    public static final int JAB=1,PILE=2,HOOK=3,OVERHEAD=4,SHOVE=5,STOMP=6;
    public record Frame(Vec3 hand,Vec3 tip,Vec3 direction,float weight,float extend) {}
    public static int windup(int mode){if(SachielGameplayMotionR32.ready())return switch(mode){case JAB->8;case HOOK->13;case OVERHEAD->20;case SHOVE->9;default->18;};return mode==OVERHEAD?18:mode==PILE?16:mode==SHOVE?10:12;}
    public static int contactStart(int mode){return windup(mode)+4;}
    public static int contactEnd(int mode){if(SachielGameplayMotionR32.ready())return contactStart(mode)+(mode==PILE?8:5);return mode==OVERHEAD?29:mode==PILE?29:mode==SHOVE?21:25;}
    public static int duration(int mode){if(SachielGameplayMotionR32.ready())return switch(mode){case JAB->27;case HOOK->36;case OVERHEAD->48;case SHOVE->32;case STOMP->43;default->47;};return mode==OVERHEAD?52:mode==PILE?48:mode==SHOVE?38:42;}
    public static float prepare(int mode,float age){return (float)CombatMotionR29.ease(age/windup(mode));}
    public static float drive(int mode,float age){return (float)CombatMotionR29.ease((age-windup(mode))/(mode==OVERHEAD?8:7));}
    public static float release(int mode,float age){int at=contactEnd(mode)+2;return (float)CombatMotionR29.ease((age-at)/(duration(mode)-at));}
    public static float weight(int mode,float age){return prepare(mode,age)*(1-release(mode,age));}
    public static boolean bothHands(int mode){return mode==SHOVE||mode==OVERHEAD&&!SachielGameplayMotionR32.ready();}
    public static boolean strikingLeft(int mode){return SachielGameplayMotionR32.ready()?SachielGameplayMotionR32.left(mode):mode==HOOK;}
    public static Vector3f torsoRotation(int mode,float age,boolean upper)
    {
        float c=prepare(mode,age),d=drive(mode,age)*(1-release(mode,age));
        float twist=bothHands(mode)?0:(.20F*c-.48F*d)*(mode==HOOK?-1:1)*(1-release(mode,age));
        float lean=(mode==OVERHEAD?-.16F*c+.41F*d:mode==SHOVE?.20F*d:.12F*d)*(1-release(mode,age));
        return new Vector3f(lean*(upper?.7F:.3F),twist*(upper?.65F:.35F),0);
    }
    private static Matrix4f trunk(SachielEntity actor,float age,float partial)
    {
        Matrix4f result=root(actor,partial);
        for(boolean upper:new boolean[]{false,true})
        {
            float y=(upper?134.979142F:90.41946F)/16;var r=torsoRotation(actor.strikeMode(),age,upper);
            result.translate(0,y,0).rotateZ(r.z).rotateY(r.y).rotateX(r.x).translate(0,-y,0);
        }
        return result;
    }
    public static Matrix4f root(SachielEntity actor,float partial)
    {
        Vec3 p=actor.level().isClientSide?actor.getPosition(partial):actor.position();float yaw=actor.level().isClientSide?net.minecraft.util.Mth.rotLerp(partial,actor.yBodyRotO,actor.yBodyRot):actor.yBodyRot;
        return new Matrix4f().translation(p.toVector3f()).rotateY((float)Math.toRadians(180-yaw)).scale(5);
    }
    private static Vec3 world(Matrix4f root,float x,float y,float z){return new Vec3(root.transformPosition(new Vector3f(x,y,z).div(16)));}
    public static Frame sample(SachielEntity actor,float partial)
    {return sample(actor,actor.strikeAge(partial),partial);}
    public static Frame sample(SachielEntity actor,float age,float partial)
    {
        return sample(actor,age,partial,strikingLeft(actor.strikeMode()));
    }
    public static Frame sample(SachielEntity actor,float age,float partial,boolean left)
    {
        if(SachielGameplayMotionR32.ready())return SachielGameplayMotionR32.contact(actor,age,partial,left);
        int mode=actor.strikeMode();Matrix4f root=trunk(actor,age,partial);boolean hook=mode==HOOK;float side=left?-1:1;
        Vec3 shoulder=world(root,side*40.344577F,172.915088F,0),rest=world(root,side*45.523135F,122.333827F,-42.753209F);
        Vec3 chamber=world(root,side*(mode==OVERHEAD?27:mode==SHOVE?35:hook?61:48),mode==OVERHEAD?230:mode==SHOVE?169:hook?155:162,mode==SHOVE?-14:8);
        Vec3 lateral=world(root,side*16,0,0).subtract(world(root,0,0,0)).normalize();
        Vec3 goal=actor.strikeAim().add(bothHands(mode)?lateral.scale(mode==OVERHEAD?2.4:5):Vec3.ZERO);
        Vec3 direction=goal.subtract(shoulder).normalize();double reach=goal.distanceTo(shoulder);
        Vec3 contact=shoulder.add(direction.scale(Math.min(26.5,Math.max(8,reach-(mode==PILE?8:1)))));
        float prepare=prepare(mode,age),drive=drive(mode,age),returning=release(mode,age);
        Vec3 hand=rest.lerp(chamber,prepare).lerp(contact,drive).lerp(rest,returning);
        if(hook)
        {
            hand=hand.add(lateral.scale(Math.sin(Math.PI*drive)*6*prepare*(1-returning)));
        }
        if(mode==OVERHEAD)direction=contact.subtract(chamber).normalize();
        float extension=mode==PILE?EvaDorsalMechanism.smooth((age-20)/5)*(1-EvaDorsalMechanism.smooth((age-29)/8)):0;
        Vec3 tip=hand.add(direction.scale(extension*Math.min(38,Math.max(2,reach-shoulder.distanceTo(contact)+2))));
        return new Frame(hand,tip,direction,prepare*(1-returning),extension);
    }
    private SachielStrike() {}
}
