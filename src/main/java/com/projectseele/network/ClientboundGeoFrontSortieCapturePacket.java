package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.core.BlockPos;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Starts the real GeoFront-to-Tokyo-3 launch capture on the integrated client. */
public final class ClientboundGeoFrontSortieCapturePacket
{
    private final int entityId;
    private final BlockPos geoFrontOrigin;

    public ClientboundGeoFrontSortieCapturePacket(int entityId, BlockPos geoFrontOrigin)
    {
        this.entityId = entityId;
        this.geoFrontOrigin = geoFrontOrigin;
    }

    public ClientboundGeoFrontSortieCapturePacket(FriendlyByteBuf buffer)
    {
        this(buffer.readVarInt(), buffer.readBlockPos());
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeVarInt(this.entityId);
        buffer.writeBlockPos(this.geoFrontOrigin);
    }

    public void handle(Supplier<NetworkEvent.Context> context)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> com.projectseele.client.visual.VisualCaptureManager
                        .startGeoFrontSortie(this.entityId, this.geoFrontOrigin));
        context.get().setPacketHandled(true);
    }
}
