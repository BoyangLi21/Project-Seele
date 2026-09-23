package com.projectseele.network;

import com.projectseele.entity.EntryPlugCarrierEntity;
import com.projectseele.world.EntryPlugDisposalR31;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.network.NetworkEvent;
import java.util.function.Supplier;

/** A physical shell can be ten blocks from its entity origin; validate the shell hit. */
public record ServerboundEntryPlugScrapR31(int entityId)
{
    public ServerboundEntryPlugScrapR31(FriendlyByteBuf buffer){this(buffer.readVarInt());}
    public void encode(FriendlyByteBuf buffer){buffer.writeVarInt(entityId);}
    public void handle(Supplier<NetworkEvent.Context> supplier)
    {
        var context=supplier.get();var player=context.getSender();
        context.enqueueWork(()->{
            if(player==null||player.isSpectator()||player.isPassenger()
                    ||!(player.serverLevel().getEntity(entityId) instanceof EntryPlugCarrierEntity plug))return;
            var hit=EntryPlugDisposalR31.hit(player,plug);
            if(hit.isPresent())plug.hurt(player.damageSources().playerAttack(player),1F);
        });
        context.setPacketHandled(true);
    }
}
