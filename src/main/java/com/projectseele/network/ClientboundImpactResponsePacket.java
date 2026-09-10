package com.projectseele.network;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.api.distmarker.Dist;
import java.util.function.Supplier;
public record ClientboundImpactResponsePacket(int entity,long tick,Vec3 direction,float strength,float height)
{
    public ClientboundImpactResponsePacket(FriendlyByteBuf b){this(b.readVarInt(),b.readLong(),new Vec3(b.readFloat(),b.readFloat(),b.readFloat()),b.readFloat(),b.readFloat());}
    public void encode(FriendlyByteBuf b){b.writeVarInt(entity);b.writeLong(tick);b.writeFloat((float)direction.x);b.writeFloat((float)direction.y);b.writeFloat((float)direction.z);b.writeFloat(strength);b.writeFloat(height);}
    public void handle(Supplier<NetworkEvent.Context> c){DistExecutor.unsafeRunWhenOn(Dist.CLIENT,()->()->com.projectseele.client.EvaImpactClient.receive(this));c.get().setPacketHandled(true);}
}
