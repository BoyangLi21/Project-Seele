package com.projectseele.network;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import java.util.function.Supplier;
public record ClientboundUNStatusPacket(boolean open,String unit00,String unit01,String reply)
{
    public ClientboundUNStatusPacket(FriendlyByteBuf b){this(b.readBoolean(),b.readUtf(2400),b.readUtf(2400),b.readUtf(2400));}
    public void encode(FriendlyByteBuf b){b.writeBoolean(open);b.writeUtf(unit00,2400);b.writeUtf(unit01,2400);b.writeUtf(reply,2400);}
    public void handle(Supplier<NetworkEvent.Context> context)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,()->()->com.projectseele.client.screen.UNPhoneScreen.receive(this));context.get().setPacketHandled(true);
    }
}
