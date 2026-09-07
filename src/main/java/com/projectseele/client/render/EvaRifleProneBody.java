package com.projectseele.client.render;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import java.util.*;

/** Body and firearm use the same synchronized stance phase, independent of packet/frame cadence. */
final class EvaRifleProneBody
{
    static final Set<String> BONES=Set.of("root","torso_lower","torso_upper","leg_l","leg_r","shin_l","shin_r","foot_l","foot_r");
    private record Pose(Quaternionf rotation,Vector3f position) {}
    private static final Map<Integer,JsonObject> PROFILES=new HashMap<>();
    private static final Map<EvaUnit01Entity,Map<String,Pose>> STANDING=new WeakHashMap<>();

    static void reload(ResourceManager manager)
    {
        PROFILES.clear();STANDING.clear();
        for(int variant=0;variant<3;variant++)
        {
            var resource=manager.getResource(new ResourceLocation(ProjectSeele.MODID,
                    "animations/eva_unit0"+variant+".animation.json"));
            if(resource.isEmpty())continue;
            try(var reader=resource.get().openAsReader())
            {
                PROFILES.put(variant,JsonParser.parseReader(reader).getAsJsonObject()
                        .getAsJsonObject("animations").getAsJsonObject("animation.eva_unit01.prone").getAsJsonObject("bones"));
            }
            catch(Exception failure){ProjectSeele.LOGGER.warn("Rifle prone profile unavailable: {}",variant,failure);}
        }
    }

    private static Vector3f first(JsonElement channel,Vector3f fallback)
    {
        if(channel==null)return fallback;
        if(channel.isJsonObject())channel=channel.getAsJsonObject().entrySet().stream()
                .min(Comparator.comparingDouble(e->Double.parseDouble(e.getKey()))).orElseThrow().getValue();
        var a=channel.getAsJsonArray();return new Vector3f(a.get(0).getAsFloat(),a.get(1).getAsFloat(),a.get(2).getAsFloat());
    }

    static void remember(EvaUnit01Entity entity,BakedGeoModel model)
    {
        Map<String,Pose> poses=new HashMap<>();
        for(String name:BONES)model.getBone(name).ifPresent(b->poses.put(name,
                new Pose(new Quaternionf().rotationZYX(b.getRotZ(),b.getRotY(),b.getRotX()),new Vector3f(b.getPosX(),b.getPosY(),b.getPosZ()))));
        STANDING.put(entity,poses);
    }

    static boolean apply(EvaUnit01Entity entity,BakedGeoModel model,float partial)
    {
        float p=entity.rifleProneBlend(partial);p=p*p*p*(10+p*(-15+6*p));
        if(p<.00001F&&!entity.isPilotProne())return false;
        JsonObject profile=PROFILES.get(entity.getUnitVariant());if(profile==null)return false;
        Map<String,Pose> source=STANDING.getOrDefault(entity,Map.of());
        for(String name:BONES)
        {
            GeoBone bone=model.getBone(name).orElseThrow();var bind=bone.getInitialSnapshot();
            Quaternionf rest=new Quaternionf().rotationZYX(bind.getRotZ(),bind.getRotY(),bind.getRotX());
            Vector3f offset=new Vector3f(bind.getOffsetX(),bind.getOffsetY(),bind.getOffsetZ());
            JsonObject channels=profile.has(name)?profile.getAsJsonObject(name):new JsonObject();
            Quaternionf end=new Quaternionf(rest);
            if(channels.has("rotation"))
            {
                Vector3f v=first(channels.get("rotation"),new Vector3f()).mul((float)(Math.PI/180));
                end.rotationZYX(v.z,-v.y,-v.x);
            }
            Vector3f position=new Vector3f(offset).add(first(channels.get("position"),new Vector3f()));
            Pose start=source.getOrDefault(name,new Pose(rest,offset));
            Quaternionf q=new Quaternionf(start.rotation()).slerp(end,p);
            Vector3f e=EvaMotionEngineV2.motionQuaternionToAuthoredEuler(q);
            bone.setRotX(e.x);bone.setRotY(e.y);bone.setRotZ(e.z);
            Vector3f pos=new Vector3f(start.position()).lerp(position,p);
            bone.setPosX(pos.x);bone.setPosY(pos.y);bone.setPosZ(pos.z);
            bone.setScaleX(1);bone.setScaleY(1);bone.setScaleZ(1);
        }
        return true;
    }
}
