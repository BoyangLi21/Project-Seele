package com.projectseele.client.render;

import com.projectseele.physics.CombatBodyDynamics;
import net.minecraft.world.entity.LivingEntity;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import java.util.HashSet;
import java.util.Set;

public final class PhysicalBodyRenderer
{
    public static EvaMotionEngineV2.BoneWrites apply(LivingEntity entity,BakedGeoModel model,float partial)
    {
        return write(CombatBodyDynamics.sample(entity,partial),model);
    }
    public static EvaMotionEngineV2.BoneWrites write(com.projectseele.entity.EvaBodyPose.Sample pose,BakedGeoModel model)
    {
        Set<String> names=new HashSet<>();
        for(String n:pose.rig.keySet())model.getBone(n).ifPresent(b->{EvaRigTransforms.rotate(b,pose.rotations.get(n));var p=pose.positions.get(n);b.setPosX(-p.x*16);b.setPosY(p.y*16);b.setPosZ(p.z*16);b.setScaleX(1);b.setScaleY(1);b.setScaleZ(1);names.add(n);});
        return new EvaMotionEngineV2.BoneWrites(Set.copyOf(names),Set.copyOf(names),"MOTION_ENGINE_LIVE_ACTION");
    }
    private PhysicalBodyRenderer(){}
}
