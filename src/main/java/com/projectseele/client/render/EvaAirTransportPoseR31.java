package com.projectseele.client.render;

import com.projectseele.entity.*;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import java.util.*;

/** Applied after locomotion, recoil and shutdown so none can stand a carried EVA up. */
final class EvaAirTransportPoseR31
{
    static EvaMotionEngineV2.BoneWrites apply(EvaUnit01Entity eva, BakedGeoModel model, float partial)
    {
        if (!EvaAirTransportR31.active(eva)) return EvaMotionEngineV2.BoneWrites.empty();
        var sample = EvaBodyPose.sample(eva, partial);
        Set<String> changed = new HashSet<>();
        for (String name : sample.rotations.keySet()) model.getBone(name).ifPresent(b ->
        {
            var r = EvaShutdownR30.euler(sample.rotations.get(name));
            var p = sample.positions.get(name);
            b.setRotX(r.x); b.setRotY(r.y); b.setRotZ(r.z);
            b.setPosX(-p.x*16); b.setPosY(p.y*16); b.setPosZ(p.z*16);
            b.setScaleX(1); b.setScaleY(1); b.setScaleZ(1);
            changed.add(name);
        });
        return new EvaMotionEngineV2.BoneWrites(Set.copyOf(changed), Set.copyOf(changed), "MOTION_ENGINE_LIVE_ACTION");
    }
    private EvaAirTransportPoseR31() {}
}
