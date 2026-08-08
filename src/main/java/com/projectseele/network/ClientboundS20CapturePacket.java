package com.projectseele.network;

import java.util.function.Supplier;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Starts the read-only fixed-camera review of the clean S20 world. */
public final class ClientboundS20CapturePacket
{
    public ClientboundS20CapturePacket()
    {
    }

    public ClientboundS20CapturePacket(FriendlyByteBuf buffer)
    {
    }

    public void encode(FriendlyByteBuf buffer)
    {
    }

    public void handle(Supplier<NetworkEvent.Context> context)
    {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () ->
                {
                    if ("s20_plug".equals(System.getProperty(
                            "projectseele.visualCaptureUnit")))
                    {
                        com.projectseele.client.visual.VisualCaptureManager
                                .startS20Plug();
                    }
                    else
                    {
                        com.projectseele.client.visual.VisualCaptureManager
                                .startS20();
                    }
                });
        context.get().setPacketHandled(true);
    }
}
