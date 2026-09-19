package com.projectseele.network;

import java.util.UUID;
import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.network.NetworkEvent;

public record ServerboundStaffConversationPacket(UUID session, String request)
{
    public ServerboundStaffConversationPacket(FriendlyByteBuf buffer)
    { this(buffer.readUUID(), buffer.readUtf(160)); }
    public void encode(FriendlyByteBuf buffer)
    { buffer.writeUUID(session); buffer.writeUtf(request, 160); }
    public void handle(Supplier<NetworkEvent.Context> supplier)
    {
        var context = supplier.get(); var player = context.getSender();
        context.enqueueWork(() ->
        {
            if (player != null) com.projectseele.world.StaffConversationR24.receive(player, session, request);
        });
        context.setPacketHandled(true);
    }
}
