package com.projectseele.network;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;
import java.util.function.Supplier;

public record ClientboundBattleFinalePacket(double x, double y, double z)
{
    public ClientboundBattleFinalePacket(FriendlyByteBuf b){this(b.readDouble(),b.readDouble(),b.readDouble());}
    public void encode(FriendlyByteBuf b){b.writeDouble(x);b.writeDouble(y);b.writeDouble(z);}
    public void handle(Supplier<NetworkEvent.Context> context)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,()->()->com.projectseele.client.fx.BattleFinaleClientR29.accept(this));
        context.get().setPacketHandled(true);
    }
}
