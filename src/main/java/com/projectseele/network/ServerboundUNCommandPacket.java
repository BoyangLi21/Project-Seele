package com.projectseele.network;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.network.NetworkEvent;
import java.util.function.Supplier;
public record ServerboundUNCommandPacket(String action,int serial,int x,int z)
{
    public ServerboundUNCommandPacket(FriendlyByteBuf b){this(b.readUtf(24),b.readVarInt(),b.readInt(),b.readInt());}
    public void encode(FriendlyByteBuf b){b.writeUtf(action,24);b.writeVarInt(serial);b.writeInt(x);b.writeInt(z);}
    public void handle(Supplier<NetworkEvent.Context> context)
    {
        var c=context.get();c.enqueueWork(()->{var player=c.getSender();if(player!=null)com.projectseele.world.UNCommandR29.receive(player,action,serial,x,z);});c.setPacketHandled(true);
    }
}
