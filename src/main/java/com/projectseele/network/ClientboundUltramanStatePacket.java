package com.projectseele.network;

import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Synchronizes the Hayata pose and Ultraman scale to tracking clients. */
public final class ClientboundUltramanStatePacket
{
    private final int entityId;
    private final boolean active;
    private final float currentScale;
    private final boolean hayataPose;

    public ClientboundUltramanStatePacket(int entityId, boolean active,
            float currentScale, boolean hayataPose)
    {
        this.entityId = entityId;
        this.active = active;
        this.currentScale = currentScale;
        this.hayataPose = hayataPose;
    }

    public ClientboundUltramanStatePacket(FriendlyByteBuf buffer)
    {
        this(buffer.readVarInt(), buffer.readBoolean(), buffer.readFloat(),
                buffer.readBoolean());
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeVarInt(this.entityId);
        buffer.writeBoolean(this.active);
        buffer.writeFloat(this.currentScale);
        buffer.writeBoolean(this.hayataPose);
    }

    public void handle(Supplier<NetworkEvent.Context> supplier)
    {
        NetworkEvent.Context context = supplier.get();
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.UltramanClientState
                        .setTarget(this.entityId, this.active,
                                this.currentScale, this.hayataPose));
        context.setPacketHandled(true);
    }
}
