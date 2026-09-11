package com.projectseele.client.render;

import com.google.gson.JsonParser;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.NervStaffEntity;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import java.util.*;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

/** Optional private artist skins, with the actual arm model and stable per-person variants. */
public final class NervStaffSkins
{
    public record Skin(ResourceLocation texture,boolean slim) {}
    private static final Map<String,List<Skin>> CATALOG=new HashMap<>();
    private static boolean loaded;
    public static void reset(){loaded=false;CATALOG.clear();}
    private static void load()
    {
        if(loaded)return;loaded=true;var manager=Minecraft.getInstance().getResourceManager();
        var resource=manager.getResource(new ResourceLocation(ProjectSeele.MODID,"staff/skins.json"));if(resource.isEmpty())return;
        try(var reader=new InputStreamReader(resource.get().open(),StandardCharsets.UTF_8))
        {
            var root=JsonParser.parseReader(reader).getAsJsonObject();
            for(var entry:root.entrySet())
            {
                List<Skin> skins=new ArrayList<>();
                for(var row:entry.getValue().getAsJsonArray())
                {
                    var data=row.getAsJsonObject();String path=data.get("texture").getAsString();
                    if(!path.matches("textures/entity/[a-z0-9_]+\\.png"))throw new IllegalArgumentException("Invalid local skin asset path");
                    var texture=new ResourceLocation(ProjectSeele.MODID,path);if(manager.getResource(texture).isEmpty())throw new IllegalArgumentException("Missing artist skin: "+path);
                    skins.add(new Skin(texture,data.has("slim")&&data.get("slim").getAsBoolean()));
                }
                if(skins.isEmpty())throw new IllegalArgumentException("Empty skin collection");CATALOG.put(entry.getKey(),List.copyOf(skins));
            }
            ProjectSeele.LOGGER.info("Private staff skin catalog loaded: {} role/identity collections",CATALOG.size());
        }
        catch(Exception e){CATALOG.clear();ProjectSeele.LOGGER.error("Private staff skin catalog rejected",e);}
    }
    public static Skin forStaff(NervStaffEntity entity)
    {
        load();var skins=CATALOG.getOrDefault("id:"+entity.memberId(),CATALOG.get(entity.skin()));
        if(skins!=null)return skins.get(Math.floorMod(entity.getUUID().hashCode(),skins.size()));
        return new Skin(new ResourceLocation(ProjectSeele.MODID,"textures/entity/staff_"+entity.skin()+".png"),Set.of("misato","ritsuko","maya").contains(entity.skin()));
    }
    private NervStaffSkins() {}
}
