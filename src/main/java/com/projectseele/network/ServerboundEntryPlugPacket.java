package com.projectseele.network;

import java.util.function.Supplier;

import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraftforge.network.NetworkEvent;

/** Extended right-click ray for synthetic dorsal plug hardware outside the AABB. */
public class ServerboundEntryPlugPacket
{
    private final int entityId;

    public ServerboundEntryPlugPacket(int entityId)
    {
        this.entityId = entityId;
    }

    public ServerboundEntryPlugPacket(FriendlyByteBuf buf)
    {
        this(buf.readVarInt());
    }

    public void encode(FriendlyByteBuf buf)
    {
        buf.writeVarInt(this.entityId);
    }

    public void handle(Supplier<NetworkEvent.Context> ctx)
    {
        ServerPlayer sender = ctx.get().getSender();
        if (sender != null && !sender.isPassenger())
        {
            Entity target = sender.serverLevel().getEntity(this.entityId);
            if (target instanceof EvaUnit01Entity eva)
            {
                // Range, rear sector, line of sight, aim cone, bed ownership
                // and launch state are all re-evaluated on the server.
                eva.tryEnterFromPlug(sender);
            }
        }
        ctx.get().setPacketHandled(true);
    }
}
