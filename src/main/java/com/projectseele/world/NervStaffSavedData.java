package com.projectseele.world;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;
import java.util.*;

/** Roster identities survive unloading and migration to a dedicated server. */
public final class NervStaffSavedData extends SavedData
{
    private final Map<String,UUID> members=new LinkedHashMap<>();
    public static NervStaffSavedData get(ServerLevel level){return level.getDataStorage().computeIfAbsent(NervStaffSavedData::load,NervStaffSavedData::new,"projectseele_staff_r15");}
    public UUID identity(String id){return members.get(id);}
    public Map<String,UUID> identities(){return Map.copyOf(members);}
    public void record(String id,UUID uuid){members.put(id,uuid);setDirty();}
    public static NervStaffSavedData load(CompoundTag tag)
    {
        var result=new NervStaffSavedData();var entries=tag.getCompound("Members");for(String id:entries.getAllKeys())if(entries.hasUUID(id))result.members.put(id,entries.getUUID(id));return result;
    }
    @Override public CompoundTag save(CompoundTag tag){var entries=new CompoundTag();members.forEach(entries::putUUID);tag.put("Members",entries);return tag;}
}
