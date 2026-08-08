package com.projectseele.world;

import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import javax.annotation.Nullable;

import com.projectseele.ProjectSeele;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/** Persistent identity and interlock state for each physical weapon elevator. */
public final class EvaWeaponLiftSavedData extends SavedData
{
    private static final String DATA_NAME = "projectseele_weapon_lifts";
    private static final int DATA_VERSION = 2;

    private final Map<Long, LiftEntry> lifts = new LinkedHashMap<>();

    public static EvaWeaponLiftSavedData get(ServerLevel level)
    {
        return level.getDataStorage().computeIfAbsent(
                EvaWeaponLiftSavedData::load,
                EvaWeaponLiftSavedData::new, DATA_NAME);
    }

    public static EvaWeaponLiftSavedData load(CompoundTag tag)
    {
        EvaWeaponLiftSavedData data = new EvaWeaponLiftSavedData();
        int version = tag.contains("Version", Tag.TAG_INT)
                ? tag.getInt("Version") : 1;
        if (version < 1 || version > DATA_VERSION)
        {
            ProjectSeele.LOGGER.error(
                    "Unsupported EVA weapon-lift data version {}; fail closed",
                    version);
            return data;
        }
        ListTag list = tag.getList("Lifts", Tag.TAG_COMPOUND);
        for (int index = 0; index < list.size(); index++)
        {
            CompoundTag item = list.getCompound(index);
            if (!item.hasUUID("Platform"))
            {
                continue;
            }
            long rack = item.getLong("Rack");
            BlockPos bottom = BlockPos.of(item.getLong("Bottom"));
            LiftEntry entry = new LiftEntry(
                    BlockPos.of(rack), bottom,
                    BlockPos.of(item.getLong("Top")),
                    Math.max(0, Math.min(2, item.getInt("Variant"))),
                    item.getInt("Weapon"), State.parse(item.getString("State")),
                    Math.max(0, item.getInt("Ticks")),
                    Math.max(0.0D, item.getDouble("Velocity")),
                    item.getUUID("Platform"),
                    item.hasUUID("WeaponEntity")
                            ? item.getUUID("WeaponEntity") : null,
                    item.hasUUID("Eva") ? item.getUUID("Eva") : null,
                    Math.max(0L, item.getLong("Nonce")),
                    item.contains("PlatformLast")
                            ? BlockPos.of(item.getLong("PlatformLast"))
                            : bottom,
                    item.contains("WeaponLast")
                            ? BlockPos.of(item.getLong("WeaponLast")) : null,
                    Math.max(0, item.getInt("PlatformUnresolvedTicks")),
                    Math.max(0, item.getInt("WeaponUnresolvedTicks")));
            data.lifts.put(rack, entry);
        }
        return data;
    }

    public Optional<LiftEntry> entry(BlockPos rack)
    {
        return Optional.ofNullable(this.lifts.get(rack.asLong()));
    }

    public Collection<LiftEntry> entries()
    {
        return ListTagCopy.copy(this.lifts.values());
    }

    public void put(LiftEntry entry)
    {
        this.lifts.put(entry.rack().asLong(), entry);
        this.setDirty();
    }

    public void remove(BlockPos rack)
    {
        if (this.lifts.remove(rack.asLong()) != null)
        {
            this.setDirty();
        }
    }

    @Override
    public CompoundTag save(CompoundTag tag)
    {
        tag.putInt("Version", DATA_VERSION);
        ListTag list = new ListTag();
        for (LiftEntry entry : this.lifts.values())
        {
            CompoundTag item = new CompoundTag();
            item.putLong("Rack", entry.rack().asLong());
            item.putLong("Bottom", entry.bottom().asLong());
            item.putLong("Top", entry.top().asLong());
            item.putInt("Variant", entry.variant());
            item.putInt("Weapon", entry.weapon());
            item.putString("State", entry.state().name());
            item.putInt("Ticks", entry.ticks());
            item.putDouble("Velocity", entry.velocity());
            item.putUUID("Platform", entry.platformId());
            if (entry.weaponEntityId() != null)
            {
                item.putUUID("WeaponEntity", entry.weaponEntityId());
            }
            if (entry.evaId() != null)
            {
                item.putUUID("Eva", entry.evaId());
            }
            item.putLong("Nonce", entry.nonce());
            item.putLong("PlatformLast", entry.platformLast().asLong());
            if (entry.weaponLast() != null)
            {
                item.putLong("WeaponLast", entry.weaponLast().asLong());
            }
            item.putInt("PlatformUnresolvedTicks",
                    entry.platformUnresolvedTicks());
            item.putInt("WeaponUnresolvedTicks",
                    entry.weaponUnresolvedTicks());
            list.add(item);
        }
        tag.put("Lifts", list);
        return tag;
    }

