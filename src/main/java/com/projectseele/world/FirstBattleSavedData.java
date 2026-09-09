package com.projectseele.world;

import com.projectseele.entity.FirstBattleSignals;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.StringTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.phys.Vec3;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

/** The directed encounter survives a normal save/reload without spawning replacement actors. */
public final class FirstBattleSavedData extends SavedData
{
    public static final class Encounter
    {
        public UUID eva,angel,pilot;
        public FirstBattleSignals.Spec spec;
        public int age,missingTicks;
        public boolean deathResolved,skipped,observedActors;
        public float originalField,originalHealth;
    }
    public Encounter active;
    public UUID missionOwner,missionAngel;
    public net.minecraft.core.BlockPos missionLastPos;
    public boolean missionCancelRequested;
    public int missionMissingTicks;
    public final Set<UUID> completedPilots=new HashSet<>();
    public static FirstBattleSavedData get(ServerLevel level)
    {
        return level.getDataStorage().computeIfAbsent(FirstBattleSavedData::load,FirstBattleSavedData::new,"projectseele_first_battle_r10");
    }
    public static CompoundTag saveSpec(FirstBattleSignals.Spec spec)
    {
        CompoundTag t=new CompoundTag();t.putDouble("X",spec.origin().x);t.putDouble("Y",spec.origin().y);t.putDouble("Z",spec.origin().z);t.putFloat("Yaw",spec.yaw());t.putFloat("EvaYaw",spec.evaYaw());t.putFloat("AngelYaw",spec.angelYaw());t.putFloat("Distance",spec.initialDistance());t.putFloat("Height",spec.initialHeight());return t;
    }
    public static FirstBattleSignals.Spec loadSpec(CompoundTag t)
    {
        return new FirstBattleSignals.Spec(new Vec3(t.getDouble("X"),t.getDouble("Y"),t.getDouble("Z")),t.getFloat("Yaw"),t.getFloat("EvaYaw"),t.getFloat("AngelYaw"),t.getFloat("Distance"),t.getFloat("Height"));
    }
    private static FirstBattleSavedData load(CompoundTag tag)
    {
        FirstBattleSavedData result=new FirstBattleSavedData();
        if(tag.contains("Active"))
        {
            CompoundTag t=tag.getCompound("Active");Encounter e=new Encounter();e.eva=t.getUUID("Eva");e.angel=t.getUUID("Angel");e.pilot=t.getUUID("Pilot");e.spec=loadSpec(t.getCompound("Spec"));e.age=t.getInt("Age");e.deathResolved=t.getBoolean("DeathResolved");e.skipped=t.getBoolean("Skipped");e.originalField=t.getFloat("OriginalField");e.originalHealth=t.getFloat("OriginalHealth");result.active=e;
        }
        if(tag.hasUUID("MissionOwner"))result.missionOwner=tag.getUUID("MissionOwner");if(tag.hasUUID("MissionAngel"))result.missionAngel=tag.getUUID("MissionAngel");
        if(tag.contains("MissionLastPos"))result.missionLastPos=net.minecraft.core.BlockPos.of(tag.getLong("MissionLastPos"));result.missionCancelRequested=tag.getBoolean("MissionCancelRequested");
        for(var value:tag.getList("CompletedPilots",8))result.completedPilots.add(UUID.fromString(value.getAsString()));return result;
    }
    @Override public CompoundTag save(CompoundTag tag)
    {
        if(active!=null)
        {
            Encounter e=active;CompoundTag t=new CompoundTag();t.putUUID("Eva",e.eva);t.putUUID("Angel",e.angel);t.putUUID("Pilot",e.pilot);t.put("Spec",saveSpec(e.spec));t.putInt("Age",e.age);t.putBoolean("DeathResolved",e.deathResolved);t.putBoolean("Skipped",e.skipped);t.putFloat("OriginalField",e.originalField);t.putFloat("OriginalHealth",e.originalHealth);tag.put("Active",t);
        }
        if(missionOwner!=null)tag.putUUID("MissionOwner",missionOwner);if(missionAngel!=null)tag.putUUID("MissionAngel",missionAngel);
        if(missionLastPos!=null)tag.putLong("MissionLastPos",missionLastPos.asLong());tag.putBoolean("MissionCancelRequested",missionCancelRequested);
        ListTag completed=new ListTag();completedPilots.stream().map(UUID::toString).sorted().forEach(s->completed.add(StringTag.valueOf(s)));tag.put("CompletedPilots",completed);return tag;
    }
}
