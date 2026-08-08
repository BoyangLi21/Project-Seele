package com.projectseele.world;

import com.projectseele.network.ClientboundCommandScreenStatePacket;
import com.projectseele.network.SeeleNetwork;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraftforge.network.PacketDistributor;

/** Persistent operator-controlled visibility for the four S20 command screens. */
public final class NervCommandDisplayState extends SavedData
{
    /**
     * Three cockpit feeds, the lower tactical board, and the rear Tokyo-3
     * city wall.  The city wall is a server-side text display rather than a
     * client raster, so it is switched by removing the entity.
     */
    public static final int SCREEN_COUNT = 5;
    public static final int CITY_SCREEN = 4;
    public static final int ALL_VISIBLE_MASK = (1 << SCREEN_COUNT) - 1;

    private static final String DATA_NAME =
            "projectseele_nerv_command_displays";
    /*
     * Version 2 adds the city wall bit.  A version-1 mask has that bit clear,
     * which would silently blank a screen that was on before the update, so an
     * older payload is deliberately discarded and everything comes back lit.
     */
    private static final int DATA_VERSION = 2;

    private int visibleMask = ALL_VISIBLE_MASK;

    public static NervCommandDisplayState get(MinecraftServer server)
    {
        return server.overworld().getDataStorage().computeIfAbsent(
                NervCommandDisplayState::load,
                NervCommandDisplayState::new, DATA_NAME);
    }

    public static NervCommandDisplayState load(CompoundTag tag)
    {
        NervCommandDisplayState state = new NervCommandDisplayState();
        if (tag.getInt("Version") == DATA_VERSION)
        {
            state.visibleMask = tag.getInt("VisibleMask")
                    & ALL_VISIBLE_MASK;
        }
        return state;
    }

    public int visibleMask()
    {
        return this.visibleMask;
    }

    public boolean isVisible(int screen)
    {
        return (this.visibleMask & 1 << screen) != 0;
    }

    public boolean toggle(int screen)
    {
        if (screen < 0 || screen >= SCREEN_COUNT)
        {
            throw new IllegalArgumentException(
                    "Invalid NERV command screen index " + screen);
        }
        this.visibleMask ^= 1 << screen;
        this.setDirty();
        return (this.visibleMask & 1 << screen) != 0;
    }

    public void broadcast(ServerLevel level)
    {
        ClientboundCommandScreenStatePacket packet =
                new ClientboundCommandScreenStatePacket(this.visibleMask);
        SeeleNetwork.CHANNEL.send(
                PacketDistributor.DIMENSION.with(level::dimension), packet);
    }

    public static void syncTo(ServerPlayer player)
    {
        ClientboundCommandScreenStatePacket packet =
                new ClientboundCommandScreenStatePacket(
                        get(player.getServer()).visibleMask());
        SeeleNetwork.CHANNEL.send(
                PacketDistributor.PLAYER.with(() -> player), packet);
    }

    @Override
    public CompoundTag save(CompoundTag tag)
    {
        tag.putInt("Version", DATA_VERSION);
        tag.putInt("VisibleMask", this.visibleMask);
        return tag;
    }
}
