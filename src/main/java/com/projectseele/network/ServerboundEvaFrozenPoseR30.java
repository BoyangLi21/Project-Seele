package com.projectseele.network;

import com.projectseele.entity.EvaShutdownR30;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.network.NetworkEvent;
import java.util.function.Supplier;

/** A pilot may supply one bounded visual snapshot after the server has declared power loss. */
public record ServerboundEvaFrozenPoseR30(int entity,CompoundTag pose)
{
    public ServerboundEvaFrozenPoseR30(FriendlyByteBuf b){this(b.readVarInt(),read(b));}
    private static CompoundTag read(FriendlyByteBuf b){if(b.readableBytes()>32768)throw new IllegalArgumentException("Frozen pose too large");var t=b.readNbt();return t==null?new CompoundTag():t;}
    public void encode(FriendlyByteBuf b){b.writeVarInt(entity);b.writeNbt(pose);}
    public void handle(Supplier<NetworkEvent.Context> context)
    {var p=context.get().getSender();if(p!=null)EvaShutdownR30.acceptPilotPose(p,entity,pose);context.get().setPacketHandled(true);}
}
