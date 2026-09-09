package com.projectseele.client.render;

import com.projectseele.entity.FirstBattleClip;
import com.projectseele.entity.FirstBattleSignals;
import net.minecraft.world.entity.Entity;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import java.util.LinkedHashSet;
import java.util.Set;

/** A single pose writer for both actors of the authored battle. */
public final class FirstBattlePoseRenderer
{
    public static EvaMotionEngineV2.BoneWrites apply(Entity entity,BakedGeoModel model,float partial)
    {
        if(!(entity instanceof FirstBattleSignals.Actor actor)||!actor.firstBattleSignals().active(entity)||!FirstBattleClip.ready())return EvaMotionEngineV2.BoneWrites.empty();
        var pose=FirstBattleClip.pose(actor.isFirstBattleEva(),actor.firstBattleSignals().time(entity,partial));
        Set<String> rotations=new LinkedHashSet<>(),positions=new LinkedHashSet<>();
        for(int i=0;i<pose.names().length;i++)
        {
            String name=pose.names()[i];var bone=model.getBone(name).orElse(null);if(bone==null)continue;
            var euler=EvaMotionEngineV2.motionQuaternionToAuthoredEuler(pose.rotations()[i]);var p=pose.positions()[i];
            bone.setRotX(-euler.x);bone.setRotY(-euler.y);bone.setRotZ(euler.z);bone.setPosX(p.x);bone.setPosY(p.y);bone.setPosZ(p.z);
            rotations.add(name);positions.add(name);
        }
        return new EvaMotionEngineV2.BoneWrites(Set.copyOf(rotations),Set.copyOf(positions),EvaMotionEngineV2.OWNER_LIVE_ACTION);
    }
    private FirstBattlePoseRenderer() {}
}
