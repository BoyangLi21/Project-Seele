package com.projectseele.network;

import com.projectseele.world.CommanderPoseState;
import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.NetworkEvent;

/** Server-authoritative toggle for the visible Commander Ikari seat pose. */
public final class ServerboundCommandSeatPosePacket
{
    public ServerboundCommandSeatPosePacket()
    {
    }

    public ServerboundCommandSeatPosePacket(FriendlyByteBuf buffer)
    {
    }

    public void encode(FriendlyByteBuf buffer)
    {
    }

    public void handle(Supplier<NetworkEvent.Context> contextSupplier)
    {
        NetworkEvent.Context context = contextSupplier.get();
        context.enqueueWork(() ->
        {
            ServerPlayer sender = context.getSender();
            if (sender == null || !sender.isPassenger())
            {
                return;
            }
            boolean active = CommanderPoseState.toggle(sender);
            sender.displayClientMessage(Component.translatable(
                    active
                            ? "msg.projectseele.commander_pose_on"
                            : "msg.projectseele.commander_pose_off"), true);
        });
        context.setPacketHandled(true);
    }
}
