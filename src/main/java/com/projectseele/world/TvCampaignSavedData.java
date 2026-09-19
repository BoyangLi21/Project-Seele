package com.projectseele.world;

import net.minecraft.core.BlockPos;
import net.minecraft.nbt.*;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;
import java.util.*;

/** One cooperative TV chronology per world; replays use the old independent system. */
public final class TvCampaignSavedData extends SavedData
{
    public int chapter;
    public UUID owner, angel;
    public UUID pilotEva, pilotPlug;
    public boolean wasRiding, resumePending;
    public int resumeTicks;
    public String active = "", phase = "idle", notice = "";
    public BlockPos lastPosition;
    public final List<String> completed = new ArrayList<>();
    public static TvCampaignSavedData get(ServerLevel level)
    { return level.getDataStorage().computeIfAbsent(TvCampaignSavedData::load, TvCampaignSavedData::new, "projectseele_tv_campaign_r24"); }
    public static TvCampaignSavedData load(CompoundTag tag)
    {
        var data = new TvCampaignSavedData();
        data.chapter = Math.max(0, Math.min(tag.getInt("Chapter"), TvCampaignCatalog.CHAPTERS.size()));
        if (tag.hasUUID("Owner")) data.owner = tag.getUUID("Owner");
        if (tag.hasUUID("Angel")) data.angel = tag.getUUID("Angel");
        if (tag.hasUUID("PilotEva")) data.pilotEva=tag.getUUID("PilotEva");
        if (tag.hasUUID("PilotPlug")) data.pilotPlug=tag.getUUID("PilotPlug");
        data.wasRiding=tag.getBoolean("WasRiding");
        data.active = tag.getString("Active"); data.phase = tag.getString("Phase"); data.notice = tag.getString("Notice");
        if (tag.contains("LastPosition")) data.lastPosition = BlockPos.of(tag.getLong("LastPosition"));
        for (var entry : tag.getList("Completed", Tag.TAG_STRING)) data.completed.add(entry.getAsString());
        data.resumePending=!data.active.isEmpty()&&data.wasRiding&&data.pilotEva!=null&&data.pilotPlug!=null;
        return data;
    }
    @Override public CompoundTag save(CompoundTag tag)
    {
        tag.putInt("Chapter", chapter); tag.putString("Active", active); tag.putString("Phase", phase); tag.putString("Notice", notice);
        if (owner != null) tag.putUUID("Owner", owner); if (angel != null) tag.putUUID("Angel", angel);
        if(pilotEva!=null)tag.putUUID("PilotEva",pilotEva);if(pilotPlug!=null)tag.putUUID("PilotPlug",pilotPlug);tag.putBoolean("WasRiding",wasRiding);
        if (lastPosition != null) tag.putLong("LastPosition", lastPosition.asLong());
        var list = new ListTag(); completed.forEach(id -> list.add(StringTag.valueOf(id))); tag.put("Completed", list); return tag;
    }
    public void clear(String reason)
    { owner = null; angel = null; pilotEva=pilotPlug=null;wasRiding=resumePending=false;resumeTicks=0;active = ""; phase = "idle"; lastPosition = null; notice = reason; setDirty(); }
    public boolean finish(String id, UUID pilot, UUID target)
    {
        if (!active.equals(id) || owner == null || !owner.equals(pilot) || angel == null || !angel.equals(target)
                || !TvCampaignCatalog.at(chapter).id().equals(id) || completed.contains(id)) return false;
        completed.add(id); chapter++; clear("作战记录已归档。请先回收机体，再查看下一份简报。"); return true;
    }
}
