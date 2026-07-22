package com.projectseele.world;

import java.util.EnumMap;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import com.projectseele.ProjectSeele;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.saveddata.SavedData;

/** Persistent, non-enforcing multiplayer assignments for NERV operations. */
public final class NervCrewSavedData extends SavedData
{
    private static final String DATA_NAME = "projectseele_nerv_crew";
    private static final int DATA_VERSION = 1;

    private final Map<Station, Assignment> assignments =
            new EnumMap<>(Station.class);

    public static NervCrewSavedData get(MinecraftServer server)
    {
        ServerLevel overworld = server.overworld();
        return overworld.getDataStorage().computeIfAbsent(
                NervCrewSavedData::load, NervCrewSavedData::new, DATA_NAME);
    }

    public static NervCrewSavedData load(CompoundTag tag)
    {
        NervCrewSavedData data = new NervCrewSavedData();
        int version = tag.contains("Version", Tag.TAG_INT)
                ? tag.getInt("Version") : 1;
        if (version != DATA_VERSION)
        {
            ProjectSeele.LOGGER.error(
                    "Unsupported NERV crew SavedData version {}; ignoring assignments",
                    version);
            return data;
        }
        ListTag entries = tag.getList("Assignments", Tag.TAG_COMPOUND);
        for (int index = 0; index < entries.size(); index++)
        {
            CompoundTag entry = entries.getCompound(index);
            Optional<Station> station = Station.parse(entry.getString("Station"));
            if (station.isEmpty() || !entry.hasUUID("Player"))
            {
                continue;
            }
            Assignment assignment = new Assignment(entry.getUUID("Player"),
                    entry.getString("Name"), entry.getBoolean("Ready"));
            data.assignments.put(station.get(), assignment);
        }
        return data;
    }

    public ClaimResult claim(Station station, ServerPlayer player)
    {
        Assignment occupied = this.assignments.get(station);
        if (occupied != null && !occupied.playerId().equals(player.getUUID()))
        {
            return ClaimResult.OCCUPIED;
        }
        Optional<Station> previous = stationFor(player.getUUID());
        if (previous.isPresent() && previous.get() == station)
        {
            Assignment refreshed = new Assignment(player.getUUID(),
                    player.getGameProfile().getName(), occupied != null && occupied.ready());
            if (!refreshed.equals(occupied))
            {
                this.assignments.put(station, refreshed);
                this.setDirty();
            }
            return ClaimResult.ALREADY_ASSIGNED;
        }
        previous.ifPresent(this.assignments::remove);
        this.assignments.put(station, new Assignment(player.getUUID(),
                player.getGameProfile().getName(), false));
        this.setDirty();
        return ClaimResult.CLAIMED;
    }

    public Optional<Station> release(UUID playerId)
    {
        Optional<Station> station = stationFor(playerId);
        if (station.isPresent())
        {
            this.assignments.remove(station.get());
            this.setDirty();
        }
        return station;
    }

    public boolean setReady(UUID playerId, boolean ready)
    {
        Optional<Station> station = stationFor(playerId);
        if (station.isEmpty())
        {
            return false;
        }
        Assignment current = this.assignments.get(station.get());
        if (current.ready() != ready)
        {
            this.assignments.put(station.get(), current.withReady(ready));
            this.setDirty();
        }
        return true;
    }

    public Optional<Assignment> clear(Station station)
    {
        Assignment removed = this.assignments.remove(station);
        if (removed != null)
        {
            this.setDirty();
        }
        return Optional.ofNullable(removed);
    }

    public Optional<Assignment> assignment(Station station)
    {
        return Optional.ofNullable(this.assignments.get(station));
    }

    public Optional<Station> stationFor(UUID playerId)
    {
        return this.assignments.entrySet().stream()
                .filter(entry -> entry.getValue().playerId().equals(playerId))
                .map(Map.Entry::getKey).findFirst();
    }

    public CrewOverview overview(MinecraftServer server)
    {
        int online = 0;
        int ready = 0;
        int onlineReady = 0;
        for (Assignment assignment : this.assignments.values())
        {
            boolean connected = server.getPlayerList()
                    .getPlayer(assignment.playerId()) != null;
            if (connected)
            {
                online++;
            }
            if (assignment.ready())
            {
                ready++;
                if (connected)
                {
                    onlineReady++;
                }
            }
        }
        return new CrewOverview(this.assignments.size(), online, ready,
                onlineReady);
    }

    @Override
    public CompoundTag save(CompoundTag tag)
    {
        tag.putInt("Version", DATA_VERSION);
        ListTag entries = new ListTag();
        for (Map.Entry<Station, Assignment> value : this.assignments.entrySet())
        {
            CompoundTag entry = new CompoundTag();
            entry.putString("Station", value.getKey().id());
            entry.putUUID("Player", value.getValue().playerId());
            entry.putString("Name", value.getValue().playerName());
            entry.putBoolean("Ready", value.getValue().ready());
            entries.add(entry);
        }
        tag.put("Assignments", entries);
        return tag;
    }

    public enum Station
    {
        COMMANDER("commander", "COMMANDER", "CMD"),
        OPERATIONS("operations", "OPERATIONS", "OPS"),
        MAGI("magi", "MAGI", "MAGI"),
        UNIT_00("unit00", "EVA-00 PILOT", "U00"),
        UNIT_01("unit01", "EVA-01 PILOT", "U01"),
        UNIT_02("unit02", "EVA-02 PILOT", "U02");

        private final String id;
        private final String label;
        private final String shortLabel;

        Station(String id, String label, String shortLabel)
        {
            this.id = id;
            this.label = label;
            this.shortLabel = shortLabel;
        }

        public String id()
        {
            return this.id;
        }

        public String label()
        {
            return this.label;
        }

        public String shortLabel()
        {
            return this.shortLabel;
        }

        public static Optional<Station> parse(String raw)
        {
            if (raw == null)
            {
                return Optional.empty();
            }
            String normalized = raw.toLowerCase(Locale.ROOT)
                    .replace("-", "").replace("_", "");
            return switch (normalized)
            {
                case "commander", "command", "cmd" -> Optional.of(COMMANDER);
                case "operations", "operation", "ops" -> Optional.of(OPERATIONS);
                case "magi" -> Optional.of(MAGI);
                case "unit00", "eva00", "00", "rei" -> Optional.of(UNIT_00);
                case "unit01", "eva01", "01", "shinji" -> Optional.of(UNIT_01);
                case "unit02", "eva02", "02", "asuka" -> Optional.of(UNIT_02);
                default -> Optional.empty();
            };
        }
    }

    public enum ClaimResult
    {
        CLAIMED,
        ALREADY_ASSIGNED,
        OCCUPIED
    }

    public record Assignment(UUID playerId, String playerName, boolean ready)
    {
        public Assignment
        {
            if (playerName == null || playerName.isBlank())
            {
                playerName = "UNKNOWN";
            }
            else if (playerName.length() > 32)
            {
                playerName = playerName.substring(0, 32);
            }
        }

        public Assignment withReady(boolean value)
        {
            return new Assignment(this.playerId, this.playerName, value);
        }
    }

    public record CrewOverview(int assigned, int online, int ready,
                               int onlineReady)
    {
        public boolean allAssignedOnlineReady()
        {
            return this.assigned > 0 && this.onlineReady == this.assigned;
        }
    }
}
