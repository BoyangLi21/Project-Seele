package com.projectseele.network;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.network.NetworkEvent;
import java.util.UUID;
import java.util.function.Supplier;

/** Server-owned articulated pose and matching collision bounds, in one update. */
public record ClientboundCombatBodyPose(int id,UUID uuid,int mode,Vec3 position,float yaw,AABB bounds,CompoundTag pose)
{
    public ClientboundCombatBodyPose(FriendlyByteBuf b)
    {this(b.readVarInt(),b.readUUID(),b.readVarInt(),new Vec3(b.readDouble(),b.readDouble(),b.readDouble()),b.readFloat(),new AABB(b.readDouble(),b.readDouble(),b.readDouble(),b.readDouble(),b.readDouble(),b.readDouble()),b.readNbt());}
    public void encode(FriendlyByteBuf b)
    {b.writeVarInt(id);b.writeUUID(uuid);b.writeVarInt(mode);b.writeDouble(position.x);b.writeDouble(position.y);b.writeDouble(position.z);b.writeFloat(yaw);b.writeDouble(bounds.minX);b.writeDouble(bounds.minY);b.writeDouble(bounds.minZ);b.writeDouble(bounds.maxX);b.writeDouble(bounds.maxY);b.writeDouble(bounds.maxZ);b.writeNbt(pose);}
    public static void handle(ClientboundCombatBodyPose packet,Supplier<NetworkEvent.Context> context)
    {context.get().enqueueWork(()->com.projectseele.client.CombatBodyClient.receive(packet));context.get().setPacketHandled(true);}
}
