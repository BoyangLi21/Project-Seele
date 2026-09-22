package com.projectseele.client.render;

import com.projectseele.entity.*;
import com.projectseele.network.*;
import net.minecraft.client.Minecraft;
import net.minecraft.nbt.*;
import org.joml.Quaternionf;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import java.util.*;

/** Retain the fully composed last live pose; the server persists the pilot's power-loss snapshot. */
final class EvaShutdownPoseR30
{
    private static final Map<EvaUnit01Entity,View> VIEWS=new WeakHashMap<>();
    private static final class View {CompoundTag live=new CompoundTag(),held=new CompoundTag(),entry=new CompoundTag();int mode;long sent=-1,released;}
    private static CompoundTag capture(BakedGeoModel model)
    {
        CompoundTag result=new CompoundTag();for(String name:EvaPoseGraph.contract().boneOrder())model.getBone(name).ifPresent(b->{ListTag v=new ListTag();for(float n:new float[]{b.getRotX(),b.getRotY(),b.getRotZ(),b.getPosX(),b.getPosY(),b.getPosZ(),b.getScaleX(),b.getScaleY(),b.getScaleZ()})v.add(FloatTag.valueOf(n));result.put(name,v);});return result;
    }
    static EvaMotionEngineV2.BoneWrites apply(EvaUnit01Entity eva,BakedGeoModel model,float partial)
    {
        var view=VIEWS.computeIfAbsent(eva,e->new View());int mode=EvaShutdownR30.displayed(eva)?EvaShutdownR30.mode(eva):0;long now=System.nanoTime();
        if(mode!=0)
        {
            if(view.mode==0){view.entry=view.live.isEmpty()?EvaShutdownR30.origin(eva).copy():view.live.copy();view.held=mode==EvaShutdownR30.POWER_LOCK&&!view.live.isEmpty()?view.live.copy():EvaShutdownR30.pose(eva).copy();}
            var mc=Minecraft.getInstance();long stamp=EvaShutdownR30.since(eva);
            if(mode==EvaShutdownR30.POWER_LOCK&&view.sent!=stamp&&mc.player!=null&&mc.player.getRootVehicle()==eva&&!view.held.isEmpty())
            {SeeleNetwork.CHANNEL.sendToServer(new ServerboundEvaFrozenPoseR30(eva.getId(),view.held.copy()));view.sent=stamp;}
            if(!EvaShutdownR30.pose(eva).isEmpty()&&!(mode==EvaShutdownR30.POWER_LOCK&&mc.player!=null&&mc.player.getRootVehicle()==eva))view.held=EvaShutdownR30.pose(eva).copy();
            float blend=EvaShutdownR30.collapse(eva,partial);if(blend<1)write(model,view.entry,1);
            view.mode=mode;view.released=0;return write(model,view.held,blend);
        }
        if(view.mode!=0){view.mode=0;view.released=now;}
        var result=EvaMotionEngineV2.BoneWrites.empty();
        if(view.released!=0&&!eva.isNervLogisticsLocked())
        {float weight=1-EvaDorsalMechanism.smooth((now-view.released)/300_000_000F);if(weight>0)result=write(model,view.held,weight);else view.released=0;}
        if(eva.isPoweredOn()&&!eva.isNervLogisticsLocked())view.live=capture(model);
        return result;
    }
    private static EvaMotionEngineV2.BoneWrites write(BakedGeoModel model,CompoundTag tag,float w)
    {
        Set<String> names=new HashSet<>();for(String name:tag.getAllKeys())model.getBone(name).ifPresent(b->{
            var v=tag.getList(name,Tag.TAG_FLOAT);if(v.size()!=9)return;
            var q=new Quaternionf().rotationZYX(b.getRotZ(),b.getRotY(),b.getRotX()).slerp(new Quaternionf().rotationZYX(v.getFloat(2),v.getFloat(1),v.getFloat(0)),w);var r=EvaShutdownR30.euler(q);
            b.setRotX(r.x);b.setRotY(r.y);b.setRotZ(r.z);b.setPosX(b.getPosX()+(v.getFloat(3)-b.getPosX())*w);b.setPosY(b.getPosY()+(v.getFloat(4)-b.getPosY())*w);b.setPosZ(b.getPosZ()+(v.getFloat(5)-b.getPosZ())*w);
            b.setScaleX(b.getScaleX()+(v.getFloat(6)-b.getScaleX())*w);b.setScaleY(b.getScaleY()+(v.getFloat(7)-b.getScaleY())*w);b.setScaleZ(b.getScaleZ()+(v.getFloat(8)-b.getScaleZ())*w);names.add(name);
        });return new EvaMotionEngineV2.BoneWrites(Set.copyOf(names),Set.copyOf(names),"MOTION_ENGINE_LIVE_ACTION");
    }
    private EvaShutdownPoseR30() {}
}
