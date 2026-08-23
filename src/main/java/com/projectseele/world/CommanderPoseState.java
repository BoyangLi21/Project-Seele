package com.projectseele.world;

import com.projectseele.network.ClientboundCommandSeatPosePacket;
import com.projectseele.network.SeeleNetwork;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.PacketDistributor;

/** Server-owned per-player state for the synchronized seated thinking pose. */
public final class CommanderPoseState
{
    private static final String TAG = "ProjectSeeleCommanderPose";

    private CommanderPoseState()
    {
    }

    public static boolean isActive(ServerPlayer player)
    {
        return player.getPersistentData().getBoolean(TAG);
    }

    public static boolean toggle(ServerPlayer player)
    {
        boolean active = !isActive(player);
        setActive(player, active);
        return active;
    }

    public static void setActive(ServerPlayer player, boolean active)
    {
        if (active)
        {
            player.getPersistentData().putBoolean(TAG, true);
        }
        else
        {
            player.getPersistentData().remove(TAG);
        }
        SeeleNetwork.CHANNEL.send(
                PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> player),
                new ClientboundCommandSeatPosePacket(player.getId(), active));
    }

    public static void syncTo(ServerPlayer viewer, ServerPlayer subject)
    {
        SeeleNetwork.CHANNEL.send(
                PacketDistributor.PLAYER.with(() -> viewer),
                new ClientboundCommandSeatPosePacket(subject.getId(),
                        isActive(subject)));
    }
}
