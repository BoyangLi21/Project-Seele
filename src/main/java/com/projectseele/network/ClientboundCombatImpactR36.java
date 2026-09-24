package com.projectseele.network;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;
import java.util.function.Supplier;

public record ClientboundCombatImpactR36(Vec3 point,Vec3 direction,float strength,boolean armor)
{
    public ClientboundCombatImpactR36(FriendlyByteBuf b)
    {this(new Vec3(b.readDouble(),b.readDouble(),b.readDouble()),new Vec3(b.readFloat(),b.readFloat(),b.readFloat()),b.readFloat(),b.readBoolean());}
    public void encode(FriendlyByteBuf b)
    {b.writeDouble(point.x);b.writeDouble(point.y);b.writeDouble(point.z);b.writeFloat((float)direction.x);b.writeFloat((float)direction.y);b.writeFloat((float)direction.z);b.writeFloat(strength);b.writeBoolean(armor);}
    public static void handle(ClientboundCombatImpactR36 p,Supplier<NetworkEvent.Context> c)
    {c.get().enqueueWork(()->DistExecutor.unsafeRunWhenOn(Dist.CLIENT,()->()->com.projectseele.client.fx.CombatImpactR36.add(p)));c.get().setPacketHandled(true);}
}
