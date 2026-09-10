package com.projectseele.entity;

import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;
import org.joml.Vector3f;

/** Shared hand and bone-lance trajectory. The client skin and server contact use the same curve. */
public final class SachielStrike
{
    public record Frame(Vec3 hand,Vec3 tip,Vec3 direction,float weight,float extend) {}
    public static Matrix4f root(SachielEntity actor,float partial)
    {
        Vec3 p=actor.level().isClientSide?actor.getPosition(partial):actor.position();float yaw=actor.level().isClientSide?net.minecraft.util.Mth.rotLerp(partial,actor.yBodyRotO,actor.yBodyRot):actor.yBodyRot;
        return new Matrix4f().translation(p.toVector3f()).rotateY((float)Math.toRadians(180-yaw)).scale(5);
    }
    private static Vec3 world(Matrix4f root,float x,float y,float z){return new Vec3(root.transformPosition(new Vector3f(x,y,z).div(16)));}
    public static Frame sample(SachielEntity actor,float partial)
    {
        float age=actor.strikeAge(partial);Matrix4f root=root(actor,partial);Vec3 shoulder=world(root,40.344577F,172.915088F,0),rest=world(root,45.523135F,122.333827F,-42.753209F),chamber=world(root,48,162,2);
        Vec3 direction=actor.strikeAim().subtract(shoulder).normalize();double reach=actor.strikeAim().distanceTo(shoulder);
        Vec3 contact=shoulder.add(direction.scale(Math.min(27,Math.max(8,reach-(actor.strikeMode()==2?8:1)))));
        float prepare=EvaDorsalMechanism.smooth(age/12),drive=EvaDorsalMechanism.smooth((age-12)/6),returning=EvaDorsalMechanism.smooth((age-25)/17);
        Vec3 hand=rest.lerp(chamber,prepare).lerp(contact,drive).lerp(rest,returning);
        float extension=actor.strikeMode()==2?EvaDorsalMechanism.smooth((age-18)/5)*(1-EvaDorsalMechanism.smooth((age-26)/8)):0;
        Vec3 tip=hand.add(direction.scale(extension*Math.min(38,Math.max(2,reach-shoulder.distanceTo(contact)+2))));
        return new Frame(hand,tip,direction,prepare*(1-returning),extension);
    }
    private SachielStrike() {}
}
