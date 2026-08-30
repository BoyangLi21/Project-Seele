package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Controls the local read-only final-matrix recorder for one real EVA. */
public class ClientboundEvaPoseRecorderPacket
{
    public static final int START = 0;
    public static final int STOP = 1;
    public static final int STATUS = 2;
    public final int operation;
    public final int entityId;
    public final String label;

    public ClientboundEvaPoseRecorderPacket(int operation, int entityId,
                                            String label)
    {
        this.operation = operation;
        this.entityId = entityId;
        this.label = label == null ? "capture" : label;
    }

    public ClientboundEvaPoseRecorderPacket(FriendlyByteBuf buffer)
    {
        this(buffer.readVarInt(), buffer.readVarInt(), buffer.readUtf(64));
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeVarInt(this.operation);
        buffer.writeVarInt(this.entityId);
        buffer.writeUtf(this.label, 64);
    }

    public void handle(Supplier<NetworkEvent.Context> context)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () ->
        {
            if (this.operation == START)
            {
                com.projectseele.client.render.EvaPoseRuntimeRecorder.start(
                        this.entityId, this.label);
            }
            else if (this.operation == STOP)
            {
                com.projectseele.client.render.EvaPoseRuntimeRecorder
                        .stopByCommand();
            }
            else
            {
                com.projectseele.client.render.EvaPoseRuntimeRecorder
                        .showStatus();
            }
        });
        context.get().setPacketHandled(true);
    }
}
