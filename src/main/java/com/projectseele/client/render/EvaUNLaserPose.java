package com.projectseele.client.render;
import com.projectseele.entity.*;
import org.joml.*;
import net.minecraft.world.phys.Vec3;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import java.util.*;
public final class EvaUNLaserPose
{
    private record Eye(Vec3 point,long tick) {}
    private static final Map<Integer,Eye> EYES=new HashMap<>();
    public static EvaMotionEngineV2.BoneWrites apply(EvaUnit01Entity eva,BakedGeoModel model,Matrix4f root)
    {
        if(!(eva instanceof EvaPrototypeEntity un)||!un.isEyeLaserActive()||root==null)return EvaMotionEngineV2.BoneWrites.empty();
        var head=model.getBone("head").orElse(null);if(head==null)return EvaMotionEngineV2.BoneWrites.empty();
        EvaRigTransforms.rotate(head,EvaRigTransforms.rotation(EvaRigTransforms.parent(head,root)).invert().mul(EvaUNOptics.orientation(un)));
        var p=EvaRigTransforms.point(head,EvaUNOptics.LENS,root);if(EYES.size()>16)EYES.clear();EYES.put(eva.getId(),new Eye(new Vec3(p.x,p.y,p.z),System.nanoTime()));
        return new EvaMotionEngineV2.BoneWrites(Set.of("head"),Set.of(),"MOTION_ENGINE_LIVE_ACTION");
    }
    public static Vec3 eye(EvaPrototypeEntity un,float partial){var e=EYES.get(un.getId());return e!=null&&System.nanoTime()-e.tick<200_000_000L?e.point:EvaUNOptics.eye(un,partial);}
    private EvaUNLaserPose() {}
}
