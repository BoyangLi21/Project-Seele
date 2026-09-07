package com.projectseele.client.render;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;
import org.joml.Quaternionf;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import java.util.*;

/** Optional private resource-pack retarget; stock animation data is never bundled. */
public final class EvaRifleMocap
{
    private record Clip(double duration, Quaternionf[][] frames) {}
    private static final Map<String,Clip> CLIPS=new HashMap<>();
    private static final Map<EvaUnit01Entity, Filter> FILTERS=new WeakHashMap<>();
    private static final class Filter
    {
        double time=Double.NaN;
        final Quaternionf[] pose={new Quaternionf(),new Quaternionf()};
    }
    public static void reload(ResourceManager manager)
    {
        CLIPS.clear();
        FILTERS.clear();
        var resource=manager.getResource(new ResourceLocation(ProjectSeele.MODID,"motion/rifle_mocap_r04.json"));
        if(resource.isEmpty())return;
        try(var reader=resource.get().openAsReader())
        {
            var clips=JsonParser.parseReader(reader).getAsJsonObject().getAsJsonObject("clips");
            for(var entry:clips.entrySet())
            {
                var d=entry.getValue().getAsJsonObject();var rows=d.getAsJsonArray("frames");
                Quaternionf[][] frames=new Quaternionf[rows.size()][2];
                for(int i=0;i<frames.length;i++)for(int j=0;j<2;j++)
                {
                    var q=rows.get(i).getAsJsonArray().get(j).getAsJsonArray();
                    frames[i][j]=new Quaternionf(q.get(1).getAsFloat(),q.get(2).getAsFloat(),q.get(3).getAsFloat(),q.get(0).getAsFloat()).normalize();
                }
                CLIPS.put(entry.getKey(),new Clip(d.get("duration").getAsDouble(),frames));
            }
            ProjectSeele.LOGGER.info("Private rifle mocap loaded: {}",CLIPS.keySet());
        }
        catch(Exception failure){CLIPS.clear();ProjectSeele.LOGGER.warn("Rifle mocap unavailable",failure);}
    }
    public static void apply(EvaUnit01Entity eva,BakedGeoModel model,float partial)
    {
        boolean moving=eva.isVisuallyMovingForRender();
        Clip clip=CLIPS.get(moving?(eva.isPilotSprinting()?"run":"walk"):"idle");
        if(clip==null||eva.isPilotProne())return;
        double t=moving?EvaMotionEngineV2.rifleGaitPhase(eva):(eva.tickCount+partial)/20D/clip.duration();
        double f=(t-Math.floor(t))*(clip.frames().length-1);
        int i=(int)f,j=Math.min(i+1,clip.frames().length-1);
        float weight=eva.rifleReadyBlend(partial)*(1-eva.rifleProneBlend(partial));
        double time=(eva.tickCount+partial)/20D;
        Filter filter=FILTERS.computeIfAbsent(eva,ignored->new Filter());
        double dt=time-filter.time;
        boolean reset=!Double.isFinite(dt)||dt<0||dt>.5;
        float blend=reset?1:(float)(1-Math.exp(-dt/.09));
        for(int b=0;b<2;b++)
        {
            Quaternionf source=new Quaternionf(clip.frames()[i][b]).slerp(clip.frames()[j][b],(float)(f-i));
            filter.pose[b].slerp(source,blend);
        }
        // Tiger's legs descend from torso_lower. Keep that pelvis and its foot
        // contacts under locomotion authority; retarget captured chest orientation
        // relative to it instead of rotating the whole lower body with the spine.
        var pelvis=model.getBone("torso_lower").orElseThrow();
        var chest=model.getBone("torso_upper").orElseThrow();
        Quaternionf hip=new Quaternionf().rotationZYX(pelvis.getRotZ(),pelvis.getRotY(),pelvis.getRotX());
        Quaternionf target=hip.invert().mul(new Quaternionf(filter.pose[0]).mul(filter.pose[1]));
        Quaternionf q=new Quaternionf().rotationZYX(chest.getRotZ(),chest.getRotY(),chest.getRotX()).slerp(target,weight);
        var e=EvaMotionEngineV2.motionQuaternionToAuthoredEuler(q);
        chest.setRotX(e.x);chest.setRotY(e.y);chest.setRotZ(e.z);
        filter.time=time;
    }
}