    public enum State
    {
        RACKED_UNDERGROUND,
        LOADING_LOCKED,
        ASCENDING,
        TOP_DOCKING,
        PRESENTED_LOCKED,
        GRIP_VERIFY,
        HANDOFF_TO_EVA,
        RELEASED_TO_EVA,
        RETURNING_EMPTY,
        DEPLOYED_TO_EVA,
        ASCENDING_EMPTY_FOR_RETURN,
        RETURN_DOCKING,
        HANDOFF_TO_PLATFORM,
        DESCENDING_WITH_WEAPON,
        EMERGENCY_STOP,
        FAULT;

        private static State parse(String value)
        {
            try
            {
                return State.valueOf(value);
            }
            catch (IllegalArgumentException ignored)
            {
                return FAULT;
            }
        }
    }

    public record LiftEntry(BlockPos rack, BlockPos bottom, BlockPos top,
                            int variant, int weapon, State state, int ticks,
                            double velocity, UUID platformId,
                            @Nullable UUID weaponEntityId,
                            @Nullable UUID evaId, long nonce,
                            BlockPos platformLast,
                            @Nullable BlockPos weaponLast,
                            int platformUnresolvedTicks,
                            int weaponUnresolvedTicks)
    {
        public LiftEntry withState(State next, int nextTicks,
                                   double nextVelocity)
        {
            return new LiftEntry(this.rack, this.bottom, this.top,
                    this.variant, this.weapon, next, nextTicks,
                    nextVelocity, this.platformId, this.weaponEntityId,
                    this.evaId, this.nonce, this.platformLast,
                    this.weaponLast, this.platformUnresolvedTicks,
                    this.weaponUnresolvedTicks);
        }

        public LiftEntry moving(State next, int nextTicks,
                                double nextVelocity)
        {
            return new LiftEntry(this.rack, this.bottom, this.top,
                    this.variant, this.weapon, next, nextTicks,
                    nextVelocity, this.platformId, this.weaponEntityId,
                    this.evaId, this.nonce, this.platformLast,
                    this.weaponLast, this.platformUnresolvedTicks,
                    this.weaponUnresolvedTicks);
        }

        public LiftEntry withWeapon(UUID id)
        {
            return new LiftEntry(this.rack, this.bottom, this.top,
                    this.variant, this.weapon, this.state, this.ticks,
                    this.velocity, this.platformId, id, this.evaId,
                    this.nonce, this.platformLast, this.weaponLast,
                    this.platformUnresolvedTicks,
                    this.weaponUnresolvedTicks);
        }

        public LiftEntry withEva(@Nullable UUID id)
        {
            return new LiftEntry(this.rack, this.bottom, this.top,
                    this.variant, this.weapon, this.state, this.ticks,
                    this.velocity, this.platformId, this.weaponEntityId, id,
                    this.nonce, this.platformLast, this.weaponLast,
                    this.platformUnresolvedTicks,
                    this.weaponUnresolvedTicks);
        }

        public LiftEntry observedPlatform(BlockPos position)
        {
            return new LiftEntry(this.rack, this.bottom, this.top,
                    this.variant, this.weapon, this.state, this.ticks,
                    this.velocity, this.platformId, this.weaponEntityId,
                    this.evaId, this.nonce, position.immutable(),
                    this.weaponLast, 0, this.weaponUnresolvedTicks);
        }

        public LiftEntry observedWeapon(BlockPos position)
        {
            return new LiftEntry(this.rack, this.bottom, this.top,
                    this.variant, this.weapon, this.state, this.ticks,
                    this.velocity, this.platformId, this.weaponEntityId,
                    this.evaId, this.nonce, this.platformLast,
                    position.immutable(), this.platformUnresolvedTicks, 0);
        }

        public LiftEntry missingPlatformTick()
        {
            return new LiftEntry(this.rack, this.bottom, this.top,
                    this.variant, this.weapon, this.state, this.ticks,
                    this.velocity, this.platformId, this.weaponEntityId,
                    this.evaId, this.nonce, this.platformLast,
                    this.weaponLast, this.platformUnresolvedTicks + 1,
                    this.weaponUnresolvedTicks);
        }

        public LiftEntry missingWeaponTick()
        {
            return new LiftEntry(this.rack, this.bottom, this.top,
                    this.variant, this.weapon, this.state, this.ticks,
                    this.velocity, this.platformId, this.weaponEntityId,
                    this.evaId, this.nonce, this.platformLast,
                    this.weaponLast, this.platformUnresolvedTicks,
                    this.weaponUnresolvedTicks + 1);
        }
    }

    /** Avoids exposing the mutable map view to the tick loop. */
    private static final class ListTagCopy
    {
        private ListTagCopy() {}

        private static <T> Collection<T> copy(Collection<T> source)
        {
            return java.util.List.copyOf(source);
        }
    }
}
